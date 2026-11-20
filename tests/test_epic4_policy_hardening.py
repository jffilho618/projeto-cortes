"""P6 (code review Épico 4) — policy_gate: limites de palavra, janela de spoiler, regras sem avaliador e TTL."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{(tmp_path / 'p6.db').as_posix()}")
    db.init_schema()
    return db


def _eval(db, slug, text, today=None):
    from picorte.risk_shield.policy_gate import evaluate_candidate_policy, sync_publisher_policies

    sync_publisher_policies(db)
    return evaluate_candidate_policy(db, game_slug=slug, title=text, today=today)


def test_ending_term_does_not_match_inside_trending(tmp_path: Path):
    res = _eval(_db(tmp_path), "gta6", "GTA 6 trending agora sending love", today=date(2026, 11, 20))
    assert res["status"] == "pass"


def test_ending_spoiler_still_blocked_inside_window(tmp_path: Path):
    res = _eval(_db(tmp_path), "gta6", "o ending do GTA 6", today=date(2026, 11, 20))
    assert res["status"] == "hard_block"


def test_story_game_without_release_date_always_checks_spoilers(tmp_path: Path):
    res = _eval(_db(tmp_path), "sony_story_games", "reagindo ao final do jogo", today=date(2030, 1, 1))
    assert res["status"] == "hard_block"


def test_zero_spoiler_window_is_respected_not_replaced_by_14(tmp_path: Path):
    from picorte.risk_shield.policy_gate import evaluate_candidate_policy

    db = _db(tmp_path)
    PicorteRepositories(db).policies.upsert_policy(
        publisher="X", game_slug="jogo0", release_date="2026-11-10", spoiler_window_days=0,
        forbidden_content_rules=["no_story_ending_spoiler"], has_licensed_radio_music=False,
        violence_check_strict=False,
    )
    res = evaluate_candidate_policy(db, game_slug="jogo0", title="final do jogo", today=date(2026, 11, 20),
                                    policies_path=tmp_path / "none.json")
    assert res["status"] == "pass"


def test_cheat_promotion_goes_to_human_review(tmp_path: Path):
    res = _eval(_db(tmp_path), "valorant", "testei o aimbot no ranked")
    assert res["status"] == "human_review"


def test_skin_gambling_promo_goes_to_human_review(tmp_path: Path):
    res = _eval(_db(tmp_path), "cs2", "ganhei no cassino de skins com cupom")
    assert res["status"] == "human_review"


def test_embargoed_cutscene_mention_goes_to_review(tmp_path: Path):
    res = _eval(_db(tmp_path), "gta6", "a cutscene da Lucia", today=date(2026, 11, 20))
    assert res["status"] == "human_review"


def test_music_rules_force_music_check(tmp_path: Path):
    from picorte.risk_shield.policy_gate import evaluate_candidate_policy

    db = _db(tmp_path)
    PicorteRepositories(db).policies.upsert_policy(
        publisher="X", game_slug="jogomus", release_date=None, spoiler_window_days=14,
        forbidden_content_rules=["no_raw_ost_music"], has_licensed_radio_music=False,
        violence_check_strict=False,
    )
    res = evaluate_candidate_policy(db, game_slug="jogomus", title="trilha", policies_path=tmp_path / "none.json")
    assert res["requires_music_check"] is True
    assert res["status"] == "pass"


def test_declared_rule_without_evaluator_never_passes_silently(tmp_path: Path):
    from picorte.risk_shield.policy_gate import evaluate_candidate_policy

    db = _db(tmp_path)
    PicorteRepositories(db).policies.upsert_policy(
        publisher="X", game_slug="jogox", release_date=None, spoiler_window_days=14,
        forbidden_content_rules=["regra_inventada_nova"], has_licensed_radio_music=False,
        violence_check_strict=False,
    )
    res = evaluate_candidate_policy(db, game_slug="jogox", title="corte normal", policies_path=tmp_path / "none.json")
    assert res["status"] == "human_review"
    assert "regra_inventada_nova" in " ".join(res["reasons"])


def test_expired_campaign_marks_source_expirada(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError, assert_can_export

    db = _db(tmp_path)
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(name="Camp", platform="twitch", channel_handle="@camp",
                                      permission_status="campanha_ativa")
    past = datetime.now(timezone.utc) - timedelta(days=10)
    repos.campaigns.create_campaign(source_id=src["id"], starts_at=(past - timedelta(days=5)).isoformat(),
                                    expires_at=past.isoformat())
    with pytest.raises(PolicyViolationError):
        assert_can_export(db, source_id=src["id"])
    assert repos.sources.get_source(src["id"])["permission_status"] == "expirada"


def test_future_campaign_is_not_valid_yet(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError, assert_can_ingest

    db = _db(tmp_path)
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(name="Fut", platform="twitch", channel_handle="@fut",
                                      permission_status="campanha_ativa")
    fut = datetime.now(timezone.utc) + timedelta(days=3)
    repos.campaigns.create_campaign(source_id=src["id"], starts_at=fut.isoformat(),
                                    expires_at=(fut + timedelta(days=10)).isoformat())
    with pytest.raises(PolicyViolationError):
        assert_can_ingest(db, source_id=src["id"])
    assert repos.sources.get_source(src["id"])["permission_status"] == "campanha_ativa"


def test_naive_now_does_not_crash(tmp_path: Path):
    from picorte.risk_shield.policy_gate import assert_can_ingest

    db = _db(tmp_path)
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(
        name="Ok", platform="twitch", channel_handle="@ok", permission_status="campanha_ativa")
    repos.campaigns.create_campaign(source_id=src["id"], starts_at="2026-11-01T00:00:00+00:00",
                                    expires_at="2026-12-01T00:00:00+00:00")
    assert assert_can_ingest(db, source_id=src["id"], now=datetime(2026, 11, 20, 12, 0))["allowed"]
