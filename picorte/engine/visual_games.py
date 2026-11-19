"""Visão Computacional de Games (Story 3.2): Facecam MAR, movimento de cabeça e emoção."""
from __future__ import annotations

import math
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from picorte.config import resolve_cli_binary, resolve_vision_preset
from picorte.engine.vram_runner import VRAMRunner


def compute_mouth_aspect_ratio(mouth_points: list[tuple[float, float]] | np.ndarray) -> float:
    """Calcula Mouth Aspect Ratio (MAR) a partir de 6 pontos (cantos horizontais + 2 pares verticais)."""
    pts = np.asarray(mouth_points, dtype=np.float64)
    if pts.shape[0] < 6 or pts.shape[1] < 2:
        return 0.0
    v1 = np.linalg.norm(pts[1] - pts[5])
    v2 = np.linalg.norm(pts[2] - pts[4])
    horiz = np.linalg.norm(pts[0] - pts[3])
    if horiz <= 1e-6:
        return 0.0
    return float((v1 + v2) / (2.0 * horiz))


def _probe_video_dimensions(video_path: str | Path) -> tuple[int, int]:
    """Obtém (width, height) sem realizar seeks por frame."""
    ffprobe_bin = resolve_cli_binary("ffprobe")
    if ffprobe_bin:
        try:
            res = subprocess.run(
                [
                    ffprobe_bin,
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=s=x:p=0",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if res.returncode == 0 and "x" in res.stdout:
                w_str, h_str = res.stdout.strip().splitlines()[0].split("x", 1)
                w, h = int(w_str), int(h_str)
                if w > 0 and h > 0:
                    return w, h
        except Exception:
            pass
    cap = cv2.VideoCapture(str(video_path))
    try:
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            if w > 0 and h > 0:
                return w, h
    finally:
        cap.release()
    return 1280, 720


def _scaled_dimensions(src_w: int, src_h: int, max_width: int = 640) -> tuple[int, int]:
    if src_w <= 0 or src_h <= 0:
        return 640, 360
    if src_w <= max_width:
        out_w = max(2, src_w - (src_w % 2))
        out_h = max(2, src_h - (src_h % 2))
        return out_w, out_h
    out_w = max(2, int(max_width) - (int(max_width) % 2))
    raw_h = int(round(src_h * (out_w / float(src_w))))
    out_h = max(2, raw_h - (raw_h % 2))
    return out_w, out_h


def sample_video_frames(
    video_path: str | Path,
    start: float,
    end: float,
    fps: float = 2.0,
    max_width: int = 640,
) -> list[np.ndarray]:
    """Amostra frames em sequência via FFmpeg (ou grab sequencial OpenCV como fallback), sem seeks por frame."""
    fps_val = max(0.5, float(fps))
    start_s = max(0.0, float(start))
    dur_s = max(0.1, float(end) - start_s)
    src_w, src_h = _probe_video_dimensions(video_path)
    out_w, out_h = _scaled_dimensions(src_w, src_h, max_width=max_width)

    ffmpeg_bin = resolve_cli_binary("ffmpeg")
    if ffmpeg_bin:
        try:
            res = subprocess.run(
                [
                    ffmpeg_bin,
                    "-v", "error",
                    "-ss", f"{start_s:.3f}",
                    "-t", f"{dur_s:.3f}",
                    "-i", str(video_path),
                    "-vf", f"fps={fps_val:g},scale={out_w}:{out_h}",
                    "-f", "rawvideo",
                    "-pix_fmt", "bgr24",
                    "pipe:1",
                ],
                capture_output=True,
                timeout=60,
                check=False,
            )
            frame_bytes = out_w * out_h * 3
            if res.returncode == 0 and res.stdout and frame_bytes > 0:
                count = len(res.stdout) // frame_bytes
                if count > 0:
                    raw = np.frombuffer(res.stdout[: count * frame_bytes], dtype=np.uint8)
                    return [raw[i * frame_bytes : (i + 1) * frame_bytes].reshape((out_h, out_w, 3)).copy() for i in range(count)]
        except Exception:
            pass

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    frames: list[np.ndarray] = []
    try:
        step = 1.0 / fps_val
        cap.set(cv2.CAP_PROP_POS_MSEC, start_s * 1000.0)
        next_t = start_s
        end_s = float(end)
        while True:
            if not cap.grab():
                break
            cur_t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if cur_t > end_s + 1e-6:
                break
            if cur_t + 1e-3 >= next_t:
                ok, frame = cap.retrieve()
                if not ok or frame is None:
                    break
                if frame.shape[1] > out_w:
                    frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
                frames.append(frame)
                while next_t <= cur_t + 1e-3:
                    next_t += step
    finally:
        cap.release()
    return frames


def _sample_video_frames(video_path: str | Path, start: float, end: float, fps: float = 2.0) -> list[np.ndarray]:
    return sample_video_frames(video_path, start, end, fps=fps)


@lru_cache(maxsize=2)
def _default_landmark_runner_factory(preset: str) -> Callable[[np.ndarray], list[tuple[float, float]] | None]:
    """Cria detector MediaPipe quando disponível; caso contrário retorna None (fallback óptico)."""
    try:
        import mediapipe as mp  # type: ignore

        face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)
        # Índices clássicos da boca no FaceMesh: cantos 61,291; verticais 37,84 e 267,314
        idxs = (61, 37, 267, 291, 314, 84)

        def _run(frame: np.ndarray):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)
            if not res.multi_face_landmarks:
                return None
            lm = res.multi_face_landmarks[0].landmark
            h, w = frame.shape[:2]
            return [(lm[i].x * w, lm[i].y * h) for i in idxs]

        return _run
    except Exception:
        return lambda _frame: None


@lru_cache(maxsize=1)
def _default_emotion_runner_factory() -> Callable[[np.ndarray], dict[str, float]]:
    try:
        from hsemotion.facial_emotions import HSEmotionRecognizer  # type: ignore

        recognizer = HSEmotionRecognizer(model_name="enet_b0_8_best_vgaf")

        def _run(frame: np.ndarray) -> dict[str, float]:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            label, scores = recognizer.predict_emotions(rgb, logits=False)
            top = float(np.max(scores)) if scores is not None else 0.0
            return {str(label).lower(): top}

        return _run
    except Exception:
        return lambda _frame: {}


def analyze_facecam_reactions(
    frames_or_video: list[np.ndarray] | str | Path,
    start: float,
    end: float,
    *,
    vision_preset: str = "auto",
    vram_mib: int | None = None,
    gpu_name: str | None = None,
    landmark_runner: Callable[[np.ndarray], Any] | None = None,
    emotion_runner: Callable[[np.ndarray], dict[str, float]] | None = None,
    vram_runner: VRAMRunner | None = None,
) -> dict[str, Any]:
    """Avalia reações na facecam respeitando o preset Low ('YuNet+MediaPipe') vs High ('+HSEmotion')."""
    resolved = resolve_vision_preset(vision_preset, vram_mib=vram_mib, gpu_name=gpu_name)
    preset = resolved["preset"]
    backend_used = resolved["models"]["facecam"]

    if isinstance(frames_or_video, (str, Path)):
        frames = _sample_video_frames(frames_or_video, start, end, fps=2.0)
    else:
        frames = list(frames_or_video or [])

    if not frames:
        return {
            "preset": preset,
            "backend_used": backend_used,
            "mar_peak": 0.0,
            "motion_peak": 0.0,
            "emotion_peak": 0.0,
            "score": 0.0,
        }

    runner = vram_runner or VRAMRunner()
    lm_fn = landmark_runner or _default_landmark_runner_factory(preset)
    use_emotion = preset == "high"
    emo_fn = (emotion_runner or _default_emotion_runner_factory()) if use_emotion else None

    def _run_stage() -> dict[str, Any]:
        mar_values: list[float] = []
        motion_values: list[float] = []
        emotion_values: list[float] = []
        prev_gray: np.ndarray | None = None

        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = cv2.absdiff(gray, prev_gray)
                motion_values.append(float(np.mean(diff)) / 32.0)
            prev_gray = gray

            pts = lm_fn(frame)
            if pts:
                mar_values.append(compute_mouth_aspect_ratio(pts))

            if emo_fn is not None:
                emo = emo_fn(frame) or {}
                excitement = max(
                    float(emo.get("surprise", 0.0)),
                    float(emo.get("happiness", 0.0)),
                    float(emo.get("fear", 0.0)),
                    float(emo.get("anger", 0.0)),
                    max((float(v) for v in emo.values()), default=0.0) * 0.7,
                )
                emotion_values.append(excitement)

        mar_peak = max(mar_values, default=0.0)
        motion_peak = min(1.0, max(motion_values, default=0.0))
        emotion_peak = min(1.0, max(emotion_values, default=0.0))

        mar_component = min(1.0, mar_peak / 0.65)
        base_score = 0.55 * mar_component + 0.35 * motion_peak
        if use_emotion:
            blended = max(base_score, 0.40 * mar_component + 0.25 * motion_peak + 0.35 * emotion_peak)
            if emotion_peak >= 0.4:
                blended = min(1.0, base_score + 0.12 * emotion_peak)
        else:
            blended = base_score

        return {
            "preset": preset,
            "backend_used": backend_used,
            "mar_peak": round(float(mar_peak), 3),
            "motion_peak": round(float(motion_peak), 3),
            "emotion_peak": round(float(emotion_peak), 3),
            "score": round(min(10.0, max(0.0, blended * 10.0)), 2),
        }

    return runner.run_stage(f"facecam_{preset}", _run_stage)
