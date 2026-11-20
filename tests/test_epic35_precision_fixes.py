"""Testes TDD da Story 3.5.1 — Correções de Precisão, Heatmap/Capítulos, NMS Pré-Visão, HUD Limpo e Dêiticos Visuais."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest


def test_detect_game_slug_and_load_gta6_dossier():
    from picorte.ai.game_dossiers.loader import detect_game_slug, load_dossier

    slug = detect_game_slug(
        "ALANZOKA JOGANDO GTA 6 PELA PRIMEIRA VEZ - TESTANDO DETALHES!",
        chapters=[{"title": "Vice City - Cozinha e Geladeira", "start_time": 120.0, "end_time": 300.0}],
    )
    assert slug == "gta6"

    dossier = load_dossier(slug)
    assert isinstance(dossier, dict)
    assert dossier["slug"] == "gta6"
    assert any("geladeira" in item.lower() for item in dossier["cultural_callbacks"])
    assert detect_game_slug("Jogo Totalmente Desconhecido XYZ 999") is None
    assert load_dossier(None) is None


def test_probe_source_persists_heatmap_chapters_channel_and_detected_game():
    import ingest

    fake_ytdlp_payload = {
        "title": "Testando segredos em GTA VI no lançamento",
        "channel": "Alanzoka",
        "duration": 3600,
        "formats": [
            {"vcodec": "avc1", "acodec": "none", "width": 1920, "height": 1080, "tbr": 5000},
            {"vcodec": "none", "acodec": "mp4a", "tbr": 128},
        ],
        "chapters": [
            {"title": "Introdução", "start_time": 0, "end_time": 180},
            {"title": "Testando a geladeira", "start_time": 800, "end_time": 950},
        ],
        "heatmap": [
            {"start_time": 0.0, "end_time": 36.0, "value": 0.2},
            {"start_time": 820.0, "end_time": 856.0, "value": 0.96},
            {"start_time": 856.0, "end_time": 892.0, "value": 0.4},
        ],
    }

    def fake_runner(cmd, **_kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(fake_ytdlp_payload), stderr="")

    meta = ingest.probe_source("https://www.youtube.com/watch?v=abc123", runner=fake_runner)
    assert meta["channel"] == "Alanzoka"
    assert meta["detected_game"] == "gta6"
    assert len(meta["chapters"]) == 2
    assert meta["chapters"][1]["title"] == "Testando a geladeira"
    assert len(meta["heatmap"]) == 3
    assert meta["heatmap"][1]["value"] == pytest.approx(0.96)


def test_probe_source_degrades_cleanly_without_heatmap_or_chapters():
    import ingest

    fake_ytdlp_payload = {
        "title": "Gameplay aleatória",
        "duration": 600,
        "formats": [{"vcodec": "avc1", "acodec": "mp4a", "width": 1280, "height": 720, "tbr": 2500}],
    }

    def fake_runner(cmd, **_kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(fake_ytdlp_payload), stderr="")

    meta = ingest.probe_source("https://www.youtube.com/watch?v=xyz789", runner=fake_runner)
    assert meta["heatmap"] == []
    assert meta["chapters"] == []
    assert meta["detected_game"] is None


def test_extract_heatmap_peaks_finds_spaced_local_maxima():
    import ingest

    heatmap = [
        {"start_time": 0.0, "end_time": 20.0, "value": 0.25},
        {"start_time": 20.0, "end_time": 40.0, "value": 0.72},
        {"start_time": 40.0, "end_time": 60.0, "value": 0.88},  # pico 1 (centro 50s)
        {"start_time": 60.0, "end_time": 80.0, "value": 0.70},  # muito perto do pico 1
        {"start_time": 200.0, "end_time": 220.0, "value": 0.40},
        {"start_time": 300.0, "end_time": 325.0, "value": 0.95},  # pico 2 (centro 312.5s)
    ]
    peaks = ingest.extract_heatmap_peaks(heatmap, min_value=0.65, min_gap_sec=35.0)
    assert len(peaks) == 2
    assert peaks[0]["value"] == pytest.approx(0.95)
    assert peaks[1]["value"] == pytest.approx(0.88)


def test_temporal_nms_prevents_same_minute_vision_clones():
    import score_clips

    # Simula o bug real do projeto 19059a3dc07d: 15 janelas sobrepostas em 1609-1649s
    candidates = []
    for i in range(15):
        candidates.append({
            "start": 1609.0 + i * 1.5,
            "end": 1649.0 + i * 1.5,
            "overall": round(9.8 - i * 0.05, 2),
            "hook": f"clone_{i}",
        })
    # Mais 6 momentos distintos espalhados pelo VOD com nota ligeiramente menor
    for j, t in enumerate([120.0, 420.0, 780.0, 1120.0, 2100.0, 2650.0]):
        candidates.append({
            "start": t,
            "end": t + 35.0,
            "overall": round(8.5 - j * 0.1, 2),
            "hook": f"distinct_{j}",
        })

    selected = score_clips.temporal_nms(candidates, iou_threshold=0.35, min_center_gap_sec=20.0, limit=12)
    hooks = [c["hook"] for c in selected]
    clones_kept = [h for h in hooks if h.startswith("clone_")]
    distinct_kept = [h for h in hooks if h.startswith("distinct_")]

    assert len(clones_kept) <= 2
    assert len(distinct_kept) == 6
    # Garantir que nenhum par selecionado tenha IoU > 0.35 ou sub-janela contida (>= 70%)
    for idx_a, a in enumerate(selected):
        for b in selected[idx_a + 1:]:
            inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
            union = max(1e-6, max(a["end"], b["end"]) - min(a["start"], b["start"]))
            min_dur = max(1e-6, min(a["end"] - a["start"], b["end"] - b["start"]))
            assert (inter / union) <= 0.35
            assert (inter / min_dur) < 0.70


def test_temporal_nms_suppresses_nested_subwindows():
    import score_clips

    cands = [
        {"start": 1958.0, "end": 2155.4, "overall": 9.5, "hook": "long_parent"},
        {"start": 2102.6, "end": 2155.4, "overall": 9.2, "hook": "nested_child"},
        {"start": 400.0, "end": 445.0, "overall": 8.4, "hook": "other_moment"},
    ]
    kept = score_clips.temporal_nms(cands, iou_threshold=0.35, min_center_gap_sec=20.0, limit=12)
    hooks = [c["hook"] for c in kept]
    assert "long_parent" in hooks
    assert "other_moment" in hooks
    assert "nested_child" not in hooks


def test_hud_detector_ignores_coco_person_and_facecam_box_without_saturation():
    from picorte.engine.hud_detector import detect_hud_events

    frames = [np.zeros((180, 320, 3), dtype=np.uint8) for _ in range(10)]

    # Simula YOLO detectando o streamer ("person") + um objeto dentro da caixa da facecam
    def fake_yolo(_frame):
        return [
            {"label": "person", "class_id": 0, "conf": 0.92, "bbox": [10, 10, 90, 90]},
            {"label": "chair", "class_id": 56, "conf": 0.85, "bbox": [12, 20, 88, 95]},
            {"label": "person", "class_id": 0, "conf": 0.88, "bbox": [140, 50, 200, 150]},
        ]

    res = detect_hud_events(
        frames,
        0.0,
        10.0,
        vision_preset="high",
        ocr_runner=lambda _f, _i: [],
        yolo_runner=fake_yolo,
        exclude_box=(0, 0, 100, 100),
    )
    assert res["score"] < 3.0
    assert not any(ev.get("keyword") == "PERSON" for ev in res["events"])

    # Banner real de OCR deve continuar pontuando forte
    res_ocr = detect_hud_events(
        frames,
        0.0,
        10.0,
        vision_preset="high",
        ocr_runner=lambda _f, idx: ["TRIPLE KILL +300"] if idx in (2, 5) else [],
        yolo_runner=fake_yolo,
        exclude_box=(0, 0, 100, 100),
    )
    assert res_ocr["score"] >= 6.0
    assert any(ev.get("keyword") == "TRIPLE KILL" for ev in res_ocr["events"])


def test_visual_deictic_openers_are_flagged_and_not_penalized_as_anaphoric():
    import score_clips

    sent_deictic = {
        "start": 100.0,
        "end": 106.0,
        "text": "Olha isso aqui, olha a mão dele abrindo a geladeira, arrumaram!",
        "words": [
            {"word": w, "start": 100.0 + i * 0.5, "end": 100.4 + i * 0.5}
            for i, w in enumerate("Olha isso aqui, olha a mão dele abrindo a geladeira, arrumaram!".split())
        ],
    }
    sent_plain_anaphoric = {
        "start": 110.0,
        "end": 115.0,
        "text": "Ele foi embora ontem depois da reunião.",
        "words": [
            {"word": w, "start": 110.0 + i * 0.5, "end": 110.4 + i * 0.5}
            for i, w in enumerate("Ele foi embora ontem depois da reunião.".split())
        ],
    }
    sent_deictic_espera = {
        "start": 120.0,
        "end": 125.0,
        "text": "Isso aqui olha a física da garrafa no jogo!",
        "words": [
            {"word": w, "start": 120.0 + i * 0.5, "end": 120.4 + i * 0.5}
            for i, w in enumerate("Isso aqui olha a física da garrafa no jogo!".split())
        ],
    }

    feat_deictic = score_clips.sentence_features(sent_deictic)
    feat_plain = score_clips.sentence_features(sent_plain_anaphoric)
    feat_espera = score_clips.sentence_features(sent_deictic_espera)

    assert feat_deictic["visual_deictic"] is True
    assert feat_deictic["anaphoric"] is False
    assert feat_espera["visual_deictic"] is True
    assert feat_espera["anaphoric"] is False
    assert feat_plain["visual_deictic"] is False
    assert feat_plain["anaphoric"] is True
