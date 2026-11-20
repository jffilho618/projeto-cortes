"""P1 (code review Épico 4) — music_surgeon: taxa de amostragem (A2), pasta por chunk, falhas e WAV 24-bit."""
from __future__ import annotations

import math
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np
import pytest


def _write_wav(path: Path, samples: np.ndarray, sr: int, sampwidth: int = 2) -> Path:
    clipped = np.clip(samples, -1.0, 1.0)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sr)
        if sampwidth == 2:
            wf.writeframes((clipped * 32767.0).astype("<i2").tobytes())
        else:  # 24-bit
            ints = (clipped * 8388607.0).astype("<i4")
            wf.writeframes(b"".join(int(v).to_bytes(3, "little", signed=True) for v in ints))
    return path


def _read(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        arr = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32767.0
    return arr, sr


def _peak_hz(arr: np.ndarray, sr: int) -> float:
    spec = np.abs(np.fft.rfft(arr * np.hanning(arr.size)))
    return float(np.fft.rfftfreq(arr.size, 1.0 / sr)[int(np.argmax(spec))])


def test_vocals_at_44k_keep_original_pitch_and_duration(tmp_path: Path):
    from picorte.risk_shield.music_surgeon import run_selective_music_surgery

    sr = 16000
    src = _write_wav(tmp_path / "in.wav", np.zeros(sr * 6, dtype=np.float32), sr)

    def demucs_44k(slice_wav: Path, out_wav: Path) -> Path:
        with wave.open(str(slice_wav), "rb") as wf:
            dur = wf.getnframes() / wf.getframerate()
        n = int(round(dur * 44100))
        t = np.arange(n, dtype=np.float32) / 44100.0
        return _write_wav(out_wav, 0.4 * np.sin(2 * math.pi * 440.0 * t), 44100)

    out = tmp_path / "out.wav"
    res = run_selective_music_surgery(src, out, intervals=[{"start": 1.0, "end": 5.0}], separator_runner=demucs_44k)
    assert res["status"] == "auto_fixed"
    arr, out_sr = _read(out)
    assert out_sr == sr
    assert arr.size == sr * 6
    mid = arr[int(2.0 * sr): int(4.0 * sr)]
    assert abs(_peak_hz(mid, sr) - 440.0) < 5.0  # sem câmera lenta / pitch errado (A2)


def test_separator_failure_degrades_to_human_review(tmp_path: Path):
    from picorte.risk_shield.music_surgeon import run_selective_music_surgery

    src = _write_wav(tmp_path / "in.wav", np.zeros(16000 * 4, dtype=np.float32), 16000)

    def broken(slice_wav: Path, out_wav: Path) -> Path:
        raise subprocess.CalledProcessError(1, ["demucs"])

    res = run_selective_music_surgery(src, tmp_path / "o.wav", intervals=[{"start": 0.5, "end": 3.5}],
                                      separator_runner=broken)
    assert res["status"] == "human_review"
    assert res["code"] == "BLOCKED_AUDIO_RETRY"


def test_default_separator_uses_current_python_and_isolated_output_dir(tmp_path: Path, monkeypatch):
    import picorte.risk_shield.music_surgeon as ms

    monkeypatch.setattr(ms, "resolve_cli_binary", lambda name: None)
    seen = []

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        out_root = Path(cmd[cmd.index("-o") + 1])
        slice_path = Path(cmd[-1])
        target = out_root / "htdemucs" / slice_path.stem / "vocals.wav"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(slice_path.name.encode())
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(ms.subprocess, "run", fake_run)
    work = tmp_path / "w"
    work.mkdir()
    a, b = work / "in_0.wav", work / "in_1.wav"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    ms._default_demucs_separator(a, work / "vox_0.wav")
    ms._default_demucs_separator(b, work / "vox_1.wav")
    assert seen[0][0] == sys.executable
    assert (work / "vox_0.wav").read_bytes() == b"in_0.wav"
    assert (work / "vox_1.wav").read_bytes() == b"in_1.wav"
    assert seen[0][seen[0].index("-o") + 1] != seen[1][seen[1].index("-o") + 1]


def test_read_wav_supports_24_bit(tmp_path: Path):
    from picorte.risk_shield.music_surgeon import _read_wav_mono

    p = _write_wav(tmp_path / "x24.wav", np.full(1000, 0.5, dtype=np.float32), 16000, sampwidth=3)
    arr, sr = _read_wav_mono(p)
    assert sr == 16000
    assert abs(float(arr.mean()) - 0.5) < 0.01


def test_non_positive_chunk_size_is_rejected():
    from picorte.risk_shield.music_surgeon import _split_long_intervals

    with pytest.raises(ValueError):
        _split_long_intervals([{"start": 0.0, "end": 10.0}], chunk_max_s=0)


def test_split_covers_the_whole_interval_without_trailing_gap():
    from picorte.risk_shield.music_surgeon import _split_long_intervals

    chunks = _split_long_intervals([{"start": 0.0, "end": 30.05}], chunk_max_s=30.0)
    assert chunks[0]["start"] == 0.0
    assert chunks[-1]["end"] == 30.05
