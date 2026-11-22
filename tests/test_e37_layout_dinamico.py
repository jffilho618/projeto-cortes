"""3.7.2 — layout dinâmico (História / Reação / Ação) e Sniper Crop ligados ao render de games."""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import numpy as np
import pytest


# ---------------------------------------------------------------- Task 1: eventos medidos

def test_rosto_mexendo_muito_vira_evento_de_reacao():
    from picorte.engine.reframe_games import _desired_layout, layout_events_from_motion

    face = [3.0] * 10 + [30.0] * 3 + [3.0] * 7
    game = [5.0] * 20
    ev = layout_events_from_motion(face, game, times=list(range(20)))
    peak = next(e for e in ev if e["t"] == 11)
    assert _desired_layout(peak) == "reacao_split_50_50"


def test_jogo_mexendo_muito_vira_evento_de_acao():
    from picorte.engine.reframe_games import _desired_layout, layout_events_from_motion

    face = [3.0] * 20
    game = [5.0] * 12 + [60.0] * 3 + [5.0] * 5
    ev = layout_events_from_motion(face, game, times=list(range(20)))
    peak = next(e for e in ev if e["t"] == 13)
    assert _desired_layout(peak) == "acao_pip"


def test_cena_parada_nao_gera_evento():
    from picorte.engine.reframe_games import layout_events_from_motion

    ev = layout_events_from_motion([0.5] * 20, [0.8] * 20, times=list(range(20)))
    assert all(e["face_emotion"] == 0.0 and e["hud_action"] == 0.0 for e in ev)


def test_nenhum_evento_antes_de_3_5_s():
    from picorte.engine.reframe_games import layout_events_from_motion

    ev = layout_events_from_motion([30.0] * 20, [5.0] * 20, times=list(range(20)))
    assert min(e["t"] for e in ev) >= 3.5


def test_movimento_medido_dentro_e_fora_da_facecam():
    from picorte.engine.reframe_games import measure_motion

    a = np.zeros((108, 192, 3), np.uint8)
    b = a.copy()
    b[0:30, 0:40] = 255          # mexeu só dentro da facecam (canto superior esquerdo)
    face, game = measure_motion([a, b], face_box=(0, 0, 400, 300), source_w=1920, source_h=1080)
    assert face[1] > 50 and game[1] < 5


# ---------------------------------------------------------------- Task 2: filtro por trechos

def test_mapa_de_layouts_jogo_protagonista():
    from picorte.engine.reframe_games import LAYOUT_RATIO_MAP

    assert LAYOUT_RATIO_MAP["historia_70_30"] == 640
    assert LAYOUT_RATIO_MAP["reacao_split_50_50"] == 960
    assert "acao_pip" in LAYOUT_RATIO_MAP


def test_sniper_nao_anda_mais_que_o_limite_por_segundo():
    from picorte.engine.reframe_games import sniper_x_points

    centers = [(0.0, 0.1), (1.0, 0.9), (2.0, 0.9), (3.0, 0.1)]
    pts = sniper_x_points(centers, 0.0, 3.0, src_w=1920, crop_w=606, max_speed=0.15)
    for (t0, x0), (t1, x1) in zip(pts, pts[1:]):
        assert abs(x1 - x0) <= 0.15 * 1920 * (t1 - t0) + 1e-6
    assert all(0 <= x <= 1920 - 606 for _, x in pts)


TIMELINE = [{"start": 0.0, "end": 4.0, "layout": "historia_70_30"},
            {"start": 4.0, "end": 7.0, "layout": "acao_pip"},
            {"start": 7.0, "end": 8.0, "layout": "reacao_split_50_50"}]


def _graph():
    from picorte.engine.reframe_games import build_dynamic_games_filter

    centers = [(float(t), 0.3 + 0.05 * t) for t in range(8)]
    return build_dynamic_games_filter(TIMELINE, src_w=1920, src_h=1080, out_w=1080, out_h=1920,
                                      face_box=(1500, 40, 380, 300), centers=centers)


def test_filtro_tem_um_trecho_por_layout_e_concat():
    g = _graph()
    assert "concat=n=3:v=1:a=0" in g
    assert "trim=start=4.000:end=7.000" in g
    assert re.search(r"crop=\d+:\d+:x='if\(", g)  # Sniper Crop na Ação
    assert "overlay=W-w-40:240" in g               # PiP do rosto na Ação
    assert not g.rstrip().endswith("]")            # termina sem rótulo, como o filtro de hoje


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="sem ffmpeg")
def test_filtro_roda_de_verdade_no_ffmpeg(tmp_path):
    out = tmp_path / "dyn.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30:duration=8",
                    "-filter_complex", _graph() + ",setsar=1[v]", "-map", "[v]", "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out)], check=True, capture_output=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration",
                            "-of", "json", str(out)], check=True, capture_output=True, text=True)
    info = json.loads(probe.stdout)
    assert (info["streams"][0]["width"], info["streams"][0]["height"]) == (1080, 1920)
    assert float(info["format"]["duration"]) == pytest.approx(8.0, abs=0.2)


def test_pico_isolado_de_um_quadro_nao_troca_o_layout():
    """Olhada no render real (2026-11-22): 15 trocas em 78 s — um quadro agitado sozinho não pode trocar."""
    from picorte.engine.reframe_games import _desired_layout, layout_events_from_motion

    face = [3.0] * 30
    game = [5.0] * 30
    game[12] = 60.0
    ev = layout_events_from_motion(face, game, times=list(range(30)))
    assert all(_desired_layout(e) == "historia_70_30" for e in ev)


def test_reacao_sustentada_troca_o_layout():
    from picorte.engine.reframe_games import _desired_layout, layout_events_from_motion

    face = [3.0] * 10 + [30.0] * 4 + [3.0] * 16
    ev = layout_events_from_motion(face, [5.0] * 30, times=list(range(30)))
    assert any(_desired_layout(e) == "reacao_split_50_50" for e in ev)


def test_pedaco_final_curto_junta_com_o_anterior():
    from picorte.engine.reframe_games import compute_dynamic_layout_timeline

    ev = [{"t": 10.0, "face_emotion": 0.9, "hud_action": 0.0}, {"t": 19.2, "face_emotion": 0.0, "hud_action": 0.9}]
    tl = compute_dynamic_layout_timeline(ev, 20.0)
    assert all(s["end"] - s["start"] >= 2.0 for s in tl)
    assert tl[-1]["end"] == 20.0


# ---------------------------------------------------------------- Task 3: render

def test_sem_facecam_o_render_cai_no_layout_fixo():
    from picorte.engine.reframe_games import plan_dynamic_games

    plan = plan_dynamic_games([], face_box=None, source_w=1920, source_h=1080, out_w=1080, out_h=1920)
    assert plan["vf"] is None
    assert "facecam" in plan["motivo"]


def test_um_trecho_so_de_historia_nao_conta_como_transformacao():
    from picorte.engine.reframe_games import plan_dynamic_games

    frames = [np.full((108, 192, 3), 10, np.uint8) for _ in range(8)]
    plan = plan_dynamic_games(frames, face_box=(1500, 40, 380, 300), source_w=1920, source_h=1080,
                              out_w=1080, out_h=1920, vision_preset="low")
    assert plan["vf"] is not None
    assert [s["layout"] for s in plan["timeline"]] == ["historia_70_30"]
    assert plan["trocas"] == 0
