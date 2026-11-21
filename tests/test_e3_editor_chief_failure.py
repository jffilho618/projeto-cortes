"""Decisão B do dono (2026-11-20): quando o Editor-Chefe (LLM) falhar, o Picorte PARA e pergunta.

Antes: falha/cota esgotada caía em silêncio para o modo sem IA (sem arquétipos, tiers nem títulos) e o projeto
terminava como "concluído". Agora: 1 nova tentativa por lote; se ainda falhar, interrompe com motivo claro.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _cands(n=3):
    return [{"start": float(i * 30), "end": float(i * 30 + 20), "overall": 7.0, "text": f"corte {i}"} for i in range(n)]


def _ok(provider, model, system_prompt, user_prompt):
    rows = json.loads(user_prompt[user_prompt.index("["):])
    return json.dumps([{"index": r["index"], "adjustment": 0.5, "reason": "ok", "archetype": "clutch_fail",
                        "tier": "forte"} for r in rows])


def test_provider_error_is_retried_once_then_stops():
    from picorte.ai.llm_router import EditorChiefUnavailable, LLMRouter

    calls = []

    def quota(provider, model, system_prompt, user_prompt):
        calls.append(provider)
        raise RuntimeError("Quota exceeded for gemini")

    with pytest.raises(EditorChiefUnavailable) as exc:
        LLMRouter(provider_runner=quota).rerank_candidates(_cands(), ai_mode="gemini")
    assert len(calls) == 2
    assert exc.value.provider == "gemini"
    assert "Quota exceeded" in str(exc.value)


def test_unparseable_answer_then_valid_answer_succeeds():
    from picorte.ai.llm_router import LLMRouter

    answers = iter(["desculpe, não consigo", None])

    def flaky(provider, model, system_prompt, user_prompt):
        nxt = next(answers)
        return nxt if nxt is not None else _ok(provider, model, system_prompt, user_prompt)

    res = LLMRouter(provider_runner=flaky).rerank_candidates(_cands(), ai_mode="claude")
    assert res["llm_mode_used"] == "claude"
    assert all(c.get("archetype") for c in res["candidates"])


def test_empty_array_counts_as_failure():
    from picorte.ai.llm_router import EditorChiefUnavailable, LLMRouter

    with pytest.raises(EditorChiefUnavailable):
        LLMRouter(provider_runner=lambda *a: "[]").rerank_candidates(_cands(), ai_mode="gemini")


def test_partial_batch_failure_also_stops(monkeypatch):
    import picorte.ai.llm_router as lr

    monkeypatch.setattr(lr, "MAX_CLI_PROMPT_CHARS", 900)  # força vários lotes
    state = {"n": 0}

    def second_batch_dies(provider, model, system_prompt, user_prompt):
        state["n"] += 1
        if state["n"] >= 2:
            raise RuntimeError("timeout")
        return _ok(provider, model, system_prompt, user_prompt)

    longos = [dict(c, text="fala longa do streamer " * 15) for c in _cands(30)]  # ~30 x 360 chars > 1 lote
    with pytest.raises(lr.EditorChiefUnavailable) as exc:
        lr.LLMRouter(provider_runner=second_batch_dies).rerank_candidates(longos, ai_mode="gemini")
    assert "lote 2/" in str(exc.value)


@pytest.mark.parametrize("dead", ["ollama", "claude"])
def test_dupla_stops_when_either_stage_fails(dead):
    from picorte.ai.llm_router import EditorChiefUnavailable, LLMRouter

    def runner(provider, model, system_prompt, user_prompt):
        if provider == dead:
            raise RuntimeError(f"{provider} fora do ar")
        return _ok(provider, model, system_prompt, user_prompt)

    with pytest.raises(EditorChiefUnavailable) as exc:
        LLMRouter(provider_runner=runner).rerank_candidates(
            _cands(), ai_mode="dupla", filter_provider="ollama", companion_provider="claude")
    assert exc.value.provider == dead


def test_select_never_falls_back_silently(tmp_path: Path, monkeypatch):
    import score_clips
    from picorte.ai import llm_router

    cands = [{"start": 10.0, "end": 40.0, "duration": 30.0, "overall": 8.5, "raw_score": 8.5, "text": "olha isso",
              "hook": "olha isso", "evidence": {}, "score_parts": {}}]
    (tmp_path / "candidates.json").write_text(json.dumps({"version": 1, "mode": "heuristic", "candidates": cands}),
                                              encoding="utf-8")
    (tmp_path / "transcript.json").write_text(json.dumps({"words": [], "duration": 60.0}), encoding="utf-8")

    def dead(*a, **k):
        raise llm_router.EditorChiefUnavailable("gemini", "cota esgotada")

    monkeypatch.setattr(llm_router.LLMRouter, "rerank_candidates", dead)
    with pytest.raises(llm_router.EditorChiefUnavailable):
        score_clips.select(tmp_path, min_score=0.0, ai_mode="gemini")
    assert not (tmp_path / "segments.json").exists()


def test_user_message_explains_what_was_kept_and_what_to_do():
    from picorte.ai.llm_router import EditorChiefUnavailable

    msg = str(EditorChiefUnavailable("gemini", "cota esgotada"))
    assert "Editor-Chefe" in msg and "gemini" in msg
    assert "salv" in msg.lower()  # download/transcrição/descoberta ficaram salvos
    assert "Claude" in msg and "sem IA" in msg
