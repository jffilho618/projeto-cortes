import json

import numpy as np
from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades, listar_capacidades
from picorte.services.fila import FilaEstudio
from picorte.services.vitrine import CacheVitrine

H = {"X-Picorte-Token": "t", "Origin": "http://testserver"}


def _cliente(tmp_path, monkeypatch):
    raiz = tmp_path / "projects"
    pasta = raiz / "aaaaaaaaaaaa"
    pasta.mkdir(parents=True)
    (pasta / "project.json").write_text(json.dumps({
        "id": "aaaaaaaaaaaa", "source": "https://youtu.be/q4ekFpRjgKQ", "status": "review", "created": 1,
        "options": {"ai_mode": "ollama", "benchmark_blind": True}, "source_meta": {"title": "EMBOSCADOS!"}}), encoding="utf-8")
    (pasta / "segments.json").write_text(json.dumps([
        {"start": 1, "end": 31, "proposed_title": "Primeiro", "tier": "ouro", "archetype": "caos_coop"}]), encoding="utf-8")
    np.savez(pasta / "audio_features.npz", rms=np.linspace(-60, -10, 120).astype(np.float32))
    import picorte.services.decisoes as dec
    monkeypatch.setattr(dec, "BIBLIOTECA_OURO", tmp_path / "golden.json")
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     fila=FilaEstudio(raiz, executar=lambda *a: 0),
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()), vitrine=CacheVitrine(tmp_path / "v.json"))
    return TestClient(app), pasta


def test_fila_separa_producao_e_prova(tmp_path, monkeypatch):
    c, _ = _cliente(tmp_path, monkeypatch)
    f = c.get("/api/fila").json()
    assert f["producao"] == [] and f["prova"][0]["titulo"] == "EMBOSCADOS!"
    assert f["prova"][0]["estagio"] == "Pronto para revisar"


def test_revisao_e_energia(tmp_path, monkeypatch):
    c, _ = _cliente(tmp_path, monkeypatch)
    r = c.get("/api/projetos/aaaaaaaaaaaa/revisao").json()
    assert r["projeto"]["energia"] is True and r["cortes"][0]["titulo"] == "Primeiro"
    e = c.get("/api/projetos/aaaaaaaaaaaa/energia", params={"de": 0, "ate": 60}).json()
    assert e["duracao_s"] == 120 and len(e["valores"]) == 60


def test_energia_indisponivel_e_404_legivel(tmp_path, monkeypatch):
    c, pasta = _cliente(tmp_path, monkeypatch)
    (pasta / "audio_features.npz").unlink()
    r = c.get("/api/projetos/aaaaaaaaaaaa/energia")
    assert r.status_code == 404 and "Forma de onda indisponível" in r.json()["erro"]


def test_rotulo_descarte_e_exemplo_ouro_pela_api(tmp_path, monkeypatch):
    c, _ = _cliente(tmp_path, monkeypatch)
    base = "/api/projetos/aaaaaaaaaaaa/cortes/001"
    assert c.post(base + "/rotulo", json={"valor": -1, "motivo": "borda errada"}, headers=H).status_code == 200
    assert c.post(base + "/descarte", json={"descartado": True}, headers=H).status_code == 200
    assert c.post(base + "/exemplo-ouro", headers=H).status_code == 200
    d = c.get("/api/projetos/aaaaaaaaaaaa/revisao").json()["cortes"][0]["decisao"]
    assert d == {"rotulo": -1, "motivo": "borda errada", "descartado": True, "exemplo_ouro": True}
    assert json.loads((tmp_path / "golden.json").read_text(encoding="utf-8"))["examples"][0]["id"] == "aaaaaaaaaaaa-001"


def test_escritas_exigem_token_e_validam(tmp_path, monkeypatch):
    c, _ = _cliente(tmp_path, monkeypatch)
    base = "/api/projetos/aaaaaaaaaaaa/cortes/001"
    assert c.post(base + "/rotulo", json={"valor": 1}).status_code == 403
    assert c.post(base + "/rotulo", json={"valor": 9}, headers=H).status_code == 400
    assert c.post("/api/projetos/aaaaaaaaaaaa/cortes/099/exemplo-ouro", headers=H).status_code == 400


def test_capacidades_da_6_6(tmp_path):
    caps = {c["id"]: c for c in listar_capacidades(tmp_path, cache_falso())["capacidades"]}
    for i in ["REV-8", "REV-9", "FIL-3", "FIL-5", "FIL-6"]:
        assert caps[i]["status"] == "ligado" and caps[i]["ligou_em"] == "2026-11-22", i
    assert caps["FIL-7"]["status"] == "parcial"
