import json
from datetime import datetime, timezone

import pytest

from picorte.db.connection import Database
from picorte.services import gestao as G
from picorte.services import publicacao as P

AGORA = datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def db(tmp_path):
    banco = Database(f"sqlite:///{tmp_path / 'p.db'}")
    banco.init_schema()
    return banco


def _fonte(db, status="liberada"):
    return G.cadastrar_fonte(db, {"nome": "ALANZOKA", "plataforma": "youtube", "handle": "@alanzoka", "status": status,
                                  "base": "tolerancia_publica", "evidencia": "https://x", "motivo": "teste"})["id"]


def _projeto(raiz, pid, cortes, *, fonte=None, aspecto="9:16"):
    pasta = raiz / pid
    (pasta / "clips").mkdir(parents=True)
    estado = {"id": pid, "status": "review", "options": {"aspect": aspecto}, "source_meta": {"title": f"VOD {pid}"}}
    if fonte:
        estado["source_gate"] = {"source_id": fonte, "allowed": True}
    (pasta / "project.json").write_text(json.dumps(estado), encoding="utf-8")
    segs = []
    for seg, tier, risco in cortes:
        segs.append({"id": seg, "tier": tier, "proposed_title": f"Corte {seg}"})
        stem = f"{seg}-abc-corte-{seg}"
        (pasta / "clips" / f"{stem}.mp4").write_bytes(b"x")
        meta = {"proposed_title": f"Corte {seg}", "tier": tier, "publish_kit": {"brand_name": "Bomba Clips", "game": "GTA 6", "streamer": {"slug": "alanzoka", "display_name": "ALANZOKA"}, "platforms": {
            r: {"title": f"T{seg}", "description": "d", "hashtags": ["#a"], "pinned_comment": "c", "upload_url": "u"}
            for r in ("youtube_shorts", "tiktok", "instagram_reels", "facebook_reels")}}}
        if risco:
            meta["risk_verdict"] = {"overall_status": risco}
        (pasta / "clips" / f"{stem}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (pasta / "segments.json").write_text(json.dumps(segs), encoding="utf-8")
    return [{"id": pid, "status": "review"}]


def test_validar_link_por_rede():
    assert P.validar_link("youtube_shorts", " https://youtube.com/shorts/abc ") == "https://youtube.com/shorts/abc"
    assert P.validar_link("youtube_long", "https://youtu.be/abc")
    assert P.validar_link("tiktok", "https://www.tiktok.com/@x/video/1")
    assert P.validar_link("instagram_reels", "https://www.instagram.com/reel/abc/")
    assert P.validar_link("facebook_reels", "https://fb.watch/abc")
    for rede, url in [("tiktok", "https://youtube.com/shorts/a"), ("youtube_shorts", "http://youtube.com/x"),
                      ("instagram_reels", "instagram.com/reel/a"), ("nada", "https://x.com")]:
        with pytest.raises(ValueError):
            P.validar_link(rede, url)


def test_pacote_ordena_por_tier_e_explica_quem_fica_de_fora(db, tmp_path):
    raiz = tmp_path / "projects"
    fonte = _fonte(db)
    projs = _projeto(raiz, "aaaaaaaaaaaa", [("001", "forte", "pass"), ("002", "ouro", "auto_fixed"),
                                             ("003", "ouro", None), ("004", "forte", "blocked")], fonte=fonte)
    projs += _projeto(raiz, "bbbbbbbbbbbb", [("001", "ouro", "pass")])  # anterior ao portão (W5)
    pacote = P.montar_pacote(db, raiz, projs, decisoes={"aaaaaaaaaaaa": {}}, agora=AGORA,
                             cadencia=tmp_path / "cad.json")
    assert [(c["projeto"], c["seg"]) for c in pacote["prontos"]] == [("aaaaaaaaaaaa", "002"), ("aaaaaaaaaaaa", "001")]
    assert pacote["prontos"][0]["quando"]["tiktok"] == "agora"
    motivos = {(f["projeto"], f["seg"]): f for f in pacote["fora"]}
    assert "Sem veredito" in motivos[("aaaaaaaaaaaa", "003")]["motivo"]
    assert "Escudo" in motivos[("aaaaaaaaaaaa", "004")]["motivo"]
    assert motivos[("bbbbbbbbbbbb", "001")]["acao"] == "preparar"
    assert motivos[("bbbbbbbbbbbb", "001")]["projeto_titulo"] == "VOD bbbbbbbbbbbb"


def test_pacote_tira_descartado_fonte_pausada_e_ja_exportado(db, tmp_path):
    raiz = tmp_path / "projects"
    fonte = _fonte(db)
    projs = _projeto(raiz, "aaaaaaaaaaaa", [("001", "ouro", "pass"), ("002", "ouro", "pass")], fonte=fonte)
    P.marcar_exportados(db, "aaaaaaaaaaaa", ["001-abc-corte-001"], raiz)
    pacote = P.montar_pacote(db, raiz, projs, decisoes={"aaaaaaaaaaaa": {"002": {"descartado": True}}}, agora=AGORA,
                             cadencia=tmp_path / "cad.json")
    assert pacote["prontos"] == [] and pacote["fora"] == []
    G.mudar_permissao(db, fonte, {"status": "lista_negra", "motivo": "pediu"})
    projs2 = _projeto(raiz, "cccccccccccc", [("001", "ouro", "pass")], fonte=fonte)
    fora = P.montar_pacote(db, raiz, projs2, decisoes={}, agora=AGORA, cadencia=tmp_path / "cad.json")["fora"]
    assert "Fonte" in fora[0]["motivo"]


def test_cooldown_aparece_no_quando_sai(db, tmp_path):
    raiz = tmp_path / "projects"
    projs = _projeto(raiz, "aaaaaaaaaaaa", [("001", "ouro", "pass")], fonte=_fonte(db))
    G.criar_cooldown("tiktok", 24, "teste", state_path=tmp_path / "cad.json")
    pacote = P.montar_pacote(db, raiz, projs, decisoes={}, cadencia=tmp_path / "cad.json")
    assert pacote["prontos"][0]["quando"]["tiktok"] != "agora"
    assert pacote["cadencia"]["tiktok"]["status"] == "block"


def test_exportado_vira_pendencia_e_so_sai_com_link_ou_nao_vou_postar(db, tmp_path):
    raiz = tmp_path / "projects"
    _projeto(raiz, "aaaaaaaaaaaa", [("001", "ouro", "pass")], fonte=_fonte(db), aspecto="16:9")
    ids = P.marcar_exportados(db, "aaaaaaaaaaaa", ["001-abc-corte-001"], raiz)
    assert len(ids) == 5  # 4 redes curtas + YouTube Longo (corte horizontal, B11)
    assert P.contar_pendentes(db) == 5
    links = P.listar_links(db, raiz)
    assert {l["rede"] for l in links} >= {"youtube_long", "tiktok"} and links[0]["kit"]["title"] == "T001"
    tiktok = next(l for l in links if l["rede"] == "tiktok")
    with pytest.raises(ValueError):
        P.registrar_link(db, tiktok["id"], "https://youtube.com/shorts/a")
    P.registrar_link(db, tiktok["id"], "https://www.tiktok.com/@x/video/1")
    ig = next(l for l in links if l["rede"] == "instagram_reels")
    with pytest.raises(ValueError, match="motivo"):
        P.nao_vou_postar(db, ig["id"], "")
    P.nao_vou_postar(db, ig["id"], "rede fora do nicho")
    assert P.contar_pendentes(db) == 3
    P.desfazer(db, ig["id"])
    assert P.contar_pendentes(db) == 4
    pub = db.fetch_one("SELECT * FROM publications WHERE id = ?", (tiktok["id"],))
    assert pub["status"] == "publicado" and pub["published_at"]
    assert P.marcar_exportados(db, "aaaaaaaaaaaa", ["001-abc-corte-001"], raiz) == []  # não duplica


def test_contadores_do_aprendizado(db, tmp_path):
    raiz = tmp_path / "projects"
    _projeto(raiz, "aaaaaaaaaaaa", [("001", "ouro", "pass")], fonte=_fonte(db))
    ids = P.marcar_exportados(db, "aaaaaaaaaaaa", ["001-abc-corte-001"], raiz)
    pub = next(i for i in ids if db.fetch_one("SELECT platform FROM publications WHERE id = ?", (i,))["platform"] == "tiktok")
    P.registrar_link(db, pub, "https://www.tiktok.com/@x/video/1")
    from picorte.services.decisoes import gravar_rotulo
    gravar_rotulo(db, "aaaaaaaaaaaa", "001", 1)
    c = P.contadores_aprendizado(db, {"gabaritos": 4, "meta": 20})
    assert c == {"rotulos": {"bons": 1, "ruins": 0}, "publicacoes_com_link": 1, "gabaritos": 4, "meta": 20}


def test_claim_segura_publicacao_exportada(db, tmp_path):
    raiz = tmp_path / "projects"
    fonte = _fonte(db)
    _projeto(raiz, "aaaaaaaaaaaa", [("001", "ouro", "pass")], fonte=fonte)
    db.execute("INSERT INTO videos (id, source_id, source_url, status, created_at, updated_at) "
               "VALUES ('studio-aaaaaaaaaaaa', ?, 'u', 'complete', 't', 't')", (fonte,))
    P.marcar_exportados(db, "aaaaaaaaaaaa", ["001-abc-corte-001"], raiz)
    assert G.previa_claim(db, fonte)["publicacoes_pendentes"] == 4
    G.registrar_claim(db, {"fonte": fonte, "rede": "tiktok", "tipo": "strike", "motivo": "strike"})
    assert P.contar_pendentes(db) == 0
