"""Fachada unificada de domínio consumida pelo Painel Web e pelo Servidor MCP (AD-10)."""
from __future__ import annotations

import re
from pathlib import Path
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
        videos = [v for v in self.repos.videos.list_videos() if not v.get("archived_at")]
        n_clips = self.db.fetch_one("SELECT COUNT(*) AS n FROM clips WHERE archived_at IS NULL")["n"]
        arq_v = self.db.fetch_one("SELECT COUNT(*) AS n FROM videos WHERE archived_at IS NOT NULL")["n"]
        arq_c = self.db.fetch_one("SELECT COUNT(*) AS n FROM clips WHERE archived_at IS NOT NULL")["n"]
        return {
            "gpu_profile": detect_gpu_profile(),
            "total_sources": len(sources),
            "total_videos": len(videos),
            "total_clips": int(n_clips),
            "queued_videos": sum(1 for v in videos if v.get("status") == "queued"),
            "blocked_p1": sum(1 for v in videos if v.get("status") == "blocked_p1"),
            "arquivados": {"videos": int(arq_v), "clips": int(arq_c)},
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

    # ---- RiskShield (Épico 4): ponto único para painel web e MCP (AD-10) ----
    RISK_PLATFORMS = ("youtube_shorts", "youtube_long", "tiktok", "instagram_reels", "facebook_reels")

    def risk_cooldown_status(self, *, state_path: Any = None) -> dict[str, Any]:
        from picorte.risk_shield.cadence_guard import get_cooldown_status

        return get_cooldown_status(state_path=state_path)

    def risk_set_cooldown(
        self, platform: str, *, hours: Any = 48.0, reason: str = "Resfriamento anti-spam", state_path: Any = None
    ) -> dict[str, Any]:
        from picorte.risk_shield.cadence_guard import activate_cooldown

        plat = str(platform or "").strip().lower()
        if plat not in self.RISK_PLATFORMS:
            raise ValueError("Provide a valid platform for cooldown.")
        return activate_cooldown(plat, hours=48.0 if hours is None else hours, reason=reason, state_path=state_path)

    def risk_clear_cooldown(self, platform: str, *, state_path: Any = None) -> dict[str, Any]:
        from picorte.risk_shield.cadence_guard import clear_cooldown

        plat = str(platform or "").strip().lower()
        if plat not in self.RISK_PLATFORMS:
            raise ValueError("Provide a valid platform for cooldown.")
        return clear_cooldown(plat, state_path=state_path)

    def risk_pause_source(
        self, source_id: str, *, claim_type: str = "copyright_claim", details: str = "", reason: str = ""
    ) -> dict[str, Any]:
        from picorte.risk_shield.source_breaker import pause_source_globally

        sid = str(source_id or "").strip()
        if not sid:
            raise ValueError("Provide source_id.")
        return pause_source_globally(self.db, source_id=sid, claim_type=claim_type, details=details, reason=reason)

    def risk_audit_clip(self, **kwargs: Any) -> dict[str, Any]:
        from picorte.risk_shield.orchestrator import audit_clip_risk

        return audit_clip_risk(self.db, **kwargs)

    def risk_game_policy(self, game_slug: str) -> dict[str, Any]:
        from picorte.risk_shield.policy_gate import sync_publisher_policies

        slug = str(game_slug or "").strip().lower()
        pol = self.repos.policies.get_by_game(slug)
        if pol is None:
            sync_publisher_policies(self.db)
            pol = self.repos.policies.get_by_game(slug)
        return {"game_slug": slug, "policy": pol}

    def update_source_permission(
        self, source_id: str, permission_status: str, evidence_url: str | None = None
    ) -> dict[str, Any]:
        return self.repos.sources.update_permission(
            source_id, permission_status, evidence_url=evidence_url
        )

    def enqueue_video(self, *, source_url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fila única (B5): cria o projeto real na fila do Estúdio, o mesmo caminho do painel."""
        from picorte.services import estudio_conexao

        return estudio_conexao.enfileirar_no_estudio([source_url], options)

    def list_clips(self, video_id: str | None = None) -> list[dict[str, Any]]:
        return self.repos.clips.list_clips(video_id=video_id)

    def _fonte_do_portao(self, portao: Any) -> str | None:
        """B1: id da fonte aprovada pelo portão P1; se o id veio de outro banco, casa pela @handle."""
        portao = portao if isinstance(portao, dict) else {}
        sid = str(portao.get("source_id") or "").strip()
        if sid and self.db.fetch_one("SELECT id FROM sources WHERE id = ?", (sid,)):
            return sid
        handle = str(portao.get("channel_handle") or "").strip().lower()
        if handle:
            linha = self.db.fetch_one("SELECT id FROM sources WHERE lower(channel_handle) = ?", (handle,))
            if linha:
                return str(linha["id"])
        return None

    def sync_studio_project(
        self,
        project_state: dict[str, Any],
        *,
        segments: list[dict[str, Any]] | None = None,
        outputs: list[str] | None = None,
        workdir: Any = "",
        duration_seconds: float = 0.0,
    ) -> dict[str, Any]:
        """Espelha um projeto nas tabelas videos e clips gravando só o que foi medido (história 6.4)."""
        from datetime import datetime, timezone

        from picorte.services.sinais import miniatura_do_corte, sinais_medidos, veredito_do_corte

        now = datetime.now(timezone.utc).isoformat()
        project_id = str(project_state["id"])
        video_id = f"studio-{project_id}"
        source_url = str(project_state.get("source") or project_state.get("video") or "")
        origin_type = "vod" if re.match(r"^https?://", source_url, re.I) else "local_file"
        status = str(project_state.get("status") or "queued")
        options = project_state.get("options") or {}
        aspect = options.get("aspect", "9:16")
        fmt = "short_9_16" if aspect == "9:16" else ("long_16_9" if aspect == "16:9" else "square_1_1")
        ai_mode = str(options.get("ai_mode") or ("ollama" if options.get("llm") else "heuristic"))
        source_id = self._fonte_do_portao(project_state.get("source_gate"))  # B1
        game_slug = str((project_state.get("source_meta") or {}).get("detected_game") or "")

        self.db.execute(
            """INSERT INTO videos (id, source_id, origin_type, source_url, game_slug, duration_seconds,
                                   workdir_path, status, archived_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
               ON CONFLICT(id) DO UPDATE SET source_id = excluded.source_id, origin_type = excluded.origin_type,
                 source_url = excluded.source_url, game_slug = excluded.game_slug,
                 duration_seconds = excluded.duration_seconds, workdir_path = excluded.workdir_path,
                 status = excluded.status, archived_at = NULL, updated_at = excluded.updated_at""",
            (video_id, source_id, origin_type, source_url, game_slug, float(duration_seconds), str(workdir),
             status, now, now),
        )

        por_prefixo = {Path(o).name.split("-", 1)[0]: str(o) for o in (outputs or [])}
        synced_clips = []
        for idx, seg in enumerate(segments or [], 1):
            seg_id = str(seg.get("id") or f"{idx:03}")
            clip_id = f"{video_id}:{seg_id}"
            mp4_path = por_prefixo.get(seg_id, "")
            s = sinais_medidos(seg)  # B2
            self.db.execute(
                """INSERT INTO clips (id, video_id, parent_long_clip_id, format_type, ab_variant, start_sec, end_sec,
                     score_chat, score_audio, score_visual, score_text, score_overall, ypp_transform_score,
                     phash_signature, llm_mode_used, risk_status, mp4_path, thumbnail_path, proposed_title,
                     context_banner_2s, pinned_comment_debate, archived_at, created_at)
                   VALUES (?, ?, NULL, ?, 1, ?, ?, ?, ?, ?, ?, ?, NULL, '', ?, 'pending', ?, ?, ?, ?, ?, NULL, ?)
                   ON CONFLICT(id) DO UPDATE SET format_type = excluded.format_type, start_sec = excluded.start_sec,
                     end_sec = excluded.end_sec, score_chat = excluded.score_chat, score_audio = excluded.score_audio,
                     score_visual = excluded.score_visual, score_text = excluded.score_text,
                     score_overall = excluded.score_overall, llm_mode_used = excluded.llm_mode_used,
                     mp4_path = excluded.mp4_path, thumbnail_path = excluded.thumbnail_path,
                     proposed_title = excluded.proposed_title, context_banner_2s = excluded.context_banner_2s,
                     pinned_comment_debate = excluded.pinned_comment_debate, archived_at = NULL""",
                (clip_id, video_id, fmt, float(seg.get("start") or 0.0), float(seg.get("end") or 0.0),
                 s["score_chat"], s["score_audio"], s["score_visual"], s["score_text"],
                 float(seg.get("overall") or 0.0), str(seg.get("llm_mode_used") or ai_mode), mp4_path,
                 miniatura_do_corte(mp4_path) if mp4_path else "",
                 str(seg.get("proposed_title") or seg.get("hook") or ""), str(seg.get("context_banner_2s") or ""),
                 str(seg.get("pinned_comment_debate") or ""), now),
            )
            veredito = veredito_do_corte(mp4_path) if mp4_path else None  # B3
            if veredito:
                self.db.execute(
                    "UPDATE clips SET risk_status = ?, ypp_transform_score = ?, phash_signature = ? WHERE id = ?",
                    (veredito["risk_status"], veredito["ypp_transform_score"], veredito["phash_signature"], clip_id),
                )
            synced_clips.append(self.db.fetch_one("SELECT * FROM clips WHERE id = ?", (clip_id,)))

        return {"video": self.db.fetch_one("SELECT * FROM videos WHERE id = ?", (video_id,)), "clips": synced_clips}

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
        prefixo = str(clip_stem).split("-", 1)[0]
        do_sync = f"{video_id}:{prefixo}"
        clip_id = do_sync if self.db.fetch_one("SELECT id FROM clips WHERE id = ?", (do_sync,))             else f"{video_id}:{clip_stem}"

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
                    None, None, None, None, 0.0, None, "", "manual", "approved",
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
