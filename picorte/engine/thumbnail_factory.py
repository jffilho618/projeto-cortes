"""Fábrica Automática de Thumbnail 1280x720 (Story 3.5, skill youtube-thumbnail-design & DESIGN.md)."""
from __future__ import annotations

import math
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from picorte.config import resolve_cli_binary, resolve_vision_preset
from picorte.engine.reaction_layout import find_reactor_face
from picorte.engine.vram_runner import VRAMRunner

THUMB_W = 1280
THUMB_H = 720
MAX_THUMB_BYTES = 2 * 1024 * 1024  # 2 MB


def _expand_facecam(
    detected: tuple[int, int, int, int], frame_w: int, frame_h: int, frame: np.ndarray
) -> tuple[int, int, int, int]:
    """Reutiliza expand_facecam_box de render_clips (compatível com execução via raiz ou pacote)."""
    try:
        from picorte.engine.render_clips import expand_facecam_box
    except ImportError:
        from render_clips import expand_facecam_box
    return expand_facecam_box(detected, frame_w, frame_h, frame=frame)


def _default_cutout_runner_factory() -> Callable[[np.ndarray, str], np.ndarray]:
    def _run(img: np.ndarray, model_name: str) -> np.ndarray:
        try:
            from rembg import new_session, remove  # type: ignore

            rembg_name = "birefnet-general" if "birefnet" in model_name.lower() else "u2netp"
            session = new_session(rembg_name)
            rgba = remove(img, session=session, only_mask=True)
            mask = np.asarray(rgba, dtype=np.uint8)
            if mask.ndim == 3:
                mask = mask[:, :, 0]
            return mask
        except Exception:
            # Sem rembg: retorna máscara vazia (nunca aplica threshold Otsu sobre folhagem/HUD).
            return np.zeros(img.shape[:2], dtype=np.uint8)

    return _run


def _trim_hook_words(title_text: str, max_words: int = 6) -> list[str]:
    words = [w.strip() for w in str(title_text or "DESTAQUE").split() if w.strip()]
    return [w.upper() for w in words[:max_words]]


def _extract_frame(frame_or_video: np.ndarray | str | Path, timestamp_s: float = 0.5) -> np.ndarray:
    if isinstance(frame_or_video, (str, Path)):
        cap = cv2.VideoCapture(str(frame_or_video))
        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, float(timestamp_s)) * 1000.0)
            ok, frame = cap.read()
            if ok and frame is not None:
                return frame
        finally:
            cap.release()
        return np.zeros((THUMB_H, THUMB_W, 3), dtype=np.uint8)
    return np.asarray(frame_or_video, dtype=np.uint8)


class ThumbnailUnsafeError(RuntimeError):
    """Selo Verde (P1): nenhum frame candidato é seguro para virar thumbnail (gore/nudez)."""


def _frame_is_safe(fr: np.ndarray, exclude_box=None) -> bool:
    from picorte.risk_shield.green_seal_15s import score_frame_visual_safety

    return bool(score_frame_visual_safety(fr, exclude_box=exclude_box)["safe"])


def _select_best_thumbnail_frame(
    frame_or_video: np.ndarray | str | Path,
    *,
    timestamp_s: float = 0.5,
    clip_start_s: float | None = None,
    clip_end_s: float | None = None,
    facecam_box: tuple[int, int, int, int] | None = None,
) -> tuple[np.ndarray, tuple[int, int, int, int] | None]:
    """Escolhe o frame mais nítido e com rosto visível dentro do clipe (evita 1 frame isolado de cabeça baixa)."""
    if not isinstance(frame_or_video, (str, Path)):
        arr = np.asarray(frame_or_video, dtype=np.uint8)
        if not _frame_is_safe(arr, facecam_box):
            raise ThumbnailUnsafeError("Frame da thumbnail reprovado no Selo Verde (gore/nudez).")
        return arr, facecam_box

    if clip_start_s is not None and clip_end_s is not None and clip_end_s > clip_start_s + 0.5:
        dur = float(clip_end_s) - float(clip_start_s)
        sample_ts = [float(clip_start_s) + dur * frac for frac in (0.18, 0.34, 0.50, 0.66, 0.82)]
    else:
        t0 = max(0.0, float(timestamp_s))
        sample_ts = sorted({max(0.0, t0 - 1.5), t0, t0 + 1.5})

    cap = cv2.VideoCapture(str(frame_or_video))
    frames: list[np.ndarray] = []
    try:
        for ts in sample_ts:
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000.0)
            ok, fr = cap.read()
            if ok and fr is not None and fr.size > 0:
                frames.append(fr)
    finally:
        cap.release()

    if not frames:
        single = _extract_frame(frame_or_video, timestamp_s=timestamp_s)
        if not _frame_is_safe(single, facecam_box):
            raise ThumbnailUnsafeError("Frame da thumbnail reprovado no Selo Verde (gore/nudez).")
        return single, facecam_box

    return _rank_thumbnail_frames(frames, facecam_box=facecam_box)


def _rank_thumbnail_frames(
    frames: list[np.ndarray], *, facecam_box: tuple[int, int, int, int] | None = None
) -> tuple[np.ndarray, tuple[int, int, int, int] | None]:
    """Ranqueia candidatos; frame reprovado no Selo Verde é DESCARTADO (nenhum bônus compensa gore/nudez)."""
    best_frame: np.ndarray | None = None
    best_score = float("-inf")
    resolved_box = facecam_box

    for fr in frames:
        sh, sw = fr.shape[:2]
        detected = find_reactor_face(fr)
        has_corner = detected is not None and _is_corner_facecam(detected, sw, sh)
        if has_corner and resolved_box is None and detected is not None:
            resolved_box = _expand_facecam(detected, sw, sh, frame=fr)

        roi = fr
        box_for_sharp = resolved_box or (detected if has_corner else None)
        if box_for_sharp is not None:
            bx, by, bw, bh = [int(v) for v in box_for_sharp]
            crop = fr[max(0, by) : min(sh, by + bh), max(0, bx) : min(sw, bx + bw)]
            if crop.size > 0:
                roi = crop
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        luma = float(gray.mean())

        # Mede riqueza visual da área central do gameplay (penaliza menus borrados, telas de load ou céu liso)
        gx0, gx1 = int(sw * 0.18), int(sw * 0.72)
        gy0, gy1 = int(sh * 0.14), int(sh * 0.86)
        game_roi = fr[gy0:gy1, gx0:gx1] if (gx1 > gx0 and gy1 > gy0) else fr
        game_gray = cv2.cvtColor(game_roi, cv2.COLOR_BGR2GRAY)
        game_sharp = float(cv2.Laplacian(game_gray, cv2.CV_64F).var())
        game_std = float(game_gray.std())
        game_luma = float(game_gray.mean())
        low_detail_penalty = -450.0 if (game_sharp < 18.0 or game_std < 22.0 or game_luma < 14.0) else 0.0

        # Selo Verde Visual na Thumbnail: frame com sangue/gore ou nudez nunca é candidato.
        if not _frame_is_safe(fr, resolved_box):
            continue

        # Penaliza frames quase pretos/transições/NSFW e bonifica forte quem tem rosto visível + gameplay nítido
        score = (
            (1000.0 if has_corner else 0.0)
            + min(sharpness, 300.0)
            + min(game_sharp * 1.4, 350.0)
            + min(game_std * 2.0, 120.0)
            + low_detail_penalty
            + (40.0 if 35.0 <= luma <= 215.0 else -60.0)
        )
        if score > best_score:
            best_score = score
            best_frame = fr

    if best_frame is None:
        raise ThumbnailUnsafeError("Todos os frames candidatos da thumbnail reprovaram no Selo Verde.")
    return best_frame, resolved_box


def _hex_to_bgr(hex_color: str | None, fallback: tuple[int, int, int] = (46, 29, 225)) -> tuple[int, int, int]:
    raw = str(hex_color or "").strip().lstrip("#")
    if len(raw) == 6:
        try:
            r = int(raw[0:2], 16)
            g = int(raw[2:4], 16)
            b = int(raw[4:6], 16)
            return (b, g, r)
        except ValueError:
            pass
    return fallback


def _draw_author_pill(
    canvas: np.ndarray,
    *,
    center_x: int,
    center_y: int,
    streamer_name: str,
    accent_hex: str | None = "#E11D2E",
) -> None:
    """Desenha selo estilizado Bomba Clips (fundo accent + borda escura + detalhe amarelo) atrás do nome do autor."""
    name = str(streamer_name or "").strip().upper()
    if not name:
        return
    h, w = canvas.shape[:2]
    pill_h = 68
    pill_w = max(250, min(int(w * 0.72), 96 + len(name) * 32))
    x0 = max(20, center_x - pill_w // 2)
    y0 = max(20, center_y - pill_h // 2)
    x1 = min(w - 20, x0 + pill_w)
    y1 = min(h - 20, y0 + pill_h)
    pw, ph = x1 - x0, y1 - y0
    if pw < 80 or ph < 30:
        return

    radius = 16
    border = 4
    inner_mask = _rounded_rect_mask(pw, ph, radius)
    outer_w, outer_h = pw + border * 2, ph + border * 2
    outer_mask = _rounded_rect_mask(outer_w, outer_h, radius + border)

    # Sombra projetada atrás da tag
    sh_pad = 16
    sh_c = np.zeros((outer_h + sh_pad * 2, outer_w + sh_pad * 2), dtype=np.float32)
    sh_c[sh_pad : sh_pad + outer_h, sh_pad : sh_pad + outer_w] = outer_mask
    sh_blur = cv2.GaussianBlur(sh_c, (23, 23), 0) * 0.72
    sx0, sy0 = x0 - border - sh_pad, y0 - border - sh_pad + 6
    xs, ys = max(0, sx0), max(0, sy0)
    xe, ye = min(w, sx0 + outer_w + sh_pad * 2), min(h, sy0 + outer_h + sh_pad * 2)
    sc = sh_blur[ys - sy0 : ye - sy0, xs - sx0 : xe - sx0][:, :, None]
    canvas[ys:ye, xs:xe] = np.clip(canvas[ys:ye, xs:xe].astype(np.float32) * (1.0 - sc), 0, 255).astype(np.uint8)

    # Borda dourada/amarela Bomba Clips (#FFD400 em BGR: 0, 212, 255)
    ox0, oy0 = max(0, x0 - border), max(0, y0 - border)
    ox1, oy1 = min(w, ox0 + outer_w), min(h, oy0 + outer_h)
    om = outer_mask[: oy1 - oy0, : ox1 - ox0, None]
    gold = np.array([0.0, 212.0, 255.0], dtype=np.float32).reshape((1, 1, 3))
    roi_o = canvas[oy0:oy1, ox0:ox1].astype(np.float32)
    canvas[oy0:oy1, ox0:ox1] = np.clip(gold * om + roi_o * (1.0 - om), 0, 255).astype(np.uint8)

    # Corpo preenchido na cor do streamer / vermelho Bomba Clips com leve gradiente vertical
    bgr = np.array(_hex_to_bgr(accent_hex), dtype=np.float32).reshape((1, 1, 3))
    grad = np.linspace(1.06, 0.78, ph, dtype=np.float32)[:, None, None]
    fill = np.clip(bgr * grad, 0, 255)
    im = inner_mask[:, :, None]
    roi_i = canvas[y0:y1, x0:x1].astype(np.float32)
    canvas[y0:y1, x0:x1] = np.clip(fill * im + roi_i * (1.0 - im), 0, 255).astype(np.uint8)


def _resize_to_thumb(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    if (w, h) == (THUMB_W, THUMB_H):
        return frame.copy()
    interp = cv2.INTER_AREA if (w >= THUMB_W and h >= THUMB_H) else cv2.INTER_LANCZOS4
    return cv2.resize(frame, (THUMB_W, THUMB_H), interpolation=interp)


def _grade_gameplay_frame(bgr: np.ndarray, *, sat_boost: float = 1.14, contrast: float = 1.08, beta: float = 3.0) -> np.ndarray:
    """Realça contraste e saturação sem estourar altas luzes."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_boost, 0.0, 255.0)
    vibrant = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return cv2.convertScaleAbs(vibrant, alpha=contrast, beta=beta)


def _apply_clean_cutout_depth(canvas: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Aplica separação suave de profundidade somente se a máscara for coesa (sem ruído fragmentado)."""
    if mask is None or mask.size == 0:
        return canvas
    mask_u8 = cv2.resize(np.asarray(mask, dtype=np.uint8), (THUMB_W, THUMB_H))
    binary = (mask_u8 > 127).astype(np.uint8)
    frac = float(binary.mean())
    if frac < 0.02 or frac > 0.65:
        return canvas

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    big_components = sum(1 for idx in range(1, num_labels) if int(stats[idx, cv2.CC_STAT_AREA]) >= 300)
    if big_components == 0 or big_components > 4:
        return canvas

    bg = cv2.GaussianBlur(canvas, (15, 15), 0)
    bg = cv2.convertScaleAbs(bg, alpha=0.72, beta=0)
    alpha = cv2.GaussianBlur(binary.astype(np.float32), (11, 11), 0)[:, :, None]
    out = canvas.astype(np.float32) * alpha + bg.astype(np.float32) * (1.0 - alpha)
    return np.clip(out, 0, 255).astype(np.uint8)


def _apply_cinematic_scrims(canvas: np.ndarray) -> np.ndarray:
    """Escurece gradualmente a metade esquerda (área do texto) e suaviza/escurece o rodapé (legendas nativas)."""
    work = canvas.astype(np.float32)

    # 1. Suavização + escurecimento do rodapé (y ~ 525..720) para diluir legendas nativas do jogo
    blurred_bot = cv2.GaussianBlur(canvas, (45, 45), 0).astype(np.float32)
    y_coords = np.arange(THUMB_H, dtype=np.float32)[:, None, None]
    bot_t = np.clip((y_coords - 525.0) / 105.0, 0.0, 1.0)
    bot_t = bot_t * bot_t * (3.0 - 2.0 * bot_t)  # smoothstep
    work = work * (1.0 - 0.94 * bot_t) + blurred_bot * (0.94 * bot_t)
    work = work * (1.0 - 0.78 * bot_t)

    # 2. Gradiente escuro suave à esquerda (0..700px) para contraste do título sem caixa dura
    x_coords = np.arange(THUMB_W, dtype=np.float32)[None, :, None]
    left_t = np.clip(1.0 - (x_coords - 120.0) / 580.0, 0.0, 1.0)
    left_t = left_t * left_t * (3.0 - 2.0 * left_t)
    # Mais forte no quadrante superior/médio-esquerdo onde o texto vive
    vert_focus = np.clip(1.0 - (y_coords - 420.0) / 300.0, 0.45, 1.0)
    left_darken = 0.68 * left_t * vert_focus
    work = work * (1.0 - left_darken) + np.array([8.0, 10.0, 14.0], dtype=np.float32) * left_darken

    # 3. Vinheta sutil nas bordas externas superiores
    top_t = np.clip(1.0 - y_coords / 90.0, 0.0, 1.0) * 0.18
    work = work * (1.0 - top_t)

    return np.clip(work, 0, 255).astype(np.uint8)


def _is_corner_facecam(box: tuple[int, int, int, int], src_w: int, src_h: int) -> bool:
    fx, fy, fw, fh = [float(v) for v in box]
    if fw <= 8 or fh <= 8:
        return False
    cx = (fx + fw / 2.0) / max(1.0, float(src_w))
    cy = (fy + fh / 2.0) / max(1.0, float(src_h))
    rel_w = fw / max(1.0, float(src_w))
    return min(cx, 1.0 - cx) <= 0.28 and min(cy, 1.0 - cy) <= 0.35 and rel_w <= 0.18


def _rounded_rect_mask(w: int, h: int, radius: int) -> np.ndarray:
    """Máscara anti-aliased de retângulo arredondado [0..1] float32."""
    scale = 2
    sw, sh, sr = w * scale, h * scale, radius * scale
    mask = np.zeros((sh, sw), dtype=np.uint8)
    cv2.rectangle(mask, (sr, 0), (sw - sr, sh), 255, -1)
    cv2.rectangle(mask, (0, sr), (sw, sh - sr), 255, -1)
    for cx, cy in ((sr, sr), (sw - sr, sr), (sr, sh - sr), (sw - sr, sh - sr)):
        cv2.circle(mask, (cx, cy), sr, 255, -1)
    down = cv2.resize(mask, (w, h), interpolation=cv2.INTER_AREA)
    return down.astype(np.float32) / 255.0


def _composite_corner_facecam(canvas: np.ndarray, raw_frame: np.ndarray) -> tuple[np.ndarray, bool]:
    """Extrai e amplia facecam de canto em card arredondado com sombra e borda em destaque."""
    src_h, src_w = raw_frame.shape[:2]
    face = find_reactor_face(raw_frame)
    if face is None or not _is_corner_facecam(face, src_w, src_h):
        return canvas, False

    bx, by, bw, bh = _expand_facecam(face, src_w, src_h, frame=raw_frame)
    if bw < 24 or bh < 24:
        return canvas, False

    work = canvas.copy()

    # Suaviza e escurece de forma emplumada (sem borda retangular dura) a área original da mini-facecam
    sx1 = max(0, int(math.floor(bx * THUMB_W / float(src_w))) - 18)
    sy1 = max(0, int(math.floor(by * THUMB_H / float(src_h))) - 18)
    sx2 = min(THUMB_W, int(math.ceil((bx + bw) * THUMB_W / float(src_w))) + 18)
    sy2 = min(THUMB_H, int(math.ceil((by + bh) * THUMB_H / float(src_h))) + 18)
    if sx2 > sx1 and sy2 > sy1:
        supp_mask = np.zeros((THUMB_H, THUMB_W), dtype=np.float32)
        supp_mask[sy1:sy2, sx1:sx2] = 1.0
        supp_mask = cv2.GaussianBlur(supp_mask, (45, 45), 0)[:, :, None]
        blurred_bg = cv2.GaussianBlur(work, (41, 41), 0).astype(np.float32) * 0.48
        work = np.clip(work.astype(np.float32) * (1.0 - supp_mask) + blurred_bg * supp_mask, 0, 255).astype(np.uint8)

    # Recorte da facecam em alta resolução (remove filete de overlay na borda superior da tela se colada ao topo)
    top_trim_margin = min(14, max(0, int(round(bh * 0.045)))) if by <= 4 else 0
    face_crop = raw_frame[by + top_trim_margin : by + bh, bx : bx + bw]
    if face_crop.size == 0:
        face_crop = raw_frame[by : by + bh, bx : bx + bw]
    face_crop = _grade_gameplay_frame(face_crop, sat_boost=1.10, contrast=1.08, beta=4.0)
    blur_f = cv2.GaussianBlur(face_crop, (0, 0), 1.4)
    face_crop = cv2.addWeighted(face_crop, 1.24, blur_f, -0.24, 0)

    # Card proporcional (~31% da largura), ancorado no topo-direito (acima do timecode y>560)
    card_w = 396
    raw_ratio = bh / float(bw)
    card_h = int(round(card_w * raw_ratio))
    if card_h > 336:
        # Mantém proporção natural evitando esticar rostos em caixas altas
        card_h = 336
        target_crop_h = int(round(bw * (card_h / float(card_w))))
        if target_crop_h < bh:
            top_trim = max(0, (bh - target_crop_h) // 3)
            face_crop = face_crop[top_trim : top_trim + target_crop_h, :]
    elif card_h < 230:
        card_h = 230
        target_crop_w = int(round(bh * (card_w / float(card_h))))
        if target_crop_w < bw:
            left_trim = max(0, (bw - target_crop_w) // 2)
            face_crop = face_crop[:, left_trim : left_trim + target_crop_w]

    card_img = cv2.resize(face_crop, (card_w, card_h), interpolation=cv2.INTER_LANCZOS4)
    card_x = THUMB_W - card_w - 28
    card_y = 28

    # Máscara arredondada + borda amarela #FFD400 (BGR: 0, 212, 255) com halo escuro externo
    radius = 22
    border_px = 4
    inner_mask = _rounded_rect_mask(card_w, card_h, radius)
    outer_w, outer_h = card_w + border_px * 2, card_h + border_px * 2
    outer_mask = _rounded_rect_mask(outer_w, outer_h, radius + border_px)

    # Sombra projetada suave atrás do card
    shadow_pad = 24
    sh_canvas = np.zeros((outer_h + shadow_pad * 2, outer_w + shadow_pad * 2), dtype=np.float32)
    sh_canvas[shadow_pad : shadow_pad + outer_h, shadow_pad : shadow_pad + outer_w] = outer_mask
    sh_blur = cv2.GaussianBlur(sh_canvas, (31, 31), 0) * 0.70

    sx0 = card_x - border_px - shadow_pad + 4
    sy0 = card_y - border_px - shadow_pad + 10
    x_start, y_start = max(0, sx0), max(0, sy0)
    x_end, y_end = min(THUMB_W, sx0 + outer_w + shadow_pad * 2), min(THUMB_H, sy0 + outer_h + shadow_pad * 2)
    sh_crop = sh_blur[y_start - sy0 : y_end - sy0, x_start - sx0 : x_end - sx0][:, :, None]
    region = work[y_start:y_end, x_start:x_end].astype(np.float32)
    work[y_start:y_end, x_start:x_end] = np.clip(region * (1.0 - sh_crop), 0, 255).astype(np.uint8)

    # Borda dourada #FFD400
    ox0, oy0 = card_x - border_px, card_y - border_px
    ox1, oy1 = ox0 + outer_w, oy0 + outer_h
    om = outer_mask[:, :, None]
    border_color = np.array([0.0, 212.0, 255.0], dtype=np.float32).reshape((1, 1, 3))
    roi_outer = work[oy0:oy1, ox0:ox1].astype(np.float32)
    work[oy0:oy1, ox0:ox1] = np.clip(border_color * om + roi_outer * (1.0 - om), 0, 255).astype(np.uint8)

    # Facecam dentro da borda
    im = inner_mask[:, :, None]
    roi_inner = work[card_y : card_y + card_h, card_x : card_x + card_w].astype(np.float32)
    work[card_y : card_y + card_h, card_x : card_x + card_w] = np.clip(
        card_img.astype(np.float32) * im + roi_inner * (1.0 - im), 0, 255
    ).astype(np.uint8)

    return work, True


def _layout_hook_lines(words: list[str]) -> list[list[str]]:
    """Quebra até 6 palavras em 1–3 linhas equilibradas para leitura instantânea a 120px."""
    if not words:
        return [["DESTAQUE"]]
    if len(words) == 1:
        return [words]
    if len(words) == 2:
        if sum(len(w) for w in words) <= 10:
            return [words]
        return [[words[0]], [words[1]]]
    if len(words) == 3:
        if len(words[0]) >= 8:
            return [[words[0]], [words[1], words[2]]]
        return [[words[0], words[1]], [words[2]]]
    if len(words) == 4:
        return [words[:2], words[2:]]
    total_chars = sum(len(w) for w in words) + len(words) - 1
    if total_chars <= 24:
        mid = math.ceil(len(words) / 2)
        return [words[:mid], words[mid:]]
    # 5–6 palavras longas: 3 linhas compactas
    return [words[:2], words[2:4], words[4:]]


def _escape_ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _build_thumbnail_ass(words: list[str], *, has_facecam: bool) -> str:
    """Constrói script ASS com tipografia de alto CTR (branco + destaque #FFD400, suporte total a UTF-8 PT-BR)."""
    lines = _layout_hook_lines(words)
    max_chars = max(len(" ".join(ln)) for ln in lines)
    max_text_width = 760 if has_facecam else 860

    if len(lines) == 1:
        base_size = 136
    elif len(lines) == 2:
        base_size = 132
    else:
        base_size = 96

    fitted_size = int(max_text_width / max(1.0, max_chars * 0.54))
    font_size = max(50, min(base_size, fitted_size))
    line_step = int(round(font_size * 1.03))
    total_h = len(lines) * line_step
    # Posiciona na banda segura esquerda (acima da linha média, longe do capítulo em y>560)
    start_y = max(68, min(195, int(round((460 - total_h) * 0.45)) + 52))
    left_x = 58
    font_name = "Arial Black" if sys.platform == "win32" else "Noto Sans"

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {THUMB_W}\n"
        f"PlayResY: {THUMB_H}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: ThumbHero,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&HC8000000,"
        "-1,0,0,0,96,100,-1,0,1,11,6,7,58,420,40,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    # Identifica a palavra de clímax (última palavra) para destacar em amarelo #FFD400 (&H0000D4FF& em BGR ASS)
    dialogues: list[str] = []
    for li, line_words in enumerate(lines):
        y_pos = start_y + li * line_step
        is_last_line = li == len(lines) - 1
        if is_last_line and len(line_words) == 1:
            rendered = f"{{\\c&H0000D4FF&}}{_escape_ass_text(line_words[0])}"
        elif is_last_line and len(line_words) >= 2:
            prefix = " ".join(_escape_ass_text(w) for w in line_words[:-1])
            climax = _escape_ass_text(line_words[-1])
            rendered = f"{{\\c&H00FFFFFF&}}{prefix} {{\\c&H0000D4FF&}}{climax}"
        else:
            rendered = f"{{\\c&H00FFFFFF&}}" + " ".join(_escape_ass_text(w) for w in line_words)
        dialogues.append(
            f"Dialogue: 0,0:00:00.00,0:00:01.00,ThumbHero,,0,0,0,,{{\\an7\\pos({left_x},{y_pos})}}{rendered}"
        )

    return header + "\n".join(dialogues) + "\n"


def _build_vertical_thumbnail_canvas(
    raw_frame: np.ndarray,
    *,
    facecam_box: tuple[int, int, int, int] | None = None,
    streamer_name: str | None = None,
    streamer_accent_hex: str | None = "#E11D2E",
) -> tuple[np.ndarray, bool, int]:
    """Monta capa vertical 1080x1920 (9:16) nativa Bomba Clips: Facecam no topo + Gameplay 100% preenchido embaixo."""
    vw, vh = 1080, 1920
    face_h = 652
    game_h = vh - face_h  # 1268
    src_h, src_w = raw_frame.shape[:2]

    box_used: tuple[int, int, int, int] | None = None
    if facecam_box is not None and len(facecam_box) == 4:
        bx, by, bw, bh = [int(v) for v in facecam_box]
        if bw >= 32 and bh >= 32:
            box_used = (max(0, bx), max(0, by), min(src_w - max(0, bx), bw), min(src_h - max(0, by), bh))

    if box_used is None:
        face = find_reactor_face(raw_frame)
        if face is not None and _is_corner_facecam(face, src_w, src_h):
            box_used = _expand_facecam(face, src_w, src_h, frame=raw_frame)

    has_facecam = box_used is not None
    canvas = np.zeros((vh, vw, 3), dtype=np.uint8)

    if has_facecam and box_used is not None:
        bx, by, bw, bh = box_used
        fc_crop = raw_frame[max(0, by) : min(src_h, by + bh), max(0, bx) : min(src_w, bx + bw)]
        if fc_crop.size > 0:
            scale = max(vw / float(fc_crop.shape[1]), face_h / float(fc_crop.shape[0]))
            rw = max(vw, int(round(fc_crop.shape[1] * scale)))
            rh = max(face_h, int(round(fc_crop.shape[0] * scale)))
            resized = cv2.resize(fc_crop, (rw, rh), interpolation=cv2.INTER_LANCZOS4)
            ox = (rw - vw) // 2
            oy = max(0, (rh - face_h) // 3)
            top_panel = _grade_gameplay_frame(
                resized[oy : oy + face_h, ox : ox + vw], sat_boost=1.08, contrast=1.06, beta=4.0
            )
            # Leve nitidez na facecam do streamer
            blur_t = cv2.GaussianBlur(top_panel, (0, 0), 1.2)
            canvas[:face_h, :] = cv2.addWeighted(top_panel, 1.18, blur_t, -0.18, 0)
        else:
            has_facecam = False

    if not has_facecam:
        # Sem facecam: gameplay 100% preenchido e centralizado de ponta a ponta
        scale = max(vw / float(src_w), vh / float(src_h))
        rw, rh = max(vw, int(round(src_w * scale))), max(vh, int(round(src_h * scale)))
        full = cv2.resize(raw_frame, (rw, rh), interpolation=cv2.INTER_LANCZOS4)
        ox, oy = (rw - vw) // 2, (rh - vh) // 2
        canvas = _grade_gameplay_frame(full[oy : oy + vh, ox : ox + vw])
    else:
        # Unanimidade: base 100% preenchida e centralizada no gameplay (evitando a webcam de canto, sem vãos borrados)
        target_ratio = vw / float(game_h)
        crop_w = min(src_w, int(round(src_h * target_ratio)))
        bx, by, bw, bh = box_used  # type: ignore[misc]
        pad_clear = max(48, int(round(bw * 0.35)))
        cx_face = (bx + bw / 2.0) / max(1.0, float(src_w))
        if cx_face < 0.40:
            gx = min(src_w - crop_w, max(0, bx + bw + pad_clear))
        elif cx_face > 0.60:
            gx = max(0, min(src_w - crop_w, bx - pad_clear - crop_w))
        else:
            gx = max(0, (src_w - crop_w) // 2)
        game_crop = raw_frame[:, gx : gx + crop_w]
        game_resized = cv2.resize(game_crop, (vw, game_h), interpolation=cv2.INTER_LANCZOS4)
        canvas[face_h:, :] = _grade_gameplay_frame(game_resized)

    # Gradiente sutil na faixa central da divisão para contraste máximo do título sem poluir rosto nem jogo
    work = canvas.astype(np.float32)
    y_coords = np.arange(vh, dtype=np.float32)[:, None, None]
    seam_y = float(face_h) if has_facecam else float(vh * 0.42)
    band_dist = np.abs(y_coords - seam_y) / 195.0
    band_dark = np.clip(1.0 - band_dist, 0.0, 1.0)
    band_dark = (band_dark * band_dark) * 0.60
    work = work * (1.0 - band_dark) + np.array([10.0, 12.0, 16.0], dtype=np.float32) * band_dark
    composed = np.clip(work, 0, 255).astype(np.uint8)

    badge_y = int(seam_y - 122) if has_facecam else int(seam_y - 138)
    clean_streamer = str(streamer_name or "").strip().upper()
    if clean_streamer:
        _draw_author_pill(
            composed,
            center_x=vw // 2,
            center_y=badge_y,
            streamer_name=clean_streamer,
            accent_hex=streamer_accent_hex,
        )

    return composed, has_facecam, badge_y


def _build_vertical_thumbnail_ass(
    words: list[str],
    *,
    seam_y: int = 652,
    streamer_name: str | None = None,
    badge_y: int | None = None,
) -> str:
    """Tipografia vertical centralizada na divisão da capa 9:16 (1080x1920) + selo do autor."""
    lines = _layout_hook_lines(words)
    font_name = "Impact" if sys.platform == "win32" else "Antonio"
    longest = max((len(" ".join(line)) for line in lines), default=8)
    font_size = 112 if longest <= 14 else (92 if longest <= 20 else 76)
    line_step = int(font_size * 1.06)
    total_h = line_step * len(lines)
    clean_streamer = str(streamer_name or "").strip().upper()
    anchor_seam = seam_y + 42 if clean_streamer else seam_y
    start_y = max(240, anchor_seam - total_h // 2 + line_step // 2)

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: ThumbVert,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&HC8000000,"
        "-1,0,0,0,96,100,-1,0,1,12,6,5,60,60,40,1\n"
        f"Style: AuthorTag,{font_name},48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,"
        "-1,0,0,0,104,100,2,0,1,4,2,5,40,40,20,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    dialogues: list[str] = []
    if clean_streamer:
        by = badge_y if badge_y is not None else max(180, seam_y - 122)
        dialogues.append(
            f"Dialogue: 1,0:00:00.00,0:00:01.00,AuthorTag,,0,0,0,,{{\\an5\\pos(540,{by})}}{_escape_ass_text(clean_streamer)}"
        )
    for li, line_words in enumerate(lines):
        y_pos = start_y + li * line_step
        is_last = li == len(lines) - 1
        if is_last and len(line_words) == 1:
            rendered = f"{{\\c&H0000D4FF&}}{_escape_ass_text(line_words[0])}"
        elif is_last and len(line_words) >= 2:
            prefix = " ".join(_escape_ass_text(w) for w in line_words[:-1])
            climax = _escape_ass_text(line_words[-1])
            rendered = f"{{\\c&H00FFFFFF&}}{prefix} {{\\c&H0000D4FF&}}{climax}"
        else:
            rendered = f"{{\\c&H00FFFFFF&}}" + " ".join(_escape_ass_text(w) for w in line_words)
        dialogues.append(
            f"Dialogue: 0,0:00:00.00,0:00:01.00,ThumbVert,,0,0,0,,{{\\an5\\pos(540,{y_pos})}}{rendered}"
        )
    return header + "\n".join(dialogues) + "\n"


def _render_title_with_ffmpeg_ass(
    canvas: np.ndarray,
    words: list[str],
    work_dir: Path,
    *,
    has_facecam: bool,
    ass_override: str | None = None,
) -> np.ndarray:
    """Queima título PT-BR via FFmpeg + libass usando cwd=work_dir e nomes relativos (AD-11)."""
    ffmpeg_bin = resolve_cli_binary("ffmpeg") or "ffmpeg"
    work_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex[:10]
    in_name = f"_picorte_thumb_{token}_in.bmp"
    ass_name = f"_picorte_thumb_{token}.ass"
    out_name = f"_picorte_thumb_{token}_out.bmp"

    in_path = work_dir / in_name
    ass_path = work_dir / ass_name
    out_path = work_dir / out_name

    try:
        ok, buf = cv2.imencode(".bmp", canvas)
        if not ok:
            raise RuntimeError("Falha ao codificar frame temporário BMP para thumbnail.")
        in_path.write_bytes(buf.tobytes())
        ass_text = ass_override if ass_override is not None else _build_thumbnail_ass(words, has_facecam=has_facecam)
        ass_path.write_text(ass_text, encoding="utf-8")

        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-i",
                in_name,
                "-vf",
                f"subtitles={ass_name}",
                "-frames:v",
                "1",
                out_name,
            ],
            cwd=str(work_dir),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        decoded = cv2.imdecode(np.frombuffer(out_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise RuntimeError("Falha ao decodificar thumbnail renderizada pelo FFmpeg.")
        return decoded
    finally:
        for tmp in (in_path, ass_path, out_path):
            try:
                tmp.unlink()
            except OSError:
                pass


def _write_encoded_image(img: np.ndarray, path: Path, ext: str, params: list[int]) -> int:
    ok, buf = cv2.imencode(ext, img, params)
    if not ok:
        raise RuntimeError(f"Falha ao codificar imagem {ext} em {path}")
    path.write_bytes(buf.tobytes())
    return path.stat().st_size


def generate_thumbnail(
    frame_or_video: np.ndarray | str | Path,
    output_path: str | Path,
    *,
    title_text: str,
    timestamp_s: float = 0.5,
    aspect: str = "16:9",
    vision_preset: str = "auto",
    vram_mib: int | None = None,
    gpu_name: str | None = None,
    facecam_box: tuple[int, int, int, int] | list[int] | None = None,
    streamer_name: str | None = None,
    streamer_accent_hex: str | None = "#E11D2E",
    clip_start_s: float | None = None,
    clip_end_s: float | None = None,
    cutout_runner: Callable[[np.ndarray, str], np.ndarray] | None = None,
    vram_runner: VRAMRunner | None = None,
) -> dict[str, Any]:
    """Gera thumbnail 1280x720 (16:9) ou capa vertical 1080x1920 (9:16) com identidade do streamer."""
    resolved = resolve_vision_preset(vision_preset, vram_mib=vram_mib, gpu_name=gpu_name)
    preset = resolved["preset"]
    cutout_model = resolved["models"]["thumbnail_cutout"]

    runner = vram_runner or VRAMRunner()
    cut_fn = cutout_runner or _default_cutout_runner_factory()
    box_tuple = (
        (int(facecam_box[0]), int(facecam_box[1]), int(facecam_box[2]), int(facecam_box[3]))
        if facecam_box is not None and len(facecam_box) == 4
        else None
    )
    raw_frame, resolved_box = _select_best_thumbnail_frame(
        frame_or_video,
        timestamp_s=timestamp_s,
        clip_start_s=clip_start_s,
        clip_end_s=clip_end_s,
        facecam_box=box_tuple,
    )
    words = _trim_hook_words(title_text, max_words=5)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    clean_streamer = str(streamer_name or "").strip().upper() or None

    if str(aspect).strip() == "9:16":
        composed, facecam_detected, badge_y = _build_vertical_thumbnail_canvas(
            raw_frame,
            facecam_box=resolved_box,
            streamer_name=clean_streamer,
            streamer_accent_hex=streamer_accent_hex,
        )
        seam_y = 652 if facecam_detected else 820
        ass_vert = _build_vertical_thumbnail_ass(
            words,
            seam_y=seam_y,
            streamer_name=clean_streamer,
            badge_y=badge_y,
        )
        composed = _render_title_with_ffmpeg_ass(
            composed, words, out.parent, has_facecam=facecam_detected, ass_override=ass_vert
        )
        out_w, out_h = 1080, 1920
    else:
        canvas_src = _resize_to_thumb(raw_frame)

        def _run_stage() -> np.ndarray:
            return cut_fn(canvas_src, cutout_model)

        mask = runner.run_stage(f"thumbnail_{preset}", _run_stage)
        graded = _grade_gameplay_frame(canvas_src)
        composed = _apply_clean_cutout_depth(graded, mask)
        composed = _apply_cinematic_scrims(composed)
        composed, facecam_detected = _composite_corner_facecam(composed, raw_frame)
        ass_wide = _build_thumbnail_ass(words, has_facecam=facecam_detected)
        if clean_streamer:
            bx = THUMB_W - 226 if facecam_detected else 210
            by = 404 if facecam_detected else 74
            _draw_author_pill(composed, center_x=bx, center_y=by, streamer_name=clean_streamer, accent_hex=streamer_accent_hex)
            font_name = "Impact" if sys.platform == "win32" else "Antonio"
            ass_wide = ass_wide.replace(
                "[Events]\n",
                f"Style: AuthorTag,{font_name},38,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,104,100,2,0,1,4,2,5,20,20,20,1\n\n[Events]\n",
            ) + f"Dialogue: 1,0:00:00.00,0:00:01.00,AuthorTag,,0,0,0,,{{\\an5\\pos({bx},{by})}}{_escape_ass_text(clean_streamer)}\n"
        composed = _render_title_with_ffmpeg_ass(
            composed, words, out.parent, has_facecam=facecam_detected, ass_override=ass_wide
        )
        out_w, out_h = THUMB_W, THUMB_H

    size_bytes = _write_encoded_image(composed, out, ".png", [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if size_bytes > MAX_THUMB_BYTES:
        jpg_out = out.with_suffix(".jpg")
        size_bytes = _write_encoded_image(composed, jpg_out, ".jpg", [cv2.IMWRITE_JPEG_QUALITY, 90])
        out = jpg_out

    return {
        "path": str(out),
        "width": out_w,
        "height": out_h,
        "preset": preset,
        "cutout_model": cutout_model,
        "size_bytes": size_bytes,
        "words": words,
        "facecam_detected": facecam_detected,
        "streamer_name": clean_streamer,
        "text_renderer": "ffmpeg_ass",
    }
