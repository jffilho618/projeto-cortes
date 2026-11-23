"""P1 diz por quê: o Selo Verde e o React perigoso gravam o que acharam e onde; cada rede grava o próprio motivo.

Antes, o veredito compactado guardava só o status por rede e esses dois portões não traziam motivo, então a
Revisão mostrava "motivo não registrado" (pedido do dono, 2026-11-23).
"""
from __future__ import annotations

import numpy as np


def _palavras(*itens):
    return [{"word": w, "start": s, "end": s + 0.4} for w, s in itens]


def test_selo_verde_diz_o_termo_e_o_segundo_do_corte():
    from picorte.risk_shield.green_seal_15s import plan_green_seal_audio_and_captions

    revisao = plan_green_seal_audio_and_captions(_palavras(("isso", 100.0), ("é", 101.0), ("nazismo", 112.4)),
                                                 clip_start=100.0, clip_end=130.0)
    assert revisao["status"] == "human_review"
    assert revisao["reasons"] == ['termo que pede revisão humana "nazismo" aos 12 s do corte']
    duas = plan_green_seal_audio_and_captions(_palavras(("eu", 100.0), ("vou", 103.0), ("se", 105.1), ("matar", 105.6)),
                                              clip_start=100.0, clip_end=150.0)
    assert duas["reasons"] == ['termo que pede revisão humana "se matar" aos 5 s do corte']
    aborta = plan_green_seal_audio_and_captions(_palavras(("fala", 100.0), ("estupro", 140.2)), clip_start=100.0, clip_end=150.0)
    assert aborta["status"] == "hard_block" and aborta["reasons"] == ['termo grave "estupro" aos 40 s do corte']
    limpo = plan_green_seal_audio_and_captions(_palavras(("boa", 100.0)), clip_start=100.0, clip_end=130.0)
    assert limpo["reasons"] == []


def test_selo_verde_visual_diz_o_que_viu_e_quando():
    from picorte.risk_shield.green_seal_15s import audit_visual_green_seal_15s

    vermelho = np.zeros((240, 320, 3), dtype=np.uint8)
    vermelho[:, :] = (0, 0, 200)  # BGR: sangue saturado ocupando o quadro
    preto = np.zeros((240, 320, 3), dtype=np.uint8)
    r = audit_visual_green_seal_15s([preto, vermelho, vermelho], fps_sampled=1.0)
    assert r["status"] == "human_review"
    assert r["reasons"] == ["sangue (gore) na tela aos 1 s e 2 s do corte"]
    assert audit_visual_green_seal_15s([preto], fps_sampled=1.0)["reasons"] == []


def test_react_perigoso_diz_onde_comeca_quanto_dura_e_os_sinais(monkeypatch):
    import picorte.risk_shield.react_guard as rg

    quadros = [np.zeros((10, 10, 3), dtype=np.uint8) for _ in range(8)]
    altos = {3, 4, 5, 6}
    contador = iter(range(8))

    def nota(_fr, exclude_box=None):
        i = next(contador)
        return {"score": 0.9 if i in altos else 0.1, "signals": ["barra_de_navegador"] if i in altos else []}

    monkeypatch.setattr(rg, "_score_single_frame_browser_react", nota)
    r = rg.detect_dangerous_react(quadros, fps_sampled=1.0)
    assert r["status"] == "hard_block"
    assert r["reasons"] == ["vídeo ou navegador de terceiro na tela dos 3 s aos 7 s do corte (4 s seguidos; sinais: barra_de_navegador)"]
    contador = iter(range(8))
    monkeypatch.setattr(rg, "_score_single_frame_browser_react", lambda _f, exclude_box=None: {"score": 0.0, "signals": []})
    assert rg.detect_dangerous_react(quadros, fps_sampled=1.0)["reasons"] == []


def test_motivos_proprios_de_cada_rede():
    from picorte.risk_shield.orchestrator import motivos_da_rede

    copia = {"status": "human_review", "ad_friendly_warnings": [{"term": "matar", "suggestion": "eliminar"}]}
    cadencia = {"status": "block", "reason": "Teto seguro atingido em tiktok: 3/3 nas últimas 24h (perfil warmup)."}
    ypp = {"tiktok_status": "human_review", "tiktok_originality_score": 52}
    assert motivos_da_rede("tiktok", copia, cadencia, ypp) == [
        'cópia com termo que tira anúncio: "matar" (sugestão: eliminar)',
        "Teto seguro atingido em tiktok: 3/3 nas últimas 24h (perfil warmup).",
        "originalidade TikTok 52 abaixo do mínimo",
    ]
    assert motivos_da_rede("youtube_shorts", {"status": "pass"}, {"status": "ok"}, ypp) == []


def test_compact_grava_os_motivos_por_rede_e_dos_portoes():
    from picorte.risk_shield.pipeline import _compact

    bruto = {"overall_status": "hard_block",
             "per_platform": {"tiktok": {"status": "human_review", "reasons": ["cadência"]},
                              "youtube_shorts": {"status": "pass", "reasons": []}},
             "gates": {"react_guard": {"status": "hard_block", "reasons": ["navegador aos 3 s"], "signals": ["x"]}}}
    v = _compact(bruto)
    assert v["per_platform"] == {"tiktok": "human_review", "youtube_shorts": "pass"}  # formato antigo preservado
    assert v["per_platform_reasons"] == {"tiktok": ["cadência"], "youtube_shorts": []}
    assert v["gates"]["react_guard"]["reasons"] == ["navegador aos 3 s"]


def test_revisao_usa_o_motivo_gravado_da_rede():
    from picorte.services.revisao import motivos_do_veredito

    v = {"overall_status": "human_review", "per_platform": {"youtube_shorts": "pass", "tiktok": "human_review"},
         "per_platform_reasons": {"youtube_shorts": [], "tiktok": ["Teto seguro atingido em tiktok."]}, "gates": {}}
    m = motivos_do_veredito(v)
    assert m["motivos_por_rede"]["tiktok"] == [{"portao": "Esta rede", "texto": "Teto seguro atingido em tiktok."}]
    assert m["motivos_por_rede"]["youtube_shorts"] == []
