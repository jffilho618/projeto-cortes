"""Testes TDD Story 4.2 — Copy Hygiene por Rede, Cadência Anti-Spam + Cool-Down 48h, YPP/TikTok Score e pHash."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _make_db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{(tmp_path / 'e4_guards.db').as_posix()}")
    db.init_schema()
    return db


def test_copy_guard_strips_cross_platform_urls_and_shorts_from_tiktok_and_flags_yellow_icon_words():
    from picorte.risk_shield.copy_guard import audit_and_sanitize_copy

    dirty_tiktok = (
        "Alanzoka mata todo mundo no GTA 6! Canal de cortes feito por fãs.\n"
        "Twitch: https://www.twitch.tv/alanzoka\n"
        "YouTube: https://www.youtube.com/@alanzoka\n"
        "#gta6 #alanzoka #shorts #gtavi #games #viral #fyp"
    )
    res_tt = audit_and_sanitize_copy(
        platform="tiktok",
        title="Alanzoka mata geral com sangue no GTA 6",
        description=dirty_tiktok,
        hashtags=["#gta6", "#alanzoka", "#shorts", "#gtavi", "#games", "#viral", "#fyp"],
        source_credit="@alanzoka",
    )

    assert "youtube.com" not in res_tt["sanitized_description"].lower()
    assert "twitch.tv" not in res_tt["sanitized_description"].lower()
    assert "#shorts" not in res_tt["sanitized_description"].lower()
    assert "canal de cortes" not in res_tt["sanitized_description"].lower()
    assert "@alanzoka" in res_tt["sanitized_description"].lower()
    assert len(res_tt["sanitized_hashtags"]) <= 5
    assert res_tt["auto_fixed"] is True
    assert len(res_tt["ad_friendly_warnings"]) >= 1  # "mata" / "sangue" sinalizados

    # No YouTube Shorts, links oficiais de crédito são permitidos e #shorts é mantido
    res_yt = audit_and_sanitize_copy(
        platform="youtube_shorts",
        title="Alanzoka testa a física da água no GTA 6",
        description="Créditos:\n• Twitch: https://www.twitch.tv/alanzoka\n#shorts #gta6 #alanzoka",
        hashtags=["#shorts", "#gta6", "#alanzoka"],
        source_credit="@alanzoka",
    )
    assert "twitch.tv/alanzoka" in res_yt["sanitized_description"].lower()
    assert "#shorts" in res_yt["sanitized_hashtags"]
    assert res_yt["ad_friendly_warnings"] == []


def test_cadence_guard_enforces_daily_cap_min_gap_and_48h_cooldown(tmp_path: Path):
    from picorte.risk_shield.cadence_guard import (
        activate_cooldown,
        check_cadence,
        clear_cooldown,
    )

    db = _make_db(tmp_path)
    repos = PicorteRepositories(db)
    state_file = tmp_path / "cadence_state.json"

    vid = repos.videos.create_video(source_url="https://yt/1", game_slug="gta6")
    clip1 = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=30.0)
    clip2 = repos.clips.create_clip(video_id=vid["id"], start_sec=40.0, end_sec=70.0)

    now = datetime.now(timezone.utc)
    # 1ª publicação há 20 minutos -> gap mínimo (4h em warmup) dispara block/warn!
    repos.publications.create_publication(
        clip_id=clip1["id"], platform="youtube_shorts", status="publicado"
    )
    db.execute(
        "UPDATE publications SET created_at = ? WHERE clip_id = ?",
        ((now - timedelta(minutes=20)).isoformat(), clip1["id"]),
    )

    chk_gap = check_cadence(db, platform="youtube_shorts", profile="warmup", state_path=state_file, now=now)
    assert chk_gap["status"] == "block"
    assert chk_gap["next_safe_at"] is not None

    # Simulando 2 publicações hoje bem espaçadas (6h e 12h atrás) -> dentro do teto de 3/dia (warmup) -> pass!
    db.execute(
        "UPDATE publications SET created_at = ? WHERE clip_id = ?",
        ((now - timedelta(hours=10)).isoformat(), clip1["id"]),
    )
    repos.publications.create_publication(clip_id=clip2["id"], platform="youtube_shorts", status="publicado")
    db.execute(
        "UPDATE publications SET created_at = ? WHERE clip_id = ?",
        ((now - timedelta(hours=5)).isoformat(), clip2["id"]),
    )
    chk_ok = check_cadence(db, platform="youtube_shorts", profile="warmup", state_path=state_file, now=now)
    assert chk_ok["status"] == "pass"
    assert chk_ok["posted_last_24h"] == 2

    # Ativando Cool-Down de 48h no TikTok -> bloqueia imediatamente até vencer
    activate_cooldown("tiktok", hours=48, reason="Burst anti-spam recovery", state_path=state_file, now=now)
    chk_cd = check_cadence(db, platform="tiktok", profile="warmup", state_path=state_file, now=now)
    assert chk_cd["status"] == "block"
    assert chk_cd["cooldown_active"] is True

    clear_cooldown("tiktok", state_path=state_file)
    chk_after = check_cadence(db, platform="tiktok", profile="warmup", state_path=state_file, now=now)
    assert chk_after["status"] == "pass"


def test_ypp_guard_computes_dual_scores_static_frames_and_phash_dedup_with_ab_exception(tmp_path: Path):
    from picorte.risk_shield.ypp_guard import compute_video_phash, evaluate_ypp_and_dedup

    db = _make_db(tmp_path)
    repos = PicorteRepositories(db)
    vid = repos.videos.create_video(source_url="https://yt/1", game_slug="gta6")

    # Cria 5 frames com movimento real (variando cena)
    dynamic_frames = []
    for i in range(6):
        fr = np.zeros((360, 202, 3), dtype=np.uint8)
        cv2.circle(fr, (40 + i * 25, 100 + i * 20), 35, (60 + i * 30, 180, 90), -1)
        cv2.rectangle(fr, (10, 220 - i * 10), (190, 340), (200, 120, 40 + i * 25), 3)
        dynamic_frames.append(fr)

    # Cria 6 frames congelados (menu parado > 4s)
    frozen = dynamic_frames[0].copy()
    static_frames = [frozen.copy() for _ in range(6)]

    phash_dyn = compute_video_phash(dynamic_frames)
    assert len(phash_dyn) >= 16

    # 1) Clipe bem transformado e inédito -> PASS (>= 70)
    res_good = evaluate_ypp_and_dedup(
        db,
        frames=dynamic_frames,
        transcript_text="Alanzoka testa a física da lama nos carros do GTA 6 e fica impressionado com os detalhes",
        has_facecam_split=True,
        has_dynamic_captions=True,
        has_context_banner=True,
        has_native_metadata=True,
        has_cold_open=True,
        audio_clean=True,
        fps_sampled=1.0,
    )
    assert res_good["ypp_score"] >= 70
    assert res_good["tiktok_originality_score"] >= 70
    assert res_good["status"] == "pass"
    assert res_good["is_duplicate"] is False
    assert "layers" in res_good["audit_trail"]

    # 2) Clipe cru sem transformação + tela congelada -> HARD_BLOCK
    res_raw = evaluate_ypp_and_dedup(
        db,
        frames=static_frames,
        transcript_text="teste curto",
        has_facecam_split=False,
        has_dynamic_captions=False,
        has_context_banner=False,
        has_native_metadata=False,
        has_cold_open=False,
        audio_clean=True,
        fps_sampled=1.0,
    )
    assert res_raw["ypp_score"] < 70
    assert res_raw["max_static_seconds"] >= 4.0
    assert res_raw["status"] == "hard_block"

    # 3) Salva o clipe bom no DB e tenta passar o mesmo clipe de novo -> DUPLICATA bloqueada!
    c1 = repos.clips.create_clip(
        video_id=vid["id"],
        start_sec=10.0,
        end_sec=45.0,
        ypp_transform_score=res_good["ypp_score"],
        phash_signature=res_good["phash_signature"],
        proposed_title="Alanzoka testa a física da lama nos carros do GTA 6",
        context_banner_2s="FÍSICA DA LAMA INSANA",
    )
    res_dup = evaluate_ypp_and_dedup(
        db,
        frames=dynamic_frames,
        transcript_text="Alanzoka testa a física da lama nos carros do GTA 6 e fica impressionado com os detalhes",
        has_facecam_split=True,
        has_dynamic_captions=True,
        has_context_banner=True,
        has_native_metadata=True,
        has_cold_open=True,
        audio_clean=True,
        fps_sampled=1.0,
    )
    assert res_dup["is_duplicate"] is True
    assert res_dup["status"] == "hard_block"
    assert res_dup["duplicate_clip_id"] == c1["id"]

    # 4) Exceção explícita para Reciclagem A/B do Épico 7 (ab_variant > 1 + parent_clip_id)
    res_ab = evaluate_ypp_and_dedup(
        db,
        frames=dynamic_frames,
        transcript_text="Alanzoka testa a física da lama nos carros do GTA 6 e fica impressionado com os detalhes",
        has_facecam_split=True,
        has_dynamic_captions=True,
        has_context_banner=True,
        has_native_metadata=True,
        has_cold_open=True,
        audio_clean=True,
        fps_sampled=1.0,
        ab_variant=2,
        parent_clip_id=c1["id"],
    )
    assert res_ab["is_duplicate"] is False
    assert res_ab["status"] == "pass"
