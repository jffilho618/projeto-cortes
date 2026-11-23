"""Code review do motor — fatia (a), 2026-11-23: o que o painel precisa acompanhar das mudanças do motor.

O painel (Épico 6) tem review próprio; aqui só o que o motor mudou e deixaria o painel mostrando dado falso.
"""
from __future__ import annotations

from pathlib import Path

from picorte.services.revisao import _sinais
from picorte.services.sinais import sinais_medidos


def test_painel_nao_mostra_facecam_de_movimento_como_medida():
    """Sem detector de rosto a 'facecam' é só movimento do quadro (nota cravada em 3,5): não é medida."""
    seg = {"evidence": {"vision_measured": True, "facecam_measured": False, "visual_games": 3.5}}
    assert sinais_medidos(seg)["score_visual"] is None
    medido = {"evidence": {"vision_measured": True, "facecam_measured": True, "visual_games": 7.2}}
    assert sinais_medidos(medido)["score_visual"] == 7.2
    antigo = {"evidence": {"vision_measured": True, "visual_games": 6.0}}  # segments.json de antes do review
    assert sinais_medidos(antigo)["score_visual"] == 6.0


def test_visao_degradada_aparece_como_falha_com_motivo(tmp_path: Path):
    seg = {"evidence": {"vision_measured": True, "facecam_measured": False, "visual_games": 3.5}}
    saude = {"vision": {"status": "failed", "detail": "12 candidatos medidos, mas degradado: MediaPipe indisponível"}}
    (visao,) = [s for s in _sinais(seg, saude, tmp_path) if s["chave"] == "visual"]
    assert visao["estado"] == "falhou" and "MediaPipe" in visao["motivo"]


def test_energia_do_audio_segue_a_parte_audio_da_saude(tmp_path: Path):
    """O motor passou a gravar a parte 'audio' (antes o painel olhava a prosódia para a energia do áudio)."""
    saude = {"audio": {"status": "failed", "detail": "não deu para medir o áudio de audio.webm"},
             "prosody": {"status": "ok", "detail": "40 candidatos medidos"}}
    (audio,) = [s for s in _sinais({"evidence": {}}, saude, tmp_path) if s["chave"] == "audio"]
    assert audio["estado"] == "falhou" and "audio.webm" in audio["motivo"]
