"""3.6.5 — silêncio digital, falha técnica, ouro com 2 sinais, standalone, confiança do projeto e heatmap fraco."""
from __future__ import annotations

import json

import numpy as np
import pytest

FLOOR = -80.0


def _rms(n, mute=()):
    r = np.full(n, -25.0)
    for a, b in mute:
        r[a:b] = FLOOR
    return r


# ---------------------------------------------------------------- Task 1: silêncio digital

def test_tres_segundos_no_piso_viram_um_trecho_mudo():
    from picorte.engine.confidence import digital_silence_ranges

    assert digital_silence_ranges(_rms(60, mute=[(10, 13)])) == [(10.0, 13.0)]


def test_um_segundo_no_piso_nao_e_silencio_digital():
    from picorte.engine.confidence import digital_silence_ranges

    assert digital_silence_ranges(_rms(60, mute=[(10, 11)])) == []


def test_audio_baixo_de_verdade_nao_e_silencio_digital():
    from picorte.engine.confidence import digital_silence_ranges

    assert digital_silence_ranges(np.full(60, -52.0)) == []


def test_fracao_de_silencio_no_corte():
    from picorte.engine.confidence import silence_fraction

    assert silence_fraction(0.0, 20.0, [(10.0, 15.0)]) == pytest.approx(0.25)
    assert silence_fraction(0.0, 20.0, []) == 0.0


def test_corte_com_mais_de_20_por_cento_mudo_sai():
    from picorte.engine.confidence import drop_muted_candidates

    cands = [{"start": 0.0, "end": 20.0, "hook": "mudo"}, {"start": 30.0, "end": 50.0, "hook": "ok"}]
    kept, dropped = drop_muted_candidates(cands, [(10.0, 15.0), (45.0, 47.0)])
    assert [c["hook"] for c in kept] == ["ok"]
    assert dropped == 1


# ---------------------------------------------------------------- Task 2: falha técnica

def test_volta_do_silencio_com_chat_caiu_vira_falha_tecnica():
    from picorte.engine.confidence import tag_technical_failures

    cands = [{"start": 95.0, "end": 130.0}]
    chat = [{"t": 125.0, "text": "caiu a live?"}, {"t": 126.0, "text": "F"}]
    out = tag_technical_failures(cands, [(90.0, 100.0)], chat, delay_s=20)
    assert "falha_tecnica" in out[0]["tags"]
    assert out[0]["archetype_hint"] == "chat_trolagem"


def test_sem_chat_de_queda_nao_marca():
    from picorte.engine.confidence import tag_technical_failures

    cands = [{"start": 95.0, "end": 130.0}]
    chat = [{"t": 125.0, "text": "kkkkk"}]
    out = tag_technical_failures(cands, [(90.0, 100.0)], chat, delay_s=20)
    assert "falha_tecnica" not in out[0].get("tags", [])


def test_corte_que_nao_contem_a_volta_do_silencio_nao_marca():
    from picorte.engine.confidence import tag_technical_failures

    cands = [{"start": 300.0, "end": 330.0}]
    out = tag_technical_failures(cands, [(90.0, 100.0)], [{"t": 125.0, "text": "travou"}], delay_s=20)
    assert "falha_tecnica" not in out[0].get("tags", [])


# ---------------------------------------------------------------- Task 3: ouro com 2 sinais + confiança

def test_ouro_so_com_a_opiniao_do_editor_vira_forte():
    from picorte.engine.confidence import enforce_gold_rule

    cands = [{"tier": "ouro", "evidence": {}}]
    assert enforce_gold_rule(cands) == 1
    assert cands[0]["tier"] == "forte"
    assert "ouro_rebaixado" in cands[0]


def test_ouro_com_chat_e_riso_medidos_fica_ouro():
    from picorte.engine.confidence import enforce_gold_rule, independent_signals

    c = {"tier": "ouro", "evidence": {"laugh": 0.7, "chat_measured": True, "chat": 7.2}}
    assert set(independent_signals(c)) == {"riso", "chat"}
    assert enforce_gold_rule([c]) == 0
    assert c["tier"] == "ouro"


def test_callback_quieto_com_batedor_e_fala_pode_ser_ouro():
    """Pilar: ouro não se mede por decibéis — leitura do batedor + pista de fala são 2 sinais independentes."""
    from picorte.engine.confidence import independent_signals

    c = {"tier": "ouro", "track_origin": "full_vod_scout", "archetype_hint": "nobada_vacilo", "evidence": {}}
    assert set(independent_signals(c)) == {"batedor", "fala"}


def test_sinais_vem_do_conteudo_e_nao_da_pista_que_pegou_o_candidato():
    """Achado do batedor com fala de detetive continua tendo o sinal 'fala' (cada candidato fica numa pista só)."""
    from picorte.engine.confidence import independent_signals

    c = {"track_origin": "full_vod_scout", "evidence": {},
         "text": "Deixa eu ver se a Rockstar corrigiu a animação da geladeira. Olha a mão dele!"}
    assert set(independent_signals(c)) == {"batedor", "fala"}


def test_achado_do_batedor_perto_do_heatmap_tambem_e_marcado():
    from picorte.engine.multitrack import build_multitrack_pool

    scout = [{"start": 1400.0, "end": 1424.0, "overall": 8.0, "hook": "scout", "text": "x"}]
    pool = build_multitrack_pool([], scout_candidates=scout, heatmap_peaks=[{"center": 1412.0}], max_total=5)
    assert pool[0]["near_heatmap"] is True


def test_chat_nao_medido_nao_conta():
    from picorte.engine.confidence import independent_signals

    assert "chat" not in independent_signals({"evidence": {"chat": 9.0}})


def test_confianca_do_projeto_lista_o_que_rodou():
    from picorte.engine.confidence import project_confidence

    health = {"comment_seeds": {"status": "ok"}, "prosody": {"status": "ok"}, "chat": {"status": "na"},
              "vision": {"status": "failed"}, "editor": {"status": "ok"}, "outra_coisa": {"status": "ok"}}
    conf = project_confidence(health)
    assert set(conf["sinais_ok"]) == {"comment_seeds", "prosody", "editor"}
    assert conf["sinais_falhos"] == ["vision"]
    assert "chat" in conf["sinais_ausentes"]
    assert 0.0 < conf["nota"] < 1.0


# ---------------------------------------------------------------- Task 4: standalone

def test_editor_grava_standalone():
    from picorte.ai.llm_router import COMPANION_SYSTEM_PROMPT, LLMRouter

    assert "standalone" in COMPANION_SYSTEM_PROMPT

    def runner(provider, model, system, payload):
        rows = json.loads(payload[payload.index("[{"):])
        return json.dumps([{"index": r["index"], "adjustment": 0.5, "standalone": 3.5} for r in rows])

    out = LLMRouter(provider_runner=runner).rerank_candidates(
        [{"start": 1.0, "end": 30.0, "overall": 7.0, "text": "piada interna"}], ai_mode="claude")["candidates"]
    assert out[0]["standalone"] == 3.5


def test_corte_que_nao_se_entende_sozinho_vai_para_longo_ou_compilacao():
    from picorte.engine.confidence import split_standalone

    segs = [{"start": 0, "end": 40, "standalone": 3.0}, {"start": 50, "end": 90, "standalone": 8.0},
            {"start": 100, "end": 140}]
    shorts, longos = split_standalone(segs)
    assert [s["start"] for s in shorts] == [50, 100]
    assert [s["start"] for s in longos] == [0]
    assert "motivo" in longos[0]


# ---------------------------------------------------------------- Task 5: heatmap fraco no Short

def test_semente_do_heatmap_deixou_de_dominar():
    from score_clips import heatmap_seed_overall

    assert heatmap_seed_overall(1.0) == pytest.approx(7.2)  # antes: 8.9
    assert heatmap_seed_overall(0.0) == pytest.approx(6.6)  # antes: 7.4


def test_heatmap_da_bonus_fraco_no_short_e_forte_no_longo():
    from picorte.engine.multitrack import build_multitrack_pool

    short = {"start": 100.0, "end": 130.0, "overall": 7.0, "hook": "short", "text": "a"}
    longo = {"start": 1000.0, "end": 1200.0, "overall": 7.0, "hook": "longo", "text": "b"}
    peaks = [{"center": 115.0}, {"center": 1100.0}]
    pool = build_multitrack_pool([short, longo], heatmap_peaks=peaks, max_total=10)
    by = {c["hook"]: c for c in pool}
    assert by["short"]["near_heatmap"] is True
    assert by["short"]["heatmap_bonus"] == pytest.approx(0.3)
    assert by["longo"]["heatmap_bonus"] == pytest.approx(1.2)
