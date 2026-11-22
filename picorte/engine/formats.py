"""Formatos irmãos do mesmo momento (Épico 3.7 — Story 3.7.3).

- Versão TikTok de 60–75 s: o mesmo momento do Short com contexto REAL (frases antes e depois), nunca enchimento.
- Proposta de Longo 16:9 de 3–5 min para Shorts ouro/forte: miolo pelo pico do heatmap (3.6.5, AC6) e frases.
- Short, versão TikTok e Longo compartilham o `moment_id` (família no pHash do Épico 4).
"""
from __future__ import annotations

from typing import Any

TIKTOK_MIN_S, TIKTOK_MAX_S = 60.0, 75.0
LONG_MIN_S, LONG_MAX_S, LONG_TARGET_S = 180.0, 300.0, 240.0
LONG_TIERS = ("ouro", "forte")
LONG_MIN_SPEECH = 0.35        # fração da janela com fala; abaixo disso não há material para um Longo
HEATMAP_REACH_S = 150.0       # pico do heatmap a até 150 s do Short pode virar o miolo
SHORT_MAX_S = 59.0

_SIBLING_DROP = ("rank", "cold_open", "transformacoes", "layout_timeline", "parent_long_clip_id")


def moment_id_for(seg: dict[str, Any]) -> str:
    return seg.get("moment_id") or f"m{int(round(float(seg['start']) * 10))}-{int(round(float(seg['end']) * 10))}"


def _sibling(seg: dict[str, Any], start: float, end: float, **extra: Any) -> dict[str, Any]:
    rec = {k: v for k, v in seg.items() if k not in _SIBLING_DROP}
    rec.update(start=round(start, 2), end=round(end, 2), duration=round(end - start, 2),
               moment_id=moment_id_for(seg), **extra)
    return rec


def tiktok_version(short: dict[str, Any], sentences: list[dict[str, Any]] | None, *,
                   source_duration: float) -> dict[str, Any] | None:
    """Versão de 60–75 s do mesmo momento: acrescenta frases inteiras, primeiro o setup (antes), depois a sequência."""
    s, e = float(short["start"]), float(short["end"])
    if e - s >= TIKTOK_MIN_S:
        return None
    sents = sorted(sentences or [], key=lambda x: float(x["start"]))
    before = [x for x in sents if float(x["end"]) <= s + 0.25][::-1]
    after = [x for x in sents if float(x["start"]) >= e - 0.25]
    start, end = s, e
    turn_before = True
    while end - start < TIKTOK_MIN_S and (before or after):
        pool = before if (turn_before and before) or not after else after
        nxt = pool.pop(0)
        cand_start = min(start, float(nxt["start"]))
        cand_end = max(end, float(nxt["end"]))
        if cand_end - cand_start > TIKTOK_MAX_S:
            if pool is before:
                before = []
            else:
                after = []
            continue
        start, end = cand_start, cand_end
        turn_before = not turn_before
    if not (TIKTOK_MIN_S <= end - start <= TIKTOK_MAX_S) or start < 0 or end > float(source_duration) + 0.01:
        return None
    return _sibling(short, start, end, formato="tiktok_60", aspect="9:16")


def long_proposal(short: dict[str, Any], sentences: list[dict[str, Any]] | None, *,
                  heatmap_peaks: list[dict[str, Any]] | None, source_duration: float) -> dict[str, Any] | None:
    """Longo 16:9 de 3–5 min em volta do momento (só ouro/forte, e só com fala suficiente)."""
    if short.get("tier") not in LONG_TIERS or float(source_duration) < LONG_MIN_S:
        return None
    s, e = float(short["start"]), float(short["end"])
    mid = (s + e) / 2.0
    near = [float(p["center"]) for p in heatmap_peaks or [] if abs(float(p["center"]) - mid) <= HEATMAP_REACH_S]
    core, miolo = (min(near, key=lambda c: abs(c - mid)), "heatmap") if near else (mid, "corte")
    lo = max(0.0, min(s, core - LONG_TARGET_S / 2.0))
    hi = min(float(source_duration), max(e, lo + LONG_TARGET_S))
    lo = max(0.0, min(lo, hi - LONG_TARGET_S))
    sents = sorted(sentences or [], key=lambda x: float(x["start"]))
    starts = [float(x["start"]) for x in sents if float(x["start"]) <= min(lo + 15.0, s)]
    ends = [float(x["end"]) for x in sents if float(x["end"]) >= max(hi - 15.0, e)]
    start = max([t for t in starts if t <= lo + 15.0], default=lo)
    end = min([t for t in ends if t >= hi - 15.0], default=hi)
    start, end = min(start, s), max(end, e)
    if not (LONG_MIN_S <= end - start <= LONG_MAX_S):
        return None
    speech = sum(max(0.0, min(end, float(x["end"])) - max(start, float(x["start"]))) for x in sents)
    if speech / (end - start) < LONG_MIN_SPEECH:
        return None
    return _sibling(short, start, end, formato="longo_16x9", aspect="16:9", miolo=miolo)


def add_format_siblings(segments: list[dict[str, Any]], sentences: list[dict[str, Any]] | None, *,
                        heatmap_peaks: list[dict[str, Any]] | None, source_duration: float) -> list[dict[str, Any]]:
    """Shorts ganham `moment_id`; cada Short ganha a versão TikTok e, se ouro/forte, a proposta de Longo (no fim)."""
    shorts = [dict(s, moment_id=moment_id_for(s)) for s in segments or []]
    extras: list[dict[str, Any]] = []
    for sh in shorts:
        if float(sh["end"]) - float(sh["start"]) > SHORT_MAX_S or sh.get("formato", "short") != "short":
            continue
        for sib in (tiktok_version(sh, sentences, source_duration=source_duration),
                    long_proposal(sh, sentences, heatmap_peaks=heatmap_peaks, source_duration=source_duration)):
            if sib is not None:
                extras.append(sib)
    return shorts + extras
