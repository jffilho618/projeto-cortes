"""Fábrica do app FastAPI do Estúdio do Criador (história 6.3)."""
from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from picorte.api.seguranca import PortaoSeguranca

DIST_PADRAO = Path(__file__).resolve().parents[1] / "web" / "dist"
PAGINA_SEM_BUILD = """<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<title>Picorte · Estúdio</title><body style="font-family:system-ui;padding:40px">
<h1>A casca do Estúdio ainda não foi construída</h1>
<p>Rode <code>npm install</code> e <code>npm run build</code> em <code>picorte/web</code>.
A API já responde em <code>/api/capacidades</code>.</p></body></html>"""


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    yield
    app.state.fila.fechar()  # termina o job filho ao desligar o Estúdio


def _erro(status: int, mensagem: str) -> JSONResponse:
    return JSONResponse({"erro": mensagem}, status_code=status)


def _registrar_erros(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def _valor(_: Request, exc: ValueError):
        return _erro(400, str(exc))

    @app.exception_handler(KeyError)
    async def _chave(_: Request, exc: KeyError):
        return _erro(400, f"Campo obrigatório ausente: {exc.args[0] if exc.args else ''}")

    @app.exception_handler(TypeError)
    async def _tipo(_: Request, exc: TypeError):
        return _erro(400, str(exc))

    @app.exception_handler(OSError)
    async def _arquivo(_: Request, exc: OSError):
        return _erro(404, "Projeto ou arquivo não encontrado.")

    from picorte.services.job_lock import ProjetoOcupado

    @app.exception_handler(ProjetoOcupado)
    async def _ocupado(_: Request, exc: ProjetoOcupado):
        return _erro(409, str(exc))


def _registrar_rotas(app: FastAPI) -> None:
    from picorte.api.rotas_projetos import rotas as rotas_projetos
    from picorte.api.rotas_sistema import rotas as rotas_sistema

    app.include_router(rotas_sistema)
    app.include_router(rotas_projetos)
    from picorte.api.rotas_lives import rotas as rotas_lives

    app.include_router(rotas_lives)
    from picorte.api.rotas_revisao import rotas as rotas_revisao

    app.include_router(rotas_revisao)
    from picorte.api.rotas_gestao import rotas as rotas_gestao

    app.include_router(rotas_gestao)


def _registrar_spa(app: FastAPI, dist: Path) -> None:
    dist = dist.resolve()

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        if caminho in {"api", "media"} or caminho.startswith(("api/", "media/")):
            return _erro(404, "Não encontrado.")
        if caminho:
            alvo = (dist / caminho).resolve()
            if alvo.is_file() and alvo.is_relative_to(dist):
                return FileResponse(alvo)
        indice = dist / "index.html"
        if indice.is_file():
            return FileResponse(indice, media_type="text/html")
        return HTMLResponse(PAGINA_SEM_BUILD)


def create_app(raiz_projetos, *, porta: int = 8770, hosts: tuple[str, ...] | None = None,
               token: str | None = None, dist: Path | None = None, fila=None,
               barramento=None, capacidades=None, vitrine=None, listar=None, sondar=None,
               portao=None) -> FastAPI:
    from picorte.capacidades import ServicoCapacidades
    from picorte.services.eventos import Barramento
    from picorte.services.fila import FilaEstudio

    app = FastAPI(title="Picorte · Estúdio do Criador", docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=_ciclo_de_vida)
    raiz = Path(raiz_projetos).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "brands").mkdir(exist_ok=True)
    app.state.raiz = raiz
    app.state.token = token or secrets.token_urlsafe(32)
    app.state.porta = porta
    app.state.barramento = barramento or (fila.barramento if fila else Barramento())
    app.state.fila = fila or FilaEstudio(raiz, barramento=app.state.barramento)
    app.state.capacidades = capacidades or ServicoCapacidades(raiz, barramento=app.state.barramento)
    if app.state.capacidades.barramento is None:
        app.state.capacidades.barramento = app.state.barramento
    from picorte.config import PROJECT_ROOT
    from picorte.services.vitrine import CacheVitrine, listar_canal
    app.state.vitrine = vitrine or CacheVitrine(PROJECT_ROOT / ".picorte" / "cache" / "vitrine.json")
    app.state.listar_canal = listar or listar_canal
    app.state.sondar = sondar
    app.state.portao = portao
    app.add_middleware(PortaoSeguranca, # "localhost" porque o YouTube recusa o player embutido de vídeo com anúncio em origem IP
                       hosts=hosts or (f"127.0.0.1:{porta}", f"localhost:{porta}"),
                       token=app.state.token)
    _registrar_erros(app)
    _registrar_rotas(app)
    _registrar_spa(app, Path(dist) if dist else DIST_PADRAO)
    return app
