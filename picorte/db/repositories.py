"""Repositórios das 10 entidades canônicas do Picorte (AD-2)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .connection import Database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class PoliciesRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_policy(
        self,
        *,
        publisher: str,
        game_slug: str,
        release_date: str | None = None,
        spoiler_window_days: int = 14,
        forbidden_content_rules: list[str] | None = None,
        has_licensed_radio_music: bool = False,
        violence_check_strict: bool = False,
    ) -> dict[str, Any]:
        existing = self.get_by_game(game_slug)
        pid = existing["id"] if existing else _new_id()
        rules_json = json.dumps(forbidden_content_rules or [], ensure_ascii=False)
        now = _now_iso()
        if existing:
            self.db.execute(
                """UPDATE publisher_policies
                   SET publisher = ?, release_date = ?, spoiler_window_days = ?,
                       forbidden_content_rules = ?, has_licensed_radio_music = ?, violence_check_strict = ?
                   WHERE game_slug = ?""",
                (
                    publisher,
                    release_date,
                    int(spoiler_window_days),
                    rules_json,
                    int(bool(has_licensed_radio_music)),
                    int(bool(violence_check_strict)),
                    game_slug,
                ),
            )
        else:
            self.db.execute(
                """INSERT INTO publisher_policies
                   (id, publisher, game_slug, release_date, spoiler_window_days,
                    forbidden_content_rules, has_licensed_radio_music, violence_check_strict, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pid,
                    publisher,
                    game_slug,
                    release_date,
                    int(spoiler_window_days),
                    rules_json,
                    int(bool(has_licensed_radio_music)),
                    int(bool(violence_check_strict)),
                    now,
                ),
            )
        return self.get_by_game(game_slug)  # type: ignore[return-value]

    def get_by_game(self, game_slug: str) -> dict[str, Any] | None:
        row = self.db.fetch_one("SELECT * FROM publisher_policies WHERE game_slug = ?", (game_slug,))
        if not row:
            return None
        row["forbidden_content_rules"] = json.loads(row.get("forbidden_content_rules") or "[]")
        row["has_licensed_radio_music"] = bool(row.get("has_licensed_radio_music"))
        row["violence_check_strict"] = bool(row.get("violence_check_strict"))
        return row


class SourcesRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_source(
        self,
        *,
        name: str,
        platform: str,
        channel_handle: str,
        permission_status: str = "desconhecida",
        permission_evidence_url: str = "",
        credit_template: str = "Créditos: @{handle}",
        default_game_slug: str = "",
        permission_basis: str = "explicita",
    ) -> dict[str, Any]:
        sid = _new_id()
        now = _now_iso()
        self.db.execute(
            """INSERT INTO sources
               (id, name, platform, channel_handle, permission_status, permission_evidence_url,
                permission_basis, credit_template, default_game_slug, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sid,
                name,
                platform,
                channel_handle,
                permission_status,
                permission_evidence_url,
                permission_basis,
                credit_template,
                default_game_slug,
                now,
                now,
            ),
        )
        return self.get_source(sid)  # type: ignore[return-value]

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        return self.db.fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))

    def list_sources(self) -> list[dict[str, Any]]:
        return self.db.fetch_all("SELECT * FROM sources ORDER BY created_at DESC")

    def update_permission(
        self, source_id: str, permission_status: str, evidence_url: str | None = None
    ) -> dict[str, Any]:
        now = _now_iso()
        if evidence_url is not None:
            self.db.execute(
                "UPDATE sources SET permission_status = ?, permission_evidence_url = ?, updated_at = ? WHERE id = ?",
                (permission_status, evidence_url, now, source_id),
            )
        else:
            self.db.execute(
                "UPDATE sources SET permission_status = ?, updated_at = ? WHERE id = ?",
                (permission_status, now, source_id),
            )
        return self.get_source(source_id)  # type: ignore[return-value]


class CampaignsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_campaign(
        self,
        *,
        source_id: str,
        game_slug: str = "",
        cpm_brl: float = 0.0,
        required_tags: list[str] | None = None,
        starts_at: str | None = None,
        expires_at: str | None = None,
        is_active: bool = True,
    ) -> dict[str, Any]:
        cid = _new_id()
        now = _now_iso()
        self.db.execute(
            """INSERT INTO campaigns
               (id, source_id, game_slug, cpm_brl, required_tags, starts_at, expires_at, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cid,
                source_id,
                game_slug,
                float(cpm_brl),
                json.dumps(required_tags or [], ensure_ascii=False),
                starts_at or now,
                expires_at,
                int(bool(is_active)),
                now,
            ),
        )
        row = self.db.fetch_one("SELECT * FROM campaigns WHERE id = ?", (cid,))
        if row:
            row["required_tags"] = json.loads(row.get("required_tags") or "[]")
            row["is_active"] = bool(row.get("is_active"))
        return row  # type: ignore[return-value]


class VideosRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_video(
        self,
        *,
        source_id: str | None = None,
        origin_type: str = "vod",
        source_url: str,
        game_slug: str = "",
        duration_seconds: float = 0.0,
        workdir_path: str = "",
        status: str = "queued",
    ) -> dict[str, Any]:
        vid = _new_id()
        now = _now_iso()
        self.db.execute(
            """INSERT INTO videos
               (id, source_id, origin_type, source_url, game_slug, duration_seconds, workdir_path, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (vid, source_id, origin_type, source_url, game_slug, float(duration_seconds), workdir_path, status, now, now),
        )
        return self.db.fetch_one("SELECT * FROM videos WHERE id = ?", (vid,))  # type: ignore[return-value]

    def list_videos(self) -> list[dict[str, Any]]:
        return self.db.fetch_all("SELECT * FROM videos ORDER BY created_at DESC")


class ClipsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_clip(
        self,
        *,
        video_id: str,
        parent_long_clip_id: str | None = None,
        format_type: str = "short_9_16",
        ab_variant: int = 1,
        start_sec: float,
        end_sec: float,
        score_chat: float = 0.0,
        score_audio: float = 0.0,
        score_visual: float = 0.0,
        score_text: float = 0.0,
        score_overall: float = 0.0,
        ypp_transform_score: int = 0,
        phash_signature: str = "",
        llm_mode_used: str = "heuristic",
        risk_status: str = "pending",
        mp4_path: str = "",
        thumbnail_path: str = "",
        proposed_title: str = "",
        context_banner_2s: str = "",
        pinned_comment_debate: str = "",
    ) -> dict[str, Any]:
        cid = _new_id()
        now = _now_iso()
        self.db.execute(
            """INSERT INTO clips
               (id, video_id, parent_long_clip_id, format_type, ab_variant, start_sec, end_sec,
                score_chat, score_audio, score_visual, score_text, score_overall,
                ypp_transform_score, phash_signature, llm_mode_used, risk_status,
                mp4_path, thumbnail_path, proposed_title, context_banner_2s, pinned_comment_debate, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cid,
                video_id,
                parent_long_clip_id,
                format_type,
                int(ab_variant),
                float(start_sec),
                float(end_sec),
                float(score_chat),
                float(score_audio),
                float(score_visual),
                float(score_text),
                float(score_overall),
                int(ypp_transform_score),
                phash_signature,
                llm_mode_used,
                risk_status,
                mp4_path,
                thumbnail_path,
                proposed_title,
                context_banner_2s,
                pinned_comment_debate,
                now,
            ),
        )
        return self.db.fetch_one("SELECT * FROM clips WHERE id = ?", (cid,))  # type: ignore[return-value]

    def list_clips(self, video_id: str | None = None) -> list[dict[str, Any]]:
        if video_id:
            return self.db.fetch_all("SELECT * FROM clips WHERE video_id = ? ORDER BY score_overall DESC", (video_id,))
        return self.db.fetch_all("SELECT * FROM clips ORDER BY created_at DESC")


class PublicationsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_publication(
        self,
        *,
        clip_id: str,
        social_account_id: str | None = None,
        platform: str,
        publish_mode: str = "assisted_manual",
        status: str = "fila",
        external_post_id: str = "",
        external_url: str = "",
        related_video_external_id: str = "",
        scheduled_for: str | None = None,
    ) -> dict[str, Any]:
        pid = _new_id()
        now = _now_iso()
        self.db.execute(
            """INSERT INTO publications
               (id, clip_id, social_account_id, platform, publish_mode, status,
                external_post_id, external_url, related_video_external_id, scheduled_for, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pid,
                clip_id,
                social_account_id,
                platform,
                publish_mode,
                status,
                external_post_id,
                external_url,
                related_video_external_id,
                scheduled_for,
                now,
            ),
        )
        return self.db.fetch_one("SELECT * FROM publications WHERE id = ?", (pid,))  # type: ignore[return-value]


class MetricsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def record_snapshot(
        self,
        *,
        publication_id: str,
        window_label: str,
        views: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        avg_view_pct: float = 0.0,
        stayed_to_watch_3s_pct: float = 0.0,
        computed_reward: float = 0.0,
    ) -> dict[str, Any]:
        mid = _new_id()
        now = _now_iso()
        self.db.execute(
            """INSERT INTO metrics_snapshots
               (id, publication_id, window_label, views, likes, comments, shares,
                avg_view_pct, stayed_to_watch_3s_pct, computed_reward, captured_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mid,
                publication_id,
                window_label,
                int(views),
                int(likes),
                int(comments),
                int(shares),
                float(avg_view_pct),
                float(stayed_to_watch_3s_pct),
                float(computed_reward),
                now,
            ),
        )
        return self.db.fetch_one("SELECT * FROM metrics_snapshots WHERE id = ?", (mid,))  # type: ignore[return-value]


class BanditRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_factor(
        self, factor_key: str, *, mu: float, sigma_sq: float, observations_count: int
    ) -> dict[str, Any]:
        now = _now_iso()
        existing = self.db.fetch_one("SELECT * FROM bandit_state WHERE factor_key = ?", (factor_key,))
        if existing:
            self.db.execute(
                "UPDATE bandit_state SET mu = ?, sigma_sq = ?, observations_count = ?, updated_at = ? WHERE factor_key = ?",
                (float(mu), float(sigma_sq), int(observations_count), now, factor_key),
            )
        else:
            self.db.execute(
                "INSERT INTO bandit_state (factor_key, mu, sigma_sq, observations_count, updated_at) VALUES (?, ?, ?, ?, ?)",
                (factor_key, float(mu), float(sigma_sq), int(observations_count), now),
            )
        return self.db.fetch_one("SELECT * FROM bandit_state WHERE factor_key = ?", (factor_key,))  # type: ignore[return-value]


class PicorteRepositories:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.policies = PoliciesRepository(db)
        self.sources = SourcesRepository(db)
        self.campaigns = CampaignsRepository(db)
        self.videos = VideosRepository(db)
        self.clips = ClipsRepository(db)
        self.publications = PublicationsRepository(db)
        self.metrics = MetricsRepository(db)
        self.bandit = BanditRepository(db)
