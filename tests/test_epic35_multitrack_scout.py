"""Testes TDD da Story 3.5.2 — Recall Multi-Pista (5 Pistas), Payoff-First Rewind, Full-VOD Scout e Durações Flexíveis."""
from __future__ import annotations

import json

import pytest


def _make_sentences(entries: list[tuple[float, float, str]]) -> list[dict]:
    out = []
    for s, e, txt in entries:
        toks = txt.split()
        dt = (e - s) / max(1, len(toks))
        words = [
            {"word": w, "start": round(s + i * dt, 2), "end": round(s + (i + 0.9) * dt, 2)}
            for i, w in enumerate(toks)
        ]
        out.append({"start": s, "end": e, "text": txt, "words": words})
    return out


def test_canonical_archetypes_and_tiers_contracts():
    from picorte.engine.multitrack import CANONICAL_ARCHETYPES, CANONICAL_TIERS

    assert len(CANONICAL_ARCHETYPES) == 12  # 3.6.3: + nobada_vacilo e mico_constrangimento
    assert set(CANONICAL_ARCHETYPES) == {
        "nobada_vacilo",
        "mico_constrangimento",
        "callback_oculto",
        "caos_coop",
        "rage_tilt",
        "serio_realtalk",
        "polemica_hottake",
        "descoberta_detalhe",
        "clutch_fail",
        "susto_tensao",
        "deadpan_karma",
        "chat_trolagem",
    }
    assert CANONICAL_TIERS == ("ouro", "forte", "experimental")


def test_anti_junk_penalty_filters_subs_sponsors_and_brb_but_keeps_gold():
    from picorte.engine.multitrack import anti_junk_penalty

    assert anti_junk_penalty("Obrigado pelo sub João, valeu pelos 12 meses de prime!") >= 0.25
    assert anti_junk_penalty("Usa meu cupom de desconto no link na descrição, oferecimento da loja.") >= 0.25
    assert anti_junk_penalty("Pera que vou no banheiro, já volto galera, aguenta aí no intervalo.") >= 0.25
    assert anti_junk_penalty("Deixa eu ver se a Rockstar corrigiu a animação da geladeira do trailer.") == 0.0
    assert anti_junk_penalty("Papo reto, sendo sincero com vocês sobre trabalhar com lives.") == 0.0


def test_compute_local_tfidf_highlights_rare_topic_sentences():
    from picorte.engine.multitrack import compute_local_tfidf

    entries = [(i * 5.0, (i + 1) * 5.0, "Vamos andar pelo mapa agora galera vamos lá.") for i in range(25)]
    entries.append((130.0, 138.0, "Olha a geladeira da cozinha, será que a Rockstar corrigiu a animação do Jason?"))
    sents = _make_sentences(entries)

    scores = compute_local_tfidf(sents)
    assert scores[25] > max(scores[i] for i in range(25))


def test_payoff_first_rewind_captures_setup_before_payoff():
    from picorte.engine.multitrack import payoff_first_rewind

    sents = _make_sentences([
        (0.0, 6.0, "Fala pessoal, estamos passeando aqui pela cidade normalmente."),
        (20.0, 28.0, "Relaxa gente, tá super seguro, eu passo dessa ponte fácil demais, confia."),
        (28.0, 35.0, "Vou acelerar com tudo aqui pela direita mantendo o controle."),
        (35.0, 41.0, "Freia freia freia! Foi você, culpa sua, não acredito!"),
        (41.0, 46.0, "Meu deus explodiu o carro inteiro."),
    ])

    rewound = payoff_first_rewind(sents, min_back_sec=12.0, max_back_sec=30.0, min_len=10.0, max_len=60.0)
    assert len(rewound) >= 1
    best = rewound[0]
    # Deve incluir o setup aos 20s e o payoff aos 35-41s
    assert best["start"] <= 22.0
    assert best["end"] >= 40.0
    assert best["track_origin"] == "coop_payoff_nontextual"


def test_multitrack_pool_preserves_quiet_callback_and_realtalk_among_35_loud_clips():
    from picorte.engine.multitrack import build_multitrack_pool

    loud_candidates = []
    for i in range(35):
        t = 100.0 + i * 60.0
        loud_candidates.append({
            "start": t,
            "end": t + 30.0,
            "duration": 30.0,
            "overall": round(9.7 - i * 0.03, 2),
            "hook": f"grito_{i}",
            "text": "CARAMBA QUE TIRO INSANO EXPLODIU TUDO VAMO!",
            "score_parts": {"energy": 0.95, "emotion": 0.8},
        })

    quiet_callback = {
        "start": 2500.0,
        "end": 2528.0,
        "duration": 28.0,
        "overall": 6.1,
        "hook": "geladeira_callback",
        "text": "Espera, deixa eu ver se a Rockstar corrigiu a animação da geladeira do trailer. Olha a mão dele!",
        "score_parts": {"energy": 0.15, "emotion": 0.2},
        "has_visual_deictic": True,
    }
    quiet_realtalk = {
        "start": 2900.0,
        "end": 2948.0,
        "duration": 48.0,
        "overall": 6.0,
        "hook": "papo_reto_serio",
        "text": "Papo reto, sendo sincero com vocês na real, um conselho de verdade sobre saúde mental nos bastidores.",
        "score_parts": {"energy": 0.12, "emotion": 0.4},
    }

    all_cands = loud_candidates + [quiet_callback, quiet_realtalk]
    sents = _make_sentences([(c["start"], c["end"], c["text"]) for c in all_cands])

    pool = build_multitrack_pool(all_cands, sentences=sents, max_total=30)
    hooks = {c["hook"]: c for c in pool}
    assert "geladeira_callback" in hooks
    assert hooks["geladeira_callback"]["track_origin"] == "deictic_detective_callback"
    assert "papo_reto_serio" in hooks
    assert hooks["papo_reto_serio"]["track_origin"] == "serio_polemica_silence"


def test_scout_full_vod_maps_sentence_ids_and_ignores_hallucinated_ids():
    from picorte.ai.game_dossiers.loader import load_dossier
    from picorte.ai.llm_router import LLMRouter
    from picorte.ai.llm_scout import build_numbered_transcript, scout_full_vod

    sents = _make_sentences([
        (10.0, 18.0, "Entrando nessa cozinha aqui no apartamento."),
        (18.0, 26.0, "Deixa eu ver se a Rockstar corrigiu a animação da geladeira do trailer."),
        (26.0, 34.0, "Olha a mão dele pegando a garrafa, arrumaram mesmo!"),
        (34.0, 42.0, "Beleza, vamos continuar a missão agora."),
    ])

    numbered, sid_map = build_numbered_transcript(sents)
    assert "[S0002]" in numbered
    assert sid_map["S0002"] == 1

    captured_prompts = []

    def fake_provider(provider, model, system_prompt, user_prompt):
        captured_prompts.append((provider, system_prompt, user_prompt))
        return json.dumps([
            {
                "start_sid": "S0001",
                "end_sid": "S0003",
                "archetype": "callback_oculto",
                "why": "Testa se a Rockstar corrigiu o spawn do item na geladeira do trailer de GTA 6",
                "duration_bucket": "short",
            },
            {
                "start_sid": "S9999",
                "end_sid": "S9998",
                "archetype": "rage_tilt",
                "why": "ID alucinado que deve ser descartado",
                "duration_bucket": "short",
            },
        ])

    router = LLMRouter(provider_runner=fake_provider)
    findings = scout_full_vod(
        sents,
        router=router,
        ai_mode="claude",
        source_meta={"title": "Alanzoka jogando GTA 6", "channel": "Alanzoka", "duration": 60.0},
        dossier=load_dossier("gta6"),
    )

    assert len(findings) == 1
    hit = findings[0]
    assert hit["start"] == pytest.approx(10.0)
    assert hit["end"] == pytest.approx(35.5)  # 34.0 + 1.5s respiro
    assert hit["archetype"] == "callback_oculto"
    assert hit["track_origin"] == "full_vod_scout"
    assert "GTA 6" in captured_prompts[0][2] or "gta6" in captured_prompts[0][2].lower()


def test_scout_full_vod_uses_mapreduce_for_long_vods():
    from picorte.ai.llm_router import LLMRouter
    from picorte.ai.llm_scout import scout_full_vod

    # Simula VOD de 3 horas (10800s) com 180 sentenças espaçadas
    entries = [(i * 60.0, i * 60.0 + 12.0, f"Fala do minuto {i} jogando normalmente.") for i in range(180)]
    entries[90] = (5400.0, 5412.0, "Deixa eu testar a geladeira do trailer de GTA 6 agora!")
    entries[91] = (5412.0, 5424.0, "Olha a mão dele, corrigiram a animação!")
    sents = _make_sentences(entries)

    calls = []

    def fake_provider(provider, model, system_prompt, user_prompt):
        calls.append(user_prompt)
        if "MAPA DE BLOCO" in system_prompt or "Resuma" in system_prompt:
            return json.dumps([
                {"start_sid": "S0091", "end_sid": "S0092", "summary": "Testa animação da geladeira do trailer GTA 6"}
            ])
        return json.dumps([
            {
                "start_sid": "S0091",
                "end_sid": "S0092",
                "archetype": "callback_oculto",
                "why": "Callback cultural da geladeira no meio de live de 3h",
                "duration_bucket": "short",
            }
        ])

    router = LLMRouter(provider_runner=fake_provider)
    findings = scout_full_vod(
        sents,
        router=router,
        ai_mode="gemini",
        source_meta={"title": "Live 3h GTA 6", "duration": 10800.0},
    )
    assert len(calls) >= 2  # Map + Reduce
    assert len(findings) == 1
    assert findings[0]["start"] == pytest.approx(5400.0)
    assert findings[0]["end"] == pytest.approx(5425.5)


def test_flexible_duration_ladder_supports_micro_short_extended_and_long():
    import score_clips

    ladder_micro = score_clips.duration_ladder(8, 120)
    assert 8 in ladder_micro
    assert 12 in ladder_micro
    assert 15 in ladder_micro
    assert 60 in ladder_micro
    assert 90 in ladder_micro
    assert 120 in ladder_micro

    # Retrocompatibilidade quando min_len=15
    ladder_default = score_clips.duration_ladder(15, 300)
    assert min(ladder_default) == 15
    assert 300 in ladder_default
