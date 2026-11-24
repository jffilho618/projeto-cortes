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

ESTADOS = {"queued": "Na fila", "failed": "Falhou", "cancelled": "Cancelado", "interrupted": "Interrompido", "new": "Criado",
           "review": "Pronto para revisar", "complete": "Pronto"}
PASSOS = {"source": "Baixando", "transcribe": "Transcrevendo", "discover": "Escolhendo cortes",
          "select": "Escolhendo cortes", "waiting": "Na fila"}
ORDEM_TIER = {"ouro": 0, "forte": 1, "experimental": 2}
NOMES_SINAL = {"chat": "Chat", "audio": "Energia do áudio", "visual": "Visão (facecam e HUD)", "texto": "Texto"}
CHAVE_SINAL = {"chat": "score_chat", "audio": "score_audio", "visual": "score_visual", "texto": "score_text"}
# "audio": o motor grava a parte própria desde o code review de 2026-11-23 (antes o painel olhava a prosódia)
PARTE_SAUDE = {"chat": "chat", "visual": "vision", "audio": "audio", "texto": "editor"}
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
    if status == "cancelled":  # parou a pedido do operador: não é falha, mas o próximo passo é o mesmo (Retomar)
        return {"motivo": erro or "Cancelado pelo operador.", "acao": "retomar"}
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


PARTES_ALERTA = ("full_vod_scout", "editor")  # falham sem derrubar o job: lote parcial, 2ª passada, batedor


def saude_atual(pasta: Path) -> dict[str, Any]:
    """W32: só as partes da última execução (marca `_execucao` do motor)."""
    from picorte.engine.health import partes_da_execucao
    dados = _ler(Path(pasta) / "engine_health.json", {})
    return partes_da_execucao(dados if isinstance(dados, dict) else {})


def alertas_da_saude(pasta: Path) -> list[dict[str, str]]:
    from picorte.services.saude import rotulo_parte
    saude = saude_atual(pasta)
    return [{"parte": rotulo_parte(p), "detalhe": str(saude[p].get("detail") or "falhou")}
            for p in PARTES_ALERTA if (saude.get(p) or {}).get("status") == "failed"]


def _redes(estado: dict[str, Any]) -> list[str] | None:
    """Redes que o projeto gera (opção `redes` do motor, 2026-11-23); projeto antigo não tem: None."""
    redes = (estado.get("options") or {}).get("redes")
    return [str(r) for r in redes] if isinstance(redes, list) and redes else None


def linha_da_fila(estado: dict[str, Any], alertas: list[dict[str, str]] | None = None) -> dict[str, Any]:
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
        "alertas": alertas or [],
        "redes": _redes(estado),
        "acao": estado.get("acao_pedida") if estado.get("acao_pedida") in {"prepare", "render", "all"} else "prepare",
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
        if (chave == "visual" and (saude.get("vision") or {}).get("status") in {"ok", "failed"}
                and (seg.get("evidence") or {}).get("vision_measured") is not True):
            # a visão rodou, mas só analisa os primeiros candidatos: este ficou de fora (não é falha nem "não rodou");
            # com a visão "na" (não rodou), o motivo da saúde vale, como antes
            saida.append({"chave": chave, "nome": nome, "estado": "nao_medido", "valor": None,
                          "motivo": "a visão não analisou este corte"})
            continue
        if parte.get("status") == "failed":
            from picorte.services.saude import degradacao_conhecida
            detalhe = str(parte.get("detail") or "a medição falhou")
            aviso = degradacao_conhecida(PARTE_SAUDE[chave], "failed", detalhe)
            saida.append({"chave": chave, "nome": nome, "estado": "falhou", "valor": None,
                          "motivo": f"{detalhe}. {aviso}" if aviso else detalhe})
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


PORTOES_P1 = {
    "source_permission": "Permissão da fonte", "publisher_policy": "Política do publisher",
    "green_seal_15s": "Selo Verde 15s", "react_guard": "React perigoso", "music_surgeon": "Música licenciada",
    "ypp_and_dedup": "YPP e duplicata",
}
_PESO_P1 = {"pass": 0, "auto_fixed": 0, "human_review": 1, "hard_block": 2, "audit_error": 2}
_SEM_MOTIVO = {1: "revisão humana pedida pelo P1 (motivo não registrado)", 2: "barrado pelo P1 (motivo não registrado)"}


def _peso(status: Any) -> int:
    return _PESO_P1.get(str(status or ""), 2)  # status desconhecido conta como barrado (falha fechada)


def motivos_do_veredito(veredito: dict[str, Any]) -> dict[str, Any]:
    """Por que o P1 barrou, só com o texto gravado no risk_verdict (nada inventado).

    Os portões valem para todas as redes; o motivo próprio de cada rede vem de `per_platform_reasons` (vereditos
    antigos não têm: rede pior que os portões fica "motivo não registrado"). A lista por rede só aparece quando
    as redes diferem.
    """
    if veredito.get("overall_status") == "audit_error":
        return {"motivos": [{"portao": "Auditoria", "texto": str(veredito.get("error") or _SEM_MOTIVO[2])}],
                "motivos_por_rede": {}}
    gerais, pior = [], 0
    for nome, g in (veredito.get("gates") or {}).items():
        peso = _peso((g or {}).get("status"))
        if peso == 0:
            continue
        pior = max(pior, peso)
        textos = list((g or {}).get("reasons") or []) or ([g["reason"]] if (g or {}).get("reason") else [])
        portao = PORTOES_P1.get(nome, nome.replace("_", " "))
        gerais += [{"portao": portao, "texto": str(t)} for t in textos] or [{"portao": portao, "texto": _SEM_MOTIVO[peso]}]
    redes = veredito.get("per_platform") or {}
    if not redes:
        return {"motivos": gerais, "motivos_por_rede": {}}
    gravados = veredito.get("per_platform_reasons") or {}  # vereditos antigos não têm: "motivo não registrado"
    por_rede = {}
    for rede, status in redes.items():
        peso = _peso(status)
        itens = gerais if peso else []
        proprios = [{"portao": "Esta rede", "texto": str(t)} for t in (gravados.get(rede) or [])]
        if proprios:
            itens = itens + proprios
        elif peso > pior:
            itens = itens + [{"portao": "Esta rede", "texto": _SEM_MOTIVO[peso]}]
        por_rede[rede] = itens
    listas = list(por_rede.values())
    if all(l == listas[0] for l in listas):
        return {"motivos": listas[0], "motivos_por_rede": {}}
    return {"motivos": [], "motivos_por_rede": por_rede}


def _p1(pasta: Path, seg_id: str) -> dict[str, Any]:
    for meta in sorted((pasta / "clips").glob(f"{seg_id}-*.meta.json")):
        veredito = _ler(meta, {}).get("risk_verdict")
        if isinstance(veredito, dict) and veredito.get("overall_status"):
            return {"sem_veredito": False, "geral": veredito["overall_status"],
                    "por_rede": dict(veredito.get("per_platform") or {}), **motivos_do_veredito(veredito)}
    return {"sem_veredito": True, "geral": None, "por_rede": {}, "motivos": [], "motivos_por_rede": {}}


EXTENSOES_VIDEO = {".mp4", ".webm", ".mkv", ".mov"}


def fonte_so_audio(video: Any) -> bool:
    """Live longa: o motor baixa só o áudio (audio.*); tocar a fonte deixa a tela preta."""
    return bool(video) and Path(str(video)).name.lower().startswith("audio.")


def imagem_proxy(pasta: Path) -> Path | None:
    """Proxy leve da descoberta (discovery.*, 240p, sem som): dá imagem a uma fonte que é só áudio."""
    achados = sorted(f for f in Path(pasta).glob("discovery.*") if f.suffix.lower() in EXTENSOES_VIDEO and f.is_file())
    return achados[0] if achados else None


def _duracao(seg: dict[str, Any]) -> float:
    d = seg.get("duration")
    if isinstance(d, (int, float)) and d > 0:
        return round(float(d), 2)
    return round(float(seg.get("end") or 0) - float(seg.get("start") or 0), 2)


def montar_revisao(pasta: Path, estado: dict[str, Any], decisoes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pasta = Path(pasta)
    segmentos = _ler(pasta / "segments.json", [])
    segmentos = segmentos if isinstance(segmentos, list) else []
    saude = saude_atual(pasta)
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
            # formato (short/vertical_longo/tiktok_60/longo_16x9/compilacao/arco_2_atos) e família (moment_id);
            # composto: a duração é a soma dos trechos (campo duration), não end - start, que cobre a live inteira
            "formato": seg.get("formato") if isinstance(seg.get("formato"), str) else None,
            "moment_id": seg.get("moment_id") if isinstance(seg.get("moment_id"), str) else None,
            "duracao": _duracao(seg),
            "trechos": [{"start": float(t["start"]), "end": float(t["end"])} for t in seg.get("trechos") or []
                        if isinstance(t, dict) and "start" in t and "end" in t],
            "titulo": str(seg.get("proposed_title") or seg.get("hook") or f"Corte {n}"),
            "hook": str(seg.get("hook") or ""),
            "arquetipo": seg.get("archetype"), "tier": seg.get("tier"),
            "faixa_2s": str(seg.get("context_banner_2s") or ""),
            "comentario": str(seg.get("pinned_comment_debate") or ""),
            "motivo": str(seg.get("why_extraordinary") or seg.get("reason") or ""),
            "sinais": sinais,
            "p1": _p1(pasta, seg_id),
            "standalone": seg.get("standalone") if isinstance(seg.get("standalone"), (int, float)) else None,
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
    from picorte.services.saude import confianca_do_projeto, degradacao_conhecida, rotulo_parte
    resumo = []
    for parte, info in saude.items():
        if isinstance(info, dict) and info.get("status") in {"failed", "na"}:
            detalhe = str(info.get("detail") or info.get("status"))
            aviso = degradacao_conhecida(parte, str(info.get("status")), detalhe)
            resumo.append(f"{rotulo_parte(parte)}: {aviso} ({detalhe})" if aviso else f"{rotulo_parte(parte)}: {detalhe}")
    pedem_voce = sum(1 for c in cortes if c["p1"].get("geral") == "human_review")
    return {
        "projeto": {
            "id": estado.get("id") or pasta.name, "titulo": _titulo(estado),
            "streamer": (estado.get("source_gate") or {}).get("source_name") or meta.get("channel"),
            "jogo": meta.get("detected_game") or None, "motor": (estado.get("options") or {}).get("ai_mode"),
            "prova": bool((estado.get("options") or {}).get("benchmark_blind")), "n_cortes": len(cortes),
            "duracao_s": meta.get("duration"), "fonte_url": estado.get("source"),
            "video_local": bool(video and Path(str(video)).is_file()),
            "fonte_so_audio": fonte_so_audio(video),
            "imagem_proxy": bool(fonte_so_audio(video) and imagem_proxy(pasta)),
            "energia": (pasta / "audio_features.npz").is_file(), "resumo_saude": resumo, "pedem_voce": pedem_voce,
            "confianca": confianca_do_projeto(saude),
            "redes": _redes(estado),
        },
        "cortes": cortes,
    }
