"""Barramento de eventos do Estúdio: alimenta o SSE /api/eventos (progresso de job e capacidades)."""
from __future__ import annotations

import json
import queue
import threading
from typing import Any


class Barramento:
    def __init__(self, tamanho_fila: int = 256) -> None:
        self._assinantes: set[queue.Queue] = set()
        self._trava = threading.Lock()
        self._tamanho = tamanho_fila

    def assinar(self) -> "queue.Queue[tuple[str, dict[str, Any]]]":
        q: queue.Queue = queue.Queue(maxsize=self._tamanho)
        with self._trava:
            self._assinantes.add(q)
        return q

    def cancelar(self, q: queue.Queue) -> None:
        with self._trava:
            self._assinantes.discard(q)

    def publicar(self, tipo: str, dados: dict[str, Any]) -> None:
        with self._trava:
            alvos = list(self._assinantes)
        for q in alvos:
            try:
                q.put_nowait((tipo, dados))
            except queue.Full:
                pass  # assinante lento perde o evento; o front relê o estado ao reconectar


def formatar_sse(tipo: str, dados: dict[str, Any]) -> str:
    return f"event: {tipo}\ndata: {json.dumps(dados, ensure_ascii=False, allow_nan=False)}\n\n"
