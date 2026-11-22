from fastapi.testclient import TestClient

from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.capacidades.sondas import ResultadoSonda
from estudio_fakes import _fixa, cache_falso

CAMPOS = {"id", "area", "titulo", "status", "tipo_motivo", "motivo", "falta", "fonte_dado",
          "origem", "escopo", "depende_de", "verificado_em", "ligou_em", "dados"}


def _tem_numero(valor) -> bool:
    if isinstance(valor, bool):
        return False
    if isinstance(valor, (int, float)):
        return True
    if isinstance(valor, dict):
        return any(_tem_numero(v) for v in valor.values())
    if isinstance(valor, list):
        return any(_tem_numero(v) for v in valor)
    return False


def _capacidades(tmp_path, cache):
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     capacidades=ServicoCapacidades(raiz, cache=cache))
    return TestClient(app).get("/api/capacidades").json()["capacidades"]


def test_toda_capacidade_segue_o_contrato(tmp_path):
    for cap in _capacidades(tmp_path, cache_falso()):
        assert set(cap) == CAMPOS, cap["id"]
        assert cap["status"] in {"ligado", "parcial", "travado"}
        assert cap["escopo"] in {"global", "projeto", "corte"}
        assert cap["verificado_em"], cap["id"]
        if cap["status"] != "ligado":
            assert cap["tipo_motivo"] in {"codigo", "config", "dado", "temporario", "escolha"}
            assert cap["motivo"], cap["id"]


def test_capacidade_travada_nunca_traz_numero_mesmo_com_sonda_cheia(tmp_path):
    cache = cache_falso(
        ollama=lambda: ResultadoSonda(False, "fora", {"host": "h", "modelos": [], "latencia_ms": 3}),
        claude=_fixa(False, caminho=None, tentativas=2),
        **{"yt-dlp": _fixa(False, tentativas=5)})
    for cap in _capacidades(tmp_path, cache):
        if cap["status"] == "travado":
            assert cap["dados"] is None, cap["id"]
            assert not _tem_numero(cap["dados"]), cap["id"]


def test_depende_de_aponta_para_ids_existentes(tmp_path):
    caps = _capacidades(tmp_path, cache_falso())
    ids = {c["id"] for c in caps}
    for cap in caps:
        assert set(cap["depende_de"]) <= ids, cap["id"]
