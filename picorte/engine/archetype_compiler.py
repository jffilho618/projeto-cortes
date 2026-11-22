"""Compilação Automática por Arquétipo da Mesma Live (Épico 3.5 — Story 3.5.5).

Quando uma live gera >= 4 momentos fortes do mesmo arquétipo (ex.: todos os
detalhes testados ou todos os rages na mesma fase), sugere e planeja uma
compilação temática de 2–4 minutos.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

ARCHETYPE_COMPILATION_TITLES: dict[str, str] = {
    "callback_oculto": "TODOS OS CALLBACKS E REFERÊNCIAS OCULTAS DESSA LIVE",
    "caos_coop": "MELHORES MOMENTOS DE CAOS CO-OP NO DISCORD",
    "rage_tilt": "A ESPIRAL COMPLETA DO TILT NESSA LIVE",
    "serio_realtalk": "OS MELHORES PAPOS RETOS E REFLEXÕES DA LIVE",
    "polemica_hottake": "AS OPINIÕES MAIS POLÊMICAS QUE DIVIDIRAM O CHAT",
    "descoberta_detalhe": "TODOS OS DETALHES E SEGREDOS TESTADOS NESSA LIVE",
    "clutch_fail": "CLUTCHES INSANOS E FAILS CINEMATOGRÁFICOS DA LIVE",
    "susto_tensao": "COMPILADO DE SUSTOS E TENSÃO AO VIVO",
    "deadpan_karma": "OS MELHORES MOMENTOS DE KARMA INSTANTÂNEO",
    "chat_trolagem": "AS MELHORES RESPOSTAS E TROLAGENS COM O CHAT",
    "nobada_vacilo": "TOP VACILOS DA LIVE",
    "mico_constrangimento": "OS MAIORES MICOS DA LIVE",
}


def compile_by_archetype(
    candidates: list[dict[str, Any]],
    *,
    min_clips: int = 4,
    min_total_sec: float = 90.0,
    max_total_sec: float = 240.0,
    min_score: float = 7.5,
) -> list[dict[str, Any]]:
    """Agrupa >= min_clips do mesmo arquétipo em compilações temáticas de 2–4 min."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cand in candidates or []:
        arch = str(cand.get("archetype") or "").strip().lower()
        score = float(cand.get("overall") or 0.0)
        if not arch or score < float(min_score):
            continue
        grouped[arch].append(dict(cand))

    compilations: list[dict[str, Any]] = []
    for arch, items in sorted(grouped.items()):
        if len(items) < int(min_clips):
            continue
        # Escolhe os melhores sem estourar max_total_sec, depois ordena cronologicamente
        ranked = sorted(items, key=lambda c: (-float(c.get("overall") or 0.0), float(c.get("start") or 0.0)))
        picked: list[dict[str, Any]] = []
        total = 0.0
        for item in ranked:
            dur = float(item.get("duration") or (float(item.get("end", 0)) - float(item.get("start", 0))))
            if dur <= 0:
                continue
            if total + dur > float(max_total_sec) and len(picked) >= int(min_clips):
                continue
            if total + dur <= float(max_total_sec):
                picked.append(item)
                total += dur
        if len(picked) < int(min_clips) or total < float(min_total_sec):
            continue
        picked.sort(key=lambda c: float(c.get("start") or 0.0))
        compilations.append({
            "archetype": arch,
            "title": ARCHETYPE_COMPILATION_TITLES.get(arch, f"COMPILADO {arch.upper()}"),
            "clips": picked,
            "clip_count": len(picked),
            "total_duration": round(total, 2),
            "avg_score": round(sum(float(c.get("overall") or 0.0) for c in picked) / len(picked), 2),
        })

    compilations.sort(key=lambda c: (-c["avg_score"], -c["clip_count"]))
    return compilations
