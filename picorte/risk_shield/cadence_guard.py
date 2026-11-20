"""Story 4.2 — Cadência Anti-Spam & Modo Cool-Down 48h por Rede (P1/A2: previne Shorts Jail e TikTok spam_risk)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator

from filelock import FileLock

from picorte.db.connection import Database

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Estado de runtime (fora do git): nunca em assets/, que é catálogo versionado.
DEFAULT_CADENCE_STATE_PATH = PROJECT_ROOT / "work" / "cadence_state.json"
MAX_COOLDOWN_HOURS = 720.0  # 30 dias

CADENCE_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "warmup": {
        "youtube_shorts": {"max_per_24h": 3, "min_gap_hours": 4.0},
        "youtube_long": {"max_per_24h": 1, "min_gap_hours": 12.0},
        "tiktok": {"max_per_24h": 3, "min_gap_hours": 4.0},
        "instagram_reels": {"max_per_24h": 3, "min_gap_hours": 4.0},
        "facebook_reels": {"max_per_24h": 3, "min_gap_hours": 4.0},
    },
    "established": {
        "youtube_shorts": {"max_per_24h": 5, "min_gap_hours": 2.0},
        "youtube_long": {"max_per_24h": 2, "min_gap_hours": 6.0},
        "tiktok": {"max_per_24h": 4, "min_gap_hours": 3.0},
        "instagram_reels": {"max_per_24h": 4, "min_gap_hours": 3.0},
        "facebook_reels": {"max_per_24h": 4, "min_gap_hours": 3.0},
    },
}


def _parse_iso(val: str | None) -> datetime | None:
    if not val:
        return None
    raw = str(val).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _aware(dt: datetime | None) -> datetime:
    dt = dt or datetime.now(timezone.utc)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _state_path(state_path: Path | str | None) -> Path:
    return Path(state_path) if state_path else DEFAULT_CADENCE_STATE_PATH


@contextmanager
def _locked_state(state_path: Path | str | None) -> Iterator[dict[str, Any]]:
    """Ler-modificar-gravar sob FileLock (multiplataforma, AD-11) com escrita atômica."""
    path = _state_path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + ".lock"):
        state = _load_state(path)
        yield state
        _save_state(state, path)


def _load_state(state_path: Path | str | None = None) -> dict[str, Any]:
    path = _state_path(state_path)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
    return {"cooldowns": {}, "profiles": {}}


def _save_state(data: dict[str, Any], state_path: Path | str | None = None) -> None:
    path = _state_path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def activate_cooldown(
    platform: str,
    *,
    hours: float = 48.0,
    reason: str = "Resfriamento anti-spam ativado pelo operador",
    state_path: Path | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Ativa Modo Cool-Down (padrão 48h) em uma rede específica, travando novas postagens até vencer."""
    try:
        h = float(hours)
    except (TypeError, ValueError) as exc:
        raise ValueError("hours precisa ser um número.") from exc
    if not math.isfinite(h) or not 1.0 <= h <= MAX_COOLDOWN_HOURS:
        raise ValueError(f"hours precisa estar entre 1 e {MAX_COOLDOWN_HOURS:.0f}.")
    now_dt = _aware(now)
    until = now_dt + timedelta(hours=h)
    plat = str(platform).strip().lower()
    entry = {"until": until.isoformat(), "reason": str(reason), "activated_at": now_dt.isoformat()}
    with _locked_state(state_path) as state:
        state.setdefault("cooldowns", {})[plat] = entry
    return {"platform": plat, "cooldown_active": True, **entry}


def clear_cooldown(platform: str, *, state_path: Path | str | None = None) -> dict[str, Any]:
    plat = str(platform).strip().lower()
    with _locked_state(state_path) as state:
        state.setdefault("cooldowns", {}).pop(plat, None)
    return {"platform": plat, "cooldown_active": False}


def get_cooldown_status(
    *, state_path: Path | str | None = None, now: datetime | None = None
) -> dict[str, dict[str, Any]]:
    now_dt = _aware(now)
    state = _load_state(state_path)
    active: dict[str, dict[str, Any]] = {}
    for plat, info in (state.get("cooldowns") or {}).items():
        until_dt = _parse_iso(info.get("until"))
        if until_dt and until_dt > now_dt:
            rem_h = round((until_dt - now_dt).total_seconds() / 3600.0, 2)
            active[plat] = {
                "cooldown_active": True,
                "until": until_dt.isoformat(),
                "remaining_hours": rem_h,
                "reason": info.get("reason") or "",
            }
    return active


def check_cadence(
    db: Database,
    *,
    platform: str,
    profile: str = "warmup",
    state_path: Path | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Avalia se publicar agora nesta rede respeita teto diário, espaçamento mínimo e Cool-Down."""
    now_dt = _aware(now)
    plat = str(platform or "youtube_shorts").strip().lower()
    prof_name = profile if profile in CADENCE_PROFILES else "warmup"
    limits = CADENCE_PROFILES[prof_name].get(plat, {"max_per_24h": 3, "min_gap_hours": 4.0})
    max_24h = int(limits["max_per_24h"])
    min_gap_h = float(limits["min_gap_hours"])

    # 1) Verifica Cool-Down ativo
    cooldowns = get_cooldown_status(state_path=state_path, now=now_dt)
    if plat in cooldowns:
        cd = cooldowns[plat]
        return {
            "gate": "cadence_anti_spam",
            "platform": plat,
            "profile": prof_name,
            "status": "block",
            "cooldown_active": True,
            "posted_last_24h": 0,
            "max_per_24h": max_24h,
            "min_gap_hours": min_gap_h,
            "next_safe_at": cd["until"],
            "reason": f"Cool-Down ativo em {plat} ({cd['remaining_hours']}h restantes): {cd['reason']}",
        }

    # 2) Consulta publicações das últimas 24h na tabela publications
    rows = db.fetch_all(
        "SELECT created_at, published_at, scheduled_for, status FROM publications "
        "WHERE platform = ? AND status IN ('publicado', 'agendado')",
        (plat,),
    )
    # Agendado conta pelo horário marcado (não pela criação); publicado pelo horário real de publicação.
    cutoff_24h = now_dt - timedelta(hours=24)
    slot_times: list[datetime] = []
    for r in rows:
        if r.get("status") == "agendado":
            dt = _parse_iso(r.get("scheduled_for") or r.get("created_at"))
        else:
            dt = _parse_iso(r.get("published_at") or r.get("created_at"))
        if dt:
            slot_times.append(dt)
    recent_times = sorted((t for t in slot_times if cutoff_24h <= t <= now_dt), reverse=True)
    upcoming = sorted(t for t in slot_times if now_dt < t <= now_dt + timedelta(hours=min_gap_h))
    posted_24h = len(recent_times)

    # Verifica teto diário
    if posted_24h >= max_24h:
        oldest_in_window = min(recent_times)
        next_safe = oldest_in_window + timedelta(hours=24)
        return {
            "gate": "cadence_anti_spam",
            "platform": plat,
            "profile": prof_name,
            "status": "block",
            "cooldown_active": False,
            "posted_last_24h": posted_24h,
            "max_per_24h": max_24h,
            "min_gap_hours": min_gap_h,
            "next_safe_at": next_safe.isoformat(),
            "reason": f"Teto seguro atingido em {plat}: {posted_24h}/{max_24h} nas últimas 24h (perfil {prof_name}).",
        }

    # Agendamento próximo demais (menos que o espaçamento mínimo à frente) também bloqueia agora
    if upcoming:
        next_safe = upcoming[-1] + timedelta(hours=min_gap_h)
        return {
            "gate": "cadence_anti_spam",
            "platform": plat,
            "profile": prof_name,
            "status": "block",
            "cooldown_active": False,
            "posted_last_24h": posted_24h,
            "max_per_24h": max_24h,
            "min_gap_hours": min_gap_h,
            "next_safe_at": next_safe.isoformat(),
            "reason": (
                f"Há postagem agendada em {plat} em menos de {min_gap_h:.0f}h "
                f"({upcoming[0].isoformat()}); postar agora ficaria colado nela."
            ),
        }

    # Verifica espaçamento mínimo desde a última publicação
    if recent_times:
        last_dt = recent_times[0]
        elapsed_h = (now_dt - last_dt).total_seconds() / 3600.0
        if elapsed_h < min_gap_h:
            next_safe = last_dt + timedelta(hours=min_gap_h)
            return {
                "gate": "cadence_anti_spam",
                "platform": plat,
                "profile": prof_name,
                "status": "block",
                "cooldown_active": False,
                "posted_last_24h": posted_24h,
                "max_per_24h": max_24h,
                "min_gap_hours": min_gap_h,
                "next_safe_at": next_safe.isoformat(),
                "reason": (
                    f"Espaçamento curto em {plat}: última postagem há {elapsed_h:.1f}h "
                    f"(mínimo seguro: {min_gap_h:.0f}h)."
                ),
            }

    return {
        "gate": "cadence_anti_spam",
        "platform": plat,
        "profile": prof_name,
        "status": "pass",
        "cooldown_active": False,
        "posted_last_24h": posted_24h,
        "max_per_24h": max_24h,
        "min_gap_hours": min_gap_h,
        "next_safe_at": None,
        "reason": f"Cadência liberada em {plat} ({posted_24h}/{max_24h} nas últimas 24h).",
    }
