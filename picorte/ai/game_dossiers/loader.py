"""Carregador e detector de dossiês culturais por jogo (Story 3.5.1 / 3.5.3)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_DOSSIERS_DIR = Path(__file__).resolve().parent


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def list_dossiers(dossiers_dir: Path | None = None) -> list[dict[str, Any]]:
    base = Path(dossiers_dir) if dossiers_dir is not None else DEFAULT_DOSSIERS_DIR
    if not base.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("slug"):
            out.append(data)
    return out


def detect_game_slug(
    title: str | None,
    chapters: list[dict[str, Any]] | None = None,
    dossiers_dir: Path | None = None,
) -> str | None:
    """Identifica o slug do jogo casando título e capítulos contra os aliases dos dossiês."""
    parts = [str(title or "")]
    for ch in chapters or []:
        if isinstance(ch, dict) and ch.get("title"):
            parts.append(str(ch["title"]))
    haystack = f" {_normalize_text(' '.join(parts))} "
    if not haystack.strip():
        return None

    for dossier in list_dossiers(dossiers_dir):
        slug = str(dossier.get("slug") or "").strip().lower()
        aliases = [slug, str(dossier.get("display_name") or "")] + [
            str(a) for a in (dossier.get("aliases") or [])
        ]
        for alias in aliases:
            norm = _normalize_text(alias)
            if not norm:
                continue
            pattern = r"(?<!\w)" + re.escape(norm) + r"(?!\w)"
            if re.search(pattern, haystack):
                return slug
    return None


def load_dossier(slug: str | None, dossiers_dir: Path | None = None) -> dict[str, Any] | None:
    if not slug:
        return None
    safe_slug = re.sub(r"[^a-z0-9_-]", "", str(slug).strip().lower())
    if not safe_slug:
        return None
    base = Path(dossiers_dir) if dossiers_dir is not None else DEFAULT_DOSSIERS_DIR
    path = base / f"{safe_slug}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def load_dossier_for_source(
    source_meta: dict[str, Any] | None,
    dossiers_dir: Path | None = None,
) -> dict[str, Any] | None:
    if not isinstance(source_meta, dict):
        return None
    slug = source_meta.get("detected_game") or detect_game_slug(
        source_meta.get("title"),
        chapters=source_meta.get("chapters"),
        dossiers_dir=dossiers_dir,
    )
    return load_dossier(slug, dossiers_dir=dossiers_dir)
