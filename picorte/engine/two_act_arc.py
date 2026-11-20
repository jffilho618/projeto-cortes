"""Arcos Narrativos de 2 Atos — Setup e Payoff Distantes (Épico 3.5 — Story 3.5.5).

Detecta promessas/previsões confiantes em um ponto da live emendadas com o
desfecho/karma distante minutos depois, e gera o filtro FFmpeg multiplataforma (AD-11).
"""
from __future__ import annotations

import re
from typing import Any

SETUP_PROMISE_RE = re.compile(
    r"\b(?:nunca\s+vou\s+morrer|relaxa|t[aá]\s+f[aá]cil|f[aá]cil\s+demais|t[aá]\s+seguro|"
    r"deixa\s+comigo|confia|vou\s+passar\s+de\s+primeira|imposs[ií]vel\s+errar|dessa\s+vez\s+vai)\b",
    re.IGNORECASE,
)

PAYOFF_FAIL_RE = re.compile(
    r"\b(?:morri|fui\s+de\s+base|morreu|perdi|explodiu|n[aã]o\s+acredito|"
    r"que\s+merda|lascou|ferrou|caguei|deu\s+ruim|de\s+novo)\b",
    re.IGNORECASE,
)


def _format_bridge_text(gap_seconds: float) -> str:
    mins = max(1, int(round(gap_seconds / 60.0)))
    return "1 minuto depois..." if mins == 1 else f"{mins} minutos depois..."


def detect_two_act_arcs(
    sentences: list[dict[str, Any]],
    *,
    min_gap_sec: float = 60.0,
    max_gap_sec: float = 1800.0,
    max_arcs: int = 5,
) -> list[dict[str, Any]]:
    """Encontra pares (Ato 1: promessa/setup -> Ato 2: karma/desfecho distante)."""
    setups: list[tuple[int, dict[str, Any]]] = []
    payoffs: list[tuple[int, dict[str, Any]]] = []
    for idx, sent in enumerate(sentences or []):
        txt = str(sent.get("text") or "")
        if SETUP_PROMISE_RE.search(txt):
            setups.append((idx, sent))
        if PAYOFF_FAIL_RE.search(txt):
            payoffs.append((idx, sent))

    arcs: list[dict[str, Any]] = []
    used_payoffs: set[int] = set()
    for s_idx, setup in setups:
        s_start = float(setup.get("start") or 0.0)
        s_end = float(setup.get("end") or s_start)
        for p_idx, payoff in payoffs:
            if p_idx <= s_idx or p_idx in used_payoffs:
                continue
            p_start = float(payoff.get("start") or 0.0)
            p_end = float(payoff.get("end") or p_start)
            gap = p_start - s_end
            if float(min_gap_sec) <= gap <= float(max_gap_sec):
                used_payoffs.add(p_idx)
                arcs.append({
                    "act1_start": round(s_start, 2),
                    "act1_end": round(s_end, 2),
                    "act1_text": str(setup.get("text") or "").strip(),
                    "act2_start": round(p_start, 2),
                    "act2_end": round(p_end, 2),
                    "act2_text": str(payoff.get("text") or "").strip(),
                    "gap_sec": round(gap, 2),
                    "bridge_text": _format_bridge_text(gap),
                    "archetype": "deadpan_karma",
                    "total_duration": round((s_end - s_start) + (p_end - p_start), 2),
                })
                break
        if len(arcs) >= int(max_arcs):
            break
    return arcs


def build_two_act_ffmpeg_filter(
    act1_start: float,
    act1_end: float,
    act2_start: float,
    act2_end: float,
    *,
    video_label: str = "vout",
    audio_label: str = "aout",
) -> str:
    """Gera filter_complex FFmpeg multiplataforma (Windows/Linux) unindo Ato 1 + Ato 2."""
    s1, e1 = round(float(act1_start), 3), round(float(act1_end), 3)
    s2, e2 = round(float(act2_start), 3), round(float(act2_end), 3)
    if e1 <= s1 or e2 <= s2:
        raise ValueError("Intervalos dos dois atos precisam ter end > start.")
    return (
        f"[0:v]trim=start={s1}:end={e1},setpts=PTS-STARTPTS[v1];"
        f"[0:a]atrim=start={s1}:end={e1},asetpts=PTS-STARTPTS[a1];"
        f"[0:v]trim=start={s2}:end={e2},setpts=PTS-STARTPTS[v2];"
        f"[0:a]atrim=start={s2}:end={e2},asetpts=PTS-STARTPTS[a2];"
        f"[v1][a1][v2][a2]concat=n=2:v=1:a=1[{video_label}][{audio_label}]"
    )
