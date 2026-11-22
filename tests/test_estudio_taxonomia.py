from fastapi.testclient import TestClient

from picorte.api import create_app
from picorte.engine.multitrack import CANONICAL_ARCHETYPES, CANONICAL_TIERS
from picorte.services.taxonomia import taxonomia


def test_listas_vem_das_constantes_canonicas():
    t = taxonomia()
    assert [a["id"] for a in t["arquetipos"]] == list(CANONICAL_ARCHETYPES)
    assert [x["id"] for x in t["tiers"]] == list(CANONICAL_TIERS)
    assert {m["id"] for m in t["modos_ia"]} == {"heuristic", "ollama", "claude", "gemini", "dupla"}
    assert {"16:9", "9:16"} <= {a["id"] for a in t["aspectos"]}
    assert all(item["rotulo"] for chave in t for item in t[chave])


def test_redes_dizem_o_proprio_status():
    redes = {r["id"]: r["status"] for r in taxonomia()["redes"]}
    assert redes["youtube_shorts"] == "ligado"
    assert redes["youtube_longo"] == "travado"


def test_endpoint(tmp_path):
    app = create_app(tmp_path / "p", hosts=("testserver",), token="t", dist=tmp_path / "d")
    r = TestClient(app).get("/api/taxonomia")
    assert r.status_code == 200 and r.json()["tiers"][0]["id"] == "ouro"
