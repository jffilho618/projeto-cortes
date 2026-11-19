from __future__ import annotations

import subprocess
from types import SimpleNamespace

import numpy as np
import pytest

from picorte.config import resolve_cli_binary


def test_transcribe_media_bypasses_pyav_metadata_errors_with_ffmpeg_pcm(tmp_path):
    import download_and_transcribe as dt

    audio_path = tmp_path / "sample.wav"
    ffmpeg = resolve_cli_binary("ffmpeg") or "ffmpeg"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-ar", "16000", "-ac", "1",
            str(audio_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    class _PyAVRejectingModel:
        def transcribe(self, audio_input, **kwargs):
            if not isinstance(audio_input, np.ndarray):
                raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")
            assert audio_input.dtype == np.float32
            assert audio_input.ndim == 1
            assert len(audio_input) > 16000
            seg = SimpleNamespace(
                start=0.0,
                end=1.0,
                text="teste ok",
                words=[SimpleNamespace(word="teste", start=0.0, end=0.5)],
            )
            info = SimpleNamespace(language="pt", language_probability=0.99, duration=2.0)
            return iter([seg]), info

    segs, words, lang, dur = dt._transcribe_media(_PyAVRejectingModel(), audio_path)
    assert lang == "pt"
    assert dur == pytest.approx(2.0)
    assert len(segs) == 1
    assert words[0]["word"] == "teste"


def test_cuda_missing_cublas_falls_back_cleanly_to_cpu(monkeypatch, tmp_path):
    import download_and_transcribe as dt
    import picorte.engine.cuda as cuda_mod

    monkeypatch.setattr(cuda_mod, "has_cuda_runtime_libraries", lambda: False)
    calls = []

    class _FakeWhisperModel:
        def __init__(self, size, device="cpu", compute_type="int8"):
            calls.append((size, device, compute_type))
            self.device = device

        def transcribe(self, audio_input, **kwargs):
            if self.device != "cpu":
                raise RuntimeError("Library libcublas.so.12 is not found or cannot be loaded")
            seg = SimpleNamespace(start=0.0, end=1.0, text="cpu ok", words=[])
            info = SimpleNamespace(language="pt", language_probability=0.9, duration=1.0)
            return iter([seg]), info

    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", SimpleNamespace(WhisperModel=_FakeWhisperModel))
    model = dt._load_model("small", "cuda", "int8")
    assert calls == [("small", "cpu", "int8")]

    # E mesmo se a falha acontecer só dentro do transcribe/encode em runtime, faz fallback para CPU
    cuda_model = _FakeWhisperModel("small", device="cuda", compute_type="int8")
    segs, words, lang, dur = dt._transcribe_media(
        cuda_model,
        tmp_path / "missing.wav",
        model_size="small",
        device="cuda",
    )
    assert lang == "pt"
    assert segs[0]["text"] == "cpu ok"

