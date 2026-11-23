"""Registro de saúde do motor (W9) — dados para o painel "Saúde do motor" do Épico 6.

Cada parte que antes podia falhar em silêncio grava em <projeto>/engine_health.json:
  {"<parte>": {"status": "ok" | "na" | "failed", "detail": str, "at": iso8601}}
- ok: funcionou · na: não se aplica a esta fonte (normal, não é alerta) · failed: quebrou (alerta).
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from filelock import FileLock

HEALTH_FILE = "engine_health.json"
STATUSES = ("ok", "na", "failed")


def _path(workdir: Any) -> Path:
    return Path(workdir) / HEALTH_FILE


def load(workdir: Any) -> dict[str, dict[str, Any]]:
    p = _path(workdir)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(p: Path, data: dict[str, Any]) -> None:
    """Escrita atômica (AD-11); quem chama segura a trava."""
    fd, tmp = tempfile.mkstemp(prefix=p.name, suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def record(workdir: Any, part: str, status: str, detail: str = "") -> None:
    """Grava o estado de uma parte (merge com as demais), com trava e escrita atômica (AD-11)."""
    if status not in STATUSES:
        raise ValueError(f"status de saúde inválido: {status!r} (use {', '.join(STATUSES)})")
    p = _path(workdir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(p) + ".lock"):
        data = load(workdir)
        data[str(part)] = {
            "status": status,
            "detail": str(detail or "")[:400],
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        _write(p, data)


def recorder(workdir: Any, part: str):
    """Callback `on_status(status, detail)` que grava a parte no projeto."""
    return lambda status, detail="": record(workdir, part, status, detail)


def failures(workdir: Any) -> list[str]:
    return sorted(k for k, v in load(workdir).items() if (v or {}).get("status") == "failed")


MARCA_EXECUCAO = "_execucao"  # não é parte: começa com "_" e não tem "status"


def marcar_execucao(workdir: Any, acao: str) -> str:
    """W32: grava o início desta execução; as partes anteriores a ela ficam de fora do painel."""
    p = _path(workdir)
    p.parent.mkdir(parents=True, exist_ok=True)
    inicio = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with FileLock(str(p) + ".lock"):
        data = load(workdir)
        data[MARCA_EXECUCAO] = {"inicio": inicio, "acao": str(acao)}
        _write(p, data)
    return inicio


def _instante(valor: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(valor))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def partes_da_execucao(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Só as partes gravadas desde a marca da última execução (sem marca, projeto antigo: todas)."""
    partes = {k: v for k, v in data.items() if not str(k).startswith("_") and isinstance(v, dict)}
    marca = data.get(MARCA_EXECUCAO)
    inicio = _instante(marca.get("inicio")) if isinstance(marca, dict) else None
    if inicio is None:
        return partes
    def desta(parte: dict[str, Any]) -> bool:
        at = _instante(parte.get("at"))  # sem horário: é de antes do registro com `at`, execução anterior
        return at is not None and at >= inicio

    return {k: v for k, v in partes.items() if desta(v)}
