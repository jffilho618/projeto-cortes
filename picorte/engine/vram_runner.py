"""Orquestrador serial de VRAM multiplataforma (Windows 11 + Linux Ubuntu) e Modo Madrugada (AD-3, AD-11, R-06)."""
from __future__ import annotations

import gc
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

from filelock import FileLock

T = TypeVar("T")

DEFAULT_LOCK_PATH = Path(tempfile.gettempdir()) / "picorte_gpu_stage.lock"
_THREAD_LOCK = threading.Lock()


def cleanup_vram_memory(stage_name: str = "") -> None:
    """Força coleta de lixo e esvazia cache CUDA quando torch/ctranslate2 estiver carregado."""
    gc.collect()
    try:
        import torch  # type: ignore[import-not-found]

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def is_in_night_window(hour: int | None = None, start_hour: int = 1, end_hour: int = 7) -> bool:
    """Avalia se o horário atual está dentro da janela do Modo Madrugada."""
    current = datetime.now().hour if hour is None else int(hour) % 24
    start = int(start_hour) % 24
    end = int(end_hour) % 24
    if start <= end:
        return start <= current < end
    return current >= start or current < end


class VRAMRunner:
    """Garante que apenas 1 estágio pesado de GPU rode por vez (entre threads e processos)."""

    def __init__(
        self,
        lock_path: Path | str | None = None,
        timeout: float = 3600.0,
        cleanup_hook: Callable[[str], None] | None = None,
    ) -> None:
        self.lock_path = Path(lock_path) if lock_path else DEFAULT_LOCK_PATH
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_lock = FileLock(str(self.lock_path), timeout=timeout)
        self.cleanup_hook = cleanup_hook or cleanup_vram_memory

    def run_stage(self, stage_name: str, fn: Callable[[], T]) -> T:
        with _THREAD_LOCK:
            with self.file_lock:
                try:
                    return fn()
                finally:
                    self.cleanup_hook(stage_name)
