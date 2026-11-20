"""Auto-Atualizador CLI/MCP de Dossiês Culturais por Jogo (Épico 3.5 — Story 3.5.5).

Uso CLI:
    python -m picorte.ai.dossier_updater --slug gta6 --name "GTA 6" --alias "gta 6" --callback "Animação da geladeira"
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from picorte.ai.game_dossiers.loader import DEFAULT_DOSSIERS_DIR


def normalize_slug(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", (raw or "").strip().lower()).strip("_")
    if not slug:
        raise ValueError("Slug do jogo não pode ser vazio.")
    return slug


def save_dossier(
    slug: str,
    *,
    display_name: str,
    aliases: list[str],
    cultural_callbacks: list[str],
    hot_details_to_watch: list[str] | None = None,
    spoiler_watch_p1: list[str] | None = None,
    dossiers_dir: Path | None = None,
) -> Path:
    """Valida o schema canônico e grava picorte/ai/game_dossiers/<slug>.json em UTF-8."""
    safe_slug = normalize_slug(slug)
    name_clean = str(display_name or "").strip()
    if not name_clean:
        raise ValueError("display_name é obrigatório.")
    clean_aliases = [str(a).strip().lower() for a in (aliases or []) if str(a).strip()]
    if safe_slug not in clean_aliases:
        clean_aliases.insert(0, safe_slug)
    clean_callbacks = [str(c).strip() for c in (cultural_callbacks or []) if str(c).strip()]
    clean_details = [str(d).strip() for d in (hot_details_to_watch or []) if str(d).strip()]
    clean_spoilers = [str(s).strip() for s in (spoiler_watch_p1 or []) if str(s).strip()]

    target_dir = Path(dossiers_dir) if dossiers_dir is not None else DEFAULT_DOSSIERS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / f"{safe_slug}.json"

    payload: dict[str, Any] = {
        "slug": safe_slug,
        "display_name": name_clean,
        "aliases": clean_aliases,
        "updated_at": date.today().isoformat(),
        "cultural_callbacks": clean_callbacks,
        "hot_details_to_watch": clean_details,
        "spoiler_watch_p1": clean_spoilers,
    }
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out_path)
    return out_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cria ou atualiza um dossiê cultural em picorte/ai/game_dossiers/.")
    ap.add_argument("--slug", required=True, help="Identificador do jogo (ex.: gta6, elden_ring)")
    ap.add_argument("--name", required=True, help="Nome exibido do jogo")
    ap.add_argument("--alias", action="append", default=[], help="Alias para detecção no título (repetível)")
    ap.add_argument("--callback", action="append", default=[], help="Callback/meme cultural (repetível)")
    ap.add_argument("--detail", action="append", default=[], help="Detalhe quente para observar (repetível)")
    ap.add_argument("--spoiler", action="append", default=[], help="Alerta de spoiler P1 (repetível)")
    ap.add_argument("--dir", default=None, help="Diretório alternativo de dossiês")
    args = ap.parse_args(argv)
    out = save_dossier(
        args.slug,
        display_name=args.name,
        aliases=args.alias,
        cultural_callbacks=args.callback,
        hot_details_to_watch=args.detail,
        spoiler_watch_p1=args.spoiler,
        dossiers_dir=Path(args.dir) if args.dir else None,
    )
    print(f"Dossiê salvo em: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
