"""Rotas da Fila e da Revisão (história 6.6)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

import projects
from picorte.services.revisao import linha_da_fila, montar_revisao

rotas = APIRouter()


def _db():
    from picorte.db.connection import get_default_db
    return get_default_db()


def _corpo(corpo) -> dict:
    if not isinstance(corpo, dict):
        raise ValueError("Esperado um objeto JSON.")
    return corpo


@rotas.get("/api/fila")
def fila(request: Request):
    linhas = [linha_da_fila(p) for p in request.app.state.fila.listar()]
    return {"producao": [l for l in linhas if not l["prova"]], "prova": [l for l in linhas if l["prova"]]}


@rotas.get("/api/projetos/{pid}/revisao")
def revisao(pid: str, request: Request):
    from picorte.services.decisoes import ler_decisoes
    pasta = projects.project_path(request.app.state.raiz, pid)
    estado = request.app.state.fila.estado(pid)
    return montar_revisao(pasta, estado, ler_decisoes(_db(), pid))


@rotas.get("/api/projetos/{pid}/energia")
def energia(pid: str, request: Request, de: float | None = None, ate: float | None = None, pontos: int | None = None):
    from picorte.services.energia import energia as calcular
    pasta = projects.project_path(request.app.state.raiz, pid)
    try:
        return calcular(pasta, de=de, ate=ate, pontos=pontos)
    except FileNotFoundError as exc:
        return JSONResponse({"erro": str(exc)}, status_code=404)


@rotas.post("/api/projetos/{pid}/cortes/{seg}/rotulo")
def rotulo(pid: str, seg: str, request: Request, corpo: dict = Body(...)):
    from picorte.services.decisoes import gravar_rotulo
    projects.project_path(request.app.state.raiz, pid)  # valida o id do projeto
    corpo = _corpo(corpo)
    valor = corpo.get("valor")
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError("O rótulo é 1 (bom), -1 (ruim) ou 0 (tirar).")
    gravar_rotulo(_db(), pid, seg, valor, str(corpo.get("motivo") or ""))
    return {"ok": True}


@rotas.post("/api/projetos/{pid}/cortes/{seg}/descarte")
def descarte(pid: str, seg: str, request: Request, corpo: dict = Body(...)):
    from picorte.services.decisoes import gravar_descarte
    projects.project_path(request.app.state.raiz, pid)
    gravar_descarte(_db(), pid, seg, bool(_corpo(corpo).get("descartado")))
    return {"ok": True}


@rotas.post("/api/projetos/{pid}/cortes/{seg}/exemplo-ouro")
def exemplo_ouro(pid: str, seg: str, request: Request):
    from picorte.services import decisoes
    pasta = projects.project_path(request.app.state.raiz, pid)
    estado = request.app.state.fila.estado(pid)
    try:
        exemplo = decisoes.salvar_exemplo_ouro(_db(), pid, pasta, estado, seg, arquivo=decisoes.BIBLIOTECA_OURO)
    except KeyError:
        raise ValueError("Esse corte não existe neste projeto.")
    return {"ok": True, "exemplo": exemplo}
