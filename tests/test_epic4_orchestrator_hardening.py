"""P3 (code review Épico 4) — Orquestrador RiskShield sem brechas: fonte sem vínculo, YPP otimista, música, rede."""
from __future__ import annotations

from pathlib import Path

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{(tmp_path / 'p3.db').as_posix()}")
    db.init_schema()
    return db


def _ok_source(db: Database) -> dict:
    return PicorteRepositories(db).sources.create_source(
        name="ALANZOKA", platform="youtube", channel_handle="@alanzoka", permission_status="liberada"
    )


def test_clip_without_any_source_link_is_hard_blocked(tmp_path: Path):
    from picorte.risk_shield.orchestrator import audit_clip_risk

    verdict = audit_clip_risk(_db(tmp_path), title="corte")
    assert verdict["gates"]["source_permission"]["status"] == "hard_block"
    assert verdict["gates"]["source_permission"]["code"] == "source_unlinked"
    assert verdict["overall_status"] == "hard_block"


def test_source_is_resolved_from_clip_video_when_not_passed(tmp_path: Path):
    from picorte.risk_shield.orchestrator import audit_clip_risk

    db = _db(tmp_path)
    repos = PicorteRepositories(db)
    src = _ok_source(db)
    vid = repos.videos.create_video(source_id=src["id"], source_url="https://yt/x", game_slug="")
    clip = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=30.0)
    verdict = audit_clip_risk(db, clip_id=clip["id"], title="corte")
    assert verdict["gates"]["source_permission"]["status"] == "pass"


def test_source_gate_cannot_be_skipped_by_caller(tmp_path: Path):
    import inspect

    from picorte.risk_shield.orchestrator import audit_clip_risk

    assert "enforce_source_gate" not in inspect.signature(audit_clip_risk).parameters


def test_transformation_flags_are_not_assumed_true_by_default(tmp_path: Path):
    from picorte.risk_shield.orchestrator import audit_clip_risk

    db = _db(tmp_path)
    src = _ok_source(db)
    bare = audit_clip_risk(db, source_id=src["id"], title="corte")
    full = audit_clip_risk(
        db, source_id=src["id"], title="corte", has_facecam_split=True, has_dynamic_captions=True,
        has_context_banner=True, has_native_metadata=True, has_cold_open=True,
    )
    assert bare["ypp_score"] < full["ypp_score"]


def test_game_with_licensed_music_requires_audio_check_when_surgery_not_run(tmp_path: Path):
    from picorte.risk_shield.orchestrator import audit_clip_risk
    from picorte.risk_shield.policy_gate import sync_publisher_policies

    db = _db(tmp_path)
    sync_publisher_policies(db)
    src = _ok_source(db)
    verdict = audit_clip_risk(db, source_id=src["id"], game_slug="gta6", title="corte", music_result=None)
    assert verdict["gates"]["music_surgeon"]["status"] == "human_review"
    assert verdict["gates"]["music_surgeon"]["code"] == "NEEDS_HUMAN_AUDIO_CHECK"
    assert verdict["overall_status"] in {"human_review", "hard_block"}


def test_overall_status_reflects_worst_platform_status(tmp_path: Path):
    from picorte.risk_shield.orchestrator import _rank, audit_clip_risk

    db = _db(tmp_path)
    src = _ok_source(db)
    verdict = audit_clip_risk(
        db, source_id=src["id"], title="corte", description="veja em youtube.com/watch?v=1",
        hashtags=["#shorts"], cadence_state_path=tmp_path / "cad.json",
    )
    worst = max((p["status"] for p in verdict["per_platform"].values()), key=_rank)
    assert _rank(verdict["overall_status"]) >= _rank(worst)


def test_long_format_is_audited_for_youtube_long(tmp_path: Path):
    from picorte.risk_shield.orchestrator import audit_clip_risk

    db = _db(tmp_path)
    src = _ok_source(db)
    verdict = audit_clip_risk(db, source_id=src["id"], title="corte longo", format_type="long_16_9",
                              cadence_state_path=tmp_path / "cad.json")
    assert set(verdict["per_platform"]) == {"youtube_long"}
