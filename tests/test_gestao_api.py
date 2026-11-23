import json

from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades, listar_capacidades
from picorte.services.fila import FilaEstudio
from picorte.services.vitrine import CacheVitrine

H = {"X-Picorte-Token": "t", "Origin": "http://testserver"}


def _cliente(tmp_path, monkeypatch):
    from picorte.db.connection import Database
    import picorte.api.rotas_gestao as rg
    db = Database(f"sqlite:///{tmp_path / 'api.db'}")
    db.init_schema()
    monkeypatch.setattr(rg, "_db", lambda: db)
    monkeypatch.setattr(rg, "CADENCIA", tmp_path / "cad.json")
    monkeypatch.setattr(rg, "BENCHMARKS", tmp_path / "benchmarks")
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d", fila=FilaEstudio(raiz, executar=lambda *a: 0),
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()), vitrine=CacheVitrine(tmp_path / "v.json"))
    return TestClient(app), db, raiz


def test_fontes_cadastro_permissao_e_pausas(tmp_path, monkeypatch):
    c, _, _ = _cliente(tmp_path, monkeypatch)
    r = c.post("/api/fontes", json={"nome": "Gaules", "plataforma": "twitch", "handle": "@gaules", "status": "liberada",
                                    "base": "explicita", "evidencia": "https://x", "motivo": "acordo"}, headers=H)
    assert r.status_code == 200
    fid = r.json()["id"]
    assert c.post(f"/api/fontes/{fid}/permissao", json={"status": "contrato", "motivo": "x"}, headers=H).status_code == 400
    assert c.post(f"/api/fontes/{fid}/permissao", json={"status": "lista_negra", "motivo": "pediu"}, headers=H).status_code == 200
    fontes = c.get("/api/fontes").json()["fontes"]
    assert fontes[0]["status"] == "lista_negra" and fontes[0]["no_cadastro"] is False
    assert c.get("/api/fontes/pausas").json()["eventos"][0]["para"] == "lista_negra"


def test_barradas_politicas_campanhas_e_dossies(tmp_path, monkeypatch):
    c, _, raiz = _cliente(tmp_path, monkeypatch)
    (raiz / "cccccccccccc").mkdir(parents=True)
    (raiz / "cccccccccccc" / "project.json").write_text(json.dumps({
        "id": "cccccccccccc", "status": "failed", "source": "https://youtu.be/x",
        "error": "[P1:pre_ingest] Fonte desconhecida: 'Fulano' não está entre os streamers cadastrados."}), encoding="utf-8")
    assert c.get("/api/fontes/barradas").json()["barradas"][0]["canal"] == "Fulano"
    assert isinstance(c.get("/api/fontes/politicas").json()["politicas"], list)
    assert "gta6" in [d["slug"] for d in c.get("/api/fontes/dossies").json()["dossies"]]
    assert c.get("/api/fontes/campanhas").json() == {"campanhas": []}


def test_escudo_cooldown_e_claim(tmp_path, monkeypatch):
    c, db, _ = _cliente(tmp_path, monkeypatch)
    fid = c.post("/api/fontes", json={"nome": "X", "plataforma": "youtube", "handle": "@x", "status": "liberada",
                                      "base": "explicita", "evidencia": "e", "motivo": "m"}, headers=H).json()["id"]
    assert c.post("/api/escudo/cooldown", json={"rede": "tiktok", "horas": 24, "motivo": ""}, headers=H).status_code == 400
    assert c.post("/api/escudo/cooldown", json={"rede": "tiktok", "horas": 24, "motivo": "muitos posts"}, headers=H).status_code == 200
    assert "tiktok" in c.get("/api/escudo").json()["cooldowns"]
    assert c.post("/api/escudo/cooldown/limpar", json={"rede": "tiktok", "motivo": "liberou"}, headers=H).status_code == 200
    assert c.get(f"/api/escudo/claim/previa?fonte={fid}").json()["fonte"] == "X"
    r = c.post("/api/escudo/claim", json={"fonte": fid, "rede": "tiktok", "link": "https://t", "tipo": "strike", "motivo": "strike"}, headers=H)
    assert r.status_code == 200 and r.json()["source_status"] == "pausada_por_claim"
    assert c.get("/api/escudo").json()["claims"][0]["tipo"] == "claim"


def test_saude_motor_e_benchmark(tmp_path, monkeypatch):
    c, _, _ = _cliente(tmp_path, monkeypatch)
    assert c.get("/api/saude/motor").json() == {"partes": [], "rotulos": {}, "projetos": []}
    assert c.get("/api/saude/benchmark").json() == {"versoes": [], "gabaritos": 0, "meta": 20}


def test_capacidades_da_6_7(tmp_path):
    caps = {c["id"]: c for c in listar_capacidades(tmp_path, cache_falso())["capacidades"]}
    for i in ["FON-3", "ESC-8"]:
        assert caps[i]["status"] == "ligado" and caps[i]["ligou_em"] == "2026-11-22", i
    assert caps["FON-6"]["status"] == "parcial" and "5.1" in caps["FON-6"]["motivo"]
