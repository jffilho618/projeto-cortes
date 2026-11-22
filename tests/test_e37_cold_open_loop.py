"""3.7.1 — Cold Open Reverso (teaser do clímax medido) e Seamless Loop (fim de frase que emenda)."""
from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pytest


def _words(items):
    return [{"word": w, "start": s, "end": e} for w, s, e in items]


WORDS = _words([("olha", 100.0, 100.4), ("isso", 100.5, 100.9), ("aqui", 101.0, 101.3),
                ("ele", 110.0, 110.3), ("caiu", 110.4, 110.8), ("do", 110.9, 111.0), ("prédio", 111.1, 111.6)])


# ---------------------------------------------------------------- Task 1: clímax

def test_climax_vem_do_pico_de_chat_mais_forte_dentro_do_corte():
    from picorte.engine.retention_engine import pick_climax

    seg = {"start": 100.0, "end": 130.0}
    peaks = [{"cause_second": 112.0, "vel_zscore": 4.0}, {"cause_second": 120.0, "vel_zscore": 6.5},
             {"cause_second": 140.0, "vel_zscore": 9.0}]
    assert pick_climax(seg, WORDS, peaks) == {"t": 120.0, "fonte": "chat"}


def test_pico_cedo_demais_nao_vira_climax():
    from picorte.engine.retention_engine import pick_climax

    seg = {"start": 100.0, "end": 130.0}
    assert pick_climax(seg, WORDS, [{"cause_second": 101.0, "vel_zscore": 9.0}]) is None


def test_sem_chat_o_climax_e_o_fim_da_punchline():
    from picorte.engine.retention_engine import pick_climax

    seg = {"start": 100.0, "end": 130.0, "hook_quote": "ele caiu do prédio"}
    assert pick_climax(seg, WORDS, []) == {"t": pytest.approx(111.1), "fonte": "punchline"}


def test_punchline_acha_mesmo_com_acento_pontuacao_e_uma_palavra_trocada():
    """Olhada nas 4 lives (2026-11-22): o hook_quote do Editor raramente bate palavra por palavra."""
    from picorte.engine.retention_engine import pick_climax

    seg = {"start": 100.0, "end": 130.0, "hook_quote": "Ele DESPENCOU do predio!"}
    assert pick_climax(seg, WORDS, []) == {"t": pytest.approx(111.1), "fonte": "punchline"}


def test_prompt_pede_hook_quote_literal():
    from picorte.ai.llm_router import COMPANION_SYSTEM_PROMPT

    assert "COPIADA LITERALMENTE" in COMPANION_SYSTEM_PROMPT


def test_punchline_parecida_demais_com_nada_nao_vira_climax():
    from picorte.engine.retention_engine import pick_climax

    seg = {"start": 100.0, "end": 130.0, "hook_quote": "que jogada absurda meu deus"}
    assert pick_climax(seg, WORDS, []) is None


def test_sem_sinal_medido_sem_cold_open():
    from picorte.engine.retention_engine import cold_open_for_segment

    plan = cold_open_for_segment({"start": 100.0, "end": 130.0, "archetype": "nobada_vacilo"}, WORDS, [])
    assert plan["enabled"] is False
    assert "medido" in plan["motivo"]


def test_arquetipo_sem_spoiler_nao_ganha_cold_open():
    from picorte.engine.retention_engine import cold_open_for_segment

    seg = {"start": 100.0, "end": 130.0, "archetype": "mico_constrangimento"}
    plan = cold_open_for_segment(seg, WORDS, [{"cause_second": 120.0, "vel_zscore": 6.0}])
    assert plan["enabled"] is False


def test_cold_open_com_climax_medido():
    from picorte.engine.retention_engine import cold_open_for_segment

    seg = {"start": 100.0, "end": 130.0, "archetype": "nobada_vacilo"}
    plan = cold_open_for_segment(seg, WORDS, [{"cause_second": 120.0, "vel_zscore": 6.0}])
    assert plan["enabled"] is True
    assert plan["teaser_start"] <= 120.0 <= plan["teaser_end"]
    assert plan["climax_fonte"] == "chat"


def test_max_len_avanca_o_comeco_sem_cortar_o_climax():
    from picorte.engine.retention_engine import cold_open_for_segment

    seg = {"start": 100.0, "end": 158.0, "archetype": "nobada_vacilo"}  # 58 s + teaser
    plan = cold_open_for_segment(seg, WORDS, [{"cause_second": 140.0, "vel_zscore": 6.0}], max_len=58)
    assert plan["enabled"] is True
    total = (158.0 - plan["novo_inicio"]) + plan["teaser_duration"] - 0.25
    assert total <= 58.0 + 1e-6
    assert plan["novo_inicio"] < plan["teaser_start"]


def test_max_len_desliga_quando_o_climax_esta_cedo_demais():
    from picorte.engine.retention_engine import cold_open_for_segment

    seg = {"start": 100.0, "end": 158.0, "archetype": "nobada_vacilo"}
    plan = cold_open_for_segment(seg, WORDS, [{"cause_second": 103.2, "vel_zscore": 6.0}], max_len=58)
    assert plan["enabled"] is False


# ---------------------------------------------------------------- Task 2: teaser no vídeo

def test_comando_do_teaser_corta_o_climax_e_emenda_com_xfade():
    from picorte.engine.retention_engine import cold_open_ffmpeg_cmd

    cmd = cold_open_ffmpeg_cmd("in.mp4", "out.mp4", 19.25, 1.5, [{"start": 0.2, "end": 0.6}])
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "trim=start=19.250:end=20.750" in graph
    assert "xfade=transition=fade:duration=0.250:offset=1.250" in graph
    assert "acrossfade=d=0.250" in graph
    assert "between(t,0.200,0.600)" in graph  # bleep do Selo Verde no teaser
    assert cmd[-1] == "out.mp4"


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="sem ffmpeg")
def test_teaser_de_verdade_num_video_sintetico(tmp_path):
    from picorte.engine.retention_engine import prepend_cold_open

    mp4 = tmp_path / "corte.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=6",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(mp4)],
                   check=True, capture_output=True)
    plan = {"enabled": True, "teaser_start": 13.0, "teaser_end": 14.5, "teaser_duration": 1.5}
    assert prepend_cold_open(mp4, plan, 10.0, []) is True
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(mp4)],
                         check=True, capture_output=True, text=True)
    dur = float(json.loads(out.stdout)["format"]["duration"])
    assert dur == pytest.approx(6.0 + 1.5 - 0.25, abs=0.15)


def test_teaser_desligado_nao_mexe_no_arquivo(tmp_path):
    from picorte.engine.retention_engine import prepend_cold_open

    calls = []
    assert prepend_cold_open(tmp_path / "x.mp4", {"enabled": False}, 0.0, [], runner=lambda *a, **k: calls.append(a)) \
        is False
    assert calls == []


def test_escudo_usa_o_cold_open_renderizado_de_verdade():
    import inspect

    from picorte.risk_shield import pipeline

    src = inspect.getsource(pipeline.attach_risk_verdict)
    assert "has_cold_open=False" not in src
    assert "rendered" in src


# ---------------------------------------------------------------- Task 3: Seamless Loop

SENTS = [{"start": 100.0, "end": 104.0, "text": "a"}, {"start": 105.0, "end": 127.6, "text": "b"},
         {"start": 128.0, "end": 129.2, "text": "c"}, {"start": 129.5, "end": 131.0, "text": "d"}]


def test_loop_escolhe_o_fim_de_frase_com_volume_parecido_com_o_comeco():
    from picorte.engine.retention_engine import seamless_loop_end

    rms = np.full(200, -20.0)
    rms[100] = -30.0          # começo do corte
    rms[127] = -31.0          # fim de frase com volume parecido
    rms[129] = -10.0          # fim de frase com volume bem diferente
    assert seamless_loop_end(SENTS, 100.0, 129.0, rms=rms) == pytest.approx(127.6)


def test_loop_nao_recua_mais_de_1_5_s_para_nao_cortar_a_reacao():
    from picorte.engine.retention_engine import seamless_loop_end

    rms = np.full(200, -20.0)
    rms[100] = -30.0
    rms[127] = -30.0  # volume idêntico ao começo, mas 2,4 s antes do fim: fora do alcance
    assert seamless_loop_end(SENTS, 100.0, 130.0, rms=rms) >= 128.5


def test_loop_sem_fim_de_frase_no_intervalo_mantem_o_fim():
    from picorte.engine.retention_engine import seamless_loop_end

    assert seamless_loop_end(SENTS, 100.0, 118.0) == 118.0


def test_loop_depois_do_riso_so_pode_avancar():
    from picorte.engine.retention_engine import seamless_loop_end

    rms = np.full(200, -20.0)
    rms[100] = -30.0
    rms[127] = -30.0
    out = seamless_loop_end(SENTS, 100.0, 129.0, rms=rms, only_forward=True)
    assert out >= 129.0


def test_loop_respeita_o_max_len():
    from picorte.engine.retention_engine import seamless_loop_end

    assert seamless_loop_end(SENTS, 100.0, 129.0, max_len=29.0) <= 129.0
