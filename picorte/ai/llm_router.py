"""Roteador de IA de 4 Modos (AD-4 / R-07):
1. ollama — 100% local na GPU (http://localhost:11434)
2. claude — CLI local da assinatura ('claude -p') ou API Anthropic se configurada
3. gemini — CLI local da assinatura ('agy -p' / 'gemini -p') ou API Google se configurada
4. dupla  — Pipeline de dois estágios ('filter_provider' filtra -> 'companion_provider' acompanha/lapida)
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Callable

from picorte.config import detect_gpu_profile, resolve_cli_binary
from picorte.engine.multitrack import CANONICAL_ARCHETYPES, CANONICAL_TIERS
from picorte.engine.vram_runner import VRAMRunner

VALID_PROVIDERS = ("ollama", "claude", "gemini")
VALID_AI_MODES = ("heuristic", "ollama", "claude", "gemini", "dupla")
VALID_TONES = ("hype", "editorial", "curioso", "ironico", "tenso")
MAX_CLI_PROMPT_CHARS = 20000
DEFAULT_GOLDEN_EXAMPLES_PATH = Path(__file__).resolve().parent / "golden_examples.json"

FILTER_SYSTEM_PROMPT = (
    "Você é o Filtro Inicial de cortes virais de games (Picorte). "
    "Avalie cada candidato de transcrição (sem discriminar momentos calmos/culturais/sérios!) e retorne APENAS um array JSON com objetos: "
    '{"index": int, "adjustment": float (-1.0 a 1.0), "reason": str}.'
)

COMPANION_SYSTEM_PROMPT = (
    "Você é o Editor-Chefe v2 de cortes extraordinários de games em português do Brasil (Picorte). "
    "Avalie cada candidato usando o Conselho de 4 Caçadores Especialistas: "
    "(1) Comédia/Caos/Deadpan (caos_coop, deadpan_karma, chat_trolagem), "
    "(2) Rage/Clutch/Susto (rage_tilt, clutch_fail, susto_tensao), "
    "(3) Cultura/Lore/Detalhes/Callbacks (callback_oculto, descoberta_detalhe), "
    "(4) Opinião/Polêmica/Real-Talk (serio_realtalk, polemica_hottake). "
    f"Arquétipos válidos: {', '.join(CANONICAL_ARCHETYPES)}. "
    f"Tiers válidos: {', '.join(CANONICAL_TIERS)}. "
    f"Tons válidos: {', '.join(VALID_TONES)}. "
    "Retorne APENAS um array JSON com objetos: "
    '{"index": int, "adjustment": float (-2.5 a 3.0), "archetype": str, "tier": "ouro"|"forte"|"experimental", '
    '"tone": "hype"|"editorial"|"curioso"|"ironico"|"tenso", '
    '"rewatchability": float (0-10), "shareability": float (0-10), '
    '"hook_quote": str (opcional, frase lapidar), '
    '"proposed_title": str, '
    '"context_banner_2s": str (4 a 6 palavras curtas, concretas e magnéticas; '
    'RUIM: "Quando o jogo pede stealth mas você conhece seu limite" ou "A cena famosa do telhado faz sentido agora"; '
    'BOM: "NO TRAILER SPAWNAVA — ELE TESTOU", "CENA DO TRAILER 1 NO JOGO!", "MENU DE SHAPE DO SAN ANDREAS!"; '
    'para referências externas, contextualize SEM dar spoiler da punchline), '
    '"thumbnail_words": str (2-3 palavras em caixa alta), '
    '"pinned_comment_debate": str, '
    '"expand_start_sec": float (opcional, 0 a 20s se o setup estiver no pre_context), '
    '"expand_end_sec": float (opcional, 0 a 15s se a punchline estiver no post_context), '
    '"reason": str}. '
    "REGRAS: NUNCA meça qualidade só por volume/grito — callbacks culturais silenciosos (como testar detalhes de trailer), "
    "desabafos sérios, hot takes e deadpan valem +2.5 a +3.0 e tier 'ouro'. "
    "Penalize (-2.0 a -2.5) leitura de subs, patrocínios, intros genéricas e telas de configuração."
)


def load_golden_examples(path: Path | None = None) -> list[dict[str, Any]]:
    """Carrega a biblioteca viva de exemplos ouro (picorte/ai/golden_examples.json)."""
    target = Path(path) if path is not None else DEFAULT_GOLDEN_EXAMPLES_PATH
    if not target.is_file():
        return []
    try:
        data = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    examples = data.get("examples") if isinstance(data, dict) else data
    if not isinstance(examples, list):
        return []
    return [ex for ex in examples if isinstance(ex, dict)]


def attach_neighbor_context(
    candidates: list[dict[str, Any]],
    sentences: list[dict[str, Any]] | None,
    *,
    pre_sec: float = 20.0,
    post_sec: float = 15.0,
) -> list[dict[str, Any]]:
    """Anexa pre_context (20s antes) e post_context (15s depois) a cada candidato."""
    sents = sentences or []
    out: list[dict[str, Any]] = []
    for cand in candidates:
        rec = dict(cand)
        if not sents:
            out.append(rec)
            continue
        s = float(rec.get("start") or 0.0)
        e = float(rec.get("end") or s)
        pre_parts = [
            str(item.get("text") or "").strip()
            for item in sents
            if float(item.get("end") or 0.0) <= s + 0.25 and float(item.get("start") or 0.0) >= s - float(pre_sec)
        ]
        post_parts = [
            str(item.get("text") or "").strip()
            for item in sents
            if float(item.get("start") or 0.0) >= e - 0.25 and float(item.get("end") or 0.0) <= e + float(post_sec)
        ]
        rec["pre_context"] = " ".join(p for p in pre_parts if p)[:320]
        rec["post_context"] = " ".join(p for p in post_parts if p)[:280]
        out.append(rec)
    return out


def mmr_diversify(
    candidates: list[dict[str, Any]],
    *,
    max_per_archetype: int = 3,
    min_time_gap_sec: float = 25.0,
    limit: int | None = None,
    keep_overflow: bool = False,
) -> list[dict[str, Any]]:
    """Diversificação MMR (temporal + por arquétipo) para nenhum tipo monopolizar a fila.

    Quando keep_overflow=True, clipes excedentes do mesmo arquétipo (sem conflito temporal)
    são anexados APÓS o conjunto diverso em vez de serem descartados.
    """
    if not candidates:
        return []
    ordered = sorted(
        candidates,
        key=lambda c: (
            0 if c.get("tier") == "ouro" else (1 if c.get("tier") == "forte" else 2),
            -float(c.get("overall") or 0.0),
            float(c.get("start") or 0.0),
        ),
    )
    selected: list[dict[str, Any]] = []
    arch_counts: dict[str, int] = {}
    deferred: list[dict[str, Any]] = []

    def _too_close_in_time(cand: dict[str, Any], pool: list[dict[str, Any]]) -> bool:
        s = float(cand.get("start") or 0.0)
        e = float(cand.get("end") or s)
        c_mid = (s + e) / 2.0
        for prev in pool:
            ps = float(prev.get("start") or 0.0)
            pe = float(prev.get("end") or ps)
            inter = max(0.0, min(e, pe) - max(s, ps))
            union = max(1e-6, max(e, pe) - min(s, ps))
            if (inter / union) > 0.35 or abs(c_mid - (ps + pe) / 2.0) < float(min_time_gap_sec):
                return True
        return False

    for cand in ordered:
        if _too_close_in_time(cand, selected):
            continue
        arch = str(cand.get("archetype") or "").strip().lower()
        if arch and arch_counts.get(arch, 0) >= int(max_per_archetype):
            deferred.append(cand)
            continue
        selected.append(cand)
        if arch:
            arch_counts[arch] = arch_counts.get(arch, 0) + 1
        if limit is not None and len(selected) >= int(limit):
            return selected

    if keep_overflow or (limit is not None and len(selected) < int(limit)):
        for cand in deferred:
            if not _too_close_in_time(cand, selected):
                selected.append(cand)
                if limit is not None and len(selected) >= int(limit):
                    break
    return selected


def _extract_json_array(raw_text: str) -> list[dict[str, Any]] | None:
    text = (raw_text or "").strip()
    if not text:
        return None
    # Strip markdown code fences if present
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if isinstance(parsed, dict):
        # Some CLIs wrap output in {"result": "..."}
        inner = parsed.get("result") or parsed.get("response") or parsed.get("text")
        if isinstance(inner, str):
            return _extract_json_array(inner)
        if isinstance(parsed.get("candidates"), list):
            return parsed["candidates"]
        return None
    return parsed if isinstance(parsed, list) else None


def _default_ollama_model() -> str:
    prof = detect_gpu_profile()
    return "qwen2.5:3b" if prof["tier"] == "notebook_4gb" else "qwen2.5:7b"


class LLMRouter:
    """Roteia seleção e copywriting entre Ollama, Claude, Gemini ou Modo Dupla."""

    def __init__(
        self,
        *,
        ollama_host: str | None = None,
        ollama_model: str | None = None,
        provider_runner: Callable[[str, str | None, str, str], str] | None = None,
        vram_runner: VRAMRunner | None = None,
    ) -> None:
        self.ollama_host = (ollama_host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.ollama_model = ollama_model or _default_ollama_model()
        self.provider_runner = provider_runner or self._run_provider
        self.vram_runner = vram_runner or VRAMRunner()

    def _run_provider(self, provider: str, model: str | None, system_prompt: str, user_prompt: str) -> str:
        if provider == "ollama":
            chosen_model = model or self.ollama_model
            payload = json.dumps({
                "model": chosen_model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }).encode("utf-8")

            def _call_ollama() -> str:
                req = urllib.request.Request(
                    f"{self.ollama_host}/api/chat",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return str((data.get("message") or {}).get("content") or "")

            return self.vram_runner.run_stage("ollama_rerank", _call_ollama)

        prompt_full = f"{system_prompt}\n\nDados dos candidatos:\n{user_prompt}"

        if provider == "claude":
            cli = resolve_cli_binary("claude")
            if cli:
                cmd = [cli, "-p", prompt_full, "--output-format", "json"]
                if model:
                    cmd.extend(["--model", model])
                res = subprocess.run(
                    cmd,
                    cwd=tempfile.gettempdir(),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=180,
                    check=True,
                )
                return res.stdout
            api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
            if api_key:
                body = json.dumps({
                    "model": model or "claude-opus-5-5",
                    "max_tokens": 2048,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=body,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            raise RuntimeError("Claude CLI ('claude') e ANTHROPIC_API_KEY indisponíveis.")

        if provider == "gemini":
            cli = resolve_cli_binary("agy") or resolve_cli_binary("gemini")
            if cli:
                cmd = [cli, "-p", prompt_full, "--output-format", "json"]
                if os.path.basename(cli).lower().startswith("agy"):
                    cmd.append("--disable-slash-commands")
                if model:
                    cmd.extend(["--model", model])
                res = subprocess.run(
                    cmd,
                    cwd=tempfile.gettempdir(),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=180,
                    check=True,
                )
                return res.stdout
            api_key = os.environ.get("GOOGLE_API_KEY", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
            if api_key:
                chosen_model = model or "gemini-2.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent?key={api_key}"
                body = json.dumps({
                    "contents": [{"parts": [{"text": prompt_full}]}],
                }).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                cands = data.get("candidates") or []
                if cands:
                    parts = (cands[0].get("content") or {}).get("parts") or []
                    return "".join(p.get("text", "") for p in parts)
                return ""
            raise RuntimeError("Gemini/Antigravity CLI ('agy'/'gemini') e GOOGLE_API_KEY indisponíveis.")

        raise ValueError(f"Provedor de IA desconhecido: {provider}")

    def _apply_entries(
        self,
        ranked_subset: list[dict[str, Any]],
        entries: list[dict[str, Any]],
        *,
        mode_label: str,
        accumulate: bool = False,
        source_duration: float | None = None,
    ) -> list[dict[str, Any]]:
        updated = [dict(item) for item in ranked_subset]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            idx = entry.get("index")
            adj = entry.get("adjustment")
            if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < len(updated):
                continue
            if isinstance(adj, bool) or not isinstance(adj, (int, float)) or not math.isfinite(adj):
                continue
            adj_clamped = max(-2.5, min(3.0, float(adj)))
            rec = updated[idx]
            base = float(rec.get("overall", 0.0))
            if not accumulate:
                prev = rec.get("llm_adjustment")
                if isinstance(prev, (int, float)) and not isinstance(prev, bool):
                    base -= float(prev)
                rec["llm_adjustment"] = adj_clamped
            else:
                prev = rec.get("llm_adjustment") or 0.0
                rec["llm_adjustment"] = float(prev) + adj_clamped
            rec["overall"] = round(max(0.0, min(10.0, base + adj_clamped)), 2)
            rec["llm_mode_used"] = mode_label
            reason = str(entry.get("reason", "")).strip()
            if reason:
                old_reason = str(rec.get("reason", "")).strip()
                rec["reason"] = f"{old_reason} | {reason}".strip(" |")[:500]
            for field in (
                "proposed_title",
                "context_banner_2s",
                "thumbnail_words",
                "pinned_comment_debate",
                "hook_quote",
                "why_extraordinary",
            ):
                val = entry.get(field)
                if isinstance(val, str) and val.strip():
                    rec[field] = val.strip()
                    if field == "proposed_title" and not rec.get("hook"):
                        rec["hook"] = val.strip()

            arch = str(entry.get("archetype") or "").strip().lower()
            if arch in CANONICAL_ARCHETYPES:
                rec["archetype"] = arch
            tier = str(entry.get("tier") or "").strip().lower()
            if tier in CANONICAL_TIERS:
                rec["tier"] = tier
            tone = str(entry.get("tone") or "").strip().lower()
            if tone in VALID_TONES:
                rec["tone"] = tone
            for num_field in ("rewatchability", "shareability"):
                val = entry.get(num_field)
                if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
                    rec[num_field] = round(max(0.0, min(10.0, float(val))), 2)

            # Ajuste fino seguro de bordas a partir de pre_context / post_context
            exp_start = entry.get("expand_start_sec")
            exp_end = entry.get("expand_end_sec")
            cur_start = float(rec.get("start") or 0.0)
            cur_end = float(rec.get("end") or cur_start)
            changed_edges = False
            if isinstance(exp_start, (int, float)) and not isinstance(exp_start, bool) and math.isfinite(exp_start) and exp_start > 0:
                delta_s = min(20.0, float(exp_start))
                cur_start = max(0.0, cur_start - delta_s)
                changed_edges = True
            if isinstance(exp_end, (int, float)) and not isinstance(exp_end, bool) and math.isfinite(exp_end) and exp_end > 0:
                delta_e = min(15.0, float(exp_end))
                cur_end = cur_end + delta_e
                if source_duration and source_duration > 0:
                    cur_end = min(float(source_duration), cur_end)
                changed_edges = True
            if changed_edges and cur_end > cur_start:
                rec["start"] = round(cur_start, 2)
                rec["end"] = round(cur_end, 2)
                rec["duration"] = round(cur_end - cur_start, 2)
        return updated

    def rerank_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        ai_mode: str = "ollama",
        filter_provider: str = "ollama",
        companion_provider: str = "claude",
        model: str | None = None,
        source_meta: dict[str, Any] | None = None,
        sentences: list[dict[str, Any]] | None = None,
        dossier: dict[str, Any] | None = None,
        golden_examples: list[dict[str, Any]] | None = None,
        max_per_archetype: int | None = None,
        keep_overflow: bool = True,
    ) -> dict[str, Any]:
        if ai_mode not in VALID_AI_MODES:
            raise ValueError(f"ai_mode inválido '{ai_mode}'. Escolha: {', '.join(VALID_AI_MODES)}")

        if not candidates or ai_mode == "heuristic":
            return {"candidates": [dict(c) for c in candidates], "llm_mode_used": "heuristic"}

        enriched_all = attach_neighbor_context(candidates, sentences) if sentences else [dict(c) for c in candidates]
        source_duration = (source_meta or {}).get("duration")

        if len(enriched_all) <= 60:
            ranked = sorted(enriched_all, key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0))))
        else:
            # Garante cobertura do vídeo inteiro (top 35 por nota + 25 distribuídos ao longo da linha do tempo)
            by_score = sorted(enriched_all, key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0))))
            top_part = by_score[:35]
            seen_ids = {id(x) for x in top_part}
            by_time = [x for x in sorted(enriched_all, key=lambda c: float(c.get("start", 0.0))) if id(x) not in seen_ids]
            step = max(1.0, len(by_time) / 25.0)
            time_part = []
            idx_f = 0.0
            while int(idx_f) < len(by_time) and len(time_part) < 25:
                time_part.append(by_time[int(idx_f)])
                idx_f += step
            ranked = sorted(top_part + time_part, key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0))))

        def _context_preamble() -> str:
            blocks: list[str] = []
            if isinstance(source_meta, dict):
                meta_lines = []
                if source_meta.get("title"):
                    meta_lines.append(f"Título: {source_meta['title']}")
                if source_meta.get("channel"):
                    meta_lines.append(f"Canal: {source_meta['channel']}")
                chapters = source_meta.get("chapters") or []
                if chapters:
                    ch_str = "; ".join(f"{int(c.get('start_time', 0))}s {c.get('title', '')}" for c in chapters[:12])
                    meta_lines.append(f"Capítulos: {ch_str}")
                if meta_lines:
                    blocks.append("CONTEXTO DO VÍDEO:\n" + "\n".join(meta_lines))
            if isinstance(dossier, dict):
                cb = "; ".join(str(x) for x in (dossier.get("cultural_callbacks") or [])[:6])
                dt = "; ".join(str(x) for x in (dossier.get("hot_details_to_watch") or [])[:5])
                blocks.append(
                    f"DOSSIÊ CULTURAL ({dossier.get('display_name') or dossier.get('slug')}):\n"
                    f"Callbacks/Memes: {cb}\nDetalhes: {dt}"
                )
            if golden_examples:
                ex_lines = [
                    f"- [{ex.get('id')}] ({ex.get('archetype')}/{ex.get('tier')}): {ex.get('summary')} | Banner: {ex.get('ideal_context_banner')}"
                    for ex in golden_examples[:6]
                ]
                blocks.append("EXEMPLOS OURO (FEW-SHOT):\n" + "\n".join(ex_lines))
            return ("\n\n".join(blocks) + "\n\n") if blocks else ""

        def _row_for(idx: int, item: dict[str, Any], include_triage: bool = False) -> dict[str, Any]:
            row: dict[str, Any] = {
                "index": idx,
                "start": item.get("start"),
                "end": item.get("end"),
                "overall": item.get("overall"),
                "text": str(item.get("text", ""))[:360],
            }
            if item.get("pre_context"):
                row["pre_context"] = str(item["pre_context"])[:200]
            if item.get("post_context"):
                row["post_context"] = str(item["post_context"])[:180]
            if item.get("track_origin"):
                row["track_origin"] = item["track_origin"]
            if item.get("has_visual_deictic"):
                row["has_visual_deictic"] = True
            if include_triage and item.get("reason"):
                row["triagem_filtro"] = str(item["reason"])[:180]
            return row

        def _payload_batches(
            items: list[dict[str, Any]],
            system_prompt: str,
            *,
            include_triage: bool = False,
            include_context: bool = True,
        ) -> list[str]:
            preamble = _context_preamble() if include_context else ""
            prefix = "Triagem do Filtro Inicial:\n" if include_triage else ""
            marker = "CANDIDATOS JSON:\n" if preamble else ""
            header_str = preamble + prefix + marker
            budget = max(4000, MAX_CLI_PROMPT_CHARS - len(system_prompt) - len(header_str))

            batches: list[list[dict[str, Any]]] = []
            cur_batch: list[dict[str, Any]] = []
            cur_len = 2
            for i, item in enumerate(items):
                row = _row_for(i, item, include_triage=include_triage)
                row_len = len(json.dumps(row, ensure_ascii=False)) + 2
                if cur_batch and (cur_len + row_len) > budget:
                    batches.append(cur_batch)
                    cur_batch = []
                    cur_len = 2
                cur_batch.append(row)
                cur_len += row_len
            if cur_batch:
                batches.append(cur_batch)
            return [header_str + json.dumps(batch, ensure_ascii=False) for batch in batches]

        def _call_batched(
            provider_name: str,
            model_name: str | None,
            system_prompt: str,
            items: list[dict[str, Any]],
            *,
            include_triage: bool = False,
            include_context: bool = True,
        ) -> list[dict[str, Any]]:
            all_entries: list[dict[str, Any]] = []
            payloads = _payload_batches(
                items, system_prompt, include_triage=include_triage, include_context=include_context
            )
            total_batches = len(payloads)
            for b_idx, payload in enumerate(payloads, 1):
                print(f"  [editor {provider_name} lote {b_idx}/{total_batches}] avaliando candidatos...", flush=True)
                raw = self.provider_runner(provider_name, model_name, system_prompt, payload)
                parsed = _extract_json_array(raw)
                if parsed:
                    all_entries.extend(parsed)
            return all_entries

        if ai_mode in VALID_PROVIDERS:
            parsed = _call_batched(ai_mode, model, COMPANION_SYSTEM_PROMPT, ranked, include_triage=False, include_context=True)
            if not parsed:
                return {"candidates": [dict(c) for c in candidates], "llm_mode_used": "heuristic"}
            updated = self._apply_entries(ranked, parsed, mode_label=ai_mode, source_duration=source_duration)
            if max_per_archetype is not None and any(c.get("archetype") for c in updated):
                updated = mmr_diversify(updated, max_per_archetype=max_per_archetype, keep_overflow=keep_overflow)
            else:
                updated.sort(key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0))))
            return {"candidates": updated, "llm_mode_used": ai_mode}

        # Modo Dupla: Stage 1 (filter_provider) -> Stage 2 (companion_provider)
        if filter_provider not in VALID_PROVIDERS or companion_provider not in VALID_PROVIDERS:
            raise ValueError("filter_provider e companion_provider devem ser ollama, claude ou gemini.")

        mode_label = f"dupla:{filter_provider}->{companion_provider}"
        parsed_filter = _call_batched(filter_provider, None, FILTER_SYSTEM_PROMPT, ranked, include_triage=False, include_context=False)
        if parsed_filter:
            after_filter = self._apply_entries(ranked, parsed_filter, mode_label=filter_provider, accumulate=False, source_duration=source_duration)
        else:
            after_filter = [dict(c) for c in ranked]

        top_filtered = sorted(
            after_filter, key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0)))
        )[:16]

        parsed_companion = _call_batched(
            companion_provider,
            model,
            COMPANION_SYSTEM_PROMPT,
            top_filtered,
            include_triage=True,
            include_context=True,
        )
        if parsed_companion:
            final_list = self._apply_entries(
                top_filtered, parsed_companion, mode_label=mode_label, accumulate=True, source_duration=source_duration
            )
        else:
            final_list = [dict(c, llm_mode_used=mode_label) for c in top_filtered]

        if max_per_archetype is not None and any(c.get("archetype") for c in final_list):
            final_list = mmr_diversify(final_list, max_per_archetype=max_per_archetype)
        final_list.sort(key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0))))
        return {"candidates": final_list, "llm_mode_used": mode_label}
