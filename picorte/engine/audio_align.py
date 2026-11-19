"""Alinhamento de áudio por correlação cruzada FFT (transplante adaptado de clipify/audio_align.py)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from picorte.config import resolve_cli_binary


def load_pcm_mono(media_path: str | Path, sample_rate: int = 16000) -> np.ndarray:
    """Extrai áudio PCM 16-bit mono via FFmpeg multiplataforma."""
    ffmpeg_bin = resolve_cli_binary("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-i",
        str(Path(media_path)),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(int(sample_rate)),
        "-ac",
        "1",
        "-f",
        "s16le",
        "pipe:1",
    ]
    res = subprocess.run(cmd, capture_output=True, check=False)
    if res.returncode != 0 or not res.stdout:
        return np.zeros(0, dtype=np.float32)
    return np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32)


def find_audio_offset(
    ref_samples: np.ndarray,
    target_samples: np.ndarray,
    *,
    sample_rate: int = 16000,
) -> float:
    """Retorna o atraso em segundos de target em relação a ref (positivo = target atrasado)."""
    a = np.asarray(ref_samples, dtype=np.float64)
    b = np.asarray(target_samples, dtype=np.float64)
    if len(a) == 0 or len(b) == 0:
        return 0.0

    a = a - np.mean(a)
    b = b - np.mean(b)
    n = len(a) + len(b) - 1
    nfft = 1 << (n - 1).bit_length()

    fa = np.fft.rfft(a, n=nfft)
    fb = np.fft.rfft(b, n=nfft)
    # Correlação cruzada: R(lag) = sum b[t + lag] * a[t] -> pico positivo quando b está atrasado
    corr = np.fft.irfft(fb * np.conj(fa), n=nfft)

    # Rearranja lags negativos (final do buffer) e positivos (início)
    max_neg = len(a) - 1
    max_pos = len(b) - 1
    pos_part = corr[: max_pos + 1]
    neg_part = corr[nfft - max_neg :]
    full_corr = np.concatenate([neg_part, pos_part])
    lags = np.arange(-max_neg, max_pos + 1)

    idx = int(np.argmax(full_corr))
    return round(float(lags[idx]) / float(sample_rate), 4)


def find_offset_files(ref_path: str | Path, target_path: str | Path, sample_rate: int = 16000) -> float:
    ref = load_pcm_mono(ref_path, sample_rate=sample_rate)
    target = load_pcm_mono(target_path, sample_rate=sample_rate)
    return find_audio_offset(ref, target, sample_rate=sample_rate)
