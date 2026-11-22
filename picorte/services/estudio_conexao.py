"""Fila única (B5, história 6.4): o MCP enfileira pelo Estúdio aberto, na mesma rota do painel."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from picorte.api.seguranca import CABECALHO_TOKEN
from picorte.config import PROJECT_ROOT

ARQUIVO_CONEXAO = PROJECT_ROOT / ".picorte" / "estudio.json"
AVISO = "O Estúdio não está rodando. Abra com: python estudio.py (o job entra na mesma fila do painel)."


class EstudioDesligado(RuntimeError):
    pass


def gravar_conexao(porta: int, token: str, arquivo: Path = ARQUIVO_CONEXAO) -> None:
    arquivo = Path(arquivo)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps({"porta": int(porta), "token": token, "pid": os.getpid()}), encoding="utf-8")


def ler_conexao(arquivo: Path = ARQUIVO_CONEXAO) -> dict[str, Any] | None:
    try:
        dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dados if isinstance(dados, dict) and dados.get("porta") and dados.get("token") else None


def apagar_conexao(arquivo: Path = ARQUIVO_CONEXAO) -> None:
    Path(arquivo).unlink(missing_ok=True)


def enfileirar_no_estudio(fontes: list[str], opcoes: dict[str, Any] | None = None, *,
                          arquivo: Path = ARQUIVO_CONEXAO, post=httpx.post) -> dict[str, Any]:
    """Cria os projetos e enfileira o preparo pela rota /api/lote do Estúdio (o portão P1 roda antes de baixar)."""
    conexao = ler_conexao(arquivo)
    if not conexao:
        raise EstudioDesligado(AVISO)
    url = f"http://127.0.0.1:{int(conexao['porta'])}/api/lote"
    try:
        resposta = post(url, json={"sources": fontes, "options": opcoes or {}},
                        headers={CABECALHO_TOKEN: str(conexao["token"])}, timeout=30)
    except httpx.HTTPError as exc:
        raise EstudioDesligado(AVISO) from exc
    dados = resposta.json() if resposta.content else {}
    if resposta.status_code >= 400:
        raise ValueError(str(dados.get("erro") or f"O Estúdio respondeu {resposta.status_code}."))
    return dados
