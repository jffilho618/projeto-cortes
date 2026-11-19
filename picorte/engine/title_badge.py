from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _torn_profile(length: int, amplitude: float, rng: np.random.Generator, step_px: int = 24) -> np.ndarray:
    """Build a smooth organic torn-paper edge profile without harsh sawtooth noise."""
    knots = max(5, length // max(8, step_px) + 2)
    coarse = rng.uniform(-amplitude, amplitude, size=knots)
    x_coarse = np.linspace(0.0, float(length - 1), knots)
    x_fine = np.arange(length, dtype=np.float32)
    base = np.interp(x_fine, x_coarse, coarse)
    # Add gentle secondary paper fiber ripple and smooth cleanly
    ripple_knots = max(8, length // max(5, step_px // 3) + 2)
    ripple = np.interp(
        x_fine,
        np.linspace(0.0, float(length - 1), ripple_knots),
        rng.uniform(-amplitude * 0.28, amplitude * 0.28, size=ripple_knots),
    )
    combined = (base + ripple).astype(np.float32)
    kernel = np.array([0.15, 0.2, 0.3, 0.2, 0.15], dtype=np.float32)
    return np.convolve(combined, kernel, mode="same").astype(np.float32)


def _build_torn_polygon(
    width: int,
    height: int,
    pad_x: int,
    pad_top: int,
    pad_bottom: int,
    amp_y: float,
    amp_x: float,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x0, x1 = pad_x, max(pad_x + 4, width - pad_x - 1)
    y0, y1 = pad_top, max(pad_top + 4, height - pad_bottom - 1)
    w_span = x1 - x0 + 1
    h_span = y1 - y0 + 1

    step_h = max(16, width // 26)
    step_v = max(12, height // 8)
    top_off = _torn_profile(w_span, amp_y, rng, step_px=step_h)
    bot_off = _torn_profile(w_span, amp_y, rng, step_px=step_h)
    right_off = _torn_profile(h_span, amp_x, rng, step_px=step_v)
    left_off = _torn_profile(h_span, amp_x, rng, step_px=step_v)

    pts: list[tuple[int, int]] = []
    xs_top = np.arange(0, w_span, max(2, w_span // 180))
    if xs_top[-1] != w_span - 1:
        xs_top = np.append(xs_top, w_span - 1)
    for idx in xs_top:
        pts.append((int(x0 + idx), int(np.clip(round(y0 + top_off[idx]), 2, height - 3))))

    ys_side = np.arange(0, h_span, max(2, h_span // 48))
    if ys_side[-1] != h_span - 1:
        ys_side = np.append(ys_side, h_span - 1)
    for idx in ys_side:
        pts.append((int(np.clip(round(x1 + right_off[idx]), 2, width - 3)), int(y0 + idx)))

    for idx in xs_top[::-1]:
        pts.append((int(x0 + idx), int(np.clip(round(y1 + bot_off[idx]), 2, height - 3))))

    for idx in ys_side[::-1]:
        pts.append((int(np.clip(round(x0 + left_off[idx]), 2, width - 3)), int(y0 + idx)))

    return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))


def create_torn_paper_badge(
    out_path: str | Path,
    width: int = 960,
    height: int = 230,
    fill_bgr: tuple[int, int, int] = (34, 20, 228),
    paper_bgr: tuple[int, int, int] = (246, 248, 252),
    seed: int = 42,
) -> Path:
    """Render an organic RGBA torn-paper strip with subtle ripped-paper highlights and shadow."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    width = max(120, int(width))
    height = max(48, int(height))

    pad_x = max(10, round(width * 0.02))
    pad_top = max(7, round(height * 0.07))
    pad_bottom = max(10, round(height * 0.11))
    amp_y = max(2.8, height * 0.036)
    amp_x = max(3.0, width * 0.0065)

    poly_body = _build_torn_polygon(width, height, pad_x, pad_top, pad_bottom, amp_y, amp_x, seed=seed)
    # Subtle off-center white torn backing peeking naturally at edges/corners instead of a thick border
    poly_paper = _build_torn_polygon(
        width,
        height,
        max(6, pad_x - max(1, round(width * 0.0025))),
        max(4, pad_top - max(1, round(height * 0.015))),
        max(6, pad_bottom - max(1, round(height * 0.008))),
        amp_y * 1.25,
        amp_x * 1.15,
        seed=seed + 23,
    )
    poly_paper[:, 0, 0] = np.clip(poly_paper[:, 0, 0] + max(1, round(width * 0.002)), 0, width - 1)
    poly_paper[:, 0, 1] = np.clip(poly_paper[:, 0, 1] - max(1, round(height * 0.01)), 0, height - 1)

    # 1. Soft drop shadow layer
    shadow_mask = np.zeros((height, width), dtype=np.uint8)
    shadow_poly = poly_body.copy()
    shadow_poly[:, 0, 1] = np.clip(shadow_poly[:, 0, 1] + max(3, round(height * 0.042)), 0, height - 1)
    cv2.fillPoly(shadow_mask, [shadow_poly], 255)
    ksize = max(7, (round(height * 0.11) | 1))
    shadow_blur = cv2.GaussianBlur(shadow_mask, (ksize, ksize), sigmaX=max(2.5, height * 0.042))
    shadow_alpha = (shadow_blur.astype(np.float32) / 255.0) * 0.65

    # 2. Delicate torn-paper edge highlight mask
    paper_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(paper_mask, [poly_paper], 255, lineType=cv2.LINE_AA)
    paper_alpha = paper_mask.astype(np.float32) / 255.0

    # 3. Rich red paper fill with subtle vertical shading and grain
    body_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(body_mask, [poly_body], 255, lineType=cv2.LINE_AA)
    body_alpha = body_mask.astype(np.float32) / 255.0

    rng = np.random.default_rng(seed + 99)
    grad_y = np.linspace(1.07, 0.88, height, dtype=np.float32)[:, None, None]
    grain = rng.normal(0.0, 3.5, size=(height, width, 1)).astype(np.float32)
    base_color = np.array(fill_bgr, dtype=np.float32).reshape((1, 1, 3))
    body_rgb = np.clip(base_color * grad_y + grain, 0, 255)

    out_rgb = np.zeros((height, width, 3), dtype=np.float32)
    out_a = shadow_alpha.copy()

    p_rgb = np.array(paper_bgr, dtype=np.float32).reshape((1, 1, 3))
    out_rgb = p_rgb * paper_alpha[:, :, None] + out_rgb * (1.0 - paper_alpha[:, :, None])
    out_a = paper_alpha + out_a * (1.0 - paper_alpha)

    out_rgb = body_rgb * body_alpha[:, :, None] + out_rgb * (1.0 - body_alpha[:, :, None])
    out_a = body_alpha + out_a * (1.0 - body_alpha)

    bgra = np.zeros((height, width, 4), dtype=np.uint8)
    bgra[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
    bgra[:, :, 3] = np.clip(np.round(out_a * 255.0), 0, 255).astype(np.uint8)

    ok, buf = cv2.imencode(".png", bgra)
    if not ok:
        raise RuntimeError(f"Falha ao codificar badge PNG em {out}")
    out.write_bytes(buf.tobytes())
    return out
