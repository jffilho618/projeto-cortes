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


# Partes do engine_health.json na ordem do pipeline (descoberta → seleção → render), com rótulo para o operador.
ROTULOS_PARTE: dict[str, str] = {
    "visual_proxy": "Vídeo leve da descoberta", "chat_download": "Download do chat",
    "comments_download": "Download dos comentários", "comments": "Comentários", "heatmap": "Mais repetidos (heatmap)",
    "audio": "Energia do áudio", "silencio_digital": "Silêncio digital (P1)", "prosody": "Prosódia da voz",
    "chat": "Sismógrafo do chat", "chat_delay": "Atraso do chat", "comment_seeds": "Momentos dos comentários",
    "vision": "Visão (facecam e HUD)", "full_vod_scout": "Batedor do VOD inteiro",
    "modo_deep": "Modo deep (arcos e compilações)", "llm_rerank": "Reordenação por IA (--llm)",
    "editor": "Editor-Chefe", "keyframes": "Keyframes", "ouro_2_sinais": "Ouro com 2 sinais",
    "end_after_laugh": "Fim depois do riso", "seamless_loop": "Loop contínuo",
    "formatos_extras": "Versões TikTok e Longo", "composicoes": "Arcos e compilações",
    "confianca_projeto": "Confiança do projeto", "benchmark_gabarito": "Gabarito do benchmark",
    "benchmark_labels": "Rótulos do benchmark", "layout_dinamico": "Layout dinâmico", "cold_open": "Cold Open",
    "freeze": "Freeze com seta", "thumbnail": "Thumbnail", "banco": "Banco",
}
_ORDEM = {parte: i for i, parte in enumerate(ROTULOS_PARTE)}
_SINAIS_DEGRADACAO = ("degradado", "mediapipe", "rosto pequeno")


def confianca_do_projeto(saude: dict[str, Any]) -> dict[str, Any] | None:
    """SAU-2 (3.6.5): nota e sinais do `confianca_projeto` da saúde; ausente ou ilegível vira None (A5)."""
    parte = saude.get("confianca_projeto") if isinstance(saude, dict) else None
    try:
        dados = json.loads(str((parte or {}).get("detail") or ""))
    except ValueError:
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("nota"), (int, float)):
        return None
    return {"nota": dados["nota"], **{k: list(dados.get(k) or []) for k in ("sinais_ok", "sinais_falhos", "sinais_ausentes")}}


def rotulo_parte(parte: str) -> str:
    return ROTULOS_PARTE.get(parte, parte.replace("_", " "))


def degradacao_conhecida(parte: str, status: str, detalhe: str) -> str | None:
    """Visão degradada é falha real e conhecida: continua vermelha, com o porquê (code review do motor, W49)."""
    if parte == "vision" and status == "failed" and any(t in detalhe.lower() for t in _SINAIS_DEGRADACAO):
        return "Degradação conhecida: a emoção no rosto fica completa com a W49 (MAR)."
    return None


def _resumo(celulas: dict[str, dict[str, str]], anteriores: int = 0) -> str:
    if not celulas:
        return "saúde não registrada (projeto anterior ao registro)"
    falhas = [rotulo_parte(p) for p in sorted(celulas, key=lambda p: (_ORDEM.get(p, 999), p))
              if celulas[p]["status"] == "failed"]
    na = sum(1 for c in celulas.values() if c["status"] == "na")
    ok = sum(1 for c in celulas.values() if c["status"] == "ok")
    partes = []
    if falhas:
        partes.append(f"{len(falhas)} parte{'s' if len(falhas) > 1 else ''} falh{'aram' if len(falhas) > 1 else 'ou'} ({', '.join(falhas)})")
    if na:
        partes.append(f"{na} não se aplica{'m' if na > 1 else ''}")
    if ok:
        partes.append(f"{ok} ok")
    if anteriores:
        partes.append(f"{anteriores} de execução anterior fora")
    return " · ".join(partes)


def matriz_motor(raiz: Path, projetos: list[dict[str, Any]]) -> dict[str, Any]:
    """W32: só as partes da última execução (marca `_execucao` do motor); projeto sem marca mostra tudo."""
    from picorte.engine.health import partes_da_execucao

    linhas, partes = [], set()
    for p in projetos:
        dados = _ler(Path(raiz) / str(p.get("id")) / "engine_health.json")
        dados = dados if isinstance(dados, dict) else {}
        todas = {k: v for k, v in dados.items() if isinstance(v, dict) and v.get("status")}
        atuais = {k: v for k, v in partes_da_execucao(dados).items() if v.get("status")}
        celulas = {}
        for parte, info in atuais.items():
            status, detalhe = str(info["status"]), str(info.get("detail") or "")
            celulas[parte] = {"status": status, "detalhe": detalhe, "em": info.get("at"),
                              "conhecida": degradacao_conhecida(parte, status, detalhe)}
        partes.update(celulas)
        anteriores = len(todas) - len(atuais)
        linhas.append({"id": p.get("id"), "titulo": _titulo(p), "resumo": _resumo(celulas, anteriores),
                       "celulas": celulas, "anteriores": anteriores, "confianca": confianca_do_projeto(atuais)})
    ordem = sorted(partes, key=lambda p: (_ORDEM.get(p, 999), p))
    return {"partes": ordem, "rotulos": {p: rotulo_parte(p) for p in ordem}, "projetos": linhas}


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
