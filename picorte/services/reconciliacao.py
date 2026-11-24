"""Banco × disco (B4) e preparação do banco no boot (B6) — história 6.4. Nunca escreve em projects/."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picorte.services.studio_service import StudioService


def _ler_json(caminho: Path, padrao: Any) -> Any:
    try:
        return json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return padrao


def sincronizar_pasta(servico: StudioService, pasta: Path, estado: dict[str, Any] | None = None) -> dict[str, Any]:
    """Espelha uma pasta de projeto no banco lendo project.json, segments.json e transcript.json (só leitura)."""
    pasta = Path(pasta)
    estado = estado if estado is not None else _ler_json(pasta / "project.json", {})
    if not isinstance(estado, dict) or not estado.get("id"):
        raise ValueError(f"project.json ilegível em {pasta.name}")
    segmentos = _ler_json(pasta / "segments.json", [])
    transcricao = _ler_json(pasta / "transcript.json", {})
    duracao = float(transcricao.get("duration") or 0.0) if isinstance(transcricao, dict) else 0.0
    return servico.sync_studio_project(
        estado,
        segments=segmentos if isinstance(segmentos, list) else [],
        outputs=estado.get("last_outputs") or [],
        workdir=pasta,
        duration_seconds=duracao,
    )


def _presente(video: dict[str, Any], raiz: Path) -> bool:
    workdir = str(video.get("workdir_path") or "").strip()
    if workdir and Path(workdir).is_dir():
        return True
    vid = str(video.get("id") or "")
    return vid.startswith("studio-") and (raiz / vid[len("studio-"):] / "project.json").is_file()


def _religar_publicacoes(db, agora: str) -> int:
    """Publicação registrada à mão antes da 6.4 apontava para um corte criado pelo nome do arquivo
    ("studio-<pid>:003-<hash>-<título>"); passa a apontar para o corte do sync ("studio-<pid>:003")."""
    religadas = 0
    # padrão como parâmetro: no Postgres um "%" literal na consulta seria lido como marcador do psycopg
    for pub in db.fetch_all("SELECT id, clip_id FROM publications WHERE clip_id LIKE ?", ("studio-%:%-%",)):
        video, _, nome = str(pub["clip_id"]).partition(":")
        alvo = f"{video}:{nome.split('-', 1)[0]}"
        if alvo == pub["clip_id"] or not db.fetch_one("SELECT id FROM clips WHERE id = ?", (alvo,)):
            continue
        db.execute("UPDATE publications SET clip_id = ? WHERE id = ?", (alvo, pub["id"]))
        db.execute("UPDATE clips SET archived_at = COALESCE(archived_at, ?) WHERE id = ? "
                   "AND NOT EXISTS (SELECT 1 FROM publications WHERE clip_id = ?)",
                   (agora, pub["clip_id"], pub["clip_id"]))
        religadas += 1
    return religadas


def reconciliar(db, raiz) -> dict[str, Any]:
    """B4: re-sincroniza as pastas existentes e arquiva (nunca apaga) o que sumiu do disco."""
    raiz = Path(raiz)
    servico = StudioService(db)
    ressincronizados, falhas = 0, []
    for arquivo in sorted(raiz.glob("*/project.json")):
        try:
            sincronizar_pasta(servico, arquivo.parent)
            ressincronizados += 1
        except Exception as exc:  # um projeto quebrado não impede os outros
            falhas.append(f"{arquivo.parent.name}: {type(exc).__name__}: {exc}")
    agora = datetime.now(timezone.utc).isoformat()
    religadas = _religar_publicacoes(db, agora)
    arquivados = reativados = 0
    for video in db.fetch_all("SELECT id, workdir_path, archived_at FROM videos"):
        presente = _presente(video, raiz)
        if presente and video.get("archived_at"):
            db.execute("UPDATE videos SET archived_at = NULL WHERE id = ?", (video["id"],))
            db.execute("UPDATE clips SET archived_at = NULL WHERE video_id = ?", (video["id"],))
            reativados += 1
        elif not presente and not video.get("archived_at"):
            db.execute("UPDATE videos SET archived_at = ? WHERE id = ?", (agora, video["id"]))
            db.execute("UPDATE clips SET archived_at = ? WHERE video_id = ? AND archived_at IS NULL",
                       (agora, video["id"]))
            arquivados += 1
    return {"ressincronizados": ressincronizados, "arquivados": arquivados, "reativados": reativados,
            "publicacoes_religadas": religadas, "falhas": falhas}


def preparar_banco(db, raiz) -> dict[str, Any]:
    """Boot do Estúdio: migração, políticas de publisher (B6) e reconciliação banco × disco (B4)."""
    from picorte.risk_shield.policy_gate import sync_publisher_policies

    db.init_schema()
    return {"politicas": sync_publisher_policies(db), **reconciliar(db, raiz)}


def arquivar_projeto(db, pid: str) -> bool:
    """Apagar pela UI: o vídeo e os cortes do projeto saem das listas, mas ficam no banco (histórico, publicações)."""
    from datetime import datetime, timezone
    video_id = f"studio-{pid}"
    if not db.fetch_one("SELECT id FROM videos WHERE id = ?", (video_id,)):
        return False
    agora = datetime.now(timezone.utc).isoformat()
    db.execute("UPDATE videos SET archived_at = COALESCE(archived_at, ?) WHERE id = ?", (agora, video_id))
    db.execute("UPDATE clips SET archived_at = COALESCE(archived_at, ?) WHERE video_id = ?", (agora, video_id))
    return True
