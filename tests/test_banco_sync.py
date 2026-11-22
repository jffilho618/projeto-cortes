import json

import pytest

from picorte.db.connection import Database
from picorte.services.studio_service import StudioService


@pytest.fixture
def servico(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 's.db'}")
    db.init_schema()
    return StudioService(db)


def _fonte(servico):
    return servico.create_source(name="DAVY JONES", platform="youtube", channel_handle="@davyjones",
                                 permission_status="liberada")


def _estado(pid="abc123def456", **extra):
    return {"id": pid, "source": "https://www.youtube.com/watch?v=x", "status": "complete",
            "options": {"aspect": "9:16", "ai_mode": "ollama"},
            "source_meta": {"detected_game": "gta6"}, **extra}


def test_b1_grava_a_fonte_do_portao(servico):
    fonte = _fonte(servico)
    r = servico.sync_studio_project(_estado(source_gate={"source_id": fonte["id"]}), segments=[])
    assert r["video"]["source_id"] == fonte["id"]
    assert r["video"]["game_slug"] == "gta6" and r["video"]["origin_type"] == "vod"


def test_b1_fonte_que_nao_existe_no_banco_fica_nula_sem_quebrar(servico):
    r = servico.sync_studio_project(_estado(source_gate={"source_id": "nao-existe"}), segments=[])
    assert r["video"]["source_id"] is None


def test_b2_sinais_medidos_ou_null(servico):
    segs = [
        {"start": 0, "end": 30, "overall": 8.0,
         "evidence": {"audio": 7.0, "chat": 2.5, "chat_measured": True, "visual": None}, "score_parts": {"text_score": 6.0}},
        {"start": 40, "end": 70, "overall": 10.0, "evidence": {}, "score_parts": {"llm_scout": 1}},
    ]
    r = servico.sync_studio_project(_estado(), segments=segs, outputs=[])
    medido, scout = r["clips"]
    assert (medido["score_chat"], medido["score_audio"], medido["score_visual"], medido["score_text"]) == (2.5, 7.0, None, 6.0)
    assert (scout["score_chat"], scout["score_audio"], scout["score_visual"], scout["score_text"]) == (None, None, None, None)
    assert scout["score_overall"] == 10.0


def test_b3_veredito_do_meta_vai_para_o_banco_e_mp4_casa_pelo_prefixo(servico, tmp_path):
    clips = tmp_path / "clips"
    clips.mkdir()
    mp4_2 = clips / "002-bbbb-segundo.mp4"
    (clips / "002-bbbb-segundo.meta.json").write_text(json.dumps({
        "thumbnail_1280x720": "t2.png",
        "risk_verdict": {"overall_status": "pass", "ypp_score": 84, "phash_signature": "ab"}}), encoding="utf-8")
    segs = [{"start": 0, "end": 30, "overall": 8.0}, {"start": 40, "end": 70, "overall": 9.0}]
    r = servico.sync_studio_project(_estado(), segments=segs, outputs=[str(mp4_2)])  # só o 2º foi renderizado
    primeiro, segundo = r["clips"]
    assert primeiro["mp4_path"] == "" and primeiro["risk_status"] == "pending" and primeiro["ypp_transform_score"] is None
    assert segundo["mp4_path"] == str(mp4_2) and segundo["thumbnail_path"] == "t2.png"
    assert (segundo["risk_status"], segundo["ypp_transform_score"], segundo["phash_signature"]) == ("pass", 84, "ab")


def test_ressincronizar_sem_meta_nao_apaga_veredito_gravado(servico):
    segs = [{"start": 0, "end": 30, "overall": 8.0}]
    servico.sync_studio_project(_estado(), segments=segs)
    servico.db.execute("UPDATE clips SET risk_status = 'hard_block', ypp_transform_score = 40 WHERE id = ?",
                       ("studio-abc123def456:001",))
    r = servico.sync_studio_project(_estado(), segments=segs)
    assert r["clips"][0]["risk_status"] == "hard_block" and r["clips"][0]["ypp_transform_score"] == 40


def test_sync_reativa_projeto_arquivado(servico):
    servico.sync_studio_project(_estado(), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    servico.db.execute("UPDATE videos SET archived_at = 't'")
    servico.db.execute("UPDATE clips SET archived_at = 't'")
    r = servico.sync_studio_project(_estado(), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    assert r["video"]["archived_at"] is None and r["clips"][0]["archived_at"] is None


def test_status_fila_conta_so_ativos(servico):
    servico.sync_studio_project(_estado("aaaaaaaaaaaa"), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    servico.sync_studio_project(_estado("bbbbbbbbbbbb"), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    servico.db.execute("UPDATE videos SET archived_at = 't' WHERE id = 'studio-bbbbbbbbbbbb'")
    servico.db.execute("UPDATE clips SET archived_at = 't' WHERE video_id = 'studio-bbbbbbbbbbbb'")
    st = servico.status_fila()
    assert (st["total_videos"], st["total_clips"]) == (1, 1)
    assert st["arquivados"] == {"videos": 1, "clips": 1}


def test_publicacao_manual_liga_ao_corte_do_sync(servico):
    servico.sync_studio_project(_estado(), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    pub = servico.record_manual_publication(project_id="abc123def456", clip_stem="001-2abd1b6f-titulo",
                                            platform="tiktok", external_url="https://tiktok.com/@x/video/1")
    assert pub["clip_id"] == "studio-abc123def456:001"
    assert servico.db.fetch_one("SELECT COUNT(*) AS n FROM clips")["n"] == 1


def test_b1_casa_pela_handle_quando_o_id_veio_de_outro_banco(servico):
    fonte = _fonte(servico)
    gate = {"source_id": "uuid-de-outro-banco", "channel_handle": "@DavyJones"}
    r = servico.sync_studio_project(_estado(source_gate=gate), segments=[])
    assert r["video"]["source_id"] == fonte["id"]
