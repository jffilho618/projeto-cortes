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


class UnavailableBackend:
    """Detector que não carregou: devolve vazio como antes, mas carrega o MOTIVO (code review 2026-11-23).

    Antes a fábrica devolvia `lambda _: None` e o `backend_used` continuava dizendo "MediaPipe": a facecam
    virava só movimento do quadro inteiro (nota cravada em 3,5) e a saúde dizia ok.
    """

    def __init__(self, name: str, exc: BaseException, empty: Callable[[], Any]):
        self.name = name
        self.reason = f"{name} indisponível ({type(exc).__name__}: {exc})"
        self._empty = empty

    def __call__(self, *_args: Any, **_kwargs: Any) -> Any:
        return self._empty()


def degraded_reasons(*runners: Any) -> list[str]:
    return [r.reason for r in runners if isinstance(r, UnavailableBackend)]


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
    except Exception as exc:
        return UnavailableBackend("MediaPipe", exc, lambda: None)


@lru_cache(maxsize=1)
def _default_emotion_runner_factory() -> Callable[[np.ndarray], dict[str, float]]:
    """HSEmotion em ONNX (CPU, `onnxruntime`): recebe o ROSTO recortado (BGR) e devolve as 8 emoções.

    Modelo `enet_b0_8_best_vgaf` (AffectNet), baixado na 1ª vez para ~/.hsemotion. Escolhido no code review de
    2026-11-23 no lugar do `hsemotion` em torch: mesmo modelo, sem disputar a GPU.
    """
    try:
        import urllib.request  # noqa: F401 — o hsemotion_onnx chama urllib.request sem importá-lo
        from hsemotion_onnx.facial_emotions import HSEmotionRecognizer  # type: ignore

        recognizer = HSEmotionRecognizer(model_name="enet_b0_8_best_vgaf")
        classes = [str(recognizer.idx_to_class[i]).lower() for i in sorted(recognizer.idx_to_class)]

        def _run(face_bgr: np.ndarray) -> dict[str, float]:
            rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
            _, scores = recognizer.predict_emotions(rgb, logits=False)
            return {c: float(s) for c, s in zip(classes, scores)}

        return _run
    except Exception as exc:
        return UnavailableBackend("HSEmotion", exc, dict)


MIN_FACE_PX = 64           # abaixo disso (proxy de 240p: rosto de 15–48 px) a emoção não é confiável
FACE_CROP_MARGIN = 0.20    # margem em volta da caixa do YuNet, como nos recortes de treino
REACTION_EMOTIONS = ("surprise", "fear", "happiness", "anger")
NOT_A_REACTION = ("neutral",)


def locate_face_fast(frame: np.ndarray, max_width: int = 640) -> tuple[int, int, int, int] | None:
    """YuNet num quadro reduzido (18 ms contra 51 ms a 1280 px) e a caixa de volta na escala do quadro original."""
    from picorte.engine import reaction_layout

    h, w = frame.shape[:2]
    if w <= max_width:
        return reaction_layout.find_reactor_face(frame)
    scale = w / float(max_width)
    small = cv2.resize(frame, (max_width, max(2, int(round(h / scale)))), interpolation=cv2.INTER_AREA)
    box = reaction_layout.find_reactor_face(small)
    if box is None:
        return None
    return tuple(int(round(v * scale)) for v in box)  # type: ignore[return-value]


def _crop_face(frame: np.ndarray, box: tuple[int, int, int, int], margin: float = FACE_CROP_MARGIN) -> np.ndarray:
    x, y, w, h = (int(v) for v in box)
    m = int(round(margin * max(w, h)))
    fh, fw = frame.shape[:2]
    return frame[max(0, y - m): min(fh, y + h + m), max(0, x - m): min(fw, x + w + m)]


EMOTION_SUSTAIN_S = 1.5   # a subida precisa durar 1,5 s seguidos para contar como reação


def _emotion_peak(series: list[dict[str, float]], *, frame_dt: float = 0.5) -> float:
    """Reação = quanto uma emoção de REAÇÃO sobe acima do rosto normal do trecho e se SUSTENTA por 1,5 s.

    Medido na ae5f08 (2026-11-23):
    - o rosto concentrado de quem joga sai "raiva" em 25 de 29 quadros: a mediana do trecho tira esse viés;
    - o modelo oscila quadro a quadro: com 1 s bastando, 11 de 12 candidatos davam pico ≥ 0,5; exigindo a subida
      sustentada (mínimo da janela de 1,5 s) só 2 se destacam (0,98 e 0,89) — as duas risadas de verdade
      ("Temos duas partes da arma já", "que você não desce, sua cachorra"); os outros ficam ≤ 0,43;
    - susto de rosto dura ~1 s e não passa: o susto é pego pelo áudio (`prosody_events`).
    Só surpresa, medo, felicidade e raiva contam; neutro, tristeza, nojo e desprezo não são reação.
    """
    if not series:
        return 0.0
    mat = np.array([[float(s.get(k, 0.0)) for k in REACTION_EMOTIONS] for s in series], dtype=np.float32)
    per_frame = np.clip(mat - np.median(mat, axis=0), 0.0, None).max(axis=1)
    win = max(1, int(round(EMOTION_SUSTAIN_S / max(1e-3, float(frame_dt)))))
    if per_frame.size < win:
        return 0.0
    sustained = np.array([per_frame[i:i + win].min() for i in range(per_frame.size - win + 1)])
    return float(min(1.0, sustained.max()))


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
    yaw_runner: Callable[[np.ndarray], float | None] | None = None,
    vram_runner: VRAMRunner | None = None,
    face_locator: Callable[[np.ndarray], tuple[int, int, int, int] | None] | None = None,
) -> dict[str, Any]:
    """Avalia reações na facecam respeitando o preset Low ('YuNet+MediaPipe') vs High ('+HSEmotion').

    No High, o rosto da facecam é localizado (YuNet, `reaction_layout.find_reactor_face`) e a emoção é medida no
    ROSTO RECORTADO; o movimento da facecam passa a ser o da região do rosto (W44, code review 2026-11-23).
    """
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
            "gaze_to_camera_sec": 0.0,
            "face_disappeared_event": False,
            "inspection_pause_score": 0.0,
            "face_measured": False,
            "emotion_measured": False,
            "degraded": [],
            "score": 0.0,
        }

    runner = vram_runner or VRAMRunner()
    lm_fn = landmark_runner or _default_landmark_runner_factory(preset)
    use_emotion = preset == "high"
    emo_fn = (emotion_runner or _default_emotion_runner_factory()) if use_emotion else None
    if face_locator is None and use_emotion:
        face_locator = locate_face_fast
    boxes = [face_locator(f) for f in frames] if face_locator is not None else [None] * len(frames)
    usable = [b for b in boxes if b is not None and min(int(b[2]), int(b[3])) >= MIN_FACE_PX]
    small = [min(int(b[2]), int(b[3])) for b in boxes if b is not None and b not in usable]
    face_region = usable[0] if usable else None  # a facecam fica parada: a 1ª caixa boa marca a região
    degraded = degraded_reasons(lm_fn, emo_fn)
    if emo_fn is not None and not usable and small and not isinstance(emo_fn, UnavailableBackend):
        degraded.append(f"rosto pequeno demais para medir emoção ({max(small)} px < {MIN_FACE_PX} px)")
    if degraded:
        backend_used = f"{backend_used} — degradado: {'; '.join(degraded)}"

    def _run_stage() -> dict[str, Any]:
        mar_values: list[float] = []
        motion_values: list[float] = []
        border_motion_values: list[float] = []
        center_motion_values: list[float] = []
        emotion_series: list[dict[str, float]] = []
        face_motion_values: list[float] = []
        face_presence: list[bool] = []
        frontal_streak = 0
        max_frontal_streak = 0
        prev_gray: np.ndarray | None = None
        dur_s = max(0.5, float(end) - float(start))
        dt = dur_s / max(1, len(frames))

        for frame, box in zip(frames, boxes):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = cv2.absdiff(gray, prev_gray)
                motion_values.append(float(np.mean(diff)) / 32.0)
                if face_region is not None:  # movimento da CABEÇA, não do jogo (W44)
                    face_diff = _crop_face(diff, face_region, margin=0.5)
                    if face_diff.size:
                        face_motion_values.append(float(np.mean(face_diff)) / 32.0)
                h, w = diff.shape[:2]
                cy1, cy2 = int(h * 0.25), int(h * 0.75)
                cx1, cx2 = int(w * 0.25), int(w * 0.75)
                center_m = float(np.mean(diff[cy1:cy2, cx1:cx2])) if (cy2 > cy1 and cx2 > cx1) else 0.0
                # Borda externa (movimento global da câmera do personagem)
                border_mask = np.ones_like(diff, dtype=bool)
                border_mask[cy1:cy2, cx1:cx2] = False
                border_m = float(np.mean(diff[border_mask])) if np.any(border_mask) else 0.0
                center_motion_values.append(center_m)
                border_motion_values.append(border_m)
            prev_gray = gray

            pts = lm_fn(frame)
            has_face = bool(pts)
            face_presence.append(has_face)
            if pts:
                mar_values.append(compute_mouth_aspect_ratio(pts))

            if yaw_runner is not None:
                yaw = yaw_runner(frame)
                if yaw is not None and abs(float(yaw)) <= 12.0:
                    frontal_streak += 1
                    max_frontal_streak = max(max_frontal_streak, frontal_streak)
                else:
                    frontal_streak = 0

            if emo_fn is not None and box is not None and min(int(box[2]), int(box[3])) >= MIN_FACE_PX:
                crop = _crop_face(frame, box)
                if crop.size:
                    emo = emo_fn(crop) or {}
                    if emo:
                        emotion_series.append({str(k).lower(): float(v) for k, v in emo.items()})

        mar_peak = max(mar_values, default=0.0)
        # Com a facecam localizada, o "movimento" da facecam é o da região do rosto; sem ela, o do quadro (legado).
        motion_peak = min(1.0, max(face_motion_values if face_region is not None else motion_values, default=0.0))
        emotion_measured = bool(emotion_series)
        emotion_peak = _emotion_peak(emotion_series, frame_dt=dt)
        mar_measured = bool(mar_values) and not isinstance(lm_fn, UnavailableBackend)
        face_measured = mar_measured or emotion_measured or not isinstance(lm_fn, UnavailableBackend)

        # Gaze-to-camera (olhar sustentado direto na lente)
        gaze_to_camera_sec = round(max_frontal_streak * dt, 2)

        # Facepalm / fuga do quadro: rosto presente por >= 2 frames e depois some abruptamente
        seen_face = sum(1 for p in face_presence if p)
        face_disappeared = False
        if seen_face >= 2:
            for idx in range(1, len(face_presence)):
                if face_presence[idx - 1] and not face_presence[idx]:
                    if sum(1 for p in face_presence[idx : idx + 2] if not p) >= 1:
                        face_disappeared = True
                        break

        # Detetive de Inspeção Visual: câmera para de mexer globalmente (borda cai a quase zero)
        # enquanto pequena região central continua mudando (ex.: abrir geladeira / olhar objeto)
        inspection_pause_score = 0.0
        if len(border_motion_values) >= 4:
            peak_border = max(border_motion_values)
            if peak_border >= 10.0:
                inspected_frames = sum(
                    1
                    for bm, cm in zip(border_motion_values, center_motion_values)
                    if bm <= peak_border * 0.25 and cm >= max(3.0, bm * 2.0)
                )
                inspection_pause_score = round(min(1.0, inspected_frames / max(1.0, len(border_motion_values) * 0.5)), 3)

        mar_component = min(1.0, mar_peak / 0.65)
        base_score = 0.55 * mar_component + 0.35 * motion_peak
        if use_emotion and emotion_measured and not mar_measured:
            # Boca não medida (sem MediaPipe): não entra como zero — a emoção leva o peso dela (sinal só vale se medido)
            blended = max(base_score, 0.65 * emotion_peak + 0.35 * motion_peak)
        elif use_emotion:
            blended = max(base_score, 0.40 * mar_component + 0.25 * motion_peak + 0.35 * emotion_peak)
            if emotion_peak >= 0.4:  # reforço, nunca rebaixa: emoção mais forte não pode dar nota menor
                blended = max(blended, min(1.0, base_score + 0.12 * emotion_peak))
        else:
            blended = base_score

        return {
            "preset": preset,
            "backend_used": backend_used,
            "mar_peak": round(float(mar_peak), 3),
            "motion_peak": round(float(motion_peak), 3),
            "emotion_peak": round(float(emotion_peak), 3),
            "gaze_to_camera_sec": gaze_to_camera_sec,
            "face_disappeared_event": face_disappeared,
            "inspection_pause_score": inspection_pause_score,
            "face_measured": face_measured,
            "emotion_measured": emotion_measured,
            "degraded": degraded,
            "score": round(min(10.0, max(0.0, blended * 10.0)), 2),
        }

    return runner.run_stage(f"facecam_{preset}", _run_stage)
