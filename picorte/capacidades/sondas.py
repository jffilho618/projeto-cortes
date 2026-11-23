"""Sondas do ambiente (Ollama, CLIs, GPU, disco, cota do Gemini) com cache por TTL."""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from picorte.capacidades.modelo import agora_iso
from picorte.config import probe_nvidia_smi, resolve_cli_binary
from picorte.engine import health


@dataclass(frozen=True)
class ResultadoSonda:
    ok: bool
    detalhe: str
    dados: dict[str, Any] = field(default_factory=dict)
    verificado_em: str = field(default_factory=agora_iso)


Sonda = Callable[[], ResultadoSonda]


class CacheSondas:
    def __init__(self, sondas: dict[str, tuple[float, Sonda]],
                 relogio: Callable[[], float] = time.monotonic) -> None:
        self._sondas = dict(sondas)
        self._relogio = relogio
        self._guardado: dict[str, tuple[float, ResultadoSonda]] = {}
        self._trava = threading.Lock()

    def obter(self, nome: str) -> ResultadoSonda:
        ttl, sonda = self._sondas[nome]
        agora = self._relogio()
        with self._trava:
            item = self._guardado.get(nome)
            if item is not None and agora - item[0] < ttl:
                return item[1]
        try:
            resultado = sonda()
        except Exception as exc:  # noqa: BLE001 - sonda quebrada não derruba o painel
            resultado = ResultadoSonda(False, f"sonda {nome} falhou: {exc}")
        with self._trava:
            self._guardado[nome] = (agora, resultado)
        return resultado

    def todas(self) -> dict[str, ResultadoSonda]:
        return {nome: self.obter(nome) for nome in self._sondas}


NOMES_SONDAS = ("gpu", "ollama", "agy", "claude", "yt-dlp", "node", "demucs", "disco")


def sonda_ollama(host: str | None = None, get=httpx.get) -> ResultadoSonda:
    host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    try:
        resposta = get(f"{host}/api/tags", timeout=1.5)
        resposta.raise_for_status()
        modelos = sorted(m["name"] for m in resposta.json().get("models", []) if m.get("name"))
    except (httpx.HTTPError, ValueError, KeyError, AttributeError) as exc:
        return ResultadoSonda(False, f"Ollama não respondeu em {host} ({exc.__class__.__name__})",
                              {"host": host})
    return ResultadoSonda(True, f"{len(modelos)} modelo(s) em {host}",
                          {"host": host, "modelos": modelos})


def sonda_binario(nome: str, resolver=resolve_cli_binary) -> ResultadoSonda:
    caminho = resolver(nome)
    if not caminho:
        return ResultadoSonda(False, f"{nome} não encontrado no PATH nem no .venv")
    return ResultadoSonda(True, f"{nome} em {caminho}", {"caminho": str(caminho)})


SEM_API_PAGA = "sem ele o Editor-Chefe para; não há troca automática para API paga (regra 6)"


def sonda_cli_ia(nome: str, resolver=resolve_cli_binary) -> ResultadoSonda:
    """CLI de assinatura (claude): sem ele, o painel diz a consequência em vez de sugerir API paga."""
    r = sonda_binario(nome, resolver=resolver)
    return r if r.ok else ResultadoSonda(False, f"{r.detalhe}; {SEM_API_PAGA}", r.dados)


def sonda_gpu(probe=probe_nvidia_smi) -> ResultadoSonda:
    vram, nome = probe()
    if vram <= 0:
        return ResultadoSonda(False, "nenhuma GPU NVIDIA detectada (nvidia-smi)")
    return ResultadoSonda(True, f"{nome} com {vram} MiB", {"gpu_name": nome, "vram_mib": int(vram)})


def sonda_disco(raiz, minimo_gib: float = 20.0) -> ResultadoSonda:
    alvo = Path(raiz).resolve()
    while not alvo.exists() and alvo != alvo.parent:
        alvo = alvo.parent
    livre = round(shutil.disk_usage(alvo).free / 1024 ** 3, 1)
    ok = livre >= minimo_gib
    detalhe = f"{livre} GiB livres" + ("" if ok else f" (abaixo de {minimo_gib} GiB)")
    return ResultadoSonda(ok, detalhe, {"livre_gib": livre})


def _ler_json(caminho: Path) -> dict:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def _falha_do_gemini(texto: str) -> bool:
    """429 explícito ou falha que cita a CLI do Gemini (o detail é cortado em 400 caracteres,
    então o "429" costuma ficar de fora: ex. CalledProcessError ... agy.exe)."""
    t = texto.lower()
    return "429" in t or "agy" in t or "gemini" in t


def _ultima_falha_gemini(raiz: Path, limite: datetime) -> str | None:
    """Varre (só leitura) os projetos mais recentes atrás de falha do Gemini depois de `limite`."""
    achados: list[datetime] = []
    pastas = sorted((p for p in raiz.glob("*") if p.is_dir()),
                    key=lambda p: p.stat().st_mtime, reverse=True)[:10]
    for pasta in pastas:
        for parte in health.load(pasta).values():
            if (isinstance(parte, dict) and parte.get("status") == "failed"
                    and _falha_do_gemini(str(parte.get("detail", "")))):
                try:
                    achados.append(datetime.fromisoformat(str(parte.get("at"))))
                except ValueError:
                    continue
        estado = _ler_json(pasta / "project.json")
        if _falha_do_gemini(str(estado.get("error") or "")) and estado.get("updated"):
            achados.append(datetime.fromtimestamp(float(estado["updated"]), tz=timezone.utc))
    recentes = [a for a in achados if a.tzinfo and a >= limite]
    return max(recentes).isoformat(timespec="seconds") if recentes else None


def sonda_agy(raiz, resolver=resolve_cli_binary, janela_h: float = 24.0,
              agora: datetime | None = None) -> ResultadoSonda:
    presente = bool(resolver("agy") or resolver("gemini"))
    limite = (agora or datetime.now(timezone.utc)) - timedelta(hours=janela_h)
    ultima = _ultima_falha_gemini(Path(raiz), limite) if presente else None
    if not presente:
        detalhe = f"CLI do Gemini (agy/gemini) não encontrada; {SEM_API_PAGA}"
    elif ultima:
        detalhe = f"o Gemini falhou num job em {ultima} (cota/429 provável)"
    else:
        detalhe = f"sem falha do Gemini nas últimas {int(janela_h)} h"
    return ResultadoSonda(presente and ultima is None, detalhe,
                          {"presente": presente, "ultima_falha": ultima})


def sondas_padrao(raiz) -> CacheSondas:
    dia = 86400.0
    return CacheSondas({
        "gpu": (300.0, sonda_gpu),
        "ollama": (30.0, sonda_ollama),
        "agy": (300.0, lambda: sonda_agy(raiz)),
        "claude": (dia, lambda: sonda_cli_ia("claude")),
        "yt-dlp": (dia, lambda: sonda_binario("yt-dlp")),
        "node": (dia, lambda: sonda_binario("node")),
        "demucs": (dia, lambda: sonda_binario("demucs")),
        "disco": (60.0, lambda: sonda_disco(raiz)),
    })
