"""Sismógrafo do Chat da Live (Story 3.1) — versão 2 (Story 3.6.2).

v1: velocidade 1 Hz, vel_zscore e bursts de emotes; o pico virava a janela [pico−6, pico+8].
v2 (medição própria de 2026-11-21: o chat reage ~25–35 s depois do lance):
- anti-ruído: comandos, links e textão copiado repetido (bots) saem antes de contar;
- atraso calibrado por VOD (correlação cruzada saltos de áudio → chat, 15–45 s; fraca → 30 s);
- âncora da causa: o salto de áudio mais forte em [t−d−15, t−d+15] ∩ [t−45, t−15];
- tipo de reação por pico (riso, hype, susto, cringe, luto, amor, pedido de corte) e concordância;
- score_chat_window credita o chat que chega DEPOIS do trecho, deslocado pelo atraso.
"""
from __future__ import annotations

from collections import Counter
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

SEISMIC_VERSION = 2
DEFAULT_DELAY_S = 30            # medido em 2026-11-21 no VOD x50ONQrBPRM (literatura: 20–27 s)
DELAY_MIN_S, DELAY_MAX_S = 15, 45
MIN_CHAT_PER_MIN = 20.0         # abaixo disso o Sismógrafo desliga (AC5)

EMOTE_BURST_RE = re.compile(
    r"(?:k{3,}|ha(?:ha){2,}|lul|omegalul|kekw|pog\w*|clip\w*|mentira|\?{3,}|\b[fF]\b|insan[oa])",
    re.IGNORECASE,
)

# ------------------------------------------------------------------------------------ anti-ruído

_COMMAND_RE = re.compile(r"^\s*!\w+")
_LINK_RE = re.compile(r"https?://|www\.|\.com(\.br)?/|\.gg/|bit\.ly", re.IGNORECASE)


def is_noise(text: Any) -> bool:
    """Comando de bot (!sorteio, !pix), link ou mensagem vazia — não é reação ao lance."""
    t = str(text or "").strip()
    return not t or bool(_COMMAND_RE.match(t)) or bool(_LINK_RE.search(t))


def drop_spam(messages: list[dict[str, Any]], *, min_len: int = 20, repeats: int = 3,
              window_s: float = 30.0) -> tuple[list[dict[str, Any]], int]:
    """Remove flood: o MESMO autor repetindo o mesmo textão 3+ vezes em 30 s.

    Sem autor nada sai por repetição: no chat real (2026-11-21) o "textão repetido" era coro da torcida,
    "kkkkkkkkkkkkkkkkkkkk" e emotes em texto — concordância, não bot. Propaganda de bot cai no is_noise (links).
    """
    times: dict[tuple[str, str], list[float]] = {}
    for m in messages:
        author = m.get("author")
        key = str(m.get("text") or "").strip().lower()
        if author and len(key) >= min_len:
            times.setdefault((str(author), key), []).append(float(m["t"]))
    spam = set()
    for key, ts in times.items():
        ts.sort()
        for i in range(len(ts) - repeats + 1):
            if ts[i + repeats - 1] - ts[i] <= window_s:
                spam.add(key)
                break
    kept = [m for m in messages
            if (str(m.get("author") or ""), str(m.get("text") or "").strip().lower()) not in spam]
    return kept, len(messages) - len(kept)


# ------------------------------------------------------------------------------------ tipo de reação

REACTION_LEXICON: dict[str, re.Pattern] = {
    "pedido_corte": re.compile(r"\bclip(a|ar|em|aram|ou)?\b|clip it|corta essa|vira corte|isso (é|e) corte"
                               r"|manda (pro|no) tiktok", re.IGNORECASE),
    "riso": re.compile(r"k{3,}|(?:ha){2,}|(?:he){3,}|rs(?:rs)+|😂|🤣|kekw|\blul\b|omegalul", re.IGNORECASE),
    "hype": re.compile(r"\bpog\w*|insan[oa]|absurd[oa]|que isso|monstr[oa]|🔥|\bgg\b|brab[oa]", re.IGNORECASE),
    "susto": re.compile(r"socorro|susto|assust|😱|😨|jumpscare", re.IGNORECASE),
    "cringe": re.compile(r"vergonha|cringe|constrang|\bmico\b|😬|🤦", re.IGNORECASE),
    "luto": re.compile(r"^\s*f+\s*$|\brip\b|😭|😢|\bluto\b", re.IGNORECASE),
    "amor": re.compile(r"❤|<3|😍|🥰|\blind[oa]\b|\bfof[oa]\b", re.IGNORECASE),
}
CLIP_REQUEST_MIN = 2


def classify_reaction(texts: list[str]) -> dict[str, Any]:
    """Tipo de reação dominante num grupo de mensagens; pedido explícito de corte vence com ≥ 2 ocorrências."""
    counts = {k: 0 for k in REACTION_LEXICON}
    for t in texts or []:
        for kind, rx in REACTION_LEXICON.items():
            if rx.search(str(t or "")):
                counts[kind] += 1
    if counts["pedido_corte"] >= CLIP_REQUEST_MIN:
        return {"tipo": "pedido_corte", "contagens": counts}
    others = {k: v for k, v in counts.items() if k != "pedido_corte"}
    kind, best = max(others.items(), key=lambda kv: kv[1])
    if best <= 0 or best < 0.1 * max(1, len(texts or [])):
        return {"tipo": None, "contagens": counts}
    return {"tipo": kind, "contagens": counts}


def _norm_token(text: str) -> str:
    t = re.sub(r"(.)\1{2,}", r"\1\1", str(text or "").strip().lower())
    return re.sub(r"[^\w❤😂🤣🔥😱😭😬]+", "", t)


def _peak_texture(msgs: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [str(m.get("text") or "") for m in msgs]
    n = max(1, len(texts))
    short_frac = sum(1 for t in texts if len(t.strip()) <= 15) / n
    tokens = Counter(_norm_token(t) for t in texts if _norm_token(t))
    agreement = (tokens.most_common(1)[0][1] / n) if tokens else 0.0
    authors_set = {m.get("author") for m in msgs if m.get("author")}
    reaction = classify_reaction(texts)
    return {"short_frac": round(short_frac, 3), "agreement": round(agreement, 3),
            "authors": len(authors_set) if authors_set else None,
            "reaction_type": reaction["tipo"], "reaction_counts": reaction["contagens"]}


def _peak_weight(z: float, tex: dict[str, Any]) -> float:
    w = z * (1.0 + 0.5 * tex["short_frac"] + 0.5 * tex["agreement"]
             + (0.3 if (tex.get("authors") or 0) >= 10 else 0.0))
    return w + (3.0 if tex.get("reaction_type") == "pedido_corte" else 0.0)


# ------------------------------------------------------------------------------------ atraso e causa

SILENCE_DB = -70.0


def audio_jump_series(rms_db: Any, baseline_db: Any = None, *, cap_db: float = 20.0) -> np.ndarray:
    """Força de "lance" por segundo a partir do volume (dB): subida brusca + quanto está acima do normal.

    A volta de um silêncio digital (≤ −70 dB, ex.: música removida) não conta como lance.
    """
    rms = np.asarray(rms_db, dtype=np.float64)
    if rms.size == 0:
        return np.zeros(0)
    base = np.asarray(baseline_db, dtype=np.float64) if baseline_db is not None else np.full_like(rms, np.median(rms))
    prev = np.concatenate([[rms[0]], rms[:-1]])
    rise = np.clip(rms - prev, 0.0, cap_db)
    above = 0.5 * np.clip(rms - base, 0.0, cap_db)
    jump = rise + above
    jump[(prev <= SILENCE_DB) | (rms <= SILENCE_DB)] = 0.0
    return jump


def calibrate_delay(chat_counts: Any, audio_jump: Any, *, lag_min: int = DELAY_MIN_S, lag_max: int = DELAY_MAX_S,
                    ref_max: int = 120, min_strength: float = 3.0, default: int = DEFAULT_DELAY_S) -> dict[str, Any]:
    """Atraso do chat por VOD: lag (15–45 s) de maior correlação áudio→chat; força = z contra lags 0–120 s."""
    chat = np.asarray(chat_counts, dtype=np.float64)
    audio = np.asarray(audio_jump, dtype=np.float64)
    n = min(len(chat), len(audio))
    fallback = {"delay_s": int(default), "strength": 0.0, "corr": 0.0, "confiavel": False}
    if n < ref_max * 3:
        return fallback
    chat, audio = chat[:n], audio[:n]
    corrs = []
    for lag in range(0, ref_max + 1):
        a, c = audio[: n - lag], chat[lag:n]
        if a.std() == 0 or c.std() == 0:
            corrs.append(0.0)
        else:
            corrs.append(float(np.corrcoef(a, c)[0, 1]))
    corrs_arr = np.asarray(corrs)
    window = corrs_arr[lag_min: lag_max + 1]
    best = int(np.argmax(window)) + lag_min
    sd = float(corrs_arr.std())
    strength = (float(corrs_arr[best]) - float(corrs_arr.mean())) / sd if sd > 0 else 0.0
    out = {"delay_s": best, "strength": round(strength, 2), "corr": round(float(corrs_arr[best]), 4),
           "confiavel": bool(strength >= min_strength and corrs_arr[best] > 0)}
    if not out["confiavel"]:
        out["delay_s"] = int(default)
    return out


def anchor_cause(peak_second: int, audio_jump: Any, delay_s: float = DEFAULT_DELAY_S) -> tuple[int, float]:
    """Segundo do lance que causou o pico: o maior salto de áudio em [t−d−15, t−d+15] ∩ [t−45, t−15]."""
    t, d = int(peak_second), int(round(delay_s))
    fallback = (max(0, t - d), 0.0)
    if audio_jump is None:
        return fallback
    jump = np.asarray(audio_jump, dtype=np.float64)
    lo = max(0, t - DELAY_MAX_S, t - d - 15)
    hi = min(len(jump) - 1, t - DELAY_MIN_S, t - d + 15)
    if jump.size == 0 or hi < lo:
        return fallback
    seg = jump[lo: hi + 1]
    if float(seg.max()) <= 0.0:
        return fallback
    i = int(np.argmax(seg))
    return lo + i, float(seg[i])


# ------------------------------------------------------------------------------------ leitura do chat

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
    """Lê chat JSON/NDJSON de Twitch, Kick ou YouTube para [{'t': float, 'text': str, 'author'?: str}]."""
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
            rec = {"t": res[0], "text": res[1]}
            author = entry.get("author") if isinstance(entry, dict) else None
            if author:
                rec["author"] = str(author)
            parsed.append(rec)
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
    windows = np.lib.stride_tricks.sliding_window_view(padded, w)
    medians = np.median(windows, axis=1)
    mads = np.median(np.abs(windows - medians[:, None]), axis=1)
    return medians, mads


# ------------------------------------------------------------------------------------ análise

def analyze_chat_seismic(
    messages: list[dict[str, Any]],
    *,
    duration_s: float | None = None,
    zscore_threshold: float = 3.5,
    baseline_window_s: int = 120,
    merge_gap_s: float = 4.0,
    audio_jump: Any = None,
    delay_s: float | None = None,
) -> dict[str, Any]:
    """Sismógrafo v2: limpa ruído, calibra o atraso, acha picos e ancora cada pico no lance que o causou."""
    if not messages and not duration_s:
        return {"version": SEISMIC_VERSION, "duration_s": 0, "per_second": [], "peaks": [],
                "delay_s": DEFAULT_DELAY_S, "noise_dropped": 0}

    raw_n = len(messages or [])
    clean = [m for m in messages or [] if not is_noise(m.get("text"))]
    clean, _spam = drop_spam(clean)
    noise_dropped = raw_n - len(clean)

    max_t = max((float(m["t"]) for m in clean), default=0.0)
    total_secs = int(math.ceil(max(float(duration_s or 0.0), max_t + 1.0, 1.0)))

    counts = np.zeros(total_secs, dtype=np.float64)
    emote_hits = np.zeros(total_secs, dtype=np.float64)
    by_sec: dict[int, list[dict[str, Any]]] = {}
    for m in clean:
        sec = min(total_secs - 1, max(0, int(float(m["t"]))))
        counts[sec] += 1.0
        by_sec.setdefault(sec, []).append(m)
        if EMOTE_BURST_RE.search(str(m.get("text") or "")):
            emote_hits[sec] += 1.0

    kernel = np.array([0.25, 0.5, 0.25], dtype=np.float64)
    smooth_counts = np.convolve(counts, kernel, mode="same")
    medians, mads = _rolling_median_mad(counts, window=baseline_window_s)
    scale = np.maximum(1.4826 * mads, np.maximum(1.0, 0.35 * medians + 0.5))
    zscores = (smooth_counts - medians) / scale
    emote_burst = np.divide(emote_hits, counts, out=np.zeros_like(counts), where=counts > 0)

    jump = np.asarray(audio_jump, dtype=np.float64) if audio_jump is not None else None
    if delay_s is not None:
        cal = {"delay_s": int(round(delay_s)), "strength": None, "corr": None, "confiavel": None, "fonte": "fixo"}
    elif jump is not None and jump.size:
        cal = {**calibrate_delay(counts, jump), "fonte": "calibrado"}
    else:
        cal = {"delay_s": DEFAULT_DELAY_S, "strength": 0.0, "corr": 0.0, "confiavel": False, "fonte": "sem_audio"}
    d = int(cal["delay_s"])

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
            peak_z = float(np.max(zscores[s_idx: e_idx + 1]))
            peak_emote = float(np.max(emote_burst[s_idx: e_idx + 1]))
            peak_sec = int(s_idx + int(np.argmax(zscores[s_idx: e_idx + 1])))
            group_msgs = [m for sec in range(s_idx, e_idx + 1) for m in by_sec.get(sec, [])]
            tex = _peak_texture(group_msgs)
            cause, cause_strength = anchor_cause(peak_sec, jump, d)
            peaks.append({
                # janela da semente: começa no lance que causou o pico (antes: [pico−6, pico+8])
                "start": round(max(0.0, float(cause) - 8.0), 2),
                "end": round(min(float(total_secs), float(cause) + 14.0), 2),
                "chat_start": round(max(0.0, float(s_idx) - 6.0), 2),
                "chat_end": round(min(float(total_secs), float(e_idx + 1) + 8.0), 2),
                "peak_second": peak_sec,
                "cause_second": int(cause),
                "cause_strength": round(cause_strength, 3),
                "delay_s": d,
                "vel_zscore": round(peak_z, 3),
                "emote_burst": round(peak_emote, 3),
                "msg_count": int(np.sum(counts[s_idx: e_idx + 1])),
                **tex,
                "weight": round(_peak_weight(peak_z, tex), 3),
            })
        peaks.sort(key=lambda p: p["weight"], reverse=True)

    per_second = [
        {
            "t": sec,
            "msg_count": int(counts[sec]),
            "vel_zscore": round(float(zscores[sec]), 3),
            "emote_burst": round(float(emote_burst[sec]), 3),
        }
        for sec in range(total_secs)
    ]
    return {
        "version": SEISMIC_VERSION,
        "duration_s": total_secs,
        "per_second": per_second,
        "peaks": peaks,
        "delay_s": d,
        "delay": cal,
        "noise_dropped": int(noise_dropped),
        "has_authors": any(m.get("author") for m in clean),
    }


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def score_chat_window(seismic: dict[str, Any] | None, start: float, end: float) -> float:
    """Nota S_chat de 0 a 10 para o trecho [start, end].

    v2: credita o chat que chega DEPOIS do trecho, em [start + d − 10, end + d + 10] (lags limitados a 15–45 s).
    v1 (sem delay_s): olha o chat dentro do próprio trecho, como antes.
    """
    if not seismic or not seismic.get("per_second"):
        return 0.0
    per_second = seismic["per_second"]
    if seismic.get("delay_s") is not None:
        d = float(seismic["delay_s"])
        start = start + _clamp(d - 10.0, DELAY_MIN_S, DELAY_MAX_S)
        end = end + _clamp(d + 10.0, DELAY_MIN_S, DELAY_MAX_S)
    lo = max(0, int(math.floor(start)))
    hi = min(len(per_second), max(lo + 1, int(math.ceil(end))))
    slice_rows = per_second[lo:hi]
    if not slice_rows:
        return 0.0
    max_z = max(float(r["vel_zscore"]) for r in slice_rows)
    mean_emote = sum(float(r["emote_burst"]) for r in slice_rows) / len(slice_rows)
    raw = max(0.0, (max_z / 5.5) * 8.0 + mean_emote * 2.5)
    return round(min(10.0, raw), 2)


def peak_reaction_for_window(seismic: dict[str, Any] | None, start: float, end: float) -> dict[str, Any] | None:
    """Pico (v2) cujo lance-causa cai dentro de [start, end] — para repassar o tipo de reação ao Editor-Chefe."""
    if not seismic or seismic.get("version") != SEISMIC_VERSION:
        return None
    hits = [p for p in seismic.get("peaks") or []
            if p.get("reaction_type") and start - 2.0 <= float(p.get("cause_second", -1)) <= end + 2.0]
    return max(hits, key=lambda p: p.get("weight", 0.0)) if hits else None
