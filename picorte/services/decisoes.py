"""Decisões da Revisão (história 6.6, B10): 👍/👎 opcional com motivo de 1 clique, descarte e Exemplo Ouro."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock

from picorte.config import PROJECT_ROOT

MOTIVOS_RUIM = ("título ruim", "borda errada", "momento fraco", "já publicado")
BIBLIOTECA_OURO = PROJECT_ROOT / "picorte" / "ai" / "golden_examples.json"
SEG = re.compile(r"\d{1,4}")


def _clip(pid: str, seg: str) -> str:
    if not SEG.fullmatch(str(seg)):
        raise ValueError("Corte inválido.")
    return f"studio-{pid}:{seg}"


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _garantir(db, clip_id: str) -> None:
    db.execute("INSERT INTO revisao_cortes (clip_id, atualizado_em) VALUES (?, ?) ON CONFLICT(clip_id) DO NOTHING",
               (clip_id, _agora()))


def ler_decisoes(db, pid: str) -> dict[str, dict[str, Any]]:
    prefixo = f"studio-{pid}:"
    linhas = db.fetch_all("SELECT * FROM revisao_cortes WHERE clip_id LIKE ?", (prefixo + "%",))
    return {str(r["clip_id"])[len(prefixo):]: {
        "rotulo": r["rotulo"], "motivo": r["motivo"] or "",
        "descartado": bool(r["descartado"]), "exemplo_ouro": bool(r["exemplo_ouro"]),
    } for r in linhas}


def gravar_rotulo(db, pid: str, seg: str, valor: int, motivo: str = "") -> None:
    """valor 1 = 👍, -1 = 👎, 0 = tirar o rótulo. Nunca muda o destino do corte (C3)."""
    if valor not in (-1, 0, 1):
        raise ValueError("O rótulo é 1 (bom), -1 (ruim) ou 0 (tirar).")
    motivo = str(motivo or "").strip()
    if motivo and motivo not in MOTIVOS_RUIM:
        raise ValueError("Motivo fora da lista de 1 clique.")
    clip_id = _clip(pid, seg)
    _garantir(db, clip_id)
    db.execute("UPDATE revisao_cortes SET rotulo = ?, motivo = ?, atualizado_em = ? WHERE clip_id = ?",
               (None if valor == 0 else valor, "" if valor == 0 else motivo, _agora(), clip_id))


def gravar_descarte(db, pid: str, seg: str, descartado: bool) -> None:
    clip_id = _clip(pid, seg)
    _garantir(db, clip_id)
    db.execute("UPDATE revisao_cortes SET descartado = ?, atualizado_em = ? WHERE clip_id = ?",
               (1 if descartado else 0, _agora(), clip_id))


def _faixa_duracao(segundos: float) -> str:
    return "short" if segundos <= 60 else ("medium" if segundos <= 180 else "long")


def salvar_exemplo_ouro(db, pid: str, pasta: Path, estado: dict[str, Any], seg: str,
                        arquivo: Path = BIBLIOTECA_OURO) -> dict[str, Any]:
    """Copia o corte para a biblioteca viva de exemplos ouro (lida pelo Editor-Chefe), sem duplicar."""
    clip_id = _clip(pid, seg)
    try:
        segmentos = json.loads((Path(pasta) / "segments.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        segmentos = []
    alvo = next((s for n, s in enumerate(segmentos, 1)
                 if isinstance(s, dict) and str(s.get("id") or f"{n:03}") == str(seg)), None)
    if alvo is None:
        raise KeyError(f"corte {seg}")
    inicio, fim = float(alvo.get("start") or 0), float(alvo.get("end") or 0)
    exemplo = {
        "id": f"{pid}-{seg}", "archetype": alvo.get("archetype"), "tier": alvo.get("tier"),
        "game": str((estado.get("source_meta") or {}).get("detected_game") or ""),
        "source_url": str(estado.get("source") or ""),
        "summary": str(alvo.get("proposed_title") or alvo.get("hook") or ""),
        "why_gold": str(alvo.get("why_extraordinary") or alvo.get("reason") or ""),
        "ideal_context_banner": str(alvo.get("context_banner_2s") or ""),
        "ideal_duration_bucket": _faixa_duracao(fim - inicio),
    }
    arquivo = Path(arquivo)
    with FileLock(str(arquivo) + ".lock"):
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            dados = {"version": 1, "examples": []}
        if isinstance(dados, list):
            dados = {"version": 1, "examples": dados}
        exemplos = [e for e in dados.get("examples") or [] if isinstance(e, dict) and e.get("id") != exemplo["id"]]
        dados["examples"] = exemplos + [exemplo]
        temp = arquivo.with_suffix(arquivo.suffix + ".tmp")
        temp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(arquivo)
    _garantir(db, clip_id)
    db.execute("UPDATE revisao_cortes SET exemplo_ouro = 1, atualizado_em = ? WHERE clip_id = ?", (_agora(), clip_id))
    return exemplo
