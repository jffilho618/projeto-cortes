"""P2 (code review Épico 4) — Liga o RiskShield ao pipeline real: cada corte renderizado ganha veredito no .meta.json.

O Pacote do Dia (`export_daily_bundle`) só exporta cortes com veredito; sem veredito = não auditado = não sai.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np

from picorte.db.connection import Database

from .music_surgeon import run_selective_music_surgery
from .orchestrator import audit_clip_risk

EXPORTABLE_STATUSES = {"pass", "auto_fixed", "human_review"}
SURGERY_SAMPLE_RATE = 44100  # taxa nativa do htdemucs: evita reamostragem dupla da voz


def clean_music_in_render(
    mp4_path: Path | str,
    *,
    separator_runner: Any = None,
    cache_dir: Path | str | None = None,
) -> dict[str, Any]:
    """W4: detecta música no corte renderizado e, se houver, troca o áudio pela voz limpa (Demucs).

    Só remonta o .mp4 quando a cirurgia foi aplicada; sem música o arquivo fica intacto. Qualquer falha
    vira `NEEDS_HUMAN_AUDIO_CHECK` (revisão humana) e nunca derruba o render.
    Nota: quando há cirurgia o áudio final sai mono (a separação é feita em mono).
    """
    import subprocess
    import tempfile

    from picorte.config import resolve_cli_binary

    mp4 = Path(mp4_path)
    ffmpeg = resolve_cli_binary("ffmpeg") or "ffmpeg"
    try:
        with tempfile.TemporaryDirectory(prefix="picorte_w4_") as td:
            tmp = Path(td)
            src_wav = tmp / "clip_audio.wav"
            subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", str(mp4), "-vn", "-ac", "1",
                 "-ar", str(SURGERY_SAMPLE_RATE), "-c:a", "pcm_s16le", str(src_wav)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            clean_wav = tmp / "clip_clean.wav"
            res = dict(run_selective_music_surgery(
                src_wav, clean_wav, separator_runner=separator_runner, cache_dir=cache_dir))
            if res.get("surgery_applied") and clean_wav.is_file():
                remuxed = tmp / "remuxed.mp4"
                subprocess.run(
                    [ffmpeg, "-y", "-loglevel", "error", "-i", str(mp4), "-i", str(clean_wav),
                     "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                     "-shortest", str(remuxed)],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                remuxed.replace(mp4)
    except Exception as exc:
        return {
            "gate": "music_surgeon",
            "status": "human_review",
            "code": "NEEDS_HUMAN_AUDIO_CHECK",
            "surgery_applied": False,
            "reason": f"Cirurgia de música falhou ({type(exc).__name__}: {exc}).",
        }
    res.pop("audio_path", None)
    return res


def _format_type(aspect: str | None) -> str:
    if aspect == "9:16":
        return "short_9_16"
    if aspect == "16:9":
        return "long_16_9"
    return "square_1_1"


def sample_clip_frames(mp4_path: Path | str | None, *, seconds: float = 15.0, fps: float = 1.0) -> list[np.ndarray]:
    """Amostra frames do corte renderizado (0–15s a 1 fps) para Selo Verde visual, React Guard e pHash."""
    if not mp4_path or not Path(mp4_path).is_file():
        return []
    import cv2

    cap = cv2.VideoCapture(str(mp4_path))
    frames: list[np.ndarray] = []
    try:
        for i in range(int(seconds * fps)):
            cap.set(cv2.CAP_PROP_POS_MSEC, (i / fps) * 1000.0)
            ok, fr = cap.read()
            if not ok or fr is None:
                break
            frames.append(fr)
    finally:
        cap.release()
    return frames


def _compact(verdict: dict[str, Any]) -> dict[str, Any]:
    gates = {}
    for name, g in (verdict.get("gates") or {}).items():
        g = g or {}
        entry = {"status": g.get("status", "pass")}
        for key in ("code", "reason", "reasons", "permission_basis"):
            if g.get(key):
                entry[key] = g[key]
        gates[name] = entry
    return {
        "overall_status": verdict["overall_status"],
        "per_platform": {k: v["status"] for k, v in (verdict.get("per_platform") or {}).items()},
        "gates": gates,
        "ypp_score": verdict.get("ypp_score"),
        "tiktok_originality_score": verdict.get("tiktok_originality_score"),
        "phash_signature": verdict.get("phash_signature") or "",
        "auto_fixes_applied": verdict.get("auto_fixes_applied") or [],
        "checked_at": verdict.get("checked_at"),
    }


def attach_risk_verdict(
    db: Database,
    *,
    meta_path: Path | str,
    source_id: str | None,
    seg: dict[str, Any],
    words: list[dict[str, Any]],
    mp4_path: Path | str | None,
    options: dict[str, Any],
    game_slug: str = "",
    music_result: dict[str, Any] | None = None,
    cadence_state_path: Path | str | None = None,
    clip_id: str | None = None,
) -> dict[str, Any]:
    """Audita o corte nos portões P1 e grava `risk_status` + `risk_verdict` no .meta.json (falha fechada)."""
    mp = Path(meta_path)
    meta = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else {}
    layout = str(options.get("layout") or "single")
    try:
        verdict = _compact(audit_clip_risk(
            db,
            source_id=source_id,
            game_slug=game_slug,
            title=str(meta.get("title") or meta.get("proposed_title") or ""),
            description=str(meta.get("description") or ""),
            hashtags=list(meta.get("hashtags") or []),
            context_banner_2s=str(seg.get("context_banner_2s") or ""),
            pinned_comment=str(seg.get("pinned_comment_debate") or ""),
            words=words,
            clip_start=float(seg.get("start") or 0.0),
            clip_end=float(seg.get("end") or 0.0),
            frames=sample_clip_frames(mp4_path),
            fps_sampled=1.0,
            format_type=_format_type(options.get("aspect")),
            has_facecam_split=layout in {"games", "split"},
            has_dynamic_captions=True,  # legenda .ass é sempre queimada no render
            has_context_banner=bool(seg.get("context_banner_2s")),
            has_native_metadata=bool(seg.get("proposed_title")),
            # 3.7.1: só conta o teaser que foi de fato colado no vídeo (fecha o W3)
            has_cold_open=bool((meta.get("cold_open") or seg.get("cold_open") or {}).get("rendered")),
            music_result=music_result,
            cadence_state_path=cadence_state_path,
            clip_id=clip_id,  # a deduplicação não compara o corte com ele mesmo
        ))
    except Exception as exc:  # falha fechada: sem veredito válido, o corte não sai no Pacote do Dia
        verdict = {
            "overall_status": "audit_error",
            "error": f"{type(exc).__name__}: {exc}",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    meta["risk_status"] = verdict["overall_status"]
    meta["risk_verdict"] = verdict
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return verdict
