from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.services.fila import FilaEstudio
from picorte.services.vitrine import CacheVitrine, normalizar_entrada

ENTRADA = {"id": "q4ekFpRjgKQ", "title": "EMBOSCADOS!", "duration": 8087, "timestamp": 1795276800}


def _cliente(tmp_path, **deps):
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     fila=FilaEstudio(raiz, executar=lambda *a: 0),
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()),
                     vitrine=CacheVitrine(tmp_path / "v.json"), **deps)
    return TestClient(app), raiz


def test_vitrine_lista_os_streamers_do_registro_na_hora(tmp_path):
    c, _ = _cliente(tmp_path)
    dados = c.get("/api/vitrine").json()
    slugs = [s["slug"] for s in dados["streamers"]]
    assert "alanzoka" in slugs and all(s["youtube"].startswith("https://www.youtube.com/") for s in dados["streamers"])


def test_prateleira_traz_videos_reais_e_o_projeto_ligado(tmp_path):
    c, raiz = _cliente(tmp_path, listar=lambda url, limite: [normalizar_entrada(ENTRADA)])
    import projects
    projects.create_project(raiz, "https://www.youtube.com/watch?v=q4ekFpRjgKQ", {})
    dados = c.get("/api/vitrine/alanzoka").json()
    assert dados["videos"][0]["titulo"] == "EMBOSCADOS!" and dados["verificado_em"]
    assert dados["videos"][0]["projeto"]["status"] == "new"


def test_prateleira_de_slug_desconhecido_e_404(tmp_path):
    c, _ = _cliente(tmp_path)
    assert c.get("/api/vitrine/nao-existe").status_code == 404


def test_prateleira_sem_rede_e_sem_cache_responde_503_legivel(tmp_path):
    def falha(url, limite):
        raise RuntimeError("rede")

    c, _ = _cliente(tmp_path, listar=falha)
    r = c.get("/api/vitrine/alanzoka")
    assert r.status_code == 503 and "Não consegui listar" in r.json()["erro"]


def test_mesa(tmp_path):
    c, _ = _cliente(tmp_path)
    m = c.get("/api/mesa").json()
    assert m["revisar"] == 0 and m["links_pendentes"] is None


def test_sala_com_link_ruim_e_400(tmp_path):
    c, _ = _cliente(tmp_path)
    r = c.get("/api/sala", params={"url": "oi"})
    assert r.status_code == 400 and "não parece um link" in r.json()["erro"]


def test_sala_usa_a_regua_injetada(tmp_path):
    c, _ = _cliente(tmp_path, sondar=lambda u: {"title": "T", "channel": "C"},
                    portao=lambda db, **kw: {"allowed": True, "source_name": "C", "permission_basis": "explicita"})
    r = c.get("/api/sala", params={"url": "https://youtu.be/q4ekFpRjgKQ"}).json()
    assert r["portao"]["liberado"] is True and r["video"]["titulo"] == "T"


def test_csp_aceita_thumbs_e_players_oficiais(tmp_path):
    c, _ = _cliente(tmp_path)
    csp = c.get("/api/mesa").headers["content-security-policy"]
    assert "https://i.ytimg.com" in csp and "frame-src https://www.youtube-nocookie.com https://player.twitch.tv" in csp


def test_lote_aceita_renderizar_sozinho_e_recusa_acao_estranha(tmp_path):
    chamadas = []
    raiz = tmp_path / "projects"
    fila = FilaEstudio(raiz, executar=lambda p, a, pr, pk: chamadas.append(a) or 0)
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d", fila=fila,
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()), vitrine=CacheVitrine(tmp_path / "v.json"))
    c = TestClient(app)
    h = {"X-Picorte-Token": "t", "Origin": "http://testserver"}
    r = c.post("/api/lote", json={"sources": ["https://youtu.be/q4ekFpRjgKQ"], "acao": "all"}, headers=h)
    fila._futuros[r.json()["projetos"][0]["id"]].result(timeout=5)
    assert chamadas == ["all"]
    r = c.post("/api/lote", json={"sources": ["https://youtu.be/q4ekFpRjgKQ"], "acao": "render"}, headers=h)
    assert r.status_code == 400 and "acao" in r.json()["erro"]


def test_rev7_traz_o_custo_medido_dos_frames(tmp_path):
    from picorte.capacidades import listar_capacidades
    rev7 = next(c for c in listar_capacidades(tmp_path, cache_falso())["capacidades"] if c["id"] == "REV-7")
    assert "US$ 0,26" in rev7["motivo"] and "20/11" in rev7["motivo"]


def test_prateleira_de_canal_sem_videos_e_404_com_orientacao(tmp_path):
    from picorte.services.vitrine import CanalSemVideos

    def sem(url, limite):
        raise CanalSemVideos("O YouTube não mostra vídeos em https://www.youtube.com/@x. Confira o canal no cadastro de streamers.")

    c, _ = _cliente(tmp_path, listar=sem)
    r = c.get("/api/vitrine/alanzoka")
    assert r.status_code == 404 and "Confira o canal" in r.json()["erro"]
