"""Make pip-installed NVIDIA runtime libraries loadable (transplantado de artbyjazi/autoclip MIT)."""
from __future__ import annotations

import ctypes
import logging
import os
import sys
import sysconfig
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

_COMPONENTS = ("cuda_runtime", "cublas", "cudnn", "cuda_nvrtc")
_WINDOWS_SUBDIR = "bin"
_POSIX_SUBDIR = "lib"


def _nvidia_root() -> Path | None:
    candidates = [sysconfig.get_paths().get("purelib"), sysconfig.get_paths().get("platlib")]
    for entry in sys.path:
        candidates.append(entry)
    for candidate in candidates:
        if not candidate:
            continue
        root = Path(candidate) / "nvidia"
        if root.is_dir():
            return root
    return None


def library_directories() -> list[Path]:
    root = _nvidia_root()
    if root is None:
        return []
    subdir = _WINDOWS_SUBDIR if sys.platform == "win32" else _POSIX_SUBDIR
    found: list[Path] = []
    for component in _COMPONENTS:
        path = root / component / subdir
        if path.is_dir():
            found.append(path)
    for child in sorted(root.iterdir()):
        path = child / subdir
        if path.is_dir() and path not in found:
            found.append(path)
    return found


@lru_cache(maxsize=1)
def ensure_cuda_libraries() -> list[Path]:
    directories = library_directories()
    if not directories:
        return []
    registered: list[Path] = []
    if sys.platform == "win32":
        add_dir = getattr(os, "add_dll_directory", None)
        for directory in directories:
            try:
                if add_dir is not None:
                    add_dir(str(directory))
                registered.append(directory)
            except OSError:
                pass
    else:
        for directory in directories:
            loaded_any = False
            for so_file in sorted(directory.glob("*.so*")):
                try:
                    ctypes.CDLL(str(so_file), mode=ctypes.RTLD_GLOBAL)
                    loaded_any = True
                except OSError:
                    pass
            if loaded_any:
                registered.append(directory)
    return registered


def has_cuda_runtime_libraries() -> bool:
    """Verifica se cuBLAS 12 (libcublas.so.12 / cublas64_12.dll) realmente carrega em runtime."""
    ensure_cuda_libraries()
    target = "cublas64_12.dll" if sys.platform == "win32" else "libcublas.so.12"
    try:
        ctypes.CDLL(target)
        return True
    except OSError:
        pass
    for directory in library_directories():
        cand = directory / target
        if cand.is_file():
            try:
                ctypes.CDLL(str(cand))
                return True
            except OSError:
                continue
    return False
