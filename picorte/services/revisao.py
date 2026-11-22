"""Fila e Revisão (história 6.6): linhas da fila em PT-BR e a ficha de cada corte, só com o que foi medido.

Só leitura de projects/. Sinal não medido sai com o motivo, nunca com zero (A5).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from picorte.services.mesa import _eh_p1
from picorte.services.sinais import sinais_medidos

ESTADOS = {"queued": "Na fila", "failed": "Falhou", "interrupted": "Interrompido", "new": "Criado",
           "review": "Pronto para revisar", "complete": "Pronto"}
PASSOS = {"source": "Baixando", "transcribe": "Transcrevendo", "discover": "Escolhendo cortes",
          "select": "Escolhendo cortes", "waiting": "Na fila"}
ORDEM_TIER = {"ouro": 0, "forte": 1, "experimental": 2}
NOMES_SINAL = {"chat": "Chat", "audio": "Energia do áudio", "visual": "Visão (facecam e HUD)", "texto": "Texto"}
CHAVE_SINAL = {"chat": "score_chat", "audio": "score_audio", "visual": "score_visual", "texto": "score_text"}
PARTE_SAUDE = {"chat": "chat", "visual": "vision", "audio": "prosody", "texto": "editor"}
CONCORDA = 5.0  # meio da escala 0–10: sinal medido a partir daqui conta a favor na ordem padrão


def _ler(caminho: Path, padrao: Any) -> Any:
    try:
        return json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return padrao


def estagio_pt(status: str | None, stage: str | None) -> str:
    if status in ESTADOS:
        return ESTADOS[status]
    passo = str(stage or "")
    if passo.startswith("render"):
        return "Renderizando"
    return PASSOS.get(passo, "Rodando")


def _progresso(estado: dict[str, Any]) -> dict[str, int] | None:
    p = estado.get("progress") or {}
    feito, total = int(p.get("done") or 0), int(p.get("total") or 0)
    if total <= 0:
        m = re.search(r"(\d+)\s*/\s*(\d+)", str(p.get("stage") or ""))
        if m:
            feito, total = int(m.group(1)), int(m.group(2))
    return {"feito": feito, "total": total} if total > 0 and estado.get("status") == "running" else None


def _falha(estado: dict[str, Any]) -> dict[str, str] | None:
    status, erro = estado.get("status"), str(estado.get("error") or "")
    if status == "interrupted":
        return {"motivo": erro or "O job parou antes de terminar.", "acao": "retomar"}
    if status != "failed":
        return None
    if _eh_p1(erro):
        return {"motivo": erro, "acao": "cadastrar_fonte"}
    baixo = erro.lower()
    if any(m in baixo for m in ("agy", "gemini", "ollama", "claude", "editor-chefe")):
        return {"motivo": erro, "acao": "trocar_motor"}
    return {"motivo": erro or "O job falhou sem mensagem.", "acao": "retomar"}


def _titulo(estado: dict[str, Any]) -> str:
    meta = estado.get("source_meta") or {}
    fonte = str(estado.get("source") or "")
    return str(meta.get("title") or (Path(fonte).name if fonte and "://" not in fonte else fonte) or estado.get("id"))


def linha_da_fila(estado: dict[str, Any]) -> dict[str, Any]:
    meta = estado.get("source_meta") or {}
    portao = estado.get("source_gate") or {}
    opcoes = estado.get("options") or {}
    return {
        "id": estado.get("id"),
        "titulo": _titulo(estado),
        "streamer": portao.get("source_name") or meta.get("channel"),
        "jogo": meta.get("detected_game") or None,
        "status": estado.get("status"),
        "estagio": estagio_pt(estado.get("status"), estado.get("stage")),
        "progresso": _progresso(estado),
        "motor": opcoes.get("ai_mode"),
        "prova": bool(opcoes.get("benchmark_blind")),
        "criado_em": estado.get("created"),
        "fonte_url": estado.get("source"),
        "falha": _falha(estado),
    }


def _sinais(seg: dict[str, Any], saude: dict[str, Any], pasta: Path) -> list[dict[str, Any]]:
    medidos = sinais_medidos(seg)
    saida = []
    for chave, nome in NOMES_SINAL.items():
        valor = medidos[CHAVE_SINAL[chave]]
        parte = saude.get(PARTE_SAUDE[chave]) if isinstance(saude.get(PARTE_SAUDE[chave]), dict) else {}
        if valor is not None:
            saida.append({"chave": chave, "nome": nome, "estado": "medido", "valor": valor, "motivo": ""})
            continue
        if parte.get("status") == "failed":
            saida.append({"chave": chave, "nome": nome, "estado": "falhou", "valor": None,
                          "motivo": str(parte.get("detail") or "a medição falhou")})
            continue
        if parte.get("status") == "na" and parte.get("detail"):
            motivo = str(parte["detail"])
        elif chave == "chat" and not (pasta / "chat.json").exists():
            motivo = "vídeo sem chat"
        elif chave == "visual":
            motivo = "a visão não rodou"
        elif chave == "audio" and not (pasta / "audio_features.npz").exists():
            motivo = "energia do áudio não registrada"
        elif chave == "texto" and seg.get("track_origin") == "full_vod_scout":
            motivo = "escolhido pelo Scout, sem nota de texto"
        else:
            motivo = "não medido neste corte"
        saida.append({"chave": chave, "nome": nome, "estado": "nao_medido", "valor": None, "motivo": motivo})
    return saida


def _arquivo(pasta: Path, sub: str, seg_id: str, sufixo: str) -> str | None:
    for f in sorted((pasta / sub).glob(f"{seg_id}-*{sufixo}")):
        if f.name.split("-", 1)[0] == seg_id:
            return f"/media/{pasta.name}/{sub}/{f.name}"
    return None


def _p1(pasta: Path, seg_id: str) -> dict[str, Any]:
    for meta in sorted((pasta / "clips").glob(f"{seg_id}-*.meta.json")):
        veredito = _ler(meta, {}).get("risk_verdict")
        if isinstance(veredito, dict) and veredito.get("overall_status"):
            return {"sem_veredito": False, "geral": veredito["overall_status"],
                    "por_rede": dict(veredito.get("per_platform") or {})}
    return {"sem_veredito": True, "geral": None, "por_rede": {}}


def montar_revisao(pasta: Path, estado: dict[str, Any], decisoes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pasta = Path(pasta)
    segmentos = _ler(pasta / "segments.json", [])
    segmentos = segmentos if isinstance(segmentos, list) else []
    saude = _ler(pasta / "engine_health.json", {})
    saude = saude if isinstance(saude, dict) else {}
    meta = estado.get("source_meta") or {}
    cortes = []
    for n, seg in enumerate(segmentos, 1):
        if not isinstance(seg, dict):
            continue
        seg_id = str(seg.get("id") or f"{n:03}")
        sinais = _sinais(seg, saude, pasta)
        d = decisoes.get(seg_id) or {}
        cortes.append({
            "n": n, "seg": seg_id,
            "start": float(seg.get("start") or 0), "end": float(seg.get("end") or 0),
            "titulo": str(seg.get("proposed_title") or seg.get("hook") or f"Corte {n}"),
            "hook": str(seg.get("hook") or ""),
            "arquetipo": seg.get("archetype"), "tier": seg.get("tier"),
            "faixa_2s": str(seg.get("context_banner_2s") or ""),
            "comentario": str(seg.get("pinned_comment_debate") or ""),
            "motivo": str(seg.get("why_extraordinary") or seg.get("reason") or ""),
            "sinais": sinais,
            "p1": _p1(pasta, seg_id),
            "render": {"clip": _arquivo(pasta, "clips", seg_id, ".mp4"),
                       "preview": _arquivo(pasta, "previews", seg_id, ".preview.mp4")},
            "decisao": {"rotulo": d.get("rotulo"), "motivo": d.get("motivo") or "",
                        "descartado": bool(d.get("descartado")), "exemplo_ouro": bool(d.get("exemplo_ouro"))},
            "_concordam": sum(1 for s in sinais if s["estado"] == "medido" and (s["valor"] or 0) >= CONCORDA),
        })
    cortes.sort(key=lambda c: (ORDEM_TIER.get(str(c["tier"]), 3), -c["_concordam"], c["n"]))
    for c in cortes:
        c.pop("_concordam")
    transcricao = _ler(pasta / "transcript.json", {})
    video = (transcricao.get("video") if isinstance(transcricao, dict) else None) or estado.get("video")
    resumo = [f"{parte}: {info.get('detail') or info.get('status')}" for parte, info in saude.items()
              if isinstance(info, dict) and info.get("status") in {"failed", "na"}]
    return {
        "projeto": {
            "id": estado.get("id") or pasta.name, "titulo": _titulo(estado),
            "streamer": (estado.get("source_gate") or {}).get("source_name") or meta.get("channel"),
            "jogo": meta.get("detected_game") or None, "motor": (estado.get("options") or {}).get("ai_mode"),
            "prova": bool((estado.get("options") or {}).get("benchmark_blind")), "n_cortes": len(cortes),
            "duracao_s": meta.get("duration"), "fonte_url": estado.get("source"),
            "video_local": bool(video and Path(str(video)).is_file()),
            "energia": (pasta / "audio_features.npz").is_file(), "resumo_saude": resumo,
        },
        "cortes": cortes,
    }
