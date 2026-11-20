"""Testes TDD da Story 3.5.4 — Keyframes Multimodais Seletivos, Comentários YouTube, Prosódia CPU/YAMNet, Facecam Rica e Segmentação de Atividade."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest


def test_selective_keyframes_extracts_3_frames_and_degrades_cleanly_on_text_only(tmp_path: Path):
    from picorte.engine.multimodal_keyframes import (
        describe_candidate_keyframes,
        extract_selective_keyframes,
        select_candidates_for_keyframes,
    )

    cands = [
        {"start": 10.0, "end": 30.0, "overall": 6.5, "has_visual_deictic": True, "text": "Olha a mão dele!"},
        {"start": 50.0, "end": 70.0, "overall": 9.1, "archetype": "rage_tilt", "text": "QUE RAIVA!"},
        {"start": 90.0, "end": 110.0, "overall": 7.2, "archetype": "callback_oculto", "text": "Geladeira do trailer"},
    ]
    picked = select_candidates_for_keyframes(cands, max_candidates=5)
    assert len(picked) == 2
    assert picked[0]["has_visual_deictic"] is True

    # Usa sampler injetado retornando 6 frames sintéticos
    fake_frames = [np.full((180, 320, 3), i * 35, dtype=np.uint8) for i in range(6)]
    saved = extract_selective_keyframes(
        tmp_path / "dummy.mp4",
        picked[0],
        tmp_path / "kf",
        frame_sampler=lambda _p, _s, _e: fake_frames,
    )
    assert len(saved) == 3
    for img_path in saved:
        assert Path(img_path).is_file()
        loaded = cv2.imread(str(img_path))
        assert loaded is not None

    # Provedor multimodal responde com descrição visual
    desc = describe_candidate_keyframes(
        saved,
        picked[0],
        provider="gemini",
        vision_runner=lambda paths, prompt: f"Vistos {len(paths)} frames: personagem abrindo geladeira.",
    )
    assert "geladeira" in desc.lower()

    # Provedor texto-apenas (ollama sem visão) degrada limpo para None
    assert describe_candidate_keyframes(saved, picked[0], provider="ollama") is None


def test_comments_miner_parses_timestamps_and_enforces_p1_gate():
    from picorte.engine.comments_miner import (
        extract_comment_timestamps,
        mine_youtube_comments,
        parse_timestamp_to_seconds,
    )

    assert parse_timestamp_to_seconds("14:22") == 862.0
    assert parse_timestamp_to_seconds("1:02:05") == 3725.0
    assert parse_timestamp_to_seconds("invalid") is None

    comments = [
        {"text": "14:22 ele testando a geladeira do trailer kkkkk", "like_count": 420},
        {"text": "Melhor live do ano sem dúvida!", "like_count": 80},
        {"text": "1:05:10 o caos no discord começou aqui", "like_count": 150},
        {"text": "99:59 fora da duração do vídeo", "like_count": 10},
    ]
    extracted = extract_comment_timestamps(comments, duration_s=4200.0)
    assert len(extracted) == 2
    assert extracted[0]["timestamp_s"] == pytest.approx(862.0)
    assert "geladeira" in extracted[0]["description"].lower()
    assert extracted[1]["timestamp_s"] == pytest.approx(3910.0)

    # Portão P1: fonte desconhecida ou lista_negra DEVE ser bloqueada!
    with pytest.raises(PermissionError):
        mine_youtube_comments("https://www.youtube.com/watch?v=abc", permission_status="desconhecida")
    with pytest.raises(PermissionError):
        mine_youtube_comments("https://www.youtube.com/watch?v=abc", permission_status="lista_negra")

    # Fonte liberada converte comentários minerados em sementes candidatas
    payload = {"duration": 4200, "comments": comments}
    def fake_runner(cmd, **_kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")

    cands = mine_youtube_comments(
        "https://www.youtube.com/watch?v=abc",
        permission_status="liberada",
        runner=fake_runner,
    )
    assert len(cands) == 2
    assert cands[0]["seed_kind"] == "comment_timestamp"
    assert cands[0]["track_origin"] == "coop_payoff_nontextual"


def test_prosody_events_cpu_detects_laugh_rhythm_jumpscare_and_speech_rate_anomalies():
    from picorte.engine.prosody_events import (
        compute_speech_rate_anomalies,
        detect_jumpscare_spike,
        detect_laugh_rhythm_cpu,
        detect_nonverbal_audio_events,
    )

    sr = 16000
    t = np.linspace(0, 4.0, 4 * sr, endpoint=False)

    # 1) Riso pulsado a 4.5 Hz (modulação de envelope dentro de 3–6 Hz)
    carrier = np.sin(2 * np.pi * 450.0 * t)
    laugh_env = 0.5 * (1.0 + np.sin(2 * np.pi * 4.5 * t))
    laugh_wave = (0.4 * laugh_env * carrier).astype(np.float32)
    flat_wave = (0.2 * carrier).astype(np.float32)

    laugh_score = detect_laugh_rhythm_cpu(laugh_wave, sample_rate=sr)
    flat_score = detect_laugh_rhythm_cpu(flat_wave, sample_rate=sr)
    assert laugh_score > 0.45
    assert laugh_score > flat_score + 0.25

    # 2) Assinatura de Susto: 2.5s de silêncio quase absoluto seguido de spike > 20 dB em 150ms
    scare_wave = np.full(int(4.0 * sr), 0.005, dtype=np.float32) * np.sin(2 * np.pi * 300.0 * t)
    spike_start = int(2.5 * sr)
    spike_end = int(2.75 * sr)
    scare_wave[spike_start:spike_end] = 0.85 * np.sin(2 * np.pi * 700.0 * t[spike_start:spike_end])

    scare_info = detect_jumpscare_spike(scare_wave, sample_rate=sr, silence_sec=2.0, spike_db=18.0)
    assert scare_info["detected"] is True
    assert scare_info["jump_db"] >= 18.0
    assert 2.3 <= scare_info["spike_time_s"] <= 2.9

    # 3) Fallback limpo sem YAMNet instalado
    events = detect_nonverbal_audio_events(scare_wave, sample_rate=sr)
    assert events["jumpscare"]["detected"] is True
    assert events["yamnet_available"] is False

    # 4) Anomalias de taxa de fala (2x rápido no pânico, 2x lento na ênfase séria)
    sentences = [
        {"start": 0.0, "end": 4.0, "text": "fala normal com oito palavras exatas aqui agora"},      # 2.0 wps
        {"start": 4.0, "end": 8.0, "text": "outra frase bem normal oito palavras exatas aqui"},     # 2.0 wps
        {"start": 8.0, "end": 12.0, "text": "mais uma frase normal oito palavras exatas aqui"},     # 2.0 wps
        {"start": 12.0, "end": 14.0, "text": "corre corre corre ele tá vindo fecha a porta agora rápido"},  # 5.0 wps (panic!)
        {"start": 14.0, "end": 22.0, "text": "papo reto escuta bem isso agora"},                    # 0.75 wps (slow!)
    ]
    anomalies = compute_speech_rate_anomalies(sentences)
    assert anomalies[3]["kind"] == "fast_panic"
    assert anomalies[4]["kind"] == "slow_emphasis"


def test_visual_games_exposes_gaze_to_camera_facepalm_and_inspection_pause():
    from picorte.engine.visual_games import analyze_facecam_reactions

    # 10 frames a 2 fps (5 segundos)
    frames = []
    for i in range(10):
        img = np.zeros((180, 320, 3), dtype=np.uint8)
        if i < 4:
            # Movimento global alto nos 4 primeiros frames
            img[:, (i * 40) % 240 : (i * 40) % 240 + 80] = 200
        else:
            # Parado globalmente, apenas pequeno detalhe mudando no centro (inspeção de objeto!)
            img[70:110, 140:180] = 50 + (i * 30) % 200
        frames.append(img)

    # Landmarks presentes nos 6 primeiros frames e desaparecem (facepalm/saída) nos 4 últimos
    def fake_landmarks(frame):
        # Usa intensidade do canto para diferenciar índice de frame sem estado mutável complexo
        return [(10.0, 20.0), (15.0, 18.0), (20.0, 18.0), (25.0, 20.0), (20.0, 22.0), (15.0, 22.0)]

    call_idx = {"i": 0}
    def fake_lm_disappear(_frame):
        idx = call_idx["i"]
        call_idx["i"] += 1
        if idx in (0, 1, 2, 3, 4, 5):
            return [(10.0, 20.0), (15.0, 18.0), (20.0, 18.0), (25.0, 20.0), (20.0, 22.0), (15.0, 22.0)]
        return None  # rosto desapareceu (facepalm ou saiu da cadeira)

    # Yaw frontal (|yaw| <= 12°) por 4 frames consecutivos a 2 fps = 2.0s de gaze-to-camera
    yaw_vals = [28.0, 25.0, 3.0, 2.0, 4.0, 1.5, None, None, None, None]
    yaw_idx = {"i": 0}
    def fake_yaw(_frame):
        v = yaw_vals[yaw_idx["i"]]
        yaw_idx["i"] += 1
        return v

    res = analyze_facecam_reactions(
        frames,
        0.0,
        5.0,
        vision_preset="low",
        landmark_runner=fake_lm_disappear,
        yaw_runner=fake_yaw,
    )
    assert res["gaze_to_camera_sec"] >= 1.5
    assert res["face_disappeared_event"] is True
    assert res["inspection_pause_score"] > 0.3


def test_activity_segmenter_classifies_just_chatting_gameplay_and_menu():
    from picorte.engine.activity_segmenter import segment_vod_activity

    sentences = [
        {"start": 5.0, "end": 55.0, "text": "Papo reto galera, antes de abrir o jogo quero conversar com vocês sobre o chat e a semana inteira."},
        {"start": 65.0, "end": 115.0, "text": "Bora pro gameplay! Atira nele, pega o loot, desvia da granada, vai pro objetivo!"},
        {"start": 125.0, "end": 175.0, "text": "Deixa eu pausar aqui no menu de configurações rapidinho."},
    ]
    blocks = segment_vod_activity(
        sentences,
        visual_motion={0: 0.08, 1: 0.72, 2: 0.04},
        facecam_ratio={0: 0.65, 1: 0.12, 2: 0.15},
        block_sec=60.0,
    )
    assert len(blocks) == 3
    assert blocks[0]["activity"] == "just_chatting"
    assert blocks[0]["archetype_weights"]["serio_realtalk"] > 1.0
    assert blocks[1]["activity"] == "gameplay"
    assert blocks[1]["archetype_weights"]["clutch_fail"] >= 1.0
    assert blocks[2]["activity"] == "menu_pausa"
