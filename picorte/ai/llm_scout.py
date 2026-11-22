"""Full-VOD Narrative Scout (Épico 3.5 — Story 3.5.2).

Compacta a transcrição inteira em blocos numerados [S0001] (com Map-Reduce para
lives longas > 90 min) para que o LLM pesque momentos extraordinários de qualquer
minuto do VOD — inclusive silenciosos/culturais — sem alucinar timestamps.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from picorte.ai.llm_router import LLMRouter, VALID_PROVIDERS, _extract_json_array
from picorte.engine.multitrack import CANONICAL_ARCHETYPES

LONG_VOD_MAPREDUCE_SECONDS = 5400.0  # 90 min
MAX_DIRECT_CHARS = 16000
BLOCK_SECONDS = 420.0  # blocos de 7 min para Map-Reduce

SCOUT_SYSTEM_PROMPT = (
    "Você é o Caçador Narrativo Global (Full-VOD Scout) do Picorte para lives de games em PT-BR. "
    "Leia TODA a transcrição numerada ([S0001]...) e encontre até 15 momentos EXTRAORDINÁRIOS — "
    "incluindo momentos SILENCIOSOS/sutis (callbacks de trailer, piadas ocultas, comparações de detalhes, "
    "real-talk sério, opiniões polêmicas, ironia deadpan/karma) e também caos co-op, rage, clutches, sustos, trocas com o chat, "
    "vacilos bobos do próprio streamer (nobada) e micos/constrangimentos (piada que não colou, silêncio constrangedor). "
    f"Arquétipos válidos: {', '.join(CANONICAL_ARCHETYPES)}. "
    "NUNCA invente timestamps em segundos: use EXATAMENTE os IDs [Sxxxx] existentes. "
    "Retorne APENAS um array JSON de objetos: "
    '{"start_sid": "S0001", "end_sid": "S0005", "archetype": str, "why": str, '
    '"duration_bucket": "micro"|"short"|"extended"|"long"}.'
)

MAP_BLOCK_SYSTEM_PROMPT = (
    "Você é o Analista de MAPA DE BLOCO do Picorte. "
    "Resuma os momentos potencialmente interessantes deste bloco de live gamer (inclusive sutis, "
    "testes de detalhe, callbacks de trailer, desabafos sérios, polêmicas, caos ou rage). "
    "Use APENAS IDs [Sxxxx] presentes no bloco. "
    'Retorne APENAS um array JSON: [{"start_sid": "S0001", "end_sid": "S0003", "summary": str}].'
)


def _fmt_mmss(sec: float) -> str:
    total = max(0, int(round(sec)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def build_numbered_transcript(sentences: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    """Formata sentenças como '[S0001] (00:14) texto' e devolve mapa sid -> índice."""
    lines: list[str] = []
    sid_map: dict[str, int] = {}
    for idx, sent in enumerate(sentences):
        sid = f"S{idx + 1:04d}"
        sid_map[sid] = idx
        ts = _fmt_mmss(float(sent.get("start") or 0.0))
        txt = str(sent.get("text") or "").strip()
        lines.append(f"[{sid}] ({ts}) {txt}")
    return "\n".join(lines), sid_map


def _context_header(source_meta: dict[str, Any] | None, dossier: dict[str, Any] | None) -> str:
    parts: list[str] = []
    if isinstance(source_meta, dict):
        if source_meta.get("title"):
            parts.append(f"TÍTULO DO VÍDEO: {source_meta['title']}")
        if source_meta.get("channel"):
            parts.append(f"CANAL: {source_meta['channel']}")
        chapters = source_meta.get("chapters") or []
        if chapters:
            ch_txt = "; ".join(
                f"{_fmt_mmss(float(c.get('start_time', 0)))} {c.get('title', '')}"
                for c in chapters[:20]
            )
            parts.append(f"CAPÍTULOS: {ch_txt}")
    if isinstance(dossier, dict):
        parts.append(f"DOSSIÊ DO JOGO ({dossier.get('display_name') or dossier.get('slug')}):")
        callbacks = dossier.get("cultural_callbacks") or []
        if callbacks:
            parts.append("  Callbacks/Memes conhecidos: " + " | ".join(str(x) for x in callbacks[:8]))
        details = dossier.get("hot_details_to_watch") or []
        if details:
            parts.append("  Detalhes para observar: " + " | ".join(str(x) for x in details[:6]))
    return "\n".join(parts)


def _chunk_sentences(
    sentences: list[dict[str, Any]],
    block_seconds: float = BLOCK_SECONDS,
    max_block_chars: int = 10000,
) -> list[list[tuple[str, dict[str, Any]]]]:
    if not sentences:
        return []
    blocks: list[list[tuple[str, dict[str, Any]]]] = []
    cur: list[tuple[str, dict[str, Any]]] = []
    cur_chars = 0
    block_start = float(sentences[0].get("start") or 0.0)
    for idx, sent in enumerate(sentences):
        sid = f"S{idx + 1:04d}"
        st = float(sent.get("start") or 0.0)
        line_len = len(str(sent.get("text") or "")) + 20
        if cur and ((st - block_start) >= float(block_seconds) or (cur_chars + line_len) > int(max_block_chars)):
            blocks.append(cur)
            cur = []
            cur_chars = 0
            block_start = st
        cur.append((sid, sent))
        cur_chars += line_len
    if cur:
        blocks.append(cur)
    return blocks


def _resolve_scout_provider(ai_mode: str, filter_provider: str, companion_provider: str) -> str | None:
    if ai_mode in VALID_PROVIDERS:
        return ai_mode
    if ai_mode == "dupla":
        return companion_provider if companion_provider in VALID_PROVIDERS else filter_provider
    return None


def scout_full_vod(
    sentences: list[dict[str, Any]],
    *,
    router: LLMRouter,
    ai_mode: str = "claude",
    source_meta: dict[str, Any] | None = None,
    dossier: dict[str, Any] | None = None,
    max_findings: int = 15,
    filter_provider: str = "ollama",
    companion_provider: str = "claude",
    model: str | None = None,
    end_breath_sec: float = 1.5,
    max_workers: int = 3,
) -> list[dict[str, Any]]:
    """Executa busca narrativa global sobre o VOD inteiro retornando candidatos validados."""
    if not sentences:
        return []
    provider = _resolve_scout_provider(ai_mode, filter_provider, companion_provider)
    if not provider:
        return []

    numbered, sid_map = build_numbered_transcript(sentences)
    header = _context_header(source_meta, dossier)
    duration = float(
        (source_meta or {}).get("duration")
        or (sentences[-1].get("end") if sentences else 0.0)
        or 0.0
    )

    use_mapreduce = duration >= LONG_VOD_MAPREDUCE_SECONDS or len(numbered) > MAX_DIRECT_CHARS
    if use_mapreduce:
        blocks = _chunk_sentences(sentences)
        total_blocks = len(blocks)
        map_provider = filter_provider if ai_mode == "dupla" and filter_provider in VALID_PROVIDERS else provider
        # Ollama usa GPU local (AD-3): mantém serial; CLIs externas (claude/gemini) rodam em paralelo seguro
        workers = 1 if map_provider == "ollama" else max(1, min(int(max_workers), total_blocks))
        print(f"  [scout] Map-Reduce em {total_blocks} blocos ({map_provider}, {workers} workers)...", flush=True)

        def _map_one(args: tuple[int, list[tuple[str, dict[str, Any]]]]) -> list[str]:
            b_idx, block = args
            print(f"  [scout bloco {b_idx}/{total_blocks}] lendo transcrição...", flush=True)
            block_text = "\n".join(
                f"[{sid}] ({_fmt_mmss(float(s.get('start') or 0.0))}) {str(s.get('text') or '').strip()}"
                for sid, s in block
            )
            prompt_block = f"{header}\n\nBLOCO DA TRANSCRIÇÃO:\n{block_text}".strip()
            try:
                raw_block = router.provider_runner(map_provider, model, MAP_BLOCK_SYSTEM_PROMPT, prompt_block)
                entries = _extract_json_array(raw_block) or []
            except Exception:
                entries = []
            local_events: list[str] = []
            for ev in entries:
                if not isinstance(ev, dict):
                    continue
                s_id = str(ev.get("start_sid") or "").strip().upper()
                e_id = str(ev.get("end_sid") or s_id).strip().upper()
                summary = str(ev.get("summary") or "").strip()
                if s_id in sid_map and e_id in sid_map and summary:
                    local_events.append(f"[{s_id}..{e_id}] {summary}")
            return local_events

        indexed_blocks = list(enumerate(blocks, 1))
        map_events: list[str] = []
        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for chunk_events in pool.map(_map_one, indexed_blocks):
                    map_events.extend(chunk_events)
        else:
            for item in indexed_blocks:
                map_events.extend(_map_one(item))

        if not map_events:
            return []
        print(f"  [scout global] consolidando {len(map_events)} eventos em até {max_findings} destaques...", flush=True)
        user_prompt = (
            f"{header}\n\nMAPA DE EVENTOS DA LIVE INTEIRA (escolha até {max_findings} melhores):\n"
            + "\n".join(map_events)
        ).strip()
    else:
        print(f"  [scout global] lendo VOD completo ({len(sentences)} sentenças) via {provider}...", flush=True)
        user_prompt = (
            f"{header}\n\nTRANSCRIÇÃO COMPLETA NUMERADA (escolha até {max_findings} melhores):\n"
            f"{numbered}"
        ).strip()

    try:
        raw = router.provider_runner(provider, model, SCOUT_SYSTEM_PROMPT, user_prompt)
    except Exception:
        return []
    parsed = _extract_json_array(raw)
    if not parsed:
        return []

    findings: list[dict[str, Any]] = []
    seen_spans: set[tuple[int, int]] = set()
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        s_id = str(entry.get("start_sid") or "").strip().upper()
        e_id = str(entry.get("end_sid") or s_id).strip().upper()
        if s_id not in sid_map or e_id not in sid_map:
            continue
        i_start, i_end = sid_map[s_id], sid_map[e_id]
        if i_end < i_start:
            continue
        if (i_start, i_end) in seen_spans:
            continue
        seen_spans.add((i_start, i_end))

        start_t = float(sentences[i_start]["start"])
        raw_end = float(sentences[i_end]["end"]) + float(end_breath_sec)
        end_t = min(duration, raw_end) if duration > 0 else raw_end
        if end_t <= start_t:
            continue

        arch = str(entry.get("archetype") or "").strip().lower()
        if arch not in CANONICAL_ARCHETYPES:
            arch = "descoberta_detalhe"
        why = str(entry.get("why") or "").strip()
        bucket = str(entry.get("duration_bucket") or "short").strip().lower()
        if bucket not in ("micro", "short", "extended", "long"):
            bucket = "short"

        win_text = " ".join(str(s.get("text") or "") for s in sentences[i_start:i_end + 1]).strip()
        findings.append({
            "start": round(start_t, 2),
            "end": round(end_t, 2),
            "duration": round(end_t - start_t, 2),
            "hook": " ".join(win_text.split()[:7]) or why[:50] or "scout_clip",
            "text": win_text,
            "overall": 8.4,
            "raw_score": 8.2,
            "seed_kind": "llm_scout",
            "track_origin": "full_vod_scout",
            "archetype": arch,
            "duration_bucket": bucket,
            "scout_sids": [s_id, e_id],
            "why_extraordinary": why,
            "score_parts": {"llm_scout": 1.0},
            "evidence": {},
            "reason": f"Full-VOD Scout ({arch}): {why}"[:300],
        })
        if len(findings) >= int(max_findings):
            break

    return findings


QUERY_SCOUT_SYSTEM_PROMPT = (
    "Você é o Buscador por Pergunta Livre (Query-Driven Clipping) do Picorte. "
    "Leia a transcrição numerada ([S0001]...) e encontre TODOS os trechos que respondam "
    "EXATAMENTE ao pedido do operador. Use APENAS IDs [Sxxxx] existentes. "
    f"Arquétipos válidos: {', '.join(CANONICAL_ARCHETYPES)}. "
    "Retorne APENAS um array JSON: "
    '[{"start_sid": "S0001", "end_sid": "S0004", "archetype": str, "why": str, "duration_bucket": "micro"|"short"|"extended"|"long"}].'
)


def query_vod_clips(
    sentences: list[dict[str, Any]],
    *,
    query: str,
    router: LLMRouter,
    ai_mode: str = "claude",
    source_meta: dict[str, Any] | None = None,
    dossier: dict[str, Any] | None = None,
    max_findings: int = 12,
    filter_provider: str = "ollama",
    companion_provider: str = "claude",
    model: str | None = None,
    end_breath_sec: float = 1.5,
) -> list[dict[str, Any]]:
    """Busca trechos de um VOD respondendo a uma pergunta livre em linguagem natural."""
    clean_query = str(query or "").strip()
    if not clean_query or not sentences:
        return []
    provider = _resolve_scout_provider(ai_mode, filter_provider, companion_provider)
    if not provider:
        return []

    numbered, sid_map = build_numbered_transcript(sentences)
    header = _context_header(source_meta, dossier)
    duration = float(
        (source_meta or {}).get("duration")
        or (sentences[-1].get("end") if sentences else 0.0)
        or 0.0
    )
    user_prompt = (
        f"PERGUNTA DO OPERADOR: {clean_query}\n\n"
        f"{header}\n\n"
        f"TRANSCRIÇÃO NUMERADA:\n{numbered[:MAX_DIRECT_CHARS]}"
    ).strip()

    try:
        raw = router.provider_runner(provider, model, QUERY_SCOUT_SYSTEM_PROMPT, user_prompt)
    except Exception:
        return []
    parsed = _extract_json_array(raw)
    if not parsed:
        return []

    findings: list[dict[str, Any]] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        s_id = str(entry.get("start_sid") or "").strip().upper()
        e_id = str(entry.get("end_sid") or s_id).strip().upper()
        if s_id not in sid_map or e_id not in sid_map:
            continue
        i_start, i_end = sid_map[s_id], sid_map[e_id]
        if i_end < i_start:
            continue
        start_t = float(sentences[i_start]["start"])
        raw_end = float(sentences[i_end]["end"]) + float(end_breath_sec)
        end_t = min(duration, raw_end) if duration > 0 else raw_end
        if end_t <= start_t:
            continue
        arch = str(entry.get("archetype") or "").strip().lower()
        if arch not in CANONICAL_ARCHETYPES:
            arch = "descoberta_detalhe"
        why = str(entry.get("why") or "").strip()
        win_text = " ".join(str(s.get("text") or "") for s in sentences[i_start:i_end + 1]).strip()
        findings.append({
            "start": round(start_t, 2),
            "end": round(end_t, 2),
            "duration": round(end_t - start_t, 2),
            "hook": " ".join(win_text.split()[:7]) or why[:50] or "query_clip",
            "text": win_text,
            "overall": 8.6,
            "raw_score": 8.4,
            "seed_kind": "query_driven",
            "track_origin": "query_driven",
            "archetype": arch,
            "why_extraordinary": why,
            "score_parts": {"query_match": 1.0},
            "evidence": {},
            "reason": f"Query '{clean_query[:40]}': {why}"[:300],
        })
        if len(findings) >= int(max_findings):
            break
    return findings
