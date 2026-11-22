"""Energia do áudio por segundo (audio_features.npz) para a onda, o minimapa e o pico de origem (história 6.6).

A escala é a do VOD inteiro (percentis 5 e 99,5), para que a janela de um corte e o minimapa conversem.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

MAX_PONTOS = 4000


def energia(pasta: Path, de: float | None = None, ate: float | None = None,
            pontos: int | None = None) -> dict[str, Any]:
    arquivo = Path(pasta) / "audio_features.npz"
    if not arquivo.is_file():
        raise FileNotFoundError("Forma de onda indisponível: este projeto não tem a energia do áudio registrada.")
    with np.load(arquivo, allow_pickle=False) as dados:
        rms = np.asarray(dados["rms"], dtype=float)
    duracao = len(rms)
    lo, hi = np.percentile(rms, 5), np.percentile(rms, 99.5)
    escala = max(float(hi - lo), 1e-9)
    ini = int(max(0, min(duracao, int(de if de is not None else 0))))
    fim = int(max(ini, min(duracao, int(ate if ate is not None else duracao))))
    trecho = np.clip((rms[ini:fim] - lo) / escala, 0.0, 1.0)
    if pontos and len(trecho) > 1:
        n = int(max(2, min(int(pontos), MAX_PONTOS)))
        trecho = np.interp(np.linspace(0, len(trecho) - 1, n), np.arange(len(trecho)), trecho)
    elif len(trecho) > MAX_PONTOS:
        trecho = np.interp(np.linspace(0, len(trecho) - 1, MAX_PONTOS), np.arange(len(trecho)), trecho)
    return {"duracao_s": duracao, "de": ini, "ate": fim, "valores": [round(float(v), 4) for v in trecho]}
