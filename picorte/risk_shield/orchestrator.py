"""Story 4.5 — Orquestrador RiskShield: contrato canônico RiskVerdict por rede + persistência no DB."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from picorte.db.connection import Database

from .cadence_guard import check_cadence
from .copy_guard import audit_and_sanitize_copy
from .green_seal_15s import audit_visual_green_seal_15s, plan_green_seal_audio_and_captions
from .policy_gate import PolicyViolationError, assert_can_export, evaluate_candidate_policy
from .react_guard import detect_dangerous_react
from .ypp_guard import evaluate_ypp_and_dedup

PLATFORMS = ("youtube_shorts", "tiktok", "instagram_reels", "facebook_reels")
LONG_PLATFORMS = ("youtube_long",)
_RANK = {"pass": 0, "auto_fixed": 1, "human_review": 2, "block": 3, "hard_block": 4}


def _rank(status: str) -> int:
    # Status desconhecido nunca é tratado como "pass": vai para revisão humana.
    return _RANK.get(status, _RANK["human_review"])


def _worst_status(statuses: list[str]) -> str:
    best = "pass"
    for s in statuses:
        if _rank(s) > _rank(best):
            best = s
    return "hard_block" if best == "block" else best


def motivos_da_rede(plat: str, copy_res: dict[str, Any], cad_res: dict[str, Any], ypp_res: dict[str, Any]) -> list[str]:
    """O que é próprio desta rede (os portões gerais têm motivo próprio): cópia, cadência e originalidade do TikTok."""
    motivos = []
    if copy_res.get("status") == "human_review":
        for w in copy_res.get("ad_friendly_warnings") or []:
            motivos.append(f'cópia com termo que tira anúncio: "{w.get("term")}" (sugestão: {w.get("suggestion")})')
    if cad_res.get("status") == "block":
        motivos.append(str(cad_res.get("reason") or "cadência: postar agora nesta rede passa do limite"))
    if plat == "tiktok" and ypp_res.get("tiktok_status") == "human_review":
        motivos.append(f"originalidade TikTok {ypp_res.get('tiktok_originality_score')} abaixo do mínimo")
    return motivos


def _source_of_clip(db: Database, clip_id: str | None) -> str | None:
    if not clip_id:
        return None
    row = db.fetch_one(
        "SELECT v.source_id AS source_id FROM clips c JOIN videos v ON v.id = c.video_id WHERE c.id = ?",
        (clip_id,),
    )
    return (row or {}).get("source_id") or None


def audit_clip_risk(
    db: Database,
    *,
    source_id: str | None = None,
    channel_handle: str | None = None,
    clip_id: str | None = None,
    game_slug: str = "",
    title: str = "",
    description: str = "",
    hashtags: list[str] | None = None,
    context_banner_2s: str = "",
    pinned_comment: str = "",
    source_credit: str = "",
    words: list[dict[str, Any]] | None = None,
    clip_start: float = 0.0,
    clip_end: float = 30.0,
    cold_open_plan: dict[str, Any] | None = None,
    frames: list[np.ndarray] | None = None,
    fps_sampled: float = 1.0,
    format_type: str = "short_9_16",
    has_facecam_split: bool = False,
    has_dynamic_captions: bool = False,
    has_context_banner: bool = False,
    has_native_metadata: bool = False,
    has_cold_open: bool = False,
    audio_clean: bool = True,
    watermark_detected: bool = False,
    music_result: dict[str, Any] | None = None,
    ab_variant: int = 1,
    parent_clip_id: str | None = None,
    family_clip_ids: Any = None,
    cadence_profile: str = "warmup",
    cadence_state_path: Path | str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Executa todos os portões P1 do Épico 4 e retorna RiskVerdict granular por rede."""
    now_iso = datetime.now(timezone.utc).isoformat()
    gates: dict[str, Any] = {}
    auto_fixes: list[str] = []

    # 1) Portão da Fonte (Pre-Export) — imutável: corte sem fonte identificável nunca sai.
    source_id = source_id or _source_of_clip(db, clip_id)
    if source_id or channel_handle:
        try:
            src_res = assert_can_export(db, source_id=source_id, channel_handle=channel_handle)
            gates["source_permission"] = {
                "status": "pass",
                "permission_status": src_res["permission_status"],
                "permission_basis": src_res["source"].get("permission_basis") or "explicita",
            }
        except PolicyViolationError as exc:
            gates["source_permission"] = {"status": "hard_block", "code": exc.code, "reason": str(exc)}
    else:
        gates["source_permission"] = {
            "status": "hard_block",
            "code": "source_unlinked",
            "reason": "[P1:pre_export] Corte sem fonte vinculada (source_id/channel_handle/clip). Nada sai.",
        }

    # 2) Política da Publisher / Jogo
    tx_text = " ".join(str(w.get("word") or "") for w in (words or []))
    pol_res = evaluate_candidate_policy(
        db, game_slug=game_slug, title=title, transcript_text=tx_text, today=today
    )
    gates["publisher_policy"] = pol_res

    # 3) Selo Verde 15s (Áudio/Legenda + Cold Open + Visão)
    gs_audio = plan_green_seal_audio_and_captions(
        words or [], clip_start=clip_start, clip_end=clip_end, cold_open_plan=cold_open_plan
    )
    if gs_audio["bleep_intervals"]:
        auto_fixes.append(f"green_seal_bleep:{len(gs_audio['bleep_intervals'])}")
    if gs_audio["cold_open_hits"]:
        auto_fixes.append(f"cold_open_profanity_guarded:{len(gs_audio['cold_open_hits'])}")

    sample_frames = list(frames or [])
    gs_vis = audit_visual_green_seal_15s(sample_frames, fps_sampled=fps_sampled)
    gates["green_seal_15s"] = {
        "status": _worst_status([gs_audio["status"], gs_vis["status"]]),
        "reasons": list(gs_audio.get("reasons") or []) + list(gs_vis.get("reasons") or []),
        "audio": gs_audio,
        "visual": gs_vis,
    }

    # 4) React Perigoso
    react_res = detect_dangerous_react(sample_frames, fps_sampled=fps_sampled, transcript_text=tx_text)
    gates["react_guard"] = react_res

    # 5) Cirurgia de Música (se já executada; jogo com música licenciada exige checagem)
    if music_result is not None:
        gates["music_surgeon"] = music_result
        if music_result.get("surgery_applied"):
            auto_fixes.append("demucs_selective_music_surgery")
    elif pol_res.get("requires_music_check"):
        gates["music_surgeon"] = {
            "status": "human_review",
            "code": "NEEDS_HUMAN_AUDIO_CHECK",
            "reason": f"Jogo '{game_slug}' tem música licenciada e a cirurgia Demucs não rodou neste corte.",
        }

    # 6) Originalidade YPP + TikTok FYP + Deduplicação pHash
    ypp_res = evaluate_ypp_and_dedup(
        db,
        frames=sample_frames,
        transcript_text=f"{title} {tx_text}",
        format_type=format_type,
        has_facecam_split=has_facecam_split,
        has_dynamic_captions=has_dynamic_captions,
        has_context_banner=has_context_banner,
        has_native_metadata=has_native_metadata,
        has_cold_open=has_cold_open,
        audio_clean=audio_clean,
        watermark_detected=watermark_detected,
        fps_sampled=fps_sampled,
        ab_variant=ab_variant,
        parent_clip_id=parent_clip_id,
        current_clip_id=clip_id,
        family_clip_ids=family_clip_ids,  # 3.7.3: Short/TikTok/Longo do mesmo momento não são duplicata
    )
    gates["ypp_and_dedup"] = ypp_res

    # 7) Avaliação granular por plataforma (Copy Hygiene + Cadência + TikTok Originality)
    base_core_status = _worst_status([
        gates["source_permission"]["status"],
        pol_res["status"],
        gates["green_seal_15s"]["status"],
        react_res["status"],
        ypp_res["status"],
        (gates.get("music_surgeon") or {}).get("status", "pass"),
    ])

    per_platform: dict[str, dict[str, Any]] = {}
    platforms = LONG_PLATFORMS if str(format_type).startswith("long") else PLATFORMS
    for plat in platforms:
        copy_res = audit_and_sanitize_copy(
            platform=plat,
            title=title,
            description=description,
            hashtags=hashtags,
            context_banner_2s=context_banner_2s,
            pinned_comment=pinned_comment,
            source_credit=source_credit,
        )
        if copy_res["auto_fixed"]:
            auto_fixes.append(f"copy_sanitized:{plat}")
        cad_res = check_cadence(
            db, platform=plat, profile=cadence_profile, state_path=cadence_state_path
        )
        plat_statuses = [base_core_status, copy_res["status"]]
        if plat == "tiktok":
            plat_statuses.append(ypp_res["tiktok_status"])
        if cad_res["status"] == "block":
            plat_statuses.append("human_review")  # bloqueia postagem imediata, mas permite agendar
        per_platform[plat] = {
            "status": _worst_status(plat_statuses),
            "reasons": motivos_da_rede(plat, copy_res, cad_res, ypp_res),
            "copy_audit": copy_res,
            "cadence": cad_res,
        }

    overall_status = _worst_status([base_core_status, *(p["status"] for p in per_platform.values())])
    if overall_status == "pass" and auto_fixes:
        overall_status = "auto_fixed"

    # 8) Persiste resultado em `clips` quando `clip_id` existir
    if clip_id and db.fetch_one("SELECT id FROM clips WHERE id = ?", (clip_id,)):
        db.execute(
            "UPDATE clips SET risk_status = ?, ypp_transform_score = ?, phash_signature = ? WHERE id = ?",
            (overall_status, int(ypp_res["ypp_score"]), str(ypp_res["phash_signature"]), clip_id),
        )

    return {
        "overall_status": overall_status,
        "ypp_score": ypp_res["ypp_score"],
        "tiktok_originality_score": ypp_res["tiktok_originality_score"],
        "phash_signature": ypp_res["phash_signature"],
        "per_platform": per_platform,
        "gates": gates,
        "auto_fixes_applied": list(dict.fromkeys(auto_fixes)),
        "audit_trail": ypp_res["audit_trail"],
        "checked_at": now_iso,
    }
