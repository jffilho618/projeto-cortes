"""Testes TDD do Pacote de Polimento 3.5.6 — Velocidade/Logs/MMR, Badge de Papel Vermelho Estático,
Modo Menu/Tela Cheia em 9:16, Thumbnails 9:16 vs 16:9 sem tampar rosto, e UI limpa."""
from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np
import pytest


def test_mmr_diversify_prioritizes_diversity_without_discarding_overflow_clips():
    from picorte.ai.llm_router import mmr_diversify

    cands = [
        {"start": 100.0, "end": 130.0, "overall": 9.8, "archetype": "descoberta_detalhe", "tier": "ouro", "hook": "d1"},
        {"start": 200.0, "end": 230.0, "overall": 9.7, "archetype": "descoberta_detalhe", "tier": "ouro", "hook": "d2"},
        {"start": 300.0, "end": 330.0, "overall": 9.6, "archetype": "descoberta_detalhe", "tier": "ouro", "hook": "d3"},
        {"start": 400.0, "end": 430.0, "overall": 9.5, "archetype": "descoberta_detalhe", "tier": "ouro", "hook": "d4"},
        {"start": 500.0, "end": 530.0, "overall": 9.4, "archetype": "descoberta_detalhe", "tier": "ouro", "hook": "d5"},
        {"start": 600.0, "end": 630.0, "overall": 8.9, "archetype": "callback_oculto", "tier": "forte", "hook": "cb1"},
        {"start": 700.0, "end": 730.0, "overall": 8.8, "archetype": "serio_realtalk", "tier": "forte", "hook": "sr1"},
    ]

    # Com keep_overflow=True e sem limit: diversidade vem primeiro (d1,d2,d3,cb1,sr1), mas d4 e d5 NÃO são jogados fora!
    ordered = mmr_diversify(cands, max_per_archetype=3, keep_overflow=True)
    hooks = [c["hook"] for c in ordered]
    assert len(hooks) == 7
    assert hooks[:5].count("cb1") == 1
    assert hooks[:5].count("sr1") == 1
    assert set(hooks[5:]) == {"d4", "d5"}


def test_scout_mapreduce_runs_blocks_in_parallel_and_logs_progress(capsys):
    from picorte.ai.llm_router import LLMRouter
    from picorte.ai.llm_scout import scout_full_vod

    entries = [
        {"start": i * 60.0, "end": i * 60.0 + 12.0, "text": f"Frase do minuto {i} jogando GTA 6."}
        for i in range(120)
    ]

    def slow_provider(provider, model, system_prompt, user_prompt):
        if "MAPA DE BLOCO" in system_prompt:
            time.sleep(0.08)
            return json.dumps([{"start_sid": "S0001", "end_sid": "S0002", "summary": "Evento"}])
        return json.dumps([{
            "start_sid": "S0001", "end_sid": "S0002",
            "archetype": "callback_oculto", "why": "Teste paralelo", "duration_bucket": "short",
        }])

    router = LLMRouter(provider_runner=slow_provider)
    t0 = time.perf_counter()
    hits = scout_full_vod(
        entries, router=router, ai_mode="gemini",
        source_meta={"title": "GTA 6", "duration": 7200.0},
        max_workers=3,
    )
    elapsed = time.perf_counter() - t0
    out = capsys.readouterr().out
    assert len(hits) == 1
    assert "[scout" in out.lower()
    # Com ~17 blocos de 7min, 3 workers deve ser bem mais rápido que serial (17*0.08=1.36s)
    assert elapsed < 1.15


def test_editor_prompt_enforces_short_punchy_context_banner():
    from picorte.ai.llm_router import COMPANION_SYSTEM_PROMPT

    low = COMPANION_SYSTEM_PROMPT.lower()
    assert "4 a 6 palavras" in low or "até 6 palavras" in low
    assert "ruim:" in low or "evite" in low


def test_detect_menu_or_wide_ui_frame_and_build_wide_games_layout():
    from picorte.engine.reaction_layout import build_wide_menu_layout, is_wide_menu_frame

    # Frame sintético tipo menu de estatísticas (várias linhas de texto horizontais nos 2 lados da tela)
    menu_frame = np.full((720, 1280, 3), (90, 30, 80), dtype=np.uint8)
    for row_y in range(120, 620, 42):
        cv2.putText(menu_frame, f"PROGRESSO ESTATISTICAS {row_y}", (80, row_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2)
        cv2.putText(menu_frame, f"ATRIBUTOS DO PERSONAGEM {row_y}", (680, row_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2)

    # Frame sintético de gameplay aberto simples (céu + chão)
    open_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    open_frame[:360, :] = (200, 140, 60)
    open_frame[360:, :] = (50, 90, 50)

    assert is_wide_menu_frame(menu_frame) is True
    assert is_wide_menu_frame(open_frame) is False

    layout = build_wide_menu_layout(source_w=1280, source_h=720, out_w=1080, out_h=1920, facecam_box=(900, 30, 320, 220))
    assert "scale=1080:" in layout["filter_chain"]
    assert "boxblur" in layout["filter_chain"]
    assert layout["mode"] == "wide_menu"


def test_static_red_torn_paper_badge_and_games_caption_position(tmp_path: Path):
    import render_clips
    from picorte.engine.title_badge import create_torn_paper_badge

    out_png = tmp_path / "_title_badge.png"
    res = create_torn_paper_badge(out_png, width=930, height=253)
    assert res == out_png
    assert out_png.is_file()
    rgba = cv2.imread(str(out_png), cv2.IMREAD_UNCHANGED)
    assert rgba is not None
    assert rgba.shape == (253, 930, 4)
    # Centro é vermelho forte (em BGR, canal R > B e R > G) e opaco
    b, g, r, a = [int(v) for v in rgba[126, 465]]
    assert a == 255 and r > 180 and r > g * 2 and r > b * 2

    ass_path = tmp_path / "games_banner.ass"
    render_clips.build_ass(
        [{"word": "teste", "start": 1.0, "end": 1.4}],
        clip_start=0.0,
        clip_end=10.0,
        path=ass_path,
        tw=1080,
        th=1920,
        font_size=74,
        margin_v=450,
        context_banner_2s="DETALHE DE SAN ANDREAS",
        games_layout=True,
        facecam_h=640,
        banner_start=0.0,
        banner_end=3.5,
    )
    ass_text = ass_path.read_text(encoding="utf-8")
    assert "0:00:00.00,0:00:03.50,ContextBanner" in ass_text
    assert "\\an8\\pos(540,1536)" in ass_text


def test_thumbnail_factory_respects_9_16_vertical_aspect_and_avoids_face_occlusion(tmp_path: Path):
    from picorte.engine.thumbnail_factory import generate_thumbnail

    frame = np.full((720, 1280, 3), (45, 55, 70), dtype=np.uint8)
    out_916 = tmp_path / "vertical_thumb.png"
    res = generate_thumbnail(
        frame,
        out_916,
        title_text="A CENA DO TRAILER",
        aspect="9:16",
        vision_preset="low",
        cutout_runner=lambda img, _m: np.zeros(img.shape[:2], dtype=np.uint8),
    )
    assert res["width"] == 1080
    assert res["height"] == 1920
    img = cv2.imread(str(out_916))
    assert img is not None
    assert img.shape[:2] == (1920, 1080)

    # 16:9 continua 1280x720
    out_169 = tmp_path / "wide_thumb.png"
    res_wide = generate_thumbnail(
        frame,
        out_169,
        title_text="SISTEMA DE KARMA",
        aspect="16:9",
        vision_preset="low",
        cutout_runner=lambda img, _m: np.zeros(img.shape[:2], dtype=np.uint8),
    )
    assert res_wide["width"] == 1280
    assert res_wide["height"] == 720
