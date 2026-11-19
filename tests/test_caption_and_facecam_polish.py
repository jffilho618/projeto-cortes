from __future__ import annotations

import numpy as np
import pytest


def test_captions_split_on_silence_and_never_freeze_on_screen(tmp_path):
    import captions
    import render_clips

    words = [
        {"word": "Ah,", "start": 0.0, "end": 0.3},
        {"word": "não.", "start": 0.3, "end": 0.6},
        # 8.6s de silêncio!
        {"word": "Impressionado", "start": 9.2, "end": 9.6},
        {"word": "ali.", "start": 9.6, "end": 10.0},
        # 35s de silêncio!
        {"word": "Meu", "start": 45.0, "end": 45.4},
        {"word": "Deus.", "start": 45.4, "end": 45.8},
    ]

    srt_path = tmp_path / "test.srt"
    captions.write_srt(words, 0.0, 48.0, srt_path, group_size=8)
    srt_text = srt_path.read_text(encoding="utf-8")
    # Não pode unir palavras através dos 35s de silêncio nem esticar além do fim da fala
    assert "00:00:00,000 --> 00:00:00,600" in srt_text
    assert "00:00:09,200 --> 00:00:10,000" in srt_text
    assert "00:00:45,000 --> 00:00:45,800" in srt_text

    ass_path = tmp_path / "test.ass"
    render_clips.build_ass(words, 0.0, 48.0, ass_path, 1080, 1920, 82, 450)
    ass_lines = [l for l in ass_path.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue: 0,")]
    assert len(ass_lines) == 6
    # A segunda palavra ("não.") termina em ~0.60s (nunca fica pendurada até 9.20s!)
    end_ts = ass_lines[1].split(",")[2]
    h, m, s = end_ts.split(":")
    end_sec = int(h) * 3600 + int(m) * 60 + float(s)
    assert end_sec <= 1.0

    # Grupos consecutivos sem pausa nunca se sobrepõem (sem legendas duplicadas na tela)
    continuous = [
        {"word": "Não", "start": 0.0, "end": 0.2},
        {"word": "me", "start": 0.2, "end": 0.4},
        {"word": "vê", "start": 0.4, "end": 0.55},
        {"word": "não,", "start": 0.55, "end": 0.8},
        {"word": "amigo,", "start": 0.8, "end": 1.0},
        {"word": "por", "start": 1.0, "end": 1.2},
    ]
    cont_ass = tmp_path / "cont.ass"
    render_clips.build_ass(continuous, 0.0, 2.0, cont_ass, 1080, 1920, 82, 450)
    c_lines = [l for l in cont_ass.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue: 0,")]
    intervals = []
    for ln in c_lines:
        parts = ln.split(",")
        def _p(ts):
            hh, mm, ss = ts.split(":")
            return int(hh) * 3600 + int(mm) * 60 + float(ss)
        intervals.append((_p(parts[1]), _p(parts[2])))
    for (s1, e1), (s2, e2) in zip(intervals, intervals[1:]):
        assert e1 <= s2 + 1e-6


def test_filter_english_npc_cues_in_ptbr_video():
    import render_clips

    words = [
        {"word": "Furtividade", "start": 0.0, "end": 0.5},
        {"word": "não", "start": 0.5, "end": 0.8},
        {"word": "é", "start": 0.8, "end": 1.0},
        {"word": "o", "start": 1.0, "end": 1.1},
        {"word": "meu", "start": 1.1, "end": 1.3},
        {"word": "forte.", "start": 1.3, "end": 1.7},
        # NPC falando em inglês depois de pausa (incluindo "He's a brat.", "I" isolado e "Believe me...")
        {"word": "He's", "start": 3.0, "end": 3.2},
        {"word": "a", "start": 3.2, "end": 3.3},
        {"word": "brat.", "start": 3.3, "end": 3.6},
        {"word": "I", "start": 3.6, "end": 4.2},
        {"word": "don't", "start": 5.7, "end": 5.9},
        {"word": "think", "start": 5.9, "end": 6.1},
        {"word": "anybody's", "start": 6.1, "end": 6.4},
        {"word": "arguing", "start": 6.4, "end": 6.7},
        {"word": "about", "start": 6.7, "end": 6.9},
        {"word": "that.", "start": 6.9, "end": 7.2},
        {"word": "Believe", "start": 7.5, "end": 7.8},
        {"word": "me,", "start": 7.8, "end": 8.0},
        {"word": "this", "start": 8.0, "end": 8.2},
        {"word": "is", "start": 8.2, "end": 8.4},
        {"word": "last.", "start": 8.4, "end": 8.7},
        # Streamer volta em PT usando gíria gamer
        {"word": "Mano,", "start": 10.0, "end": 10.3},
        {"word": "que", "start": 10.3, "end": 10.5},
        {"word": "clutch", "start": 10.5, "end": 10.9},
        {"word": "absurdo!", "start": 10.9, "end": 11.4},
    ]

    filtered = render_clips.filter_streamer_language_words(words, dominant_language="pt")
    joined = " ".join(w["word"] for w in filtered)
    assert "Furtividade" in joined
    assert "clutch" in joined
    assert "brat" not in joined
    assert "Believe" not in joined
    assert "anybody's" not in joined
    assert "don't" not in joined
    assert " I " not in f" {joined} "


def test_expand_facecam_box_clamps_to_overlay_border_without_game_bleed():
    import render_clips

    # Simula 1920x1080: jogo verde brilhante fora da webcam; webcam cinza-escura em x=1540..1920, y=0..270
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame[:, :] = (40, 180, 50)  # folhagem verde do jogo
    frame[0:270, 1540:1920] = (32, 36, 44)  # fundo escuro da webcam
    frame[55:193, 1653:1751] = (180, 150, 130)  # rosto detectado

    x, y, w, h = render_clips.expand_facecam_box(
        (1653, 55, 98, 138), frame_w=1920, frame_h=1080, frame=frame
    )
    # Não deve invadir a folhagem verde à esquerda (x=1540) nem o jogo abaixo (y=270)
    assert x >= 1536
    assert y + h <= 278
    assert x + w <= 1920
