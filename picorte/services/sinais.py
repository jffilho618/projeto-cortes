"""Notas por sinal e veredito P1 por corte, só quando medidos (B2/B3 da história 6.4, convenção A5)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _numero(valor: Any) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return float(valor)


def sinais_medidos(seg: dict[str, Any]) -> dict[str, float | None]:
    """Cada sinal só sai com número se foi medido; senão None (NULL no banco, "não medido" na tela)."""
    ev = seg.get("evidence") if isinstance(seg.get("evidence"), dict) else {}
    partes = seg.get("score_parts") if isinstance(seg.get("score_parts"), dict) else {}
    chat = _numero(ev.get("chat")) if ev.get("chat_measured") is True else None
    visual = _numero(ev.get("visual"))
    if visual is None and ev.get("vision_measured") is True:
        visual = _numero(ev.get("visual_games"))  # sem a marca, visual_games só herda a nota geral
    return {
        "score_chat": chat,
        "score_audio": _numero(ev.get("audio")),
        "score_visual": visual,
        "score_text": _numero(partes.get("text_score")),
    }


def _meta(mp4: str | Path) -> dict[str, Any]:
    caminho = Path(mp4).with_suffix(".meta.json")
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def veredito_do_corte(mp4: str | Path) -> dict[str, Any] | None:
    """Veredito P1 gravado no .meta.json pelo attach_risk_verdict; None quando o corte nunca foi auditado."""
    veredito = _meta(mp4).get("risk_verdict")
    if not isinstance(veredito, dict) or not veredito.get("overall_status"):
        return None
    ypp = veredito.get("ypp_score")
    return {
        "risk_status": str(veredito["overall_status"]),
        "ypp_transform_score": int(ypp) if isinstance(ypp, (int, float)) and not isinstance(ypp, bool) else None,
        "phash_signature": str(veredito.get("phash_signature") or ""),
    }


def miniatura_do_corte(mp4: str | Path) -> str:
    return str(_meta(mp4).get("thumbnail_1280x720") or "")
