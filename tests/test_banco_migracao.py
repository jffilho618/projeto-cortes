import sqlite3

from picorte.db.connection import Database

DDL_ANTIGO = """
CREATE TABLE sources (id TEXT PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL, channel_handle TEXT NOT NULL,
  permission_status TEXT NOT NULL DEFAULT 'desconhecida', permission_evidence_url TEXT DEFAULT '',
  credit_template TEXT DEFAULT 'Créditos: @{handle}', default_game_slug TEXT DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE videos (id TEXT PRIMARY KEY, source_id TEXT REFERENCES sources(id), origin_type TEXT NOT NULL DEFAULT 'vod',
  source_url TEXT NOT NULL, game_slug TEXT NOT NULL DEFAULT '', duration_seconds REAL NOT NULL DEFAULT 0.0,
  workdir_path TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE clips (id TEXT PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id), parent_long_clip_id TEXT REFERENCES clips(id),
  format_type TEXT NOT NULL DEFAULT 'short_9_16', ab_variant INTEGER NOT NULL DEFAULT 1, start_sec REAL NOT NULL, end_sec REAL NOT NULL,
  score_chat REAL NOT NULL DEFAULT 0.0, score_audio REAL NOT NULL DEFAULT 0.0, score_visual REAL NOT NULL DEFAULT 0.0,
  score_text REAL NOT NULL DEFAULT 0.0, score_overall REAL NOT NULL DEFAULT 0.0, ypp_transform_score INTEGER NOT NULL DEFAULT 0,
  phash_signature TEXT NOT NULL DEFAULT '', llm_mode_used TEXT NOT NULL DEFAULT 'heuristic', risk_status TEXT NOT NULL DEFAULT 'pending',
  mp4_path TEXT NOT NULL DEFAULT '', thumbnail_path TEXT NOT NULL DEFAULT '', proposed_title TEXT NOT NULL DEFAULT '',
  context_banner_2s TEXT NOT NULL DEFAULT '', pinned_comment_debate TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE publications (id TEXT PRIMARY KEY, clip_id TEXT NOT NULL REFERENCES clips(id), social_account_id TEXT,
  platform TEXT NOT NULL, publish_mode TEXT NOT NULL DEFAULT 'assisted_manual', status TEXT NOT NULL DEFAULT 'fila',
  external_post_id TEXT NOT NULL DEFAULT '', external_url TEXT NOT NULL DEFAULT '', related_video_external_id TEXT NOT NULL DEFAULT '',
  scheduled_for TEXT, published_at TEXT, created_at TEXT NOT NULL);
INSERT INTO videos VALUES ('v1', NULL, 'vod', 'u', '', 0, '', 'complete', 't', 't');
INSERT INTO clips (id, video_id, start_sec, end_sec, score_text, score_overall, created_at) VALUES ('c1', 'v1', 0, 10, 9.5, 9.5, 't');
INSERT INTO publications (id, clip_id, platform, status, external_url, created_at) VALUES ('p1', 'c1', 'tiktok', 'publicado', 'https://x', 't');
"""


def _banco_antigo(tmp_path):
    arq = tmp_path / "antigo.db"
    con = sqlite3.connect(arq)
    con.executescript(DDL_ANTIGO)
    con.close()
    return Database(f"sqlite:///{arq}")


def _info(db, tabela):
    with db.connect() as c:
        return {r["name"]: r for r in c.execute(f"PRAGMA table_info({tabela})").fetchall()}


def test_banco_novo_ja_nasce_com_sinais_anulaveis(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'novo.db'}")
    db.init_schema()
    info = _info(db, "clips")
    for col in ("score_chat", "score_audio", "score_visual", "score_text", "ypp_transform_score"):
        assert info[col]["notnull"] == 0, col
    assert "archived_at" in info and "archived_at" in _info(db, "videos")


def test_banco_antigo_migra_anula_zeros_falsos_e_preserva_publicacao(tmp_path):
    db = _banco_antigo(tmp_path)
    db.init_schema()
    corte = db.fetch_one("SELECT * FROM clips WHERE id = 'c1'")
    assert corte["score_chat"] is None and corte["score_audio"] is None and corte["score_visual"] is None
    assert corte["score_text"] is None  # era a nota geral copiada, não um sinal medido
    assert corte["ypp_transform_score"] is None  # sem veredito
    assert corte["score_overall"] == 9.5
    pub = db.fetch_one("SELECT * FROM publications WHERE id = 'p1'")
    assert pub["clip_id"] == "c1" and pub["external_url"] == "https://x"
    with db.connect() as c:
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migracao_e_idempotente(tmp_path):
    db = _banco_antigo(tmp_path)
    db.init_schema()
    db.execute("UPDATE clips SET score_audio = 7.5 WHERE id = 'c1'")
    db.init_schema()
    assert db.fetch_one("SELECT score_audio FROM clips WHERE id = 'c1'")["score_audio"] == 7.5


def test_create_clip_sem_sinal_grava_null(tmp_path):
    from picorte.db.repositories import PicorteRepositories
    db = Database(f"sqlite:///{tmp_path / 'r.db'}")
    db.init_schema()
    repos = PicorteRepositories(db)
    vid = repos.videos.create_video(source_url="u")
    clip = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=10.0)
    assert clip["score_chat"] is None and clip["score_text"] is None


def test_list_clips_esconde_arquivados(tmp_path):
    from picorte.db.repositories import PicorteRepositories
    db = Database(f"sqlite:///{tmp_path / 'r.db'}")
    db.init_schema()
    repos = PicorteRepositories(db)
    vid = repos.videos.create_video(source_url="u")
    a = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=10.0)
    b = repos.clips.create_clip(video_id=vid["id"], start_sec=10.0, end_sec=20.0)
    db.execute("UPDATE clips SET archived_at = 't' WHERE id = ?", (b["id"],))
    assert [c["id"] for c in repos.clips.list_clips()] == [a["id"]]
    assert {c["id"] for c in repos.clips.list_clips(incluir_arquivados=True)} == {a["id"], b["id"]}
