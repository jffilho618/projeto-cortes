"""Sismógrafo do Chat da Live (Story 3.1): velocidade 1 Hz, vel_zscore e bursts de emotes."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

EMOTE_BURST_RE = re.compile(
    r"(?:k{3,}|ha(?:ha){2,}|lul|omegalul|kekw|pog\w*|clip\w*|mentira|\?{3,}|\b[fF]\b|insan[oa])",
    re.IGNORECASE,
)


def _extract_timestamp_and_text(raw: dict[str, Any]) -> tuple[float, str] | None:
    if not isinstance(raw, dict):
        return None
    t_val = None
    for key in ("t", "offset_seconds", "content_offset_seconds", "timestamp_s", "offset"):
        if key in raw and raw[key] is not None:
            t_val = float(raw[key])
            break
    if t_val is None and "videoOffsetTimeMsec" in raw and raw["videoOffsetTimeMsec"] is not None:
        t_val = float(raw["videoOffsetTimeMsec"]) / 1000.0
    if t_val is None and "time_in_seconds" in raw and raw["time_in_seconds"] is not None:
        t_val = float(raw["time_in_seconds"])
    if t_val is None or not math.isfinite(t_val) or t_val < 0:
        return None

    text = ""
    msg = raw.get("message")
    if isinstance(msg, dict):
        text = str(msg.get("body") or msg.get("text") or "")
    elif isinstance(raw.get("body"), str):
        text = raw["body"]
    elif isinstance(raw.get("text"), str):
        text = raw["text"]
    elif isinstance(raw.get("content"), str):
        text = raw["content"]
    return t_val, text


def parse_chat_log(path_or_data: str | Path | list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    """Lê chat JSON/NDJSON de Twitch, Kick ou YouTube para lista normalizada [{'t': float, 'text': str}]."""
    if isinstance(path_or_data, (str, Path)):
        raw_text = Path(path_or_data).read_text(encoding="utf-8").strip()
        if not raw_text:
            return []
        if "\n" in raw_text and not raw_text.startswith("{") and not raw_text.startswith("["):
            items = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
        else:
            try:
                items = json.loads(raw_text)
            except json.JSONDecodeError:
                items = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
    else:
        items = path_or_data

    if isinstance(items, dict):
        for key in ("comments", "messages", "events", "chat"):
            if isinstance(items.get(key), list):
                items = items[key]
                break
        else:
            items = [items]

    if not isinstance(items, list):
        return []

    parsed: list[dict[str, Any]] = []
    for entry in items:
        res = _extract_timestamp_and_text(entry)
        if res is not None:
            parsed.append({"t": res[0], "text": res[1]})
    parsed.sort(key=lambda x: x["t"])
    return parsed


def _rolling_median_mad(arr: np.ndarray, window: int = 120) -> tuple[np.ndarray, np.ndarray]:
    """Mediana e MAD móveis com padding por reflexão/borda em O(N * log W) rápido para logs longos."""
    n = len(arr)
    if n == 0:
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    w = max(5, min(window, n))
    if w % 2 == 0:
        w = max(5, w - 1)

    half = w // 2
    padded = np.pad(arr, (half, half), mode="edge")
    # sliding_window_view é O(1) em memória e super rápido em NumPy
    windows = np.lib.stride_tricks.sliding_window_view(padded, w)
    medians = np.median(windows, axis=1)
    mads = np.median(np.abs(windows - medians[:, None]), axis=1)
    return medians, mads


def analyze_chat_seismic(
    messages: list[dict[str, Any]],
    *,
    duration_s: float | None = None,
    zscore_threshold: float = 3.5,
    baseline_window_s: int = 120,
    merge_gap_s: float = 4.0,
) -> dict[str, Any]:
    """Calcula vel_zscore 1 Hz, emote_burst e janelas candidatas onde vel_zscore >= zscore_threshold."""
    if not messages and not duration_s:
        return {"duration_s": 0, "per_second": [], "peaks": []}

    max_t = max((float(m["t"]) for m in messages), default=0.0)
    total_secs = int(math.ceil(max(float(duration_s or 0.0), max_t + 1.0, 1.0)))

    counts = np.zeros(total_secs, dtype=np.float64)
    emote_hits = np.zeros(total_secs, dtype=np.float64)
    for m in messages:
        sec = min(total_secs - 1, max(0, int(float(m["t"]))))
        counts[sec] += 1.0
        if EMOTE_BURST_RE.search(str(m.get("text") or "")):
            emote_hits[sec] += 1.0

    # Suavização leve de 3s para evitar picos de 1 mensagem isolada, mantendo resposta em 1Hz
    kernel = np.array([0.25, 0.5, 0.25], dtype=np.float64)
    smooth_counts = np.convolve(counts, kernel, mode="same")

    medians, mads = _rolling_median_mad(counts, window=baseline_window_s)
    # Escala robusta com piso para quando MAD == 0 (baseline estável)
    scale = np.maximum(1.4826 * mads, np.maximum(1.0, 0.35 * medians + 0.5))
    zscores = (smooth_counts - medians) / scale
    emote_burst = np.divide(emote_hits, counts, out=np.zeros_like(counts), where=counts > 0)

    # Identifica blocos contíguos onde zscore >= threshold
    hot_indices = np.flatnonzero(zscores >= float(zscore_threshold))
    peaks: list[dict[str, Any]] = []
    if len(hot_indices) > 0:
        groups: list[list[int]] = [[int(hot_indices[0]), int(hot_indices[0])]]
        for idx in hot_indices[1:]:
            idx_i = int(idx)
            if idx_i - groups[-1][1] <= int(merge_gap_s):
                groups[-1][1] = idx_i
            else:
                groups.append([idx_i, idx_i])

        for s_idx, e_idx in groups:
            peak_z = float(np.max(zscores[s_idx : e_idx + 1]))
            peak_emote = float(np.max(emote_burst[s_idx : e_idx + 1]))
            win_start = max(0.0, float(s_idx) - 6.0)
            win_end = min(float(total_secs), float(e_idx + 1) + 8.0)
            peaks.append(
                {
                    "start": round(win_start, 2),
                    "end": round(win_end, 2),
                    "peak_second": int(s_idx + int(np.argmax(zscores[s_idx : e_idx + 1]))),
                    "vel_zscore": round(peak_z, 3),
                    "emote_burst": round(peak_emote, 3),
                    "msg_count": int(np.sum(counts[s_idx : e_idx + 1])),
                }
            )
        peaks.sort(key=lambda p: (p["vel_zscore"] + 2.0 * p["emote_burst"]), reverse=True)

    per_second = [
        {
            "t": sec,
            "msg_count": int(counts[sec]),
            "vel_zscore": round(float(zscores[sec]), 3),
            "emote_burst": round(float(emote_burst[sec]), 3),
        }
        for sec in range(total_secs)
    ]
    return {"duration_s": total_secs, "per_second": per_second, "peaks": peaks}


def score_chat_window(seismic: dict[str, Any] | None, start: float, end: float) -> float:
    """Converte atividade sísmica de [start, end] para nota S_chat de 0.0 a 10.0."""
    if not seismic or not seismic.get("per_second"):
        return 0.0
    per_second = seismic["per_second"]
    lo = max(0, int(math.floor(start)))
    hi = min(len(per_second), max(lo + 1, int(math.ceil(end))))
    slice_rows = per_second[lo:hi]
    if not slice_rows:
        return 0.0
    max_z = max(float(r["vel_zscore"]) for r in slice_rows)
    mean_emote = sum(float(r["emote_burst"]) for r in slice_rows) / len(slice_rows)
    # Normaliza zscore (3.5 -> ~6.5, >= 6.0 -> ~9.0+) + bônus de emote_burst
    raw = max(0.0, (max_z / 5.5) * 8.0 + mean_emote * 2.5)
    return round(min(10.0, raw), 2)
