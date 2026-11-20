"""D1 (code review Épico 4) — Portão Pre-Ingest real: identifica a fonte pelo CANAL antes de baixar 1 byte."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories

REGISTRY = {
    "streamers": [
        {
            "slug": "alanzoka",
            "display_name": "ALANZOKA",
            "aliases": ["alanzoka", "alan", "cortes do alanzoka"],
            "twitch": "https://www.twitch.tv/alanzoka",
            "youtube": "https://www.youtube.com/@alanzoka",
            "handle": "@alanzoka",
        },
        {
            "slug": "davy-jones",
            "display_name": "DAVY JONES",
            "aliases": ["davy jones", "gameplayrj", "cortes do davy jones"],
            "twitch": "https://www.twitch.tv/davyjones",
            "youtube": "https://www.youtube.com/@Gameplayrj",
            "handle": "@davyjones",
        },
    ]
}


def _make_db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{(tmp_path / 'gate.db').as_posix()}")
    db.init_schema()
    return db


def _registry(tmp_path: Path) -> Path:
    p = tmp_path / "registry.json"
    p.write_text(json.dumps(REGISTRY), encoding="utf-8")
    return p


def test_sources_table_has_permission_basis_column_and_migrates_old_db(tmp_path: Path):
    import sqlite3

    old = tmp_path / "old.db"
    con = sqlite3.connect(old)
    con.execute(
        "CREATE TABLE sources (id TEXT PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL, "
        "channel_handle TEXT NOT NULL, permission_status TEXT NOT NULL DEFAULT 'desconhecida', "
        "permission_evidence_url TEXT DEFAULT '', credit_template TEXT DEFAULT '', "
        "default_game_slug TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    con.commit()
    con.close()
    db = Database(f"sqlite:///{old.as_posix()}")
    db.init_schema()
    assert "permission_basis" in db.list_columns("sources")


def test_seed_registry_marks_streamers_liberada_by_public_tolerance(tmp_path: Path):
    from picorte.risk_shield.source_resolver import seed_registry_sources

    db = _make_db(tmp_path)
    seed_registry_sources(db, registry_path=_registry(tmp_path))
    rows = {r["channel_handle"]: r for r in PicorteRepositories(db).sources.list_sources()}
    assert rows["@alanzoka"]["permission_status"] == "liberada"
    assert rows["@alanzoka"]["permission_basis"] == "tolerancia_publica"
    assert rows["@davyjones"]["permission_status"] == "liberada"


def test_seed_never_overrides_paused_or_blacklisted_source(tmp_path: Path):
    from picorte.risk_shield.source_resolver import seed_registry_sources

    db = _make_db(tmp_path)
    repos = PicorteRepositories(db)
    seed_registry_sources(db, registry_path=_registry(tmp_path))
    alan = next(r for r in repos.sources.list_sources() if r["channel_handle"] == "@alanzoka")
    repos.sources.update_permission(alan["id"], "pausada_por_claim")

    seed_registry_sources(db, registry_path=_registry(tmp_path))
    assert repos.sources.get_source(alan["id"])["permission_status"] == "pausada_por_claim"
    assert len([r for r in repos.sources.list_sources() if r["channel_handle"] == "@alanzoka"]) == 1


def test_url_from_registered_streamer_channel_passes(tmp_path: Path):
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    res = gate_project_source(
        db,
        source_input="https://www.youtube.com/watch?v=abc",
        meta={"url": True, "channel": "Gameplayrj", "title": "Live de GTA"},
        registry_path=_registry(tmp_path),
    )
    assert res["allowed"] is True
    assert res["channel_handle"] == "@davyjones"
    assert res["permission_basis"] == "tolerancia_publica"
    assert res["source_id"]


def test_url_from_unknown_channel_is_blocked_before_download(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    with pytest.raises(PolicyViolationError) as exc:
        gate_project_source(
            db,
            source_input="https://www.youtube.com/watch?v=xyz",
            meta={"url": True, "channel": "Canal Aleatorio", "title": "Alanzoka reage ao trailer"},
            registry_path=_registry(tmp_path),
        )
    assert exc.value.code == "source_unknown"
    assert "Canal Aleatorio" in str(exc.value)


def test_third_party_cortes_channel_never_matches_by_title_or_cortes_alias(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    with pytest.raises(PolicyViolationError):
        gate_project_source(
            db,
            source_input="https://www.youtube.com/watch?v=c1",
            meta={"url": True, "channel": "Cortes do Alanzoka", "title": "ALANZOKA morre no GTA"},
            registry_path=_registry(tmp_path),
        )


def test_url_without_channel_metadata_is_blocked(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    with pytest.raises(PolicyViolationError):
        gate_project_source(
            db,
            source_input="https://www.youtube.com/watch?v=nochan",
            meta={"url": True, "channel": None, "title": "alanzoka"},
            registry_path=_registry(tmp_path),
        )


def test_twitch_url_path_identifies_streamer(tmp_path: Path):
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    res = gate_project_source(
        db,
        source_input="https://www.twitch.tv/alanzoka/clip/abc",
        meta={"url": True, "channel": None, "title": "clip"},
        registry_path=_registry(tmp_path),
    )
    assert res["channel_handle"] == "@alanzoka"


def test_paused_streamer_is_blocked_at_ingest(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError
    from picorte.risk_shield.source_resolver import gate_project_source, seed_registry_sources

    db = _make_db(tmp_path)
    repos = PicorteRepositories(db)
    seed_registry_sources(db, registry_path=_registry(tmp_path))
    alan = next(r for r in repos.sources.list_sources() if r["channel_handle"] == "@alanzoka")
    repos.sources.update_permission(alan["id"], "pausada_por_claim")
    with pytest.raises(PolicyViolationError) as exc:
        gate_project_source(
            db,
            source_input="https://www.youtube.com/watch?v=abc",
            meta={"url": True, "channel": "alanzoka"},
            registry_path=_registry(tmp_path),
        )
    assert exc.value.code == "source_pausada_por_claim"


def test_local_file_without_declared_owner_is_blocked(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    with pytest.raises(PolicyViolationError) as exc:
        gate_project_source(
            db, source_input=str(tmp_path / "v.mp4"), meta={"url": False}, owner=None,
            registry_path=_registry(tmp_path),
        )
    assert exc.value.code == "source_owner_required"


def test_local_file_declared_as_own_gameplay_passes(tmp_path: Path):
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    res = gate_project_source(
        db, source_input=str(tmp_path / "v.mp4"), meta={"url": False}, owner="proprio",
        registry_path=_registry(tmp_path),
    )
    assert res["permission_status"] == "gameplay_proprio"
    assert res["source_id"]


def test_local_file_declared_as_registered_streamer_uses_that_source(tmp_path: Path):
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    res = gate_project_source(
        db, source_input=str(tmp_path / "v.mp4"), meta={"url": False}, owner="alanzoka",
        registry_path=_registry(tmp_path),
    )
    assert res["channel_handle"] == "@alanzoka"
    assert res["permission_status"] == "liberada"


def test_local_file_declared_as_unknown_streamer_is_blocked(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError
    from picorte.risk_shield.source_resolver import gate_project_source

    db = _make_db(tmp_path)
    with pytest.raises(PolicyViolationError):
        gate_project_source(
            db, source_input=str(tmp_path / "v.mp4"), meta={"url": False}, owner="fulano",
            registry_path=_registry(tmp_path),
        )


def test_run_project_blocks_unknown_url_before_any_download(tmp_path: Path, monkeypatch):
    import projects
    import ingest
    import download_and_transcribe as dt

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'proj.db').as_posix()}")
    import picorte.db.connection as conn
    monkeypatch.setattr(conn, "_DEFAULT_DB", None)

    monkeypatch.setattr(ingest, "probe_source", lambda s, runner=None: {
        "source": s, "url": True, "title": "Alanzoka reage", "channel": "Canal Pirata", "duration": 600.0,
    })
    downloads = []
    monkeypatch.setattr(ingest, "download_discovery", lambda *a, **k: downloads.append(a))
    monkeypatch.setattr(dt, "resolve_source", lambda *a, **k: downloads.append(a))

    state = projects.create_project(tmp_path / "projects", "https://www.youtube.com/watch?v=pirata", {})
    path = projects.project_path(tmp_path / "projects", state["id"])
    with pytest.raises(Exception) as exc:
        projects.run_project(path, action="prepare")
    assert "P1" in str(exc.value)
    assert downloads == []
    assert projects.read_project(path)["status"] == "failed"


def test_project_options_accept_source_owner():
    import projects

    assert projects.validate_options({"source_owner": "proprio"})["source_owner"] == "proprio"
    with pytest.raises(ValueError):
        projects.validate_options({"source_owner": 123})
