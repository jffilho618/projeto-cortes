"""Story 4.2 — Guardião de Originalidade (YPP >= 70 + TikTok FYP) e Deduplicação Perceptual pHash + Texto."""
from __future__ import annotations

import re
from typing import Any
import unicodedata

import cv2
import numpy as np

from picorte.db.connection import Database


def _norm_tokens(text: str | None) -> list[str]:
    raw = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return [t for t in re.findall(r"[a-z0-9]+", raw.lower()) if len(t) >= 2]


def _ngrams(tokens: list[str], n: int = 3) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def text_similarity(text_a: str | None, text_b: str | None) -> float:
    ta, tb = _norm_tokens(text_a), _norm_tokens(text_b)
    if not ta or not tb:
        return 0.0
    ga, gb = _ngrams(ta, 3), _ngrams(tb, 3)
    if not ga or not gb:
        sa, sb = set(ta), set(tb)
        return len(sa & sb) / float(max(1, len(sa | sb)))
    return len(ga & gb) / float(max(1, len(ga | gb)))


def _frame_dhash_64(frame: np.ndarray) -> int:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]
    bits = 0
    for val in diff.flatten():
        bits = (bits << 1) | int(bool(val))
    return bits


PHASH_MAX_FRAMES = 16
PHASH_MAX_SHIFT = 3  # tolera o mesmo lance cortado 2–3s antes/depois (a 1 fps)


def compute_video_phash(frames: list[np.ndarray]) -> str:
    """Calcula assinatura perceptual (dHash multi-frame, até 16 frames ~1/s) em hexadecimal estável."""
    valid = [f for f in frames if f is not None and getattr(f, "size", 0) > 0]
    if not valid:
        return ""
    if len(valid) > PHASH_MAX_FRAMES:
        idxs = [int(round(i * (len(valid) - 1) / (PHASH_MAX_FRAMES - 1))) for i in range(PHASH_MAX_FRAMES)]
        sample = [valid[i] for i in idxs]
    else:
        sample = valid
    hashes = [f"{_frame_dhash_64(fr):016x}" for fr in sample]
    return ":".join(hashes)


def phash_similarity(sig_a: str | None, sig_b: str | None) -> float:
    """Retorna similaridade [0.0, 1.0] baseada na distância de Hamming média entre assinaturas pHash."""
    if not sig_a or not sig_b:
        return 0.0
    parts_a = [p for p in str(sig_a).split(":") if len(p) == 16]
    parts_b = [p for p in str(sig_b).split(":") if len(p) == 16]
    if not parts_a or not parts_b:
        return 0.0
    try:
        ha = [int(x, 16) for x in parts_a]
        hb = [int(x, 16) for x in parts_b]
    except ValueError:
        return 0.0
    n_min = min(len(ha), len(hb))
    min_overlap = min(n_min, max(3, n_min - PHASH_MAX_SHIFT))
    best = 0.0
    # Melhor alinhamento entre deslocamentos de até ±3 frames (mesmo lance com início levemente diferente)
    for shift in range(-PHASH_MAX_SHIFT, PHASH_MAX_SHIFT + 1):
        sims = [
            1.0 - ((ha[i] ^ hb[i + shift]).bit_count() / 64.0)
            for i in range(len(ha))
            if 0 <= i + shift < len(hb)
        ]
        if len(sims) >= min_overlap:
            best = max(best, sum(sims) / len(sims))
    return best


def detect_platform_watermark(frames: list[np.ndarray], *, min_fraction: float = 0.6) -> dict[str, Any]:
    """Detecta marca d'água do TikTok (logo ciano #25F4EE + rosa #FE2C55 lado a lado) nos cantos.

    Conservador de propósito: overlays estáticos de live (logo do streamer, alertas) NÃO disparam,
    porque exige a assinatura de cor dupla do TikTok, persistente na maioria dos frames.
    """
    valid = [f for f in frames if f is not None and getattr(f, "size", 0) > 0 and f.ndim == 3]
    if len(valid) < 3:
        return {"detected": False, "frames_flagged": 0, "frames_checked": len(valid)}
    flagged = 0
    for fr in valid:
        h, w = fr.shape[:2]
        ch, cw = max(8, int(h * 0.16)), max(8, int(w * 0.18))
        corners = (fr[:ch, :cw], fr[:ch, w - cw:], fr[h - ch:, :cw], fr[h - ch:, w - cw:])
        for corner in corners:
            hsv = cv2.cvtColor(corner, cv2.COLOR_BGR2HSV)
            hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
            bright = (sat > 120) & (val > 150)
            cyan = float(np.mean(bright & (hue >= 80) & (hue <= 100)))
            pink = float(np.mean(bright & ((hue >= 165) | (hue <= 5))))
            if cyan >= 0.005 and pink >= 0.005:
                flagged += 1
                break
    return {
        "detected": flagged >= max(3, int(np.ceil(min_fraction * len(valid)))),
        "frames_flagged": flagged,
        "frames_checked": len(valid),
    }


def measure_max_static_seconds(frames: list[np.ndarray], *, fps_sampled: float = 1.0) -> float:
    """Estima a maior sequência contínua (em segundos) de tela congelada/estática (penalizada no TikTok FYP)."""
    valid = [f for f in frames if f is not None and getattr(f, "size", 0) > 0]
    if len(valid) < 2 or fps_sampled <= 0:
        return 0.0
    step = 1.0 / float(fps_sampled)
    max_run = 0.0
    cur_run = 0.0
    prev = cv2.resize(cv2.cvtColor(valid[0], cv2.COLOR_BGR2GRAY) if valid[0].ndim == 3 else valid[0], (96, 96))
    for fr in valid[1:]:
        cur = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr, (96, 96))
        mad = float(np.mean(np.abs(cur.astype(np.float32) - prev.astype(np.float32))))
        if mad < 1.8:
            cur_run += step
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0.0
        prev = cur
    return round(max_run, 2)


def evaluate_ypp_and_dedup(
    db: Database,
    *,
    frames: list[np.ndarray],
    transcript_text: str = "",
    format_type: str = "short_9_16",
    has_facecam_split: bool = False,
    has_dynamic_captions: bool = False,
    has_context_banner: bool = False,
    has_native_metadata: bool = False,
    has_cold_open: bool = False,
    audio_clean: bool = True,
    watermark_detected: bool = False,
    fps_sampled: float = 1.0,
    min_ypp_score: int = 70,
    dup_threshold: float = 0.85,
    ab_variant: int = 1,
    parent_clip_id: str | None = None,
    current_clip_id: str | None = None,
    family_clip_ids: Any = None,
) -> dict[str, Any]:
    """Calcula YPP Score (YouTube), TikTok Originality Score, Audit Trail e Deduplicação Híbrida (pHash + texto).

    `family_clip_ids` (3.7.3): Short, versão TikTok e Longo do MESMO momento são família, não reupload — os
    cortes da família não entram como referência de duplicata.
    """
    family = {str(x) for x in (family_clip_ids or [])}
    max_static_sec = measure_max_static_seconds(frames, fps_sampled=fps_sampled)
    phash_sig = compute_video_phash(frames)
    n_valid_frames = len([f for f in frames if f is not None and getattr(f, "size", 0) > 0])
    watermark_detected = bool(watermark_detected) or detect_platform_watermark(frames)["detected"]

    # 1) Pontuação YPP (YouTube — 0..100)
    layers: dict[str, int] = {
        "facecam_or_reframe": 20 if has_facecam_split else (15 if format_type == "long_16_9" else 0),
        "dynamic_captions_ass": 20 if has_dynamic_captions else 0,
        "context_banner_or_chapters": 15 if has_context_banner else 0,
        "native_metadata_credit": 15 if has_native_metadata else 0,
        # Sem frames não há como provar ritmo: só ganha os pontos com Cold Open ou frames medidos.
        "pacing_or_cold_open": 15 if (has_cold_open or (n_valid_frames >= 2 and max_static_sec < 4.0)) else 0,
        "clean_audio_no_watermark": 15 if (audio_clean and not watermark_detected) else 0,
    }
    ypp_score = sum(layers.values())

    # 2) Pontuação TikTok FYP Originality (penaliza mais forte telas paradas > 4s e marcas d'água)
    tiktok_score = ypp_score
    tiktok_penalties: list[str] = []
    if max_static_sec >= 4.0:
        tiktok_score -= 25
        tiktok_penalties.append(f"static_screen_{max_static_sec:.1f}s")
    if watermark_detected:
        tiktok_score -= 40
        tiktok_penalties.append("external_watermark")
    if not has_facecam_split:
        tiktok_score -= 10
        tiktok_penalties.append("no_creator_presence")
    tiktok_score = max(0, min(100, tiktok_score))

    # 3) Deduplicação Híbrida contra tabela `clips` no DB (exceção explícita para Reciclagem A/B do Épico 7)
    is_ab_recycle = (
        int(ab_variant or 1) > 1
        and bool(parent_clip_id)
        and db.fetch_one("SELECT id FROM clips WHERE id = ?", (str(parent_clip_id),)) is not None
    )
    is_duplicate = False
    duplicate_clip_id: str | None = None
    best_sim = 0.0

    if not is_ab_recycle:
        existing_clips = db.fetch_all(
            "SELECT id, phash_signature, proposed_title, context_banner_2s FROM clips "
            "WHERE COALESCE(risk_status, '') <> 'hard_block'"
        )
        for row in existing_clips:
            cid = str(row.get("id") or "")
            if (current_clip_id and cid == current_clip_id) or cid in family:
                continue
            p_sim = phash_similarity(phash_sig, row.get("phash_signature"))
            row_txt = f"{row.get('proposed_title') or ''} {row.get('context_banner_2s') or ''}"
            t_sim = text_similarity(transcript_text, row_txt)
            # Se pHash existir, usa combinação conservadora; se só texto existir, exige alta similaridade textual
            combined_sim = max(p_sim, t_sim) if (p_sim >= dup_threshold or (p_sim >= 0.72 and t_sim >= 0.72)) else (
                t_sim if not row.get("phash_signature") else (0.7 * p_sim + 0.3 * t_sim)
            )
            if combined_sim > best_sim:
                best_sim = combined_sim
            if combined_sim > dup_threshold:
                is_duplicate = True
                duplicate_clip_id = cid
                break

    reasons: list[str] = []
    status = "pass"
    if is_duplicate:
        status = "hard_block"
        reasons.append(f"Duplicata perceptual detectada (similaridade={best_sim:.2f} > {dup_threshold}, clip_id={duplicate_clip_id}).")
    if watermark_detected:
        status = "hard_block"
        reasons.append("Marca d'água externa detectada no vídeo (viola P2).")
    if ypp_score < min_ypp_score:
        status = "hard_block"
        reasons.append(f"YPP Transformation Score abaixo do mínimo ({ypp_score} < {min_ypp_score}).")

    tiktok_status = "hard_block" if status == "hard_block" else (
        "human_review" if tiktok_score < min_ypp_score else "pass"
    )

    return {
        "gate": "ypp_and_dedup",
        "status": status,
        "tiktok_status": tiktok_status,
        "ypp_score": int(ypp_score),
        "tiktok_originality_score": int(tiktok_score),
        "max_static_seconds": max_static_sec,
        "watermark_detected": bool(watermark_detected),
        "phash_signature": phash_sig,
        "is_duplicate": is_duplicate,
        "duplicate_clip_id": duplicate_clip_id,
        "duplicate_similarity": round(best_sim, 3),
        "ab_recycle_allowed": is_ab_recycle,
        "reasons": reasons,
        "audit_trail": {
            "format_type": format_type,
            "layers": layers,
            "tiktok_penalties": tiktok_penalties,
        },
    }
