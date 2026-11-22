"""Saúde do motor e benchmark (história 6.7). Só leitura de projects/ e benchmarks/."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from picorte.services.revisao import _titulo

META_GABARITOS = 20  # história 3.6.6: pesos calibrados a partir de 20 VODs com gabarito
AMOSTRA_MINIMA = 3


def _ler(caminho: Path) -> Any:
    try:
        return json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _resumo(celulas: dict[str, dict[str, str]]) -> str:
    if not celulas:
        return "saúde não registrada (projeto anterior ao registro)"
    falhas = sorted(p for p, c in celulas.items() if c["status"] == "failed")
    na = sum(1 for c in celulas.values() if c["status"] == "na")
    ok = sum(1 for c in celulas.values() if c["status"] == "ok")
    partes = []
    if falhas:
        partes.append(f"{len(falhas)} parte{'s' if len(falhas) > 1 else ''} falh{'aram' if len(falhas) > 1 else 'ou'} ({', '.join(falhas)})")
    if na:
        partes.append(f"{na} não se aplica{'m' if na > 1 else ''}")
    if ok:
        partes.append(f"{ok} ok")
    return " · ".join(partes)


def matriz_motor(raiz: Path, projetos: list[dict[str, Any]]) -> dict[str, Any]:
    linhas, partes = [], set()
    for p in projetos:
        dados = _ler(Path(raiz) / str(p.get("id")) / "engine_health.json")
        celulas = {}
        if isinstance(dados, dict):
            for parte, info in dados.items():
                if isinstance(info, dict) and info.get("status"):
                    celulas[parte] = {"status": str(info["status"]), "detalhe": str(info.get("detail") or "")}
        partes.update(celulas)
        linhas.append({"id": p.get("id"), "titulo": _titulo(p), "resumo": _resumo(celulas), "celulas": celulas})
    return {"partes": sorted(partes), "projetos": linhas}


def benchmark(pasta: Path) -> dict[str, Any]:
    pasta = Path(pasta)
    versoes = []
    for arquivo in sorted(pasta.glob("*.json")) if pasta.is_dir() else []:
        dados = _ler(arquivo)
        media = dados.get("media") if isinstance(dados, dict) else None
        if not isinstance(media, dict) or not isinstance(media.get("k"), dict):
            continue
        n = int(media.get("vods_com_gabarito") or 0)
        versoes.append({
            "label": str(dados.get("label") or arquivo.stem), "data": str(dados.get("data") or ""), "n": n,
            "amostra_pequena": n < AMOSTRA_MINIMA,
            "ks": {k: {"precisao": v.get("precisao"), "acaso": v.get("precisao_acaso"), "lift": v.get("lift")}
                   for k, v in media["k"].items() if isinstance(v, dict)},
            "arquivo": arquivo.name,
        })
    versoes.sort(key=lambda v: (v["data"], v["arquivo"]), reverse=True)
    gabaritos = len(list((pasta / "gabaritos").glob("*.json"))) if (pasta / "gabaritos").is_dir() else 0
    return {"versoes": versoes, "gabaritos": gabaritos, "meta": META_GABARITOS}
