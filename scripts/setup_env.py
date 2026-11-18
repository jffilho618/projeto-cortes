"""Bootstrap multiplataforma (Windows 11 + Linux Ubuntu) para o Picorte.

Uso em qualquer sistema (Windows PowerShell/CMD ou Linux bash):
    python scripts/setup_env.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IS_WIN = sys.platform == "win32"
VENV_DIR = ROOT / ".venv"
VENV_BIN = VENV_DIR / ("Scripts" if IS_WIN else "bin")
PYTHON_EXE = VENV_BIN / ("python.exe" if IS_WIN else "python")
FFMPEG_EXE = VENV_BIN / ("ffmpeg.exe" if IS_WIN else "ffmpeg")
FFPROBE_EXE = VENV_BIN / ("ffprobe.exe" if IS_WIN else "ffprobe")


def ensure_venv() -> None:
    if PYTHON_EXE.exists():
        print(f"[ok] Virtualenv existente em {VENV_DIR}")
        return
    print(f"=== Criando ambiente virtual em {VENV_DIR} ===")
    if shutil.which("uv"):
        subprocess.run(["uv", "venv", "--python", "3.12", str(VENV_DIR)], check=True)
    else:
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)


def install_requirements() -> None:
    req = ROOT / "requirements.txt"
    print("=== Instalando dependências Python ===")
    if shutil.which("uv"):
        subprocess.run(["uv", "pip", "install", "--python", str(PYTHON_EXE), "-r", str(req)], check=True)
    else:
        subprocess.run([str(PYTHON_EXE), "-m", "pip", "install", "-r", str(req)], check=True)


def ensure_ffmpeg() -> None:
    if FFMPEG_EXE.exists() and FFPROBE_EXE.exists():
        print(f"[ok] FFmpeg já instalado em {VENV_BIN}")
        return
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        print("[ok] FFmpeg já disponível no PATH do sistema")
        return

    VENV_BIN.mkdir(parents=True, exist_ok=True)
    if IS_WIN:
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        print(f"=== Baixando FFmpeg estático para Windows (com libass + nvenc): {url} ===")
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "ffmpeg-win64.zip"
            urllib.request.urlretrieve(url, str(archive))
            with zipfile.ZipFile(archive, "r") as zf:
                for name in zf.namelist():
                    if name.endswith("/bin/ffmpeg.exe"):
                        FFMPEG_EXE.write_bytes(zf.read(name))
                    elif name.endswith("/bin/ffprobe.exe"):
                        FFPROBE_EXE.write_bytes(zf.read(name))
    else:
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
        print(f"=== Baixando FFmpeg estático para Linux (com libass + nvenc): {url} ===")
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "ffmpeg-linux64.tar.xz"
            urllib.request.urlretrieve(url, str(archive))
            with tarfile.open(archive, "r:xz") as tf:
                for member in tf.getmembers():
                    if member.name.endswith("/bin/ffmpeg"):
                        f = tf.extractfile(member)
                        if f:
                            FFMPEG_EXE.write_bytes(f.read())
                            FFMPEG_EXE.chmod(0o755)
                    elif member.name.endswith("/bin/ffprobe"):
                        f = tf.extractfile(member)
                        if f:
                            FFPROBE_EXE.write_bytes(f.read())
                            FFPROBE_EXE.chmod(0o755)


def main() -> None:
    ensure_venv()
    install_requirements()
    ensure_ffmpeg()
    print("\n=== Setup concluído com sucesso! ===")


if __name__ == "__main__":
    main()
