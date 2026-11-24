"""Cancelar job e apagar projeto pela UI (decisões do dono, 2026-11-23)."""
from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

import projects
from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.services.fila import FilaEstudio
from picorte.services.vitrine import CacheVitrine

H = {"X-Picorte-Token": "t", "Origin": "http://testserver"}
PID = "abcdef123456"


def _projeto(raiz, pid=PID, status="review"):
    path = raiz / pid
    (path / "clips").mkdir(parents=True)
    projects.atomic_json(path / "project.json", {
        "id": pid, "source": "x.mp4", "options": {}, "status": status, "stage": "waiting",
        "created": 1.0, "updated": 1.0, "cache": {}, "renders": {}, "error": None})
    return path


def test_cancelar_job_so_na_fila_tira_da_fila_e_marca_cancelado(tmp_path):
    _projeto(tmp_path, "aaaaaaaaaaaa")
    path_b = _projeto(tmp_path, "bbbbbbbbbbbb")
    solta = threading.Event()
    fila = FilaEstudio(tmp_path, executar=lambda *a: solta.wait(5) and 0)
    fila.enfileirar("aaaaaaaaaaaa", "all")  # ocupa o único worker
    fila.enfileirar("bbbbbbbbbbbb", "all")  # fica esperando
    assert fila.cancelar("bbbbbbbbbbbb") == "fila"
    assert projects.read_project(path_b)["status"] == "cancelled" and not fila.na_fila("bbbbbbbbbbbb")
    solta.set()
    fila.fechar()


def test_cancelar_job_rodando_pede_ao_motor_e_cancelled_nao_vira_failed(tmp_path):
    path = _projeto(tmp_path)
    comecou, solta = threading.Event(), threading.Event()

    def executar(p, *_a):
        comecou.set()
        solta.wait(5)
        estado = projects.read_project(p)  # o motor viu o cancelar.flag e parou
        estado.update(status="cancelled", error="Cancelado pelo operador.")
        projects.save_project(p, estado)
        return 1  # o processo filho sai com erro

    fila = FilaEstudio(tmp_path, executar=executar)
    fila.enfileirar(PID, "all")
    comecou.wait(5)
    assert fila.cancelar(PID) == "pedido"
    assert (path / projects.CANCEL_FLAG).exists()
    solta.set()
    fila._futuros[PID].result(timeout=5)
    assert projects.read_project(path)["status"] == "cancelled"
    fila.fechar()


def test_cancelar_job_parado_e_recusado(tmp_path):
    _projeto(tmp_path)
    fila = FilaEstudio(tmp_path, executar=lambda *a: 0)
    with pytest.raises(ValueError, match="não está rodando"):
        fila.cancelar(PID)
    fila.fechar()


def _cliente(tmp_path, monkeypatch, fila=None):
    import picorte.api.rotas_projetos as rp
    arquivados = []
    monkeypatch.setattr(rp, "_arquivar_no_banco", arquivados.append)
    raiz = tmp_path / "projects"
    raiz.mkdir(exist_ok=True)
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     fila=fila or FilaEstudio(raiz, executar=lambda *a: 0),
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()), vitrine=CacheVitrine(tmp_path / "v.json"))
    return TestClient(app), raiz, arquivados


def test_apagar_mostra_o_tamanho_pede_o_id_e_arquiva(tmp_path, monkeypatch):
    c, raiz, arquivados = _cliente(tmp_path, monkeypatch)
    path = _projeto(raiz)
    (path / "clips" / "001-a.mp4").write_bytes(b"x" * 1000)
    (path / "clips" / "002-b.mp4").write_bytes(b"x" * 1000)
    (path / "audio.webm").write_bytes(b"x" * 3000)
    previa = c.get(f"/api/projetos/{PID}/apagar").json()
    assert previa["cortes"] == 2 and previa["bytes"] >= 5000 and "gb" in previa
    assert c.post(f"/api/projetos/{PID}/apagar", json={}, headers=H).status_code == 400  # sem confirmar o id
    assert c.post(f"/api/projetos/{PID}/apagar", json={"confirmar": "outro"}, headers=H).status_code == 400
    r = c.post(f"/api/projetos/{PID}/apagar", json={"confirmar": PID}, headers=H)
    assert r.status_code == 200 and not path.exists() and arquivados == [PID]


def test_apagar_com_job_ativo_e_recusado(tmp_path, monkeypatch):
    solta = threading.Event()
    raiz = tmp_path / "projects"
    fila = FilaEstudio(raiz, executar=lambda *a: solta.wait(5) and 0)
    c, raiz, _ = _cliente(tmp_path, monkeypatch, fila)
    path = _projeto(raiz)
    fila.enfileirar(PID, "all")
    assert c.post(f"/api/projetos/{PID}/apagar", json={"confirmar": PID}, headers=H).status_code == 409
    assert path.exists()
    assert c.post(f"/api/projetos/{PID}/cancelar", json={}, headers=H).json()["cancelamento"] in {"fila", "pedido"}
    solta.set()
    fila.fechar()


def test_arquivar_projeto_no_banco(tmp_path):
    from picorte.db.connection import Database
    from picorte.services.reconciliacao import arquivar_projeto

    db = Database(f"sqlite:///{tmp_path / 'a.db'}")
    db.init_schema()
    db.execute("INSERT INTO videos (id, source_url, status, created_at, updated_at) VALUES ('studio-abc', 'u', 'complete', 't', 't')")
    db.execute("INSERT INTO clips (id, video_id, start_sec, end_sec, created_at) VALUES ('studio-abc:001', 'studio-abc', 0, 1, 't')")
    assert arquivar_projeto(db, "abc") is True
    assert db.fetch_one("SELECT archived_at FROM videos WHERE id = 'studio-abc'")["archived_at"]
    assert db.fetch_one("SELECT archived_at FROM clips WHERE id = 'studio-abc:001'")["archived_at"]
    assert arquivar_projeto(db, "nao-existe") is False


def test_fila_mostra_cancelado_com_retomar_e_as_redes():
    from picorte.services.revisao import linha_da_fila

    linha = linha_da_fila({"id": "x", "status": "cancelled", "error": "Cancelado pelo operador.", "acao_pedida": "all",
                           "options": {"redes": ["youtube_shorts", "tiktok"]}})
    assert linha["estagio"] == "Cancelado"
    assert linha["falha"] == {"motivo": "Cancelado pelo operador.", "acao": "retomar"} and linha["acao"] == "all"
    assert linha["redes"] == ["youtube_shorts", "tiktok"]
    assert linha_da_fila({"id": "y", "status": "review", "options": {}})["redes"] is None  # projeto antigo


def test_revisao_traz_as_redes_do_projeto(tmp_path):
    from picorte.services.revisao import montar_revisao

    rev = montar_revisao(tmp_path, {"id": "p", "options": {"redes": ["youtube_shorts", "youtube_longo"]}}, {})
    assert rev["projeto"]["redes"] == ["youtube_shorts", "youtube_longo"]
