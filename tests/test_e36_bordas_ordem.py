"""3.6.4 — bordas por frase, pré-roll do setup, fim após o riso e Editor-Chefe sem viés de ordem.

Tudo com roteador e decodificador falsos: nenhuma chamada a LLM, nenhum ffmpeg.
"""
from __future__ import annotations

import json
import re

import numpy as np
import pytest


def _sents(items):
    return [{"start": s, "end": e, "text": t} for s, e, t in items]


def _rows(payload: str) -> list[dict]:
    """Linhas de candidatos enviadas ao Editor-Chefe (o array JSON no fim do prompt)."""
    return json.loads(payload[payload.index("[{"):])


# ---------------------------------------------------------------- Task 1: bordas por frase

SENTS = _sents([
    (80.0, 84.0, "vamos atravessar a ponte"),
    (85.0, 89.0, "segura a moto aí"),
    (90.0, 94.0, "acelera agora"),
    (100.0, 110.0, "o momento em si"),
    (111.0, 114.0, "kkkk caiu da ponte"),
    (115.0, 118.0, "não acredito"),
])


def _one_candidate_router(entry: dict):
    from picorte.ai.llm_router import LLMRouter

    sent = []

    def runner(provider, model, system, payload):
        sent.append(payload)
        rows = _rows(payload)
        return json.dumps([{**entry, "index": r["index"]} for r in rows])

    return LLMRouter(provider_runner=runner), sent


def test_editor_estende_duas_frases_antes_pelo_comeco_exato_da_frase():
    router, _ = _one_candidate_router({"adjustment": 1.0, "extend_sentences_before": 2})
    cand = [{"start": 100.0, "end": 110.0, "overall": 7.0, "text": "o momento em si"}]
    out = router.rerank_candidates(cand, ai_mode="claude", sentences=SENTS)["candidates"]
    assert out[0]["start"] == 85.0
    assert out[0]["end"] == 110.0


def test_editor_estende_uma_frase_depois_pelo_fim_exato_da_frase():
    router, _ = _one_candidate_router({"adjustment": 1.0, "extend_sentences_after": 1})
    cand = [{"start": 100.0, "end": 110.0, "overall": 7.0, "text": "o momento em si"}]
    out = router.rerank_candidates(cand, ai_mode="claude", sentences=SENTS)["candidates"]
    assert out[0]["end"] == 114.0


def test_pedir_mais_frases_do_que_existem_usa_a_mais_distante():
    router, _ = _one_candidate_router({"adjustment": 1.0, "extend_sentences_before": 9})
    cand = [{"start": 100.0, "end": 110.0, "overall": 7.0, "text": "o momento em si"}]
    out = router.rerank_candidates(cand, ai_mode="claude", sentences=SENTS)["candidates"]
    assert out[0]["start"] == 80.0


def test_contexto_vai_numerado_por_frase():
    router, sent = _one_candidate_router({"adjustment": 0.0})
    cand = [{"start": 100.0, "end": 110.0, "overall": 7.0, "text": "o momento em si"}]
    router.rerank_candidates(cand, ai_mode="claude", sentences=SENTS)
    row = _rows(sent[0])[0]
    assert "[-1] acelera agora" in row["pre_context"]
    assert "[+1] kkkk caiu da ponte" in row["post_context"]


def test_prompt_pede_frases_e_nao_segundos():
    from picorte.ai.llm_router import COMPANION_SYSTEM_PROMPT

    assert "extend_sentences_before" in COMPANION_SYSTEM_PROMPT
    assert "expand_start_sec" not in COMPANION_SYSTEM_PROMPT


# ---------------------------------------------------------------- Task 2: pré-roll do setup

def test_preroll_volta_ao_comeco_da_frase_do_setup():
    from picorte.engine.snap_boundaries import setup_preroll_start

    sents = _sents([(80.0, 88.0, "conversa antiga"), (94.0, 99.0, "olha o que eu vou fazer"),
                    (99.5, 103.0, "o lance")])
    assert setup_preroll_start(sents, 100.0) == 94.0


def test_preroll_desiste_quando_a_frase_comeca_longe_demais():
    from picorte.engine.snap_boundaries import setup_preroll_start

    sents = _sents([(70.0, 101.0, "frase enorme de meio minuto")])
    assert setup_preroll_start(sents, 100.0) is None


def test_preroll_sem_frases_devolve_none():
    from picorte.engine.snap_boundaries import setup_preroll_start

    assert setup_preroll_start([], 100.0) is None


def test_semente_de_chat_comeca_na_frase_do_setup():
    from score_clips import chat_seed_window

    sents = _sents([(80.0, 88.0, "conversa antiga"), (94.0, 99.0, "olha o que eu vou fazer"),
                    (99.5, 103.0, "o lance")])
    pk = {"start": 92.0, "end": 114.0, "cause_second": 100.0}
    ws, we = chat_seed_window(pk, sents, 15, 60, 3600.0)
    assert ws == 94.0
    assert we == 114.0


def test_semente_de_chat_sem_causa_fica_como_antes():
    from score_clips import chat_seed_window

    ws, we = chat_seed_window({"start": 92.0, "end": 114.0}, [], 15, 60, 3600.0)
    assert (ws, we) == (92.0, 114.0)


# ---------------------------------------------------------------- Task 3: fim depois do riso

SR = 16000


def _fake_audio(laugh_until: float):
    """Riso (envelope modulado em 4,5 Hz) até `laugh_until`; depois, ruído de envelope plano."""
    rng = np.random.default_rng(7)

    def decoder(path, start, end):
        t = np.arange(int((end - start) * SR)) / SR + start
        noise = rng.standard_normal(t.size).astype(np.float32)
        env = np.where(t < laugh_until, 0.5 + 0.5 * np.sin(2 * np.pi * 4.5 * t), 1.0)
        return (noise * env).astype(np.float32)

    return decoder


def test_riso_cruzando_o_fim_empurra_o_fim_ate_o_riso_acabar():
    from picorte.engine.prosody_events import extend_end_past_laugh

    segs = [{"start": 70.0, "end": 100.0, "duration": 30.0}]
    out = extend_end_past_laugh(segs, "fake.mp4", decoder=_fake_audio(laugh_until=103.0), max_len=60)
    assert 103.0 <= out[0]["end"] <= 105.0
    assert out[0]["duration"] == pytest.approx(out[0]["end"] - 70.0)
    assert out[0]["evidence"]["end_after_laugh_s"] > 0


def test_sem_riso_o_fim_nao_muda():
    from picorte.engine.prosody_events import extend_end_past_laugh

    segs = [{"start": 70.0, "end": 100.0, "duration": 30.0}]
    out = extend_end_past_laugh(segs, "fake.mp4", decoder=_fake_audio(laugh_until=0.0), max_len=60)
    assert out[0]["end"] == 100.0


def test_riso_respeita_a_duracao_maxima():
    from picorte.engine.prosody_events import extend_end_past_laugh

    segs = [{"start": 70.0, "end": 100.0, "duration": 30.0}]
    out = extend_end_past_laugh(segs, "fake.mp4", decoder=_fake_audio(laugh_until=106.0), max_len=31)
    assert out[0]["end"] == 101.0


def test_erro_no_audio_nao_muda_nada():
    from picorte.engine.prosody_events import extend_end_past_laugh

    def broken(*a):
        raise OSError("sem ffmpeg")

    segs = [{"start": 70.0, "end": 100.0, "duration": 30.0}]
    assert extend_end_past_laugh(segs, "fake.mp4", decoder=broken)[0]["end"] == 100.0


# ---------------------------------------------------------------- Task 4: ordem embaralhada + 2ª passada

def _cands(n):
    return [{"start": 100.0 * i, "end": 100.0 * i + 30.0, "overall": 7.0 + i * 0.01, "text": f"cand{i:02d}"}
            for i in range(n)]


def _order_router(adjust_by_pass: dict[int, dict[str, float]] | None = None, tier="ouro", **kw):
    """Roteador falso: devolve, para cada linha, o ajuste definido pelo texto do candidato e pela passada."""
    from picorte.ai.llm_router import LLMRouter

    calls: list[list[str]] = []

    def runner(provider, model, system, payload):
        rows = _rows(payload)
        calls.append([r["text"] for r in rows])
        table = (adjust_by_pass or {}).get(len(calls), {})
        return json.dumps([{"index": r["index"], "adjustment": table.get(r["text"], 1.0), "tier": tier}
                           for r in rows])

    return LLMRouter(provider_runner=runner, **kw), calls


def test_mesma_semente_mesma_ordem_e_semente_diferente_muda():
    r1, c1 = _order_router()
    r2, c2 = _order_router()
    r3, c3 = _order_router()
    r1.rerank_candidates(_cands(20), ai_mode="claude", order_seed=11)
    r2.rerank_candidates(_cands(20), ai_mode="claude", order_seed=11)
    r3.rerank_candidates(_cands(20), ai_mode="claude", order_seed=12)
    assert c1[0] == c2[0]
    assert c1[0] != c3[0]
    assert c1[0] != sorted(c1[0])  # embaralhado, não na ordem da nota


def test_semente_usada_volta_no_resultado():
    r, _ = _order_router()
    res = r.rerank_candidates(_cands(5), ai_mode="claude", order_seed=42)
    assert res["ordem_semente"] == 42


def test_segunda_passada_so_nos_finalistas():
    r, calls = _order_router()
    r.rerank_candidates(_cands(30), ai_mode="claude", order_seed=5)
    assert len(calls) == 2
    assert len(calls[1]) == 15


def test_discordancia_entre_passadas_marca_confianca_baixa_e_tira_o_ouro():
    r, _ = _order_router({1: {"cand03": 3.0}, 2: {"cand03": -0.5}})
    out = r.rerank_candidates(_cands(5), ai_mode="claude", order_seed=5)["candidates"]
    c3 = next(c for c in out if c["text"] == "cand03")
    assert c3["confianca_baixa"] is True
    assert c3["tier"] == "forte"
    assert c3["llm_adjustment"] == pytest.approx(1.25)


def test_concordancia_usa_a_media_e_mantem_o_ouro():
    r, _ = _order_router({1: {"cand01": 2.0}, 2: {"cand01": 1.0}})
    out = r.rerank_candidates(_cands(5), ai_mode="claude", order_seed=5)["candidates"]
    c1 = next(c for c in out if c["text"] == "cand01")
    assert not c1.get("confianca_baixa")
    assert c1["tier"] == "ouro"
    assert c1["llm_adjustment"] == pytest.approx(1.5)
    assert c1["overall"] == pytest.approx(7.01 + 1.5)


def test_modo_deterministico_usa_a_semente_fixa():
    from picorte.ai.llm_router import BENCHMARK_SEED

    r, _ = _order_router(deterministic=True)
    assert r.rerank_candidates(_cands(5), ai_mode="claude")["ordem_semente"] == BENCHMARK_SEED


def test_dupla_compara_so_notas_do_editor_e_nao_a_do_filtro():
    """Filtro dá −2,5; na 1ª passada o Editor só avalia os pares (+3,0); na 2ª responde por todos (+3,0).

    Os ímpares não têm nota do Editor da 1ª passada, então não podem ser comparados com a nota do filtro.
    """
    from picorte.ai.llm_router import LLMRouter

    editor_calls = []

    def runner(provider, model, system, payload):
        rows = _rows(payload)
        if provider == "ollama":
            return json.dumps([{"index": r["index"], "adjustment": -2.5} for r in rows])
        editor_calls.append(1)
        if len(editor_calls) == 1:
            rows = [r for r in rows if int(r["text"][-2:]) % 2 == 0]
        return json.dumps([{"index": r["index"], "adjustment": 3.0, "tier": "ouro"} for r in rows])

    out = LLMRouter(provider_runner=runner).rerank_candidates(
        _cands(6), ai_mode="dupla", filter_provider="ollama", companion_provider="claude", order_seed=3)
    assert out["confianca_baixa"] == 0
    pares = [c for c in out["candidates"] if int(c["text"][-2:]) % 2 == 0]
    assert pares and all(c["tier"] == "ouro" for c in pares)


def test_modo_heuristico_nao_chama_ninguem():
    r, calls = _order_router()
    r.rerank_candidates(_cands(5), ai_mode="heuristic")
    assert calls == []
