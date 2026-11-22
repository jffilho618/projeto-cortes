"""Rotas da Publicação assistida e dos contadores do Aprendizado (história 6.8)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request

from picorte.config import PROJECT_ROOT
from picorte.services import publicacao as P

rotas = APIRouter()
CADENCIA = None  # None = work/cadence_state.json do cadence_guard; os testes trocam
SAIDA = PROJECT_ROOT / "prontos_para_postar"
BENCHMARKS = PROJECT_ROOT / "benchmarks"


def _db():
    from picorte.db.connection import get_default_db
    return get_default_db()


def _abrir(pasta: Path) -> None:
    from dashboard import _open_in_file_manager  # Windows e Linux (C4)
    _open_in_file_manager(pasta)


def _corpo(corpo) -> dict:
    if not isinstance(corpo, dict):
        raise ValueError("Esperado um objeto JSON.")
    return corpo


@rotas.get("/api/publicacao/pacote")
def pacote(request: Request):
    estado = request.app.state
    return P.montar_pacote(_db(), estado.raiz, estado.fila.listar(), cadencia=CADENCIA)


@rotas.post("/api/publicacao/exportar")
def exportar(request: Request, corpo: dict = Body(...)):
    from picorte.engine.publish_kit import export_daily_bundle
    itens = _corpo(corpo).get("itens")
    if not isinstance(itens, list) or not itens:
        raise ValueError("Escolha ao menos um corte para exportar.")
    por_projeto: dict[str, list[str]] = {}
    for item in itens:
        pid, stem = str((item or {}).get("projeto") or ""), str((item or {}).get("stem") or "")
        if not pid.isalnum() or not stem:
            raise ValueError("Item de exportação inválido.")
        por_projeto.setdefault(pid, []).append(stem)
    db, raiz = _db(), request.app.state.raiz
    pastas, exportados, pulados = [], 0, []
    for pid, stems in por_projeto.items():
        feito = export_daily_bundle(raiz / pid, clip_stems=stems, out_root=SAIDA, db=db, cadence_state_path=CADENCIA)
        ok = [f["stem"] for f in feito["files"]]
        P.marcar_exportados(db, pid, ok, raiz)
        pastas.append(feito["bundle_dir"])
        exportados += len(ok)
        pulados += [{"projeto": pid, "stem": s} for s in feito["skipped_blocked"]]
    return {"pastas": pastas, "exportados": exportados, "pulados": pulados}


def _na_publicacao(acao, *args):
    try:
        return acao(_db(), *args)
    except P.PublicacaoNaoEncontrada as erro:
        raise HTTPException(404, str(erro)) from erro


@rotas.get("/api/publicacao/links")
def links(request: Request):
    return {"links": P.listar_links(_db(), request.app.state.raiz)}


@rotas.post("/api/publicacao/links/{pub_id}")
def colar_link(pub_id: str, corpo: dict = Body(...)):
    return _na_publicacao(P.registrar_link, pub_id, str(_corpo(corpo).get("url") or ""))


@rotas.post("/api/publicacao/links/{pub_id}/nao-vou-postar")
def nao_vou_postar(pub_id: str, corpo: dict = Body(...)):
    return _na_publicacao(P.nao_vou_postar, pub_id, str(_corpo(corpo).get("motivo") or ""))


@rotas.post("/api/publicacao/links/{pub_id}/desfazer")
def desfazer(pub_id: str):
    return _na_publicacao(P.desfazer, pub_id)


@rotas.post("/api/publicacao/abrir")
def abrir(corpo: dict = Body(...)):
    pasta = Path(str(_corpo(corpo).get("pasta") or "")).resolve()
    if not pasta.is_dir() or not pasta.is_relative_to(Path(SAIDA).resolve()):
        raise ValueError("Só abro pastas do Pacote do Dia.")
    _abrir(pasta)
    return {"ok": True}


@rotas.get("/api/aprendizado/contadores")
def contadores():
    from picorte.services.saude import benchmark
    return P.contadores_aprendizado(_db(), benchmark(BENCHMARKS))
