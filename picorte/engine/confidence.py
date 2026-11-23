"""Confiança da seleção (Épico 3.6 — Story 3.6.5).

- Silêncio digital: trecho mudo (música removida pelo YouTube, queda da live) não vira corte (P1).
- Falha técnica: a volta do silêncio com o chat dizendo "caiu"/"travou"/"F" vira tag de `chat_trolagem`.
- Ouro com 2 sinais: o tier `ouro` exige ≥ 2 sinais independentes MEDIDOS; senão `forte`.
- `standalone`: corte que não se entende sem conhecer o streamer não vai para Short isolado.
- Confiança do projeto: quais sinais rodaram de verdade (para o painel do Épico 6, W9).
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from picorte.engine.evidence import SILENCE_DB as _AUDIO_FLOOR_DB

# O cache de áudio (evidence.SILENCE_DB) trava o volume no piso (−80 dB): "colado no piso" = áudio zerado.
# Importado, não copiado: se o piso do áudio mudar, o silêncio digital acompanha (code review 2026-11-23).
DIGITAL_SILENCE_FLOOR_DB = _AUDIO_FLOOR_DB + 0.5
DIGITAL_SILENCE_MIN_S = 2.0
DIGITAL_SILENCE_MAX_FRACTION = 0.20

TECH_FAILURE_RE = re.compile(r"\bcaiu\b|\btravou\b|\btravad[oa]\b|\blag\b|\bvoltou\b|^\s*f+\s*$", re.IGNORECASE)
TECH_FAILURE_WINDOW_S = 30.0

# Pistas que só pegam candidato pela FALA. Ficaram de fora (code review 2026-11-23):
# - "coop_payoff_nontextual": também recebe pico de chat, mídia e comentário sem fala; o léxico co-op é conferido;
# - "vacilo_mico": a nota também vem do comentário e do chat; conta como fala só pela `archetype_hint_source`.
LEXICAL_TRACKS = ("deictic_detective_callback", "serio_polemica_silence")
# Dica de arquétipo que veio de outro sinal (comentário, chat): já conta como esse sinal, não como "fala".
HINT_SOURCES_NOT_SPEECH = ("comentario", "chat")
GOLD_MIN_SIGNALS = 2
STANDALONE_MIN = 5.0

# Partes da saúde (engine_health.json) que são SINAIS de seleção.
SIGNAL_PARTS = ("prosody", "chat", "vision", "comment_seeds", "heatmap", "editor", "full_vod_scout")


def digital_silence_ranges(rms_db: Any, *, floor_db: float = DIGITAL_SILENCE_FLOOR_DB,
                           min_s: float = DIGITAL_SILENCE_MIN_S) -> list[tuple[float, float]]:
    """Trechos (início, fim) em segundos com o volume colado no piso por ≥ `min_s` (1 valor de rms por segundo)."""
    rms = np.asarray(rms_db, dtype=np.float64).ravel()
    out: list[tuple[float, float]] = []
    start = None
    for i, v in enumerate(np.append(rms, 0.0)):  # sentinela fecha o último trecho
        if v <= floor_db and i < rms.size:
            if start is None:
                start = i
        elif start is not None:
            if i - start >= min_s:
                out.append((float(start), float(i)))
            start = None
    return out


def silence_fraction(start: float, end: float, ranges: list[tuple[float, float]]) -> float:
    span = float(end) - float(start)
    if span <= 0:
        return 0.0
    muted = sum(max(0.0, min(float(end), b) - max(float(start), a)) for a, b in ranges or [])
    return min(1.0, muted / span)


def drop_muted_candidates(candidates: list[dict[str, Any]], ranges: list[tuple[float, float]], *,
                          max_fraction: float = DIGITAL_SILENCE_MAX_FRACTION) -> tuple[list[dict[str, Any]], int]:
    """Descarta candidatos com mais de `max_fraction` de silêncio digital. Devolve (mantidos, descartados)."""
    if not ranges:
        return list(candidates or []), 0
    kept = [c for c in candidates or []
            if silence_fraction(float(c.get("start") or 0.0), float(c.get("end") or 0.0), ranges) <= max_fraction]
    return kept, len(candidates or []) - len(kept)


def tag_technical_failures(candidates: list[dict[str, Any]], ranges: list[tuple[float, float]],
                           chat_messages: list[dict[str, Any]] | None, delay_s: float) -> list[dict[str, Any]]:
    """Candidato que contém a VOLTA de um silêncio digital e cujo chat logo depois fala em queda → falha_tecnica."""
    msgs = chat_messages or []
    out = []
    for cand in candidates or []:
        rec = dict(cand)
        s, e = float(rec.get("start") or 0.0), float(rec.get("end") or 0.0)
        for _, back in ranges or []:
            if not (s <= back <= e):
                continue
            hi = back + float(delay_s) + TECH_FAILURE_WINDOW_S
            if any(back <= float(m.get("t") or 0.0) <= hi and TECH_FAILURE_RE.search(str(m.get("text") or ""))
                   for m in msgs):
                tags = list(rec.get("tags") or [])
                if "falha_tecnica" not in tags:
                    tags.append("falha_tecnica")
                rec["tags"] = tags
                if not rec.get("archetype_hint"):
                    rec["archetype_hint"] = "chat_trolagem"
                    rec["archetype_hint_source"] = "chat"
                break
        out.append(rec)
    return out


def independent_signals(cand: dict[str, Any]) -> list[str]:
    """Sinais independentes MEDIDOS que sustentam o candidato (a opinião do Editor-Chefe não conta)."""
    from picorte.engine.prosody_events import LAUGH_MIN

    ev = cand.get("evidence") or {}
    out: list[str] = []
    if float(ev.get("laugh") or 0.0) >= LAUGH_MIN:
        out.append("riso")
    # O pico de som (`jumpscare_db`) não conta: é susto só às vezes — também é explosão do jogo ou grito de doação
    # (ouvido pelo dono em 2026-11-23). O Editor-Chefe decide pela fala.
    if ev.get("chat_measured") and (float(ev.get("chat") or 0.0) >= 6.0 or ev.get("chat_reaction")):
        out.append("chat")
    if (ev.get("vision_measured") and ev.get("facecam_measured", True)
            and float(ev.get("visual_games") or 0.0) >= 6.5):
        out.append("visao")
    if ev.get("vision_measured") and float(ev.get("hud") or 0.0) >= 5.0 and int(ev.get("hud_ocr_hits") or 0) > 0:
        out.append("hud")  # só com texto do jogo lido pelo OCR (movimento + objetos do COCO não são HUD)
    if cand.get("comment_hint"):
        out.append("comentario")
    if cand.get("seed_kind") == "heatmap_peak" or cand.get("near_heatmap"):
        out.append("heatmap")
    if cand.get("track_origin") == "full_vod_scout":
        out.append("batedor")
    if _speech_signal(cand):
        out.append("fala")
    return out


def _speech_signal(cand: dict[str, Any]) -> bool:
    """Sinal de FALA medido pelo conteúdo (léxico, dêitico, dica de arquétipo), não pela pista que pegou o
    candidato: cada candidato fica numa pista só, e o achado do batedor perderia a fala de detetive."""
    from picorte.engine.multitrack import (ARCHETYPE_LEXICON_PTBR, MICO_LEXICON_PTBR, VACILO_LEXICON_PTBR,
                                           _lexicon_hits, _phrase_hits, detect_collective_echo)

    hint_from_speech = (cand.get("archetype_hint")
                        and cand.get("archetype_hint_source") not in HINT_SOURCES_NOT_SPEECH)
    if cand.get("track_origin") in LEXICAL_TRACKS or hint_from_speech or cand.get("has_visual_deictic"):
        return True
    text = str(cand.get("text") or "")
    if not text.strip():
        return False
    return bool(_lexicon_hits(text, ARCHETYPE_LEXICON_PTBR["detective_callback"])
                or _lexicon_hits(text, ARCHETYPE_LEXICON_PTBR["coop_karma_payoff"]) or detect_collective_echo(text)
                or _lexicon_hits(text, ARCHETYPE_LEXICON_PTBR["serio_polemica"])
                or _phrase_hits(text, VACILO_LEXICON_PTBR) or _phrase_hits(text, MICO_LEXICON_PTBR))


def enforce_gold_rule(candidates: list[dict[str, Any]], *, min_signals: int = GOLD_MIN_SIGNALS) -> int:
    """`ouro` com menos de `min_signals` sinais independentes vira `forte` (em lugar). Devolve quantos caíram."""
    dropped = 0
    for cand in candidates or []:
        sig = independent_signals(cand)
        cand["sinais_independentes"] = sig
        if cand.get("tier") == "ouro" and len(sig) < min_signals:
            cand["tier"] = "forte"
            cand["ouro_rebaixado"] = f"só {len(sig)} sinal(is) medido(s): {', '.join(sig) or 'nenhum'}"
            dropped += 1
    return dropped


def split_standalone(segments: list[dict[str, Any]], *, min_score: float = STANDALONE_MIN
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separa (Shorts, Longo/compilação): `standalone` < 5 não vai para Short isolado. Sem a nota, fica."""
    shorts, longos = [], []
    for seg in segments or []:
        val = seg.get("standalone")
        if isinstance(val, (int, float)) and not isinstance(val, bool) and float(val) < float(min_score):
            longos.append({**seg, "motivo": f"standalone {float(val):g} < {min_score:g}: só se entende com "
                                            "contexto; vai para Longo/compilação, não para Short isolado"})
        else:
            shorts.append(seg)
    return shorts, longos


def project_confidence(health: dict[str, Any]) -> dict[str, Any]:
    """Quais sinais de seleção rodaram de verdade neste projeto e uma nota 0–1 (ok / total de sinais)."""
    ok, failed, absent = [], [], []
    for part in SIGNAL_PARTS:
        status = str((health.get(part) or {}).get("status") or "")
        (ok if status == "ok" else failed if status == "failed" else absent).append(part)
    return {"sinais_ok": ok, "sinais_falhos": failed, "sinais_ausentes": absent,
            "nota": round(len(ok) / len(SIGNAL_PARTS), 2)}
