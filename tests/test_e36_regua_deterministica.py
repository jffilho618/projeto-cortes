"""3.6.2 — régua justa: o controle de 2026-11-21 mostrou que só re-rodar o Qwen muda a P@5 de uma live em até 0,27.

Correções da medição (o uso normal do motor não muda):
1. no conjunto de prova (projeto em modo cego) o Editor-Chefe local roda determinístico (temperatura 0, semente fixa);
2. o benchmark mede também a etapa ANTES do Editor-Chefe (a lista de candidatos da descoberta), sem sorteio.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _capture(monkeypatch):
    import picorte.ai.llm_router as lr

    sent = []

    def fake_urlopen(req, timeout=None):
        sent.append(json.loads(req.data.decode("utf-8")))
        return _Resp(json.dumps({"message": {"content": "[]"}}).encode("utf-8"))

    monkeypatch.setattr(lr.urllib.request, "urlopen", fake_urlopen)
    return lr, sent


def test_deterministic_router_sends_temperature_zero_and_fixed_seed(monkeypatch):
    lr, sent = _capture(monkeypatch)
    lr.LLMRouter(ollama_model="qwen3.5:9b", deterministic=True)._run_provider("ollama", None, "s", "u")
    assert sent[0]["options"]["temperature"] == 0
    assert sent[0]["options"]["seed"] == lr.BENCHMARK_SEED


def test_normal_router_keeps_model_default_sampling(monkeypatch):
    lr, sent = _capture(monkeypatch)
    lr.LLMRouter(ollama_model="qwen3.5:9b")._run_provider("ollama", None, "s", "u")
    assert "temperature" not in sent[0]["options"] and "seed" not in sent[0]["options"]


def _workdir_for_select(tmp_path: Path, blind: bool) -> Path:
    cand = {"start": 10.0, "end": 40.0, "duration": 30.0, "overall": 8.5, "raw_score": 8.5, "text": "olha isso",
            "hook": "olha isso", "score_parts": {}, "evidence": {}}
    (tmp_path / "candidates.json").write_text(json.dumps({"candidates": [cand], "source_duration": 600.0}),
                                              encoding="utf-8")
    (tmp_path / "project.json").write_text(json.dumps({"options": {"benchmark_blind": blind}, "source_meta": {}}),
                                           encoding="utf-8")
    return tmp_path


class _Stop(Exception):
    pass


@pytest.mark.parametrize("blind", [True, False])
def test_select_uses_deterministic_editor_only_in_the_test_set(tmp_path, monkeypatch, blind):
    import picorte.ai.llm_router as lr
    import score_clips

    seen = {}

    def fake_router(**kwargs):
        seen.update(kwargs)
        raise _Stop()

    monkeypatch.setattr(lr, "LLMRouter", fake_router)
    with pytest.raises(_Stop):
        score_clips.select(_workdir_for_select(tmp_path, blind), ai_mode="ollama")
    assert seen.get("deterministic", False) is blind


# ---------------------------------------------------------------- benchmark antes do Editor-Chefe

def _seed(ts, text="lance"):
    return {"start": 0.0, "end": 0.0, "timestamp_s": ts, "text": text, "score_parts": {"comment_likes": 0}}


def test_run_benchmark_also_measures_candidates_before_the_editor(tmp_path):
    from picorte.engine import benchmark as b

    d = tmp_path / "projects" / "p1"
    d.mkdir(parents=True)
    (d / "project.json").write_text(json.dumps({"id": "p1", "source": "https://youtu.be/AAAAAAAAAAA", "updated": 1.0,
                                                "options": {"benchmark_blind": True},
                                                "source_meta": {"duration": 1000.0}}), encoding="utf-8")
    (d / "segments.json").write_text(json.dumps([{"start": 0.0, "end": 30.0, "rank": 1}]), encoding="utf-8")
    cands = [{"start": 900.0 - 100 * i, "end": 930.0 - 100 * i, "overall": 9.0 - i} for i in range(10)]
    (d / "candidates.json").write_text(json.dumps({"candidates": cands}), encoding="utf-8")
    (d / "comment_seeds.json").write_text(json.dumps([_seed(915.0), _seed(615.0)]), encoding="utf-8")

    rep = b.run_benchmark(tmp_path / "projects", tmp_path / "out", date="2026-11-21")
    pre = rep["vods"][0]["pre_editor"]
    assert pre["candidatos"] == 10
    assert pre["k"]["10"]["acertos"] == 2            # 900 e 600 acertam; ordem pela nota do motor
    assert pre["cobertura"] == pytest.approx(1.0)    # todo momento do público tem ao menos um candidato
    assert rep["media_pre_editor"]["k"]["10"]["precisao"] == pytest.approx(0.2)
