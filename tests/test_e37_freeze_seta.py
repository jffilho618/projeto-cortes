"""3.7.5 — freeze + círculo/seta no momento-chave medido e edição dirigida pelo conteúdo."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

WORDS = [{"word": w, "start": s, "end": e} for w, s, e in (
    ("olha", 100.0, 100.4), ("isso", 100.5, 100.9), ("ele", 110.0, 110.3), ("caiu", 110.4, 110.8),
    ("do", 110.9, 111.0), ("prédio", 111.1, 111.6))]
PEAK = [{"cause_second": 120.0, "vel_zscore": 6.0}]


# ---------------------------------------------------------------- plano do freeze

def test_freeze_no_climax_medido():
    from picorte.engine.edit_effects import freeze_for_segment

    plan = freeze_for_segment({"start": 100.0, "end": 130.0}, WORDS, PEAK, max_len=58)
    assert plan["enabled"] is True
    assert plan["t"] == pytest.approx(20.0)
    assert 0.6 <= plan["d"] <= 1.2


def test_sem_sinal_medido_sem_freeze():
    from picorte.engine.edit_effects import freeze_for_segment

    plan = freeze_for_segment({"start": 100.0, "end": 130.0}, WORDS, [], max_len=58)
    assert plan["enabled"] is False


def test_freeze_nao_estoura_o_max_len():
    from picorte.engine.edit_effects import freeze_for_segment

    plan = freeze_for_segment({"start": 100.0, "end": 157.8}, WORDS, PEAK, max_len=58)
    assert plan["enabled"] is False


def test_longo_e_compostos_sem_freeze():
    from picorte.engine.edit_effects import freeze_for_segment

    for fmt in ("longo_16x9", "arco_2_atos", "compilacao"):
        assert freeze_for_segment({"start": 100.0, "end": 130.0, "formato": fmt}, WORDS, PEAK,
                                  max_len=300)["enabled"] is False


# ---------------------------------------------------------------- edição dirigida pelo conteúdo

def test_cor_da_seta_vem_do_arquetipo():
    from picorte.engine.edit_effects import arrow_color_for

    assert arrow_color_for("nobada_vacilo") != arrow_color_for("mico_constrangimento")
    assert arrow_color_for("nobada_vacilo") == arrow_color_for("rage_tilt")  # mesmo estilo (hype)


def test_mesmo_arquetipo_com_momento_chave_diferente_sai_diferente():
    from picorte.engine.edit_effects import freeze_for_segment

    a = freeze_for_segment({"start": 100.0, "end": 130.0, "archetype": "caos_coop"}, WORDS,
                           [{"cause_second": 110.0, "vel_zscore": 5.0}], max_len=58)
    b = freeze_for_segment({"start": 100.0, "end": 130.0, "archetype": "caos_coop"}, WORDS,
                           [{"cause_second": 124.0, "vel_zscore": 5.0}], max_len=58)
    assert a["t"] != b["t"]


def test_alvo_muda_com_o_layout_do_instante():
    from picorte.engine.edit_effects import target_point

    tl = [{"start": 0.0, "end": 10.0, "layout": "historia_70_30"}, {"start": 10.0, "end": 20.0, "layout": "acao_pip"}]
    assert target_point(tl, 5.0, 1080, 1920) != target_point(tl, 15.0, 1080, 1920)
    assert target_point([], 5.0, 1080, 1920) == (540, 960)


# ---------------------------------------------------------------- render

def test_comando_do_freeze():
    from picorte.engine.edit_effects import freeze_ffmpeg_cmd

    cmd = freeze_ffmpeg_cmd("in.mp4", "seta.png", "out.mp4", t=2.0, d=0.8)
    g = cmd[cmd.index("-filter_complex") + 1]
    assert "tpad=stop_mode=clone:stop_duration=0.800" in g
    assert "apad=pad_dur=0.800" in g
    assert "enable='between(t,2.000,2.800)'" in g
    assert "concat=n=2:v=1:a=1" in g


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="sem ffmpeg")
def test_freeze_de_verdade(tmp_path):
    from picorte.engine.edit_effects import apply_freeze

    mp4 = tmp_path / "c.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=360x640:rate=30:duration=4",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(mp4)], check=True, capture_output=True)
    seg = {"freeze": {"enabled": True, "t": 2.0, "d": 0.8}, "archetype": "nobada_vacilo"}
    assert apply_freeze(seg, mp4, size=(360, 640)) is True
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(mp4)],
                           check=True, capture_output=True, text=True)
    assert float(json.loads(probe.stdout)["format"]["duration"]) == pytest.approx(4.8, abs=0.15)
    assert any(t["nome"] == "freeze_seta" for t in seg["transformacoes"])


def test_teaser_depois_do_freeze_e_deslocado():
    from picorte.engine.edit_effects import cold_open_start_after_freeze

    plan = {"enabled": True, "teaser_start": 125.0}
    assert cold_open_start_after_freeze(100.0, plan, {"enabled": True, "t": 20.0, "d": 0.8}) == pytest.approx(99.2)
    assert cold_open_start_after_freeze(100.0, plan, {"enabled": True, "t": 26.0, "d": 0.8}) == 100.0
    assert cold_open_start_after_freeze(100.0, plan, None) == 100.0


def test_faixa_de_contexto_entra_nas_transformacoes():
    from render_clips import _record_banner

    seg = {"context_banner_2s": "ELE CAIU DO PRÉDIO"}
    _record_banner(seg, "ELE CAIU DO PRÉDIO")
    assert seg["transformacoes"][0]["nome"] == "faixa_contexto"
