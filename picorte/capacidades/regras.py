"""Sondas → status real das capacidades que dependem do ambiente (SIS-1, 6, 7, 8, 11, 14)."""
from __future__ import annotations

from dataclasses import replace

from picorte.capacidades.modelo import Capacidade
from picorte.capacidades.sondas import ResultadoSonda

NAO_VERIFICADA = ResultadoSonda(False, "sonda não executada", {}, None)


def _com(cap: Capacidade, status: str, tipo: str | None, motivo: str, falta: tuple[str, ...],
         sonda: ResultadoSonda, dados: dict | None) -> Capacidade:
    return replace(cap, status=status, tipo_motivo=tipo, motivo=motivo, falta=falta,
                   verificado_em=sonda.verificado_em, dados=dados)


def aplicar_regras(cap: Capacidade, sondas: dict[str, ResultadoSonda]) -> Capacidade:
    s = lambda nome: sondas.get(nome, NAO_VERIFICADA)  # noqa: E731
    if cap.id == "SIS-1":
        g = s("gpu")
        if g.ok:
            return _com(cap, "ligado", None, g.detalhe, (), g, g.dados)
        return _com(cap, "parcial", "config", f"{g.detalhe}; o motor roda em CPU",
                    ("instalar driver NVIDIA ou usar a máquina com GPU",), g, None)
    if cap.id == "SIS-6":
        o = s("ollama")
        if o.ok and o.dados.get("modelos"):
            return _com(cap, "ligado", None, o.detalhe, (), o, o.dados)
        if o.ok:
            return _com(cap, "parcial", "config", "Ollama no ar, mas sem modelos instalados",
                        ("ollama pull do modelo do Editor-Chefe",), o, o.dados)
        return _com(cap, "travado", "config", o.detalhe, ("iniciar o Ollama",), o, None)
    if cap.id == "SIS-7":
        a = s("agy")
        if not a.dados.get("presente"):
            return _com(cap, "travado", "config", a.detalhe, ("instalar a CLI agy ou gemini",), a, None)
        if a.dados.get("ultima_falha"):
            return _com(cap, "parcial", "temporario", a.detalhe,
                        ("esperar a cota do Gemini renovar ou trocar de motor",), a, a.dados)
        return _com(cap, "ligado", None, a.detalhe, (), a, a.dados)
    if cap.id == "SIS-8":
        c = s("claude")
        if c.ok:
            return _com(cap, "ligado", None, c.detalhe, (), c, c.dados)
        return _com(cap, "travado", "config", c.detalhe, ("instalar o Claude CLI",), c, None)
    if cap.id == "SIS-11":
        y = s("yt-dlp")
        faltando = [n for n in ("yt-dlp", "node", "demucs") if not s(n).ok]
        dados = {n: s(n).dados.get("caminho") for n in ("yt-dlp", "node", "demucs")}
        if not y.ok:
            return _com(cap, "travado", "config", "yt-dlp ausente: nada é baixado",
                        tuple(f"instalar {n}" for n in faltando), y, None)
        if faltando:
            return _com(cap, "parcial", "config", "faltando: " + ", ".join(faltando),
                        tuple(f"instalar {n}" for n in faltando), y, dados)
        return _com(cap, "ligado", None, "yt-dlp, node e demucs encontrados", (), y, dados)
    if cap.id == "SIS-14":
        d = s("disco")
        if d.ok:
            return _com(cap, "ligado", None, d.detalhe, (), d, d.dados)
        return _com(cap, "parcial", "temporario", d.detalhe, ("liberar espaço em disco",), d, d.dados)
    return cap
