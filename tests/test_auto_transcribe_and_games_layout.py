from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from picorte.config import resolve_cli_binary


def test_validate_options_auto_resolves_whisper_and_device_from_hardware(monkeypatch):
    import picorte.config as cfg
    import projects

    # Simula Notebook GTX 1650 (4 GB)
    monkeypatch.setattr(cfg, "probe_nvidia_smi", lambda: (4096, "NVIDIA GeForce GTX 1650"))
    opts_low = projects.validate_options({})
    assert opts_low["whisper_model"] == "small"
    assert opts_low["device"] == "cuda"

    # Simula Desktop RTX 4070 Ti (12 GB) com preset auto
    monkeypatch.setattr(cfg, "probe_nvidia_smi", lambda: (12288, "NVIDIA GeForce RTX 4070 Ti"))
    opts_high = projects.validate_options({})
    assert opts_high["whisper_model"] == "large-v3-turbo"
    assert opts_high["device"] == "cuda"

    # Sem GPU: cai para base + cpu
    monkeypatch.setattr(cfg, "probe_nvidia_smi", lambda: (0, ""))
    opts_cpu = projects.validate_options({})
    assert opts_cpu["whisper_model"] == "base"
    assert opts_cpu["device"] == "cpu"

    # Escolha explícita do operador é preservada
    opts_manual = projects.validate_options({"whisper_model": "tiny", "device": "cpu"})
    assert opts_manual["whisper_model"] == "tiny"
    assert opts_manual["device"] == "cpu"


def test_games_layout_option_and_real_render_9_16(tmp_path):
    import projects
    import render_clips

    opts = projects.validate_options({"aspect": "9:16", "layout": "games"})
    assert opts["layout"] == "games"

    with pytest.raises(ValueError):
        projects.validate_options({"aspect": "16:9", "layout": "games"})

    # Gera vídeo 16:9 real com quadro de facecam colorido no canto superior esquerdo e gameplay na área principal
    src = tmp_path / "games_source.mp4"
    ffmpeg = resolve_cli_binary("ffmpeg") or "ffmpeg"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=15:duration=4",
            "-f", "lavfi", "-i", "sine=frequency=520:duration=4",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(src),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    words = [
        {"word": "jogada", "start": 0.2, "end": 0.8},
        {"word": "epica", "start": 0.9, "end": 1.6},
    ]
    out_dir = tmp_path / "clips"
    out_dir.mkdir()
    seg = {
        "id": "001",
        "start": 0.0,
        "end": 3.5,
        "hook": "clutch games layout",
        "overall": 9.1,
        "context_banner_2s": "FACECAM + GAMEPLAY!",
    }
    out_mp4 = render_clips.render(
        seg,
        words,
        src,
        1280,
        720,
        tmp_path,
        "9:16",
        out_dir=out_dir,
        layout="games",
        vision_preset="low",
    )
    assert out_mp4.is_file() and out_mp4.stat().st_size > 5000

    # Verifica resolução final exata 1080x1920
    cap = cv2.VideoCapture(str(out_mp4))
    ok, frame = cap.read()
    cap.release()
    assert ok and frame is not None
    assert frame.shape[:2] == (1920, 1080)

    # Verifica UI expõe games layout e large-v3-turbo / auto
    html = Path("assets/studio/index.html").read_text(encoding="utf-8")
    assert 'value="games"' in html
    assert "large-v3-turbo" in html


def test_dashboard_run_disables_interactive_stdin_and_passes_no_input(tmp_path, monkeypatch):
    import dashboard
    import projects

    captured = {}

    class _FakeProc:
        def wait(self):
            return 0

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _FakeProc()

    monkeypatch.setattr(dashboard.subprocess, "Popen", fake_popen)
    app = dashboard.Studio(tmp_path / "projects")
    state = projects.create_project(tmp_path / "projects", str(tmp_path / "x.mp4"), {"aspect": "9:16"})
    pdir = projects.project_path(tmp_path / "projects", state["id"])
    app._run(pdir, "prepare", False, None)
    app.close()

    assert "--no-input" in captured["cmd"]
    assert captured["kwargs"].get("stdin") == dashboard.subprocess.DEVNULL

