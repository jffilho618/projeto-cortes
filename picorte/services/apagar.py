"""Apagar projeto pela UI (decisão do dono, 2026-11-23): a pasta inteira, cortes renderizados inclusos."""
from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any


def previa(pasta: Path) -> dict[str, Any]:
    """O que vai junto, para a confirmação: tamanho em disco e quantos cortes renderizados."""
    pasta = Path(pasta)
    tamanho = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file())
    cortes = sum(1 for f in (pasta / "clips").glob("*.mp4")) if (pasta / "clips").is_dir() else 0
    return {"bytes": tamanho, "gb": round(tamanho / 1024 ** 3, 2), "cortes": cortes}


def _liberar_e_tentar(funcao, caminho, _exc) -> None:
    os.chmod(caminho, stat.S_IWRITE)  # Windows: arquivo só leitura não sai sem isso
    funcao(caminho)


def apagar(pasta: Path) -> None:
    if sys.version_info >= (3, 12):
        shutil.rmtree(Path(pasta), onexc=_liberar_e_tentar)
    else:  # AD-11: o notebook Linux pode ter Python anterior ao onexc
        shutil.rmtree(Path(pasta), onerror=_liberar_e_tentar)
