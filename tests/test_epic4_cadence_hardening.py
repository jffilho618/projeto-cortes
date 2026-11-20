"""P8 (code review Épico 4) — cadence_guard: agendados contam pelo horário marcado, estado protegido e horas válidas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import threading

import pytest

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _db_with_pub(tmp_path: Path, *, status: str, scheduled_for: datetime | None, created: datetime):
    db = Database(f"sqlite:///{(tmp_path / 'p8.db').as_posix()}")
    db.init_schema()
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(name="S", platform="twitch", channel_handle="@s", permission_status="liberada")
    vid = repos.videos.create_video(source_id=src["id"], source_url="u", game_slug="")
    clip = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=30.0)
    pub = repos.publications.create_publication(clip_id=clip["id"], platform="tiktok", status=status)
    db.execute("UPDATE publications SET created_at = ?, scheduled_for = ? WHERE id = ?",
               (created.isoformat(), scheduled_for.isoformat() if scheduled_for else None, pub["id"]))
    return db


def test_scheduled_post_counts_at_its_scheduled_time(tmp_path: Path):
    from picorte.risk_shield.cadence_guard import check_cadence

    now = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
    # Criado há 3 dias, mas agendado para daqui a 1h: postar agora fica colado nele.
    db = _db_with_pub(tmp_path, status="agendado", scheduled_for=now + timedelta(hours=1),
                      created=now - timedelta(days=3))
    res = check_cadence(db, platform="tiktok", state_path=tmp_path / "c.json", now=now)
    assert res["status"] == "block"


def test_old_creation_of_far_future_schedule_does_not_block(tmp_path: Path):
    from picorte.risk_shield.cadence_guard import check_cadence

    now = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
    db = _db_with_pub(tmp_path, status="agendado", scheduled_for=now + timedelta(days=3),
                      created=now - timedelta(minutes=10))
    res = check_cadence(db, platform="tiktok", state_path=tmp_path / "c.json", now=now)
    assert res["status"] == "pass"


def test_naive_now_does_not_crash(tmp_path: Path):
    from picorte.risk_shield.cadence_guard import check_cadence, get_cooldown_status

    db = _db_with_pub(tmp_path, status="publicado", scheduled_for=None,
                      created=datetime(2026, 11, 19, tzinfo=timezone.utc))
    check_cadence(db, platform="tiktok", state_path=tmp_path / "c.json", now=datetime(2026, 11, 20, 12, 0))
    get_cooldown_status(state_path=tmp_path / "c.json", now=datetime(2026, 11, 20, 12, 0))


def test_default_state_lives_in_work_dir_not_assets():
    from picorte.risk_shield import cadence_guard

    assert cadence_guard.DEFAULT_CADENCE_STATE_PATH.parent.name == "work"


@pytest.mark.parametrize("bad", [0, -5, math.inf, math.nan, 10_000])
def test_invalid_cooldown_hours_are_rejected(tmp_path: Path, bad):
    from picorte.risk_shield.cadence_guard import activate_cooldown

    with pytest.raises(ValueError):
        activate_cooldown("tiktok", hours=bad, state_path=tmp_path / "c.json")


def test_concurrent_cooldowns_do_not_lose_updates(tmp_path: Path):
    from picorte.risk_shield.cadence_guard import activate_cooldown

    state = tmp_path / "c.json"
    plats = ["youtube_shorts", "tiktok", "instagram_reels", "facebook_reels", "youtube_long"] * 4
    threads = [threading.Thread(target=activate_cooldown, args=(p,), kwargs={"hours": 2, "state_path": state})
               for p in plats]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    data = json.loads(state.read_text(encoding="utf-8"))
    assert set(data["cooldowns"]) == set(plats)
    assert not list(tmp_path.glob("*.tmp"))
