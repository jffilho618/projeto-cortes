"""Escudo Anti-Strike, Anti-Desmonetização e Anti-Bloqueio do Picorte (Épico 4 — P1 Inegociável)."""
from __future__ import annotations

from .cadence_guard import activate_cooldown, check_cadence, clear_cooldown, get_cooldown_status
from .copy_guard import audit_and_sanitize_copy
from .green_seal_15s import (
    apply_audio_bleeps,
    audit_visual_green_seal_15s,
    plan_green_seal_audio_and_captions,
    score_frame_visual_safety,
)
from .music_surgeon import detect_music_intervals, run_selective_music_surgery
from .orchestrator import audit_clip_risk
from .policy_gate import (
    ALLOWED_PERMISSION_STATUSES,
    BLOCKED_PERMISSION_STATUSES,
    PolicyViolationError,
    assert_can_export,
    assert_can_ingest,
    evaluate_candidate_policy,
    load_publisher_policies,
    sync_publisher_policies,
    sync_registry_sources,
)
from .react_guard import detect_dangerous_react
from .source_breaker import pause_source_globally
from .ypp_guard import compute_video_phash, evaluate_ypp_and_dedup

__all__ = [
    "ALLOWED_PERMISSION_STATUSES",
    "BLOCKED_PERMISSION_STATUSES",
    "PolicyViolationError",
    "activate_cooldown",
    "apply_audio_bleeps",
    "assert_can_export",
    "assert_can_ingest",
    "audit_and_sanitize_copy",
    "audit_clip_risk",
    "audit_visual_green_seal_15s",
    "check_cadence",
    "clear_cooldown",
    "compute_video_phash",
    "detect_dangerous_react",
    "detect_music_intervals",
    "evaluate_candidate_policy",
    "evaluate_ypp_and_dedup",
    "get_cooldown_status",
    "load_publisher_policies",
    "pause_source_globally",
    "plan_green_seal_audio_and_captions",
    "run_selective_music_surgery",
    "score_frame_visual_safety",
    "sync_publisher_policies",
    "sync_registry_sources",
]
