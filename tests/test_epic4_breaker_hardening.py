"""P7 (code review Épico 4) — Disjuntor de fonte atômico, com motivo, pausa de emergência e vídeos na fila."""
from __future__ import annotations

from pathlib import Path

import pytest

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _setup(tmp_path: Path):
    db = Database(f"sqlite:///{(tmp_path / 'p7.db').as_posix()}")
    db.init_schema()
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(name="S", platform="youtube", channel_handle="@s", permission_status="liberada")
    vid = repos.videos.create_video(source_id=src["id"], source_url="https://yt/1", game_slug="")
    clip = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=30.0)
    pub = repos.publications.create_publication(clip_id=clip["id"], platform="tiktok", status="fila")
    return db, repos, src, vid, pub


def test_breaker_is_atomic_when_a_step_fails(tmp_path: Path):
    from picorte.risk_shield.source_breaker import pause_source_globally

    db, repos, src, _vid, pub = _setup(tmp_path)
    db.execute("DROP TABLE claims_events")
    with pytest.raises(Exception):
        pause_source_globally(db, source_id=src["id"])
    assert repos.sources.get_source(src["id"])["permission_status"] == "liberada"
    assert db.fetch_one("SELECT status FROM publications WHERE id = ?", (pub["id"],))["status"] == "fila"


def test_breaker_records_reason(tmp_path: Path):
    from picorte.risk_shield.source_breaker import pause_source_globally

    db, _repos, src, _vid, _pub = _setup(tmp_path)
    res = pause_source_globally(db, source_id=src["id"], reason="Streamer pediu remoção por DM")
    ev = db.fetch_one("SELECT details FROM claims_events WHERE id = ?", (res["claim_event_id"],))
    assert "Streamer pediu remoção por DM" in ev["details"]
    assert res["reason"] == "Streamer pediu remoção por DM"


def test_manual_emergency_pause_uses_its_own_status_and_still_blocks(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError, assert_can_ingest
    from picorte.risk_shield.source_breaker import pause_source_globally

    db, repos, src, _vid, pub = _setup(tmp_path)
    res = pause_source_globally(db, source_id=src["id"], claim_type="manual_emergency")
    assert res["source_status"] == "pausada_emergencia"
    assert repos.sources.get_source(src["id"])["permission_status"] == "pausada_emergencia"
    assert db.fetch_one("SELECT status FROM publications WHERE id = ?", (pub["id"],))["status"] == "pausado_emergencia"
    with pytest.raises(PolicyViolationError):
        assert_can_ingest(db, source_id=src["id"])


def test_breaker_blocks_queued_videos_of_the_source(tmp_path: Path):
    from picorte.risk_shield.source_breaker import pause_source_globally

    db, _repos, src, vid, _pub = _setup(tmp_path)
    res = pause_source_globally(db, source_id=src["id"])
    assert db.fetch_one("SELECT status FROM videos WHERE id = ?", (vid["id"],))["status"] == "bloqueado_p1"
    assert res["blocked_videos"] == 1
