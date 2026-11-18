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
