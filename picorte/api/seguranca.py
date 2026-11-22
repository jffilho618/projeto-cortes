"""Portões do Estúdio (portados do dashboard.py): Host, Origin, token anti-CSRF e cabeçalhos."""
from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

CABECALHO_TOKEN = "X-Picorte-Token"
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}
CSP = ("default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self'; "
       "img-src 'self' data: https://i.ytimg.com; font-src 'self'; connect-src 'self'; "
       "frame-src https://www.youtube-nocookie.com https://player.twitch.tv; "
       "frame-ancestors 'none'; base-uri 'none'")


def _cabecalhos(resposta: Response) -> Response:
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["Content-Security-Policy"] = CSP
    resposta.headers.setdefault("Cache-Control", "no-store")
    return resposta


def _recusa(mensagem: str) -> Response:
    return _cabecalhos(JSONResponse({"erro": mensagem}, status_code=403))


class PortaoSeguranca(BaseHTTPMiddleware):
    def __init__(self, app, *, hosts: tuple[str, ...], token: str) -> None:
        super().__init__(app)
        self.hosts = set(hosts)
        self.token = token.encode()

    async def dispatch(self, request, call_next):
        host = request.headers.get("host", "")
        if host not in self.hosts:
            return _recusa("Use o endereço local do Estúdio (127.0.0.1).")
        if request.method not in METODOS_SEGUROS:
            origem = request.headers.get("origin")
            if origem is not None and origem != f"http://{host}":
                return _recusa("Origem recusada.")
            enviado = request.headers.get(CABECALHO_TOKEN, "").encode("utf-8", "replace")
            if not secrets.compare_digest(enviado, self.token):
                return _recusa("Pedido recusado. Recarregue o Estúdio e tente de novo.")
        return _cabecalhos(await call_next(request))
