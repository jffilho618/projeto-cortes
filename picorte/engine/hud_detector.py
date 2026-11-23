"""Detector de HUD e Killfeed (Story 3.2): Low (RapidOCR+optical_flow) vs High (YOLO11n+RapidOCR)."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from picorte.config import resolve_vision_preset
from picorte.engine.visual_games import UnavailableBackend, degraded_reasons, sample_video_frames
from picorte.engine.vram_runner import VRAMRunner

HUD_KEYWORDS_RE = re.compile(
    r"\b(?:KILL|DOUBLE KILL|TRIPLE KILL|ACE|CLUTCH|VICTORY|WIN|WINNER|ELIMINATED|WASTED|HEADSHOT|KNOCKED|BOOYAH"
    # PT-BR (canais brasileiros; code review 2026-11-23)
    r"|ELIMINOU|ELIMINAD[OA]S?|VIT[ÓO]RIA|VENCEDOR(?:ES)?|ABATES?|ABATID[OA]|DERRUBAD[OA]|DERRUBOU"
    r"|NOCAUTEAD[OA]|MORT[OA]|MISS[ÃA]O (?:CUMPRIDA|FALHOU|FRACASSADA))\b",
    re.IGNORECASE,
)
# Sem texto do jogo lido pelo OCR, movimento no topo + objetos do YOLO (treinado no COCO: carro, cavalo, bola)
# não dizem que houve um lance: ficam como bônus pequeno e nunca viram o sinal "hud" (code review 2026-11-23).
NON_OCR_HUD_CAP = 2.0

# Classes genéricas de COCO que representam pessoas/mobília de webcam, nunca banners de HUD.
IGNORED_YOLO_LABELS = {
    "person", "chair", "couch", "bed", "dining table", "tv", "laptop",
    "keyboard", "mouse", "cell phone", "bottle", "cup", "book", "clock",
    "potted plant", "tie", "backpack", "handbag",
}


def _box_inside_exclude(bbox: Any, exclude_box: tuple[int, int, int, int] | None) -> bool:
    if not exclude_box or not bbox or len(bbox) != 4:
        return False
    try:
        x1, y1, x2, y2 = (float(v) for v in bbox)
        ex1, ey1, ex2, ey2 = (float(v) for v in exclude_box)
    except (TypeError, ValueError):
        return False
    inter_x = max(0.0, min(x2, ex2) - max(x1, ex1))
    inter_y = max(0.0, min(y2, ey2) - max(y1, ey1))
    area = max(1e-6, (x2 - x1) * (y2 - y1))
    return (inter_x * inter_y) / area >= 0.45


def _sample_hud_frames(video_path: str | Path, start: float, end: float, fps: float = 1.0) -> list[np.ndarray]:
    return sample_video_frames(video_path, start, end, fps=fps)


def _resolve_yolo_weights_path() -> str:
    """Resolve caminho de cache do yolo11n.pt sem sujar a raiz do repositório."""
    cache_weights = Path.home() / ".cache" / "picorte" / "yolo11n.pt"
    if cache_weights.is_file():
        return str(cache_weights)
    local_weights = Path("yolo11n.pt")
    if local_weights.is_file():
        return str(local_weights)
    cache_weights.parent.mkdir(parents=True, exist_ok=True)
    return str(cache_weights)


@lru_cache(maxsize=1)
def _default_ocr_runner_factory() -> Callable[[np.ndarray, int], list[str]]:
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore

        ocr = RapidOCR()

        def _run(frame: np.ndarray, _idx: int) -> list[str]:
            result, _ = ocr(frame, use_cls=False)  # texto de HUD não vem girado; sem o classificador, −25% de tempo
            if not result:
                return []
            return [str(item[1]) for item in result if len(item) > 1]

        return _run
    except Exception as exc:
        return UnavailableBackend("RapidOCR", exc, list)


@lru_cache(maxsize=1)
def _default_yolo_runner_factory() -> Callable[[np.ndarray], list[dict[str, Any]]]:
    try:
        from ultralytics import YOLO  # type: ignore

        model = YOLO(_resolve_yolo_weights_path())

        def _run(frame: np.ndarray) -> list[dict[str, Any]]:
            preds = model.predict(frame, verbose=False)
            out: list[dict[str, Any]] = []
            for r in preds:
                names = getattr(r, "names", {})
                boxes = getattr(r, "boxes", None)
                if boxes is None:
                    continue
                xyxy = boxes.xyxy.tolist() if getattr(boxes, "xyxy", None) is not None else [None] * len(boxes.cls)
                for cls_id, conf, bbox in zip(boxes.cls.tolist(), boxes.conf.tolist(), xyxy):
                    out.append({
                        "label": str(names.get(int(cls_id), cls_id)),
                        "class_id": int(cls_id),
                        "conf": float(conf),
                        "bbox": bbox,
                    })
            return out

        return _run
    except Exception as exc:
        return UnavailableBackend("YOLO11n", exc, list)


def detect_hud_events(
    frames_or_video: list[np.ndarray] | str | Path,
    start: float,
    end: float,
    *,
    vision_preset: str = "auto",
    vram_mib: int | None = None,
    gpu_name: str | None = None,
    ocr_runner: Callable[[np.ndarray, int], list[str]] | None = None,
    yolo_runner: Callable[[np.ndarray], list[dict[str, Any]]] | None = None,
    vram_runner: VRAMRunner | None = None,
    exclude_box: tuple[int, int, int, int] | None = None,
    ocr_every_s: float = 0.0,
    ocr_min_change: float = 4.0,
) -> dict[str, Any]:
    """Detecta eventos de HUD/Killfeed usando RapidOCR+OpticalFlow (low) ou YOLO11n+RapidOCR (high)."""
    resolved = resolve_vision_preset(vision_preset, vram_mib=vram_mib, gpu_name=gpu_name)
    preset = resolved["preset"]
    backend_used = resolved["models"]["hud"]

    if isinstance(frames_or_video, (str, Path)):
        frames = _sample_hud_frames(frames_or_video, start, end, fps=1.0)
    else:
        frames = list(frames_or_video or [])

    if not frames:
        return {"preset": preset, "backend_used": backend_used, "events": [], "ocr_hits": 0, "degraded": [],
                "score": 0.0}

    runner = vram_runner or VRAMRunner()
    ocr_fn = ocr_runner or _default_ocr_runner_factory()
    use_yolo = preset == "high"
    yolo_fn = (yolo_runner or _default_yolo_runner_factory()) if use_yolo else None
    degraded = degraded_reasons(ocr_fn, yolo_fn)
    if degraded:
        backend_used = f"{backend_used} — degradado: {'; '.join(degraded)}"

    def _run_stage() -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        yolo_hits = 0
        flow_spikes = 0
        prev_gray: np.ndarray | None = None
        last_ocr_ts: float | None = None
        last_ocr_gray: np.ndarray | None = None
        dur = max(1.0, float(end) - float(start))
        dt = dur / max(1, len(frames))

        for idx, frame in enumerate(frames):
            ts = round(float(start) + idx * dt, 2)
            # Região superior (killfeed/banner costuma ficar nos primeiros 30% do topo)
            h = frame.shape[0]
            top_roi = frame[: max(1, int(h * 0.35)), :]
            gray = cv2.cvtColor(top_roi, cv2.COLOR_BGR2GRAY) if top_roi.ndim == 3 else top_roi
            if prev_gray is not None and prev_gray.shape == gray.shape:
                delta = float(np.mean(cv2.absdiff(gray, prev_gray)))
                if delta >= 18.0:
                    flow_spikes += 1
            prev_gray = gray

            # OCR custa ~0,8 s/quadro (medido na ae5f08: ~8 textos fixos de sobreposição no topo). Com
            # `ocr_every_s`, lê no máximo a cada N s e só se o topo mudou: o killfeed fica vários segundos na tela.
            run_ocr = True
            if ocr_every_s > 0:
                if last_ocr_ts is not None and ts - last_ocr_ts < float(ocr_every_s) - 1e-6:
                    run_ocr = False
                elif (last_ocr_gray is not None and last_ocr_gray.shape == gray.shape
                      and float(np.mean(cv2.absdiff(gray, last_ocr_gray))) < float(ocr_min_change)):
                    run_ocr = False
            texts = []
            if run_ocr:
                texts = ocr_fn(top_roi, idx) or []
                last_ocr_ts, last_ocr_gray = ts, gray
            for txt in texts:
                m = HUD_KEYWORDS_RE.search(txt)
                if m:
                    events.append({"t": ts, "keyword": m.group(0).upper(), "text": txt})

            if yolo_fn is not None:
                dets = yolo_fn(frame) or []
                for det in dets:
                    label = str(det.get("label", "")).strip().lower()
                    cls_id = det.get("class_id")
                    if cls_id == 0 or label in IGNORED_YOLO_LABELS:
                        continue
                    if _box_inside_exclude(det.get("bbox"), exclude_box):
                        continue
                    if float(det.get("conf", 0.0)) >= 0.45:
                        yolo_hits += 1
                        events.append({"t": ts, "keyword": str(det.get("label", "HUD")).upper(), "conf": float(det["conf"])})

        ocr_hits = sum(1 for ev in events if "text" in ev)
        non_ocr = min(2.4, flow_spikes * 0.8) + (min(3.5, yolo_hits * 0.7) if use_yolo else 0.0)
        raw = min(10.0, ocr_hits * 3.8 + min(NON_OCR_HUD_CAP, non_ocr))
        return {
            "preset": preset,
            "backend_used": backend_used,
            "events": events,
            "ocr_hits": ocr_hits,
            "degraded": degraded,
            "score": round(raw, 2),
        }

    return runner.run_stage(f"hud_{preset}", _run_stage)
