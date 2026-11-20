"""P4 (code review Épico 4) — Selo Verde 15s sem brechas: Cold Open, Camada 2/3, fade 15ms, máscara e thumbnail."""
from __future__ import annotations

from pathlib import Path
import subprocess
import wave

import numpy as np
import pytest


def _w(word, s, e):
    return {"word": word, "start": s, "end": e}


def test_cold_open_profanity_gets_teaser_relative_bleep_and_censored_caption():
    from picorte.risk_shield.green_seal_15s import plan_green_seal_audio_and_captions

    words = [_w("olha", 100.0, 100.4), _w("caralho", 125.2, 125.6), _w("mano", 125.7, 126.0)]
    plan = plan_green_seal_audio_and_captions(
        words, clip_start=100.0, clip_end=140.0,
        cold_open_plan={"enabled": True, "teaser_start": 125.0, "teaser_end": 126.5},
    )
    assert plan["cold_open_bleeps"] == [{"start": pytest.approx(0.16, abs=0.01),
                                         "end": pytest.approx(0.64, abs=0.01),
                                         "original_word": "caralho"}]
    teaser_words = [w["word"] for w in plan["cold_open_censored_words"]]
    assert teaser_words == ["***", "mano"]
    assert plan["status"] == "auto_fixed"


def test_tier2_sensitive_term_in_first_15s_requires_review():
    from picorte.risk_shield.green_seal_15s import plan_green_seal_audio_and_captions

    plan = plan_green_seal_audio_and_captions([_w("cocaína", 2.0, 2.5)], clip_start=0.0, clip_end=30.0)
    assert plan["status"] == "human_review"
    assert plan["tier2_hits"]


def test_render_helper_aborts_on_hard_block_and_never_swallows_errors(monkeypatch):
    from picorte.engine import render_clips
    from picorte.risk_shield.policy_gate import PolicyViolationError

    with pytest.raises(PolicyViolationError):
        render_clips._apply_green_seal({}, [_w("estupro", 1.0, 1.5)], 0.0, 30.0)

    import picorte.risk_shield.green_seal_15s as gs

    def boom(*a, **k):
        raise RuntimeError("falhou")

    monkeypatch.setattr(gs, "plan_green_seal_audio_and_captions", boom)
    with pytest.raises(RuntimeError):
        render_clips._apply_green_seal({}, [_w("oi", 1.0, 1.5)], 0.0, 30.0)


def test_render_helper_clears_stale_bleeps():
    from picorte.engine import render_clips

    seg = {"_green_seal_bleeps": [{"start": 1.0, "end": 1.5}]}
    words = render_clips._apply_green_seal(seg, [_w("oi", 1.0, 1.5)], 0.0, 30.0)
    assert seg["_green_seal_bleeps"] == []
    assert words[0]["word"] == "oi"


def test_root_render_module_has_same_green_seal_helper():
    import render_clips as root_rc

    assert hasattr(root_rc, "_apply_green_seal") and hasattr(root_rc, "_green_seal_audio_filter")


def test_bleep_filter_ramps_without_hard_step(tmp_path: Path):
    from picorte.config import resolve_cli_binary
    from picorte.engine.render_clips import _green_seal_audio_filter

    sr = 48000
    src = tmp_path / "tone.wav"
    t = np.arange(sr * 2) / sr
    tone = (0.5 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    with wave.open(str(src), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(tone.tobytes())
    af = _green_seal_audio_filter([{"start": 0.5, "end": 1.0}], 2.0)
    out = tmp_path / "out.wav"
    ffmpeg = resolve_cli_binary("ffmpeg") or "ffmpeg"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-af", af, str(out)], check=True)
    with wave.open(str(out), "rb") as wf:
        arr = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32767.0
    win = int(sr * 0.002)
    env = np.array([np.max(np.abs(arr[i:i + win])) for i in range(0, arr.size - win, win)])
    mid = env[int(0.7 * sr / win): int(0.8 * sr / win)]
    assert float(mid.max()) < 0.05  # mudo no meio
    edge = env[int(0.49 * sr / win): int(0.53 * sr / win)]
    assert np.count_nonzero((edge > 0.05) & (edge < 0.45)) >= 2  # há rampa (não degrau seco)


def test_excluded_facecam_area_does_not_dilute_gore_ratio():
    from picorte.risk_shield.green_seal_15s import score_frame_visual_safety

    fr = np.full((360, 640, 3), (40, 120, 40), dtype=np.uint8)
    fr[:, 320:440] = (0, 0, 200)  # sangue saturado em ~37% da área NÃO excluída
    res = score_frame_visual_safety(fr, exclude_box=(0, 0, 320, 360))
    assert "gore" in res["flags"]


def test_thumbnail_never_picks_unsafe_frame_even_with_facecam_bonus():
    from picorte.engine.thumbnail_factory import _rank_thumbnail_frames

    gore = np.full((360, 640, 3), (0, 0, 200), dtype=np.uint8)
    safe = np.full((360, 640, 3), (90, 140, 90), dtype=np.uint8)
    safe[100:200, 100:300] = (200, 200, 200)
    best, _box = _rank_thumbnail_frames([gore, safe], facecam_box=None)
    assert best is safe


def test_thumbnail_fails_closed_when_every_frame_is_unsafe():
    from picorte.engine.thumbnail_factory import ThumbnailUnsafeError, _rank_thumbnail_frames

    gore = np.full((360, 640, 3), (0, 0, 200), dtype=np.uint8)
    with pytest.raises(ThumbnailUnsafeError):
        _rank_thumbnail_frames([gore, gore.copy()], facecam_box=None)
