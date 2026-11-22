"""Rotas de projetos do Estúdio: leitura (sem escrita), mídia com Range e ações explícitas."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Body, Request
from fastapi.responses import FileResponse, JSONResponse

import projects
from picorte.services.job_lock import ProjetoOcupado
from picorte.services.projeto_detalhe import detalhe_projeto

rotas = APIRouter()
PASTAS_MIDIA = {"clips", "previews"}
EXTENSOES_MIDIA = {".mp4", ".srt", ".png", ".json"}


@rotas.get("/api/projetos")
def listar(request: Request):
    return {"projetos": request.app.state.fila.listar()}


@rotas.get("/api/projetos/{pid}")
def detalhe(pid: str, request: Request):
    fila = request.app.state.fila
    dados = detalhe_projeto(request.app.state.raiz, pid)
    dados["project"] = fila.estado(pid)
    dados["busy"] = fila.ocupado(pid)
    return dados


@rotas.get("/media/{pid}/source")
def video_fonte(pid: str, request: Request):
    path = projects.project_path(request.app.state.raiz, pid).resolve()
    fonte = Path(projects.read_json(path / "transcript.json")["video"])
    if not fonte.is_file():
        raise FileNotFoundError(fonte)
    return FileResponse(fonte)


@rotas.get("/media/{pid}/{pasta}/{arquivo}")
def midia(pid: str, pasta: str, arquivo: str, request: Request):
    path = projects.project_path(request.app.state.raiz, pid).resolve()
    if pasta not in PASTAS_MIDIA:
        raise ValueError("Pasta de mídia desconhecida.")
    alvo = (path / pasta / arquivo).resolve()
    if alvo.parent != path / pasta or alvo.suffix not in EXTENSOES_MIDIA:
        raise ValueError("Caminho de mídia inválido.")
    if not alvo.is_file():
        raise FileNotFoundError(alvo)
    return FileResponse(alvo)


REDES_MANUAIS = {"youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"}
ACOES_LIVRES = {"mark-posted", "open-folder", "export-bundle"}  # não editam o projeto
NOME_MARCA = re.compile(r"[a-zA-Z0-9_-]{1,60}")


def _corpo(corpo) -> dict:
    if not isinstance(corpo, dict):
        raise ValueError("Esperado um objeto JSON.")
    return corpo


@rotas.post("/api/projetos", status_code=201)
def criar(request: Request, corpo: dict = Body(...)):
    corpo = _corpo(corpo)
    return projects.create_project(request.app.state.raiz, corpo["source"], corpo.get("options", {}))


@rotas.post("/api/lote", status_code=201)
def lote(request: Request, corpo: dict = Body(...)):
    corpo = _corpo(corpo)
    fontes = corpo.get("sources")
    if (not isinstance(fontes, list) or not 1 <= len(fontes) <= 100
            or any(not isinstance(f, str) or not f.strip() for f in fontes)):
        raise ValueError("Envie de 1 a 100 fontes.")
    opcoes = projects.validate_options(corpo.get("options", {}))
    acao = corpo.get("acao", "prepare")  # "all" = renderizar sozinho os aprovados pelos portões (padrão da Sala)
    if acao not in {"prepare", "all"}:
        raise ValueError("acao precisa ser prepare (esperar minha revisão) ou all (renderizar sozinho).")
    criados = []
    for fonte in fontes:
        estado = projects.create_project(request.app.state.raiz, fonte, opcoes)
        request.app.state.fila.enfileirar(estado["id"], acao)
        criados.append(estado)
    return {"projetos": criados}


@rotas.post("/api/projetos/{pid}/{acao}")
def acao_projeto(pid: str, acao: str, request: Request, corpo: dict = Body(default_factory=dict)):
    corpo = _corpo(corpo)
    raiz = request.app.state.raiz
    fila = request.app.state.fila
    path = projects.project_path(raiz, pid)
    estado = projects.read_project(path)
    if acao not in ACOES_LIVRES and fila.ocupado(pid):
        raise ProjetoOcupado("Espere o job deste projeto terminar antes de editar.")
    if acao == "settings":
        ajustes = dict(corpo)
        if "brand_name" in ajustes:
            nome = ajustes.pop("brand_name")
            if nome and (not isinstance(nome, str) or not NOME_MARCA.fullmatch(nome)):
                raise ValueError("Marca inválida.")
            ajustes["brand"] = str(raiz / "brands" / f"{nome}.json") if nome else None
        estado["options"] = projects.validate_options({**estado["options"], **ajustes})
        projects.save_project(path, estado)
    elif acao == "transcript":
        projects.edit_transcript(path, corpo["words"])
    elif acao == "candidates":
        duracao = projects.read_json(path / "transcript.json")["duration"]
        projects.atomic_json(path / "segments.json",
                             projects.validate_segments(corpo["candidates"], duracao))
    elif acao == "run":
        fila.enfileirar(pid, corpo.get("action", "prepare"), corpo.get("preview", False),
                        corpo.get("pick"))
    elif acao == "mark-posted":
        stem = str(corpo.get("clip_stem") or "").strip()
        rede = str(corpo.get("platform") or "").strip()
        if not stem or rede not in REDES_MANUAIS:
            raise ValueError("Informe um clip_stem e uma rede válidos.")
        from picorte.services.studio_service import StudioService
        pub = StudioService().record_manual_publication(
            project_id=pid, clip_stem=stem, platform=rede,
            external_url=str(corpo.get("external_url") or "").strip(),
            source_url=str(estado.get("source") or ""))
        return {"ok": True, "publication": pub}
    elif acao == "export-bundle":
        from dashboard import _open_in_file_manager
        from picorte.engine.publish_kit import export_daily_bundle
        stems = corpo.get("clip_stems")
        pacote = export_daily_bundle(path, clip_stems=stems if isinstance(stems, list) else None,
                                     out_root=corpo.get("out_root"),
                                     per_day=int(corpo.get("per_day") or 3))
        if corpo.get("open_folder", True):
            _open_in_file_manager(Path(pacote["bundle_dir"]))
        return {"ok": True, **pacote}
    elif acao == "open-folder":
        from dashboard import _open_in_file_manager
        nome = str(corpo.get("file") or "").strip()
        tipo = str(corpo.get("kind") or "clips").strip()
        tipo = tipo if tipo in PASTAS_MIDIA else "clips"
        alvo = ((path / tipo / nome) if nome else (path / tipo)).resolve()
        if not alvo.is_relative_to(path.resolve()):
            raise ValueError("Caminho inválido.")
        if not alvo.exists():
            alvo = (path / tipo).resolve()
        _open_in_file_manager(alvo)
        return {"ok": True, "path": str(alvo)}
    else:
        return JSONResponse({"erro": "Não encontrado."}, status_code=404)
    return {"ok": True}
