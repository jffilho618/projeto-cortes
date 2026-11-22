"""Vitrine "Recentes" dos streamers cadastrados (história 6.5): metadados pelo yt-dlp, sem baixar mídia.

Sem a chave da YouTube Data API a lista é parcial (sem estatísticas oficiais); lives em curso ficam de fora
até existir a consulta oficial (LIV-1). Cache: prazo de 6 h e nada guardado por mais de 30 dias (AD-9).
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from picorte.config import resolve_cli_binary

ID = re.compile(r"(?:v=|youtu\.be/|/live/|/shorts/)([A-Za-z0-9_-]{11})")


def _inteiro(valor: Any) -> int | None:
    return int(valor) if isinstance(valor, (int, float)) and not isinstance(valor, bool) else None


def normalizar_entrada(e: dict[str, Any]) -> dict[str, Any] | None:
    vid = str(e.get("id") or "")
    if len(vid) != 11 or e.get("live_status") in {"is_live", "is_upcoming"}:
        return None
    ts = _inteiro(e.get("timestamp"))
    return {
        "id": vid,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "titulo": str(e.get("title") or ""),
        "duracao_s": _inteiro(e.get("duration")),
        "publicado_em": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None,
        "visualizacoes": _inteiro(e.get("view_count")),
        "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        "era_live": e.get("live_status") == "was_live",
    }


class CanalSemVideos(RuntimeError):
    """O canal cadastrado não existe ou não mostra vídeos: é problema de cadastro, não de rede."""


def classificar_falha(saida: str) -> str:
    t = saida.lower()
    if "does not have a" in t or "http error 404" in t or "requested entity was not found" in t:
        return "sem_aba"
    return "rede"


def rodar_ytdlp(url: str, limite: int) -> dict[str, Any] | None:
    binario = resolve_cli_binary("yt-dlp")
    if not binario:
        return {"_falha": "rede"}
    cmd = [str(binario), "--flat-playlist", "-J", "--playlist-end", str(int(limite)),
           "--extractor-args", "youtubetab:approximate_date", "--no-warnings", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return {"_falha": "rede"}
    try:
        dados = json.loads(r.stdout) if r.stdout.strip() else None
    except ValueError:
        dados = None
    if r.returncode != 0 or not isinstance(dados, dict):
        return {"_falha": classificar_falha(r.stderr or "")}
    return dados


def listar_canal(url_canal: str, limite: int = 8, *, rodar=rodar_ytdlp) -> list[dict[str, Any]]:
    base = url_canal.rstrip("/")
    vistos: dict[str, dict[str, Any]] = {}
    respondeu = False
    falhas: list[str] = []
    for aba in ("videos", "streams"):
        dados = rodar(f"{base}/{aba}", limite)
        if not dados or "_falha" in dados:
            falhas.append(str((dados or {}).get("_falha") or "rede"))
            continue
        respondeu = True
        for e in dados.get("entries") or []:
            v = normalizar_entrada(e) if isinstance(e, dict) else None
            if v and v["id"] not in vistos:
                vistos[v["id"]] = v
    if not respondeu:
        if falhas and all(f == "sem_aba" for f in falhas):
            raise CanalSemVideos(f"O YouTube não mostra vídeos em {base}. Confira o canal no cadastro de streamers.")
        raise RuntimeError(f"Não consegui listar {base} agora.")
    return sorted(vistos.values(), key=lambda v: v["publicado_em"] or "", reverse=True)[:limite]


class CacheVitrine:
    def __init__(self, arquivo: Path, prazo_s: float = 6 * 3600, maximo_s: float = 30 * 86400,
                 relogio: Callable[[], float] = time.time) -> None:
        self.arquivo, self.prazo_s, self.maximo_s, self.relogio = Path(arquivo), prazo_s, maximo_s, relogio
        self._trava = threading.Lock()

    def _ler(self) -> dict[str, Any]:
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
            return dados if isinstance(dados, dict) else {}
        except (OSError, ValueError):
            return {}

    def obter(self, chave: str, buscar: Callable[[], list[dict[str, Any]]]) -> dict[str, Any]:
        agora = self.relogio()
        with self._trava:
            dados = {k: v for k, v in self._ler().items()
                     if isinstance(v, dict) and agora - float(v.get("em", 0)) <= self.maximo_s}  # AD-9
            item = dados.get(chave)
        if item and agora - float(item["em"]) < self.prazo_s:
            return {"verificado_em": item["verificado_em"], "videos": item["videos"], "desatualizado": False}
        try:
            videos = buscar()
        except Exception:
            if item:
                return {"verificado_em": item["verificado_em"], "videos": item["videos"], "desatualizado": True}
            raise
        verificado = datetime.fromtimestamp(agora, tz=timezone.utc).isoformat(timespec="seconds")
        with self._trava:
            dados[chave] = {"em": agora, "verificado_em": verificado, "videos": videos}
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            self.arquivo.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        return {"verificado_em": verificado, "videos": videos, "desatualizado": False}


def id_do_video(url: str) -> str | None:
    m = ID.search(str(url or ""))
    return m.group(1) if m else None


def indice_projetos(projetos: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indice: dict[str, dict[str, Any]] = {}
    for p in projetos:
        vid = id_do_video(str(p.get("source") or ""))
        if vid and vid not in indice:  # listar() vem do mais novo para o mais antigo
            indice[vid] = {"id": p.get("id"), "status": p.get("status"), "stage": p.get("stage")}
    return indice
