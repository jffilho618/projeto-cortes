"""Fila serial única do Estúdio (B5/B9): um job por vez; "interrompido" é derivado, nunca gravado."""
from __future__ import annotations

import re
import subprocess
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

import projects
from picorte.services.eventos import Barramento
from picorte.services.job_lock import ProjetoOcupado, job_ativo

RAIZ_REPO = Path(__file__).resolve().parents[2]
ACOES = {"prepare", "render", "all"}
ATIVOS = {"queued", "running"}
Executar = Callable[[Path, str, bool, "str | None"], int]


class FilaEstudio:
    def __init__(self, raiz, *, barramento: Barramento | None = None,
                 executar: Executar | None = None, intervalo: float = 1.0) -> None:
        self.raiz = Path(raiz).resolve()
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.barramento = barramento or Barramento()
        self._executar = executar or self._executar_subprocesso
        self._intervalo = intervalo
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="picorte-fila")
        self._trava = threading.RLock()
        self._futuros: dict[str, Future] = {}
        self._processos: set[subprocess.Popen] = set()
        self._fechando = False

    def na_fila(self, pid: str) -> bool:
        futuro = self._futuros.get(pid)
        return futuro is not None and not futuro.done()

    def ocupado(self, pid: str) -> bool:
        return self.na_fila(pid) or job_ativo(projects.project_path(self.raiz, pid))

    def status_efetivo(self, pid: str, estado: dict[str, Any]) -> str:
        status = estado.get("status", "new")
        if status in ATIVOS and not self.ocupado(pid):
            return "interrupted"
        return status

    def estado(self, pid: str) -> dict[str, Any]:
        gravado = projects.read_project(projects.project_path(self.raiz, pid))
        return {**gravado, "status_gravado": gravado.get("status"),
                "status": self.status_efetivo(pid, gravado), "na_fila": self.na_fila(pid)}

    def listar(self) -> list[dict[str, Any]]:
        itens = []
        for arquivo in self.raiz.glob("*/project.json"):
            try:
                itens.append(self.estado(arquivo.parent.name))
            except (ValueError, OSError, KeyError):
                continue
        return sorted(itens, key=lambda p: p.get("created", 0), reverse=True)

    def enfileirar(self, pid: str, acao: str, preview: bool = False, pick: str | None = None) -> None:
        if acao not in ACOES:
            raise ValueError("Ação desconhecida. Use prepare, render ou all.")
        if not isinstance(preview, bool):
            raise ValueError("Preview precisa ser verdadeiro ou falso.")
        if pick is not None and (not isinstance(pick, str) or not re.fullmatch(r"\d+(,\d+)*", pick)):
            raise ValueError("Escolha cortes numerados, por exemplo 1,3,5.")
        with self._trava:
            path = projects.project_path(self.raiz, pid)
            if self.ocupado(pid):
                raise ProjetoOcupado("Este projeto já está na fila ou rodando.")
            estado = projects.read_project(path)
            estado.update(status="queued", stage=acao, error=None)
            projects.save_project(path, estado)
            self.barramento.publicar("job", {"projeto": pid, "fase": "na_fila", "acao": acao})
            self._futuros[pid] = self._pool.submit(self._rodar, path, acao, preview, pick)

    def _rodar(self, path: Path, acao: str, preview: bool, pick: str | None) -> None:
        pid = path.name
        self.barramento.publicar("job", {"projeto": pid, "fase": "inicio", "acao": acao})
        try:
            codigo = self._executar(path, acao, preview, pick)
            if codigo:
                self._marcar_falha(path, None)
        except Exception as exc:  # noqa: BLE001 - qualquer falha vira estado visível
            codigo = 1
            self._marcar_falha(path, str(exc))
        self.barramento.publicar("job", {"projeto": pid, "fase": "fim", "acao": acao,
                                         "ok": codigo == 0})

    @staticmethod
    def _marcar_falha(path: Path, erro: str | None) -> None:
        estado = projects.read_project(path)
        estado.update(status="failed", error=erro or estado.get("error")
                      or "O job falhou. Abra o log do job para ver o motivo.")
        projects.save_project(path, estado)

    def _executar_subprocesso(self, path: Path, acao: str, preview: bool, pick: str | None) -> int:
        cmd = [sys.executable, str(RAIZ_REPO / "chopify.py"), "--project", str(path),
               "--action", acao, "--no-input",
               "--out", str(path / ("previews" if preview else "clips"))]
        if preview:
            cmd.append("--preview")
        if pick:
            cmd += ["--clips", pick]
        with (path / "job.log").open("w", encoding="utf-8") as log:
            with self._trava:
                if self._fechando:
                    return 1
                filho = subprocess.Popen(cmd, cwd=RAIZ_REPO, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT)
                self._processos.add(filho)
            ultimo = None
            try:
                while True:
                    try:
                        return filho.wait(timeout=self._intervalo)
                    except subprocess.TimeoutExpired:
                        ultimo = self._publicar_progresso(path, ultimo)
            finally:
                with self._trava:
                    self._processos.discard(filho)

    def _publicar_progresso(self, path: Path, ultimo: dict | None) -> dict | None:
        try:
            progresso = projects.read_project(path).get("progress") or {}
        except (ValueError, OSError):
            return ultimo
        if progresso != ultimo:
            self.barramento.publicar("progresso", {"projeto": path.name, **progresso})
        return progresso

    def fechar(self) -> None:
        with self._trava:
            self._fechando = True
            for filho in list(self._processos):
                filho.terminate()
        self._pool.shutdown(wait=False, cancel_futures=True)
