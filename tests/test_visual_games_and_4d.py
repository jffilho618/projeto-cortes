from __future__ import annotations

import numpy as np
import pytest


def test_snap_boundaries_avoids_mid_word_cuts_and_snaps_to_silence():
    from picorte.engine.snap_boundaries import find_nearest_silence, snap_window_to_words_and_silences

    silences = [(9.4, 10.1), (34.8, 35.6)]
    assert find_nearest_silence(silences, 9.9, max_snap=1.0) == pytest.approx(9.9)
    assert find_nearest_silence(silences, 10.3, max_snap=1.0) == pytest.approx(10.1)

    words = [
        {"word": "olha", "start": 9.8, "end": 10.3},
        {"word": "esse", "start": 10.4, "end": 10.8},
        {"word": "clutch", "start": 34.1, "end": 34.7},
    ]
    # Cutting at 10.0 and 34.4 slices right through "olha" and "clutch"
    s, e = snap_window_to_words_and_silences(10.0, 34.4, words=words, silences=[], duration_s=60.0)
    assert s <= 9.8
    assert e >= 34.7


def test_visual_games_mar_and_preset_dispatch():
    from picorte.engine.visual_games import analyze_facecam_reactions, compute_mouth_aspect_ratio

    # Closed vs wide-open mouth (vertical/horizontal 6-point landmark loop)
    closed = [(0, 0), (1, 0.05), (2, 0.05), (3, 0), (2, -0.05), (1, -0.05)]
    open_mouth = [(0, 0), (1, 0.9), (2, 0.9), (3, 0), (2, -0.9), (1, -0.9)]
    assert compute_mouth_aspect_ratio(closed) < 0.15
    assert compute_mouth_aspect_ratio(open_mouth) > 0.50

    frames = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(4)]
    frames[1][10:50, 10:50] = 200  # visual motion

    emotion_called = {"count": 0}

    def fake_landmarks(_frame):
        return open_mouth

    def fake_emotion(_frame):
        emotion_called["count"] += 1
        return {"surprise": 0.92, "happiness": 0.05}

    low_res = analyze_facecam_reactions(
        frames,
        0.0,
        4.0,
        vision_preset="low",
        vram_mib=4096,
        landmark_runner=fake_landmarks,
        emotion_runner=fake_emotion,
    )
    assert low_res["backend_used"] == "YuNet+MediaPipe"
    assert emotion_called["count"] == 0
    assert low_res["score"] > 5.0

    high_res = analyze_facecam_reactions(
        frames,
        0.0,
        4.0,
        vision_preset="high",
        vram_mib=12288,
        landmark_runner=fake_landmarks,
        emotion_runner=fake_emotion,
    )
    assert high_res["backend_used"] == "YuNet+MediaPipe+HSEmotion"
    assert emotion_called["count"] == 4
    assert high_res["score"] >= low_res["score"]


def test_hud_detector_recognizes_killfeed_and_presets():
    from picorte.engine.hud_detector import detect_hud_events

    frames = [np.zeros((72, 128, 3), dtype=np.uint8) for _ in range(3)]
    yolo_called = {"count": 0}

    def fake_ocr(frame, idx):
        if idx == 1:
            return ["ELIMINATED PLAYER_X", "+100 KILL"]
        if idx == 2:
            return ["VICTORY ROYALE"]
        return []

    def fake_yolo(_frame):
        yolo_called["count"] += 1
        return [{"label": "kill_banner", "conf": 0.91}]

    low_hud = detect_hud_events(
        frames,
        10.0,
        13.0,
        vision_preset="low",
        vram_mib=4096,
        ocr_runner=fake_ocr,
        yolo_runner=fake_yolo,
    )
    assert low_hud["backend_used"] == "RapidOCR+optical_flow"
    assert yolo_called["count"] == 0
    assert len(low_hud["events"]) >= 2
    assert low_hud["score"] >= 7.0

    high_hud = detect_hud_events(
        frames,
        10.0,
        13.0,
        vision_preset="high",
        vram_mib=12288,
        ocr_runner=fake_ocr,
        yolo_runner=fake_yolo,
    )
    assert high_hud["backend_used"] == "YOLO11n+RapidOCR"
    assert yolo_called["count"] == 3
    assert high_hud["score"] >= low_hud["score"]


def test_score_clips_4d_fusion_and_snap_integration():
    import score_clips

    fused = score_clips.fuse_4d_score(
        score_chat=9.0,
        score_audio=8.5,
        score_visual=8.0,
        score_text=7.5,
        hud_score=9.0,
    )
    assert 8.0 <= fused["overall"] <= 10.0
    assert fused["score_chat"] == pytest.approx(9.0)
    assert fused["score_hud"] == pytest.approx(9.0)

    cands = [{"start": 10.0, "end": 30.0, "overall": 7.4, "reason": "base"}]
    words = [
        {"word": "olha", "start": 9.7, "end": 10.2},
        {"word": "isso", "start": 29.8, "end": 30.3},
    ]
    updated = score_clips.apply_4d_and_snap(
        cands,
        words=words,
        silences=[],
        duration_s=60.0,
        chat_seismic={"per_second": [{"t": i, "vel_zscore": 5.5 if 10 <= i <= 30 else 0.0, "emote_burst": 0.5 if 10 <= i <= 30 else 0.0} for i in range(60)]},
        visual_scores={(10.0, 30.0): {"visual_score": 8.6, "hud_score": 8.8}},
    )
    assert updated[0]["start"] <= 9.7
    assert updated[0]["end"] >= 30.3
    assert updated[0]["overall"] > 7.4
    assert updated[0]["evidence"]["chat"] >= 7.0


def test_sample_video_frames_avoids_per_frame_seek_and_caches_runners(tmp_path, monkeypatch):
    import subprocess
    import cv2
    from picorte.config import resolve_cli_binary
    from picorte.engine import hud_detector, visual_games

    src = tmp_path / "sample.mp4"
    ff = resolve_cli_binary("ffmpeg") or "ffmpeg"
    subprocess.run(
        [
            ff, "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=15:duration=4",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(src),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    seek_calls = {"count": 0}
    orig_vc = cv2.VideoCapture

    class CountingVC:
        def __init__(self, *args, **kwargs):
            self._inner = orig_vc(*args, **kwargs)

        def set(self, prop, val):
            if prop == cv2.CAP_PROP_POS_MSEC:
                seek_calls["count"] += 1
            return self._inner.set(prop, val)

        def __getattr__(self, item):
            return getattr(self._inner, item)

    monkeypatch.setattr(cv2, "VideoCapture", CountingVC)
    frames = visual_games.sample_video_frames(src, 1.0, 3.0, fps=2.0, max_width=320)
    assert len(frames) >= 4
    assert frames[0].shape[1] <= 320
    assert seek_calls["count"] <= 1

    # Cache de runners pesados entre candidatos
    assert hud_detector._default_ocr_runner_factory() is hud_detector._default_ocr_runner_factory()
    assert visual_games._default_landmark_runner_factory("low") is visual_games._default_landmark_runner_factory("low")
