from __future__ import annotations

import numpy as np
import pytest


def test_audio_align_finds_shifted_lag_via_fft():
    from picorte.engine.audio_align import find_audio_offset

    sr = 16000
    t = np.linspace(0, 4.0, sr * 4, endpoint=False)
    # Impulso harmônico em t=1.0s na referência e t=1.5s no alvo -> alvo atrasado +0.5s
    ref = np.zeros_like(t)
    burst = np.sin(2 * np.pi * 440.0 * t[: sr // 4]) * np.hanning(sr // 4)
    ref[sr : sr + sr // 4] = burst

    target = np.zeros_like(t)
    shift = int(1.5 * sr)
    target[shift : shift + sr // 4] = burst

    offset_s = find_audio_offset(ref, target, sample_rate=sr)
    assert offset_s == pytest.approx(0.5, abs=0.03)


def test_retention_engine_cold_open_banner_loop_cross_and_pairing():
    from picorte.engine.retention_engine import (
        build_cold_open_plan,
        build_context_banner_ass,
        build_cross_streamer_sync_plan,
        find_seamless_loop_end,
        pair_short_and_long_clips,
    )

    plan = build_cold_open_plan(100.0, 145.0, peak_t=132.0, teaser_dur=1.5)
    assert 1.2 <= plan["teaser_duration"] <= 1.8
    assert plan["teaser_start"] >= 100.0
    assert plan["teaser_end"] <= 145.0

    ass = build_context_banner_ass("O QUE ELE FEZ AQUI?!", width=1080, height=1920, duration_s=2.0)
    assert "0:00:02.00" in ass
    assert "\\pos(540,300)" in ass or "\\an8" in ass
    assert "O QUE ELE FEZ AQUI?!" in ass

    words = [
        {"word": "ele", "start": 100.2, "end": 100.5},
        {"word": "ganhou", "start": 139.0, "end": 139.6},
        {"word": "tudo", "start": 141.2, "end": 141.6},
    ]
    loop_end = find_seamless_loop_end(words, 100.0, 145.0)
    assert 141.6 <= loop_end <= 145.0

    sr = 8000
    base = np.zeros(sr * 2, dtype=np.float32)
    base[4000:5000] = np.sin(np.linspace(0, 30, 1000))
    shifted = np.zeros(sr * 2, dtype=np.float32)
    shifted[4800:5800] = base[4000:5000]
    sync = build_cross_streamer_sync_plan([base, shifted], sample_rate=sr)
    assert len(sync["offsets_s"]) == 2
    assert sync["offsets_s"][0] == pytest.approx(0.0)
    assert sync["offsets_s"][1] == pytest.approx(0.1, abs=0.03)

    long_clip = {"id": "long-1", "start": 90.0, "end": 300.0, "duration": 210.0, "aspect": "16:9"}
    short_clip = {"id": "short-1", "start": 110.0, "end": 152.0, "duration": 42.0, "aspect": "9:16"}
    paired = pair_short_and_long_clips([long_clip, short_clip])
    paired_short = next(c for c in paired if c["id"] == "short-1")
    assert paired_short["parent_long_clip_id"] == "long-1"


def test_thumbnail_factory_1280x720_presets_and_safe_zones(tmp_path):
    import cv2
    from picorte.engine.thumbnail_factory import generate_thumbnail

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :] = (30, 30, 80)
    frame[150:680, 720:1150] = (200, 180, 150)  # sujeito simulado à direita

    cutout_calls = []

    def fake_cutout(img, model_name):
        cutout_calls.append(model_name)
        mask = np.zeros(img.shape[:2], dtype=np.uint8)
        mask[150:680, 720:1150] = 255
        return mask

    out_low = tmp_path / "thumb_low.png"
    res_low = generate_thumbnail(
        frame,
        out_low,
        title_text="CLUTCH ABSURDO NO FINAL DA PARTIDA EPICA",
        vision_preset="low",
        vram_mib=4096,
        cutout_runner=fake_cutout,
    )
    assert res_low["cutout_model"] == "u2netp"
    assert res_low["width"] == 1280 and res_low["height"] == 720
    assert out_low.is_file() and out_low.stat().st_size <= 2 * 1024 * 1024
    assert len(res_low["words"]) <= 6
    loaded = cv2.imread(str(out_low))
    assert loaded.shape == (720, 1280, 3)

    out_high = tmp_path / "thumb_high.png"
    res_high = generate_thumbnail(
        frame,
        out_high,
        title_text="IMPOSSÍVEL ESSE CLUTCH!",
        vision_preset="high",
        vram_mib=12288,
        cutout_runner=fake_cutout,
    )
    assert res_high["cutout_model"] == "BiRefNet"
    assert cutout_calls == ["u2netp", "BiRefNet"]


def test_thumbnail_no_orange_pollution_on_complex_foliage_scene(tmp_path):
    import cv2
    from picorte.engine.thumbnail_factory import generate_thumbnail

    rng = np.random.default_rng(7)
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    # Simula folhagem densa (textura de alto contraste) + céu claro no topo + chão escuro
    frame[:, :] = (24, 48, 28)
    foliage = rng.integers(30, 230, size=(520, 1920, 3), dtype=np.uint8)
    foliage[:, :, 1] = np.clip(foliage[:, :, 1] + 35, 0, 255)
    frame[:520, :] = foliage
    # Minimapa brilhante no canto inferior esquerdo e legenda nativa no rodapé
    frame[880:1050, 35:320] = (90, 170, 90)
    cv2.putText(frame, "Kingfishers: texto nativo do jogo", (480, 970), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (240, 240, 240), 3)

    out_path = tmp_path / "ação_épica" / "thumb_ação.png"
    res = generate_thumbnail(
        frame,
        out_path,
        title_text="NÃO ME VÊ!",
        vision_preset="low",
        vram_mib=4096,
    )
    assert out_path.is_file()
    assert res["width"] == 1280 and res["height"] == 720
    assert res["size_bytes"] <= 2 * 1024 * 1024

    img = cv2.imdecode(np.frombuffer(out_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert img is not None and img.shape == (720, 1280, 3)

    # Nunca pode rabiscar o contorno laranja/âmbar (11, 158, 245) sobre a folhagem
    amber_mask = (
        (np.abs(img[:, :, 0].astype(int) - 11) <= 8)
        & (np.abs(img[:, :, 1].astype(int) - 158) <= 8)
        & (np.abs(img[:, :, 2].astype(int) - 245) <= 8)
    )
    assert int(amber_mask[:520, :].sum()) < 100


def test_thumbnail_uses_ffmpeg_ass_and_renders_ptbr_accents(tmp_path):
    import cv2
    from picorte.engine.thumbnail_factory import generate_thumbnail

    dark = np.full((720, 1280, 3), 24, dtype=np.uint8)
    out_pt = tmp_path / "pt.png"
    out_ascii = tmp_path / "ascii.png"
    out_q = tmp_path / "q.png"

    res_pt = generate_thumbnail(dark, out_pt, title_text="NÃO ME VÊ!", vision_preset="low")
    generate_thumbnail(dark, out_ascii, title_text="NAO ME VE!", vision_preset="low")
    generate_thumbnail(dark, out_q, title_text="N?O ME V?!", vision_preset="low")

    assert res_pt.get("text_renderer") == "ffmpeg_ass"

    img_pt = cv2.imdecode(np.frombuffer(out_pt.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    img_ascii = cv2.imdecode(np.frombuffer(out_ascii.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    img_q = cv2.imdecode(np.frombuffer(out_q.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)

    # Acentos (Ã, Ê) renderizados realmente diferentes de sem-acento e de '?'
    roi_pt = img_pt[40:520, 40:820]
    assert int(np.abs(roi_pt.astype(int) - img_ascii[40:520, 40:820].astype(int)).sum()) > 50_000
    assert int(np.abs(roi_pt.astype(int) - img_q[40:520, 40:820].astype(int)).sum()) > 100_000

    # Presença de branco forte e destaque amarelo (#FFD400 -> BGR ~(0,212,255)) na zona de texto esquerda
    white_pixels = (roi_pt[:, :, 0] > 210) & (roi_pt[:, :, 1] > 210) & (roi_pt[:, :, 2] > 210)
    gold_pixels = (roi_pt[:, :, 0] < 70) & (roi_pt[:, :, 1] > 180) & (roi_pt[:, :, 2] > 220)
    assert int(white_pixels.sum()) > 1500
    assert int(gold_pixels.sum()) > 500


def test_thumbnail_enhances_corner_facecam_and_respects_safe_zones(tmp_path, monkeypatch):
    import cv2
    import picorte.engine.thumbnail_factory as tf

    frame = np.full((1080, 1920, 3), 20, dtype=np.uint8)
    # Webcam no canto superior direito (x=1540..1920, y=0..270 -> 1027..1280, 0..180 em 720p)
    frame[0:270, 1540:1920] = (200, 180, 40)  # ciano/azul-esverdeado distinto
    frame[60:200, 1650:1760] = (180, 160, 210)  # rosto simulado

    monkeypatch.setattr(tf, "find_reactor_face", lambda _f: (1652, 63, 103, 133))
    out = tmp_path / "facecam_thumb.png"
    res = tf.generate_thumbnail(frame, out, title_text="CLUTCH ABSURDO!", vision_preset="low")

    assert res.get("facecam_detected") is True
    img = cv2.imdecode(np.frombuffer(out.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert img.shape == (720, 1280, 3)

    # A facecam ampliada deve avançar à esquerda de x=1027 (ex: x<=940) e abaixo de y=180 (ex: y>=240)
    teal_mask = (img[:, :, 0] > 150) & (img[:, :, 1] > 130) & (img[:, :, 2] < 90)
    ys, xs = np.where(teal_mask)
    assert len(xs) > 10_000
    assert int(xs.min()) < 940
    assert int(ys.max()) > 240

    # Safe zone do timecode do YouTube (canto inferior direito x>920, y>580) deve permanecer limpa/escura
    ts_zone = img[580:710, 920:1260]
    assert float(ts_zone.mean()) < 45.0
