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


# ---- Ligação ao pipeline (etapa 1b, 2026-11-20): opcional, Claude Sonnet, uma chamada por VOD ----
KEYFRAMES_MODEL = "sonnet"  # Haiku alucinou no teste real; Sonnet descreveu fielmente
KEYFRAMES_TIMEOUT = 300
_UNCERTAIN = {"", "incerto", "n/a", "na", "nada", "desconhecido"}


def build_claude_vision_cmd(cli: str, prompt: str, workdir: str | Path, *, model: str = KEYFRAMES_MODEL) -> list[str]:
    """`claude -p` com acesso SOMENTE de leitura à pasta dos frames."""
    return [cli, "-p", prompt, "--model", model, "--allowedTools", "Read", "--add-dir", str(workdir),
            "--output-format", "json"]


def claude_vision_runner(prompt: str, workdir: str | Path) -> tuple[str, float]:
    import json
    import subprocess

    from picorte.config import resolve_cli_binary

    cli = resolve_cli_binary("claude")
    if not cli:
        raise RuntimeError("CLI 'claude' não encontrada no PATH.")
    res = subprocess.run(build_claude_vision_cmd(cli, prompt, workdir), cwd=str(workdir), capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=KEYFRAMES_TIMEOUT, check=True)
    data = json.loads(res.stdout or "{}")
    return str(data.get("result") or ""), float(data.get("total_cost_usd") or 0.0)


def describe_keyframes_batch(
    candidates: list[dict[str, Any]],
    video_path: str | Path,
    out_dir: str | Path,
    *,
    runner: Callable[[str, Path], tuple[str, float]] | None = None,
    frame_sampler: Callable[[str | Path, float, float], list[np.ndarray]] | None = None,
    max_candidates: int = 5,
) -> dict[str, Any]:
    """Escolhe os candidatos que dependem da tela, extrai 3 frames de cada e pede ao Claude, numa chamada só,
    UMA frase do que é visível. Respostas "incerto" não viram descrição (nada de inventar)."""
    from picorte.ai.llm_router import _extract_json_array

    out = [dict(c) for c in candidates]
    chosen = select_candidates_for_keyframes(out, max_candidates=max_candidates)
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    targets: list[dict[str, Any]] = []
    for cand in chosen:
        frames = extract_selective_keyframes(video_path, cand, folder, frame_sampler=frame_sampler)
        if not frames:
            continue
        idx = len(targets)
        targets.append(cand)
        fala = str(cand.get("text") or "")[:240]
        blocks.append(f'[{idx}] fala: "{fala}" | frames: ' + " ".join(str(p) for p in frames))
    if not targets:
        return {"candidates": out, "described": 0, "cost_usd": 0.0}

    prompt = (
        "Você vai ler frames (início, meio, fim) de trechos de uma live de games. Abra cada arquivo listado. "
        "Para cada trecho, descreva em UMA frase curta em português SOMENTE o que está visível na tela. "
        'Não invente ação que não aparece nos frames; se não der para ver, responda "incerto". '
        'Responda APENAS um array JSON: [{"index": int, "visao": str}].\n\n' + "\n".join(blocks)
    )
    raw, cost = (runner or claude_vision_runner)(prompt, folder)
    described = 0
    for entry in _extract_json_array(raw) or []:
        try:
            idx = int(entry.get("index"))
        except (TypeError, ValueError):
            continue
        text = str(entry.get("visao") or "").strip()
        if 0 <= idx < len(targets) and text.lower().strip(" .") not in _UNCERTAIN:
            targets[idx]["visual_description"] = text[:240]
            described += 1
    return {"candidates": out, "described": described, "cost_usd": round(float(cost or 0.0), 4)}
