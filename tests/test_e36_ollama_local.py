"""3.6.1 — Editor-Chefe local (Ollama) sem cortar o prompt e sem o bloco de pensamento.

A cota do Gemini acabou no preparo do conjunto de prova (429, 2026-11-21); o dono pediu um modelo local.
O Ollama usa contexto padrão de 2–4 mil tokens e cortaria em silêncio os prompts do Editor-Chefe (~6 mil).
"""
from __future__ import annotations

import io
import json

import pytest


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _capture(monkeypatch, content):
    import picorte.ai.llm_router as lr

    sent = []

    def fake_urlopen(req, timeout=None):
        sent.append(json.loads(req.data.decode("utf-8")))
        return _Resp(json.dumps({"message": {"content": content}}).encode("utf-8"))

    monkeypatch.setattr(lr.urllib.request, "urlopen", fake_urlopen)
    return lr, sent


def test_ollama_call_sets_a_context_big_enough_for_the_editor_chief(monkeypatch):
    lr, sent = _capture(monkeypatch, "[]")
    lr.LLMRouter(ollama_model="qwen2.5:7b")._run_provider("ollama", None, "sys", "user")
    assert sent[0]["options"]["num_ctx"] >= 16384


@pytest.mark.parametrize("model", ["qwen3.5:9b", "qwen3:8b", "deepseek-r1:8b"])
def test_thinking_models_have_thinking_turned_off(monkeypatch, model):
    lr, sent = _capture(monkeypatch, "[]")
    lr.LLMRouter(ollama_model=model)._run_provider("ollama", None, "sys", "user")
    assert sent[0]["think"] is False


def test_non_thinking_models_do_not_receive_the_think_flag(monkeypatch):
    lr, sent = _capture(monkeypatch, "[]")
    lr.LLMRouter(ollama_model="qwen2.5:7b")._run_provider("ollama", None, "sys", "user")
    assert "think" not in sent[0]


def test_leftover_think_block_is_stripped_from_the_answer(monkeypatch):
    lr, _ = _capture(monkeypatch, "<think>hmm, vejamos</think>\n[{\"index\": 0}]")
    out = lr.LLMRouter(ollama_model="qwen3.5:9b")._run_provider("ollama", None, "sys", "user")
    assert out == "[{\"index\": 0}]"


# 3.6.2 — resposta longa não pode estourar o prazo (2026-11-22): um lote de 28 candidatos gera ~7 mil tokens,
# ~5 min no Qwen 9b; sem streaming o prazo de 180 s virava "a resposta inteira cabe em 3 min".
def _stream(monkeypatch, chunks):
    import picorte.ai.llm_router as lr

    sent = []

    def fake_urlopen(req, timeout=None):
        sent.append(json.loads(req.data.decode("utf-8")))
        lines = [json.dumps({"message": {"content": c}, "done": False}) for c in chunks]
        lines.append(json.dumps({"message": {"content": ""}, "done": True}))
        return _Resp(("\n".join(lines) + "\n").encode("utf-8"))

    monkeypatch.setattr(lr.urllib.request, "urlopen", fake_urlopen)
    return lr, sent


def test_ollama_answer_is_streamed_so_the_timeout_only_catches_a_silent_server(monkeypatch):
    lr, sent = _stream(monkeypatch, ["[{\"index\"", ": 0}", "]"])
    out = lr.LLMRouter(ollama_model="qwen3.5:9b")._run_provider("ollama", None, "sys", "user")
    assert sent[0]["stream"] is True
    assert out == "[{\"index\": 0}]"


def test_streamed_answer_has_a_total_ceiling(monkeypatch):
    lr, _ = _stream(monkeypatch, ["a"] * 50)
    clock = iter(range(0, 100000, 60))  # cada leitura "leva" 60 s
    monkeypatch.setattr(lr.time, "monotonic", lambda: next(clock))
    with pytest.raises(TimeoutError):
        lr.LLMRouter(ollama_model="qwen3.5:9b")._run_provider("ollama", None, "sys", "user")
