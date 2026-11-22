"""Sala do vídeo (história 6.5): metadados e portão P1 com a mesma régua do preparo. Nunca baixa mídia."""
from __future__ import annotations

import re
from typing import Any, Callable

from picorte.risk_shield.policy_gate import PolicyViolationError
from picorte.services.vitrine import id_do_video, indice_projetos

LINK = re.compile(r"^https?://(www\.|m\.)?(youtube\.com/(watch\?|live/|shorts/)|youtu\.be/|twitch\.tv/videos/|"
                  r"(www\.)?kick\.com/[^/]+/videos?/|kick\.com/video/)", re.I)
AVISO_LINK = "Isso não parece um link de vídeo do YouTube, Twitch ou Kick."


def validar_link(url: str) -> str:
    limpo = str(url or "").strip()
    if not LINK.match(limpo):
        raise ValueError(AVISO_LINK)
    return limpo


def _plataforma(url: str) -> str:
    u = url.lower()
    return "youtube" if ("youtube" in u or "youtu.be" in u) else ("twitch" if "twitch" in u else "kick")


def abrir_sala(url: str, *, db: Any, projetos: list[dict[str, Any]],
               sondar: Callable[[str], dict[str, Any]] | None = None,
               portao: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    url = validar_link(url)
    if sondar is None:
        import ingest
        sondar = ingest.probe_source
    if portao is None:
        from picorte.risk_shield.source_resolver import gate_project_source as portao
    try:
        meta = dict(sondar(url) or {})
    except Exception as exc:
        raise ValueError(f"Não consegui ler este vídeo agora ({type(exc).__name__}). Tente de novo.") from exc
    meta.pop("formats", None)
    try:
        g = portao(db, source_input=url, meta=meta)
        veredito = {"liberado": True, "fonte": g.get("source_name") or g.get("channel_handle"),
                    "base": g.get("permission_basis")}
    except PolicyViolationError as exc:
        veredito = {"liberado": False, "codigo": getattr(exc, "code", "p1_blocked"), "motivo": str(exc)}
    vid = id_do_video(url)
    duracao = meta.get("duration")
    return {
        "video": {"url": url, "titulo": str(meta.get("title") or ""), "canal": str(meta.get("channel") or ""),
                  "duracao_s": int(duracao) if isinstance(duracao, (int, float)) else None,
                  "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None,
                  "ao_vivo": meta.get("live_status") == "is_live", "plataforma": _plataforma(url),
                  "id_youtube": vid},
        "portao": veredito,
        "projeto": indice_projetos(projetos).get(vid) if vid else None,
    }
