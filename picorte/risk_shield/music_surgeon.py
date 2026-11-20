"""Story 4.3 — Cirurgia Seletiva de Música com Demucs na GPU (P1 + A2: remove música sem alterar pitch/speed)."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable
import wave

import numpy as np

from picorte.config import resolve_cli_binary
from picorte.engine.vram_runner import VRAMRunner


def _is_demucs_available() -> bool:
    return importlib.util.find_spec("demucs") is not None or bool(resolve_cli_binary("demucs"))


def _pcm16_copy(path: Path) -> Path:
    """Converte WAV não-PCM (ex.: float32 do Demucs) para PCM 16-bit via ffmpeg, preservando a taxa."""
    out = path.with_name(f"{path.stem}_pcm16.wav")
    ffmpeg_bin = resolve_cli_binary("ffmpeg") or "ffmpeg"
    subprocess.run(
        [ffmpeg_bin, "-y", "-i", str(path), "-c:a", "pcm_s16le", str(out)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return out


def _read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    try:
        wf = wave.open(str(path), "rb")
    except wave.Error:
        return _read_wav_mono(_pcm16_copy(Path(path)))
    with wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if sw == 1:
        arr = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sw == 2:
        arr = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        ints = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        ints = np.where(ints >= 1 << 23, ints - (1 << 24), ints)
        arr = ints.astype(np.float32) / 8388608.0
    elif sw == 4:
        arr = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"WAV com {sw * 8} bits não suportado: {path}")
    if nch > 1:
        arr = arr.reshape(-1, nch).mean(axis=1)
    return arr, sr


def _resample(arr: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    """Reamostra sem mudar duração nem pitch (A2). Passa-baixa simples antes de reduzir a taxa."""
    if src_sr == dst_sr or arr.size == 0:
        return arr
    if src_sr > dst_sr:
        k = int(round(src_sr / dst_sr))
        if k > 1:
            arr = np.convolve(arr, np.ones(k, dtype=np.float32) / k, mode="same")
    n_out = int(round(arr.size * dst_sr / src_sr))
    t_src = np.arange(arr.size, dtype=np.float64) / src_sr
    t_dst = np.arange(n_out, dtype=np.float64) / dst_sr
    return np.interp(t_dst, t_src, arr).astype(np.float32)


def _write_wav_mono(path: Path, samples: np.ndarray, sr: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Peak limiter suave em -1.5 dBTP (~0.841)
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    limit = 0.841  # -1.5 dBTP
    if peak > limit:
        samples = samples * (limit / peak)
    pcm = np.clip(samples * 32767.0, -32768.0, 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _ensure_wav_16k(audio_path: Path, tmp_dir: Path) -> Path:
    if audio_path.suffix.lower() == ".wav":
        return audio_path
    out_wav = tmp_dir / "src_16k.wav"
    ffmpeg_bin = resolve_cli_binary("ffmpeg") or "ffmpeg"
    subprocess.run(
        [ffmpeg_bin, "-y", "-i", str(audio_path), "-ac", "1", "-ar", "16000", str(out_wav)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return out_wav


def detect_music_intervals(
    audio_path: Path | str,
    *,
    min_duration_s: float = 2.5,
    window_s: float = 0.5,
) -> list[dict[str, float]]:
    """Estágio 1 (CPU rápido): detecta janelas contínuas (>= min_duration_s) com energia harmônica/tonal musical."""
    src = Path(audio_path)
    if not src.is_file():
        return []
    with tempfile.TemporaryDirectory(prefix="picorte_mus_") as td:
        wav_path = _ensure_wav_16k(src, Path(td))
        samples, sr = _read_wav_mono(wav_path)

    win_n = max(256, int(round(sr * window_s)))
    if samples.size < win_n:
        return []

    n_wins = samples.size // win_n
    hann = np.hanning(win_n).astype(np.float32)
    freqs = np.fft.rfftfreq(win_n, d=1.0 / sr)
    band_mask = (freqs >= 80.0) & (freqs <= 4000.0)

    is_music_win: list[bool] = []
    for i in range(n_wins):
        chunk = samples[i * win_n : (i + 1) * win_n]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        if rms < 0.03:
            is_music_win.append(False)
            continue
        spec = np.abs(np.fft.rfft(chunk * hann))[band_mask] + 1e-9
        # Razão de tonalidade (picos harmônicos pronunciados vs piso espectral) + estabilidade temporal interna
        geo_mean = float(np.exp(np.mean(np.log(spec))))
        arith_mean = float(np.mean(spec))
        flatness = geo_mean / max(arith_mean, 1e-9)
        top_k = np.sort(spec)[-6:]
        peak_ratio = float(np.mean(top_k) / max(arith_mean, 1e-9))

        # Continuidade interna em sub-blocos (música sustenta energia contínua; fala esparsa tem pausas)
        sub = np.array_split(chunk, 4)
        sub_rms = [float(np.sqrt(np.mean(s ** 2))) for s in sub]
        sustained = min(sub_rms) >= (0.35 * max(sub_rms) + 1e-6) and min(sub_rms) >= 0.025

        is_music_win.append(bool(sustained and (flatness < 0.28 or peak_ratio > 7.5)))

    # Agrupa janelas contíguas tolerando até 1 janela de lacuna (0.5s)
    intervals: list[dict[str, float]] = []
    start_idx: int | None = None
    gap = 0
    for idx, flag in enumerate(is_music_win):
        if flag:
            if start_idx is None:
                start_idx = idx
            gap = 0
        elif start_idx is not None:
            gap += 1
            if gap > 1:
                end_idx = idx - gap + 1
                s_t, e_t = start_idx * window_s, end_idx * window_s
                if (e_t - s_t) >= min_duration_s:
                    intervals.append({"start": round(s_t, 2), "end": round(e_t, 2)})
                start_idx = None
                gap = 0
    if start_idx is not None:
        s_t, e_t = start_idx * window_s, n_wins * window_s
        if (e_t - s_t) >= min_duration_s:
            intervals.append({"start": round(s_t, 2), "end": round(e_t, 2)})
    return intervals


def _default_demucs_separator(slice_wav: Path, out_vocals_wav: Path) -> Path:
    """Executa htdemucs em caminho ASCII seguro (AD-11) e extrai vocals.wav."""
    demucs_bin = resolve_cli_binary("demucs")
    # Pasta exclusiva por chunk: chunks diferentes nunca leem o vocals.wav um do outro.
    out_root = out_vocals_wav.parent / f"_demucs_out_{out_vocals_wav.stem}"
    out_root.mkdir(parents=True, exist_ok=True)
    args = ["--two-stems=vocals", "-n", "htdemucs", "--shifts", "0", "--segment", "6", "-o", str(out_root), str(slice_wav)]
    cmd = [demucs_bin, *args] if demucs_bin else [sys.executable, "-m", "demucs", *args]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    vocals = out_root / "htdemucs" / Path(slice_wav).stem / "vocals.wav"
    if not vocals.is_file():
        raise RuntimeError("Demucs concluiu sem gerar vocals.wav.")
    shutil.copy2(vocals, out_vocals_wav)
    return out_vocals_wav


def _split_long_intervals(intervals: list[dict[str, float]], chunk_max_s: float = 30.0) -> list[dict[str, float]]:
    if not chunk_max_s or chunk_max_s <= 0:
        raise ValueError("chunk_max_s precisa ser maior que zero.")
    out: list[dict[str, float]] = []
    for iv in intervals:
        s, e = float(iv["start"]), float(iv["end"])
        first = len(out)
        while e - s > chunk_max_s:
            out.append({"start": round(s, 3), "end": round(s + chunk_max_s, 3)})
            s += chunk_max_s
        if e - s > 0:
            # Sobra curta (< 1s) é anexada ao chunk anterior: nenhum pedaço de música fica sem cirurgia.
            if e - s < 1.0 and len(out) > first:
                out[-1]["end"] = round(e, 3)
            else:
                out.append({"start": round(s, 3), "end": round(e, 3)})
    return out


def run_selective_music_surgery(
    audio_path: Path | str,
    output_path: Path | str,
    *,
    intervals: list[dict[str, float]] | None = None,
    vram_runner: VRAMRunner | None = None,
    separator_runner: Callable[[Path, Path], Path] | None = None,
    cache_dir: Path | str | None = None,
    crossfade_ms: int = 150,
    chunk_max_s: float = 30.0,
) -> dict[str, Any]:
    """Estágio 2 (GPU serial via VRAMRunner): aplica Demucs SOMENTE nas janelas musicais com crossfade 150ms."""
    src = Path(audio_path)
    out = Path(output_path)
    detected = intervals if intervals is not None else detect_music_intervals(src)
    if not detected:
        return {
            "gate": "music_surgeon",
            "status": "pass",
            "surgery_applied": False,
            "cache_hit": False,
            "intervals": [],
            "audio_path": str(src),
        }

    if separator_runner is None and not _is_demucs_available():
        return {
            "gate": "music_surgeon",
            "status": "human_review",
            "code": "NEEDS_HUMAN_AUDIO_CHECK",
            "surgery_applied": False,
            "cache_hit": False,
            "intervals": detected,
            "reason": "Música licenciada detectada, mas Demucs não está instalado neste ambiente.",
            "audio_path": str(src),
        }

    chunks = _split_long_intervals(detected, chunk_max_s=chunk_max_s)
    runner = vram_runner or VRAMRunner()
    sep_fn = separator_runner or _default_demucs_separator
    c_dir = Path(cache_dir) if cache_dir else None
    if c_dir:
        c_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="picorte_surg_") as td:
        tmp = Path(td)
        wav_src = _ensure_wav_16k(src, tmp)
        base_samples, sr = _read_wav_mono(wav_src)
        result_samples = base_samples.copy()
        n_total = result_samples.size
        fade_n = max(16, int(round(sr * (crossfade_ms / 1000.0))))

        all_cache_hits = True
        low_snr_warnings: list[str] = []

        for idx, iv in enumerate(chunks):
            s_i = max(0, min(n_total, int(round(iv["start"] * sr))))
            e_i = max(s_i, min(n_total, int(round(iv["end"] * sr))))
            if e_i - s_i < 160:
                continue
            seg_arr = base_samples[s_i:e_i]
            seg_hash = hashlib.sha256(seg_arr.tobytes()).hexdigest()[:16]
            cached_vox = (c_dir / f"vox_{seg_hash}.wav") if c_dir else None

            if cached_vox is not None and cached_vox.is_file():
                vox_arr, vox_sr = _read_wav_mono(cached_vox)
                vox_arr = _resample(vox_arr, vox_sr, sr)
            else:
                all_cache_hits = False
                slice_in = _write_wav_mono(tmp / f"in_{idx}.wav", seg_arr, sr)
                vox_out = tmp / f"vox_{idx}.wav"
                try:
                    produced = runner.run_stage("demucs_htdemucs", lambda si=slice_in, vo=vox_out: sep_fn(si, vo))
                except (RuntimeError, subprocess.CalledProcessError, OSError, ValueError) as exc:
                    return {
                        "gate": "music_surgeon",
                        "status": "human_review",
                        "code": "BLOCKED_AUDIO_RETRY",
                        "surgery_applied": False,
                        "intervals": detected,
                        "reason": f"Falha ao executar Demucs ({exc})",
                        "audio_path": str(src),
                    }
                vox_arr, vox_sr = _read_wav_mono(Path(produced))
                # htdemucs devolve 44,1 kHz: reamostra para a taxa do trecho (nunca mistura taxas — A2).
                vox_arr = _resample(vox_arr, vox_sr, sr)
                if cached_vox is not None:
                    _write_wav_mono(cached_vox, vox_arr, sr)

            # Ajusta comprimento do stem vocal ao slice original
            seg_len = e_i - s_i
            if vox_arr.size < seg_len:
                vox_arr = np.pad(vox_arr, (0, seg_len - vox_arr.size))
            elif vox_arr.size > seg_len:
                vox_arr = vox_arr[:seg_len]

            # Validação de qualidade vocal pós-Demucs
            orig_rms = float(np.sqrt(np.mean(seg_arr ** 2))) + 1e-6
            vox_rms = float(np.sqrt(np.mean(vox_arr ** 2)))
            if vox_rms < orig_rms * 0.04:
                low_snr_warnings.append(f"Trecho {iv['start']:.1f}-{iv['end']:.1f}s ficou quase mudo após Demucs.")

            # Crossfade equal-power nas bordas (150ms)
            cf = min(fade_n, seg_len // 4)
            blended = vox_arr.copy()
            if cf > 1:
                t_lin = np.linspace(0.0, np.pi / 2.0, cf, dtype=np.float32)
                fade_in = np.sin(t_lin)
                fade_out = np.cos(t_lin)
                blended[:cf] = seg_arr[:cf] * fade_out + vox_arr[:cf] * fade_in
                blended[-cf:] = vox_arr[-cf:] * fade_out + seg_arr[-cf:] * fade_in

            result_samples[s_i:e_i] = blended

        _write_wav_mono(out, result_samples, sr)

    status = "human_review" if low_snr_warnings else "auto_fixed"
    return {
        "gate": "music_surgeon",
        "status": status,
        "surgery_applied": True,
        "cache_hit": all_cache_hits,
        "intervals": detected,
        "chunks_processed": len(chunks),
        "warnings": low_snr_warnings,
        "audio_path": str(out),
    }
