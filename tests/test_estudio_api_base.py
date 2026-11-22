from fastapi.testclient import TestClient

from picorte.api import create_app

TOKEN = "tok-teste"


def _cliente(tmp_path, dist=None):
    app = create_app(tmp_path / "projects", hosts=("testserver",), token=TOKEN,
                     dist=dist or tmp_path / "dist")
    return TestClient(app)


def test_host_estranho_e_recusado(tmp_path):
    r = _cliente(tmp_path).get("/", headers={"host": "evil.com"})
    assert r.status_code == 403
    assert "erro" in r.json()


def test_cabecalhos_de_seguranca_em_toda_resposta(tmp_path):
    r = _cliente(tmp_path).get("/")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_post_sem_token_e_recusado(tmp_path):
    assert _cliente(tmp_path).post("/api/projetos", json={}).status_code == 403


def test_post_com_origem_estranha_e_recusado(tmp_path):
    r = _cliente(tmp_path).post("/api/projetos", json={},
                                headers={"X-Picorte-Token": TOKEN, "Origin": "http://evil.com"})
    assert r.status_code == 403


def test_post_com_token_passa_do_portao(tmp_path):
    r = _cliente(tmp_path).post("/api/qualquer", json={},
                                headers={"X-Picorte-Token": TOKEN, "Origin": "http://testserver"})
    assert r.status_code != 403


def test_sem_build_mostra_aviso_em_portugues(tmp_path):
    r = _cliente(tmp_path).get("/lives")
    assert r.status_code == 200
    assert "npm run build" in r.text


def test_spa_serve_index_e_arquivos_do_build(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    c = _cliente(tmp_path, dist)
    assert 'id="root"' in c.get("/revisao/abcdef123456").text
    assert c.get("/assets/app.js").text == "console.log(1)"


def test_spa_nao_sai_da_pasta_do_build(tmp_path):
    (tmp_path / "segredo.txt").write_text("SEGREDO", encoding="utf-8")
    r = _cliente(tmp_path).get("/..%2Fsegredo.txt")
    assert "SEGREDO" not in r.text


def test_api_desconhecida_responde_404_em_json(tmp_path):
    r = _cliente(tmp_path).get("/api/nao-existe")
    assert r.status_code == 404
    assert r.json() == {"erro": "Não encontrado."}


def test_token_e_gerado_quando_nao_informado(tmp_path):
    app = create_app(tmp_path / "projects", hosts=("testserver",))
    assert len(app.state.token) >= 32
    assert app.state.raiz == (tmp_path / "projects").resolve()


def test_por_padrao_aceita_127_e_localhost_e_recusa_o_resto(tmp_path):
    # o YouTube só toca o player embutido de vídeo com anúncio em "localhost", não em "127.0.0.1"
    from fastapi.testclient import TestClient
    from picorte.api import create_app
    c = TestClient(create_app(tmp_path / "p", porta=8770, token="t", dist=tmp_path / "d"))
    assert c.get("/api/taxonomia", headers={"host": "localhost:8770"}).status_code == 200
    assert c.get("/api/taxonomia", headers={"host": "127.0.0.1:8770"}).status_code == 200
    assert c.get("/api/taxonomia", headers={"host": "localhost:9999"}).status_code == 403
    assert c.get("/api/taxonomia", headers={"host": "evil.com"}).status_code == 403
