# 6.5-A — Lives e Sala do vídeo (backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao front da página Lives dados reais. São três coisas:
- **a vitrine "Recentes"** dos streamers cadastrados, pelo `yt-dlp`, só metadados, com cache;
- **a faixa "Na sua mesa"**, montada dos projetos reais;
- **a Sala do vídeo:** metadados, portão P1 com a mesma régua do preparo e o projeto que já existe para o vídeo.

**Architecture:** Três serviços puros e testáveis com dependências injetadas:
- `picorte/services/vitrine.py`: lista as abas `videos` e `streams` do canal pelo `yt-dlp --flat-playlist`, com cache em `.picorte/cache/vitrine.json` (prazo de 6 h; nada guardado por mais de 30 dias, AD-9);
- `picorte/services/mesa.py`: chips a partir de `fila.listar()`;
- `picorte/services/sala.py`: `ingest.probe_source` + `gate_project_source`, que é exatamente o que o `projects.py` faz antes de baixar.

O módulo novo `picorte/api/rotas_lives.py` expõe as rotas. A CSP passa a aceitar as thumbs do YouTube e os players oficiais.

**Tech Stack:** Python 3.12, FastAPI 0.165, `yt-dlp` (binário via `resolve_cli_binary`), pytest.

**Spec:**
- `epics.md`, Story 6.5 (AC 1–5);
- `EXPERIENCE.md`: Lives e Sala do vídeo, State Patterns de Lives e Sala, e a faixa "Na sua mesa";
- protótipos `design/estudio/fonte/lives.html` e `sala.html`.

## Global Constraints

- **Não editar:** `projects/`, `benchmarks/`, `score_clips.py`, `picorte/engine/score_clips.py`, `llm_router.py`, `benchmark.py`, `ingest.py`, `picorte/engine/ingest.py`, `chat_seismic.py`, `tests/test_e36_*`, `tests/test_e3_practical_e2e.py`. Ler e chamar `ingest.probe_source` é permitido.
- **Não competir com a sessão do motor:** só testes leves e direcionados (com fakes no lugar do `yt-dlp`), nada de GPU e sem suíte completa. Fumaça real no máximo com 1 canal.
- **Não commitar.**
- **A5:**
  - nada de número inventado;
  - "Links pendentes" sai `None` (não medido) até a 6.8 marcar os exportados;
  - live "ao vivo agora" não aparece sem a API oficial (LIV-1 e LIV-6 seguem travados): o `yt-dlp` só lista VODs.
- **P1:** a vitrine só lista canais do `assets/streamers/registry.json` (fontes cadastradas). A Sala responde o portão com `gate_project_source`, a mesma função que barra o preparo, e nunca baixa mídia.
- **Windows e Linux:** `subprocess` com lista de argumentos, `pathlib`, binário por `resolve_cli_binary("yt-dlp")`.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `picorte/services/vitrine.py` (novo) | `normalizar_entrada`, `listar_canal`, `CacheVitrine`, `id_do_video`, `indice_projetos`, `prateleira`. |
| `picorte/services/mesa.py` (novo) | `na_sua_mesa(projetos)`. |
| `picorte/services/sala.py` (novo) | `validar_link`, `abrir_sala`. |
| `picorte/api/rotas_lives.py` (novo) | `GET /api/vitrine`, `GET /api/vitrine/{slug}`, `GET /api/mesa`, `GET /api/sala`. |
| `picorte/api/app.py` | Inclui `rotas_lives`; `app.state.vitrine` (cache) injetável. |
| `picorte/api/seguranca.py` | CSP: `img-src` com `https://i.ytimg.com`; `frame-src` com `https://www.youtube-nocookie.com https://player.twitch.tv`. |
| `picorte/capacidades/catalogo.py` | LIV-4 parcial `config` (lista pelo `yt-dlp`, sem estatísticas oficiais); LIV-5 ligado. |
| Testes | `tests/test_lives_vitrine.py`, `tests/test_lives_mesa.py`, `tests/test_lives_sala.py`, `tests/test_lives_api.py`, mais o ajuste em `tests/test_estudio_api_base.py` (CSP) e em `tests/test_estudio_capacidades.py`. |

---

### Task 1: Vitrine — listar o canal com cache (AD-9)

**Files:** Create `picorte/services/vitrine.py`; Test `tests/test_lives_vitrine.py`.

**Interfaces (Produces):**
- `normalizar_entrada(e: dict) -> dict | None`, que devolve `{id, url, titulo, duracao_s, publicado_em, visualizacoes, thumb, era_live}`. Devolve `None` para lives em curso ou agendadas e para entradas sem id;
- `listar_canal(url_canal: str, limite: int = 8, *, rodar=rodar_ytdlp) -> list[dict]`: junta as abas `/videos` e `/streams`, sem duplicatas, da mais nova para a mais antiga;
- `rodar_ytdlp(url: str, limite: int) -> dict | None`;
- `CacheVitrine(arquivo: Path, prazo_s=21600, maximo_s=2592000, relogio=time.time)` com `.obter(slug, buscar) -> {"verificado_em": iso, "videos": [...], "desatualizado": bool}` (levanta `RuntimeError` se nunca obteve e a busca falha);
- `id_do_video(url: str) -> str | None` (YouTube `watch?v=`, `youtu.be/`, `/live/`, `/shorts/`);
- `indice_projetos(projetos: list[dict]) -> dict[str, dict]` (id do vídeo → `{id, status, stage}`).

- [ ] **Step 1: Teste (falhando)** — `tests/test_lives_vitrine.py`:

```python
import json

import pytest

from picorte.services.vitrine import (CacheVitrine, id_do_video, indice_projetos, listar_canal,
                                      normalizar_entrada)

ENTRADA = {"id": "q4ekFpRjgKQ", "title": "EMBOSCADOS! - GRAND THEFT AUTO 6 - Parte 6", "duration": 8087,
           "timestamp": 1795276800, "view_count": 287000, "live_status": None}


def test_normaliza_uma_entrada_real_do_ytdlp():
    v = normalizar_entrada(ENTRADA)
    assert v == {"id": "q4ekFpRjgKQ", "url": "https://www.youtube.com/watch?v=q4ekFpRjgKQ",
                 "titulo": "EMBOSCADOS! - GRAND THEFT AUTO 6 - Parte 6", "duracao_s": 8087,
                 "publicado_em": "2026-11-21T16:00:00+00:00", "visualizacoes": 287000,
                 "thumb": "https://i.ytimg.com/vi/q4ekFpRjgKQ/hqdefault.jpg", "era_live": False}


def test_live_em_curso_ou_agendada_fica_de_fora_sem_api_oficial():
    assert normalizar_entrada({**ENTRADA, "live_status": "is_live"}) is None
    assert normalizar_entrada({**ENTRADA, "live_status": "is_upcoming"}) is None
    assert normalizar_entrada({"title": "sem id"}) is None


def test_campos_ausentes_ficam_none_nunca_zero():
    v = normalizar_entrada({"id": "abc12345678", "title": "x"})
    assert v["duracao_s"] is None and v["visualizacoes"] is None and v["publicado_em"] is None


def test_listar_canal_junta_abas_sem_duplicar_e_ordena():
    abas = {
        "https://www.youtube.com/@x/videos": {"entries": [ENTRADA, {**ENTRADA, "id": "velho000000", "timestamp": 1700000000}]},
        "https://www.youtube.com/@x/streams": {"entries": [{**ENTRADA, "live_status": "was_live"},
                                                          {**ENTRADA, "id": "novo0000000", "timestamp": 1795300000}]},
    }
    vids = listar_canal("https://www.youtube.com/@x", limite=3, rodar=lambda url, limite: abas.get(url))
    assert [v["id"] for v in vids] == ["novo0000000", "q4ekFpRjgKQ", "velho000000"]


def test_listar_canal_falha_quando_nenhuma_aba_responde():
    with pytest.raises(RuntimeError):
        listar_canal("https://www.youtube.com/@x", rodar=lambda url, limite: None)


def test_cache_respeita_prazo_e_usa_o_velho_quando_a_busca_falha(tmp_path):
    agora = [1_000_000.0]
    cache = CacheVitrine(tmp_path / "v.json", prazo_s=100, relogio=lambda: agora[0])
    chamadas = []
    buscar = lambda: chamadas.append(1) or [normalizar_entrada(ENTRADA)]  # noqa: E731
    assert cache.obter("alanzoka", buscar)["desatualizado"] is False
    cache.obter("alanzoka", buscar)
    assert len(chamadas) == 1  # dentro do prazo: não busca de novo
    agora[0] += 200

    def falha():
        raise RuntimeError("rede")

    r = cache.obter("alanzoka", falha)
    assert r["desatualizado"] is True and r["videos"][0]["id"] == "q4ekFpRjgKQ"


def test_cache_nunca_guarda_mais_de_30_dias(tmp_path):
    agora = [1_000_000.0]
    arq = tmp_path / "v.json"
    cache = CacheVitrine(arq, prazo_s=100, maximo_s=1000, relogio=lambda: agora[0])
    cache.obter("a", lambda: [normalizar_entrada(ENTRADA)])
    agora[0] += 2000
    cache.obter("b", lambda: [])
    assert "a" not in json.loads(arq.read_text(encoding="utf-8"))


def test_cache_sem_dado_e_busca_falhando_levanta(tmp_path):
    cache = CacheVitrine(tmp_path / "v.json")
    with pytest.raises(RuntimeError):
        cache.obter("x", lambda: (_ for _ in ()).throw(RuntimeError("rede")))


def test_id_do_video_e_indice_de_projetos():
    assert id_do_video("https://www.youtube.com/watch?v=q4ekFpRjgKQ&t=10") == "q4ekFpRjgKQ"
    assert id_do_video("https://youtu.be/q4ekFpRjgKQ") == "q4ekFpRjgKQ"
    assert id_do_video("https://www.youtube.com/live/q4ekFpRjgKQ") == "q4ekFpRjgKQ"
    assert id_do_video("C:/videos/meu.mp4") is None
    ind = indice_projetos([{"id": "p1", "source": "https://youtu.be/q4ekFpRjgKQ", "status": "review", "stage": "x"},
                           {"id": "p2", "source": "C:/a.mp4", "status": "complete"}])
    assert ind == {"q4ekFpRjgKQ": {"id": "p1", "status": "review", "stage": "x"}}
```

- [ ] **Step 2: Ver falhar.** Run: `python -m pytest -q -p no:cacheprovider tests/test_lives_vitrine.py`.

- [ ] **Step 3: Implementar** — `picorte/services/vitrine.py`:

```python
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


def rodar_ytdlp(url: str, limite: int) -> dict[str, Any] | None:
    binario = resolve_cli_binary("yt-dlp")
    if not binario:
        return None
    cmd = [str(binario), "--flat-playlist", "-J", "--playlist-end", str(int(limite)),
           "--extractor-args", "youtubetab:approximate_date", "--no-warnings", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def listar_canal(url_canal: str, limite: int = 8, *, rodar=rodar_ytdlp) -> list[dict[str, Any]]:
    base = url_canal.rstrip("/")
    vistos: dict[str, dict[str, Any]] = {}
    respondeu = False
    for aba in ("videos", "streams"):
        dados = rodar(f"{base}/{aba}", limite)
        if not dados:
            continue
        respondeu = True
        for e in dados.get("entries") or []:
            v = normalizar_entrada(e) if isinstance(e, dict) else None
            if v and v["id"] not in vistos:
                vistos[v["id"]] = v
    if not respondeu:
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
```

- [ ] **Step 4: Rodar.** Expected: 9 passam.
- [ ] **Step 5: Sem commit.**

---

### Task 2: Na sua mesa

**Files:** Create `picorte/services/mesa.py`; Test `tests/test_lives_mesa.py`.

**Interfaces (Produces):** `na_sua_mesa(projetos: list[dict]) -> {"pede_voce": [{"projeto", "motivo"}], "revisar": int, "na_fila": {"n": int, "estagio": str | None}, "falhas": [{"projeto", "motivo", "proximo_passo"}], "links_pendentes": None, "links_pendentes_motivo": str}`.

- [ ] **Step 1: Teste (falhando)** — `tests/test_lives_mesa.py`:

```python
from picorte.services.mesa import na_sua_mesa


def test_mesa_a_partir_dos_projetos_reais():
    projetos = [
        {"id": "a", "status": "review"}, {"id": "b", "status": "review"},
        {"id": "c", "status": "running", "stage": "render 4/17"}, {"id": "d", "status": "queued"},
        {"id": "e", "status": "failed", "error": "[P1:pre_ingest] Fonte desconhecida: 'BisteconeLive' não está entre os streamers cadastrados. Nada foi baixado."},
        {"id": "f", "status": "failed", "error": "lote 1/2 falhou 2x: CalledProcessError: Command '['agy.exe'"},
        {"id": "g", "status": "interrupted"}, {"id": "h", "status": "complete"},
    ]
    m = na_sua_mesa(projetos)
    assert m["revisar"] == 2
    assert m["na_fila"] == {"n": 2, "estagio": "render 4/17"}
    assert m["pede_voce"] == [{"projeto": "e", "motivo": projetos[4]["error"]}]
    falhas = {f["projeto"]: f for f in m["falhas"]}
    assert set(falhas) == {"f", "g"}
    assert falhas["f"]["proximo_passo"] == "Trocar o motor de IA e retomar"
    assert falhas["g"]["proximo_passo"] == "Retomar"


def test_links_pendentes_nao_medido_ate_a_6_8():
    m = na_sua_mesa([])
    assert m["links_pendentes"] is None and "6.8" in m["links_pendentes_motivo"]
    assert m["revisar"] == 0 and m["pede_voce"] == [] and m["na_fila"] == {"n": 0, "estagio": None}
```

- [ ] **Step 2: Ver falhar.**
- [ ] **Step 3: Implementar** — `picorte/services/mesa.py`:

```python
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


def na_sua_mesa(projetos: list[dict[str, Any]]) -> dict[str, Any]:
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
        "links_pendentes": None,  # A5: ninguém marca "Exportado" por corte ainda
        "links_pendentes_motivo": "Os cortes exportados passam a ser marcados na história 6.8.",
    }
```

- [ ] **Step 4: Rodar.** Expected: 2 passam.
- [ ] **Step 5: Sem commit.**

---

### Task 3: Sala do vídeo — link, metadados, portão P1 e projeto existente

**Files:** Create `picorte/services/sala.py`; Test `tests/test_lives_sala.py`.

**Interfaces (Produces):**
- `validar_link(url: str) -> str` (devolve a URL limpa ou levanta `ValueError("Isso não parece um link de vídeo do YouTube, Twitch ou Kick.")`);
- `abrir_sala(url, *, db, projetos, sondar=ingest.probe_source, portao=gate_project_source) -> dict`, que devolve:
  - `video`: `{url, titulo, canal, duracao_s, thumb, ao_vivo, plataforma, id_youtube}`;
  - `portao`: `{liberado: bool, fonte?, base?, codigo?, motivo?}`;
  - `projeto`: `{id, status, stage} | None`.

- [ ] **Step 1: Teste (falhando)** — `tests/test_lives_sala.py`:

```python
import pytest

from picorte.risk_shield.policy_gate import PolicyViolationError
from picorte.services.sala import abrir_sala, validar_link

META = {"title": "GTA 6 É AGORA", "channel": "Davy Jones", "channel_url": "https://www.youtube.com/@Gameplayrj",
        "duration": 40815, "thumbnail": "https://i.ytimg.com/vi/x50ONQrBPRM/maxresdefault.jpg",
        "live_status": "was_live", "formats": [{"x": 1}]}


def test_validar_link():
    assert validar_link(" https://www.youtube.com/watch?v=x50ONQrBPRM ") == "https://www.youtube.com/watch?v=x50ONQrBPRM"
    assert validar_link("https://www.twitch.tv/videos/123456789")
    assert validar_link("https://kick.com/video/abc-123")
    for ruim in ["", "oi", "https://example.com/watch?v=x", "file:///C:/a.mp4"]:
        with pytest.raises(ValueError, match="não parece um link de vídeo"):
            validar_link(ruim)


def test_sala_liberada_com_metadados_e_projeto_existente():
    visto = {}

    def portao(db, *, source_input, meta, owner=None):
        visto.update(source_input=source_input, meta=meta)
        return {"allowed": True, "source_name": "DAVY JONES", "permission_basis": "tolerancia_publica"}

    r = abrir_sala("https://www.youtube.com/watch?v=x50ONQrBPRM", db=None, sondar=lambda u: dict(META), portao=portao,
                   projetos=[{"id": "p1", "source": "https://youtu.be/x50ONQrBPRM", "status": "review", "stage": "x"}])
    assert r["video"]["titulo"] == "GTA 6 É AGORA" and r["video"]["duracao_s"] == 40815
    assert r["video"]["id_youtube"] == "x50ONQrBPRM" and r["video"]["plataforma"] == "youtube"
    assert r["video"]["ao_vivo"] is False
    assert r["portao"] == {"liberado": True, "fonte": "DAVY JONES", "base": "tolerancia_publica"}
    assert r["projeto"] == {"id": "p1", "status": "review", "stage": "x"}
    assert "formats" not in visto["meta"]  # a mesma régua do preparo, sem a lista de formatos


def test_sala_barrada_diz_o_motivo_e_nada_e_baixado():
    def barra(db, **kw):
        raise PolicyViolationError("[P1:pre_ingest] Fonte desconhecida: 'X'. Nada foi baixado.", code="source_unknown")

    r = abrir_sala("https://www.youtube.com/watch?v=x50ONQrBPRM", db=None, sondar=lambda u: dict(META),
                   portao=barra, projetos=[])
    assert r["portao"] == {"liberado": False, "codigo": "source_unknown",
                           "motivo": "[P1:pre_ingest] Fonte desconhecida: 'X'. Nada foi baixado."}
    assert r["projeto"] is None


def test_metadados_indisponiveis_viram_erro_legivel():
    def falha(url):
        raise RuntimeError("yt-dlp: HTTP Error 404")

    with pytest.raises(ValueError, match="Não consegui ler este vídeo"):
        abrir_sala("https://www.youtube.com/watch?v=x50ONQrBPRM", db=None, sondar=falha, portao=None, projetos=[])
```

- [ ] **Step 2: Ver falhar.**
- [ ] **Step 3: Implementar** — `picorte/services/sala.py`:

```python
"""Sala do vídeo (história 6.5): metadados e portão P1 com a mesma régua do preparo. Nunca baixa mídia."""
from __future__ import annotations

import re
from typing import Any, Callable

from picorte.risk_shield.policy_gate import PolicyViolationError
from picorte.services.vitrine import id_do_video, indice_projetos

LINK = re.compile(r"^https?://(www\.|m\.)?(youtube\.com/(watch\?|live/|shorts/)|youtu\.be/|twitch\.tv/videos/|"
                  r"(www\.)?kick\.com/[^/]+/videos?/|kick\.com/video/)", re.I)
AVISO_LINK = "Isso não parece um link de vídeo do YouTube, Twitch ou Kick."


def validar_link(url: str) -> str:
    limpo = str(url or "").strip()
    if not LINK.match(limpo):
        raise ValueError(AVISO_LINK)
    return limpo


def _plataforma(url: str) -> str:
    u = url.lower()
    return "youtube" if ("youtube" in u or "youtu.be" in u) else ("twitch" if "twitch" in u else "kick")


def abrir_sala(url: str, *, db: Any, projetos: list[dict[str, Any]],
               sondar: Callable[[str], dict[str, Any]] | None = None,
               portao: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    url = validar_link(url)
    if sondar is None:
        import ingest
        sondar = ingest.probe_source
    if portao is None:
        from picorte.risk_shield.source_resolver import gate_project_source as portao
    try:
        meta = dict(sondar(url) or {})
    except Exception as exc:
        raise ValueError(f"Não consegui ler este vídeo agora ({type(exc).__name__}). Tente de novo.") from exc
    meta.pop("formats", None)
    try:
        g = portao(db, source_input=url, meta=meta)
        veredito = {"liberado": True, "fonte": g.get("source_name") or g.get("channel_handle"),
                    "base": g.get("permission_basis")}
    except PolicyViolationError as exc:
        veredito = {"liberado": False, "codigo": getattr(exc, "code", "p1_blocked"), "motivo": str(exc)}
    vid = id_do_video(url)
    duracao = meta.get("duration")
    return {
        "video": {"url": url, "titulo": str(meta.get("title") or ""), "canal": str(meta.get("channel") or ""),
                  "duracao_s": int(duracao) if isinstance(duracao, (int, float)) else None,
                  "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None,
                  "ao_vivo": meta.get("live_status") == "is_live", "plataforma": _plataforma(url),
                  "id_youtube": vid},
        "portao": veredito,
        "projeto": indice_projetos(projetos).get(vid) if vid else None,
    }
```

Nota: a thumb da Sala é a `hqdefault` do YouTube, para caber na CSP (`i.ytimg.com`). Twitch e Kick saem com `thumb = None` e o front desenha o vazio de imagem, nunca uma imagem de exemplo.

- [ ] **Step 4: Rodar.** Expected: 4 passam.
- [ ] **Step 5: Sem commit.**

---

### Task 4: Rotas, CSP e capacidades

**Files:**
- Create: `picorte/api/rotas_lives.py`
- Modify: `picorte/api/app.py` (incluir as rotas e `vitrine=` opcional em `create_app`), `picorte/api/seguranca.py` (CSP), `picorte/capacidades/catalogo.py` (LIV-4 e LIV-5)
- Test: `tests/test_lives_api.py`, mais o ajuste em `tests/test_estudio_capacidades.py`

**Interfaces (Produces):**
- `GET /api/vitrine` devolve `{"streamers": [{slug, nome, handle, youtube, cor, fonte: {id, permission_status} | None}]}`, que é instantâneo e sai do registro;
- `GET /api/vitrine/{slug}?limite=8` devolve `{slug, verificado_em, desatualizado, videos: [... + projeto | None]}` (404 para slug fora do registro);
- `GET /api/mesa` devolve o `na_sua_mesa(fila.listar())`;
- `GET /api/sala?url=` devolve o `abrir_sala(...)`;
- `create_app(..., vitrine: CacheVitrine | None = None, listar=listar_canal, sondar=None, portao=None)`, com dependências injetáveis para os testes.

- [ ] **Step 1: Teste (falhando)** — `tests/test_lives_api.py`:

```python
from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.services.fila import FilaEstudio
from picorte.services.vitrine import CacheVitrine, normalizar_entrada

ENTRADA = {"id": "q4ekFpRjgKQ", "title": "EMBOSCADOS!", "duration": 8087, "timestamp": 1795276800}


def _cliente(tmp_path, **deps):
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     fila=FilaEstudio(raiz, executar=lambda *a: 0),
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()),
                     vitrine=CacheVitrine(tmp_path / "v.json"), **deps)
    return TestClient(app), raiz


def test_vitrine_lista_os_streamers_do_registro_na_hora(tmp_path):
    c, _ = _cliente(tmp_path)
    dados = c.get("/api/vitrine").json()
    slugs = [s["slug"] for s in dados["streamers"]]
    assert "alanzoka" in slugs and all(s["youtube"].startswith("https://www.youtube.com/") for s in dados["streamers"])


def test_prateleira_traz_videos_reais_e_o_projeto_ligado(tmp_path):
    c, raiz = _cliente(tmp_path, listar=lambda url, limite: [normalizar_entrada(ENTRADA)])
    import projects
    projects.create_project(raiz, "https://www.youtube.com/watch?v=q4ekFpRjgKQ", {})
    dados = c.get("/api/vitrine/alanzoka").json()
    assert dados["videos"][0]["titulo"] == "EMBOSCADOS!" and dados["verificado_em"]
    assert dados["videos"][0]["projeto"]["status"] == "new"


def test_prateleira_de_slug_desconhecido_e_404(tmp_path):
    c, _ = _cliente(tmp_path)
    assert c.get("/api/vitrine/nao-existe").status_code == 404


def test_prateleira_sem_rede_e_sem_cache_responde_503_legivel(tmp_path):
    def falha(url, limite):
        raise RuntimeError("rede")

    c, _ = _cliente(tmp_path, listar=falha)
    r = c.get("/api/vitrine/alanzoka")
    assert r.status_code == 503 and "Não consegui listar" in r.json()["erro"]


def test_mesa(tmp_path):
    c, _ = _cliente(tmp_path)
    m = c.get("/api/mesa").json()
    assert m["revisar"] == 0 and m["links_pendentes"] is None


def test_sala_com_link_ruim_e_400(tmp_path):
    c, _ = _cliente(tmp_path)
    r = c.get("/api/sala", params={"url": "oi"})
    assert r.status_code == 400 and "não parece um link" in r.json()["erro"]


def test_sala_usa_a_regua_injetada(tmp_path):
    c, _ = _cliente(tmp_path, sondar=lambda u: {"title": "T", "channel": "C"},
                    portao=lambda db, **kw: {"allowed": True, "source_name": "C", "permission_basis": "explicita"})
    r = c.get("/api/sala", params={"url": "https://youtu.be/q4ekFpRjgKQ"}).json()
    assert r["portao"]["liberado"] is True and r["video"]["titulo"] == "T"


def test_csp_aceita_thumbs_e_players_oficiais(tmp_path):
    c, _ = _cliente(tmp_path)
    csp = c.get("/api/mesa").headers["content-security-policy"]
    assert "https://i.ytimg.com" in csp and "frame-src https://www.youtube-nocookie.com https://player.twitch.tv" in csp
```

Acrescente a `tests/test_estudio_capacidades.py`:

```python
def test_historia_6_5_ligou_a_sala_e_recentes_e_parcial(tmp_path):
    caps = _por_id(listar_capacidades(tmp_path, cache_falso()))
    assert caps["LIV-5"]["status"] == "ligado" and caps["LIV-5"]["ligou_em"] == "2026-11-22"
    assert (caps["LIV-4"]["status"], caps["LIV-4"]["tipo_motivo"]) == ("parcial", "config")
    for i in ["LIV-1", "LIV-2", "LIV-3", "LIV-6"]:
        assert caps[i]["status"] == "travado", i
```

- [ ] **Step 2: Ver falhar.**
- [ ] **Step 3: Implementar**

`picorte/api/rotas_lives.py`:

```python
"""Rotas da página Lives e da Sala do vídeo (história 6.5)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from picorte.services.mesa import na_sua_mesa
from picorte.services.vitrine import indice_projetos

rotas = APIRouter()


def _registro() -> list[dict]:
    from picorte.engine.publish_kit import load_streamer_registry
    return [s for s in (load_streamer_registry(None).get("streamers") or []) if s.get("youtube")]


def _fontes() -> dict[str, dict]:
    from picorte.db.connection import get_default_db
    linhas = get_default_db().fetch_all("SELECT id, channel_handle, permission_status FROM sources")
    return {str(r["channel_handle"] or "").lower(): {"id": r["id"], "permission_status": r["permission_status"]}
            for r in linhas}


@rotas.get("/api/vitrine")
def vitrine():
    fontes = _fontes()
    return {"streamers": [
        {"slug": s["slug"], "nome": s.get("display_name") or s["slug"], "handle": s.get("handle"),
         "youtube": s["youtube"], "cor": s.get("accent_hex"),
         "fonte": fontes.get(str(s.get("handle") or f"@{s['slug']}").lower())}
        for s in _registro()]}


@rotas.get("/api/vitrine/{slug}")
def prateleira(slug: str, request: Request, limite: int = 8):
    estado = request.app.state
    st = next((s for s in _registro() if s["slug"] == slug), None)
    if st is None:
        return JSONResponse({"erro": "Streamer não cadastrado."}, status_code=404)
    limite = max(1, min(int(limite), 30))
    try:
        r = estado.vitrine.obter(f"{slug}:{limite}", lambda: estado.listar_canal(st["youtube"], limite))
    except Exception:
        return JSONResponse({"erro": f"Não consegui listar os vídeos de {st.get('display_name') or slug} agora."},
                            status_code=503)
    indice = indice_projetos(estado.fila.listar())
    return {"slug": slug, "verificado_em": r["verificado_em"], "desatualizado": r["desatualizado"],
            "videos": [{**v, "projeto": indice.get(v["id"])} for v in r["videos"]]}


@rotas.get("/api/mesa")
def mesa(request: Request):
    return na_sua_mesa(request.app.state.fila.listar())


@rotas.get("/api/sala")
def sala(url: str, request: Request):
    from picorte.db.connection import get_default_db
    from picorte.services.sala import abrir_sala
    estado = request.app.state
    return abrir_sala(url, db=get_default_db(), projetos=estado.fila.listar(),
                      sondar=estado.sondar, portao=estado.portao)
```

Em `picorte/api/app.py`:
1. `_registrar_rotas`: acrescente `from picorte.api.rotas_lives import rotas as rotas_lives` e `app.include_router(rotas_lives)`, antes do fallback da SPA.
2. `create_app` ganha os parâmetros `vitrine=None, listar=None, sondar=None, portao=None` e grava:

   ```python
       from picorte.config import PROJECT_ROOT
       from picorte.services.vitrine import CacheVitrine, listar_canal
       app.state.vitrine = vitrine or CacheVitrine(PROJECT_ROOT / ".picorte" / "cache" / "vitrine.json")
       app.state.listar_canal = listar or listar_canal
       app.state.sondar = sondar
       app.state.portao = portao
   ```

Em `picorte/api/seguranca.py`, a CSP vira:

```python
CSP = ("default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self'; "
       "img-src 'self' data: https://i.ytimg.com; font-src 'self'; connect-src 'self'; "
       "frame-src https://www.youtube-nocookie.com https://player.twitch.tv; "
       "frame-ancestors 'none'; base-uri 'none'")
```

Em `picorte/capacidades/catalogo.py`, troque LIV-4 e LIV-5 por:

```python
        _c("LIV-4", "lives", "Recentes: vídeos recentes dos streamers cadastrados", P, "config", "sem a chave da YouTube Data API a lista vem do yt-dlp, sem estatísticas oficiais; a chave entra em Configurações (6.7)", "registry.json + yt-dlp (cache 6 h, máx. 30 dias)", "6", "6.5"),
        _c("LIV-5", "lives", "Cortar um VOD na Sala do vídeo", L, None, "", "GET /api/sala + POST /api/lote", "6", "6.5", ligou_em="2026-11-22"),
```

- [ ] **Step 4: Rodar.** Run: `python -m pytest -q -p no:cacheprovider tests/test_lives_*.py tests/test_estudio_*.py`. Expected: tudo passa. Se `test_estudio_api_base` checar a CSP antiga literal, atualize para a nova.
- [ ] **Step 5: Fumaça leve (1 canal só).** Com o Estúdio numa pasta vazia e uma cópia do banco: `curl /api/vitrine/alanzoka` uma vez (só metadados) e `curl "/api/sala?url=<um vídeo da lista>"`. Os dois chamam o `yt-dlp` de metadados por poucos segundos, sem GPU. Confira que o `.picorte/cache/vitrine.json` foi criado e que nada mudou em `projects/`.
- [ ] **Step 6: Sem commit.**

## Execução (2026-11-22)

- Data do teste corrigida: o timestamp 1795276800 dá 16:00 UTC, não 12:00.
- 15 testes de serviço e 8 de API passam; a suíte do Estúdio e a do banco seguem verdes (135).
- **Fumaça real** (Estúdio numa pasta vazia com a cópia do banco):
  - `/api/vitrine` listou os 5 streamers, todos com fonte `liberada`;
  - `/api/vitrine/alanzoka` trouxe 8 VODs reais em ~2,5 s e criou o cache;
  - `/api/sala` respondeu em 3,7 s, com o portão "liberado · tolerância pública" e sem baixar nada;
  - `projects/` ficou intocado.

## 6.5-B — front de Lives e da Sala (executado em 2026-11-22, com o impeccable em modo Operate)

- **Caminho escolhido:** não rodei a máquina de estados "comp-led" do impeccable (plates, hero e comp-diff). Ela foi feita para comps em imagem. Aqui o comp aprovado é HTML no mesmo CSS do sistema, e as thumbs dele são dados reais. Portei a marcação e as classes de `design/estudio/fonte/{lives,sala}.html` para React e conferi no Edge (2560×1440, escuro e claro).
- **Arquivos:**
  - `src/api/lives.ts` (tipos e consultas); `enviar()` e `obterToken()` em `src/api/cliente.ts`;
  - `src/paginas/lives/{Lives,MesaFaixa,Recentes,CardVideo,regras}.tsx`;
  - `src/paginas/sala/{Sala,PainelCorte}.tsx`;
  - a mesa ligada à sidebar (Revisão e Fontes em alerta) e aos eventos de job.
- **Backend extra:**
  - `/api/lote` aceita `acao` (`all` = renderizar sozinho, padrão da Sala; `prepare` = esperar minha revisão);
  - a REV-7 traz o custo medido dos frames (auditoria E3, 20/11);
  - `CanalSemVideos`: canal inexistente ou sem abas vira 404 "confira o cadastro", não "indisponível agora".
- **Defeitos achados no navegador e corrigidos:**
  - um 503 com `{erro}` do próprio Estúdio era lido como "Picorte desligado";
  - o botão desabilitado continuava laranja;
  - os esqueletos tinham tamanho diferente da prateleira real.
- **Achados de dados (do dono):** no `registry.json`, o YouTube do Coringa (`@loud_coringa`) não existe, e o do Bistecone (`@bistecone`) não tem vídeos públicos.
- **Player:** o YouTube embutido recusa vídeos no Edge automatizado ("Este vídeo não está disponível"), mas toca o vídeo de demonstração oficial. A configuração (referrer `strict-origin-when-cross-origin`) está certa; sem referrer dá o Erro 153. Por isso a Sala tem sempre o link "Abrir no YouTube". Falta conferir num navegador normal.
- **Desvio de TDD:** `regras.ts` foi escrito junto com o teste, sem vê-lo falhar antes.
- **Fora da 6.5 (fica para depois):**
  - arrastar um arquivo local para a vitrine (o navegador não entrega o caminho);
  - mini-VOD nos cards já cortados;
  - busca por pergunta na Sala (6.6);
  - marcador Novo.
