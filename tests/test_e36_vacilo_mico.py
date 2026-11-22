"""3.6.3 — arquétipos `nobada_vacilo` e `mico_constrangimento` (10 → 12), pista "vacilo_mico" e dica dos comentários.

Validação por TDD com transcrições sintéticas (decisão do dono em 2026-11-22: sem re-medição de P@K a cada história).
"""
from __future__ import annotations

import io
import json

NOVOS = ("nobada_vacilo", "mico_constrangimento")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# ---------------------------------------------------------------- Task 1: 12 arquétipos e tabelas

def test_doze_arquetipos_com_tabelas_completas():
    from picorte.engine.activity_segmenter import ACTIVITY_WEIGHTS
    from picorte.engine.archetype_compiler import ARCHETYPE_COMPILATION_TITLES
    from picorte.engine.multitrack import CANONICAL_ARCHETYPES
    from picorte.engine.retention_engine import ARCHETYPE_RETENTION_POLICIES

    assert len(CANONICAL_ARCHETYPES) == 12
    for a in NOVOS:
        assert a in CANONICAL_ARCHETYPES
        assert a in ARCHETYPE_COMPILATION_TITLES
        assert a in ARCHETYPE_RETENTION_POLICIES
    assert ACTIVITY_WEIGHTS["gameplay"]["nobada_vacilo"] > 1.0
    assert ACTIVITY_WEIGHTS["just_chatting"]["mico_constrangimento"] > 1.0


def test_mico_nao_usa_cold_open_porque_precisa_do_setup():
    from picorte.engine.retention_engine import ARCHETYPE_RETENTION_POLICIES

    assert ARCHETYPE_RETENTION_POLICIES["mico_constrangimento"]["use_cold_open"] is False
    assert ARCHETYPE_RETENTION_POLICIES["nobada_vacilo"]["use_cold_open"] is True


def test_prompt_do_editor_chefe_explica_a_diferenca_para_clutch_fail():
    from picorte.ai.llm_router import COMPANION_SYSTEM_PROMPT

    for a in NOVOS:
        assert a in COMPANION_SYSTEM_PROMPT
    assert "erro bobo" in COMPANION_SYSTEM_PROMPT
    assert "dica_arquetipo" in COMPANION_SYSTEM_PROMPT


def test_editor_chefe_aceita_os_novos_arquetipos(monkeypatch):
    import picorte.ai.llm_router as lr

    answer = json.dumps([{"index": 0, "adjustment": 1.0, "archetype": "mico_constrangimento", "tier": "forte"}])

    def fake_urlopen(req, timeout=None):
        return _Resp(json.dumps({"message": {"content": answer}, "done": True}).encode("utf-8"))

    monkeypatch.setattr(lr.urllib.request, "urlopen", fake_urlopen)
    cand = [{"start": 10.0, "end": 40.0, "overall": 7.0, "text": "piada que não colou"}]
    out = lr.LLMRouter(ollama_model="qwen2.5:7b").rerank_candidates(cand, ai_mode="ollama")["candidates"]
    assert out[0]["archetype"] == "mico_constrangimento"


# ---------------------------------------------------------------- Task 2: exemplos ouro

def test_exemplos_ouro_tem_dois_de_cada_novo():
    from collections import Counter

    from picorte.ai.llm_router import load_golden_examples

    c = Counter(ex["archetype"] for ex in load_golden_examples())
    assert c["nobada_vacilo"] >= 2
    assert c["mico_constrangimento"] >= 2


def test_prompt_mostra_exemplos_de_arquetipos_variados():
    from picorte.ai.llm_router import pick_golden_for_prompt

    exs = [{"id": f"a{i}", "archetype": "a"} for i in range(6)] + [{"id": "n1", "archetype": "nobada_vacilo"}]
    picked = pick_golden_for_prompt(exs, limit=3)
    assert [p["archetype"] for p in picked] == ["a", "nobada_vacilo", "a"]


def test_todos_os_arquetipos_dos_exemplos_sao_validos():
    from picorte.ai.llm_router import load_golden_examples
    from picorte.engine.multitrack import CANONICAL_ARCHETYPES

    assert all(ex["archetype"] in CANONICAL_ARCHETYPES for ex in load_golden_examples())


# ---------------------------------------------------------------- Task 3: pista vacilo_mico

def _sents(items):
    return [{"start": s, "end": e, "text": t} for s, e, t in items]


def test_autodepreciacao_com_riso_vira_nobada():
    from picorte.engine.multitrack import vacilo_mico_score

    sents = _sents([(100.0, 104.0, "vou pular aqui de boa"),
                    (104.5, 108.0, "não acredito que eu fiz isso, burro demais")])
    cand = {"start": 100.0, "end": 108.0, "text": " ".join(s["text"] for s in sents),
            "evidence": {"laugh": 0.8}}
    score, hint = vacilo_mico_score(cand, sents)
    assert score >= 1.5
    assert hint == "nobada_vacilo"


def test_piada_silencio_e_vergonha_vira_mico():
    from picorte.engine.multitrack import detect_shock_silence, vacilo_mico_score

    sents = _sents([(200.0, 205.0, "e aí o pato falou: quack, entendeu?"),
                    (207.0, 210.0, "nossa que vergonha kkk ninguém riu")])
    assert detect_shock_silence(sents, 200.0, 210.0) is True
    cand = {"start": 200.0, "end": 210.0, "text": " ".join(s["text"] for s in sents), "evidence": {}}
    score, hint = vacilo_mico_score(cand, sents)
    assert score >= 1.5
    assert hint == "mico_constrangimento"


def test_silencio_sem_reacao_depois_nao_conta():
    from picorte.engine.multitrack import detect_shock_silence

    sents = _sents([(300.0, 304.0, "agora a gente vai pra missão"),
                    (306.0, 310.0, "pega a arma no baú da esquerda")])
    assert detect_shock_silence(sents, 300.0, 310.0) is False


def test_silencio_longo_demais_nao_e_choque():
    from picorte.engine.multitrack import detect_shock_silence

    sents = _sents([(400.0, 404.0, "olha isso"), (409.0, 412.0, "kkkkk que vergonha")])
    assert detect_shock_silence(sents, 400.0, 412.0) is False


def test_riso_da_prosodia_sozinho_nao_basta():
    from picorte.engine.multitrack import vacilo_mico_score

    sents = _sents([(500.0, 510.0, "vamos lá pessoal, mais uma partida")])
    cand = {"start": 500.0, "end": 510.0, "text": sents[0]["text"], "evidence": {"laugh": 0.9}}
    score, hint = vacilo_mico_score(cand, sents)
    assert hint is None


def test_frase_generica_sozinha_nao_basta():
    """Olhada nas 4 lives (2026-11-22): 'realmente não era pra lutar com todo mundo' virava vacilo."""
    from picorte.engine.multitrack import VACILO_MICO_MIN_SCORE, vacilo_mico_score

    sents = _sents([(700.0, 706.0, "realmente não era pra lutar com todo mundo")])
    cand = {"start": 700.0, "end": 706.0, "text": sents[0]["text"], "evidence": {"laugh": 0.6}}
    assert vacilo_mico_score(cand, sents)[1] is None
    sents = _sents([(800.0, 806.0, "esqueci de pegar a arma no baú")])
    cand = {"start": 800.0, "end": 806.0, "text": sents[0]["text"], "evidence": {}}
    assert vacilo_mico_score(cand, sents)[0] < VACILO_MICO_MIN_SCORE


def test_streamer_anunciando_o_corte_conta():
    from picorte.engine.multitrack import vacilo_mico_score

    sents = _sents([(600.0, 606.0, "caí sozinho do prédio, isso vai virar corte")])
    cand = {"start": 600.0, "end": 606.0, "text": sents[0]["text"], "evidence": {"chat_reaction": "riso"}}
    score, hint = vacilo_mico_score(cand, sents)
    assert score >= 1.5
    assert hint == "nobada_vacilo"


def test_vacilo_quieto_sobrevive_a_35_cortes_barulhentos():
    from picorte.engine.multitrack import build_multitrack_pool

    loud = [{"start": 1000.0 + i * 60, "end": 1030.0 + i * 60, "overall": round(9.7 - i * 0.03, 2),
             "hook": f"grito_{i}", "text": "CARAMBA QUE TIRO INSANO EXPLODIU TUDO VAMO!",
             "score_parts": {"energy": 0.95}} for i in range(35)]
    vacilo = {"start": 5000.0, "end": 5012.0, "overall": 5.5, "hook": "vacilo",
              "text": "esqueci de recarregar, que burro, volta volta", "evidence": {"laugh": 0.7},
              "score_parts": {"energy": 0.3}}
    sents = _sents([(c["start"], c["end"], c["text"]) for c in loud + [vacilo]])
    pool = build_multitrack_pool(loud + [vacilo], sentences=sents, max_total=30)
    hooks = {c["hook"]: c for c in pool}
    assert "vacilo" in hooks
    assert hooks["vacilo"]["track_origin"] == "vacilo_mico"
    assert hooks["vacilo"]["archetype_hint"] == "nobada_vacilo"


# ---------------------------------------------------------------- Task 4: comentários e dica para o Editor

def test_comentario_kkkk_vira_dica_de_nobada():
    from picorte.engine.comments_miner import archetype_hint_from_comment

    assert archetype_hint_from_comment("kkkkkkk 12:34 ele pulou no buraco") == "nobada_vacilo"
    assert archetype_hint_from_comment("que vergonha 1:02:10") == "mico_constrangimento"
    assert archetype_hint_from_comment("que música é essa 3:20") is None


def test_merge_comment_seeds_propaga_a_dica():
    from score_clips import merge_comment_seeds

    seeds = [{"start": 10.0, "end": 40.0, "text": "kkkkk", "score_parts": {"comment_likes": 12}}]
    out = merge_comment_seeds([], seeds, [])
    assert out[0]["archetype_hint"] == "nobada_vacilo"


def test_linha_do_editor_chefe_leva_a_dica(monkeypatch):
    import picorte.ai.llm_router as lr

    sent = []

    def fake_urlopen(req, timeout=None):
        sent.append(json.loads(req.data.decode("utf-8")))
        return _Resp(json.dumps({"message": {"content": "[]"}, "done": True}).encode("utf-8"))

    monkeypatch.setattr(lr.urllib.request, "urlopen", fake_urlopen)
    cand = [{"start": 10.0, "end": 40.0, "overall": 7.0, "text": "burro demais", "archetype_hint": "nobada_vacilo"}]
    try:
        lr.LLMRouter(ollama_model="qwen2.5:7b").rerank_candidates(cand, ai_mode="ollama")
    except lr.EditorChiefUnavailable:
        pass  # resposta vazia: só interessa o que foi enviado
    user_msg = sent[0]["messages"][1]["content"]
    assert '"dica_arquetipo": "nobada_vacilo"' in user_msg
