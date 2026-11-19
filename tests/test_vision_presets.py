from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest


def test_resolve_vision_preset_auto_low_and_high():
    from picorte.config import VISION_PRESETS, resolve_vision_preset

    low = resolve_vision_preset("auto", vram_mib=4096, gpu_name="NVIDIA GeForce GTX 1650")
    assert low["preset"] == "low"
    assert low["requested_preset"] == "auto"
    assert low["auto_detected"] == "low"
    assert low["models"]["facecam"] == "YuNet+MediaPipe"
    assert low["models"]["hud"] == "RapidOCR+optical_flow"
    assert low["models"]["sniper_crop"] == "optical_flow"
    assert low["models"]["thumbnail_cutout"] == "u2netp"
    assert low["models"]["whisper_model"] == "small"
    assert low["models"]["compute_type"] == "int8"

    high = resolve_vision_preset("auto", vram_mib=12288, gpu_name="NVIDIA GeForce RTX 4070 Ti")
    assert high["preset"] == "high"
    assert high["requested_preset"] == "auto"
    assert high["auto_detected"] == "high"
    assert high["models"]["facecam"] == "YuNet+MediaPipe+HSEmotion"
    assert high["models"]["hud"] == "YOLO11n+RapidOCR"
    assert high["models"]["sniper_crop"] == "YOLO11n+tracking"
    assert high["models"]["thumbnail_cutout"] == "BiRefNet"
    assert high["models"]["whisper_model"] == "large-v3-turbo"
    assert high["models"]["compute_type"] == "int8_float16"

    assert set(VISION_PRESETS) == {"low", "high"}


def test_resolve_vision_preset_manual_override_and_invalid():
    from picorte.config import resolve_vision_preset

    override_high = resolve_vision_preset("high", vram_mib=4096, gpu_name="GTX 1650")
    assert override_high["preset"] == "high"
    assert override_high["requested_preset"] == "high"
    assert override_high["auto_detected"] == "low"

    override_low = resolve_vision_preset("low", vram_mib=12288, gpu_name="RTX 4070 Ti")
    assert override_low["preset"] == "low"
    assert override_low["requested_preset"] == "low"
    assert override_low["auto_detected"] == "high"

    with pytest.raises(ValueError):
        resolve_vision_preset("ultra")


def test_projects_validates_vision_preset_option():
    import projects

    assert projects.validate_options({})["vision_preset"] == "auto"
    assert projects.validate_options({"vision_preset": "high"})["vision_preset"] == "high"
    assert projects.validate_options({"vision_preset": "low"})["vision_preset"] == "low"
    with pytest.raises(ValueError):
        projects.validate_options({"vision_preset": "ultra"})


def test_dashboard_config_exposes_vision_presets_and_html_controls(tmp_path):
    import dashboard

    server = dashboard.make_server(tmp_path / "projects", 0)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/config") as resp:
            cfg = json.loads(resp.read().decode("utf-8"))
        assert "vision_presets" in cfg
        assert {item["id"] for item in cfg["vision_presets"]} == {"auto", "low", "high"}
        assert "detected_gpu" in cfg
        assert cfg["detected_vision_preset"]["preset"] in {"low", "high"}
    finally:
        server.shutdown()
        server.app.close()
        server.server_close()

    html = Path("assets/studio/index.html").read_text(encoding="utf-8")
    assert 'name="vision_preset"' in html
    assert 'name="ai_mode"' in html
    assert 'id="hardware-badge"' in html
    assert 'id="db-badge"' in html
