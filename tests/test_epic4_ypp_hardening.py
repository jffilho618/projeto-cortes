"""P10 (code review Épico 4) — ypp_guard: marca d'água, A/B com pai real, sem frames, deslocamento e clipes bloqueados."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{(tmp_path / 'p10.db').as_posix()}")
    db.init_schema()
    return db


def _scene(seed: int, n: int = 15) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    frames = []
    for i in range(n):
        fr = np.full((360, 640, 3), (60, 90, 70), dtype=np.uint8)
        for _ in range(6):
            x, y = int(rng.integers(0, 600)), int(rng.integers(0, 320))
            cv2.rectangle(fr, (x, y), (x + 40, y + 40), tuple(int(c) for c in rng.integers(0, 255, 3)), -1)
        frames.append(fr)
    return frames


def _ypp(db, frames, **kw):
    from picorte.risk_shield.ypp_guard import evaluate_ypp_and_dedup

    base = dict(has_facecam_split=True, has_dynamic_captions=True, has_context_banner=True,
                has_native_metadata=True, has_cold_open=False)
    base.update(kw)
    return evaluate_ypp_and_dedup(db, frames=frames, **base)


def _tiktok_logo(fr: np.ndarray) -> np.ndarray:
    out = fr.copy()
    cv2.putText(out, "d", (14, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (238, 244, 37), 4)  # ciano #25F4EE
    cv2.putText(out, "d", (18, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (85, 44, 254), 4)   # rosa #FE2C55
    return out


def test_tiktok_watermark_in_corner_is_detected_from_frames(tmp_path: Path):
    frames = [_tiktok_logo(f) for f in _scene(1)]
    res = _ypp(_db(tmp_path), frames)
    assert res["watermark_detected"] is True
    assert res["status"] == "hard_block"


def test_clean_gameplay_has_no_watermark(tmp_path: Path):
    res = _ypp(_db(tmp_path), _scene(2))
    assert res["watermark_detected"] is False


def test_ab_variant_requires_existing_parent(tmp_path: Path):
    db = _db(tmp_path)
    res = _ypp(db, _scene(3), ab_variant=2, parent_clip_id="nao-existe")
    assert res["ab_recycle_allowed"] is False


def test_no_frames_does_not_earn_pacing_points(tmp_path: Path):
    res = _ypp(_db(tmp_path), [])
    assert res["audit_trail"]["layers"]["pacing_or_cold_open"] == 0


def test_same_clip_shifted_by_2s_is_still_duplicate(tmp_path: Path):
    from picorte.risk_shield.ypp_guard import compute_video_phash, phash_similarity

    scene = _scene(4, n=20)
    a = compute_video_phash(scene[0:15])
    b = compute_video_phash(scene[2:17])
    assert phash_similarity(a, b) > 0.85


def test_blocked_clips_are_not_used_as_dedup_reference(tmp_path: Path):
    from picorte.risk_shield.ypp_guard import compute_video_phash

    db = _db(tmp_path)
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(name="S", platform="twitch", channel_handle="@s", permission_status="liberada")
    vid = repos.videos.create_video(source_id=src["id"], source_url="u", game_slug="")
    clip = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=30.0)
    frames = _scene(5)
    db.execute("UPDATE clips SET phash_signature = ?, risk_status = 'hard_block' WHERE id = ?",
               (compute_video_phash(frames), clip["id"]))
    res = _ypp(db, frames)
    assert res["is_duplicate"] is False
