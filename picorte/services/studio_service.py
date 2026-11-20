"""Fachada unificada de domínio consumida pelo Painel Web e pelo Servidor MCP (AD-10)."""
from __future__ import annotations

from typing import Any

from picorte.config import detect_gpu_profile
from picorte.db.connection import Database, get_default_db
from picorte.db.repositories import PicorteRepositories


class StudioService:
    """Concentra todas as operações de negócio sobre fontes, vídeos, cortes e status da fila."""

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or get_default_db()
        self.repos = PicorteRepositories(self.db)

    def status_fila(self) -> dict[str, Any]:
        sources = self.repos.sources.list_sources()
        videos = self.repos.videos.list_videos()
        clips = self.repos.clips.list_clips()
        return {
            "gpu_profile": detect_gpu_profile(),
            "total_sources": len(sources),
            "total_videos": len(videos),
            "total_clips": len(clips),
            "queued_videos": sum(1 for v in videos if v.get("status") == "queued"),
            "blocked_p1": sum(1 for v in videos if v.get("status") == "blocked_p1"),
        }

    def list_sources(self) -> list[dict[str, Any]]:
        return self.repos.sources.list_sources()

    def create_source(
        self,
        *,
        name: str,
        platform: str,
        channel_handle: str,
        permission_status: str = "desconhecida",
        evidence_url: str = "",
        default_game_slug: str = "",
    ) -> dict[str, Any]:
        return self.repos.sources.create_source(
            name=name,
            platform=platform,
            channel_handle=channel_handle,
            permission_status=permission_status,
            permission_evidence_url=evidence_url,
            default_game_slug=default_game_slug,
        )

    def update_source_permission(
        self, source_id: str, permission_status: str, evidence_url: str | None = None
    ) -> dict[str, Any]:
        return self.repos.sources.update_permission(
            source_id, permission_status, evidence_url=evidence_url
        )

    def enqueue_video(
        self,
        *,
        source_url: str,
        source_id: str | None = None,
        origin_type: str = "vod",
        game_slug: str = "",
        workdir_path: str = "",
    ) -> dict[str, Any]:
        return self.repos.videos.create_video(
            source_id=source_id,
            origin_type=origin_type,
            source_url=source_url,
            game_slug=game_slug,
            workdir_path=workdir_path,
            status="queued",
        )

    def list_clips(self, video_id: str | None = None) -> list[dict[str, Any]]:
        return self.repos.clips.list_clips(video_id=video_id)

    def sync_studio_project(
        self,
        project_state: dict[str, Any],
        *,
        segments: list[dict[str, Any]] | None = None,
        outputs: list[str] | None = None,
        workdir: Any = "",
        duration_seconds: float = 0.0,
    ) -> dict[str, Any]:
        """Espelha um projeto do Studio/CLI para as tabelas canônicas videos e clips."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        project_id = str(project_state["id"])
        video_id = f"studio-{project_id}"
        source_url = str(project_state.get("source") or project_state.get("video") or "")
        status = str(project_state.get("status") or "queued")
        options = project_state.get("options") or {}
        aspect = options.get("aspect", "9:16")
        fmt = "short_9_16" if aspect == "9:16" else ("long_16_9" if aspect == "16:9" else "square_1_1")
        ai_mode = str(options.get("ai_mode") or ("ollama" if options.get("llm") else "heuristic"))

        existing_video = self.db.fetch_one("SELECT * FROM videos WHERE id = ?", (video_id,))
        if existing_video:
            self.db.execute(
                """UPDATE videos SET source_url = ?, duration_seconds = ?, workdir_path = ?,
                   status = ?, updated_at = ? WHERE id = ?""",
                (source_url, float(duration_seconds), str(workdir), status, now, video_id),
            )
        else:
            self.db.execute(
                """INSERT INTO videos
                   (id, source_id, origin_type, source_url, game_slug, duration_seconds, workdir_path, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (video_id, None, "local_file", source_url, "", float(duration_seconds), str(workdir), status, now, now),
            )

        out_list = list(outputs or [])
        synced_clips = []
        for idx, seg in enumerate(segments or [], 1):
            seg_id = str(seg.get("id") or f"{idx:03}")
            clip_id = f"{video_id}:{seg_id}"
            mp4_path = out_list[idx - 1] if idx - 1 < len(out_list) else ""
            mode_used = str(seg.get("llm_mode_used") or ai_mode)
            title = str(seg.get("proposed_title") or seg.get("hook") or "")
            ctx_banner = str(seg.get("context_banner_2s") or "")
            pinned = str(seg.get("pinned_comment_debate") or "")
            overall = float(seg.get("overall") or 0.0)
            start_sec = float(seg.get("start") or 0.0)
            end_sec = float(seg.get("end") or 0.0)

            existing_clip = self.db.fetch_one("SELECT id FROM clips WHERE id = ?", (clip_id,))
            if existing_clip:
                self.db.execute(
                    """UPDATE clips SET start_sec = ?, end_sec = ?, score_overall = ?,
                       llm_mode_used = ?, mp4_path = ?, proposed_title = ?,
                       context_banner_2s = ?, pinned_comment_debate = ? WHERE id = ?""",
                    (start_sec, end_sec, overall, mode_used, mp4_path, title, ctx_banner, pinned, clip_id),
                )
            else:
                self.db.execute(
                    """INSERT INTO clips
                       (id, video_id, parent_long_clip_id, format_type, ab_variant, start_sec, end_sec,
                        score_chat, score_audio, score_visual, score_text, score_overall,
                        ypp_transform_score, phash_signature, llm_mode_used, risk_status,
                        mp4_path, thumbnail_path, proposed_title, context_banner_2s, pinned_comment_debate, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        clip_id,
                        video_id,
                        None,
                        fmt,
                        1,
                        start_sec,
                        end_sec,
                        0.0,
                        0.0,
                        0.0,
                        overall,
                        overall,
                        0,
                        "",
                        mode_used,
                        "pending",
                        mp4_path,
                        "",
                        title,
                        ctx_banner,
                        pinned,
                        now,
                    ),
                )
            synced_clips.append(self.db.fetch_one("SELECT * FROM clips WHERE id = ?", (clip_id,)))

        return {
            "video": self.db.fetch_one("SELECT * FROM videos WHERE id = ?", (video_id,)),
            "clips": synced_clips,
        }

    def record_manual_publication(
        self,
        *,
        project_id: str,
        clip_stem: str,
        platform: str,
        external_url: str = "",
        source_url: str = "",
    ) -> dict[str, Any]:
        """Registra publicação assistida/manual na tabela `publications` (alimenta o Épico 7 / P3)."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        video_id = f"studio-{project_id}"
        clip_id = f"{video_id}:{clip_stem}"

        if not self.db.fetch_one("SELECT id FROM videos WHERE id = ?", (video_id,)):
            self.db.execute(
                """INSERT INTO videos
                   (id, source_id, origin_type, source_url, game_slug, duration_seconds, workdir_path, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (video_id, None, "vod", str(source_url or ""), "", 0.0, "", "complete", now, now),
            )
        if not self.db.fetch_one("SELECT id FROM clips WHERE id = ?", (clip_id,)):
            self.db.execute(
                """INSERT INTO clips
                   (id, video_id, parent_long_clip_id, format_type, ab_variant, start_sec, end_sec,
                    score_chat, score_audio, score_visual, score_text, score_overall,
                    ypp_transform_score, phash_signature, llm_mode_used, risk_status,
                    mp4_path, thumbnail_path, proposed_title, context_banner_2s, pinned_comment_debate, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    clip_id, video_id, None, "short_9_16", 1, 0.0, 0.0,
                    0.0, 0.0, 0.0, 0.0, 0.0, 0, "", "manual", "approved",
                    "", "", clip_stem, "", "", now,
                ),
            )

        existing = self.db.fetch_one(
            "SELECT * FROM publications WHERE clip_id = ? AND platform = ? ORDER BY created_at DESC LIMIT 1",
            (clip_id, platform),
        )
        if existing:
            self.db.execute(
                "UPDATE publications SET status = ?, external_url = ?, publish_mode = ? WHERE id = ?",
                ("publicado", str(external_url or existing.get("external_url") or ""), "assisted_manual", existing["id"]),
            )
            return self.db.fetch_one("SELECT * FROM publications WHERE id = ?", (existing["id"],))  # type: ignore[return-value]

        return self.repos.publications.create_publication(
            clip_id=clip_id,
            platform=platform,
            publish_mode="assisted_manual",
            status="publicado",
            external_url=str(external_url or ""),
        )

    def list_project_publications(self, project_id: str) -> dict[str, dict[str, dict[str, Any]]]:
        """Retorna mapa clip_stem -> platform -> registro de publicação já gravado no banco."""
        prefix = f"studio-{project_id}:"
        rows = self.db.fetch_all(
            "SELECT * FROM publications WHERE clip_id LIKE ? ORDER BY created_at DESC",
            (prefix + "%",),
        )
        result: dict[str, dict[str, dict[str, Any]]] = {}
        for row in rows:
            cid = str(row.get("clip_id") or "")
            stem = cid[len(prefix):] if cid.startswith(prefix) else cid
            plat = str(row.get("platform") or "")
            if stem and plat and plat not in result.setdefault(stem, {}):
                result[stem][plat] = {
                    "id": row.get("id"),
                    "status": row.get("status"),
                    "publish_mode": row.get("publish_mode"),
                    "external_url": row.get("external_url") or "",
                    "created_at": row.get("created_at") or "",
                }
        return result
