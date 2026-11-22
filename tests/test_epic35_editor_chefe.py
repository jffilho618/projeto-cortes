"""Testes TDD da Story 3.5.3 — Editor-Chefe v2, golden_examples.json, game_dossiers, pre/post_context, MMR e Benchmark Geladeira."""
from __future__ import annotations

import json
from pathlib import Path

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


def test_load_golden_examples_contains_alanzoka_geladeira_and_valid_taxonomy():
    from picorte.ai.llm_router import load_golden_examples
    from picorte.engine.multitrack import CANONICAL_ARCHETYPES, CANONICAL_TIERS

    examples = load_golden_examples()
    assert len(examples) >= 5
    ids = {ex["id"]: ex for ex in examples}
    assert "alanzoka-gta6-geladeira" in ids
    gel = ids["alanzoka-gta6-geladeira"]
    assert gel["archetype"] == "callback_oculto"
    assert gel["tier"] == "ouro"
    assert gel["game"] == "gta6"

    for ex in examples:
        assert ex["archetype"] in CANONICAL_ARCHETYPES
        assert ex["tier"] in CANONICAL_TIERS
        assert ex.get("ideal_context_banner")


def test_attach_neighbor_context_adds_pre_20s_and_post_15s():
    from picorte.ai.llm_router import attach_neighbor_context

    sents = _make_sentences([
        (60.0, 68.0, "Muito antes, fora da janela de 20s."),
        (85.0, 95.0, "Entrei na cozinha do apartamento do Jason."),
        (100.0, 118.0, "Deixa eu abrir essa geladeira pra ver se a Rockstar corrigiu."),
        (120.0, 130.0, "Arrumaram! Ele pegou a garrafa de verdade, não spawnou!"),
        (150.0, 160.0, "Muito depois, fora da janela de 15s."),
    ])
    cands = [{"start": 100.0, "end": 118.0, "text": "Deixa eu abrir essa geladeira pra ver se a Rockstar corrigiu."}]

    enriched = attach_neighbor_context(cands, sents, pre_sec=20.0, post_sec=15.0)
    assert "cozinha do apartamento" in enriched[0]["pre_context"]
    assert "Muito antes" not in enriched[0]["pre_context"]
    assert "não spawnou" in enriched[0]["post_context"]
    assert "Muito depois" not in enriched[0]["post_context"]


def test_editor_chefe_v2_injects_context_and_applies_archetype_tier_tone_and_edge_adjust():
    from picorte.ai.game_dossiers.loader import load_dossier
    from picorte.ai.llm_router import LLMRouter, load_golden_examples

    sents = _make_sentences([
        (85.0, 98.0, "Tô entrando na cozinha aqui, lembra do trailer?"),
        (100.0, 120.0, "Deixa eu ver se a Rockstar corrigiu a animação da geladeira."),
        (120.0, 128.0, "Olha a mão dele, arrumaram mesmo!"),
    ])
    cands = [{
        "start": 100.0,
        "end": 120.0,
        "duration": 20.0,
        "overall": 6.4,
        "text": "Deixa eu ver se a Rockstar corrigiu a animação da geladeira.",
        "track_origin": "deictic_detective_callback",
        "has_visual_deictic": True,
    }]

    seen_calls = []

    def fake_provider(provider, model, system_prompt, user_prompt):
        seen_calls.append((system_prompt, user_prompt))
        return json.dumps([{
            "index": 0,
            "adjustment": 2.9,
            "archetype": "callback_oculto",
            "tier": "ouro",
            "tone": "curioso",
            "rewatchability": 9.4,
            "shareability": 9.2,
            "hook_quote": "Será que corrigiram a geladeira do trailer?",
            "proposed_title": "ELE FOI TESTAR A GELADEIRA DO TRAILER DE GTA 6",
            "context_banner_2s": "No trailer o item spawnava na mão — ele foi testar",
            "thumbnail_words": "ARRUMARAM A GELADEIRA?",
            "pinned_comment_debate": "Você também reparou nesse detalhe no trailer de GTA 6?",
            "expand_start_sec": 6.0,
            "expand_end_sec": 8.0,
            "reason": "Callback cultural silencioso de altíssimo valor viral",
        }])

    router = LLMRouter(provider_runner=fake_provider)
    res = router.rerank_candidates(
        cands,
        ai_mode="claude",
        source_meta={"title": "Alanzoka jogando GTA 6", "channel": "Alanzoka", "duration": 600.0},
        sentences=sents,
        dossier=load_dossier("gta6"),
        golden_examples=load_golden_examples(),
    )

    assert len(seen_calls) == 1
    sys_prompt, usr_prompt = seen_calls[0]
    assert "callback_oculto" in sys_prompt
    assert "Conselho" in sys_prompt or "4 Caçadores" in sys_prompt
    assert "alanzoka-gta6-geladeira" in usr_prompt or "geladeira" in usr_prompt.lower()
    assert "pre_context" in usr_prompt
    assert "post_context" in usr_prompt

    top = res["candidates"][0]
    assert top["archetype"] == "callback_oculto"
    assert top["tier"] == "ouro"
    assert top["tone"] == "curioso"
    assert top["rewatchability"] == pytest.approx(9.4)
    assert top["shareability"] == pytest.approx(9.2)
    assert top["overall"] == pytest.approx(9.3)
    assert top["start"] == pytest.approx(94.0)  # 100 - 6
    assert top["end"] == pytest.approx(128.0)   # 120 + 8
    assert "trailer" in top["context_banner_2s"].lower()


def test_mmr_diversify_caps_dominant_archetype_and_spreads_timeline():
    from picorte.ai.llm_router import mmr_diversify

    cands = [
        {"start": 100.0, "end": 130.0, "overall": 9.6, "archetype": "rage_tilt", "hook": "r1"},
        {"start": 200.0, "end": 230.0, "overall": 9.5, "archetype": "rage_tilt", "hook": "r2"},
        {"start": 300.0, "end": 330.0, "overall": 9.4, "archetype": "rage_tilt", "hook": "r3"},
        {"start": 400.0, "end": 430.0, "overall": 9.3, "archetype": "rage_tilt", "hook": "r4"},
        {"start": 500.0, "end": 530.0, "overall": 8.9, "archetype": "callback_oculto", "hook": "cb1"},
        {"start": 600.0, "end": 630.0, "overall": 8.7, "archetype": "serio_realtalk", "hook": "sr1"},
        {"start": 700.0, "end": 730.0, "overall": 8.6, "archetype": "caos_coop", "hook": "cc1"},
        {"start": 800.0, "end": 830.0, "overall": 8.4, "archetype": "deadpan_karma", "hook": "dk1"},
    ]

    diverse = mmr_diversify(cands, max_per_archetype=2, min_time_gap_sec=25.0, limit=6)
    assert len(diverse) == 6
    rage_count = sum(1 for c in diverse if c["archetype"] == "rage_tilt")
    assert rage_count == 2
    archetypes_found = {c["archetype"] for c in diverse}
    assert {"rage_tilt", "callback_oculto", "serio_realtalk", "caos_coop", "deadpan_karma"}.issubset(archetypes_found)


def test_benchmark_geladeira_alanzoka_end_to_end_select(tmp_path: Path, monkeypatch):
    import score_clips
    from picorte.ai import llm_router as lr_mod

    # Monta transcrição de 35 frases barulhentas + 1 momento silencioso da geladeira
    entries = []
    for i in range(32):
        t = 30.0 + i * 40.0
        entries.append((t, t + 28.0, f"CARAMBA EXPLODIU TUDO TIRO INSANO VAMO GALERA {i}!"))
    # Momento silencioso da geladeira aos 1400s (enterrado em energia baixa)
    entries.append((1385.0, 1398.0, "Entrando aqui nessa cozinha, lembra do trailer do jogo?"))
    entries.append((1400.0, 1424.0, "Deixa eu ver se a Rockstar corrigiu a animação da geladeira. Olha a mão dele, arrumaram!"))
    entries.append((1425.0, 1435.0, "Que detalhe absurdo, escola Rockstar demais."))

    sents = _make_sentences(entries)
    words = [w for s in sents for w in s["words"]]
    (tmp_path / "transcript.json").write_text(
        json.dumps({"video": str(tmp_path / "fake.mp4"), "duration": 1500.0, "words": words}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "project.json").write_text(
        json.dumps({
            "source_meta": {
                "title": "ALANZOKA JOGANDO GTA 6 PELA PRIMEIRA VEZ",
                "channel": "Alanzoka",
                "duration": 1500.0,
                "detected_game": "gta6",
                "chapters": [{"title": "Explorando o apartamento", "start_time": 1350.0, "end_time": 1460.0}],
                "heatmap": [{"start_time": 1400.0, "end_time": 1425.0, "value": 0.92}],
            }
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    # Candidatos iniciais onde a geladeira está em último com nota 6.2 (abaixo dos 32 barulhentos)
    raw_cands = []
    for i in range(32):
        t = 30.0 + i * 40.0
        raw_cands.append({
            "start": t,
            "end": t + 28.0,
            "duration": 28.0,
            "hook": f"barulho_{i}",
            "text": f"CARAMBA EXPLODIU TUDO TIRO INSANO VAMO GALERA {i}!",
            "overall": round(8.8 - i * 0.02, 2),
            "raw_score": 8.4,
            "seed_kind": "sentence",
            "score_parts": {"energy": 0.95},
            "evidence": {},
            "reason": "Alta energia",
        })
    raw_cands.append({
        "start": 1400.0,
        "end": 1424.0,
        "duration": 24.0,
        "hook": "deixa eu ver se a rockstar",
        "text": "Deixa eu ver se a Rockstar corrigiu a animação da geladeira. Olha a mão dele, arrumaram!",
        "overall": 6.2,
        "raw_score": 6.2,
        "seed_kind": "sentence",
        "has_visual_deictic": True,
        "score_parts": {"energy": 0.14},
        "evidence": {},
        "reason": "Baixo volume",
    })
    score_clips.save_candidates(tmp_path, raw_cands, {"source_duration": 1500.0, "content_profile": "mixed"})

    def fake_provider(self, provider, model, system_prompt, user_prompt):
        if "Full-VOD Scout" in system_prompt:
            return json.dumps([{
                "start_sid": "S0033",
                "end_sid": "S0035",
                "archetype": "callback_oculto",
                "why": "Alanzoka testa se a animação da geladeira do trailer de GTA 6 foi corrigida",
                "duration_bucket": "short",
            }])
        # Editor-Chefe v2: extrai a lista JSON após o cabeçalho de contexto
        json_part = user_prompt.split("CANDIDATOS JSON:\n", 1)[-1]
        rows = json.loads(json_part)
        out = []
        for row in rows:
            idx = row["index"]
            if "geladeira" in str(row.get("text", "")).lower():
                out.append({
                    "index": idx,
                    "adjustment": 3.0,
                    "archetype": "callback_oculto",
                    "tier": "ouro",
                    "tone": "curioso",
                    "rewatchability": 9.6,
                    "shareability": 9.5,
                    "proposed_title": "ALANZOKA TESTA SE ARRUMARAM A GELADEIRA DO TRAILER DE GTA 6",
                    "context_banner_2s": "No trailer o item spawnava na mão — ele foi testar",
                    "thumbnail_words": "ARRUMARAM A GELADEIRA?",
                    "pinned_comment_debate": "Você lembrava desse detalhe do trailer?",
                    "reason": "Callback cultural ouro",
                })
            else:
                out.append({
                    "index": idx,
                    "adjustment": -0.3,
                    "archetype": "rage_tilt",
                    "tier": "forte",
                    "tone": "hype",
                    "reason": "Ação comum",
                })
        return json.dumps(out, ensure_ascii=False)

    monkeypatch.setattr(lr_mod.LLMRouter, "_run_provider", fake_provider)

    segments, used_mode = score_clips.select(tmp_path, min_score=7.5, max_clips=6, ai_mode="claude")
    assert used_mode == "claude"
    gel_clips = [s for s in segments if s.get("archetype") == "callback_oculto"]
    assert len(gel_clips) >= 1
    gel = gel_clips[0]
    assert gel["tier"] == "ouro", (gel.get("ouro_rebaixado"), gel.get("sinais_independentes"), gel.get("track_origin"))
    assert "trailer" in gel["context_banner_2s"].lower()
    assert gel["overall"] >= 9.0


def test_editor_chefe_v2_batches_large_payloads_under_windows_cli_limit():
    from picorte.ai.llm_router import LLMRouter

    # 45 candidatos grandes com pre/post context (total > 35.000 chars sem batching)
    big_cands = []
    for i in range(45):
        big_cands.append({
            "start": float(i * 50),
            "end": float(i * 50 + 30),
            "duration": 30.0,
            "overall": 7.5,
            "text": f"Candidato {i} " + ("texto de gameplay longo " * 18),
            "pre_context": "contexto anterior " * 12,
            "post_context": "contexto posterior " * 10,
        })

    prompt_sizes = []

    def fake_provider(provider, model, system_prompt, user_prompt):
        prompt_sizes.append(len(system_prompt) + len(user_prompt))
        json_part = user_prompt.split("CANDIDATOS JSON:\n", 1)[-1]
        rows = json.loads(json_part)
        return json.dumps([
            {
                "index": row["index"],
                "adjustment": 0.5,
                "archetype": "descoberta_detalhe",
                "tier": "forte",
                "reason": f"Avaliado {row['index']}",
            }
            for row in rows
        ])

    router = LLMRouter(provider_runner=fake_provider)
    res = router.rerank_candidates(big_cands, ai_mode="gemini")
    assert len(prompt_sizes) >= 2
    assert all(sz <= 24000 for sz in prompt_sizes)
    assert len(res["candidates"]) == 45
    assert all(c.get("archetype") == "descoberta_detalhe" for c in res["candidates"])
