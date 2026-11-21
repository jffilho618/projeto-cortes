"""D1 (code review Épico 4) — Identifica a fonte de um projeto pelo CANAL e aplica o Hard Gate Pre-Ingest.

Regras (decididas pelo dono em 2026-11-20):
- Os streamers do `assets/streamers/registry.json` nascem `liberada` com `permission_basis='tolerancia_publica'`
  (sem permissão formal; rede de segurança = crédito + aviso de remoção + disjuntor no 1º claim).
- A identificação usa SOMENTE a identidade do canal (nome, handle, URL do canal/Twitch), nunca o título nem
  apelidos — assim "Cortes do X" ou "X reage..." publicados por terceiros não passam como se fossem do X.
- Arquivo local exige declaração de dono: `proprio` (gameplay próprio) ou o slug de um streamer cadastrado.
- O seed nunca rebaixa nem promove uma fonte que já existe (uma fonte pausada por claim continua pausada).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories

from .policy_gate import PolicyViolationError, assert_can_ingest

OWN_GAMEPLAY_OWNER = "proprio"
OWN_GAMEPLAY_HANDLE = "@gameplay-proprio"
_TWITCH_RESERVED = {"videos", "directory", "settings", "p", "search", "downloads"}


def _key(text: str | None) -> str:
    from picorte.engine.publish_kit import _norm_text

    return _norm_text(text).replace(" ", "")


def _url_identity(url: str | None) -> str:
    """Extrai o login/handle de URLs de canal (twitch.tv/<login>, youtube.com/@handle)."""
    if not url:
        return ""
    parsed = urlparse(str(url).strip())
    host = (parsed.netloc or "").lower()
    parts = [p for p in (parsed.path or "").split("/") if p]
    if not parts:
        return ""
    if "twitch.tv" in host:
        return "" if parts[0].lower() in _TWITCH_RESERVED else _key(parts[0])
    if "youtube.com" in host and parts[0].startswith("@"):
        return _key(parts[0][1:])
    if "youtube.com" in host and parts[0] == "channel" and len(parts) > 1:
        return "ytchannel:" + parts[1].strip()  # ID do canal (UC...), exato
    return ""


def _streamer_identities(st: dict[str, Any]) -> set[str]:
    ids = {
        _key(st.get("display_name")),
        _key(st.get("slug")),
        _key(str(st.get("handle") or "").lstrip("@")),
        _url_identity(st.get("youtube")),
        _url_identity(st.get("twitch")),
    }
    # Canais oficiais extras do mesmo streamer (ex.: canal só de lives), liberados pelo dono.
    ids.update(_url_identity(url) for url in st.get("extra_channels") or [])
    return {i for i in ids if i}


def _handle_of(st: dict[str, Any]) -> str:
    return str(st.get("handle") or f"@{st.get('slug')}").strip().lower()


def _load_registry(registry_path: Path | str | None) -> list[dict[str, Any]]:
    from picorte.engine.publish_kit import load_streamer_registry

    return list(load_streamer_registry(registry_path).get("streamers") or [])


def seed_registry_sources(db: Database, *, registry_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Cria as fontes dos streamers cadastrados como `liberada` / `tolerancia_publica` (só as que faltam)."""
    repos = PicorteRepositories(db)
    existing = {str(s.get("channel_handle") or "").strip().lower() for s in repos.sources.list_sources()}
    created: list[dict[str, Any]] = []
    for st in _load_registry(registry_path):
        handle = _handle_of(st)
        if handle in existing:
            continue
        created.append(
            repos.sources.create_source(
                name=str(st.get("display_name") or st.get("slug") or handle),
                platform="twitch" if st.get("twitch") else "youtube",
                channel_handle=handle,
                permission_status="liberada",
                permission_basis="tolerancia_publica",
                credit_template=f"Créditos: {handle}",
            )
        )
        existing.add(handle)
    return created


def _ensure_own_gameplay_source(db: Database) -> None:
    repos = PicorteRepositories(db)
    if any(str(s.get("channel_handle") or "").lower() == OWN_GAMEPLAY_HANDLE for s in repos.sources.list_sources()):
        return
    repos.sources.create_source(
        name="Gameplay próprio",
        platform="local",
        channel_handle=OWN_GAMEPLAY_HANDLE,
        permission_status="gameplay_proprio",
        permission_basis="explicita",
        credit_template="",
    )


def match_registered_streamer(
    *, channel: str | None, source_url: str | None, channel_url: str | None = None,
    registry_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """Casa o canal com um streamer cadastrado usando apenas identidade de canal (nunca título/apelido)."""
    probes = {_key(channel), _url_identity(channel_url), _url_identity(source_url)}
    probes.discard("")
    if not probes:
        return None
    for st in _load_registry(registry_path):
        if probes & _streamer_identities(st):
            return st
    return None


def _match_by_owner(owner: str, registry_path: Path | str | None) -> dict[str, Any] | None:
    want = _key(owner.lstrip("@"))
    for st in _load_registry(registry_path):
        if want in _streamer_identities(st):
            return st
    return None


def gate_project_source(
    db: Database,
    *,
    source_input: str,
    meta: dict[str, Any] | None,
    owner: str | None = None,
    registry_path: Path | str | None = None,
) -> dict[str, Any]:
    """Hard Gate Pre-Ingest de um projeto. Levanta PolicyViolationError antes de qualquer download."""
    meta = meta or {}
    seed_registry_sources(db, registry_path=registry_path)
    is_url = bool(meta.get("url")) or bool(re.match(r"^https?://", str(source_input or ""), re.I))

    if is_url:
        st = match_registered_streamer(
            channel=meta.get("channel"),
            source_url=source_input,
            channel_url=meta.get("channel_url"),
            registry_path=registry_path,
        )
        if st is None:
            label = meta.get("channel") or "canal não identificado"
            raise PolicyViolationError(
                f"[P1:pre_ingest] Fonte desconhecida: '{label}' não está entre os streamers cadastrados. "
                "Nada foi baixado. Cadastre e libere a fonte antes de processar.",
                code="source_unknown",
                details={"stage": "pre_ingest", "channel": meta.get("channel"), "source_url": source_input},
            )
        handle = _handle_of(st)
    else:
        own = str(owner or "").strip().lower()
        if not own:
            raise PolicyViolationError(
                "[P1:pre_ingest] Arquivo local sem dono declarado. Informe se é gameplay próprio "
                "ou de qual streamer cadastrado é o vídeo.",
                code="source_owner_required",
                details={"stage": "pre_ingest", "source_input": source_input},
            )
        if own == OWN_GAMEPLAY_OWNER:
            _ensure_own_gameplay_source(db)
            handle = OWN_GAMEPLAY_HANDLE
        else:
            st = _match_by_owner(own, registry_path)
            if st is None:
                raise PolicyViolationError(
                    f"[P1:pre_ingest] Dono declarado '{owner}' não é um streamer cadastrado.",
                    code="source_unknown",
                    details={"stage": "pre_ingest", "owner": owner},
                )
            handle = _handle_of(st)

    res = assert_can_ingest(db, channel_handle=handle)
    src = res["source"]
    return {
        "allowed": True,
        "stage": "pre_ingest",
        "source_id": src["id"],
        "source_name": src.get("name"),
        "channel_handle": src.get("channel_handle"),
        "permission_status": res["permission_status"],
        "permission_basis": src.get("permission_basis") or "explicita",
        "owner": owner,
    }
