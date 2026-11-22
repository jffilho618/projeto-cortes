from fastapi.testclient import TestClient

import projects
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.services.fila import FilaEstudio
from estudio_fakes import cache_falso

H = {"X-Picorte-Token": "t", "Origin": "http://testserver"}


def _cliente(tmp_path, executar=lambda *a: 0):
    raiz = tmp_path / "projects"
    fila = FilaEstudio(raiz, executar=executar)
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d", fila=fila,
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()))
    return TestClient(app), raiz, fila


def test_config_entrega_o_token(tmp_path):
    c, _, _ = _cliente(tmp_path)
    dados = c.get("/api/config").json()
    assert dados["token"] == "t" and "defaults" in dados and "caption_presets" in dados


def test_criar_projeto_e_enfileirar(tmp_path):
    chamadas = []
    c, raiz, fila = _cliente(tmp_path, executar=lambda p, a, pr, pk: chamadas.append(a) or 0)
    r = c.post("/api/projetos", json={"source": "https://www.youtube.com/watch?v=abc"}, headers=H)
    assert r.status_code == 201
    pid = r.json()["id"]
    r = c.post(f"/api/projetos/{pid}/run", json={"action": "prepare"}, headers=H)
    assert r.status_code == 200 and r.json() == {"ok": True}
    fila._futuros[pid].result(timeout=5)
    assert chamadas == ["prepare"]


def test_projeto_ocupado_responde_409(tmp_path):
    import threading
    solta = threading.Event()
    c, raiz, fila = _cliente(tmp_path, executar=lambda *a: solta.wait(5) and 0)
    pid = c.post("/api/projetos", json={"source": "https://youtu.be/x"}, headers=H).json()["id"]
    c.post(f"/api/projetos/{pid}/run", json={"action": "prepare"}, headers=H)
    r = c.post(f"/api/projetos/{pid}/settings", json={"min_len": 20}, headers=H)
    assert r.status_code == 409
    solta.set()
    fila._futuros[pid].result(timeout=5)


def test_lote_valida_tamanho(tmp_path):
    c, _, _ = _cliente(tmp_path)
    assert c.post("/api/lote", json={"sources": []}, headers=H).status_code == 400
    r = c.post("/api/lote", json={"sources": ["https://youtu.be/a", "https://youtu.be/b"]}, headers=H)
    assert r.status_code == 201 and len(r.json()["projetos"]) == 2


def test_settings_grava_opcao_validada(tmp_path):
    c, raiz, _ = _cliente(tmp_path)
    pid = c.post("/api/projetos", json={"source": "https://youtu.be/x"}, headers=H).json()["id"]
    assert c.post(f"/api/projetos/{pid}/settings", json={"min_len": 20}, headers=H).status_code == 200
    assert projects.read_project(raiz / pid)["options"]["min_len"] == 20
    assert c.post(f"/api/projetos/{pid}/settings", json={"inventada": 1}, headers=H).status_code == 400


def test_acao_desconhecida_e_404(tmp_path):
    c, _, _ = _cliente(tmp_path)
    pid = c.post("/api/projetos", json={"source": "https://youtu.be/x"}, headers=H).json()["id"]
    assert c.post(f"/api/projetos/{pid}/apagar-tudo", json={}, headers=H).status_code == 404


def test_mark_posted_valida_rede(tmp_path):
    c, _, _ = _cliente(tmp_path)
    pid = c.post("/api/projetos", json={"source": "https://youtu.be/x"}, headers=H).json()["id"]
    r = c.post(f"/api/projetos/{pid}/mark-posted", json={"clip_stem": "01", "platform": "orkut"},
               headers=H)
    assert r.status_code == 400
