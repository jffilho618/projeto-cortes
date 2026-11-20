"""Testes TDD Stories 4.3 & 4.4 — Cirurgia Seletiva de Música (Demucs), Selo Verde 15s (Áudio/Visão/ColdOpen/Thumb) e React Guard."""
from __future__ import annotations

import math
from pathlib import Path
import wave

import cv2
import numpy as np


def _write_wav(path: Path, samples: np.ndarray, sr: int = 16000) -> Path:
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
        return arr, sr


def test_music_surgeon_detects_music_interval_runs_selective_surgery_with_crossfade_and_caches(tmp_path: Path):
    from picorte.risk_shield.music_surgeon import detect_music_intervals, run_selective_music_surgery

    sr = 16000
    dur_s = 10.0
    t = np.linspace(0, dur_s, int(sr * dur_s), endpoint=False, dtype=np.float32)
    rng = np.random.default_rng(42)

    # 0-3s: fala/ruído impulsivo sem acorde contínuo; 3-7s: acorde musical tonal contínuo + voz; 7-10s: fala limpa
    signal = rng.normal(0, 0.02, size=t.shape).astype(np.float32)
    # Adiciona fala esparsa (pulsos curtos modulados) em 0-3s e 7-10s
    for p_start in (0.4, 1.4, 2.2, 7.5, 8.6):
        mask = (t >= p_start) & (t < p_start + 0.35)
        signal[mask] += 0.18 * np.sin(2 * math.pi * (180 + 90 * np.sin(12 * t[mask])) * t[mask])

    # Em 3.0s..7.0s: acorde harmônico musical contínuo (A4 + C#5 + E5 + baixo A2)
    m_mask = (t >= 3.0) & (t < 7.0)
    music_bed = (
        0.25 * np.sin(2 * math.pi * 110.0 * t[m_mask])
        + 0.25 * np.sin(2 * math.pi * 440.0 * t[m_mask])
        + 0.20 * np.sin(2 * math.pi * 554.37 * t[m_mask])
        + 0.20 * np.sin(2 * math.pi * 659.25 * t[m_mask])
    )
    signal[m_mask] += music_bed

    in_wav = _write_wav(tmp_path / "clip_in.wav", signal, sr=sr)
    intervals = detect_music_intervals(in_wav, min_duration_s=2.5)
    assert len(intervals) >= 1
    assert any(iv["start"] <= 4.0 and iv["end"] >= 6.0 for iv in intervals)

    calls = {"n": 0}

    def fake_demucs(slice_wav: Path, out_vocals_wav: Path) -> Path:
        calls["n"] += 1
        arr, s_sr = _read_wav(slice_wav)
        # Retorna stem vocal limpo com voz sintética clara
        tt = np.linspace(0, len(arr) / s_sr, len(arr), endpoint=False, dtype=np.float32)
        clean_vox = 0.25 * np.sin(2 * math.pi * 240.0 * tt)
        return _write_wav(out_vocals_wav, clean_vox, sr=s_sr)

    cache_dir = tmp_path / "stems_cache"
    out_wav = tmp_path / "clip_clean.wav"
    res1 = run_selective_music_surgery(
        in_wav,
        out_wav,
        intervals=intervals,
        separator_runner=fake_demucs,
        cache_dir=cache_dir,
        crossfade_ms=150,
    )
    assert res1["status"] == "auto_fixed"
    assert res1["surgery_applied"] is True
    assert out_wav.is_file()
    assert calls["n"] == len(intervals)

    # Verifica peak limiter (-1.5 dBTP -> amplitude <= 0.86)
    cleaned, _ = _read_wav(out_wav)
    assert float(np.max(np.abs(cleaned))) <= 0.87

    # 2ª execução no mesmo trecho reutiliza cache (calls["n"] não aumenta!)
    out_wav2 = tmp_path / "clip_clean_2.wav"
    res2 = run_selective_music_surgery(
        in_wav,
        out_wav2,
        intervals=intervals,
        separator_runner=fake_demucs,
        cache_dir=cache_dir,
    )
    assert res2["cache_hit"] is True
    assert calls["n"] == len(intervals)


def test_music_surgeon_degrades_explicitly_when_demucs_unavailable(tmp_path: Path, monkeypatch):
    from picorte.risk_shield import music_surgeon

    sr = 16000
    t = np.linspace(0, 4.0, sr * 4, endpoint=False, dtype=np.float32)
    in_wav = _write_wav(tmp_path / "m.wav", 0.3 * np.sin(2 * math.pi * 440.0 * t), sr=sr)
    monkeypatch.setattr(music_surgeon, "_is_demucs_available", lambda: False)

    res = music_surgeon.run_selective_music_surgery(
        in_wav,
        tmp_path / "out.wav",
        intervals=[{"start": 0.5, "end": 3.5}],
    )
    assert res["status"] == "human_review"
    assert res["code"] == "NEEDS_HUMAN_AUDIO_CHECK"


def test_green_seal_15s_censors_severe_ptbr_respects_allowlist_protects_cold_open_and_bleeps_audio(tmp_path: Path):
    from picorte.risk_shield.green_seal_15s import apply_audio_bleeps, plan_green_seal_audio_and_captions

    words = [
        {"word": "Meu", "start": 10.0, "end": 10.2},
        {"word": "computador", "start": 10.2, "end": 10.6},  # allowlist! não pode censurar 'puta'
        {"word": "travou,", "start": 10.6, "end": 11.0},
        {"word": "porra!", "start": 11.1, "end": 11.5},     # 1.1s do clipe -> censurar!
        {"word": "caralho", "start": 14.0, "end": 14.4},    # 4.0s do clipe -> censurar!
        {"word": "foda-se", "start": 32.0, "end": 32.5},    # 22.0s (fora dos 15s, MAS está no Cold Open!)
    ]
    cold_open = {"enabled": True, "teaser_start": 31.5, "teaser_end": 33.0}

    plan = plan_green_seal_audio_and_captions(
        words, clip_start=10.0, clip_end=40.0, cold_open_plan=cold_open
    )
    assert plan["status"] == "auto_fixed"
    censored_texts = [w["word"] for w in plan["censored_words"]]
    assert "computador" in censored_texts  # allowlist intacta!
    assert censored_texts[3] == "***"
    assert censored_texts[4] == "***"
    assert len(plan["bleep_intervals"]) == 2
    assert len(plan["cold_open_hits"]) == 1  # detectou palavrão no teaser do Cold Open!

    # Testa bleep/soft-mute real em WAV sem click/clipping
    sr = 16000
    t = np.linspace(0, 6.0, sr * 6, endpoint=False, dtype=np.float32)
    in_wav = _write_wav(tmp_path / "talk.wav", 0.35 * np.sin(2 * math.pi * 300.0 * t), sr=sr)
    out_wav = tmp_path / "bleeped.wav"
    apply_audio_bleeps(in_wav, out_wav, [{"start": 1.1, "end": 1.5}], mode="soft_mute", fade_ms=15.0)
    arr, _ = _read_wav(out_wav)
    # Trecho mutado (1.2s..1.4s) tem amplitude muito reduzida, trecho fora (3.0s..3.5s) intacto
    muted_rms = float(np.sqrt(np.mean(arr[int(1.2 * sr) : int(1.4 * sr)] ** 2)))
    normal_rms = float(np.sqrt(np.mean(arr[int(3.0 * sr) : int(3.5 * sr)] ** 2)))
    assert muted_rms < normal_rms * 0.1


def test_green_seal_visual_detects_gore_and_nudity_and_react_guard_distinguishes_browser_from_game_ui():
    from picorte.risk_shield.green_seal_15s import score_frame_visual_safety
    from picorte.risk_shield.react_guard import detect_dangerous_react

    # Frame seguro de gameplay (verde/azul equilibrado)
    safe_frame = np.full((360, 640, 3), (90, 120, 60), dtype=np.uint8)
    s_safe = score_frame_visual_safety(safe_frame)
    assert s_safe["safe"] is True

    # Frame com sangue saturado concentrado (gore)
    gore_frame = safe_frame.copy()
    gore_frame[60:300, 140:500] = (15, 18, 210)  # BGR vermelho-sangue intenso
    s_gore = score_frame_visual_safety(gore_frame)
    assert s_gore["safe"] is False
    assert "gore" in s_gore["flags"]

    # Frame com exposição excessiva de pele (banho/nudez)
    skin_frame = np.full((360, 640, 3), (128, 162, 212), dtype=np.uint8)  # BGR tom de pele dominante
    s_skin = score_frame_visual_safety(skin_frame)
    assert s_skin["safe"] is False
    assert "nudity_exposure" in s_skin["flags"]

    # React Guard: 4 frames (4s a 1fps) com interface de browser branco + barra vermelha do YouTube no rodapé
    browser_frames = []
    for _ in range(4):
        bf = np.full((360, 640, 3), (242, 242, 245), dtype=np.uint8)
        bf[0:32, :] = (225, 225, 230)  # barra de abas/endereço no topo
        cv2.rectangle(bf, (20, 44), (480, 315), (25, 25, 28), -1)  # player de vídeo
        cv2.rectangle(bf, (20, 305), (360, 311), (10, 10, 235), -1)  # barra vermelha YouTube
        browser_frames.append(bf)

    r_browser = detect_dangerous_react(
        browser_frames, fps_sampled=1.0, transcript_text="vamos ver esse vídeo aqui do youtube"
    )
    assert r_browser["is_dangerous_react"] is True
    assert r_browser["status"] == "hard_block"

    # Jogo normal com celular in-game pequeno no canto (NÃO pode dar falso positivo!)
    game_phone_frames = []
    for _ in range(4):
        gf = np.full((360, 640, 3), (55, 80, 65), dtype=np.uint8)
        cv2.rectangle(gf, (520, 180), (610, 330), (235, 235, 240), -1)  # celular in-game GTA 6
        game_phone_frames.append(gf)
    r_game = detect_dangerous_react(game_phone_frames, fps_sampled=1.0, transcript_text="olha o celular do jason no gta")
    assert r_game["is_dangerous_react"] is False
    assert r_game["status"] == "pass"
