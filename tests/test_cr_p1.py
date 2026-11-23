"""Code review do motor — fatia (d) P1 (2026-11-23): nenhuma entrada baixa fonte sem passar pelo portão."""
from __future__ import annotations

import sys

import pytest


def test_download_pela_linha_de_comando_passa_pelo_portao_p1(monkeypatch, tmp_path):
    import download_and_transcribe as dt
    import ingest
    from picorte.risk_shield import source_resolver
    from picorte.risk_shield.policy_gate import PolicyViolationError

    def nao_baixa(*a, **k):
        raise AssertionError("baixou antes do portão P1")

    def portao(db, *, source_input, meta, owner=None, registry_path=None):
        raise PolicyViolationError("[P1:pre_ingest] Fonte desconhecida", code="source_unknown")

    monkeypatch.setattr(dt, "resolve_source", nao_baixa)
    monkeypatch.setattr(ingest, "probe_source", lambda url: {"channel": "canal estranho"})
    monkeypatch.setattr(source_resolver, "gate_project_source", portao)
    monkeypatch.setattr(sys, "argv", ["download_and_transcribe.py", "https://www.youtube.com/watch?v=x",
                                      "--workdir", str(tmp_path)])
    with pytest.raises(PolicyViolationError):
        dt.main()


# ------------------------------------------------------------------ W55 (decisão a): Camada 3 sem colisão com jogo

def _plano(texto, t0=2.0):
    from picorte.risk_shield.green_seal_15s import plan_green_seal_audio_and_captions

    words = [{"word": w, "start": t0 + i * 0.4, "end": t0 + i * 0.4 + 0.3} for i, w in enumerate(texto.split())]
    return plan_green_seal_audio_and_captions(words, clip_start=0.0, clip_end=60.0)


@pytest.mark.parametrize("texto", ["that was rape", "a pedophile", "pedophilia", "child porn", "estupro"])
def test_termos_graves_sem_colisao_com_jogo_bloqueiam(texto):
    assert _plano(texto)["status"] == "hard_block"


@pytest.mark.parametrize("texto", ["jogando Suicide Squad hoje", "matei o nazi", "o nazismo do jogo",
                                   "ele vai se matar", "kill myself"])
def test_nome_de_jogo_e_termo_sensivel_vao_para_revisao_humana_nao_abortam(texto):
    assert _plano(texto)["status"] == "human_review"
