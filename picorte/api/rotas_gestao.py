"""Rotas de Fontes, Escudo e Saúde (história 6.7)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Body, Request

from picorte.config import PROJECT_ROOT
from picorte.services import gestao
from picorte.services.saude import benchmark, matriz_motor

rotas = APIRouter()
CADENCIA = None  # None = o estado padrão do cadence_guard (work/cadence_state.json); os testes trocam
BENCHMARKS = PROJECT_ROOT / "benchmarks"
DOSSIES = PROJECT_ROOT / "picorte" / "ai" / "game_dossiers"


def _db():
    from picorte.db.connection import get_default_db
    return get_default_db()


def _corpo(corpo) -> dict:
    if not isinstance(corpo, dict):
        raise ValueError("Esperado um objeto JSON.")
    return corpo


def _registro() -> list[dict]:
    from picorte.engine.publish_kit import load_streamer_registry
    return list(load_streamer_registry(None).get("streamers") or [])


@rotas.get("/api/fontes")
def fontes():
    return {"fontes": gestao.listar_fontes(_db(), _registro())}


@rotas.post("/api/fontes")
def cadastrar(corpo: dict = Body(...)):
    return gestao.cadastrar_fonte(_db(), _corpo(corpo))


@rotas.post("/api/fontes/{fid}/permissao")
def permissao(fid: str, corpo: dict = Body(...)):
    return gestao.mudar_permissao(_db(), fid, _corpo(corpo))


@rotas.get("/api/fontes/barradas")
def barradas(request: Request):
    return {"barradas": gestao.fontes_barradas(request.app.state.fila.listar())}


@rotas.get("/api/fontes/politicas")
def politicas():
    linhas = _db().fetch_all("SELECT * FROM publisher_policies ORDER BY game_slug")
    for p in linhas:
        p["forbidden_content_rules"] = json.loads(p.get("forbidden_content_rules") or "[]")
    return {"politicas": linhas}


@rotas.get("/api/fontes/dossies")
def dossies():
    saida = []
    for arq in sorted(DOSSIES.glob("*.json")):
        try:
            d = json.loads(arq.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict):
            saida.append({"slug": d.get("slug") or arq.stem, "nome": d.get("display_name") or arq.stem,
                          "aliases": d.get("aliases") or [], "atualizado_em": d.get("updated_at"),
                          "callbacks": d.get("cultural_callbacks") or [], "detalhes": d.get("hot_details_to_watch") or [],
                          "spoiler": d.get("spoiler_watch_p1") or []})
    return {"dossies": saida}


@rotas.get("/api/fontes/campanhas")
def campanhas():
    return {"campanhas": gestao.listar_campanhas(_db())}


@rotas.post("/api/fontes/campanhas")
def criar_campanha(corpo: dict = Body(...)):
    return gestao.criar_campanha(_db(), _corpo(corpo))


@rotas.get("/api/fontes/pausas")
def pausas():
    return {"eventos": gestao.eventos_de_pausa(_db())}


@rotas.get("/api/escudo")
def escudo():
    return {"cooldowns": gestao.estado_escudo(state_path=CADENCIA),
            "claims": [e for e in gestao.eventos_de_pausa(_db()) if e["tipo"] == "claim"]}


@rotas.post("/api/escudo/cooldown")
def cooldown(corpo: dict = Body(...)):
    corpo = _corpo(corpo)
    return gestao.criar_cooldown(str(corpo.get("rede") or ""), corpo.get("horas", 48), str(corpo.get("motivo") or ""),
                                 state_path=CADENCIA)


@rotas.post("/api/escudo/cooldown/limpar")
def limpar(corpo: dict = Body(...)):
    corpo = _corpo(corpo)
    return gestao.limpar_cooldown(str(corpo.get("rede") or ""), str(corpo.get("motivo") or ""), state_path=CADENCIA)


@rotas.get("/api/escudo/claim/previa")
def previa(fonte: str):
    return gestao.previa_claim(_db(), fonte)


@rotas.post("/api/escudo/claim")
def claim(corpo: dict = Body(...)):
    return gestao.registrar_claim(_db(), _corpo(corpo))


@rotas.get("/api/saude/motor")
def saude_motor(request: Request):
    return matriz_motor(request.app.state.raiz, request.app.state.fila.listar())


@rotas.get("/api/saude/benchmark")
def saude_benchmark():
    return benchmark(BENCHMARKS)
