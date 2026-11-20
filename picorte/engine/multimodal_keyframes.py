"""Keyframes Multimodais Seletivos (Épico 3.5 — Story 3.5.4).

Extrai 3 frames leves (início/meio/clímax) SOMENTE para candidatos com dêiticos
visuais, arquétipos dependentes de tela ou nota limítrofe, e valida visualmente
via provedor multimodal (degradando limpo para None quando o provedor é só texto).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from picorte.engine.visual_games import sample_video_frames

VISUAL_DEPENDENT_ARCHETYPES = ("callback_oculto", "descoberta_detalhe", "deadpan_karma")
MULTIMODAL_PROVIDERS = ("gemini", "claude")


def select_candidates_for_keyframes(
    candidates: list[dict[str, Any]],
    *,
    max_candidates: int = 5,
    borderline_range: tuple[float, float] = (6.2, 8.2),
) -> list[dict[str, Any]]:
    """Seleciona até max_candidates que realmente justificam inspeção por keyframes."""
    lo, hi = borderline_range
    scored: list[tuple[int, float, dict[str, Any]]] = []
    for cand in candidates or []:
        deictic = bool(cand.get("has_visual_deictic"))
        arch = str(cand.get("archetype") or "").strip().lower()
        overall = float(cand.get("overall") or 0.0)
        priority = 0
        if deictic:
            priority += 3
        if arch in VISUAL_DEPENDENT_ARCHETYPES:
            priority += 2
        if lo <= overall <= hi and priority > 0:
            priority += 1
        elif lo <= overall <= hi and cand.get("track_origin") == "deictic_detective_callback":
            priority += 2
        if priority > 0:
            scored.append((priority, overall, cand))

    scored.sort(key=lambda item: (-item[0], -item[1]))
    return [item[2] for item in scored[: int(max_candidates)]]


def extract_selective_keyframes(
    video_path: str | Path,
    candidate: dict[str, Any],
    out_dir: str | Path,
    *,
    max_width: int = 512,
    frame_sampler: Callable[[str | Path, float, float], list[np.ndarray]] | None = None,
) -> list[Path]:
    """Extrai 3 keyframes (início, meio, clímax) em JPEG leve para o candidato."""
    start = float(candidate.get("start") or 0.0)
    end = float(candidate.get("end") or start + 10.0)
    if frame_sampler is not None:
        frames = list(frame_sampler(video_path, start, end) or [])
    else:
        frames = sample_video_frames(video_path, start, end, fps=1.0, max_width=max_width)
    if not frames:
        return []

    n = len(frames)
    if n == 1:
        idxs = [0, 0, 0]
    elif n == 2:
        idxs = [0, 0, 1]
    else:
        idxs = [
            min(n - 1, max(0, int(round((n - 1) * 0.15)))),
            n // 2,
            min(n - 1, max(0, int(round((n - 1) * 0.85)))),
        ]

    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = f"kf_{int(round(start))}_{int(round(end))}"
    saved: list[Path] = []
    for k, idx in enumerate(idxs, 1):
        img = frames[idx]
        if img.shape[1] > max_width:
            scale = max_width / float(img.shape[1])
            new_h = max(2, int(round(img.shape[0] * scale)))
            img = cv2.resize(img, (max_width, new_h), interpolation=cv2.INTER_AREA)
        out_path = target_dir / f"{stem}_{k}.jpg"
        if cv2.imwrite(str(out_path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 80]):
            saved.append(out_path)
    return saved


def describe_candidate_keyframes(
    keyframes: list[Path],
    candidate: dict[str, Any],
    *,
    provider: str = "gemini",
    vision_runner: Callable[[list[Path], str], str] | None = None,
) -> str | None:
    """Envia os 3 keyframes ao provedor multimodal; degrada limpo para None em provedor texto-apenas."""
    if not keyframes:
        return None
    if str(provider or "").strip().lower() not in MULTIMODAL_PROVIDERS:
        return None
    if vision_runner is None:
        return None

    transcript = str(candidate.get("text") or "").strip()[:300]
    prompt = (
        "Analise estes 3 frames (início, meio, fim) de uma live de games. "
        f"O streamer disse: \"{transcript}\". "
        "Em 1 frase curta em português, o que está acontecendo visualmente na tela que explica ou confirma a fala?"
    )
    try:
        resp = vision_runner(list(keyframes), prompt)
    except Exception:
        return None
    cleaned = str(resp or "").strip()
    return cleaned or None
