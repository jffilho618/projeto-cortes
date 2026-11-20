"""P2 (code review Épico 4) — RiskShield ligado ao pipeline real: veredito no .meta.json e Pacote do Dia que respeita P1."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{(tmp_path / 'p2.db').as_posix()}")
    db.init_schema()
    return db


def _source(db: Database, status: str = "liberada") -> dict:
    return PicorteRepositories(db).sources.create_source(
        name="ALANZOKA", platform="twitch", channel_handle="@alanzoka", permission_status=status)


def _meta(title: str = "Corte limpo") -> dict:
    return {"title": title, "description": "Créditos: @alanzoka", "hashtags": ["#gta6"],
            "proposed_title": title, "start": 10.0, "end": 40.0}


def test_attach_risk_verdict_writes_compact_verdict_into_meta(tmp_path: Path):
    from picorte.risk_shield.pipeline import attach_risk_verdict

    db = _db(tmp_path)
    src = _source(db)
    meta_path = tmp_path / "c.meta.json"
    meta_path.write_text(json.dumps(_meta()), encoding="utf-8")
    words = [{"word": "olha", "start": 10.5, "end": 10.9}]
    verdict = attach_risk_verdict(db, meta_path=meta_path, source_id=src["id"], seg={"start": 10.0, "end": 40.0},
                                  words=words, mp4_path=None, options={"aspect": "9:16", "layout": "games"},
                                  game_slug="", cadence_state_path=tmp_path / "cad.json")
    saved = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved["risk_status"] == verdict["overall_status"]
    # Sem .mp4 não há frames para provar ritmo (P10): o YPP cai e o corte pode ser barrado — aqui só a estrutura.
    assert saved["risk_verdict"]["per_platform"]["tiktok"] in {"pass", "auto_fixed", "human_review", "hard_block"}
    assert "source_permission" in saved["risk_verdict"]["gates"]


def test_attach_risk_verdict_fails_closed_on_audit_error(tmp_path: Path, monkeypatch):
    import picorte.risk_shield.pipeline as pl

    def boom(*a, **k):
        raise RuntimeError("quebrou")

    monkeypatch.setattr(pl, "audit_clip_risk", boom)
    meta_path = tmp_path / "c.meta.json"
    meta_path.write_text(json.dumps(_meta()), encoding="utf-8")
    pl.attach_risk_verdict(_db(tmp_path), meta_path=meta_path, source_id=None, seg={"start": 0, "end": 30},
                           words=[], mp4_path=None, options={}, game_slug="")
    saved = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved["risk_status"] == "audit_error"


def _project(tmp_path: Path, source_id: str | None, clips: dict[str, str | None]) -> Path:
    pdir = tmp_path / "proj1"
    cdir = pdir / "clips"
    cdir.mkdir(parents=True)
    (pdir / "project.json").write_text(json.dumps({
        "id": "proj1", "source_meta": {"channel": "alanzoka", "title": "GTA 6"},
        "source_gate": {"source_id": source_id},
    }), encoding="utf-8")
    for stem, status in clips.items():
        (cdir / f"{stem}.mp4").write_bytes(b"mp4")
        meta = {"proposed_title": f"Corte {stem}"}
        if status is not None:
            meta["risk_status"] = status
        (cdir / f"{stem}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return pdir


def test_export_skips_unaudited_and_blocked_and_flags_review(tmp_path: Path):
    from picorte.engine.publish_kit import export_daily_bundle

    db = _db(tmp_path)
    src = _source(db)
    pdir = _project(tmp_path, src["id"], {"001-ok": "pass", "002-sem": None, "003-bloq": "hard_block",
                                          "004-rev": "human_review"})
    res = export_daily_bundle(pdir, out_root=tmp_path / "out", db=db, cadence_state_path=tmp_path / "cad.json")
    stems = [f["stem"] for f in res["files"]]
    assert stems == ["001-ok", "004-rev"]
    assert set(res["skipped_blocked"]) == {"002-sem", "003-bloq"}
    rev = next(f for f in res["files"] if f["stem"] == "004-rev")
    assert rev["needs_review"] is True
    assert Path(rev["mp4"]).name.startswith("REVISAR_")


def test_export_blocks_whole_bundle_when_source_was_paused(tmp_path: Path):
    from picorte.engine.publish_kit import export_daily_bundle
    from picorte.risk_shield.policy_gate import PolicyViolationError

    db = _db(tmp_path)
    src = _source(db, status="pausada_por_claim")
    pdir = _project(tmp_path, src["id"], {"001-ok": "pass"})
    with pytest.raises(PolicyViolationError):
        export_daily_bundle(pdir, out_root=tmp_path / "out", db=db)


def test_export_blocks_project_without_source_link(tmp_path: Path):
    from picorte.engine.publish_kit import export_daily_bundle
    from picorte.risk_shield.policy_gate import PolicyViolationError

    pdir = _project(tmp_path, None, {"001-ok": "pass"})
    with pytest.raises(PolicyViolationError):
        export_daily_bundle(pdir, out_root=tmp_path / "out", db=_db(tmp_path))


def test_export_warns_platform_in_cooldown(tmp_path: Path):
    from picorte.engine.publish_kit import export_daily_bundle
    from picorte.risk_shield.cadence_guard import activate_cooldown

    db = _db(tmp_path)
    src = _source(db)
    cad = tmp_path / "cad.json"
    activate_cooldown("tiktok", hours=48, reason="teste", state_path=cad)
    pdir = _project(tmp_path, src["id"], {"001-ok": "pass"})
    res = export_daily_bundle(pdir, out_root=tmp_path / "out", db=db, cadence_state_path=cad)
    assert "tiktok" in res["cadence_blocked"]
    txt = Path(res["files"][0]["copy_txt"]).read_text(encoding="utf-8")
    assert "NÃO POSTAR" in txt and "TIKTOK" in txt.upper()
