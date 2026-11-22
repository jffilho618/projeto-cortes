from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades, listar_capacidades
from picorte.services import gestao as G
from picorte.services.fila import FilaEstudio
from picorte.services.vitrine import CacheVitrine
from test_publicacao_servico import _projeto

H = {"X-Picorte-Token": "t", "Origin": "http://testserver"}


def _cliente(tmp_path, monkeypatch):
    from picorte.db.connection import Database
    import picorte.api.rotas_publicacao as rp
    db = Database(f"sqlite:///{tmp_path / 'api.db'}")
    db.init_schema()
    abertas = []
    monkeypatch.setattr(rp, "_db", lambda: db)
    monkeypatch.setattr(rp, "CADENCIA", tmp_path / "cad.json")
    monkeypatch.setattr(rp, "SAIDA", tmp_path / "prontos")
    monkeypatch.setattr(rp, "BENCHMARKS", tmp_path / "benchmarks")
    monkeypatch.setattr(rp, "_abrir", abertas.append)
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d", fila=FilaEstudio(raiz, executar=lambda *a: 0),
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()), vitrine=CacheVitrine(tmp_path / "v.json"))
    return TestClient(app), db, raiz, abertas


def test_pacote_exportar_link_e_nao_vou_postar(tmp_path, monkeypatch):
    c, db, raiz, abertas = _cliente(tmp_path, monkeypatch)
    fonte = G.cadastrar_fonte(db, {"nome": "A", "plataforma": "youtube", "handle": "@a", "status": "liberada",
                                   "base": "explicita", "evidencia": "e", "motivo": "m"})["id"]
    _projeto(raiz, "aaaaaaaaaaaa", [("001", "ouro", "pass"), ("002", "forte", None)], fonte=fonte)
    pacote = c.get("/api/publicacao/pacote").json()
    assert [p["seg"] for p in pacote["prontos"]] == ["001"] and pacote["fora"][0]["seg"] == "002"

    r = c.post("/api/publicacao/exportar", json={"itens": [{"projeto": "aaaaaaaaaaaa", "stem": "001-abc-corte-001"}]}, headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["exportados"] == 1
    assert c.get("/api/publicacao/pacote").json()["prontos"] == []
    links = c.get("/api/publicacao/links").json()["links"]
    assert len(links) == 4 and all(l["status"] == "exportado" for l in links)

    tiktok = next(l for l in links if l["rede"] == "tiktok")
    assert c.post(f"/api/publicacao/links/{tiktok['id']}", json={"url": "https://youtu.be/x"}, headers=H).status_code == 400
    assert c.post(f"/api/publicacao/links/{tiktok['id']}", json={"url": "https://www.tiktok.com/@a/video/1"}, headers=H).status_code == 200
    fb = next(l for l in links if l["rede"] == "facebook_reels")
    assert c.post(f"/api/publicacao/links/{fb['id']}/nao-vou-postar", json={"motivo": "não uso"}, headers=H).status_code == 200
    assert c.post(f"/api/publicacao/links/{fb['id']}/desfazer", json={}, headers=H).status_code == 200
    assert c.post("/api/publicacao/links/nada", json={"url": "https://x"}, headers=H).status_code == 404

    pasta = r.json()["pastas"][0]
    assert c.post("/api/publicacao/abrir", json={"pasta": pasta}, headers=H).status_code == 200 and abertas
    assert c.post("/api/publicacao/abrir", json={"pasta": str(tmp_path)}, headers=H).status_code == 400

    cont = c.get("/api/aprendizado/contadores").json()
    assert cont["publicacoes_com_link"] == 1 and cont["meta"] == 20


def test_capacidades_da_6_8(tmp_path):
    caps = {c["id"]: c for c in listar_capacidades(tmp_path, cache_falso())["capacidades"]}
    assert caps["PUB-3"]["ligou_em"] == "2026-11-22" and "/api/publicacao/links" in caps["PUB-3"]["fonte_dado"]
