"""Layout automático Facecam + Gameplay 9:16 (adaptado de FujiwaraChoki/supoclip reaction_layout.py)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np


def _score_corner_facecam(box: tuple[float, float, float, float], w: int, h: int, conf: float = 1.0) -> float:
    """Pontua rostos dando prioridade máxima a webcams pequenas nos 4 cantos (ignora NPCs/personagens grandes)."""
    fx, fy, fw, fh = [float(v) for v in box]
    cx = (fx + fw / 2.0) / max(1.0, float(w))
    cy = (fy + fh / 2.0) / max(1.0, float(h))
    rel_w = fw / max(1.0, float(w))
    # Distância normalizada ao canto mais próximo (0 = bem no canto, 1 = no centro)
    dx = min(cx, 1.0 - cx)
    dy = min(cy, 1.0 - cy)
    in_corner_band = (dx <= 0.24 and dy <= 0.32) and (rel_w <= 0.16)
    corner_bonus = 10.0 if in_corner_band else 0.0
    # Penaliza rostos grandes (> 14% da largura costumam ser personagens em cena/cutscene)
    size_penalty = max(0.0, (rel_w - 0.12) * 35.0)
    proximity = 3.0 * (1.0 - (dx + dy))
    return corner_bonus + proximity + float(conf) * 2.0 - size_penalty


def find_reactor_face(frame: np.ndarray) -> tuple[int, int, int, int] | None:
    """Detecta rosto da facecam nos cantos usando YuNet (priorizando webcams e evitando NPCs no centro)."""
    h, w = frame.shape[:2]
    model_path = Path(__file__).resolve().parent.parent / "models" / "yunet.onnx"
    if model_path.is_file() and hasattr(cv2, "FaceDetectorYN_create"):
        try:
            det = cv2.FaceDetectorYN_create(str(model_path), "", (w, h), 0.55, 0.3, 10)
            _, faces = det.detect(frame)
            if faces is not None and len(faces) > 0:
                best = max(
                    faces,
                    key=lambda f: _score_corner_facecam(
                        (float(f[0]), float(f[1]), float(f[2]), float(f[3])),
                        w,
                        h,
                        float(f[-1]) if len(f) > 4 else 1.0,
                    ),
                )
                return int(best[0]), int(best[1]), int(best[2]), int(best[3])
        except Exception:
            pass

    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(32, 32))
        if len(faces) > 0:
            x, y, fw, fh = max(
                faces,
                key=lambda b: _score_corner_facecam((b[0], b[1], b[2], b[3]), w, h, 1.0),
            )
            return int(x), int(y), int(fw), int(fh)
    except Exception:
        pass
    return None


def measure_reaction_inset(
    *,
    source_w: int,
    source_h: int,
    facecam_box: tuple[int, int, int, int] | None = None,
    corner: str | None = None,
) -> dict[str, Any]:
    """Determina o box e o canto da facecam (ou cria fallback proporcional 16:9 no canto superior esquerdo)."""
    if facecam_box is not None:
        x, y, w, h = [int(v) for v in facecam_box]
    else:
        w = max(160, int(source_w * 0.24))
        h = max(120, int(source_h * 0.28))
        x = int(source_w * 0.02)
        y = int(source_h * 0.03)

    cx = x + w / 2.0
    cy = y + h / 2.0
    if corner is None:
        vert = "top" if cy < source_h / 2.0 else "bottom"
        horiz = "left" if cx < source_w / 2.0 else "right"
        corner = f"{vert}_{horiz}"

    return {
        "x": max(0, x),
        "y": max(0, y),
        "width": max(16, min(source_w - max(0, x), w)),
        "height": max(16, min(source_h - max(0, y), h)),
        "corner": corner,
    }


def build_reaction_layout(
    *,
    source_w: int,
    source_h: int,
    out_w: int = 1080,
    out_h: int = 1920,
    facecam_box: tuple[int, int, int, int] | None = None,
    facecam_h: int = 640,
    focus_x_norm: float = 0.5,
    focus_y_norm: float = 0.5,
) -> dict[str, Any]:
    """Gera especificacao e filter_complex FFmpeg para 9:16 split Facecam (topo) + Gameplay (base)."""
    inset = measure_reaction_inset(source_w=source_w, source_h=source_h, facecam_box=facecam_box)
    face_h = (max(240, min(out_h - 400, int(facecam_h))) // 2) * 2
    game_h = ((out_h - face_h) // 2) * 2

    # Janela de Sniper Crop proporcional no gameplay
    target_ratio = out_w / float(game_h)
    crop_h = (source_h // 2) * 2
    crop_w = (min(source_w, int(round(crop_h * target_ratio))) // 2) * 2
    if crop_w < 16:
        crop_w = (source_w // 2) * 2
    max_cx = max(0, source_w - crop_w)
    max_cy = max(0, source_h - crop_h)
    gx = int(round(max(0.0, min(1.0, focus_x_norm)) * max_cx))
    gy = int(round(max(0.0, min(1.0, focus_y_norm)) * max_cy))

    fx, fy, fw, fh = inset["x"], inset["y"], inset["width"], inset["height"]
    filter_chain = (
        f"[0:v]split=2[vface][vgame];"
        f"[vface]crop={fw}:{fh}:{fx}:{fy},scale={out_w}:{face_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{face_h}[top];"
        f"[vgame]crop={crop_w}:{crop_h}:{gx}:{gy},scale={out_w}:{game_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{game_h}[bot];"
        f"[top][bot]vstack=inputs=2"
    )
    filter_complex = filter_chain + "[v]"

    return {
        "out_w": out_w,
        "out_h": out_h,
        "facecam_h": face_h,
        "gameplay_h": game_h,
        "inset": inset,
        "gameplay_crop": {"w": crop_w, "h": crop_h, "x": gx, "y": gy},
        "filter_chain": filter_chain,
        "filter_complex": filter_complex,
    }
