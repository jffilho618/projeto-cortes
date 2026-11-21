"""Etapa 1b — Keyframes (3.5.4) opcionais e desligados por padrão: o Editor-Chefe passa a "ver" 3 frames dos
candidatos que dependem da tela, via Claude Sonnet (assinatura, `claude -p`), em UMA chamada por VOD.

Decisão do dono (2026-11-20). Teste real: Sonnet descreve fielmente; Haiku alucinou → não usar Haiku.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest


def test_option_is_off_by_default_and_validated():
    import projects

    assert projects.DEFAULT_OPTIONS["keyframes"] is False
    assert projects.validate_options({"keyframes": True})["keyframes"] is True
    with pytest.raises(ValueError):
        projects.validate_options({"keyframes": "sim"})


def test_toggling_keyframes_invalidates_selection_cache():
    import projects

    base = projects.validate_options({})
    k1 = projects.score_keys("t", {"words": []}, base)[1]
    k2 = projects.score_keys("t", {"words": []}, {**base, "keyframes": True})[1]
    assert k1 != k2


def test_claude_vision_command_uses_sonnet_and_read_only_access(tmp_path: Path):
    from picorte.engine.multimodal_keyframes import build_claude_vision_cmd

    cmd = build_claude_vision_cmd("claude", "prompt", tmp_path)
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    assert cmd[cmd.index("--allowedTools") + 1] == "Read"
    assert cmd[cmd.index("--add-dir") + 1] == str(tmp_path)
    assert "--output-format" in cmd


def _frames(video, start, end):
    return [np.full((90, 160, 3), (40, 90, 40), dtype=np.uint8) for _ in range(5)]


def test_batch_describer_makes_one_call_and_maps_descriptions(tmp_path: Path):
    from picorte.engine.multimodal_keyframes import describe_keyframes_batch

    cands = [{"start": 10.0, "end": 20.0, "text": "olha isso", "has_visual_deictic": True, "overall": 7.0},
             {"start": 40.0, "end": 55.0, "text": "repara na mão", "has_visual_deictic": True, "overall": 7.5}]
    calls = []

    def runner(prompt, workdir):
        calls.append(prompt)
        # Como o modelo real: lê no prompt qual índice corresponde a cada fala.
        idx_of = {line.split('fala: "')[1].split('"')[0]: int(line[1:line.index("]")])
                  for line in prompt.splitlines() if line.startswith("[")}
        return json.dumps([{"index": idx_of["olha isso"], "visao": "carro voando sobre a ponte"},
                           {"index": idx_of["repara na mão"], "visao": "incerto"}]), 0.12

    out = describe_keyframes_batch(cands, "video.mp4", tmp_path, runner=runner, frame_sampler=_frames)
    assert len(calls) == 1
    assert out["described"] == 1  # "incerto" não vira descrição
    assert out["candidates"][0]["visual_description"] == "carro voando sobre a ponte"
    assert "visual_description" not in out["candidates"][1]
    assert out["cost_usd"] == 0.12
    assert prompt_mentions_all_frames(calls[0], tmp_path)


def prompt_mentions_all_frames(prompt: str, folder: Path) -> bool:
    return len(list(folder.rglob("*.jpg"))) == 6 and all(str(p) in prompt for p in folder.rglob("*.jpg"))


def test_editor_chief_receives_visual_description():
    from picorte.ai.llm_router import LLMRouter

    prompts = []

    def fake(provider, model, system_prompt, user_prompt):
        prompts.append(user_prompt)
        rows = json.loads(user_prompt[user_prompt.index("["):])
        return json.dumps([{"index": r["index"], "adjustment": 0.0, "reason": "ok"} for r in rows])

    cand = {"start": 1.0, "end": 9.0, "overall": 8.0, "text": "olha isso", "visual_description": "carro voando"}
    LLMRouter(provider_runner=fake).rerank_candidates([cand], ai_mode="claude")
    rows = json.loads(prompts[0][prompts[0].index("["):])
    assert rows[0]["visao"] == "carro voando"


def _workdir(tmp_path: Path) -> Path:
    cands = [{"start": 10.0, "end": 40.0, "duration": 30.0, "overall": 7.4, "raw_score": 7.4, "text": "olha isso aqui",
              "hook": "olha isso", "evidence": {}, "score_parts": {}, "has_visual_deictic": True}]
    (tmp_path / "candidates.json").write_text(json.dumps({"version": 1, "mode": "heuristic", "candidates": cands}),
                                              encoding="utf-8")
    (tmp_path / "transcript.json").write_text(json.dumps({"words": [], "duration": 60.0}), encoding="utf-8")
    (tmp_path / "discovery.mp4").write_bytes(b"v")
    return tmp_path


def _router_capture(monkeypatch, seen):
    from picorte.ai import llm_router

    def rerank(self, c, **k):
        seen.extend(c)
        return {"candidates": [dict(x, archetype="descoberta_detalhe") for x in c], "llm_mode_used": "claude"}

    monkeypatch.setattr(llm_router.LLMRouter, "rerank_candidates", rerank)


def test_select_runs_keyframes_only_when_enabled(tmp_path: Path, monkeypatch):
    import score_clips
    from picorte.engine import multimodal_keyframes as mk

    wd = _workdir(tmp_path)
    used = []
    monkeypatch.setattr(mk, "describe_keyframes_batch", lambda cands, video, out_dir, **k: used.append(video) or {
        "candidates": [dict(c, visual_description="detalhe na mão") for c in cands], "described": len(cands),
        "cost_usd": 0.2})
    seen = []
    _router_capture(monkeypatch, seen)
    score_clips.select(wd, min_score=0.0, ai_mode="claude")
    assert used == []
    score_clips.select(wd, min_score=0.0, ai_mode="claude", keyframes=True)
    assert used and used[0].endswith("discovery.mp4")
    assert any(c.get("visual_description") == "detalhe na mão" for c in seen)


def test_keyframes_failure_is_recorded_and_selection_continues(tmp_path: Path, monkeypatch):
    import score_clips
    from picorte.engine import health
    from picorte.engine import multimodal_keyframes as mk

    wd = _workdir(tmp_path)
    monkeypatch.setattr(mk, "describe_keyframes_batch",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("claude fora")))
    _router_capture(monkeypatch, [])
    segs, _ = score_clips.select(wd, min_score=0.0, ai_mode="claude", keyframes=True)
    assert segs
    assert health.load(wd)["keyframes"]["status"] == "failed"
