"""Code review do motor — fatia (c) render e formato (2026-11-23).

Cada teste nasceu de um achado verificado no código; o nome diz o que quebrava.
"""
from __future__ import annotations

import pytest

import render_clips


def _w(word, s, e, **extra):
    return {"word": word, "start": s, "end": e, **extra}


# ------------------------------------------------------------------ item 1 (P1): idioma filtrado não escapa do Selo Verde

def test_palavrao_em_ingles_filtrado_da_legenda_ainda_leva_bleep():
    """Medido no review: 'mano / what the fuck is that?' numa live PT saía com bleeps [] e status pass."""
    todas = [_w("mano", 0.5, 0.9), _w("what", 2.0, 2.1), _w("the", 2.1, 2.2), _w("fuck", 2.3, 2.6),
             _w("is", 2.7, 2.8), _w("that?", 2.8, 3.0)]
    legenda = [todas[0]]  # o filtro de "inglês de NPC" deixa só "mano"
    seg = {}
    out = render_clips._apply_green_seal(seg, legenda, 0.0, 30.0, full_words=todas)
    assert seg["_green_seal_bleeps"], "o áudio ainda tem o palavrão: precisa de bleep"
    assert seg["_green_seal_status"] != "pass"
    assert [w["word"] for w in out] == ["mano"]


def test_camada_3_que_saiu_da_legenda_ainda_bloqueia():
    """O bloqueio olha o áudio inteiro, não só o que sobrou na legenda (a lista da Camada 3 é só PT: W55)."""
    from picorte.risk_shield.policy_gate import PolicyViolationError

    todas = [_w("mano", 0.5, 0.9), _w("estupro", 2.0, 2.4)]
    with pytest.raises(PolicyViolationError):
        render_clips._apply_green_seal({}, [todas[0]], 0.0, 30.0, full_words=todas)


# ------------------------------------------------------------------ item 2 (P1): legenda do teaser censurada

def test_palavrao_do_teaser_sai_censurado_na_legenda():
    """O teaser toca no 0:00: o palavrão dele (aos 20 s do corte) não pode aparecer escrito na tela."""
    palavras = [_w("olha", 1.0, 1.4), _w("porra", 20.1, 20.5), _w("mano", 20.6, 21.0)]
    seg = {"cold_open": {"enabled": True, "teaser_start": 19.5, "teaser_end": 21.0}}
    out = render_clips._apply_green_seal(seg, palavras, 0.0, 30.0)
    assert [w["word"] for w in out] == ["olha", "***", "mano"]
    assert seg["_cold_open_bleeps"]


# ------------------------------------------------------------------ item 4: teaser não vira quadro congelado

def test_teaser_que_pega_o_freeze_termina_no_climax():
    start = 100.0
    seg = {"freeze": {"enabled": True, "t": 10.0, "d": 0.8},
           "cold_open": {"enabled": True, "teaser_start": start + 9.25, "teaser_end": start + 10.75}}
    render_clips._teaser_before_freeze(seg, start)
    co = seg["cold_open"]
    assert co["teaser_end"] == pytest.approx(start + 10.0)
    assert co["teaser_start"] == pytest.approx(start + 8.5)
    assert "freeze" in co.get("ajuste", "")


def test_teaser_longe_do_freeze_fica_como_estava():
    seg = {"freeze": {"enabled": True, "t": 30.0, "d": 0.8},
           "cold_open": {"enabled": True, "teaser_start": 105.0, "teaser_end": 106.5}}
    render_clips._teaser_before_freeze(seg, 100.0)
    assert (seg["cold_open"]["teaser_start"], seg["cold_open"]["teaser_end"]) == (105.0, 106.5)


# ------------------------------------------------------------------ item 5: .srt acompanha freeze e Cold Open

def test_srt_acompanha_freeze_e_cold_open():
    from picorte.engine.retention_engine import COLD_OPEN_XFADE_S

    start = 100.0
    seg = {"freeze": {"enabled": True, "rendered": True, "t": 10.0, "d": 0.8},
           "cold_open": {"enabled": True, "rendered": True, "teaser_start": 108.5, "teaser_end": 110.0}}
    words = [_w("antes", 105.0, 105.5), _w("depois", 112.0, 112.5)]
    out, extra = render_clips._srt_timeline(seg, words, start)
    teaser = 1.5 - COLD_OPEN_XFADE_S
    assert out[0]["start"] == pytest.approx(105.0 + teaser)
    assert out[1]["start"] == pytest.approx(112.0 + 0.8 + teaser)
    assert extra == pytest.approx(0.8 + teaser)


def test_srt_sem_efeitos_fica_igual():
    words = [_w("oi", 101.0, 101.5)]
    out, extra = render_clips._srt_timeline({}, words, 100.0)
    assert out == words and extra == 0.0


# ------------------------------------------------------------------ item 6: re-render não duplica transformações

def test_rerender_nao_duplica_transformacoes_nem_mexe_no_segmento_original():
    original = {"transformacoes": [{"nome": "faixa_contexto"}, {"nome": "fim_antes"}, {"nome": "cold_open"}]}
    seg = {**original}  # como o main() copia: lista compartilhada
    render_clips._reset_render_transforms(seg)
    assert [t["nome"] for t in seg["transformacoes"]] == ["fim_antes"]
    assert len(original["transformacoes"]) == 3


# ------------------------------------------------------------------ item 8: --tighten mantém escondida/ênfase

def test_tighten_mantem_palavra_escondida_e_enfase():
    import tighten

    words = [_w("oi", 0.5, 0.9, hidden=True), _w("mano", 1.0, 1.4, emphasis=True)]
    out, _ = tighten.remap_words(words, 0.0, [(0.0, 2.0)])
    assert out[0].get("hidden") is True and out[1].get("emphasis") is True


# ------------------------------------------------------------------ item 10: um corte barrado não para o lote

def test_lote_segue_quando_um_corte_e_barrado_pelo_selo_verde():
    from picorte.risk_shield.policy_gate import PolicyViolationError

    def render_one(seg):
        if seg["id"] == "002":
            raise PolicyViolationError("[P1:selo_verde] Camada 3", code="green_seal_hard_block")
        return f"{seg['id']}.mp4"

    segs = [{"hook": "a"}, {"hook": None}, {"hook": "c"}]
    saved, failed, blocked = render_clips._render_batch(segs, render_one)
    assert saved == ["001.mp4", "003.mp4"] and failed == 0
    assert blocked and "002" in blocked[0]


# ------------------------------------------------------------------ item 9: freeze/Cold Open na saúde

def test_freeze_e_cold_open_vao_para_a_saude(tmp_path):
    from picorte.engine import health

    seg = {"freeze": {"enabled": True, "rendered": True},
           "cold_open": {"enabled": True, "rendered": False,
                         "motivo": "falha no ffmpeg ao colar o teaser (corte saiu sem Cold Open)"}}
    render_clips._record_effects_health(tmp_path, seg)
    h = health.load(tmp_path)
    assert h["freeze"]["status"] == "ok"
    assert h["cold_open"]["status"] == "failed" and "ffmpeg" in h["cold_open"]["detail"]


def test_efeito_desligado_de_proposito_e_na(tmp_path):
    from picorte.engine import health

    seg = {"cold_open": {"enabled": False, "motivo": "preview"}}
    render_clips._record_effects_health(tmp_path, seg)
    assert health.load(tmp_path)["cold_open"]["status"] == "na"


# ------------------------------------------------------------------ item 7: compostos

def _comp():
    return {"id": "arc1", "formato": "compilacao", "hook": "top", "freeze": {"enabled": True, "t": 3.0},
            "context_banner_2s": "TÍTULO DO COMPOSTO", "proposed_title": "TÍTULO", "thumbnail_1280x720": "x.png",
            "trechos": [{"start": float(i * 30), "end": float(i * 30 + 20)} for i in range(4)]}


def test_trecho_do_composto_nao_herda_freeze_banner_nem_titulo(tmp_path):
    from picorte.engine.composites import render_composite

    vistos = []

    def fake_render(sub, out_dir):
        vistos.append(sub)
        p = tmp_path / f"{sub['id']}.mp4"
        p.write_bytes(b"x")
        return p

    render_composite(_comp(), out_dir=tmp_path, render_fn=fake_render, concat_fn=lambda parts, final: None,
                     size=(1080, 1920))
    assert vistos and all(k not in s for s in vistos for k in ("freeze", "context_banner_2s", "proposed_title",
                                                                 "thumbnail_1280x720"))
    assert all(s.get("sem_banner") for s in vistos)


def test_composto_que_falha_na_emenda_nao_deixa_arquivo_solto(tmp_path):
    import subprocess

    from picorte.engine.composites import render_composite

    def fake_render(sub, out_dir):
        p = tmp_path / f"{sub['id']}.mp4"
        p.write_bytes(b"x")
        return p

    def emenda_quebra(parts, final):
        raise subprocess.CalledProcessError(1, "ffmpeg")

    with pytest.raises(subprocess.CalledProcessError):
        render_composite(_comp(), out_dir=tmp_path, render_fn=fake_render, concat_fn=emenda_quebra,
                         size=(1080, 1920))
    assert not list(tmp_path.glob("arc1-p*.mp4"))
