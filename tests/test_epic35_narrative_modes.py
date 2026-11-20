"""Testes TDD da Story 3.5.5 — Arcos de 2 Atos, Compilação por Arquétipo, Estilo Adaptado, Query-Driven, Deep Hunt e Auto-Atualizador de Dossiês + MCP."""
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


def test_two_act_arc_detects_distant_promise_and_builds_cross_platform_ffmpeg_filter():
    from picorte.engine.two_act_arc import build_two_act_ffmpeg_filter, detect_two_act_arcs

    sents = _make_sentences([
        (250.0, 260.0, "Relaxa galera, eu nunca vou morrer nessa fase, tá fácil demais, confia."),
        (600.0, 615.0, "Seguindo o caminho normalmente pelo corredor."),
        (1180.0, 1192.0, "Morri de novo, fui de base, não acredito nisso!"),
    ])

    arcs = detect_two_act_arcs(sents, min_gap_sec=60.0, max_gap_sec=1800.0)
    assert len(arcs) == 1
    arc = arcs[0]
    assert arc["act1_start"] == pytest.approx(250.0)
    assert arc["act2_start"] == pytest.approx(1180.0)
    assert "minutos depois" in arc["bridge_text"].lower()

    flt = build_two_act_ffmpeg_filter(
        arc["act1_start"], arc["act1_end"], arc["act2_start"], arc["act2_end"]
    )
    assert "trim=start=250.0:end=260.0" in flt
    assert "trim=start=1180.0:end=1192.0" in flt
    assert "setpts=PTS-STARTPTS" in flt
    assert "concat=n=2:v=1:a=1" in flt


def test_archetype_compiler_groups_four_plus_clips_into_thematic_compilation():
    from picorte.engine.archetype_compiler import compile_by_archetype

    cands = [
        {"start": 100.0, "end": 135.0, "duration": 35.0, "overall": 8.9, "archetype": "descoberta_detalhe", "hook": "d1"},
        {"start": 300.0, "end": 335.0, "duration": 35.0, "overall": 8.7, "archetype": "descoberta_detalhe", "hook": "d2"},
        {"start": 500.0, "end": 530.0, "duration": 30.0, "overall": 8.6, "archetype": "descoberta_detalhe", "hook": "d3"},
        {"start": 700.0, "end": 740.0, "duration": 40.0, "overall": 8.5, "archetype": "descoberta_detalhe", "hook": "d4"},
        {"start": 900.0, "end": 930.0, "duration": 30.0, "overall": 9.1, "archetype": "rage_tilt", "hook": "r1"},
        {"start": 960.0, "end": 990.0, "duration": 30.0, "overall": 8.8, "archetype": "rage_tilt", "hook": "r2"},
    ]

    compilations = compile_by_archetype(cands, min_clips=4, min_total_sec=90.0, max_total_sec=240.0)
    assert len(compilations) == 1
    comp = compilations[0]
    assert comp["archetype"] == "descoberta_detalhe"
    assert len(comp["clips"]) == 4
    assert 90.0 <= comp["total_duration"] <= 240.0


def test_retention_engine_adapts_cold_open_and_banner_style_by_archetype():
    from picorte.engine.retention_engine import (
        build_cold_open_plan,
        build_context_banner_ass,
        resolve_archetype_retention_policy,
    )

    p_susto = resolve_archetype_retention_policy("susto_tensao")
    assert p_susto["use_cold_open"] is False
    assert p_susto["banner_style"] == "tenso"

    p_serio = resolve_archetype_retention_policy("serio_realtalk")
    assert p_serio["use_cold_open"] is False
    assert p_serio["banner_style"] == "editorial"

    p_coop = resolve_archetype_retention_policy("caos_coop")
    assert p_coop["use_cold_open"] is True
    assert p_coop["banner_style"] == "hype"

    co_susto = build_cold_open_plan(10.0, 40.0, archetype="susto_tensao")
    assert co_susto["enabled"] is False
    assert co_susto["teaser_duration"] == 0.0

    co_coop = build_cold_open_plan(10.0, 40.0, archetype="caos_coop")
    assert co_coop["enabled"] is True
    assert 1.2 <= co_coop["teaser_duration"] <= 1.8

    ass_serio = build_context_banner_ass("Ele pausou a live pra falar sério", archetype="serio_realtalk")
    ass_hype = build_context_banner_ass("O plano durou 8 segundos!", archetype="caos_coop")
    assert "Archivo" in ass_serio
    assert ass_serio != ass_hype


def test_query_driven_clipping_and_hunt_mode_options():
    import projects
    from picorte.ai.llm_router import LLMRouter
    from picorte.ai.llm_scout import query_vod_clips

    sents = _make_sentences([
        (10.0, 20.0, "Começando a live andando de carro."),
        (120.0, 134.0, "Deixa eu ver se a Rockstar corrigiu a animação da geladeira do trailer."),
        (134.0, 144.0, "Olha a mão dele, arrumaram mesmo!"),
    ])

    captured = []

    def fake_provider(provider, model, system_prompt, user_prompt):
        captured.append(user_prompt)
        return json.dumps([{
            "start_sid": "S0002",
            "end_sid": "S0003",
            "archetype": "callback_oculto",
            "why": "Responde exatamente à pergunta sobre comparações com o trailer",
            "duration_bucket": "short",
        }])

    router = LLMRouter(provider_runner=fake_provider)
    hits = query_vod_clips(
        sents,
        query="comparações com o trailer ou testes de física",
        router=router,
        ai_mode="claude",
        source_meta={"title": "GTA 6 Live", "duration": 200.0},
    )
    assert len(hits) == 1
    assert "comparações com o trailer" in captured[0]
    assert hits[0]["start"] == pytest.approx(120.0)
    assert hits[0]["track_origin"] == "query_driven"

    # Validação de opções query e hunt_mode no projects.py
    opts = projects.validate_options({"query": "melhores rages", "hunt_mode": "deep"})
    assert opts["query"] == "melhores rages"
    assert opts["hunt_mode"] == "deep"
    with pytest.raises(ValueError):
        projects.validate_options({"hunt_mode": "turbo_invalido"})


def test_dossier_updater_and_mcp_tools(tmp_path: Path):
    from picorte.ai.dossier_updater import save_dossier
    from picorte.ai.game_dossiers.loader import load_dossier
    from picorte.mcp.server import PicorteMCPServer

    path = save_dossier(
        "elden_ring",
        display_name="Elden Ring",
        aliases=["elden ring", "terras intermedias", "shadow of the erdtree"],
        cultural_callbacks=["Let Me Solo Her", "Malenia Blade of Miquella"],
        hot_details_to_watch=["Bosses secretos", "Morte na primeira tentativa"],
        dossiers_dir=tmp_path,
    )
    assert path.is_file()
    loaded = load_dossier("elden_ring", dossiers_dir=tmp_path)
    assert loaded is not None
    assert loaded["display_name"] == "Elden Ring"
    assert "Let Me Solo Her" in loaded["cultural_callbacks"]

    server = PicorteMCPServer()
    tool_names = {t["name"] for t in server.list_tools()}
    assert "picorte_buscar_por_pergunta" in tool_names
    assert "picorte_atualizar_dossie" in tool_names

    res = server.call_tool(
        "picorte_atualizar_dossie",
        {
            "slug": "hollow_knight_silksong",
            "display_name": "Hollow Knight: Silksong",
            "aliases": ["silksong", "hollow knight"],
            "cultural_callbacks": ["Meme do palhaço esperando lançamento"],
            "dossiers_dir": str(tmp_path),
        },
    )
    assert res["slug"] == "hollow_knight_silksong"
    assert Path(res["path"]).is_file()
