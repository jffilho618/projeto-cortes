"""W4 — Cirurgia de música ligada ao render: detecta no corte final e remonta o áudio limpo no .mp4."""
from __future__ import annotations

from pathlib import Path
import subprocess
import wave

import numpy as np
import pytest

from picorte.config import resolve_cli_binary

FFMPEG = resolve_cli_binary("ffmpeg") or "ffmpeg"


def _make_mp4(path: Path, *, with_music: bool) -> Path:
    if with_music:
        # 0–2s ruído (fala), 2–7s acorde contínuo (A2 + A4 + C#5 + E5), 7–9s ruído
        expr = (
            "if(between(t,2,7),0.2*sin(2*PI*110*t)+0.2*sin(2*PI*440*t)+0.15*sin(2*PI*554.37*t)"
            "+0.15*sin(2*PI*659.25*t),0.03*(random(0)*2-1))"
        )
    else:
        expr = "0.03*(random(0)*2-1)"
    subprocess.run([
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=9",
        "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d=9",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ], check=True)
    return path


def _audio_rms(mp4: Path, start: float, end: float, tmp: Path) -> float:
    wav = tmp / f"probe_{start}_{end}.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp4), "-ss", str(start), "-to", str(end),
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], check=True)
    with wave.open(str(wav), "rb") as wf:
        arr = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32767.0
    return float(np.sqrt(np.mean(arr ** 2)))


def _silent_vocals(slice_wav: Path, out_wav: Path) -> Path:
    with wave.open(str(slice_wav), "rb") as src, wave.open(str(out_wav), "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(src.getframerate())
        dst.writeframes(np.zeros(src.getnframes(), dtype="<i2").tobytes())
    return out_wav


def test_music_in_rendered_clip_is_removed_and_audio_remuxed(tmp_path: Path):
    from picorte.risk_shield.pipeline import clean_music_in_render

    mp4 = _make_mp4(tmp_path / "clip.mp4", with_music=True)
    before = _audio_rms(mp4, 3.0, 6.0, tmp_path)
    res = clean_music_in_render(mp4, separator_runner=_silent_vocals, cache_dir=tmp_path / "stems")
    assert res["surgery_applied"] is True
    assert res["status"] in {"auto_fixed", "human_review"}
    after = _audio_rms(mp4, 3.5, 5.5, tmp_path)
    assert after < before * 0.2
    assert "audio_path" not in res  # caminho temporário não vaza para o veredito


def test_clip_without_music_is_left_untouched(tmp_path: Path):
    from picorte.risk_shield.pipeline import clean_music_in_render

    mp4 = _make_mp4(tmp_path / "clip.mp4", with_music=False)
    original = mp4.read_bytes()
    res = clean_music_in_render(mp4, separator_runner=_silent_vocals)
    assert res["surgery_applied"] is False
    assert res["status"] == "pass"
    assert mp4.read_bytes() == original


def test_music_without_demucs_installed_degrades_to_review_and_keeps_file(tmp_path: Path, monkeypatch):
    import picorte.risk_shield.music_surgeon as ms
    from picorte.risk_shield.pipeline import clean_music_in_render

    monkeypatch.setattr(ms, "_is_demucs_available", lambda: False)
    mp4 = _make_mp4(tmp_path / "clip.mp4", with_music=True)
    original = mp4.read_bytes()
    res = clean_music_in_render(mp4)
    assert res["status"] == "human_review"
    assert res["code"] == "NEEDS_HUMAN_AUDIO_CHECK"
    assert mp4.read_bytes() == original


def test_unexpected_failure_never_breaks_render_and_asks_review(tmp_path: Path, monkeypatch):
    import picorte.risk_shield.pipeline as pl

    def boom(*a, **k):
        raise RuntimeError("ffmpeg sumiu")

    monkeypatch.setattr(pl, "run_selective_music_surgery", boom)
    mp4 = _make_mp4(tmp_path / "clip.mp4", with_music=True)
    res = pl.clean_music_in_render(mp4)
    assert res["status"] == "human_review"
    assert res["code"] == "NEEDS_HUMAN_AUDIO_CHECK"


def test_attach_risk_verdict_forwards_music_result(tmp_path: Path):
    import json

    from picorte.db.connection import Database
    from picorte.db.repositories import PicorteRepositories
    from picorte.risk_shield.pipeline import attach_risk_verdict
    from picorte.risk_shield.policy_gate import sync_publisher_policies

    db = Database(f"sqlite:///{(tmp_path / 'w4.db').as_posix()}")
    db.init_schema()
    sync_publisher_policies(db)
    src = PicorteRepositories(db).sources.create_source(
        name="A", platform="twitch", channel_handle="@a", permission_status="liberada")
    meta = tmp_path / "c.meta.json"
    meta.write_text(json.dumps({"title": "corte"}), encoding="utf-8")
    v = attach_risk_verdict(db, meta_path=meta, source_id=src["id"], seg={"start": 0, "end": 30}, words=[],
                            mp4_path=None, options={"aspect": "9:16"}, game_slug="gta6",
                            music_result={"status": "pass", "surgery_applied": False, "intervals": []},
                            cadence_state_path=tmp_path / "cad.json")
    assert v["gates"]["music_surgeon"]["status"] == "pass"
