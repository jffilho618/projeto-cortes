"""Configuração global multiplataforma (Linux Ubuntu + Windows 11) e detecção de GPU/VRAM (AD-3, AD-11)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_venv_bin_dir(repo_root: Path | None = None, platform_name: str | None = None) -> Path:
    """Retorna .venv/Scripts no Windows e .venv/bin no Linux/macOS."""
    root = Path(repo_root) if repo_root is not None else PROJECT_ROOT
    plat = platform_name if platform_name is not None else sys.platform
    subdir = "Scripts" if plat == "win32" else "bin"
    return root / ".venv" / subdir


def ensure_venv_on_path(repo_root: Path | None = None) -> Path:
    """Injeta .venv/bin (Linux) ou .venv/Scripts (Windows) no PATH do processo atual."""
    bin_dir = get_venv_bin_dir(repo_root)
    if bin_dir.is_dir():
        current_path = os.environ.get("PATH", "")
        parts = current_path.split(os.pathsep) if current_path else []
        if str(bin_dir) not in parts:
            os.environ["PATH"] = str(bin_dir) + (os.pathsep + current_path if current_path else "")
    return bin_dir


def resolve_cli_binary(name: str) -> str | None:
    """Resolve executáveis no Linux e no Windows (.exe, .cmd, .bat), incluindo .venv e pastas padrão."""
    ensure_venv_on_path()
    found = shutil.which(name)
    if found:
        return found

    home = Path.home()
    candidates: list[Path] = []
    if sys.platform == "win32":
        local_app = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        if name == "nvidia-smi":
            candidates.extend([
                Path(r"C:\Windows\System32\nvidia-smi.exe"),
                Path(r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"),
            ])
        elif name == "agy":
            candidates.extend([
                home / ".gemini" / "bin" / "agy.exe",
                home / ".gemini" / "bin" / "agy.cmd",
                home / ".gemini" / "antigravity" / "bin" / "agy.exe",
                local_app / "Programs" / "Antigravity" / "agy.exe",
            ])
        elif name == "claude":
            candidates.extend([
                home / ".local" / "bin" / "claude.exe",
                home / ".claude" / "local" / "claude.exe",
                local_app / "Programs" / "claude" / "claude.exe",
            ])
        elif name == "ollama":
            candidates.append(local_app / "Programs" / "Ollama" / "ollama.exe")
    else:
        if name == "agy":
            candidates.extend([
                home / ".gemini" / "bin" / "agy",
                home / ".gemini" / "antigravity" / "bin" / "agy",
                Path("/usr/local/bin/agy"),
            ])
        elif name == "claude":
            candidates.extend([
                home / ".local" / "bin" / "claude",
                home / ".claude" / "local" / "claude",
                Path("/usr/local/bin/claude"),
            ])
        elif name == "ollama":
            candidates.extend([
                Path("/usr/local/bin/ollama"),
                Path("/usr/bin/ollama"),
            ])

    for cand in candidates:
        if cand.is_file():
            return str(cand)

    if name == "agy":
        env_exe = os.environ.get("ANTIGRAVITY_AGENTAPI_EXE", "").strip()
        if env_exe and not env_exe.endswith(".old") and os.path.isfile(env_exe):
            return env_exe
    return None


def probe_nvidia_smi() -> tuple[int, str]:
    """Consulta nvidia-smi (Linux ou Windows) para obter (vram_mib, gpu_name). Retorna (0, '') se ausente."""
    smi_bin = resolve_cli_binary("nvidia-smi") or "nvidia-smi"
    try:
        res = subprocess.run(
            [smi_bin, "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return 0, ""
        first_line = res.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in first_line.split(",", 1)]
        vram = int(float(parts[0]))
        name = parts[1] if len(parts) > 1 else "NVIDIA GPU"
        return vram, name
    except Exception:
        return 0, ""


def detect_gpu_profile(vram_mib: int | None = None, gpu_name: str | None = None) -> dict[str, Any]:
    """Seleciona automaticamente o perfil seguro de VRAM conforme AD-3:
    - <= 0 MiB (sem GPU): CPU only ('base', 'int8')
    - <= 6144 MiB (Notebook GTX 1650 4GB): 'notebook_4gb' ('small', 'int8')
    - >= 6145 MiB (Desktop Windows RTX 4060 Ti 8GB / 4070 Ti 12GB+): 'desktop_8gb_plus' ('large-v3-turbo', 'int8_float16')
    """
    ensure_venv_on_path()
    if vram_mib is None or gpu_name is None:
        detected_vram, detected_name = probe_nvidia_smi()
        if vram_mib is None:
            vram_mib = detected_vram
        if gpu_name is None:
            gpu_name = detected_name

    vram_mib = max(0, int(vram_mib))
    gpu_name = (gpu_name or "").strip()

    if vram_mib <= 0:
        return {
            "device": "cpu",
            "tier": "cpu_only",
            "whisper_model": "base",
            "compute_type": "int8",
            "vram_mib": 0,
            "gpu_name": "",
        }

    if vram_mib <= 6144:
        return {
            "device": "cuda",
            "tier": "notebook_4gb",
            "whisper_model": "small",
            "compute_type": "int8",
            "vram_mib": vram_mib,
            "gpu_name": gpu_name,
        }

    return {
        "device": "cuda",
        "tier": "desktop_8gb_plus",
        "whisper_model": "large-v3-turbo",
        "compute_type": "int8_float16",
        "vram_mib": vram_mib,
        "gpu_name": gpu_name,
    }


VISION_PRESET_CHOICES = ("auto", "low", "high")

VISION_PRESETS: dict[str, dict[str, Any]] = {
    "low": {
        "id": "low",
        "label": "Leve / Low (Notebook GTX 1650 4 GB ou CPU)",
        "facecam": "YuNet+MediaPipe",
        "hud": "RapidOCR+optical_flow",
        "sniper_crop": "optical_flow",
        "thumbnail_cutout": "u2netp",
        "whisper_model": "small",
        "compute_type": "int8",
    },
    "high": {
        "id": "high",
        "label": "Pesado / High (Desktop RTX 4060 Ti / 4070 Ti 8 GB+)",
        "facecam": "YuNet+MediaPipe+HSEmotion",
        "hud": "YOLO11n+RapidOCR",
        "sniper_crop": "YOLO11n+tracking",
        "thumbnail_cutout": "BiRefNet",
        "whisper_model": "large-v3-turbo",
        "compute_type": "int8_float16",
    },
}


def resolve_vision_preset(
    requested_preset: str = "auto",
    *,
    vram_mib: int | None = None,
    gpu_name: str | None = None,
) -> dict[str, Any]:
    """Resolve o preset de Visão Computacional ('auto' | 'low' | 'high') combinando detector de GPU e override."""
    choice = (requested_preset or "auto").strip().lower()
    if choice not in VISION_PRESET_CHOICES:
        raise ValueError(f"Preset de visao invalido: {requested_preset!r}. Use auto, low ou high.")

    gpu_profile = detect_gpu_profile(vram_mib=vram_mib, gpu_name=gpu_name)
    auto_detected = "high" if gpu_profile["tier"] == "desktop_8gb_plus" else "low"
    resolved = auto_detected if choice == "auto" else choice
    spec = VISION_PRESETS[resolved]
    models = {
        "facecam": spec["facecam"],
        "hud": spec["hud"],
        "sniper_crop": spec["sniper_crop"],
        "thumbnail_cutout": spec["thumbnail_cutout"],
        "whisper_model": spec["whisper_model"],
        "compute_type": spec["compute_type"],
    }
    return {
        "preset": resolved,
        "requested_preset": choice,
        "auto_detected": auto_detected,
        "gpu_profile": gpu_profile,
        "models": models,
    }


ensure_venv_on_path()
