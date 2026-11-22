from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades, listar_capacidades
from picorte.mcp.server import PicorteMCPServer


def _cliente(tmp_path, cache):
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "dist",
                     capacidades=ServicoCapacidades(raiz, cache=cache))
    return TestClient(app)


def test_endpoint_devolve_o_contrato(tmp_path):
    r = _cliente(tmp_path, cache_falso()).get("/api/capacidades")
    assert r.status_code == 200
    dados = r.json()
    assert len(dados["capacidades"]) == 82
    assert dados["capacidades"][0]["id"] == "SIS-1"


def test_paridade_painel_e_mcp(tmp_path):
    cache = cache_falso()
    raiz = tmp_path / "projects"
    api = _cliente(tmp_path, cache).get("/api/capacidades").json()
    mcp = PicorteMCPServer(service=object(),
                           capacidades=lambda: listar_capacidades(raiz, cache))
    assert any(t["name"] == "picorte_capacidades" for t in mcp.list_tools())
    via_mcp = mcp.call_tool("picorte_capacidades", {})
    assert via_mcp["capacidades"] == api["capacidades"]
    assert via_mcp["resumo"] == api["resumo"]
