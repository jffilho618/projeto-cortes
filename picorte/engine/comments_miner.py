"""Mineração Opcional de Comentários com Timestamp do YouTube (Épico 3.5 — Story 3.5.4).

Respeita o portão P1: NUNCA minera vídeos de fontes 'desconhecida' ou 'lista_negra'.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any, Callable
from picorte.config import ytdlp_base_cmd

BLOCKED_PERMISSION_STATUSES = {"desconhecida", "lista_negra", "pausada_por_claim", "expirada"}
TIMESTAMP_RE = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")


def parse_timestamp_to_seconds(ts_str: str) -> float | None:
    """Converte 'mm:ss' ou 'hh:mm:ss' em segundos float."""
    match = TIMESTAMP_RE.fullmatch((ts_str or "").strip())
    if not match:
        return None
    h_str, m_str, s_str = match.groups()
    hours = int(h_str) if h_str is not None else 0
    minutes = int(m_str)
    seconds = int(s_str)
    if seconds >= 60 or (h_str is not None and minutes >= 60):
        return None
    return float(hours * 3600 + minutes * 60 + seconds)


def extract_comment_timestamps(
    comments: list[dict[str, Any]],
    *,
    duration_s: float | None = None,
    min_gap_sec: float = 20.0,
) -> list[dict[str, Any]]:
    """Extrai timestamps válidos e descrições humanas dos comentários do VOD."""
    hits: list[dict[str, Any]] = []
    for item in comments or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        likes = int(item.get("like_count") or 0)
        for match in TIMESTAMP_RE.finditer(text):
            sec = parse_timestamp_to_seconds(match.group(0))
            if sec is None:
                continue
            if duration_s is not None and duration_s > 0 and sec > float(duration_s):
                continue
            desc = TIMESTAMP_RE.sub("", text).strip(" -–—:;,.")
            hits.append({
                "timestamp_s": round(sec, 2),
                "likes": likes,
                "comment_text": text[:280],
                "description": (desc or text)[:180],
            })
            break

    hits.sort(key=lambda h: (-h["likes"], h["timestamp_s"]))
    deduped: list[dict[str, Any]] = []
    for h in hits:
        if all(abs(h["timestamp_s"] - prev["timestamp_s"]) >= float(min_gap_sec) for prev in deduped):
            deduped.append(h)
    return deduped


def mine_youtube_comments(
    url: str,
    *,
    permission_status: str = "desconhecida",
    runner: Callable[..., Any] | None = None,
    max_comments: int = 100,
    window_before_sec: float = 12.0,
    window_after_sec: float = 22.0,
) -> list[dict[str, Any]]:
    """Minera comentários com timestamp de um VOD autorizado no YouTube via yt-dlp."""
    status = str(permission_status or "desconhecida").strip().lower()
    if status in BLOCKED_PERMISSION_STATUSES:
        raise PermissionError(
            f"Portão P1: mineração de comentários bloqueada para fonte com status '{status}'."
        )

    exec_fn = runner or subprocess.run
    cmd = [
        *ytdlp_base_cmd(),
        "--dump-single-json", "--skip-download", "--no-playlist",
        "--write-comments",
        "--extractor-args", f"youtube:max_comments={int(max_comments)},all,0,0",
        url,
    ]
    res = exec_fn(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout or "{}")
    duration = data.get("duration")
    try:
        duration_f = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_f = None

    extracted = extract_comment_timestamps(data.get("comments") or [], duration_s=duration_f)
    candidates: list[dict[str, Any]] = []
    for item in extracted:
        t = item["timestamp_s"]
        start = max(0.0, t - float(window_before_sec))
        end = t + float(window_after_sec)
        if duration_f and duration_f > 0:
            end = min(duration_f, end)
        if end <= start + 4.0:
            continue
        like_bonus = min(1.5, item["likes"] / 250.0)
        candidates.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "hook": item["description"][:70] or f"Comentário em {int(t)}s",
            "text": item["description"],
            "overall": round(7.4 + like_bonus, 2),
            "raw_score": round(7.4 + like_bonus, 2),
            "seed_kind": "comment_timestamp",
            "track_origin": "coop_payoff_nontextual",
            "score_parts": {"comment_likes": item["likes"]},
            "evidence": {},
            "reason": f"Timestamp de comentário ({item['likes']} likes): {item['description']}"[:300],
        })
    return candidates


COMMENTS_TIMEOUT = 5 * 60
_YOUTUBE_HOSTS = ("youtube.com", "youtu.be")


def save_comment_seeds(
    url: str,
    workdir: Any,
    *,
    permission_status: str = "desconhecida",
    max_comments: int = 300,
    timeout: float = COMMENTS_TIMEOUT,
    on_status: Any = None,
) -> Any:
    """Liga o minerador (3.5.4) ao prepare: grava <workdir>/comment_seeds.json (cache), só YouTube, nunca fatal."""
    from pathlib import Path
    from urllib.parse import urlparse

    report = on_status or (lambda status, detail="": None)
    out = Path(workdir) / "comment_seeds.json"
    if out.is_file():
        report("ok", "comentários em cache")
        return out
    host = (urlparse(str(url)).netloc or "").lower()
    if not any(h in host for h in _YOUTUBE_HOSTS):
        report("na", "fonte não é YouTube")
        return None
    if str(permission_status or "").strip().lower() in BLOCKED_PERMISSION_STATUSES:
        report("na", f"bloqueado pelo P1 (status {permission_status})")
        return None

    def _run_with_timeout(cmd, **kwargs):
        return subprocess.run(cmd, timeout=timeout, **kwargs)

    try:
        seeds = mine_youtube_comments(url, permission_status=permission_status, runner=_run_with_timeout,
                                      max_comments=max_comments)
    except Exception as exc:
        print(f"Comentários com timestamp indisponíveis ({type(exc).__name__}); seguindo sem eles.", flush=True)
        report("failed", f"{type(exc).__name__}: {exc}")
        return None
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(seeds, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out)
    report("ok" if seeds else "na", f"{len(seeds)} momentos marcados pelo público" if seeds else
           "nenhum comentário com horário")
    return out
