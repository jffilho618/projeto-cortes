import pytest

from picorte.db.connection import Database
from picorte.services import gestao as G


@pytest.fixture
def db(tmp_path):
    banco = Database(f"sqlite:///{tmp_path / 'g.db'}")
    banco.init_schema()
    return banco


REGISTRO = [{"slug": "alanzoka", "display_name": "ALANZOKA", "handle": "@alanzoka"}]


def _fonte(db, **extra):
    dados = {"nome": "ALANZOKA", "plataforma": "youtube", "handle": "@alanzoka", "status": "liberada",
             "base": "tolerancia_publica", "evidencia": "https://x/regras", "motivo": "cadastro inicial", **extra}
    return G.cadastrar_fonte(db, dados)


def test_cadastro_exige_base_evidencia_e_motivo_para_liberar(db):
    with pytest.raises(ValueError, match="base"):
        _fonte(db, base="")
    with pytest.raises(ValueError, match="evidência"):
        _fonte(db, evidencia="")
    with pytest.raises(ValueError, match="motivo"):
        _fonte(db, motivo="")
    desconhecida = G.cadastrar_fonte(db, {"nome": "X", "plataforma": "twitch", "handle": "@x", "status": "desconhecida",
                                          "motivo": "vi no radar"})
    assert desconhecida["status"] == "desconhecida"


def test_listar_fontes_com_registro_e_elo_de_videos(db):
    f = _fonte(db)
    db.execute("INSERT INTO videos (id, source_id, source_url, status, created_at, updated_at) VALUES ('v1', ?, 'u', 'complete', 't', 't')", (f["id"],))
    db.execute("INSERT INTO clips (id, video_id, start_sec, end_sec, created_at) VALUES ('c1', 'v1', 0, 10, 't')")
    lista = G.listar_fontes(db, REGISTRO)
    assert lista[0]["nome"] == "ALANZOKA" and lista[0]["no_cadastro"] is True
    assert (lista[0]["videos"], lista[0]["cortes"]) == (1, 1)


def test_mudar_permissao_c1_e_historico(db):
    f = _fonte(db)
    with pytest.raises(ValueError, match="evidência"):
        G.mudar_permissao(db, f["id"], {"status": "contrato", "base": "explicita", "evidencia": "", "motivo": "fechamos"})
    G.mudar_permissao(db, f["id"], {"status": "contrato", "base": "explicita", "evidencia": "contrato.pdf", "motivo": "fechamos"})
    G.mudar_permissao(db, f["id"], {"status": "lista_negra", "motivo": "pediu para não cortar"})
    eventos = G.eventos_de_pausa(db)
    assert [(e["de"], e["para"]) for e in eventos if e["tipo"] == "permissao"] == [("contrato", "lista_negra"), ("liberada", "contrato")]
    with pytest.raises(ValueError, match="Status"):
        G.mudar_permissao(db, f["id"], {"status": "qualquer", "motivo": "x"})


def test_barradas_vem_dos_erros_p1_dos_projetos():
    projetos = [
        {"id": "p1", "status": "failed", "source": "https://youtu.be/abc", "updated": 1795276800,
         "error": "[P1:pre_ingest] Fonte desconhecida: 'BisteconeLive' não está entre os streamers cadastrados. Nada foi baixado."},
        {"id": "p2", "status": "failed", "error": "TimeoutError"},
        {"id": "p3", "status": "review"},
    ]
    b = G.fontes_barradas(projetos)
    assert len(b) == 1 and b[0]["canal"] == "BisteconeLive" and b[0]["projeto"] == "p1"
    assert b[0]["quando"] == "2026-11-21T16:00:00+00:00"


def test_campanha_vencida_aparece_como_vencida(db):
    f = _fonte(db)
    G.criar_campanha(db, {"fonte": f["id"], "jogo": "gta6", "cpm_brl": 4.5, "tags": ["#gta6"],
                          "inicio": "2026-11-01T00:00:00+00:00", "expira": "2026-11-10T00:00:00+00:00"})
    G.criar_campanha(db, {"fonte": f["id"], "jogo": "gta6", "cpm_brl": 3, "tags": [], "inicio": "2026-11-20T00:00:00+00:00"})
    camp = G.listar_campanhas(db, agora="2026-11-22T00:00:00+00:00")
    assert sorted(c["vencida"] for c in camp) == [False, True]
    with pytest.raises(ValueError):
        G.criar_campanha(db, {"fonte": f["id"], "cpm_brl": -1})


def test_previa_e_registro_de_claim_pausam_a_fonte(db):
    f = _fonte(db)
    db.execute("INSERT INTO videos (id, source_id, source_url, status, created_at, updated_at) VALUES ('v1', ?, 'u', 'complete', 't', 't')", (f["id"],))
    db.execute("INSERT INTO clips (id, video_id, start_sec, end_sec, created_at) VALUES ('c1', 'v1', 0, 10, 't')")
    db.execute("INSERT INTO publications (id, clip_id, platform, status, created_at) VALUES ('p1', 'c1', 'tiktok', 'fila', 't')")
    previa = G.previa_claim(db, f["id"])
    assert previa == {"fonte": "ALANZOKA", "videos": 1, "cortes": 1, "publicacoes_pendentes": 1}
    with pytest.raises(ValueError, match="motivo"):
        G.registrar_claim(db, {"fonte": f["id"], "rede": "tiktok", "link": "https://t", "tipo": "copyright_claim", "motivo": ""})
    r = G.registrar_claim(db, {"fonte": f["id"], "rede": "tiktok", "link": "https://t", "tipo": "copyright_claim", "motivo": "claim da Rockstar"})
    assert r["source_status"] == "pausada_por_claim" and r["paused_publications"] == 1
    eventos = G.eventos_de_pausa(db)
    assert eventos[0]["tipo"] == "claim" and "tiktok" in eventos[0]["motivo"]


def test_escudo_mostra_cooldowns_com_motivo_e_restante(tmp_path):
    estado = tmp_path / "cad.json"
    G.criar_cooldown("tiktok", 24, "muitos posts seguidos", state_path=estado)
    e = G.estado_escudo(state_path=estado)
    assert e["tiktok"]["motivo"] == "muitos posts seguidos" and e["tiktok"]["pode_limpar"] is True
    assert 23 < e["tiktok"]["restante_h"] <= 24
    with pytest.raises(ValueError, match="motivo"):
        G.limpar_cooldown("tiktok", "", state_path=estado)
    G.limpar_cooldown("tiktok", "a rede liberou", state_path=estado)
    assert G.estado_escudo(state_path=estado) == {}
