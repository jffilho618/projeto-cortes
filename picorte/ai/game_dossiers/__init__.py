"""Dossiês culturais por jogo (Épico 3.5)."""
from picorte.ai.game_dossiers.loader import (
    DEFAULT_DOSSIERS_DIR,
    detect_game_slug,
    list_dossiers,
    load_dossier,
    load_dossier_for_source,
)

__all__ = [
    "DEFAULT_DOSSIERS_DIR",
    "detect_game_slug",
    "list_dossiers",
    "load_dossier",
    "load_dossier_for_source",
]
