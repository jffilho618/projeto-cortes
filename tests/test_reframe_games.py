from __future__ import annotations

import numpy as np
import pytest


def test_reaction_layout_transplanted_builds_split_filter_spec():
    from picorte.engine.reaction_layout import build_reaction_layout, measure_reaction_inset

    inset = measure_reaction_inset(
        source_w=1920,
        source_h=1080,
        facecam_box=(40, 40, 400, 300),
    )
    assert inset["corner"] == "top_left"
    assert inset["width"] == 400
    assert inset["height"] == 300

    spec = build_reaction_layout(
        source_w=1920,
        source_h=1080,
        out_w=1080,
        out_h=1920,
        facecam_box=(40, 40, 400, 300),
        facecam_h=640,
    )
    assert spec["out_w"] == 1080
    assert spec["out_h"] == 1920
    assert spec["facecam_h"] == 640
    assert spec["gameplay_h"] == 1280
    assert "vstack" in spec["filter_complex"]


def test_dynamic_layout_state_machine_enforces_hysteresis():
    from picorte.engine.reframe_games import compute_dynamic_layout_timeline

    # Rapid flickering events every 0.8s should be damped by >= 3.0s hysteresis
    timeline = [
        {"t": 0.0, "face_emotion": 0.1, "hud_action": 0.1},
        {"t": 0.8, "face_emotion": 0.9, "hud_action": 0.2},  # wants reacao_split_50_50 (< 3s hold -> blocked)
        {"t": 1.6, "face_emotion": 0.1, "hud_action": 0.9},  # wants acao_pip (< 3s hold -> blocked)
        {"t": 3.2, "face_emotion": 0.95, "hud_action": 0.1}, # >= 3.0s -> allowed switch to reacao_split_50_50
        {"t": 4.0, "face_emotion": 0.1, "hud_action": 0.9},  # < 3.0s since 3.2 -> blocked
        {"t": 6.5, "face_emotion": 0.1, "hud_action": 0.95}, # >= 3.0s since 3.2 -> allowed switch to acao_pip
    ]
    segments = compute_dynamic_layout_timeline(timeline, duration_s=10.0, min_hold_s=3.0)
    assert len(segments) >= 2
    for seg in segments:
        if seg["end"] < 10.0:
            assert (seg["end"] - seg["start"]) >= 3.0 - 1e-6
    assert segments[0]["layout"] == "historia_70_30"
    assert segments[1]["layout"] == "reacao_split_50_50"
    assert segments[2]["layout"] == "acao_pip"


def test_sniper_crop_ema_smoothing_and_preset_backends():
    from picorte.engine.reframe_games import compute_sniper_crop_track

    # Synthetic gameplay frames (1280x720) with moving bright target from left to right
    frames = []
    for idx in range(6):
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        cx = 120 + idx * 70
        frame[150:210, max(0, cx - 20) : min(640, cx + 20)] = 255
        frames.append(frame)

    low_track = compute_sniper_crop_track(
        frames,
        source_w=640,
        source_h=360,
        vision_preset="low",
        vram_mib=4096,
        ema_alpha=0.3,
    )
    assert low_track["backend_used"] == "optical_flow"
    assert len(low_track["centers"]) == 6
    # Center moves rightward smoothly without wild jumps
    assert low_track["centers"][-1][0] > low_track["centers"][0][0]

    yolo_calls = {"count": 0}

    def fake_tracker(frame, idx):
        yolo_calls["count"] += 1
        return (0.2 + idx * 0.12, 0.5)

    high_track = compute_sniper_crop_track(
        frames,
        source_w=640,
        source_h=360,
        vision_preset="high",
        vram_mib=12288,
        tracker_runner=fake_tracker,
        ema_alpha=0.3,
    )
    assert high_track["backend_used"] == "YOLO11n+tracking"
    assert yolo_calls["count"] == 6
    assert high_track["centers"][-1][0] > high_track["centers"][0][0]
