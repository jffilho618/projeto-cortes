"""Prosódia Avançada em CPU + Hook Opcional YAMNet/PANNs (Épico 3.5 — Story 3.5.4).

Detecta:
- Riso contagiante pulsado (modulação de envelope vocal em 3–6 Hz, 100% CPU);
- Assinatura de Susto (silêncio >2s seguido de spike >18 dB em <300ms);
- Anomalias de taxa de fala (2x rápido no pânico, 2x lento na ênfase séria);
- Eventos acústicos não-verbais via YAMNet/PANNs opcional (fallback limpo em CPU).
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np


def detect_laugh_rhythm_cpu(samples: np.ndarray, *, sample_rate: int = 16000) -> float:
    """Mede proporção de energia modulada na banda rítmica de riso (3–6 Hz) em 0..1."""
    arr = np.asarray(samples, dtype=np.float32).ravel()
    if arr.size < sample_rate // 2:
        return 0.0
    # Envelope em janelas de 25ms (40 Hz de taxa de amostragem do envelope)
    hop = max(1, int(sample_rate * 0.025))
    n_frames = arr.size // hop
    if n_frames < 16:
        return 0.0
    framed = arr[: n_frames * hop].reshape((n_frames, hop))
    env = np.sqrt(np.mean(framed * framed, axis=1) + 1e-12)
    env_centered = env - float(np.mean(env))
    total_energy = float(np.sum(env_centered * env_centered))
    if total_energy <= 1e-10:
        return 0.0

    env_sr = float(sample_rate) / float(hop)
    spectrum = np.abs(np.fft.rfft(env_centered)) ** 2
    freqs = np.fft.rfftfreq(len(env_centered), d=1.0 / env_sr)
    valid_mask = freqs >= 0.5
    band_mask = (freqs >= 3.0) & (freqs <= 6.0)
    total_ac = float(np.sum(spectrum[valid_mask]))
    if total_ac <= 1e-12:
        return 0.0
    band_power = float(np.sum(spectrum[band_mask]))
    return round(min(1.0, max(0.0, band_power / total_ac)), 3)


def detect_jumpscare_spike(
    samples: np.ndarray,
    *,
    sample_rate: int = 16000,
    silence_sec: float = 2.0,
    spike_db: float = 18.0,
    rise_ms: float = 300.0,
) -> dict[str, Any]:
    """Detecta silêncio tenso (>= silence_sec) quebrado por spike >= spike_db em <= rise_ms."""
    arr = np.asarray(samples, dtype=np.float32).ravel()
    hop = max(1, int(sample_rate * 0.05))  # 50ms por bin
    n_bins = arr.size // hop
    silence_bins = max(4, int(round(silence_sec / 0.05)))
    rise_bins = max(1, int(round((rise_ms / 1000.0) / 0.05)))
    if n_bins <= silence_bins + rise_bins:
        return {"detected": False, "jump_db": 0.0, "spike_time_s": None}

    framed = arr[: n_bins * hop].reshape((n_bins, hop))
    rms = np.sqrt(np.mean(framed * framed, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms + 1e-12)

    best_jump = 0.0
    best_idx: int | None = None
    for i in range(silence_bins, n_bins):
        prev_window = db[i - silence_bins : i]
        # Janela anterior precisa ser estável e relativamente silenciosa
        if float(np.std(prev_window)) > 6.0:
            continue
        base_db = float(np.median(prev_window))
        local_slice = db[i : min(n_bins, i + rise_bins)]
        peak_offset = int(np.argmax(local_slice))
        local_peak = float(local_slice[peak_offset])
        jump = local_peak - base_db
        if jump > best_jump:
            best_jump = jump
            best_idx = i + peak_offset

    detected = best_idx is not None and best_jump >= float(spike_db)
    return {
        "detected": bool(detected),
        "jump_db": round(float(best_jump), 2),
        "spike_time_s": round(best_idx * 0.05, 2) if detected and best_idx is not None else None,
    }


def compute_speech_rate_anomalies(
    sentences: list[dict[str, Any]],
    *,
    fast_ratio: float = 1.85,
    slow_ratio: float = 0.55,
) -> dict[int, dict[str, Any]]:
    """Detecta sentenças com aceleração súbita (pânico/caos) ou desaceleração (ênfase séria)."""
    rates: list[tuple[int, float]] = []
    for idx, sent in enumerate(sentences or []):
        dur = max(0.2, float(sent.get("end") or 0.0) - float(sent.get("start") or 0.0))
        words = len(str(sent.get("text") or "").split())
        if words > 0:
            rates.append((idx, words / dur))
    if not rates:
        return {}
    median_wps = float(np.median([r for _, r in rates]))
    if median_wps <= 0.1:
        return {}

    anomalies: dict[int, dict[str, Any]] = {}
    for idx, wps in rates:
        ratio = wps / median_wps
        if ratio >= float(fast_ratio):
            anomalies[idx] = {"kind": "fast_panic", "wps": round(wps, 2), "ratio": round(ratio, 2)}
        elif ratio <= float(slow_ratio):
            anomalies[idx] = {"kind": "slow_emphasis", "wps": round(wps, 2), "ratio": round(ratio, 2)}
    return anomalies


def detect_nonverbal_audio_events(
    samples: np.ndarray,
    *,
    sample_rate: int = 16000,
    yamnet_runner: Callable[[np.ndarray, int], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Combina detectores de prosódia em CPU com hook opcional YAMNet/PANNs."""
    laugh_score = detect_laugh_rhythm_cpu(samples, sample_rate=sample_rate)
    jumpscare = detect_jumpscare_spike(samples, sample_rate=sample_rate)

    yamnet_events: list[dict[str, Any]] = []
    yamnet_available = False
    if yamnet_runner is not None:
        try:
            yamnet_events = list(yamnet_runner(samples, sample_rate) or [])
            yamnet_available = True
        except Exception:
            yamnet_events = []
            yamnet_available = False

    return {
        "laugh_rhythm_score": laugh_score,
        "jumpscare": jumpscare,
        "yamnet_available": yamnet_available,
        "yamnet_events": yamnet_events,
    }


LAUGH_MIN = 0.35
PROSODY_BONUS = {"laugh": 0.6, "jumpscare": 0.8, "fast_panic": 0.3}


def _ffmpeg_window(audio_path: Any, start: float, end: float, sample_rate: int = 16000) -> np.ndarray:
    import subprocess

    from picorte.config import resolve_cli_binary

    proc = subprocess.run(
        [resolve_cli_binary("ffmpeg") or "ffmpeg", "-v", "error", "-ss", f"{max(0.0, start):.3f}",
         "-t", f"{max(0.1, end - start):.3f}", "-i", str(audio_path), "-vn", "-ac", "1",
         "-ar", str(sample_rate), "-f", "f32le", "-"],
        capture_output=True, check=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.float32)


def attach_prosody_evidence(
    candidates: list[dict[str, Any]],
    audio_path: Any,
    sentences: list[dict[str, Any]] | None,
    *,
    limit: int = 40,
    decoder: Callable[[Any, float, float], np.ndarray] | None = None,
    sample_rate: int = 16000,
) -> list[dict[str, Any]]:
    """Liga a prosódia (3.5.4) à descoberta: riso 3–6 Hz, susto e ritmo de fala nos `limit` melhores candidatos.

    Grava `evidence.laugh`, `evidence.jumpscare_db`, `evidence.speech_rate` e soma um bônus modesto em
    `overall` (registrado em `score_parts.prosody_bonus`). Falha ao decodificar um trecho não derruba nada.
    """
    out = [dict(c, evidence=dict(c.get("evidence") or {}), score_parts=dict(c.get("score_parts") or {}))
           for c in candidates]
    decode = decoder or (lambda p, s, e: _ffmpeg_window(p, s, e, sample_rate))
    anomalies = compute_speech_rate_anomalies(sentences or [])
    sent_list = list(sentences or [])
    ranked = sorted(range(len(out)), key=lambda i: -float(out[i].get("overall") or 0.0))[: max(0, int(limit))]
    for i in ranked:
        cand = out[i]
        s, e = float(cand.get("start") or 0.0), float(cand.get("end") or 0.0)
        try:
            samples = decode(audio_path, s, e)
        except Exception:
            continue
        laugh = detect_laugh_rhythm_cpu(samples, sample_rate=sample_rate)
        scare = detect_jumpscare_spike(samples, sample_rate=sample_rate)
        rate = None
        for idx, info in anomalies.items():
            sent = sent_list[idx]
            if float(sent.get("end") or 0.0) > s and float(sent.get("start") or 0.0) < e:
                if info["kind"] == "fast_panic" or rate is None:
                    rate = info["kind"]
        bonus = 0.0
        if laugh >= LAUGH_MIN:
            bonus += PROSODY_BONUS["laugh"]
        if scare["detected"]:
            bonus += PROSODY_BONUS["jumpscare"]
        if rate == "fast_panic":
            bonus += PROSODY_BONUS["fast_panic"]
        cand["evidence"].update({
            "laugh": laugh,
            "jumpscare_db": float(scare["jump_db"]) if scare["detected"] else 0.0,
            "speech_rate": rate,
        })
        if bonus:
            cand["score_parts"]["prosody_bonus"] = round(bonus, 2)
            cand["overall"] = round(min(10.0, float(cand.get("overall") or 0.0) + bonus), 2)
    return out


LAUGH_WINDOW_S = 1.5
LAUGH_STEP_S = 0.5


def extend_end_past_laugh(
    segments: list[dict[str, Any]],
    audio_path: Any,
    *,
    max_len: float | None = None,
    source_duration: float | None = None,
    decoder: Callable[[Any, float, float], np.ndarray] | None = None,
    sample_rate: int = 16000,
    max_extra: float = 6.0,
) -> list[dict[str, Any]]:
    """3.6.4 (AC3): o corte nunca termina no meio de um riso.

    Mede o riso (3–6 Hz) em janelas de 1,5 s com passo de 0,5 s de `end−1` até `end+max_extra`. Se o
    riso está ativo no fim, o fim avança até o riso acabar (+1 s), respeitando `max_len`, a duração da
    fonte e `max_extra`. Sem áudio ou com erro de decodificação, o corte fica como está.
    """
    decode = decoder or (lambda p, s, e: _ffmpeg_window(p, s, e, sample_rate))
    out = [dict(seg, evidence=dict(seg.get("evidence") or {})) for seg in segments or []]
    for seg in out:
        start, end = float(seg.get("start") or 0.0), float(seg.get("end") or 0.0)
        if end <= start:
            continue
        limit = end + float(max_extra)
        if max_len:
            limit = min(limit, start + float(max_len))
        if source_duration and source_duration > 0:
            limit = min(limit, float(source_duration))
        if limit <= end:
            continue
        t0 = max(0.0, end - 1.0)
        try:
            samples = np.asarray(decode(audio_path, t0, limit + LAUGH_WINDOW_S), dtype=np.float32).ravel()
        except Exception:
            continue
        win, step = int(LAUGH_WINDOW_S * sample_rate), int(LAUGH_STEP_S * sample_rate)
        last_laugh_start = None
        k = 0
        while k * step + win <= samples.size:
            a = t0 + k * LAUGH_STEP_S
            if a > limit:
                break
            if detect_laugh_rhythm_cpu(samples[k * step: k * step + win], sample_rate=sample_rate) < LAUGH_MIN:
                break
            last_laugh_start = a
            k += 1
        if last_laugh_start is None:
            continue  # sem riso cruzando o fim
        new_end = min(limit, last_laugh_start + 1.0 + 1.0)  # fim do riso ≈ meio da última janela; +1 s
        if new_end > end:
            seg["evidence"]["end_after_laugh_s"] = round(new_end - end, 2)
            seg["end"] = round(new_end, 2)
            seg["duration"] = round(new_end - start, 2)
    return out
