"""Segmentação de Atividade em Lives Longas (Épico 3.5 — Story 3.5.4).

Separa blocos em 'just_chatting', 'gameplay', 'menu_pausa' ou 'cutscene' e
devolve multiplicadores de peso por arquétipo adequados a cada momento da live.
"""
from __future__ import annotations

import re
from typing import Any

ACTIVITY_WEIGHTS: dict[str, dict[str, float]] = {
    "just_chatting": {
        "serio_realtalk": 1.35,
        "polemica_hottake": 1.30,
        "chat_trolagem": 1.25,
        "callback_oculto": 1.05,
        "clutch_fail": 0.50,
        "mico_constrangimento": 1.25,
    },
    "gameplay": {
        "clutch_fail": 1.25,
        "caos_coop": 1.25,
        "rage_tilt": 1.20,
        "descoberta_detalhe": 1.25,
        "callback_oculto": 1.25,
        "susto_tensao": 1.25,
        "deadpan_karma": 1.20,
        "nobada_vacilo": 1.25,
        "mico_constrangimento": 1.10,
    },
    "menu_pausa": {
        "serio_realtalk": 1.20,
        "polemica_hottake": 1.15,
        "chat_trolagem": 1.15,
        "clutch_fail": 0.40,
        "mico_constrangimento": 1.10,
    },
    "cutscene": {
        "callback_oculto": 1.30,
        "descoberta_detalhe": 1.25,
        "deadpan_karma": 1.20,
        "susto_tensao": 1.15,
    },
}

_MENU_RE = re.compile(r"\b(?:menu|configura[cç][oõ]es|pausar|pausa|ajuste|gr[aá]ficos|sensibilidade)\b", re.IGNORECASE)
_CHAT_RE = re.compile(r"\b(?:papo reto|conversar com voc[eê]s|antes de abrir o jogo|chat|live de hoje|desabafo)\b", re.IGNORECASE)


def segment_vod_activity(
    sentences: list[dict[str, Any]],
    *,
    visual_motion: dict[int, float] | None = None,
    facecam_ratio: dict[int, float] | None = None,
    block_sec: float = 60.0,
) -> list[dict[str, Any]]:
    """Classifica blocos de block_sec segundos do VOD por atividade dominante."""
    if not sentences:
        return []
    max_end = max(float(s.get("end") or 0.0) for s in sentences)
    n_blocks = max(1, int((max_end + block_sec - 1e-6) // block_sec))
    motion_map = visual_motion or {}
    face_map = facecam_ratio or {}

    blocks: list[dict[str, Any]] = []
    for b_idx in range(n_blocks):
        bs = b_idx * float(block_sec)
        be = (b_idx + 1) * float(block_sec)
        b_sents = [
            s for s in sentences
            if float(s.get("end") or 0.0) > bs and float(s.get("start") or 0.0) < be
        ]
        b_text = " ".join(str(s.get("text") or "") for s in b_sents).strip()
        motion = float(motion_map.get(b_idx, 0.45))
        fc_ratio = float(face_map.get(b_idx, 0.15))

        if _MENU_RE.search(b_text) and motion < 0.25:
            activity = "menu_pausa"
        elif fc_ratio >= 0.45 or (_CHAT_RE.search(b_text) and motion < 0.25):
            activity = "just_chatting"
        elif motion < 0.15 and len(b_text.split()) < 12:
            activity = "cutscene"
        else:
            activity = "gameplay"

        blocks.append({
            "block_index": b_idx,
            "start": round(bs, 2),
            "end": round(min(max_end, be), 2),
            "activity": activity,
            "archetype_weights": dict(ACTIVITY_WEIGHTS[activity]),
        })
    return blocks
