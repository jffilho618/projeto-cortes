import json

import pytest

from picorte.db.connection import Database
from picorte.services.studio_service import StudioService


@pytest.fixture
def servico(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'r.db'}")
    db.init_schema()
    return StudioService(db)


def _projeto(raiz, pid, *, status="complete", segmentos=None, gate=None):
    pasta = raiz / pid
    pasta.mkdir(parents=True)
    (pasta / "project.json").write_text(json.dumps({
        "id": pid, "source": "https://www.youtube.com/watch?v=x", "status": status, "options": {"aspect": "9:16"},
        "source_gate": gate, "last_outputs": []}), encoding="utf-8")
    (pasta / "segments.json").write_text(json.dumps(segmentos or []), encoding="utf-8")
    (pasta / "transcript.json").write_text(json.dumps({"duration": 3600.0, "words": []}), encoding="utf-8")
    return pasta


def _foto(pasta):
    return {p.name: p.stat().st_mtime_ns for p in pasta.iterdir()}


def test_sincronizar_pasta_le_tudo_e_nao_escreve_na_pasta(servico, tmp_path):
    from picorte.services.reconciliacao import sincronizar_pasta
    pasta = _projeto(tmp_path / "projects", "aaaaaaaaaaaa", segmentos=[{"start": 0, "end": 30, "overall": 7.0}])
    antes = _foto(pasta)
    r = sincronizar_pasta(servico, pasta)
    assert r["video"]["duration_seconds"] == 3600.0 and len(r["clips"]) == 1
    assert _foto(pasta) == antes


def test_attach_risk_verdict_repassa_o_clip_id(monkeypatch, tmp_path):
    from picorte.risk_shield import pipeline
    visto = {}
    monkeypatch.setattr(pipeline, "audit_clip_risk", lambda db, **kw: visto.update(kw) or {
        "overall_status": "pass", "gates": {}, "per_platform": {}})
    monkeypatch.setattr(pipeline, "sample_clip_frames", lambda mp4: [])
    pipeline.attach_risk_verdict(None, meta_path=tmp_path / "x.meta.json", source_id=None, seg={},
                                 words=[], mp4_path=None, options={}, clip_id="studio-p:001")
    assert visto["clip_id"] == "studio-p:001"


def test_reconciliar_arquiva_orfaos_sem_perder_publicados(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    raiz = tmp_path / "projects"
    _projeto(raiz, "aaaaaaaaaaaa", segmentos=[{"start": 0, "end": 30, "overall": 7.0}])
    db = servico.db
    db.execute("INSERT INTO videos (id, source_url, workdir_path, status, created_at, updated_at) "
               "VALUES ('studio-zzzzzzzzzzzz', 'u', '/home/bomba/projects/zzzzzzzzzzzz', 'complete', 't', 't')")
    db.execute("INSERT INTO clips (id, video_id, start_sec, end_sec, created_at) "
               "VALUES ('studio-zzzzzzzzzzzz:001', 'studio-zzzzzzzzzzzz', 0, 10, 't')")
    db.execute("INSERT INTO publications (id, clip_id, platform, status, external_url, created_at) "
               "VALUES ('p1', 'studio-zzzzzzzzzzzz:001', 'tiktok', 'publicado', 'https://x', 't')")
    r = reconciliar(db, raiz)
    assert r["ressincronizados"] == 1 and r["arquivados"] == 1 and r["falhas"] == []
    assert db.fetch_one("SELECT archived_at FROM videos WHERE id = 'studio-zzzzzzzzzzzz'")["archived_at"]
    assert db.fetch_one("SELECT archived_at FROM clips WHERE id = 'studio-zzzzzzzzzzzz:001'")["archived_at"]
    assert db.fetch_one("SELECT clip_id FROM publications WHERE id = 'p1'")["clip_id"] == "studio-zzzzzzzzzzzz:001"
    assert db.fetch_one("SELECT archived_at FROM videos WHERE id = 'studio-aaaaaaaaaaaa'")["archived_at"] is None


def test_reconciliar_reativa_quando_a_pasta_volta(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    raiz = tmp_path / "projects"
    servico.db.execute("INSERT INTO videos (id, source_url, workdir_path, status, archived_at, created_at, updated_at) "
                       "VALUES ('studio-bbbbbbbbbbbb', 'u', '', 'complete', 't', 't', 't')")
    _projeto(raiz, "bbbbbbbbbbbb")
    r = reconciliar(servico.db, raiz)
    assert servico.db.fetch_one("SELECT archived_at FROM videos WHERE id = 'studio-bbbbbbbbbbbb'")["archived_at"] is None
    assert r["arquivados"] == 0


def test_caminho_vazio_nao_conta_como_presente(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    servico.db.execute("INSERT INTO videos (id, source_url, workdir_path, status, created_at, updated_at) "
                       "VALUES ('mcp-antigo', 'u', '', 'queued', 't', 't')")
    assert reconciliar(servico.db, tmp_path / "projects")["arquivados"] == 1


def test_reconciliar_registra_falha_sem_parar(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    raiz = tmp_path / "projects"
    (raiz / "quebrado00000").mkdir(parents=True)
    (raiz / "quebrado00000" / "project.json").write_text("{", encoding="utf-8")
    _projeto(raiz, "cccccccccccc")
    r = reconciliar(servico.db, raiz)
    assert r["ressincronizados"] == 1 and r["falhas"] and "quebrado00000" in r["falhas"][0]


def test_preparar_banco_sincroniza_politicas_e_reconcilia(tmp_path):
    from picorte.services.reconciliacao import preparar_banco
    db = Database(f"sqlite:///{tmp_path / 'b.db'}")
    r = preparar_banco(db, tmp_path / "projects")
    assert r["politicas"] >= 1
    assert db.fetch_one("SELECT COUNT(*) AS n FROM publisher_policies")["n"] == r["politicas"]


def test_reconciliar_religa_publicacao_antiga_ao_corte_do_sync(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    raiz = tmp_path / "projects"
    _projeto(raiz, "dddddddddddd", segmentos=[{"start": 0, "end": 30, "overall": 7.0}] * 3)
    db = servico.db
    reconciliar(db, raiz)
    antigo = "studio-dddddddddddd:003-954f0e5a-titulo-do-arquivo"
    db.execute("INSERT INTO clips (id, video_id, start_sec, end_sec, llm_mode_used, risk_status, created_at) "
               "VALUES (?, 'studio-dddddddddddd', 0, 0, 'manual', 'approved', 't')", (antigo,))
    db.execute("INSERT INTO publications (id, clip_id, platform, status, external_url, created_at) "
               "VALUES ('p9', ?, 'youtube_shorts', 'publicado', 'https://yt/9', 't')", (antigo,))
    r = reconciliar(db, raiz)
    assert r["publicacoes_religadas"] == 1
    assert db.fetch_one("SELECT clip_id FROM publications WHERE id = 'p9'")["clip_id"] == "studio-dddddddddddd:003"
    assert db.fetch_one("SELECT archived_at FROM clips WHERE id = ?", (antigo,))["archived_at"]
    assert reconciliar(db, raiz)["publicacoes_religadas"] == 0
