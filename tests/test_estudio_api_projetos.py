import json

from fastapi.testclient import TestClient

import projects
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from estudio_fakes import cache_falso

PID = "abcdef123456"


def _app(tmp_path, status="running"):
    raiz = tmp_path / "projects"
    path = raiz / PID
    (path / "clips").mkdir(parents=True)
    projects.atomic_json(path / "project.json", {
        "id": PID, "source": "x.mp4", "options": {}, "status": status, "stage": "render",
        "created": 1.0, "updated": 1.0, "cache": {}, "renders": {}, "error": None})
    (path / "clips" / "01.mp4").write_bytes(bytes(range(256)) * 4)
    video = tmp_path / "fonte.mp4"
    video.write_bytes(b"0123456789")
    (path / "transcript.json").write_text(json.dumps({"video": str(video), "duration": 10}),
                                          encoding="utf-8")
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()))
    return TestClient(app), path


def test_listar_e_abrir_nunca_escrevem_project_json(tmp_path):
    c, path = _app(tmp_path)
    antes = (path / "project.json").read_bytes()
    lista = c.get("/api/projetos").json()["projetos"]
    detalhe = c.get(f"/api/projetos/{PID}").json()
    assert (path / "project.json").read_bytes() == antes
    assert lista[0]["status"] == "interrupted"
    assert detalhe["project"]["status"] == "interrupted"
    assert detalhe["busy"] is False
    assert detalhe["files"][0]["url"] == f"/media/{PID}/clips/01.mp4"


def test_id_invalido_e_400(tmp_path):
    c, _ = _app(tmp_path)
    assert c.get("/api/projetos/..%2F..").status_code in (400, 404)
    assert c.get("/api/projetos/XYZ").status_code == 400


def test_midia_inteira_e_parcial(tmp_path):
    c, _ = _app(tmp_path)
    r = c.get(f"/media/{PID}/clips/01.mp4")
    assert r.status_code == 200 and len(r.content) == 1024
    r = c.get(f"/media/{PID}/clips/01.mp4", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206
    assert r.headers["content-range"] == "bytes 10-19/1024"
    assert r.content == bytes(range(10, 20))


def test_midia_recusa_extensao_e_pasta_fora_da_lista(tmp_path):
    c, path = _app(tmp_path)
    (path / "clips" / "x.py").write_text("print(1)", encoding="utf-8")
    assert c.get(f"/media/{PID}/clips/x.py").status_code == 400
    assert c.get(f"/media/{PID}/work/01.mp4").status_code == 400


def test_video_fonte(tmp_path):
    c, _ = _app(tmp_path)
    assert c.get(f"/media/{PID}/source").content == b"0123456789"


def test_dashboard_antigo_usa_o_mesmo_detalhe():
    import dashboard
    from picorte.services.projeto_detalhe import detalhe_projeto
    assert dashboard.project_detail is detalhe_projeto
