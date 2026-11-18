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
import urllib.request
from typing import Any, Callable

from picorte.config import detect_gpu_profile, resolve_cli_binary
from picorte.engine.vram_runner import VRAMRunner

VALID_PROVIDERS = ("ollama", "claude", "gemini")
VALID_AI_MODES = ("heuristic", "ollama", "claude", "gemini", "dupla")

FILTER_SYSTEM_PROMPT = (
    "Você é o Filtro Inicial de cortes virais de games (Picorte). "
    "Avalie cada candidato de transcrição e retorne APENAS um array JSON com objetos: "
    '{"index": int, "adjustment": float (-1.0 a 1.0), "reason": str}.'
)

COMPANION_SYSTEM_PROMPT = (
    "Você é o Editor-Chefe de cortes de games em português do Brasil (Picorte). "
    "Revise os candidatos (considerando as notas da Triagem quando presentes) e retorne APENAS um array JSON com objetos: "
    '{"index": int, "adjustment": float (-1.0 a 1.0), "reason": str, '
    '"proposed_title": str, "context_banner_2s": str (até 8 palavras), '
    '"thumbnail_words": str (2-3 palavras em caixa alta), "pinned_comment_debate": str}.'
)


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
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=True)
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
                if model:
                    cmd.extend(["--model", model])
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=True)
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
            adj_clamped = max(-1.0, min(1.0, float(adj)))
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
                rec["reason"] = f"{old_reason} | {reason}".strip(" |")[:220]
            for field in ("proposed_title", "context_banner_2s", "thumbnail_words", "pinned_comment_debate"):
                val = entry.get(field)
                if isinstance(val, str) and val.strip():
                    rec[field] = val.strip()
                    if field == "proposed_title" and not rec.get("hook"):
                        rec["hook"] = val.strip()
        return updated

    def rerank_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        ai_mode: str = "ollama",
        filter_provider: str = "ollama",
        companion_provider: str = "claude",
        model: str | None = None,
    ) -> dict[str, Any]:
        if ai_mode not in VALID_AI_MODES:
            raise ValueError(f"ai_mode inválido '{ai_mode}'. Escolha: {', '.join(VALID_AI_MODES)}")

        if not candidates or ai_mode == "heuristic":
            return {"candidates": [dict(c) for c in candidates], "llm_mode_used": "heuristic"}

        ranked = sorted(candidates, key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0))))[:50]

        def _payload_for(items: list[dict[str, Any]], include_triage: bool = False) -> str:
            rows = []
            for i, item in enumerate(items):
                row: dict[str, Any] = {
                    "index": i,
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "overall": item.get("overall"),
                    "text": str(item.get("text", ""))[:450],
                }
                if include_triage and item.get("reason"):
                    row["triagem_filtro"] = item["reason"]
                rows.append(row)
            prefix = "Triagem do Filtro Inicial:\n" if include_triage else ""
            return prefix + json.dumps(rows, ensure_ascii=False)

        if ai_mode in VALID_PROVIDERS:
            raw = self.provider_runner(ai_mode, model, COMPANION_SYSTEM_PROMPT, _payload_for(ranked))
            parsed = _extract_json_array(raw)
            if not parsed:
                return {"candidates": [dict(c) for c in candidates], "llm_mode_used": "heuristic"}
            updated = self._apply_entries(ranked, parsed, mode_label=ai_mode)
            updated.sort(key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0))))
            return {"candidates": updated, "llm_mode_used": ai_mode}

        # Modo Dupla: Stage 1 (filter_provider) -> Stage 2 (companion_provider)
        if filter_provider not in VALID_PROVIDERS or companion_provider not in VALID_PROVIDERS:
            raise ValueError("filter_provider e companion_provider devem ser ollama, claude ou gemini.")

        mode_label = f"dupla:{filter_provider}->{companion_provider}"
        raw_filter = self.provider_runner(filter_provider, None, FILTER_SYSTEM_PROMPT, _payload_for(ranked))
        parsed_filter = _extract_json_array(raw_filter)
        if parsed_filter:
            after_filter = self._apply_entries(ranked, parsed_filter, mode_label=filter_provider, accumulate=False)
        else:
            after_filter = [dict(c) for c in ranked]

        top_filtered = sorted(
            after_filter, key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0)))
        )[:12]

        raw_companion = self.provider_runner(
            companion_provider,
            model,
            COMPANION_SYSTEM_PROMPT,
            _payload_for(top_filtered, include_triage=True),
        )
        parsed_companion = _extract_json_array(raw_companion)
        if parsed_companion:
            final_list = self._apply_entries(top_filtered, parsed_companion, mode_label=mode_label, accumulate=True)
        else:
            final_list = [dict(c, llm_mode_used=mode_label) for c in top_filtered]

        final_list.sort(key=lambda c: (-float(c.get("overall", 0.0)), float(c.get("start", 0.0))))
        return {"candidates": final_list, "llm_mode_used": mode_label}
