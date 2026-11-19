"""Reenquadramento 9:16 de Games (Story 3.3): Troca Dinâmica com Histerese + Sniper Crop (EMA)."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

import cv2
import numpy as np

from picorte.config import resolve_vision_preset
from picorte.engine.hud_detector import _resolve_yolo_weights_path
from picorte.engine.reaction_layout import build_reaction_layout, find_reactor_face
from picorte.engine.vram_runner import VRAMRunner

LAYOUT_RATIO_MAP = {
    "historia_70_30": 576,     # 30% topo facecam (~576px) + 70% gameplay (~1344px)
    "reacao_split_50_50": 960, # 50% topo facecam (960px) + 50% gameplay (960px)
    "acao_pip": 420,           # Gameplay protagonista com PiP/topo compacto (420px)
}


def _desired_layout(ev: dict[str, Any]) -> str:
    face_emo = float(ev.get("face_emotion", 0.0))
    hud_act = float(ev.get("hud_action", 0.0))
    if face_emo >= 0.70 and face_emo >= hud_act:
        return "reacao_split_50_50"
    if hud_act >= 0.70:
        return "acao_pip"
    return "historia_70_30"


def compute_dynamic_layout_timeline(
    events: list[dict[str, Any]],
    duration_s: float,
    *,
    min_hold_s: float = 3.0,
    initial_layout: str = "historia_70_30",
) -> list[dict[str, Any]]:
    """Máquina de estados de layout 9:16 com histerese mínima de min_hold_s (padrão 3.0s)."""
    dur = max(0.5, float(duration_s))
    ordered = sorted(events or [], key=lambda e: float(e.get("t", 0.0)))
    current = initial_layout if initial_layout in LAYOUT_RATIO_MAP else "historia_70_30"
    seg_start = 0.0
    segments: list[dict[str, Any]] = []

    for ev in ordered:
        t = float(ev.get("t", 0.0))
        if t <= 0.0 or t >= dur:
            continue
        wanted = _desired_layout(ev)
        if wanted != current and (t - seg_start) >= float(min_hold_s) - 1e-9:
            segments.append(
                {
                    "start": round(seg_start, 3),
                    "end": round(t, 3),
                    "layout": current,
                    "facecam_h": LAYOUT_RATIO_MAP[current],
                }
            )
            current = wanted
            seg_start = t

    segments.append(
        {
            "start": round(seg_start, 3),
            "end": round(dur, 3),
            "layout": current,
            "facecam_h": LAYOUT_RATIO_MAP[current],
        }
    )
    return segments


def _normalize_exclude_box(
    exclude_box: tuple[int, int, int, int] | None,
    source_w: int,
    source_h: int,
) -> tuple[float, float, float, float] | None:
    if exclude_box is None:
        return None
    ex, ey, ew, eh = [float(v) for v in exclude_box]
    if ew <= 0 or eh <= 0:
        return None
    sw = max(1.0, float(source_w))
    sh = max(1.0, float(source_h))
    return (
        max(0.0, min(1.0, ex / sw)),
        max(0.0, min(1.0, ey / sh)),
        max(0.0, min(1.0, (ex + ew) / sw)),
        max(0.0, min(1.0, (ey + eh) / sh)),
    )


def _point_in_norm_box(rx: float, ry: float, norm_box: tuple[float, float, float, float] | None) -> bool:
    if norm_box is None:
        return False
    x0, y0, x1, y1 = norm_box
    return x0 <= rx <= x1 and y0 <= ry <= y1


@lru_cache(maxsize=1)
def _load_yolo_sniper_model():
    from ultralytics import YOLO  # type: ignore

    return YOLO(_resolve_yolo_weights_path())


def _default_yolo_tracker_factory(
    exclude_norm: tuple[float, float, float, float] | None = None,
) -> Callable[[np.ndarray, int], tuple[float, float] | None]:
    try:
        model = _load_yolo_sniper_model()

        def _track(frame: np.ndarray, _idx: int) -> tuple[float, float] | None:
            h, w = frame.shape[:2]
            preds = model.predict(frame, verbose=False)
            for r in preds:
                boxes = getattr(r, "boxes", None)
                if boxes is None or len(boxes) == 0:
                    continue
                for box_xywh in boxes.xywh.tolist():
                    rx = float(box_xywh[0]) / max(1.0, float(w))
                    ry = float(box_xywh[1]) / max(1.0, float(h))
                    if not _point_in_norm_box(rx, ry, exclude_norm):
                        return rx, ry
            return None

        return _track
    except Exception:
        return lambda _frame, _idx: None


def _optical_centroid(
    frame: np.ndarray,
    prev_gray: np.ndarray | None,
    exclude_norm: tuple[float, float, float, float] | None = None,
) -> tuple[float, float, np.ndarray]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    h, w = gray.shape[:2]
    if prev_gray is None or prev_gray.shape != gray.shape:
        energy = gray.astype(np.float64)
    else:
        diff = cv2.absdiff(gray, prev_gray).astype(np.float64)
        energy = diff + 0.25 * gray.astype(np.float64)

    if exclude_norm is not None:
        x0 = max(0, min(w, int(round(exclude_norm[0] * w))))
        y0 = max(0, min(h, int(round(exclude_norm[1] * h))))
        x1 = max(0, min(w, int(round(exclude_norm[2] * w))))
        y1 = max(0, min(h, int(round(exclude_norm[3] * h))))
        if x1 > x0 and y1 > y0:
            energy[y0:y1, x0:x1] = 0.0

    total = float(np.sum(energy))
    if total <= 1e-6:
        return 0.5, 0.5, gray
    ys, xs = np.mgrid[0:h, 0:w]
    cx = float(np.sum(xs * energy) / total) / max(1.0, float(w))
    cy = float(np.sum(ys * energy) / total) / max(1.0, float(h))
    return cx, cy, gray


def compute_sniper_crop_track(
    frames: list[np.ndarray],
    *,
    source_w: int = 1920,
    source_h: int = 1080,
    vision_preset: str = "auto",
    vram_mib: int | None = None,
    gpu_name: str | None = None,
    tracker_runner: Callable[[np.ndarray, int], tuple[float, float] | None] | None = None,
    ema_alpha: float = 0.25,
    exclude_box: tuple[int, int, int, int] | None = None,
    vram_runner: VRAMRunner | None = None,
) -> dict[str, Any]:
    """Calcula trajetória suavizada (EMA) para o Sniper Crop no gameplay respeitando o preset Low/High."""
    resolved = resolve_vision_preset(vision_preset, vram_mib=vram_mib, gpu_name=gpu_name)
    preset = resolved["preset"]
    backend_used = resolved["models"]["sniper_crop"]
    if not frames:
        return {"preset": preset, "backend_used": backend_used, "centers": [(0.5, 0.5)]}

    exclude_norm = _normalize_exclude_box(exclude_box, source_w, source_h)
    runner = vram_runner or VRAMRunner()
    use_yolo = preset == "high"
    track_fn = (tracker_runner or _default_yolo_tracker_factory(exclude_norm)) if use_yolo else None

    def _run_stage() -> dict[str, Any]:
        centers: list[tuple[float, float]] = []
        prev_gray: np.ndarray | None = None
        ema_x, ema_y = 0.5, 0.5
        alpha = max(0.05, min(1.0, float(ema_alpha)))

        for idx, frame in enumerate(frames):
            coords = track_fn(frame, idx) if track_fn is not None else None
            if coords is not None and _point_in_norm_box(float(coords[0]), float(coords[1]), exclude_norm):
                coords = None
            if coords is None:
                rx, ry, prev_gray = _optical_centroid(frame, prev_gray, exclude_norm=exclude_norm)
            else:
                rx, ry = float(coords[0]), float(coords[1])
                prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame

            rx = max(0.0, min(1.0, rx))
            ry = max(0.0, min(1.0, ry))
            if idx == 0:
                ema_x, ema_y = rx, ry
            else:
                ema_x = alpha * rx + (1.0 - alpha) * ema_x
                ema_y = alpha * ry + (1.0 - alpha) * ema_y
            centers.append((round(ema_x, 4), round(ema_y, 4)))

        return {
            "preset": preset,
            "backend_used": backend_used,
            "source_w": source_w,
            "source_h": source_h,
            "centers": centers,
        }

    return runner.run_stage(f"sniper_crop_{preset}", _run_stage)


def detect_facecam_and_build_reframe(
    sample_frame: np.ndarray | None,
    *,
    source_w: int = 1920,
    source_h: int = 1080,
    layout: str = "historia_70_30",
    focus_x_norm: float = 0.5,
    focus_y_norm: float = 0.5,
) -> dict[str, Any]:
    """Detecta facecam automaticamente e devolve filtro FFmpeg 9:16 pronto."""
    face_box = find_reactor_face(sample_frame) if sample_frame is not None else None
    facecam_h = LAYOUT_RATIO_MAP.get(layout, 640)
    return build_reaction_layout(
        source_w=source_w,
        source_h=source_h,
        out_w=1080,
        out_h=1920,
        facecam_box=face_box,
        facecam_h=facecam_h,
        focus_x_norm=focus_x_norm,
        focus_y_norm=focus_y_norm,
    )
