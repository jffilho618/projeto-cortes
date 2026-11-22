"""Faixa "Na sua mesa" (história 6.5): pendências reais do dia, montadas da fila do Estúdio."""
from __future__ import annotations

from typing import Any


def _eh_p1(erro: str) -> bool:
    return erro.startswith("[P1") or "Fonte desconhecida" in erro or "Nada foi baixado" in erro


def _proximo_passo(projeto: dict[str, Any]) -> str:
    erro = str(projeto.get("error") or "").lower()
    if projeto.get("status") == "interrupted":
        return "Retomar"
    if "agy" in erro or "gemini" in erro or "ollama" in erro or "claude" in erro or "editor-chefe" in erro:
        return "Trocar o motor de IA e retomar"
    return "Ver o detalhe e retomar"


def na_sua_mesa(projetos: list[dict[str, Any]], links_pendentes: int | None = None) -> dict[str, Any]:
    pede_voce, falhas = [], []
    for p in projetos:
        status, erro = p.get("status"), str(p.get("error") or "")
        if status == "failed" and _eh_p1(erro):
            pede_voce.append({"projeto": p.get("id"), "motivo": erro})
        elif status in {"failed", "interrupted"}:
            falhas.append({"projeto": p.get("id"), "motivo": erro or "O job parou antes de terminar.",
                           "proximo_passo": _proximo_passo(p)})
    rodando = next((p for p in projetos if p.get("status") == "running"), None)
    return {
        "pede_voce": pede_voce,
        "revisar": sum(1 for p in projetos if p.get("status") == "review"),
        "na_fila": {"n": sum(1 for p in projetos if p.get("status") in {"queued", "running"}),
                    "estagio": (rodando or {}).get("stage")},
        "falhas": falhas,
        "links_pendentes": links_pendentes,  # C2: exportado sem link (história 6.8); None = banco ilegível (A5)
        "links_pendentes_motivo": "" if links_pendentes is not None else "Não consegui contar os links pendentes no banco.",
    }
