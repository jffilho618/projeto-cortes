"""Snap de fronteiras de corte baseado em silêncios e palavras (adaptado de AgriciDaniel/claude-shorts)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from picorte.config import resolve_cli_binary


def load_word_timeline(transcript_path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(transcript_path).read_text(encoding="utf-8"))
    words: list[dict[str, Any]] = []
    if isinstance(data, dict) and isinstance(data.get("words"), list):
        for w in data["words"]:
            if "start" in w and "end" in w:
                words.append({"word": str(w.get("word") or w.get("text") or "").strip(), "start": float(w["start"]), "end": float(w["end"])})
        return words

    for seg in data.get("segments", []) if isinstance(data, dict) else []:
        seg_words = seg.get("words") or []
        if seg_words:
            for w in seg_words:
                if "start" in w and "end" in w:
                    words.append({"word": str(w.get("word") or "").strip(), "start": float(w["start"]), "end": float(w["end"])})
        elif "start" in seg and "end" in seg:
            words.append({"word": str(seg.get("text") or "").strip(), "start": float(seg["start"]), "end": float(seg["end"])})
    return words


def detect_silences(
    video_path: str | Path,
    noise_db: float = -35.0,
    min_dur: float = 0.25,
) -> list[tuple[float, float]]:
    ffmpeg_bin = resolve_cli_binary("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-i",
        str(Path(video_path)),
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_dur}",
        "-f",
        "null",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    silences: list[tuple[float, float]] = []
    cur_start: float | None = None
    for line in res.stderr.splitlines():
        m_s = re.search(r"silence_start:\s*([0-9.]+)", line)
        if m_s:
            cur_start = float(m_s.group(1))
            continue
        m_e = re.search(r"silence_end:\s*([0-9.]+)", line)
        if m_e and cur_start is not None:
            silences.append((cur_start, float(m_e.group(1))))
            cur_start = None
    return silences


def find_nearest_silence(
    silences: list[tuple[float, float]],
    target: float,
    max_snap: float = 1.5,
) -> float:
    best_t = float(target)
    best_dist = float(max_snap)
    for s_start, s_end in silences:
        if s_start <= target <= s_end:
            return float(target)
        for edge in (s_start, s_end):
            dist = abs(edge - target)
            if dist < best_dist:
                best_dist = dist
                best_t = float(edge)
    return best_t


def snap_window_to_words_and_silences(
    start: float,
    end: float,
    *,
    words: list[dict[str, Any]] | None = None,
    silences: list[tuple[float, float]] | None = None,
    duration_s: float | None = None,
    pad: float = 0.08,
) -> tuple[float, float]:
    """Garante que start e end nunca cortem no meio de uma palavra e ajusta para silêncio próximo."""
    s = float(start)
    e = float(end)
    if words:
        for w in words:
            ws = float(w["start"])
            we = float(w["end"])
            if ws < s < we:
                s = min(s, max(0.0, ws - pad))
            if ws < e < we:
                e = max(e, we + pad)

    if silences:
        s_snap = find_nearest_silence(silences, s, max_snap=1.0)
        e_snap = find_nearest_silence(silences, e, max_snap=1.0)
        # Só aplica snap de silêncio se não invadir palavras dentro da janela
        if not words or all(float(w["end"]) <= s_snap or float(w["start"]) >= s_snap for w in words):
            s = s_snap
        if not words or all(float(w["end"]) <= e_snap or float(w["start"]) >= e_snap for w in words):
            e = e_snap

    s = max(0.0, s)
    if duration_s is not None and duration_s > 0:
        e = min(float(duration_s), e)
    if e <= s:
        e = s + 0.5
    return round(s, 3), round(e, 3)


def setup_preroll_start(
    sentences: list[dict[str, Any]],
    cause_s: float,
    *,
    min_back: float = 3.0,
    max_back: float = 8.0,
    max_reach: float = 15.0,
) -> float | None:
    """3.6.4 (AC2): começo da frase do SETUP de uma semente de reação, 3–8 s antes da causa.

    Usa a frase mais antiga que começa em [causa−8, causa−3]; se nenhuma começa ali, o começo da frase
    que cobre causa−3, desde que esteja a no máximo 15 s da causa. Sem frase utilizável → None
    (a janela da semente fica como estava).
    """
    lo, hi = float(cause_s) - float(max_back), float(cause_s) - float(min_back)
    starts = sorted(float(s.get("start") or 0.0) for s in sentences or []
                    if lo <= float(s.get("start") or 0.0) <= hi)
    if starts:
        return starts[0]
    for s in sentences or []:
        st, en = float(s.get("start") or 0.0), float(s.get("end") or 0.0)
        if st <= hi <= en and float(cause_s) - st <= float(max_reach):
            return st
    return None
