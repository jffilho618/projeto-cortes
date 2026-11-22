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

# 3.7.2 — decisão do dono (2026-11-22): "jogo protagonista". O nome `historia_70_30` ficou por compatibilidade.
LAYOUT_RATIO_MAP = {
    "historia_70_30": 640,     # rosto ≈ 33% em cima (= layout fixo de hoje) + jogo embaixo
    "reacao_split_50_50": 960, # rosto 50% + jogo 50%
    "acao_pip": 420,           # jogo em tela cheia + rosto em PiP (o render da 3.7.2 usa PIP_W)
}
PIP_W = 360
PIP_MARGIN_X = 40
PIP_Y = 240               # abaixo da área de interface da rede (área segura)
FIRST_HOLD_S = 3.5        # 1º trecho sempre História: a faixa (2 s) e o selo (3,5 s) usam a emenda de 640 px
MOTION_FLOOR = 2.0        # diferença média (0–255) abaixo disso = cena parada, sem eventos
SNIPER_MAX_SPEED = 0.15   # fração da largura da fonte por segundo
DYNAMIC_MIN_HOLD_S = 4.0  # tempo mínimo em cada arrumação no render (a função base mantém 3 s, Story 3.3)
MIN_TAIL_S = 2.0


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
    # 3.7.2: pedaço final curto (< 2 s) é só um piscar — junta com o anterior
    if len(segments) > 1 and segments[-1]["end"] - segments[-1]["start"] < MIN_TAIL_S:
        tail = segments.pop()
        segments[-1]["end"] = tail["end"]
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


# ------------------------------------------------------------------ 3.7.2: layout dinâmico ligado ao render

def measure_motion(
    frames: list[np.ndarray],
    *,
    face_box: tuple[int, int, int, int],
    source_w: int,
    source_h: int,
) -> tuple[list[float], list[float]]:
    """Movimento MEDIDO por quadro amostrado: diferença média (0–255) dentro da facecam e na região do jogo."""
    face_m: list[float] = [0.0]
    game_m: list[float] = [0.0]
    prev = None
    for idx, frame in enumerate(frames or []):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        if prev is not None and prev.shape == gray.shape:
            h, w = gray.shape[:2]
            fx, fy, fw, fh = face_box
            x0 = max(0, int(fx / source_w * w))
            y0 = max(0, int(fy / source_h * h))
            x1 = min(w, max(x0 + 1, int((fx + fw) / source_w * w)))
            y1 = min(h, max(y0 + 1, int((fy + fh) / source_h * h)))
            diff = cv2.absdiff(gray, prev).astype(np.float64)
            mask = np.zeros(gray.shape, bool)
            mask[y0:y1, x0:x1] = True
            face_m.append(float(diff[mask].mean()) if mask.any() else 0.0)
            game_m.append(float(diff[~mask].mean()) if (~mask).any() else 0.0)
        elif idx > 0:
            face_m.append(0.0)
            game_m.append(0.0)
        prev = gray
    return face_m[: len(frames or [])], game_m[: len(frames or [])]


def _relative_activity(series: list[float], floor: float) -> np.ndarray:
    """0–1: quanto cada amostra sobe acima do normal do próprio corte (mediana → p90). Cena parada → zeros."""
    arr = np.asarray(series, dtype=np.float64)
    if arr.size == 0 or float(arr.max()) < floor:
        return np.zeros_like(arr)
    med = float(np.median(arr))
    spread = max(float(np.percentile(arr, 90)) - med, floor)
    return np.clip((arr - med) / spread, 0.0, 1.0)


def layout_events_from_motion(
    face_motion: list[float],
    game_motion: list[float],
    *,
    times: list[float],
    first_hold: float = FIRST_HOLD_S,
    floor: float = MOTION_FLOOR,
) -> list[dict[str, Any]]:
    """Eventos medidos para `compute_dynamic_layout_timeline` (rosto reagindo → Reação; jogo agitado → Ação)."""
    # Suaviza em 3 amostras (≈ 3 s): só reação/ação SUSTENTADA troca o layout, não um quadro isolado
    # (render real de 2026-11-22: sem isso, 15 trocas em 78 s).
    kernel = np.ones(3) / 3.0
    face = np.convolve(_relative_activity(face_motion, floor), kernel, mode="same")
    game = np.convolve(_relative_activity(game_motion, floor), kernel, mode="same")
    return [
        {"t": float(t), "face_emotion": round(float(f), 3), "hud_action": round(float(g), 3)}
        for t, f, g in zip(times, face, game)
        if float(t) >= float(first_hold)
    ]


def sniper_x_points(
    centers: list[tuple[float, float]],
    sec_start: float,
    sec_end: float,
    *,
    src_w: int,
    crop_w: int,
    max_speed: float = SNIPER_MAX_SPEED,
) -> list[tuple[float, float]]:
    """Pontos (t local ao trecho, x em px) do Sniper Crop, com deslocamento limitado por segundo."""
    hi = max(0.0, float(src_w - crop_w))
    inside = [(float(t), float(x)) for t, x in centers or [] if sec_start <= float(t) <= sec_end]
    if not inside and centers:
        mid = (sec_start + sec_end) / 2.0
        inside = [min(((float(t), float(x)) for t, x in centers), key=lambda c: abs(c[0] - mid))]
    if not inside:
        inside = [(sec_start, 0.5)]
    vmax = float(max_speed) * float(src_w)
    pts: list[tuple[float, float]] = []
    for t, xn in sorted(inside):
        x = min(hi, max(0.0, xn * src_w - crop_w / 2.0))
        tl = max(0.0, t - sec_start)
        if pts:
            pt, px = pts[-1]
            step = vmax * max(0.0, tl - pt)
            x = min(px + step, max(px - step, x))
        pts.append((round(tl, 3), round(x, 1)))
    return pts


def _x_expr(pts: list[tuple[float, float]]) -> str:
    """Expressão FFmpeg linear por partes em t (crop avalia x a cada quadro)."""
    if len(pts) == 1:
        return f"{pts[0][1]:.1f}"
    expr = f"{pts[-1][1]:.1f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(pts, pts[1:]))):
        dt = max(1e-3, t1 - t0)
        expr = f"if(lt(t,{t1:.3f}),{x0:.1f}+({x1 - x0:.1f})*(t-{t0:.3f})/{dt:.3f},{expr})"
    return f"if(lt(t,{pts[0][0]:.3f}),{pts[0][1]:.1f},{expr})"


def build_dynamic_games_filter(
    timeline: list[dict[str, Any]],
    *,
    src_w: int,
    src_h: int,
    out_w: int,
    out_h: int,
    face_box: tuple[int, int, int, int],
    centers: list[tuple[float, float]] | None = None,
) -> str:
    """Filtro FFmpeg por trechos (trim → arrumação → concat). Termina SEM rótulo, como o filtro fixo de hoje."""
    from picorte.engine.reaction_layout import measure_reaction_inset

    n = len(timeline)
    labels = [f"[in{i}]" for i in range(n)] if n > 1 else ["[0:v]"]
    parts = [f"[0:v]split={n}{''.join(labels)};"] if n > 1 else []
    inset = measure_reaction_inset(source_w=src_w, source_h=src_h, facecam_box=face_box)
    fx, fy, fw, fh = inset["x"], inset["y"], inset["width"], inset["height"]
    for i, sec in enumerate(timeline):
        a, b = float(sec["start"]), float(sec["end"])
        base = f"{labels[i]}trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,split=2[f{i}][g{i}];"
        if sec["layout"] == "acao_pip":
            ch = (src_h // 2) * 2
            cw = min((src_w // 2) * 2, (int(round(ch * out_w / out_h)) // 2) * 2)
            xe = _x_expr(sniper_x_points(centers or [], a, b, src_w=src_w, crop_w=cw))
            parts.append(
                base
                + f"[g{i}]crop={cw}:{ch}:x='{xe}':y=0,scale={out_w}:{out_h},setsar=1[bg{i}];"
                + f"[f{i}]crop={fw}:{fh}:{fx}:{fy},scale={PIP_W}:-2,setsar=1[p{i}];"
                + f"[bg{i}][p{i}]overlay=W-w-{PIP_MARGIN_X}:{PIP_Y}[s{i}];"
            )
        else:
            rl = build_reaction_layout(source_w=src_w, source_h=src_h, out_w=out_w, out_h=out_h,
                                       facecam_box=face_box, facecam_h=LAYOUT_RATIO_MAP[sec["layout"]])
            gc, face_h, game_h = rl["gameplay_crop"], rl["facecam_h"], rl["gameplay_h"]
            parts.append(
                base
                + f"[f{i}]crop={fw}:{fh}:{fx}:{fy},scale={out_w}:{face_h}:force_original_aspect_ratio=increase,"
                + f"crop={out_w}:{face_h}[t{i}];"
                + f"[g{i}]crop={gc['w']}:{gc['h']}:{gc['x']}:{gc['y']},scale={out_w}:{game_h}"
                + f":force_original_aspect_ratio=increase,crop={out_w}:{game_h}[b{i}];"
                + f"[t{i}][b{i}]vstack=inputs=2,setsar=1[s{i}];"
            )
    parts.append("".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0")
    return "".join(parts)


def plan_dynamic_games(
    frames: list[np.ndarray],
    *,
    face_box: tuple[int, int, int, int] | None,
    source_w: int,
    source_h: int,
    out_w: int,
    out_h: int,
    times: list[float] | None = None,
    duration: float | None = None,
    vision_preset: str = "auto",
) -> dict[str, Any]:
    """Plano do layout dinâmico de um corte: {vf, timeline, trocas, motivo}. Sem dado medido → vf None."""
    if face_box is None:
        return {"vf": None, "timeline": [], "trocas": 0, "motivo": "sem facecam detectada"}
    if len(frames or []) < 2:
        return {"vf": None, "timeline": [], "trocas": 0, "motivo": "poucos quadros amostrados"}
    times = list(times) if times is not None else [float(i) for i in range(len(frames))]
    dur = float(duration) if duration else float(len(frames))
    face_m, game_m = measure_motion(frames, face_box=face_box, source_w=source_w, source_h=source_h)
    events = layout_events_from_motion(face_m, game_m, times=times)
    timeline = compute_dynamic_layout_timeline(events, dur, min_hold_s=DYNAMIC_MIN_HOLD_S)
    centers: list[tuple[float, float]] = []
    if any(s["layout"] == "acao_pip" for s in timeline):
        track = compute_sniper_crop_track(frames, source_w=source_w, source_h=source_h,
                                          vision_preset=vision_preset, exclude_box=face_box)
        centers = [(t, float(c[0])) for t, c in zip(times, track.get("centers") or [])]
    vf = build_dynamic_games_filter(timeline, src_w=source_w, src_h=source_h, out_w=out_w, out_h=out_h,
                                    face_box=face_box, centers=centers)
    return {"vf": vf, "timeline": timeline, "trocas": max(0, len(timeline) - 1), "motivo": None}
