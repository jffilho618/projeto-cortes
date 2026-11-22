"""Lock por projeto entre processos (B9, AD-11): o painel sabe se um job está vivo sem gravar nada."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock, Timeout

NOME_LOCK = ".job.lock"


class ProjetoOcupado(RuntimeError):
    """Já existe um job vivo neste projeto (nesta ou em outra janela/processo)."""


def caminho_lock(projeto) -> Path:
    return Path(projeto) / NOME_LOCK


@contextmanager
def segurar_job(projeto, espera: float = 2.0) -> Iterator[None]:
    lock = FileLock(str(caminho_lock(projeto)), timeout=espera)
    try:
        lock.acquire()
    except Timeout as exc:
        raise ProjetoOcupado(
            f"O projeto {Path(projeto).name} já tem um job rodando em outro processo.") from exc
    try:
        yield
    finally:
        lock.release()


def job_ativo(projeto) -> bool:
    """True se outro dono segura o lock. Não cria o arquivo de lock quando ele não existe."""
    arquivo = caminho_lock(projeto)
    if not arquivo.exists():
        return False
    lock = FileLock(str(arquivo), timeout=0)
    try:
        lock.acquire()
    except Timeout:
        return True
    lock.release()
    return False
