import numpy as np
import pytest

from picorte.services.energia import energia


def _npz(pasta, rms):
    pasta.mkdir(parents=True, exist_ok=True)
    np.savez(pasta / "audio_features.npz", rms=np.asarray(rms, dtype=np.float32), duration=np.float64(len(rms)))
    return pasta


def test_energia_normalizada_pelo_arquivo_inteiro(tmp_path):
    pasta = _npz(tmp_path / "p", np.linspace(-60, -10, 100))
    r = energia(pasta)
    assert r["duracao_s"] == 100 and r["de"] == 0 and r["ate"] == 100 and len(r["valores"]) == 100
    assert 0.0 <= min(r["valores"]) and max(r["valores"]) <= 1.0
    assert r["valores"][0] < r["valores"][-1]


def test_janela_usa_a_mesma_escala_do_vod(tmp_path):
    pasta = _npz(tmp_path / "p", np.linspace(-60, -10, 100))
    tudo = energia(pasta)["valores"]
    janela = energia(pasta, de=40, ate=60)
    assert janela["de"] == 40 and janela["ate"] == 60 and len(janela["valores"]) == 20
    assert janela["valores"][0] == pytest.approx(tudo[40])


def test_reamostra_para_o_numero_de_pontos(tmp_path):
    pasta = _npz(tmp_path / "p", np.random.default_rng(1).normal(-30, 5, 5000))
    r = energia(pasta, pontos=640)
    assert len(r["valores"]) == 640


def test_limites_fora_do_arquivo_sao_cortados(tmp_path):
    pasta = _npz(tmp_path / "p", np.linspace(-60, -10, 100))
    r = energia(pasta, de=-10, ate=500)
    assert (r["de"], r["ate"]) == (0, 100)


def test_sem_energia_registrada_avisa(tmp_path):
    (tmp_path / "p").mkdir()
    with pytest.raises(FileNotFoundError, match="(?i)forma de onda indisponível"):
        energia(tmp_path / "p")
