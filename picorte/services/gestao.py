"""Fontes e Escudo (história 6.7). C1: liberar ou mudar permissão exige base + evidência + motivo, com histórico."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from picorte.db.repositories import PicorteRepositories
from picorte.risk_shield.policy_gate import ALLOWED_PERMISSION_STATUSES
from picorte.services.mesa import _eh_p1

STATUS_VALIDOS = set(ALLOWED_PERMISSION_STATUSES) | {"desconhecida", "lista_negra"}
REDES = ("youtube_shorts", "youtube_long", "tiktok", "instagram_reels", "facebook_reels")
TIPOS_CLAIM = {"copyright_claim": "claim de bloqueio", "strike": "strike", "desmonetizacao": "desmonetização"}


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _texto(dados: dict[str, Any], chave: str) -> str:
    return str(dados.get(chave) or "").strip()


def _validar_permissao(status: str, base: str, evidencia: str, motivo: str) -> None:
    if status not in STATUS_VALIDOS:
        raise ValueError(f"Status de permissão inválido: {status or 'vazio'}.")
    if status in ALLOWED_PERMISSION_STATUSES:
        if not base:
            raise ValueError("Para liberar a fonte, informe a base da permissão.")
        if not evidencia:
            raise ValueError("Para liberar a fonte, informe a evidência (link ou nota).")
    if not motivo:
        raise ValueError("Informe o motivo da mudança: ele fica no histórico.")


def listar_fontes(db, registro: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cadastrados = {str(s.get("handle") or f"@{s.get('slug')}").lower() for s in registro}
    saida = []
    for f in PicorteRepositories(db).sources.list_sources():
        n_v = db.fetch_one("SELECT COUNT(*) AS n FROM videos WHERE source_id = ? AND archived_at IS NULL", (f["id"],))["n"]
        n_c = db.fetch_one("SELECT COUNT(*) AS n FROM clips c JOIN videos v ON v.id = c.video_id "
                           "WHERE v.source_id = ? AND c.archived_at IS NULL", (f["id"],))["n"]
        saida.append({"id": f["id"], "nome": f["name"], "plataforma": f["platform"], "handle": f["channel_handle"],
                      "status": f["permission_status"], "base": f.get("permission_basis") or "",
                      "evidencia": f.get("permission_evidence_url") or "", "jogo": f.get("default_game_slug") or "",
                      "no_cadastro": str(f["channel_handle"] or "").lower() in cadastrados,
                      "videos": int(n_v), "cortes": int(n_c)})
    return saida


def cadastrar_fonte(db, dados: dict[str, Any]) -> dict[str, Any]:
    nome, handle, plataforma = _texto(dados, "nome"), _texto(dados, "handle").lower(), _texto(dados, "plataforma")
    status, base, evidencia, motivo = (_texto(dados, k) for k in ("status", "base", "evidencia", "motivo"))
    if not nome or not handle or plataforma not in {"youtube", "twitch", "kick"}:
        raise ValueError("Informe nome, @ do canal e a plataforma (youtube, twitch ou kick).")
    status = status or "desconhecida"
    _validar_permissao(status, base, evidencia, motivo)
    if db.fetch_one("SELECT id FROM sources WHERE lower(channel_handle) = ?", (handle,)):
        raise ValueError("Já existe uma fonte com esse @.")
    f = PicorteRepositories(db).sources.create_source(
        name=nome, platform=plataforma, channel_handle=handle, permission_status=status,
        permission_evidence_url=evidencia, permission_basis=base or "explicita")
    return {"id": f["id"], "nome": f["name"], "status": f["permission_status"]}


def mudar_permissao(db, source_id: str, dados: dict[str, Any]) -> dict[str, Any]:
    status, base, evidencia, motivo = (_texto(dados, k) for k in ("status", "base", "evidencia", "motivo"))
    _validar_permissao(status, base, evidencia, motivo)
    fonte = db.fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))
    if not fonte:
        raise ValueError("Fonte não encontrada.")
    agora = _agora()
    with db.transaction() as tx:
        tx.execute("UPDATE sources SET permission_status = ?, permission_basis = ?, permission_evidence_url = ?, "
                   "updated_at = ? WHERE id = ?",
                   (status, base or fonte.get("permission_basis") or "explicita",
                    evidencia or fonte.get("permission_evidence_url") or "", agora, source_id))
        tx.execute("INSERT INTO fontes_historico (source_id, de, para, base, evidencia, motivo, em) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (source_id, fonte["permission_status"], status, base, evidencia, motivo, agora))
    return {"id": source_id, "de": fonte["permission_status"], "para": status}


def fontes_barradas(projetos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    saida = []
    for p in projetos:
        erro = str(p.get("error") or "")
        if p.get("status") != "failed" or not _eh_p1(erro):
            continue
        m = re.search(r"Fonte desconhecida:\s*'([^']+)'", erro)
        quando = p.get("updated")
        saida.append({"projeto": p.get("id"), "canal": m.group(1) if m else None, "url": p.get("source"),
                      "quando": datetime.fromtimestamp(float(quando), tz=timezone.utc).isoformat() if quando else None,
                      "motivo": erro})
    return saida


def criar_campanha(db, dados: dict[str, Any]) -> dict[str, Any]:
    fonte = _texto(dados, "fonte")
    if not db.fetch_one("SELECT id FROM sources WHERE id = ?", (fonte,)):
        raise ValueError("Escolha uma fonte cadastrada.")
    try:
        cpm = float(dados.get("cpm_brl") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("CPM precisa ser um número.") from exc
    if cpm < 0:
        raise ValueError("CPM não pode ser negativo.")
    tags = dados.get("tags") or []
    if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
        raise ValueError("Tags precisam ser uma lista de textos.")
    return PicorteRepositories(db).campaigns.create_campaign(
        source_id=fonte, game_slug=_texto(dados, "jogo"), cpm_brl=cpm, required_tags=tags,
        starts_at=_texto(dados, "inicio") or None, expires_at=_texto(dados, "expira") or None)


def listar_campanhas(db, agora: str | None = None) -> list[dict[str, Any]]:
    agora = agora or _agora()
    linhas = db.fetch_all("SELECT c.*, s.name AS fonte_nome FROM campaigns c LEFT JOIN sources s ON s.id = c.source_id "
                          "ORDER BY c.starts_at DESC")
    return [{"id": c["id"], "fonte": c["fonte_nome"], "jogo": c["game_slug"], "cpm_brl": c["cpm_brl"],
             "tags": json.loads(c["required_tags"] or "[]"), "inicio": c["starts_at"], "expira": c["expires_at"],
             "vencida": bool(c["expires_at"] and c["expires_at"] < agora)} for c in linhas]


def eventos_de_pausa(db) -> list[dict[str, Any]]:
    claims = db.fetch_all("SELECT ce.*, s.name AS fonte FROM claims_events ce LEFT JOIN sources s ON s.id = ce.source_id")
    historico = db.fetch_all("SELECT h.*, s.name AS fonte FROM fontes_historico h LEFT JOIN sources s ON s.id = h.source_id")
    eventos = [{"tipo": "claim", "fonte": c["fonte"], "de": None, "para": "pausada",
                "motivo": f"{TIPOS_CLAIM.get(c['claim_type'], c['claim_type'])} · {c['details']}", "quando": c["detected_at"],
                "_ordem": 0} for c in claims]
    eventos += [{"tipo": "permissao", "fonte": h["fonte"], "de": h["de"], "para": h["para"], "motivo": h["motivo"],
                 "quando": h["em"], "_ordem": h["id"]} for h in historico]
    eventos.sort(key=lambda e: (e["quando"] or "", e["_ordem"]), reverse=True)
    for e in eventos:
        e.pop("_ordem")
    return eventos


def previa_claim(db, source_id: str) -> dict[str, Any]:
    fonte = db.fetch_one("SELECT name FROM sources WHERE id = ?", (source_id,))
    if not fonte:
        raise ValueError("Fonte não encontrada.")
    videos = db.fetch_one("SELECT COUNT(*) AS n FROM videos WHERE source_id = ?", (source_id,))["n"]
    cortes = db.fetch_one("SELECT COUNT(*) AS n FROM clips c JOIN videos v ON v.id = c.video_id WHERE v.source_id = ?",
                          (source_id,))["n"]
    pendentes = db.fetch_one("SELECT COUNT(*) AS n FROM publications p JOIN clips c ON c.id = p.clip_id "
                             "JOIN videos v ON v.id = c.video_id WHERE v.source_id = ? AND p.status IN ('fila', 'agendado')",
                             (source_id,))["n"]
    return {"fonte": fonte["name"], "videos": int(videos), "cortes": int(cortes), "publicacoes_pendentes": int(pendentes)}


def registrar_claim(db, dados: dict[str, Any]) -> dict[str, Any]:
    from picorte.risk_shield.source_breaker import pause_source_globally
    fonte, rede, link, tipo, motivo = (_texto(dados, k) for k in ("fonte", "rede", "link", "tipo", "motivo"))
    if rede not in REDES or tipo not in TIPOS_CLAIM:
        raise ValueError("Informe a rede e o tipo do claim.")
    if not motivo:
        raise ValueError("Informe o motivo: ele fica no histórico de pausas.")
    return pause_source_globally(db, source_id=fonte, claim_type=tipo, details=f"{rede} · {link}".strip(" ·"), reason=motivo)


def estado_escudo(state_path=None) -> dict[str, dict[str, Any]]:
    from picorte.risk_shield.cadence_guard import get_cooldown_status
    return {rede: {"ate": info["until"], "motivo": info.get("reason") or "", "restante_h": info["remaining_hours"],
                   "pode_limpar": True}  # hoje todo cooldown gravado é do operador (C1); o automático é a cadência
            for rede, info in get_cooldown_status(state_path=state_path).items()}


def criar_cooldown(rede: str, horas: float, motivo: str, state_path=None) -> dict[str, Any]:
    from picorte.risk_shield.cadence_guard import activate_cooldown
    if rede not in REDES:
        raise ValueError("Rede inválida.")
    if not str(motivo or "").strip():
        raise ValueError("Informe o motivo do cooldown.")
    return activate_cooldown(rede, hours=horas, reason=str(motivo).strip(), state_path=state_path)


def limpar_cooldown(rede: str, motivo: str, state_path=None) -> dict[str, Any]:
    from picorte.risk_shield.cadence_guard import clear_cooldown
    if not str(motivo or "").strip():
        raise ValueError("Informe o motivo para limpar o cooldown.")
    return clear_cooldown(rede, state_path=state_path)
