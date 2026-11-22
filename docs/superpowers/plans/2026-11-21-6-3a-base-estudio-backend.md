# História 6.3-A — Base do Estúdio (backend FastAPI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** criar o backend FastAPI do Estúdio do Criador, que diz o status real de cada função do Picorte (`/api/capacidades`, também como ferramenta MCP), publica eventos por SSE e porta do `dashboard.py` a fila serial, a mídia com Range e os portões de segurança, sem nunca escrever em `project.json` ao abrir ou ler.

**Architecture:**
- O pacote novo `picorte/api/` monta o app (`create_app`), com um middleware de segurança e um fallback de SPA.
- A lógica fica em serviços sem HTTP, para o MCP chamar as mesmas funções (AD-10):
  - `picorte/services/` (`job_lock`, `fila`, `eventos`, `projeto_detalhe`, `taxonomia`);
  - `picorte/capacidades/` (`modelo`, `sondas`, `catalogo`, `regras`, `servico`).
- O status "interrompido" é derivado na leitura (lock livre + fora da fila) e nunca gravado.

**Tech Stack:**
- Python 3.12, FastAPI 0.165.0 e uvicorn 0.54.0;
- `httpx` 0.28 (já instalado: sonda do Ollama e `TestClient`);
- `filelock` 3.20 (já instalado);
- pytest.

**Spec:**
- `_bmad-output/planning-artifacts/epics.md`: Epic 6, Story 6.3, AC 1 a 6 (a AC 7, casca React, fica no plano 6.3-B).
- Mapa de capacidades: `_bmad-output/brainstorming/brainstorm-mapa-painel-estudio-do-criador-2026-11-21/brainstorm-intent.md` (seções "Inventário por área" e "Contrato `GET /api/capacidades`").
- Arquitetura: `architecture.md` (AD-10, AD-11, convenção "Travado nunca é falso").

## Global Constraints

- **Não editar:**
  - `projects/` (nenhum arquivo dentro dela), `benchmarks/`;
  - `score_clips.py`, `picorte/ai/llm_router.py`, `benchmark.py`;
  - os testes da 3.6.1 (`tests/test_e36_*`).

  Outra sessão está trabalhando neles.
- **Não commitar.** O dono não autorizou commit nesta etapa. Os passos de "commit" da skill viram "conferir `git status`" (CLAUDE.md, regra 1).
- **Windows 11 e Linux (AD-11):**
  - caminhos só com `pathlib.Path`;
  - trava só com `filelock`, nunca `fcntl`;
  - nada de comando de shell específico de um sistema.
- **Abrir ou ler nunca escreve `project.json`.** Só uma ação explícita do usuário escreve: enfileirar, salvar ajustes, editar.
- **Travado nunca é falso (A5):** uma capacidade `travado` sai com `dados: null`, e sinal não medido sai `null`, nunca `0`.
- **Status permitidos:**
  - status: `ligado` | `parcial` | `travado`;
  - `tipo_motivo`: `codigo` | `config` | `dado` | `temporario` | `escolha`;
  - escopo: `global` | `projeto` | `corte`.
- **Rotas novas em português:**
  - `/api/capacidades`, `/api/taxonomia`, `/api/eventos`;
  - `/api/projetos`, `/api/lote`, `/api/marcas`;
  - `/api/risco/...`, `/api/config`;
  - `/media/...`.
- **Cabeçalho do token:** `X-Picorte-Token`.
- **Porta padrão do Estúdio novo:** `8770`, para conviver com o `dashboard.py`, que fica na `8765` até a 6.3-B.
- **Mensagens novas em PT-BR.** As mensagens que vêm das funções antigas de `projects.py` ficam como estão.
- **Espelho do motor:** toda mudança em `projects.py` vale igual em `picorte/engine/projects.py`. `diff projects.py picorte/engine/projects.py` precisa sair vazio.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `requirements.txt` (modificar) | + `fastapi==0.165.0`, `uvicorn==0.54.0`, `httpx>=0.28` |
| `picorte/api/__init__.py` | exporta `create_app` |
| `picorte/api/app.py` | fábrica do app, handlers de erro, registro das rotas e fallback de SPA |
| `picorte/api/seguranca.py` | middleware de Host/Origin/token e cabeçalhos (CSP etc.) |
| `picorte/api/rotas_sistema.py` | `/api/capacidades`, `/api/taxonomia`, `/api/eventos`, `/api/config`, `/api/db/*`, `/api/risco/*`, `/api/marcas` |
| `picorte/api/rotas_projetos.py` | `/api/projetos*`, `/api/lote`, `/media/*` |
| `picorte/services/job_lock.py` | lock por projeto entre processos (B9) |
| `picorte/services/eventos.py` | barramento de eventos + formato SSE |
| `picorte/services/fila.py` | fila serial única, status derivado sem escrita |
| `picorte/services/projeto_detalhe.py` | `detalhe_projeto` (movido do `dashboard.py`) |
| `picorte/services/taxonomia.py` | listas canônicas para o front |
| `picorte/capacidades/__init__.py` | exporta `listar_capacidades`, `ServicoCapacidades` |
| `picorte/capacidades/modelo.py` | `Capacidade` + saneamento A5 |
| `picorte/capacidades/sondas.py` | `ResultadoSonda`, `CacheSondas`, sondas concretas |
| `picorte/capacidades/catalogo.py` | as 82 capacidades do mapa (estáticas) |
| `picorte/capacidades/regras.py` | sondas → status dinâmico |
| `picorte/capacidades/servico.py` | `listar_capacidades`, `ServicoCapacidades` (evento quando muda) |
| `picorte/mcp/server.py` (modificar) | ferramenta `picorte_capacidades` |
| `projects.py` + `picorte/engine/projects.py` (modificar) | `run_project` segura o lock |
| `dashboard.py` (modificar) | importa `detalhe_projeto` do serviço |
| `estudio.py` | ponto de entrada (`python estudio.py`) |
| `tests/test_estudio_*.py` | testes novos |

---

### Task 1: Dependências, fábrica do app, portões de segurança e fallback de SPA

**Files:**
- Modify: `requirements.txt`
- Create: `picorte/api/__init__.py`, `picorte/api/app.py`, `picorte/api/seguranca.py`
- Test: `tests/test_estudio_api_base.py`

**Interfaces:**
- Produces:
  - `create_app(raiz_projetos, *, porta=8770, hosts=None, token=None, dist=None) -> FastAPI`;
  - `app.state.raiz: Path` e `app.state.token: str`;
  - `_registrar_rotas(app)`: as tarefas seguintes acrescentam `include_router` aqui;
  - `CABECALHO_TOKEN = "X-Picorte-Token"`;
  - erros: `ValueError`/`KeyError`/`TypeError` → 400, `OSError` → 404, sempre `{"erro": str}`.

- [ ] **Step 1: Instalar as dependências**

Acrescente ao fim de `requirements.txt`:

```
fastapi==0.165.0
uvicorn==0.54.0
httpx>=0.28.0
```

Run: `python -m pip install fastapi==0.165.0 uvicorn==0.54.0`
Expected: `Successfully installed ... fastapi-0.165.0 ... uvicorn-0.54.0`

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_estudio_api_base.py`:

```python
from fastapi.testclient import TestClient

from picorte.api import create_app

TOKEN = "tok-teste"


def _cliente(tmp_path, dist=None):
    app = create_app(tmp_path / "projects", hosts=("testserver",), token=TOKEN,
                     dist=dist or tmp_path / "dist")
    return TestClient(app)


def test_host_estranho_e_recusado(tmp_path):
    r = _cliente(tmp_path).get("/", headers={"host": "evil.com"})
    assert r.status_code == 403
    assert "erro" in r.json()


def test_cabecalhos_de_seguranca_em_toda_resposta(tmp_path):
    r = _cliente(tmp_path).get("/")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_post_sem_token_e_recusado(tmp_path):
    assert _cliente(tmp_path).post("/api/projetos", json={}).status_code == 403


def test_post_com_origem_estranha_e_recusado(tmp_path):
    r = _cliente(tmp_path).post("/api/projetos", json={},
                                headers={"X-Picorte-Token": TOKEN, "Origin": "http://evil.com"})
    assert r.status_code == 403


def test_post_com_token_passa_do_portao(tmp_path):
    r = _cliente(tmp_path).post("/api/qualquer", json={},
                                headers={"X-Picorte-Token": TOKEN, "Origin": "http://testserver"})
    assert r.status_code != 403


def test_sem_build_mostra_aviso_em_portugues(tmp_path):
    r = _cliente(tmp_path).get("/lives")
    assert r.status_code == 200
    assert "npm run build" in r.text


def test_spa_serve_index_e_arquivos_do_build(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    c = _cliente(tmp_path, dist)
    assert 'id="root"' in c.get("/revisao/abcdef123456").text
    assert c.get("/assets/app.js").text == "console.log(1)"


def test_spa_nao_sai_da_pasta_do_build(tmp_path):
    (tmp_path / "segredo.txt").write_text("SEGREDO", encoding="utf-8")
    r = _cliente(tmp_path).get("/..%2Fsegredo.txt")
    assert "SEGREDO" not in r.text


def test_api_desconhecida_responde_404_em_json(tmp_path):
    r = _cliente(tmp_path).get("/api/nao-existe")
    assert r.status_code == 404
    assert r.json() == {"erro": "Não encontrado."}


def test_token_e_gerado_quando_nao_informado(tmp_path):
    app = create_app(tmp_path / "projects", hosts=("testserver",))
    assert len(app.state.token) >= 32
    assert app.state.raiz == (tmp_path / "projects").resolve()
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_api_base.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'picorte.api'`

- [ ] **Step 4: Implementar**

`picorte/api/seguranca.py`:

```python
"""Portões do Estúdio (portados do dashboard.py): Host, Origin, token anti-CSRF e cabeçalhos."""
from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

CABECALHO_TOKEN = "X-Picorte-Token"
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}
CSP = ("default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self'; "
       "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'")


def _cabecalhos(resposta: Response) -> Response:
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["Content-Security-Policy"] = CSP
    resposta.headers.setdefault("Cache-Control", "no-store")
    return resposta


def _recusa(mensagem: str) -> Response:
    return _cabecalhos(JSONResponse({"erro": mensagem}, status_code=403))


class PortaoSeguranca(BaseHTTPMiddleware):
    def __init__(self, app, *, hosts: tuple[str, ...], token: str) -> None:
        super().__init__(app)
        self.hosts = set(hosts)
        self.token = token.encode()

    async def dispatch(self, request, call_next):
        host = request.headers.get("host", "")
        if host not in self.hosts:
            return _recusa("Use o endereço local do Estúdio (127.0.0.1).")
        if request.method not in METODOS_SEGUROS:
            origem = request.headers.get("origin")
            if origem is not None and origem != f"http://{host}":
                return _recusa("Origem recusada.")
            enviado = request.headers.get(CABECALHO_TOKEN, "").encode("utf-8", "replace")
            if not secrets.compare_digest(enviado, self.token):
                return _recusa("Pedido recusado. Recarregue o Estúdio e tente de novo.")
        return _cabecalhos(await call_next(request))
```

`picorte/api/app.py`:

```python
"""Fábrica do app FastAPI do Estúdio do Criador (história 6.3)."""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from picorte.api.seguranca import PortaoSeguranca

DIST_PADRAO = Path(__file__).resolve().parents[1] / "web" / "dist"
PAGINA_SEM_BUILD = """<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<title>Picorte · Estúdio</title><body style="font-family:system-ui;padding:40px">
<h1>A casca do Estúdio ainda não foi construída</h1>
<p>Rode <code>npm install</code> e <code>npm run build</code> em <code>picorte/web</code>.
A API já responde em <code>/api/capacidades</code>.</p></body></html>"""


def _erro(status: int, mensagem: str) -> JSONResponse:
    return JSONResponse({"erro": mensagem}, status_code=status)


def _registrar_erros(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def _valor(_: Request, exc: ValueError):
        return _erro(400, str(exc))

    @app.exception_handler(KeyError)
    async def _chave(_: Request, exc: KeyError):
        return _erro(400, f"Campo obrigatório ausente: {exc.args[0] if exc.args else ''}")

    @app.exception_handler(TypeError)
    async def _tipo(_: Request, exc: TypeError):
        return _erro(400, str(exc))

    @app.exception_handler(OSError)
    async def _arquivo(_: Request, exc: OSError):
        return _erro(404, "Projeto ou arquivo não encontrado.")


def _registrar_rotas(app: FastAPI) -> None:
    """As tarefas seguintes acrescentam aqui os `include_router`."""


def _registrar_spa(app: FastAPI, dist: Path) -> None:
    dist = dist.resolve()

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        if caminho in {"api", "media"} or caminho.startswith(("api/", "media/")):
            return _erro(404, "Não encontrado.")
        if caminho:
            alvo = (dist / caminho).resolve()
            if alvo.is_file() and alvo.is_relative_to(dist):
                return FileResponse(alvo)
        indice = dist / "index.html"
        if indice.is_file():
            return FileResponse(indice, media_type="text/html")
        return HTMLResponse(PAGINA_SEM_BUILD)


def create_app(raiz_projetos, *, porta: int = 8770, hosts: tuple[str, ...] | None = None,
               token: str | None = None, dist: Path | None = None) -> FastAPI:
    app = FastAPI(title="Picorte · Estúdio do Criador", docs_url=None, redoc_url=None,
                  openapi_url=None)
    raiz = Path(raiz_projetos).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    app.state.raiz = raiz
    app.state.token = token or secrets.token_urlsafe(32)
    app.state.porta = porta
    app.add_middleware(PortaoSeguranca, hosts=hosts or (f"127.0.0.1:{porta}",),
                       token=app.state.token)
    _registrar_erros(app)
    _registrar_rotas(app)
    _registrar_spa(app, Path(dist) if dist else DIST_PADRAO)
    return app
```

`picorte/api/__init__.py`:

```python
"""API HTTP do Estúdio do Criador (FastAPI)."""
from picorte.api.app import create_app

__all__ = ["create_app"]
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_api_base.py -v`
Expected: 10 passed.

- [ ] **Step 6: Conferir (sem commit)**

Run: `git status --short picorte/api tests/test_estudio_api_base.py requirements.txt`
Expected: só os arquivos desta tarefa como novos ou modificados.

---

### Task 2: Lock de job por projeto entre processos (B9)

**Files:**
- Create: `picorte/services/job_lock.py`
- Modify: `projects.py` (`run_project`, linha ~229) e `picorte/engine/projects.py` (idem, espelho)
- Test: `tests/test_estudio_job_lock.py`

**Interfaces:**
- Produces:
  - `NOME_LOCK = ".job.lock"`;
  - `class ProjetoOcupado(RuntimeError)`;
  - `segurar_job(projeto: Path, espera: float = 2.0)`, um context manager;
  - `job_ativo(projeto: Path) -> bool`.
  - `projects.run_project(...)` segura o lock durante todo o job. O corpo antigo vira `projects._run_project(...)`, com a mesma assinatura.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_job_lock.py`:

```python
import subprocess
import sys

import pytest

from picorte.services.job_lock import ProjetoOcupado, job_ativo, segurar_job

SEGURAR = ("import sys, time\nfrom filelock import FileLock\n"
           "l = FileLock(sys.argv[1]); l.acquire(); print('ok', flush=True); time.sleep(60)")


def _outro_processo_segura(arquivo):
    p = subprocess.Popen([sys.executable, "-c", SEGURAR, str(arquivo)],
                         stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "ok"
    return p


def test_sem_lock_nao_ha_job(tmp_path):
    assert job_ativo(tmp_path) is False


def test_job_ativo_nao_cria_arquivo(tmp_path):
    job_ativo(tmp_path)
    assert not (tmp_path / ".job.lock").exists()


def test_lock_de_outro_processo_conta_como_job_ativo(tmp_path):
    p = _outro_processo_segura(tmp_path / ".job.lock")
    try:
        assert job_ativo(tmp_path) is True
        with pytest.raises(ProjetoOcupado):
            with segurar_job(tmp_path, espera=0.2):
                pass
    finally:
        p.kill()
        p.wait()
    assert job_ativo(tmp_path) is False


def test_segurar_job_libera_ao_sair(tmp_path):
    with segurar_job(tmp_path):
        pass
    assert job_ativo(tmp_path) is False


def test_run_project_segura_o_lock_durante_o_job(tmp_path, monkeypatch):
    import projects
    visto = {}

    def falso(path, action="all", preview=False, pick=None, resume=True, progress=None):
        visto["ativo"] = job_ativo(tmp_path)
        return {"ok": True}

    monkeypatch.setattr(projects, "_run_project", falso)
    assert projects.run_project(tmp_path, action="prepare") == {"ok": True}
    assert visto["ativo"] is True
    assert job_ativo(tmp_path) is False


def test_espelho_do_motor_continua_identico():
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    assert (raiz / "projects.py").read_bytes() == (raiz / "picorte/engine/projects.py").read_bytes()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_job_lock.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'picorte.services.job_lock'`

- [ ] **Step 3: Implementar o lock**

`picorte/services/job_lock.py`:

```python
"""Lock por projeto entre processos (B9, AD-11): o painel sabe se um job está vivo sem gravar nada."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock, Timeout

NOME_LOCK = ".job.lock"


class ProjetoOcupado(RuntimeError):
    """Já existe um job vivo neste projeto (nesta ou em outra janela/processo)."""


def caminho_lock(projeto) -> Path:
    return Path(projeto) / NOME_LOCK


@contextmanager
def segurar_job(projeto, espera: float = 2.0) -> Iterator[None]:
    lock = FileLock(str(caminho_lock(projeto)), timeout=espera)
    try:
        lock.acquire()
    except Timeout as exc:
        raise ProjetoOcupado(
            f"O projeto {Path(projeto).name} já tem um job rodando em outro processo.") from exc
    try:
        yield
    finally:
        lock.release()


def job_ativo(projeto) -> bool:
    """True se outro dono segura o lock. Não cria o arquivo de lock quando ele não existe."""
    arquivo = caminho_lock(projeto)
    if not arquivo.exists():
        return False
    lock = FileLock(str(arquivo), timeout=0)
    try:
        lock.acquire()
    except Timeout:
        return True
    lock.release()
    return False
```

- [ ] **Step 4: Envolver o `run_project` (nos dois arquivos)**

Em `projects.py` **e** em `picorte/engine/projects.py`:
1. Renomeie a função `def run_project(path, action="all", preview=False, pick=None, resume=True, progress=None):` para `def _run_project(path, action="all", preview=False, pick=None, resume=True, progress=None):`, sem mexer no corpo.
2. Logo **acima** dela, acrescente:

```python
def run_project(path, action="all", preview=False, pick=None, resume=True, progress=None):
    """Prepare candidates or render saved candidates; checkpoint every successful clip.

    Holds the per-project job lock (B9) so the Studio can tell a live job from an interrupted one.
    """
    from picorte.services.job_lock import segurar_job
    with segurar_job(Path(path).resolve()):
        return _run_project(path, action=action, preview=preview, pick=pick,
                            resume=resume, progress=progress)
```

3. Na `_run_project`, troque a docstring para `"""Body of run_project, called with the job lock held."""`.

Run: `diff projects.py picorte/engine/projects.py`
Expected: nenhuma saída.

- [ ] **Step 5: Rodar os testes novos e os do motor que usam `run_project`**

Run: `python -m pytest tests/test_estudio_job_lock.py -v`
Expected: 6 passed.

Run: `python -m pytest tests -q -x -k "project or studio or dashboard or source_gate"`
Expected: passa como antes. Se algum teste falhar, compare com `git stash` não é permitido aqui (há trabalho de outra sessão na árvore). Rode o mesmo comando antes da mudança, guardando a saída, para comparar.

- [ ] **Step 6: Conferir (sem commit)**

Run: `git status --short projects.py picorte/engine/projects.py picorte/services/job_lock.py`

---

### Task 3: Barramento de eventos e fila serial única, com status derivado sem escrita

**Files:**
- Create: `picorte/services/eventos.py`, `picorte/services/fila.py`
- Test: `tests/test_estudio_fila.py`

**Interfaces:**
- Consumes: `job_ativo`, `ProjetoOcupado` (Task 2); `projects.project_path/read_project/save_project`.
- Produces:
  - `Barramento().assinar() -> queue.Queue[tuple[str, dict]]`, `.cancelar(q)`, `.publicar(tipo: str, dados: dict)`;
  - `formatar_sse(tipo: str, dados: dict) -> str`;
  - `FilaEstudio(raiz, *, barramento=None, executar=None, intervalo=1.0)`, com:
    - `.na_fila(pid) -> bool` e `.ocupado(pid) -> bool`;
    - `.status_efetivo(pid, estado) -> str` e `.estado(pid) -> dict`, que traz `status`, `status_gravado` e `na_fila`;
    - `.listar() -> list[dict]`;
    - `.enfileirar(pid, acao, preview=False, pick=None)` e `.fechar()`.
  - `executar(path: Path, acao: str, preview: bool, pick: str | None) -> int`: o código de saída; 0 = ok.
  - Eventos publicados:
    - `("job", {"projeto", "fase": "na_fila"|"inicio"|"fim", "acao", "ok"?})`;
    - `("progresso", {"projeto", **progress})`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_fila.py`:

```python
import subprocess
import sys
import threading

import pytest

import projects
from picorte.services.eventos import Barramento, formatar_sse
from picorte.services.fila import FilaEstudio
from picorte.services.job_lock import ProjetoOcupado

PID = "abcdef123456"
SEGURAR = ("import sys, time\nfrom filelock import FileLock\n"
           "l = FileLock(sys.argv[1]); l.acquire(); print('ok', flush=True); time.sleep(60)")


def _projeto(raiz, status="new", pid=PID):
    path = raiz / pid
    path.mkdir(parents=True)
    projects.atomic_json(path / "project.json", {
        "id": pid, "source": "x.mp4", "options": {}, "status": status, "stage": "waiting",
        "created": 1.0, "updated": 1.0, "cache": {}, "renders": {}, "error": None})
    return path


def _eventos(q):
    itens = []
    while not q.empty():
        itens.append(q.get_nowait())
    return itens


def test_formatar_sse():
    assert formatar_sse("job", {"a": "ç"}) == 'event: job\ndata: {"a": "ç"}\n\n'


def test_abrir_e_listar_nao_escreve_project_json(tmp_path):
    path = _projeto(tmp_path, status="running")
    antes = (path / "project.json").read_bytes()
    fila = FilaEstudio(tmp_path)
    [item] = fila.listar()
    assert (path / "project.json").read_bytes() == antes
    assert item["status"] == "interrupted"
    assert item["status_gravado"] == "running"
    fila.fechar()


def test_job_vivo_em_outro_processo_continua_rodando(tmp_path):
    path = _projeto(tmp_path, status="running")
    p = subprocess.Popen([sys.executable, "-c", SEGURAR, str(path / ".job.lock")],
                         stdout=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == "ok"
        fila = FilaEstudio(tmp_path)
        assert fila.listar()[0]["status"] == "running"
        assert fila.ocupado(PID) is True
        fila.fechar()
    finally:
        p.kill()
        p.wait()


def test_enfileirar_roda_e_publica_eventos(tmp_path):
    _projeto(tmp_path)
    chamadas = []
    bus = Barramento()
    q = bus.assinar()
    fila = FilaEstudio(tmp_path, barramento=bus,
                       executar=lambda path, acao, preview, pick: chamadas.append((path.name, acao)) or 0)
    fila.enfileirar(PID, "prepare")
    fila._futuros[PID].result(timeout=5)
    assert chamadas == [(PID, "prepare")]
    fases = [d["fase"] for t, d in _eventos(q) if t == "job"]
    assert fases == ["na_fila", "inicio", "fim"]
    fila.fechar()


def test_falha_do_job_marca_failed(tmp_path):
    path = _projeto(tmp_path)
    fila = FilaEstudio(tmp_path, executar=lambda *a: 2)
    fila.enfileirar(PID, "render")
    fila._futuros[PID].result(timeout=5)
    estado = projects.read_project(path)
    assert estado["status"] == "failed"
    assert estado["error"]
    fila.fechar()


def test_enfileirar_duas_vezes_e_recusado(tmp_path):
    _projeto(tmp_path)
    solta = threading.Event()
    fila = FilaEstudio(tmp_path, executar=lambda *a: solta.wait(5) and 0)
    fila.enfileirar(PID, "prepare")
    with pytest.raises(ProjetoOcupado):
        fila.enfileirar(PID, "prepare")
    solta.set()
    fila._futuros[PID].result(timeout=5)
    fila.fechar()


def test_acao_e_selecao_invalidas(tmp_path):
    _projeto(tmp_path)
    fila = FilaEstudio(tmp_path, executar=lambda *a: 0)
    with pytest.raises(ValueError):
        fila.enfileirar(PID, "apagar")
    with pytest.raises(ValueError):
        fila.enfileirar(PID, "render", pick="1;rm")
    fila.fechar()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_fila.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'picorte.services.eventos'`

- [ ] **Step 3: Implementar o barramento**

`picorte/services/eventos.py`:

```python
"""Barramento de eventos do Estúdio: alimenta o SSE /api/eventos (progresso de job e capacidades)."""
from __future__ import annotations

import json
import queue
import threading
from typing import Any


class Barramento:
    def __init__(self, tamanho_fila: int = 256) -> None:
        self._assinantes: set[queue.Queue] = set()
        self._trava = threading.Lock()
        self._tamanho = tamanho_fila

    def assinar(self) -> "queue.Queue[tuple[str, dict[str, Any]]]":
        q: queue.Queue = queue.Queue(maxsize=self._tamanho)
        with self._trava:
            self._assinantes.add(q)
        return q

    def cancelar(self, q: queue.Queue) -> None:
        with self._trava:
            self._assinantes.discard(q)

    def publicar(self, tipo: str, dados: dict[str, Any]) -> None:
        with self._trava:
            alvos = list(self._assinantes)
        for q in alvos:
            try:
                q.put_nowait((tipo, dados))
            except queue.Full:
                pass  # assinante lento perde o evento; o front relê o estado ao reconectar


def formatar_sse(tipo: str, dados: dict[str, Any]) -> str:
    return f"event: {tipo}\ndata: {json.dumps(dados, ensure_ascii=False, allow_nan=False)}\n\n"
```

- [ ] **Step 4: Implementar a fila**

`picorte/services/fila.py`:

```python
"""Fila serial única do Estúdio (B5/B9): um job por vez; "interrompido" é derivado, nunca gravado."""
from __future__ import annotations

import re
import subprocess
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

import projects
from picorte.services.eventos import Barramento
from picorte.services.job_lock import ProjetoOcupado, job_ativo

RAIZ_REPO = Path(__file__).resolve().parents[2]
ACOES = {"prepare", "render", "all"}
ATIVOS = {"queued", "running"}
Executar = Callable[[Path, str, bool, "str | None"], int]


class FilaEstudio:
    def __init__(self, raiz, *, barramento: Barramento | None = None,
                 executar: Executar | None = None, intervalo: float = 1.0) -> None:
        self.raiz = Path(raiz).resolve()
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.barramento = barramento or Barramento()
        self._executar = executar or self._executar_subprocesso
        self._intervalo = intervalo
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="picorte-fila")
        self._trava = threading.RLock()
        self._futuros: dict[str, Future] = {}
        self._processos: set[subprocess.Popen] = set()
        self._fechando = False

    def na_fila(self, pid: str) -> bool:
        futuro = self._futuros.get(pid)
        return futuro is not None and not futuro.done()

    def ocupado(self, pid: str) -> bool:
        return self.na_fila(pid) or job_ativo(projects.project_path(self.raiz, pid))

    def status_efetivo(self, pid: str, estado: dict[str, Any]) -> str:
        status = estado.get("status", "new")
        if status in ATIVOS and not self.ocupado(pid):
            return "interrupted"
        return status

    def estado(self, pid: str) -> dict[str, Any]:
        gravado = projects.read_project(projects.project_path(self.raiz, pid))
        return {**gravado, "status_gravado": gravado.get("status"),
                "status": self.status_efetivo(pid, gravado), "na_fila": self.na_fila(pid)}

    def listar(self) -> list[dict[str, Any]]:
        itens = []
        for arquivo in self.raiz.glob("*/project.json"):
            try:
                itens.append(self.estado(arquivo.parent.name))
            except (ValueError, OSError, KeyError):
                continue
        return sorted(itens, key=lambda p: p.get("created", 0), reverse=True)

    def enfileirar(self, pid: str, acao: str, preview: bool = False, pick: str | None = None) -> None:
        if acao not in ACOES:
            raise ValueError("Ação desconhecida. Use prepare, render ou all.")
        if not isinstance(preview, bool):
            raise ValueError("Preview precisa ser verdadeiro ou falso.")
        if pick is not None and (not isinstance(pick, str) or not re.fullmatch(r"\d+(,\d+)*", pick)):
            raise ValueError("Escolha cortes numerados, por exemplo 1,3,5.")
        with self._trava:
            path = projects.project_path(self.raiz, pid)
            if self.ocupado(pid):
                raise ProjetoOcupado("Este projeto já está na fila ou rodando.")
            estado = projects.read_project(path)
            estado.update(status="queued", stage=acao, error=None)
            projects.save_project(path, estado)
            # publicar ANTES do submit: senão "inicio" pode sair antes de "na_fila" (achado na execução)
            self.barramento.publicar("job", {"projeto": pid, "fase": "na_fila", "acao": acao})
            self._futuros[pid] = self._pool.submit(self._rodar, path, acao, preview, pick)

    def _rodar(self, path: Path, acao: str, preview: bool, pick: str | None) -> None:
        pid = path.name
        self.barramento.publicar("job", {"projeto": pid, "fase": "inicio", "acao": acao})
        try:
            codigo = self._executar(path, acao, preview, pick)
            if codigo:
                self._marcar_falha(path, None)
        except Exception as exc:  # noqa: BLE001 - qualquer falha vira estado visível
            codigo = 1
            self._marcar_falha(path, str(exc))
        self.barramento.publicar("job", {"projeto": pid, "fase": "fim", "acao": acao,
                                         "ok": codigo == 0})

    @staticmethod
    def _marcar_falha(path: Path, erro: str | None) -> None:
        estado = projects.read_project(path)
        estado.update(status="failed", error=erro or estado.get("error")
                      or "O job falhou. Abra o log do job para ver o motivo.")
        projects.save_project(path, estado)

    def _executar_subprocesso(self, path: Path, acao: str, preview: bool, pick: str | None) -> int:
        cmd = [sys.executable, str(RAIZ_REPO / "chopify.py"), "--project", str(path),
               "--action", acao, "--no-input",
               "--out", str(path / ("previews" if preview else "clips"))]
        if preview:
            cmd.append("--preview")
        if pick:
            cmd += ["--clips", pick]
        with (path / "job.log").open("w", encoding="utf-8") as log:
            with self._trava:
                if self._fechando:
                    return 1
                filho = subprocess.Popen(cmd, cwd=RAIZ_REPO, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT)
                self._processos.add(filho)
            ultimo = None
            try:
                while True:
                    try:
                        return filho.wait(timeout=self._intervalo)
                    except subprocess.TimeoutExpired:
                        ultimo = self._publicar_progresso(path, ultimo)
            finally:
                with self._trava:
                    self._processos.discard(filho)

    def _publicar_progresso(self, path: Path, ultimo: dict | None) -> dict | None:
        try:
            progresso = projects.read_project(path).get("progress") or {}
        except (ValueError, OSError):
            return ultimo
        if progresso != ultimo:
            self.barramento.publicar("progresso", {"projeto": path.name, **progresso})
        return progresso

    def fechar(self) -> None:
        with self._trava:
            self._fechando = True
            for filho in list(self._processos):
                filho.terminate()
        self._pool.shutdown(wait=False, cancel_futures=True)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_fila.py -v`
Expected: 7 passed.

- [ ] **Step 6: Conferir (sem commit)**

Run: `git status --short picorte/services tests/test_estudio_fila.py`

---

### Task 4: Modelo `Capacidade` (saneamento A5) e cache de sondas com TTL

**Files:**
- Create: `picorte/capacidades/__init__.py` (vazio por ora), `picorte/capacidades/modelo.py`, `picorte/capacidades/sondas.py` (só o núcleo; as sondas concretas vêm na Task 5)
- Test: `tests/test_estudio_capacidades_modelo.py`

**Interfaces:**
- Produces:
  - `STATUS`, `TIPOS_MOTIVO`, `ESCOPOS` (tuplas);
  - `Capacidade(...)`, uma dataclass frozen, com `.para_json() -> dict`; quando o status é `travado`, sai `dados=None`;
  - `agora_iso() -> str`;
  - `ResultadoSonda(ok: bool, detalhe: str, dados: dict = {}, verificado_em: str = agora_iso())`;
  - `CacheSondas(sondas: dict[str, tuple[float, Callable[[], ResultadoSonda]]], relogio=time.monotonic)`, com `.obter(nome)` e `.todas() -> dict[str, ResultadoSonda]`. Uma sonda que levanta exceção vira `ok=False`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_capacidades_modelo.py`:

```python
import pytest

from picorte.capacidades.modelo import Capacidade
from picorte.capacidades.sondas import CacheSondas, ResultadoSonda


def _cap(**kw):
    base = dict(id="X-1", area="sistema", titulo="Teste", status="ligado", tipo_motivo=None,
                motivo="", falta=(), fonte_dado="teste", origem={"epico": "6", "historia": "6.3"},
                escopo="global")
    return Capacidade(**{**base, **kw})


def test_travado_nunca_sai_com_dados():
    cap = _cap(status="travado", tipo_motivo="codigo", motivo="falta código",
               dados={"total": 42})
    assert cap.para_json()["dados"] is None


def test_ligado_mantem_dados_e_listas_viram_listas():
    j = _cap(dados={"vram_mib": 8188}, falta=("a",), depende_de=("SIS-1",)).para_json()
    assert j["dados"] == {"vram_mib": 8188}
    assert j["falta"] == ["a"] and j["depende_de"] == ["SIS-1"]
    assert set(j) == {"id", "area", "titulo", "status", "tipo_motivo", "motivo", "falta",
                      "fonte_dado", "origem", "escopo", "depende_de", "verificado_em",
                      "ligou_em", "dados"}


@pytest.mark.parametrize("campo,valor", [("status", "quase"), ("tipo_motivo", "preguica"),
                                          ("escopo", "universo")])
def test_valores_fora_do_contrato_sao_recusados(campo, valor):
    with pytest.raises(ValueError):
        _cap(**{campo: valor, **({"tipo_motivo": "codigo"} if campo == "status" else {})})


def test_travado_e_parcial_exigem_tipo_motivo():
    with pytest.raises(ValueError):
        _cap(status="travado", tipo_motivo=None)
    with pytest.raises(ValueError):
        _cap(status="parcial", tipo_motivo=None)


def test_cache_respeita_ttl():
    agora = [100.0]
    chamadas = []

    def sonda():
        chamadas.append(1)
        return ResultadoSonda(True, "ok")

    cache = CacheSondas({"s": (30.0, sonda)}, relogio=lambda: agora[0])
    cache.obter("s")
    agora[0] = 120.0
    cache.obter("s")
    assert len(chamadas) == 1
    agora[0] = 131.0
    cache.obter("s")
    assert len(chamadas) == 2


def test_sonda_que_explode_vira_resultado_falho():
    def quebra():
        raise RuntimeError("bum")

    r = CacheSondas({"s": (1.0, quebra)}).obter("s")
    assert r.ok is False and "bum" in r.detalhe
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_capacidades_modelo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'picorte.capacidades'`

- [ ] **Step 3: Implementar**

`picorte/capacidades/__init__.py`:

```python
"""Contrato de capacidades do Picorte: o backend decide o status real de cada função (A5)."""
```

`picorte/capacidades/modelo.py`:

```python
"""Uma capacidade do Picorte e o saneamento A5 (travado nunca sai com número)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

STATUS = ("ligado", "parcial", "travado")
TIPOS_MOTIVO = ("codigo", "config", "dado", "temporario", "escolha")
ESCOPOS = ("global", "projeto", "corte")


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Capacidade:
    id: str
    area: str
    titulo: str
    status: str
    tipo_motivo: str | None
    motivo: str
    falta: tuple[str, ...]
    fonte_dado: str
    origem: dict[str, Any]
    escopo: str
    depende_de: tuple[str, ...] = ()
    verificado_em: str | None = None
    ligou_em: str | None = None
    dados: dict[str, Any] | None = field(default=None)

    def __post_init__(self) -> None:
        if self.status not in STATUS:
            raise ValueError(f"{self.id}: status inválido {self.status!r}")
        if self.tipo_motivo is not None and self.tipo_motivo not in TIPOS_MOTIVO:
            raise ValueError(f"{self.id}: tipo_motivo inválido {self.tipo_motivo!r}")
        if self.status != "ligado" and self.tipo_motivo is None:
            raise ValueError(f"{self.id}: {self.status} precisa de tipo_motivo")
        if self.escopo not in ESCOPOS:
            raise ValueError(f"{self.id}: escopo inválido {self.escopo!r}")

    def para_json(self) -> dict[str, Any]:
        j = asdict(self)
        j["falta"] = list(self.falta)
        j["depende_de"] = list(self.depende_de)
        if self.status == "travado":
            j["dados"] = None  # A5: função travada nunca exibe número
        return j
```

`picorte/capacidades/sondas.py` (núcleo):

```python
"""Sondas do ambiente (Ollama, CLIs, GPU, disco, cota do Gemini) com cache por TTL."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from picorte.capacidades.modelo import agora_iso


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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_capacidades_modelo.py -v`
Expected: 8 passed.

- [ ] **Step 5: Conferir (sem commit)**

Run: `git status --short picorte/capacidades tests/test_estudio_capacidades_modelo.py`

---

### Task 5: Sondas concretas — Ollama, CLIs, GPU, disco e cota do Gemini (429)

**Files:**
- Modify: `picorte/capacidades/sondas.py` (acrescentar no fim)
- Test: `tests/test_estudio_sondas.py`

**Interfaces:**
- Consumes:
  - `picorte.config.resolve_cli_binary(nome) -> str | None`;
  - `picorte.config.probe_nvidia_smi() -> tuple[int, str]`;
  - `picorte.engine.health.load(workdir) -> dict`, no formato `{parte: {status, detail, at}}`.
- Produces:
  - `sonda_ollama(host=None, get=httpx.get)`, com `dados={"host", "modelos": [str]}`;
  - `sonda_binario(nome, resolver=resolve_cli_binary)`, com `dados={"caminho"}`;
  - `sonda_gpu(probe=probe_nvidia_smi)`, com `dados={"gpu_name", "vram_mib"}`;
  - `sonda_disco(raiz, minimo_gib=20.0)`, com `dados={"livre_gib"}`;
  - `sonda_agy(raiz, resolver=resolve_cli_binary, janela_h=24.0, agora=None)`, com `dados={"presente": bool, "ultimo_429": str|None}` e `ok = presente and ultimo_429 is None`;
  - `NOMES_SONDAS = ("gpu", "ollama", "agy", "claude", "yt-dlp", "node", "demucs", "disco")`;
  - `sondas_padrao(raiz) -> CacheSondas`, com TTL em segundos: ollama 30, gpu 300, disco 60, agy 300, binários 86400.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_sondas.py`:

```python
import json
import time
from datetime import datetime, timedelta, timezone

import httpx

from picorte.capacidades import sondas as S


class _Resp:
    def __init__(self, dados, status=200):
        self._dados, self.status_code = dados, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("x", request=None, response=None)

    def json(self):
        return self._dados


def test_ollama_lista_modelos():
    r = S.sonda_ollama("http://h:11434", get=lambda url, timeout: _Resp(
        {"models": [{"name": "qwen3.5:9b"}, {"name": "nomic-embed-text"}]}))
    assert r.ok and r.dados["modelos"] == ["nomic-embed-text", "qwen3.5:9b"]


def test_ollama_fora_do_ar():
    def falha(url, timeout):
        raise httpx.ConnectError("recusado")

    r = S.sonda_ollama("http://h:11434", get=falha)
    assert r.ok is False and "h:11434" in r.detalhe


def test_ollama_host_sem_esquema_ganha_http(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0:11434")
    vistos = []
    S.sonda_ollama(get=lambda url, timeout: vistos.append(url) or _Resp({"models": []}))
    assert vistos == ["http://0.0.0.0:11434/api/tags"]


def test_binario_presente_e_ausente():
    assert S.sonda_binario("node", resolver=lambda n: "/usr/bin/node").ok
    assert S.sonda_binario("node", resolver=lambda n: None).ok is False


def test_gpu_com_e_sem_placa():
    assert S.sonda_gpu(probe=lambda: (8188, "RTX 4060 Ti")).dados == {
        "gpu_name": "RTX 4060 Ti", "vram_mib": 8188}
    assert S.sonda_gpu(probe=lambda: (0, "")).ok is False


def test_disco_informa_espaco_livre(tmp_path):
    r = S.sonda_disco(tmp_path, minimo_gib=0.0)
    assert r.ok and r.dados["livre_gib"] > 0


def test_agy_ve_429_recente_no_engine_health(tmp_path):
    proj = tmp_path / "abcdef123456"
    proj.mkdir()
    quando = datetime.now(timezone.utc) - timedelta(hours=2)
    (proj / "engine_health.json").write_text(json.dumps({"editor": {
        "status": "failed", "detail": "agy: 429 RESOURCE_EXHAUSTED",
        "at": quando.isoformat(timespec="seconds")}}), encoding="utf-8")
    r = S.sonda_agy(tmp_path, resolver=lambda n: "C:/agy.cmd" if n == "agy" else None)
    assert r.ok is False
    assert r.dados["presente"] is True and r.dados["ultimo_429"] == quando.isoformat(timespec="seconds")


def test_agy_429_antigo_nao_conta(tmp_path):
    proj = tmp_path / "abcdef123456"
    proj.mkdir()
    velho = datetime.now(timezone.utc) - timedelta(days=3)
    (proj / "engine_health.json").write_text(json.dumps({"editor": {
        "status": "failed", "detail": "429", "at": velho.isoformat()}}), encoding="utf-8")
    r = S.sonda_agy(tmp_path, resolver=lambda n: "agy")
    assert r.ok is True and r.dados["ultimo_429"] is None


def test_agy_429_no_erro_do_projeto(tmp_path):
    proj = tmp_path / "abcdef123456"
    proj.mkdir()
    (proj / "project.json").write_text(json.dumps({
        "error": "Editor-Chefe falhou: gemini 429", "updated": time.time() - 60}), encoding="utf-8")
    r = S.sonda_agy(tmp_path, resolver=lambda n: "agy")
    assert r.ok is False and r.dados["ultimo_429"]


def test_sondas_padrao_tem_todos_os_nomes(tmp_path):
    cache = S.sondas_padrao(tmp_path)
    assert set(cache._sondas) == set(S.NOMES_SONDAS)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_sondas.py -v`
Expected: FAIL com `AttributeError: module 'picorte.capacidades.sondas' has no attribute 'sonda_ollama'`

- [ ] **Step 3: Implementar (acrescentar ao fim de `sondas.py`)**

Acrescente aos imports do topo de `picorte/capacidades/sondas.py`:

```python
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from picorte.config import probe_nvidia_smi, resolve_cli_binary
from picorte.engine import health
```

E no fim do arquivo:

```python
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


def _ultimo_429(raiz: Path, limite: datetime) -> str | None:
    """Varre (só leitura) os projetos mais recentes atrás de 429 do Gemini depois de `limite`."""
    achados: list[datetime] = []
    pastas = sorted((p for p in raiz.glob("*") if p.is_dir()),
                    key=lambda p: p.stat().st_mtime, reverse=True)[:10]
    for pasta in pastas:
        for parte in health.load(pasta).values():
            if (isinstance(parte, dict) and parte.get("status") == "failed"
                    and "429" in str(parte.get("detail", ""))):
                try:
                    achados.append(datetime.fromisoformat(str(parte.get("at"))))
                except ValueError:
                    continue
        estado = _ler_json(pasta / "project.json")
        if "429" in str(estado.get("error") or "") and estado.get("updated"):
            achados.append(datetime.fromtimestamp(float(estado["updated"]), tz=timezone.utc))
    recentes = [a for a in achados if a.tzinfo and a >= limite]
    return max(recentes).isoformat(timespec="seconds") if recentes else None


def sonda_agy(raiz, resolver=resolve_cli_binary, janela_h: float = 24.0,
              agora: datetime | None = None) -> ResultadoSonda:
    presente = bool(resolver("agy") or resolver("gemini"))
    limite = (agora or datetime.now(timezone.utc)) - timedelta(hours=janela_h)
    ultimo = _ultimo_429(Path(raiz), limite) if presente else None
    if not presente:
        detalhe = "CLI do Gemini (agy/gemini) não encontrada"
    elif ultimo:
        detalhe = f"cota do Gemini esgotada (429) em {ultimo}"
    else:
        detalhe = f"sem 429 nas últimas {int(janela_h)} h"
    return ResultadoSonda(presente and ultimo is None, detalhe,
                          {"presente": presente, "ultimo_429": ultimo})


def sondas_padrao(raiz) -> CacheSondas:
    dia = 86400.0
    return CacheSondas({
        "gpu": (300.0, sonda_gpu),
        "ollama": (30.0, sonda_ollama),
        "agy": (300.0, lambda: sonda_agy(raiz)),
        "claude": (dia, lambda: sonda_binario("claude")),
        "yt-dlp": (dia, lambda: sonda_binario("yt-dlp")),
        "node": (dia, lambda: sonda_binario("node")),
        "demucs": (dia, lambda: sonda_binario("demucs")),
        "disco": (60.0, lambda: sonda_disco(raiz)),
    })
```

> **Correção da execução (2026-11-21):** em `projects/` a falha real do Gemini ficou gravada como `CalledProcessError ... agy.exe`, sem "429" (o `detail` é cortado em 400 caracteres). Por isso, a sonda conta qualquer falha que cite `429`, `agy` ou `gemini` (`_falha_do_gemini`), e o campo virou `ultima_falha` (era `ultimo_429`). Há dois testes a mais: o formato real e "falha do Ollama não conta". O código acima ficou só como histórico; a fonte da verdade é `picorte/capacidades/sondas.py`.

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_sondas.py tests/test_estudio_capacidades_modelo.py -v`
Expected: 18 passed.

- [ ] **Step 5: Conferir (sem commit)**

Run: `git status --short picorte/capacidades tests/test_estudio_sondas.py`

---

### Task 6: Catálogo das capacidades, regras dinâmicas e `listar_capacidades`

**Files:**
- Create: `picorte/capacidades/catalogo.py`, `picorte/capacidades/regras.py`, `picorte/capacidades/servico.py`
- Modify: `picorte/capacidades/__init__.py`
- Test: `tests/test_estudio_capacidades.py`

**Interfaces:**
- Consumes: `Capacidade` e `STATUS` (Task 4); `CacheSondas`, `ResultadoSonda` e `sondas_padrao` (Task 5); `Barramento` (Task 3).
- Produces:
  - `catalogo() -> list[Capacidade]`, com as 82 capacidades: as 81 do mapa + `SIS-14`, disco;
  - `aplicar_regras(cap: Capacidade, sondas: dict[str, ResultadoSonda]) -> Capacidade`;
  - `listar_capacidades(raiz, cache: CacheSondas | None = None) -> dict`, no formato `{"gerado_em", "capacidades": [dict], "resumo": {"ligado": n, "parcial": n, "travado": n}}`;
  - `ServicoCapacidades(raiz, cache=None, barramento=None)`, com `.atual() -> dict`, que publica `("capacidades", {"mudaram": [{"id", "de", "para"}]})` quando algum status muda.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_capacidades.py`:

```python
import re

from picorte.capacidades import ServicoCapacidades, listar_capacidades
from picorte.capacidades.catalogo import catalogo
from picorte.capacidades.sondas import CacheSondas, ResultadoSonda
from picorte.services.eventos import Barramento

QUANDO = "2026-11-21T12:00:00+00:00"


def _fixa(ok, detalhe="", **dados):
    return lambda: ResultadoSonda(ok, detalhe, dados, QUANDO)


def cache_falso(**troca):
    base = {
        "gpu": _fixa(True, gpu_name="RTX 4060 Ti", vram_mib=8188),
        "ollama": _fixa(True, host="http://localhost:11434", modelos=["qwen3.5:9b"]),
        "agy": _fixa(True, presente=True, ultimo_429=None),
        "claude": _fixa(True, caminho="claude"), "yt-dlp": _fixa(True, caminho="yt-dlp"),
        "node": _fixa(True, caminho="node"), "demucs": _fixa(True, caminho="demucs"),
        "disco": _fixa(True, livre_gib=300.0),
    }
    base.update(troca)
    return CacheSondas({k: (999.0, v) for k, v in base.items()})


def _por_id(dados):
    return {c["id"]: c for c in dados["capacidades"]}


def test_catalogo_cobre_o_mapa_inteiro():
    ids = [c.id for c in catalogo()]
    assert len(ids) == len(set(ids)) == 82
    for prefixo, n in {"SIS": 14, "FIL": 7, "REV": 15, "FON": 9, "ESC": 9, "SAU": 5,
                       "PUB": 6, "MET": 6, "RAD": 5, "LIV": 6}.items():
        assert sum(1 for i in ids if i.startswith(prefixo + "-")) == n, prefixo


def test_cada_capacidade_tem_origem_e_fonte():
    for c in catalogo():
        assert c.origem.get("epico") and c.fonte_dado and c.titulo, c.id
        assert re.fullmatch(r"[A-Z]{3}-\d+", c.id)


def test_areas_inteiras_travadas_continuam_travadas(tmp_path):
    caps = _por_id(listar_capacidades(tmp_path, cache_falso()))
    for i in ["MET-1", "MET-3", "RAD-1", "RAD-2", "PUB-5", "PUB-6", "REV-8", "LIV-1", "LIV-3"]:
        assert caps[i]["status"] == "travado", i
        assert caps[i]["dados"] is None


def test_fila_ganhou_o_lock_e_ficou_ligada(tmp_path):
    assert _por_id(listar_capacidades(tmp_path, cache_falso()))["SIS-2"]["status"] == "ligado"


def test_ollama_fora_do_ar_trava_por_config(tmp_path):
    cache = cache_falso(ollama=_fixa(False, "Ollama não respondeu", host="http://localhost:11434"))
    sis6 = _por_id(listar_capacidades(tmp_path, cache))["SIS-6"]
    assert sis6["status"] == "travado" and sis6["tipo_motivo"] == "config"
    assert sis6["dados"] is None and sis6["verificado_em"] == QUANDO


def test_ollama_no_ar_mostra_modelos(tmp_path):
    sis6 = _por_id(listar_capacidades(tmp_path, cache_falso()))["SIS-6"]
    assert sis6["status"] == "ligado" and sis6["dados"]["modelos"] == ["qwen3.5:9b"]


def test_gemini_com_429_fica_parcial_temporario(tmp_path):
    cache = cache_falso(agy=_fixa(False, "cota", presente=True, ultimo_429=QUANDO))
    sis7 = _por_id(listar_capacidades(tmp_path, cache))["SIS-7"]
    assert (sis7["status"], sis7["tipo_motivo"]) == ("parcial", "temporario")


def test_ytdlp_ausente_trava_e_demucs_ausente_e_parcial(tmp_path):
    caps = _por_id(listar_capacidades(tmp_path, cache_falso(**{"yt-dlp": _fixa(False)})))
    assert caps["SIS-11"]["status"] == "travado"
    caps = _por_id(listar_capacidades(tmp_path, cache_falso(demucs=_fixa(False))))
    assert caps["SIS-11"]["status"] == "parcial" and "demucs" in caps["SIS-11"]["motivo"]


def test_resumo_conta_os_status(tmp_path):
    dados = listar_capacidades(tmp_path, cache_falso())
    assert sum(dados["resumo"].values()) == 82


def test_servico_publica_evento_quando_status_muda(tmp_path):
    estado = {"ok": True}
    cache = CacheSondas({**{k: (0.0, v) for k, v in {
        "gpu": _fixa(True, gpu_name="g", vram_mib=1), "agy": _fixa(True, presente=True, ultimo_429=None),
        "claude": _fixa(True), "yt-dlp": _fixa(True), "node": _fixa(True), "demucs": _fixa(True),
        "disco": _fixa(True, livre_gib=99.0)}.items()},
        "ollama": (0.0, lambda: ResultadoSonda(estado["ok"], "", {"modelos": ["m"]}, QUANDO))})
    bus = Barramento()
    q = bus.assinar()
    servico = ServicoCapacidades(tmp_path, cache=cache, barramento=bus)
    servico.atual()
    assert q.empty()
    estado["ok"] = False
    servico.atual()
    tipo, dados = q.get_nowait()
    assert tipo == "capacidades"
    assert {"id": "SIS-6", "de": "ligado", "para": "travado"} in dados["mudaram"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_capacidades.py -v`
Expected: FAIL com `ImportError: cannot import name 'ServicoCapacidades'`

- [ ] **Step 3: Implementar o catálogo**

`picorte/capacidades/catalogo.py`. Os textos vêm do mapa medido em 2026-11-21. `SIS-2` passa a `ligado` porque a Task 2 entrega o lock (B9). `SIS-14` (disco) é nova, exigida pela AC 3.

```python
"""Catálogo estático das capacidades (mapa medido em 2026-11-21, brainstorm-intent.md).

O status daqui é o ponto de partida; `regras.py` sobrescreve as capacidades que dependem de sonda.
Ao ligar uma função, atualize a linha aqui (status, falta) e preencha `ligou_em`.
"""
from __future__ import annotations

from picorte.capacidades.modelo import Capacidade

MAPA_VERIFICADO_EM = "2026-11-21"


def _c(id_, area, titulo, status, tipo, falta, fonte, epico, historia, cap=None,
       escopo="global", depende=(), ligou_em=None) -> Capacidade:
    itens = tuple(p.strip() for p in falta.split(";") if p.strip()) if falta else ()
    return Capacidade(
        id=id_, area=area, titulo=titulo, status=status, tipo_motivo=tipo,
        motivo=falta or "", falta=itens, fonte_dado=fonte,
        origem={"epico": epico, "historia": historia, "cap": cap}, escopo=escopo,
        depende_de=tuple(depende), verificado_em=MAPA_VERIFICADO_EM, ligou_em=ligou_em)


L, P, T = "ligado", "parcial", "travado"


def catalogo() -> list[Capacidade]:
    return [
        # 1. Sistema
        _c("SIS-1", "sistema", "GPU detectada e preset de visão", L, None, "", "config.detect_gpu_profile", "1", "1.1"),
        _c("SIS-2", "sistema", "Fila serial de jobs (1 por vez)", L, None, "", "picorte.services.fila", "6", "6.3", ligou_em="2026-11-21"),
        _c("SIS-3", "sistema", "Lock de estágio de VRAM", L, None, "", "vram_runner.py", "2", "2.2"),
        _c("SIS-4", "sistema", "Modo Madrugada", P, "codigo", "agendador e controle na tela; só existe is_in_night_window", "vram_runner.py", "2", "2.2"),
        _c("SIS-5", "sistema", "Banco", P, "dado", "B1–B4 e B6 (história 6.4)", "picorte.db", "2", "2.1", depende=("FON-4",)),
        _c("SIS-6", "sistema", "Motor de IA: Ollama", L, None, "", "Ollama /api/tags", "2", "2.3"),
        _c("SIS-7", "sistema", "Motor de IA: Gemini (agy)", L, None, "", "engine_health.json + erro do projeto", "2", "2.3"),
        _c("SIS-8", "sistema", "Motor de IA: Claude CLI", L, None, "", "claude no PATH", "2", "2.3"),
        _c("SIS-9", "sistema", "Modo Dupla", P, "dado", "nenhum uso real registrado", "llm_router", "2", "2.3", depende=("SIS-6", "SIS-8")),
        _c("SIS-10", "sistema", "Modo determinístico", L, "escolha", "aviso: nada do E3.5 roda nesse modo", "options.ai_mode", "3", "auditoria E3"),
        _c("SIS-11", "sistema", "yt-dlp, node e demucs", L, None, "", "sondas de binário", "1", "W4/W9"),
        _c("SIS-12", "sistema", "Servidor MCP", P, "codigo", "B5 fila única (história 6.4)", "picorte/mcp/server.py", "2", "2.4"),
        _c("SIS-13", "sistema", "Custos e teto mensal", T, "codigo", "registro de gastos (B12)", "—", "6", "regra 6"),
        _c("SIS-14", "sistema", "Espaço livre em disco", L, None, "", "shutil.disk_usage", "6", "6.3"),
        # 2. Fila e projetos
        _c("FIL-1", "fila", "Criar projeto (URL ou arquivo; lote de 1–100)", L, None, "", "POST /api/projetos, /api/lote", "1", "E1"),
        _c("FIL-2", "fila", "Portão P1 antes de baixar", L, None, "", "project.json.source_gate", "4", "4.1", escopo="projeto"),
        _c("FIL-3", "fila", "Estágio, progresso e log", P, "codigo", "textos em PT-BR; resumo do log; título real no lugar da URL", "project.json, job.log", "1", "E1", escopo="projeto"),
        _c("FIL-4", "fila", "VOD longo em blocos de 30 min e por seções", L, None, "", "*.partNNN.json, sections/", "1", "1.2", escopo="projeto"),
        _c("FIL-5", "fila", "Falha do Editor-Chefe com próximo passo", P, "codigo", "ação trocar motor e retomar", "project.error", "1", "auditoria 1b", escopo="projeto"),
        _c("FIL-6", "fila", "Separar conjunto de prova da produção", P, "codigo", "filtro na tela", "options.benchmark_blind", "3.6", "3.6.1"),
        _c("FIL-7", "fila", "Caça profunda e busca por pergunta", P, "codigo", "controles na tela; hoje só CLI/MCP", "hunt_mode, picorte_buscar_por_pergunta", "3.5", "3.5.5", escopo="projeto"),
        # 3. Revisão
        _c("REV-1", "revisao", "Arquétipo, tier, título, faixa 2s, 1º comentário, motivo", L, None, "", "segments.json, selection.json, .meta.json", "3.5", "3.5.3", escopo="corte"),
        _c("REV-2", "revisao", "Sinais medidos por corte", P, "dado", "B2: gravar só o que foi medido; não medido sai null", "campo sinais, engine_health.json", "3", "3.2/3.5.4", escopo="corte"),
        _c("REV-3", "revisao", "Ajustar início/fim; editar transcrição e legenda", L, None, "", "/candidates, /transcript", "1", "E1", escopo="corte"),
        _c("REV-4", "revisao", "Preview 480p e render final", L, None, "", "run (preview/render)", "1", "E1", escopo="corte"),
        _c("REV-5", "revisao", "Thumbnail automática", L, None, "", "*_thumb.png", "3.5", "3.5", escopo="corte"),
        _c("REV-6", "revisao", "Faixa de contexto 2s no vídeo", L, None, "", "render_clips.py", "3", "3.4", escopo="corte"),
        _c("REV-7", "revisao", "Keyframes (o LLM vê 3 frames)", L, "escolha", "desligado por padrão; custo estimado por VOD (Sonnet)", "options.keyframes", "3.5", "3.5.4", escopo="projeto"),
        _c("REV-8", "revisao", "👍/👎 por corte", T, "codigo", "B10 + endpoint (história 6.6)", "—", "6", "6.6", escopo="corte"),
        _c("REV-9", "revisao", "Salvar como Exemplo Ouro", T, "codigo", "endpoint de gravação", "golden_examples.json", "6", "6.6", escopo="corte"),
        _c("REV-10", "revisao", "Cold Open e Seamless Loop", T, "codigo", "render", "retention_engine", "3.7", "3.7.1", escopo="corte"),
        _c("REV-11", "revisao", "Layout dinâmico e Sniper Crop", T, "codigo", "ligar ao render", "reframe_games", "3.7", "3.7.2", escopo="corte"),
        _c("REV-12", "revisao", "Par Short ↔ Longo", T, "codigo", "corrigir o bug A11; parent_long_clip_id NULL", "clips", "3.7", "3.7.3", escopo="corte"),
        _c("REV-13", "revisao", "Arcos de 2 atos e compilação por arquétipo", P, "codigo", "render; hoje só JSON no modo deep", "two_act_arc, archetype_compiler", "3.7", "3.7.4", escopo="projeto"),
        _c("REV-14", "revisao", "Compilação cross-streamer", T, "codigo", "Épico 5", "—", "5", "A10"),
        _c("REV-15", "revisao", "nobada/mico, standalone, bordas por frase, ouro com 2 sinais", T, "codigo", "histórias 3.6.3–3.6.5", "—", "3.6", "3.6.3"),
        # 4. Fontes e permissões (P1)
        _c("FON-1", "fontes", "Lista de fontes com status e base da permissão", L, None, "", "sources + registry.json", "4", "4.1"),
        _c("FON-2", "fontes", "Cadastrar fonte e mudar permissão", L, None, "", "StudioService.create_source", "2", "2.4"),
        _c("FON-3", "fontes", "Tentativas barradas", P, "dado", "registro próprio; hoje só no erro do projeto", "project.error [P1:pre_ingest]", "4", "4.1"),
        _c("FON-4", "fontes", "Elo fonte → vídeos → cortes", T, "dado", "B1: videos.source_id (história 6.4)", "videos.source_id", "2", "2.1"),
        _c("FON-5", "fontes", "Políticas por publisher/jogo", P, "dado", "B6: sincronizar publishers.json (história 6.4)", "assets/policies/publishers.json", "4", "4.1"),
        _c("FON-6", "fontes", "Campanhas CPM", P, "codigo", "tela de cadastro e radar", "campaigns", "4", "4.1/5.1"),
        _c("FON-7", "fontes", "Pausar fonte (disjuntor manual)", L, None, "", "/api/risco/pausar-fonte, MCP", "4", "4.1"),
        _c("FON-8", "fontes", "Dossiês de jogo", L, None, "", "picorte/ai/game_dossiers/", "3.5", "3.5.5"),
        _c("FON-9", "fontes", "Perfis e piadas internas", T, "codigo", "história 5.4", "—", "5", "5.4"),
        # 5. Escudo (P1)
        _c("ESC-1", "escudo", "Veredito por corte e por rede", P, "dado", "B3; cortes antigos sem veredito: re-auditar", ".meta.json.risk_verdict", "4", "4.5", escopo="corte"),
        _c("ESC-2", "escudo", "Selo Verde 15s (bleep e ***)", L, None, "", "render", "4", "4.4", escopo="corte"),
        _c("ESC-3", "escudo", "Remoção de música com Demucs", L, None, "", "clean_music_in_render", "4", "4.3", escopo="corte", depende=("SIS-11",)),
        _c("ESC-4", "escudo", "React Guard", L, None, "", "orquestrador", "4", "4.4", escopo="corte"),
        _c("ESC-5", "escudo", "YPP, originalidade TikTok e pHash", P, "dado", "B3 (história 6.4)", ".meta.json", "4", "4.2", escopo="corte"),
        _c("ESC-6", "escudo", "Limpeza de texto por rede", L, None, "", "publish_kit", "4", "4.2", escopo="corte"),
        _c("ESC-7", "escudo", "Cadência e cooldown de 48h", L, None, "", "work/cadence_state.json", "4", "4.2"),
        _c("ESC-8", "escudo", "Registrar claim manual → pausa", P, "codigo", "formulário na tela", "claims_events", "4", "4.1"),
        _c("ESC-9", "escudo", "Monitor automático de claims", T, "codigo", "história 6.2", "—", "6", "6.2", "CAP-16"),
        # 6. Saúde e benchmark
        _c("SAU-1", "saude", "Saúde por projeto e por parte", L, None, "", "engine_health.json", "1", "1b/W9", escopo="projeto"),
        _c("SAU-2", "saude", "Confiança do projeto", T, "codigo", "história 3.6.5", "—", "3.6", "3.6.5", escopo="projeto"),
        _c("SAU-3", "saude", "Precision@K com lift contra o acaso", L, None, "amostra pequena (n=1)", "benchmarks/*.json", "3.6", "3.6.1"),
        _c("SAU-4", "saude", "Gabaritos acumulados para a 3.6.6", L, None, "", "benchmarks/gabaritos/", "3.6", "3.6.1"),
        _c("SAU-5", "saude", "Canário semanal e yt-dlp diário", T, "codigo", "W9", "—", "6", "W9"),
        # 7. Publicação
        _c("PUB-1", "publicacao", "Pacote do Dia", L, None, "", "export-bundle", "4", "4.5", escopo="projeto"),
        _c("PUB-2", "publicacao", "Kit por rede, copiar em 1 clique", L, None, "", ".meta.json.publish_kit", "4", "4.2/6.1", escopo="corte"),
        _c("PUB-3", "publicacao", "Registrar a URL publicada", L, None, "", "publications", "6", "6.1", escopo="corte"),
        _c("PUB-4", "publicacao", "YouTube Longo e Related Video", T, "codigo", "B11 + 3.7.3", "—", "6", "3.7.3", "CAP-15", depende=("REV-12",)),
        _c("PUB-5", "publicacao", "Contas OAuth das 5 redes", T, "codigo", "6.1 cofre de tokens; app aprovado por rede (T1)", "social_accounts", "6", "6.1", "CAP-15"),
        _c("PUB-6", "publicacao", "Publicação automática", T, "codigo", "6.1 + auditorias", "—", "6", "6.1", "CAP-15", depende=("PUB-5",)),
        # 8. Métricas e aprendizado
        _c("MET-1", "metricas", "Snapshots 1h/24h/7d", T, "codigo", "história 7.1", "metric_snapshots", "7", "7.1", "CAP-18", depende=("PUB-3",)),
        _c("MET-2", "metricas", "Recompensa anti-clickbait", T, "codigo", "história 7.1", "—", "7", "7.1", "CAP-18", depende=("MET-1",)),
        _c("MET-3", "metricas", "Bandit com esquecimento", T, "codigo", "história 7.2", "—", "7", "7.2", "CAP-18", depende=("MET-1",)),
        _c("MET-4", "metricas", "Reciclagem A/B do gancho", T, "codigo", "história 7.2", "—", "7", "7.2", "CAP-18", depende=("MET-3",)),
        _c("MET-5", "metricas", "Dataset rotulado e treino local", T, "codigo", "história 7.3", "—", "7", "7.3", "CAP-18", depende=("REV-8",)),
        _c("MET-6", "metricas", "Pesos calibrados pelo gabarito (≥ 20 VODs)", T, "codigo", "história 3.6.6", "—", "3.6", "3.6.6", depende=("SAU-4",)),
        # 9. Radar
        _c("RAD-1", "radar", "Tendências e calendário", T, "codigo", "história 5.1", "—", "5", "5.1"),
        _c("RAD-2", "radar", "Monitor de lives ao vivo, com chat da Twitch", T, "codigo", "história 5.2", "—", "5", "5.2"),
        _c("RAD-3", "radar", "Caçador de clipes de terceiros", T, "codigo", "história 5.3", "—", "5", "5.3"),
        _c("RAD-4", "radar", "Detector de treta e consenso entre streamers", T, "codigo", "história 5.3", "—", "5", "5.3"),
        _c("RAD-5", "radar", "Limpeza de dados de terceiros em 30 dias", T, "codigo", "história 5.1", "—", "5", "5.1"),
        # 10. Lives
        _c("LIV-1", "lives", "Ao vivo: streamers cadastrados transmitindo agora", T, "config", "credencial de app da Twitch (grátis e revogável); consulta oficial de está ao vivo", "sources + API oficial", "6", "6.5"),
        _c("LIV-2", "lives", "Abrir a live com player ao vivo e opções de corte", T, "codigo", "player embutido oficial + captura da live (5.2)", "—", "5", "5.2", depende=("LIV-1",)),
        _c("LIV-3", "lives", "Em alta", T, "codigo", "radar com a ordenação oficial das APIs (5.1)", "—", "5", "5.1"),
        _c("LIV-4", "lives", "Recentes: vídeos recentes dos streamers cadastrados", P, "codigo", "listar os vídeos recentes dos canais do registry.json (história 6.5)", "registry.json + API", "6", "6.5"),
        _c("LIV-5", "lives", "Cortar um VOD na Sala do vídeo", P, "codigo", "Sala do vídeo (história 6.5); ingestão e portão P1 já ligados", "POST /api/projetos", "6", "6.5"),
        _c("LIV-6", "lives", "Selo AO VIVO, espectadores, duração", T, "codigo", "só com dado da API oficial e verificado_em", "API oficial", "5", "5.2", depende=("LIV-1",)),
    ]
```

- [ ] **Step 4: Implementar as regras dinâmicas**

`picorte/capacidades/regras.py`:

```python
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
        if a.dados.get("ultimo_429"):
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
```

- [ ] **Step 5: Implementar o serviço**

`picorte/capacidades/servico.py`:

```python
"""Uma fonte só para o painel e para os agentes (AD-10): GET /api/capacidades e MCP picorte_capacidades."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from picorte.capacidades.catalogo import catalogo
from picorte.capacidades.modelo import STATUS, agora_iso
from picorte.capacidades.regras import aplicar_regras
from picorte.capacidades.sondas import CacheSondas, sondas_padrao
from picorte.services.eventos import Barramento


def listar_capacidades(raiz, cache: CacheSondas | None = None) -> dict[str, Any]:
    sondas = (cache or sondas_padrao(Path(raiz))).todas()
    itens = [aplicar_regras(c, sondas).para_json() for c in catalogo()]
    resumo = {s: sum(1 for i in itens if i["status"] == s) for s in STATUS}
    return {"gerado_em": agora_iso(), "capacidades": itens, "resumo": resumo}


class ServicoCapacidades:
    def __init__(self, raiz, cache: CacheSondas | None = None,
                 barramento: Barramento | None = None) -> None:
        self.raiz = Path(raiz)
        self.cache = cache or sondas_padrao(self.raiz)
        self.barramento = barramento
        self._ultimo: dict[str, str] | None = None
        self._trava = threading.Lock()

    def atual(self) -> dict[str, Any]:
        dados = listar_capacidades(self.raiz, self.cache)
        status = {c["id"]: c["status"] for c in dados["capacidades"]}
        with self._trava:
            anterior, self._ultimo = self._ultimo, status
        if anterior is not None and self.barramento is not None:
            mudaram = [{"id": i, "de": anterior.get(i), "para": s}
                       for i, s in status.items() if anterior.get(i) != s]
            if mudaram:
                self.barramento.publicar("capacidades", {"mudaram": mudaram})
        return dados
```

`picorte/capacidades/__init__.py` (substituir):

```python
"""Contrato de capacidades do Picorte: o backend decide o status real de cada função (A5)."""
from picorte.capacidades.servico import ServicoCapacidades, listar_capacidades

__all__ = ["ServicoCapacidades", "listar_capacidades"]
```

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_capacidades.py tests/test_estudio_capacidades_modelo.py tests/test_estudio_sondas.py -v`
Expected: todos passam (28).

- [ ] **Step 7: Conferir (sem commit)**

Run: `git status --short picorte/capacidades tests/test_estudio_capacidades.py`

---

### Task 7: `GET /api/capacidades` e ferramenta MCP `picorte_capacidades`, com teste de paridade

**Files:**
- Create: `picorte/api/rotas_sistema.py`
- Modify: `picorte/api/app.py` (`create_app` e `_registrar_rotas`), `picorte/mcp/server.py`
- Test: `tests/test_estudio_api_capacidades.py`

**Interfaces:**
- Consumes: `ServicoCapacidades` e `listar_capacidades` (Task 6); `Barramento` e `FilaEstudio` (Task 3).
- Produces:
  - `create_app(..., fila=None, barramento=None, capacidades=None)`;
  - `app.state.fila`, `app.state.barramento` e `app.state.capacidades` (`ServicoCapacidades`);
  - `GET /api/capacidades`, que devolve o mesmo dicionário de `listar_capacidades`;
  - `PicorteMCPServer(service=None, *, db=None, capacidades=None)`, em que `capacidades: Callable[[], dict]`; a ferramenta se chama `picorte_capacidades`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_api_capacidades.py`:

```python
from fastapi.testclient import TestClient

from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades, listar_capacidades
from picorte.mcp.server import PicorteMCPServer
from estudio_fakes import cache_falso


def _cliente(tmp_path, cache):
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "dist",
                     capacidades=ServicoCapacidades(raiz, cache=cache))
    return TestClient(app)


def test_endpoint_devolve_o_contrato(tmp_path):
    r = _cliente(tmp_path, cache_falso()).get("/api/capacidades")
    assert r.status_code == 200
    dados = r.json()
    assert len(dados["capacidades"]) == 82
    assert dados["capacidades"][0]["id"] == "SIS-1"


def test_paridade_painel_e_mcp(tmp_path):
    cache = cache_falso()
    raiz = tmp_path / "projects"
    api = _cliente(tmp_path, cache).get("/api/capacidades").json()
    mcp = PicorteMCPServer(service=object(),
                           capacidades=lambda: listar_capacidades(raiz, cache))
    assert any(t["name"] == "picorte_capacidades" for t in mcp.list_tools())
    via_mcp = mcp.call_tool("picorte_capacidades", {})
    assert via_mcp["capacidades"] == api["capacidades"]
    assert via_mcp["resumo"] == api["resumo"]
```

Observação: `tests/` não tem `__init__.py`. Por isso, os fakes `QUANDO`, `_fixa` e `cache_falso` moram em `tests/estudio_fakes.py`, criado na Task 6, e são importados com `from estudio_fakes import ...`. O pytest, no modo `prepend`, põe `tests/` no `sys.path`. Onde este plano mostrar `from tests.test_estudio_capacidades import ...`, leia `from estudio_fakes import ...`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_api_capacidades.py -v`
Expected: FAIL com `TypeError: create_app() got an unexpected keyword argument 'capacidades'`

- [ ] **Step 3: Criar o módulo de rotas do sistema**

`picorte/api/rotas_sistema.py`:

```python
"""Rotas de sistema do Estúdio: capacidades, taxonomia, eventos, config, banco e risco."""
from __future__ import annotations

from fastapi import APIRouter, Request

rotas = APIRouter()


@rotas.get("/api/capacidades")
def capacidades(request: Request):
    return request.app.state.capacidades.atual()
```

- [ ] **Step 4: Ligar no app**

Em `picorte/api/app.py`:
1. Troque a assinatura e o corpo de `create_app` por:

```python
def create_app(raiz_projetos, *, porta: int = 8770, hosts: tuple[str, ...] | None = None,
               token: str | None = None, dist: Path | None = None, fila=None,
               barramento=None, capacidades=None) -> FastAPI:
    from picorte.capacidades import ServicoCapacidades
    from picorte.services.eventos import Barramento
    from picorte.services.fila import FilaEstudio

    app = FastAPI(title="Picorte · Estúdio do Criador", docs_url=None, redoc_url=None,
                  openapi_url=None)
    raiz = Path(raiz_projetos).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    app.state.raiz = raiz
    app.state.token = token or secrets.token_urlsafe(32)
    app.state.porta = porta
    app.state.barramento = barramento or (fila.barramento if fila else Barramento())
    app.state.fila = fila or FilaEstudio(raiz, barramento=app.state.barramento)
    app.state.capacidades = capacidades or ServicoCapacidades(raiz, barramento=app.state.barramento)
    if app.state.capacidades.barramento is None:
        app.state.capacidades.barramento = app.state.barramento
    app.add_middleware(PortaoSeguranca, hosts=hosts or (f"127.0.0.1:{porta}",),
                       token=app.state.token)
    _registrar_erros(app)
    _registrar_rotas(app)
    _registrar_spa(app, Path(dist) if dist else DIST_PADRAO)
    return app
```

Nota da execução: o FastAPI 0.165 (Starlette 1.0) não tem mais `add_event_handler`. O desligamento usa `lifespan`: um `@asynccontextmanager async def _ciclo_de_vida(app)` que faz `yield` e depois `app.state.fila.fechar()`, passado em `FastAPI(..., lifespan=_ciclo_de_vida)`.

2. Troque `_registrar_rotas` por:

```python
def _registrar_rotas(app: FastAPI) -> None:
    from picorte.api.rotas_sistema import rotas as rotas_sistema

    app.include_router(rotas_sistema)
```

3. Acrescente, em `_registrar_erros`, o tratamento de projeto ocupado (409):

```python
    from picorte.services.job_lock import ProjetoOcupado

    @app.exception_handler(ProjetoOcupado)
    async def _ocupado(_: Request, exc: ProjetoOcupado):
        return _erro(409, str(exc))
```

- [ ] **Step 5: Ferramenta MCP**

Em `picorte/mcp/server.py`:
1. Troque o `__init__`:

```python
    def __init__(self, service: StudioService | None = None, *, db: Any = None,
                 capacidades: "Callable[[], dict[str, Any]] | None" = None) -> None:
        self.service = service or (StudioService(db=db) if db is not None else StudioService())
        self._capacidades = capacidades
```

2. Acrescente aos imports do topo: `from typing import Any, Callable`, trocando `from typing import Any`.
3. Acrescente ao fim da lista de `list_tools()`, antes do `]`:

```python
            {
                "name": "picorte_capacidades",
                "description": "Status real de cada função do Picorte (ligado/parcial/travado), com motivo, o que falta, fonte do dado e origem. Mesma função do painel (GET /api/capacidades).",
                "inputSchema": {"type": "object", "properties": {}},
            },
```

4. Em `call_tool`, antes do `raise ValueError(...)` final:

```python
        if name == "picorte_capacidades":
            if self._capacidades is not None:
                return self._capacidades()
            from picorte.capacidades import listar_capacidades
            from picorte.config import PROJECT_ROOT
            return listar_capacidades(PROJECT_ROOT / "projects")
```

- [ ] **Step 6: Rodar e ver passar (inclusive os testes antigos do MCP e da base)**

Run: `python -m pytest tests/test_estudio_api_capacidades.py tests/test_estudio_api_base.py -v`
Expected: todos passam.

Run: `python -m pytest tests -q -k "mcp"`
Expected: os testes antigos do MCP continuam passando. Se algum testa o número exato de ferramentas, ajuste a contagem: **essa** mudança é esperada; registre-a no relatório da tarefa.

- [ ] **Step 7: Conferir (sem commit)**

Run: `git status --short picorte/api picorte/mcp tests/test_estudio_api_capacidades.py`

---

### Task 8: `GET /api/taxonomia`

**Files:**
- Create: `picorte/services/taxonomia.py`
- Modify: `picorte/api/rotas_sistema.py`
- Test: `tests/test_estudio_taxonomia.py`

**Interfaces:**
- Consumes:
  - `picorte.engine.multitrack.CANONICAL_ARCHETYPES` e `CANONICAL_TIERS`;
  - `picorte.ai.llm_router.VALID_AI_MODES` (só leitura de constante);
  - `picorte.config.VISION_PRESETS`;
  - `render_clips.ASPECTS` e `CAPTION_STYLES`;
  - `picorte.engine.publish_kit.PLATFORM_UPLOAD_URLS`.
- Produces: `taxonomia() -> dict`, com as chaves:
  - `arquetipos`, `tiers`, `redes`, `modos_ia`;
  - `presets_visao`, `aspectos`, `estilos_legenda`, `layouts`.

  Cada item é `{"id", "rotulo"}`. As redes trazem também `"status"`: `ligado` para as 4 do kit assistido e `travado` para `youtube_longo` (PUB-4).

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_taxonomia.py`:

```python
from fastapi.testclient import TestClient

from picorte.api import create_app
from picorte.engine.multitrack import CANONICAL_ARCHETYPES, CANONICAL_TIERS
from picorte.services.taxonomia import taxonomia


def test_listas_vem_das_constantes_canonicas():
    t = taxonomia()
    assert [a["id"] for a in t["arquetipos"]] == list(CANONICAL_ARCHETYPES)
    assert [x["id"] for x in t["tiers"]] == list(CANONICAL_TIERS)
    assert {m["id"] for m in t["modos_ia"]} == {"heuristic", "ollama", "claude", "gemini", "dupla"}
    assert {"16:9", "9:16"} <= {a["id"] for a in t["aspectos"]}
    assert all(item["rotulo"] for chave in t for item in t[chave])


def test_redes_dizem_o_proprio_status():
    redes = {r["id"]: r["status"] for r in taxonomia()["redes"]}
    assert redes["youtube_shorts"] == "ligado"
    assert redes["youtube_longo"] == "travado"


def test_endpoint(tmp_path):
    app = create_app(tmp_path / "p", hosts=("testserver",), token="t", dist=tmp_path / "d")
    r = TestClient(app).get("/api/taxonomia")
    assert r.status_code == 200 and r.json()["tiers"][0]["id"] == "ouro"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_taxonomia.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'picorte.services.taxonomia'`

- [ ] **Step 3: Implementar**

`picorte/services/taxonomia.py`:

```python
"""Listas canônicas para o front (B7): o painel nunca fixa arquétipos, tiers, redes ou modos."""
from __future__ import annotations

from typing import Any

ROTULOS_ARQUETIPO = {
    "callback_oculto": "Callback oculto", "caos_coop": "Caos no coop", "rage_tilt": "Rage / tilt",
    "serio_realtalk": "Papo sério", "polemica_hottake": "Polêmica / hot take",
    "descoberta_detalhe": "Descoberta de detalhe", "clutch_fail": "Clutch ou fail",
    "susto_tensao": "Susto / tensão", "deadpan_karma": "Deadpan / karma",
    "chat_trolagem": "Trolagem do chat",
}
ROTULOS_TIER = {"ouro": "Ouro", "forte": "Forte", "experimental": "Experimental"}
ROTULOS_MODO = {"heuristic": "Determinístico (sem IA)", "ollama": "Só Ollama (local)",
                "claude": "Só Claude", "gemini": "Só Gemini", "dupla": "Dupla (filtro + acompanhante)"}
ROTULOS_REDE = {"youtube_shorts": "YouTube Shorts", "tiktok": "TikTok",
                "instagram_reels": "Instagram Reels", "facebook_reels": "Facebook Reels"}
ROTULOS_LAYOUT = {"single": "Tela única", "split": "Tela dividida", "games": "Facecam + jogo"}


def _itens(ids, rotulos: dict[str, str]) -> list[dict[str, Any]]:
    return [{"id": i, "rotulo": rotulos.get(i, i)} for i in ids]


def taxonomia() -> dict[str, list[dict[str, Any]]]:
    import render_clips
    from picorte.ai.llm_router import VALID_AI_MODES
    from picorte.config import VISION_PRESETS
    from picorte.engine.multitrack import CANONICAL_ARCHETYPES, CANONICAL_TIERS
    from picorte.engine.publish_kit import PLATFORM_UPLOAD_URLS

    redes = [{**item, "status": "ligado"} for item in _itens(PLATFORM_UPLOAD_URLS, ROTULOS_REDE)]
    redes.append({"id": "youtube_longo", "rotulo": "YouTube Longo", "status": "travado",
                  "capacidade": "PUB-4"})
    return {
        "arquetipos": _itens(CANONICAL_ARCHETYPES, ROTULOS_ARQUETIPO),
        "tiers": _itens(CANONICAL_TIERS, ROTULOS_TIER),
        "redes": redes,
        "modos_ia": _itens(VALID_AI_MODES, ROTULOS_MODO),
        "presets_visao": [{"id": "auto", "rotulo": "Automático (detecta a GPU)"}] + [
            {"id": k, "rotulo": str(v.get("label") or k)} for k, v in VISION_PRESETS.items()],
        "aspectos": _itens(render_clips.ASPECTS, {}),
        "estilos_legenda": _itens(render_clips.CAPTION_STYLES, {}),
        "layouts": _itens(ROTULOS_LAYOUT, ROTULOS_LAYOUT),
    }
```

Em `picorte/api/rotas_sistema.py`, acrescente:

```python
@rotas.get("/api/taxonomia")
def rota_taxonomia():
    from picorte.services.taxonomia import taxonomia
    return taxonomia()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_taxonomia.py -v`
Expected: 3 passed.

- [ ] **Step 5: Conferir (sem commit)**

Run: `git status --short picorte/services/taxonomia.py picorte/api tests/test_estudio_taxonomia.py`

---

### Task 9: SSE `/api/eventos`

**Files:**
- Modify: `picorte/api/rotas_sistema.py`
- Test: `tests/test_estudio_eventos.py`

**Interfaces:**
- Consumes: `app.state.barramento` (`Barramento`), `app.state.capacidades.atual()`, `formatar_sse`.
- Produces: `GET /api/eventos?max_eventos=N` (`text/event-stream`):
  - a primeira mensagem é `event: ola` com `{"resumo": {...}}` das capacidades;
  - depois vêm os eventos do barramento;
  - a cada 15 s sem evento, sai `: ping` e as capacidades são reavaliadas (a mudança vira evento);
  - `max_eventos` serve para testes e fecha o fluxo depois de N eventos, contando o `ola`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_eventos.py`:

```python
import threading
import time

from fastapi.testclient import TestClient

from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from estudio_fakes import cache_falso


def test_fluxo_comeca_com_ola_e_entrega_eventos_do_barramento(tmp_path):
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()))
    bus = app.state.barramento

    def publicar_depois():
        time.sleep(0.5)
        bus.publicar("job", {"projeto": "abcdef123456", "fase": "inicio"})

    threading.Thread(target=publicar_depois, daemon=True).start()
    with TestClient(app).stream("GET", "/api/eventos?max_eventos=2") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        corpo = "".join(r.iter_text())
    assert corpo.startswith("retry: 3000\n\nevent: ola\n")
    assert 'event: job\ndata: {"projeto": "abcdef123456", "fase": "inicio"}' in corpo
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_eventos.py -v`
Expected: FAIL com 404 ou `AssertionError` no `content-type`.

- [ ] **Step 3: Implementar**

Em `picorte/api/rotas_sistema.py`, acrescente:

```python
import queue

from fastapi.responses import StreamingResponse

from picorte.services.eventos import formatar_sse

INTERVALO_PING = 15.0


@rotas.get("/api/eventos")
def eventos(request: Request, max_eventos: int | None = None):
    estado = request.app.state
    assinatura = estado.barramento.assinar()

    def fluxo():
        enviados = 0
        try:
            yield "retry: 3000\n\n"
            yield formatar_sse("ola", {"resumo": estado.capacidades.atual()["resumo"]})
            enviados += 1
            while max_eventos is None or enviados < max_eventos:
                try:
                    tipo, dados = assinatura.get(timeout=INTERVALO_PING)
                except queue.Empty:
                    estado.capacidades.atual()  # mudança de status vira evento no barramento
                    yield ": ping\n\n"
                    continue
                yield formatar_sse(tipo, dados)
                enviados += 1
        finally:
            estado.barramento.cancelar(assinatura)

    return StreamingResponse(fluxo(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
```

Mova `import queue` e os outros imports para o topo do arquivo, junto dos imports existentes.

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_eventos.py -v`
Expected: 1 passed, em menos de 3 s.

- [ ] **Step 5: Conferir (sem commit)**

Run: `git status --short picorte/api tests/test_estudio_eventos.py`

---

### Task 10: Projetos (leitura) e mídia com Range/206; `detalhe_projeto` movido para serviço

**Files:**
- Create: `picorte/services/projeto_detalhe.py`, `picorte/api/rotas_projetos.py`
- Modify: `dashboard.py` (remover o corpo de `project_detail`, importar do serviço); `picorte/api/app.py` (`_registrar_rotas`)
- Test: `tests/test_estudio_api_projetos.py`

**Interfaces:**
- Consumes: `FilaEstudio.listar/estado/ocupado` (Task 3).
- Produces:
  - `detalhe_projeto(raiz, pid) -> dict`, com as mesmas chaves do `project_detail` antigo; o campo `project` traz o `status` efetivo quando chamado pela rota;
  - `GET /api/projetos` → `{"projetos": [...]}`;
  - `GET /api/projetos/{pid}` → o detalhe com `"busy"`;
  - `GET /media/{pid}/source`;
  - `GET /media/{pid}/{clips|previews}/{arquivo}`, que aceita Range e responde 206.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_api_projetos.py`:

```python
import json

from fastapi.testclient import TestClient

import projects
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from estudio_fakes import cache_falso

PID = "abcdef123456"


def _app(tmp_path, status="running"):
    raiz = tmp_path / "projects"
    path = raiz / PID
    (path / "clips").mkdir(parents=True)
    projects.atomic_json(path / "project.json", {
        "id": PID, "source": "x.mp4", "options": {}, "status": status, "stage": "render",
        "created": 1.0, "updated": 1.0, "cache": {}, "renders": {}, "error": None})
    (path / "clips" / "01.mp4").write_bytes(bytes(range(256)) * 4)
    video = tmp_path / "fonte.mp4"
    video.write_bytes(b"0123456789")
    (path / "transcript.json").write_text(json.dumps({"video": str(video), "duration": 10}),
                                          encoding="utf-8")
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()))
    return TestClient(app), path


def test_listar_e_abrir_nunca_escrevem_project_json(tmp_path):
    c, path = _app(tmp_path)
    antes = (path / "project.json").read_bytes()
    lista = c.get("/api/projetos").json()["projetos"]
    detalhe = c.get(f"/api/projetos/{PID}").json()
    assert (path / "project.json").read_bytes() == antes
    assert lista[0]["status"] == "interrupted"
    assert detalhe["project"]["status"] == "interrupted"
    assert detalhe["busy"] is False
    assert detalhe["files"][0]["url"] == f"/media/{PID}/clips/01.mp4"


def test_id_invalido_e_400(tmp_path):
    c, _ = _app(tmp_path)
    assert c.get("/api/projetos/..%2F..").status_code in (400, 404)
    assert c.get("/api/projetos/XYZ").status_code == 400


def test_midia_inteira_e_parcial(tmp_path):
    c, _ = _app(tmp_path)
    r = c.get(f"/media/{PID}/clips/01.mp4")
    assert r.status_code == 200 and len(r.content) == 1024
    r = c.get(f"/media/{PID}/clips/01.mp4", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206
    assert r.headers["content-range"] == "bytes 10-19/1024"
    assert r.content == bytes(range(10, 20))


def test_midia_recusa_extensao_e_pasta_fora_da_lista(tmp_path):
    c, path = _app(tmp_path)
    (path / "clips" / "x.py").write_text("print(1)", encoding="utf-8")
    assert c.get(f"/media/{PID}/clips/x.py").status_code == 400
    assert c.get(f"/media/{PID}/work/01.mp4").status_code == 400


def test_video_fonte(tmp_path):
    c, _ = _app(tmp_path)
    assert c.get(f"/media/{PID}/source").content == b"0123456789"


def test_dashboard_antigo_usa_o_mesmo_detalhe():
    import dashboard
    from picorte.services.projeto_detalhe import detalhe_projeto
    assert dashboard.project_detail is detalhe_projeto
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_api_projetos.py -v`
Expected: FAIL (`ModuleNotFoundError: picorte.services.projeto_detalhe` ou 404 nas rotas).

- [ ] **Step 3: Mover `project_detail` para o serviço**

Crie `picorte/services/projeto_detalhe.py` com a docstring `"""Detalhe de um projeto para o painel (movido do dashboard.py; só leitura)."""`. Acrescente `from pathlib import Path` e `import projects` e **copie, sem mudar a lógica**, o corpo da função `project_detail` de `dashboard.py` (linhas 44–115), renomeando a função para `detalhe_projeto(root, project_id)`. A única mudança permitida: os dois `from picorte.services.studio_service import StudioService`, que já são internos à função, continuam onde estão.

Em `dashboard.py`, apague a função `project_detail` inteira (linhas 44–115) e, junto dos imports do topo, acrescente:

```python
from picorte.services.projeto_detalhe import detalhe_projeto as project_detail
```

Run: `python -m pytest tests/test_dashboard.py tests/test_studio.py -q`
Expected: passam como antes da mudança.

- [ ] **Step 4: Criar as rotas de projeto**

`picorte/api/rotas_projetos.py`:

```python
"""Rotas de projetos do Estúdio: leitura (sem escrita), mídia com Range e ações explícitas."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

import projects
from picorte.services.projeto_detalhe import detalhe_projeto

rotas = APIRouter()
PASTAS_MIDIA = {"clips", "previews"}
EXTENSOES_MIDIA = {".mp4", ".srt", ".png", ".json"}


@rotas.get("/api/projetos")
def listar(request: Request):
    return {"projetos": request.app.state.fila.listar()}


@rotas.get("/api/projetos/{pid}")
def detalhe(pid: str, request: Request):
    fila = request.app.state.fila
    dados = detalhe_projeto(request.app.state.raiz, pid)
    dados["project"] = fila.estado(pid)
    dados["busy"] = fila.ocupado(pid)
    return dados


@rotas.get("/media/{pid}/source")
def video_fonte(pid: str, request: Request):
    path = projects.project_path(request.app.state.raiz, pid).resolve()
    fonte = Path(projects.read_json(path / "transcript.json")["video"])
    if not fonte.is_file():
        raise FileNotFoundError(fonte)
    return FileResponse(fonte)


@rotas.get("/media/{pid}/{pasta}/{arquivo}")
def midia(pid: str, pasta: str, arquivo: str, request: Request):
    path = projects.project_path(request.app.state.raiz, pid).resolve()
    if pasta not in PASTAS_MIDIA:
        raise ValueError("Pasta de mídia desconhecida.")
    alvo = (path / pasta / arquivo).resolve()
    if alvo.parent != path / pasta or alvo.suffix not in EXTENSOES_MIDIA:
        raise ValueError("Caminho de mídia inválido.")
    if not alvo.is_file():
        raise FileNotFoundError(alvo)
    return FileResponse(alvo)
```

O `FileResponse` do Starlette (≥ 0.39, que vem com o FastAPI 0.165) já responde a `Range` com 206 e `Content-Range`, e a um intervalo fora do arquivo com 416. O teste confirma.

Em `picorte/api/app.py`, `_registrar_rotas`:

```python
def _registrar_rotas(app: FastAPI) -> None:
    from picorte.api.rotas_projetos import rotas as rotas_projetos
    from picorte.api.rotas_sistema import rotas as rotas_sistema

    app.include_router(rotas_sistema)
    app.include_router(rotas_projetos)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_api_projetos.py -v`
Expected: 6 passed.

- [ ] **Step 6: Conferir (sem commit)**

Run: `git status --short dashboard.py picorte tests/test_estudio_api_projetos.py`

---

### Task 11: Ações explícitas (POST) e `/api/config`, portadas do `dashboard.py`

**Files:**
- Modify: `picorte/api/rotas_projetos.py`, `picorte/api/rotas_sistema.py`
- Test: `tests/test_estudio_api_acoes.py`

**Interfaces:**
- Consumes: `FilaEstudio.enfileirar/ocupado`; `projects.create_project`, `validate_options`, `save_project`, `edit_transcript`, `validate_segments`, `atomic_json`; `StudioService`; `export_daily_bundle`; `dashboard._open_in_file_manager` (reuso).
- Produces (todas exigem `X-Picorte-Token`):
  - projetos:
    - `POST /api/projetos {source, options?}` → 201 com o estado;
    - `POST /api/lote {sources: [1..100], options?}` → 201 `{"projetos": [...]}`, já enfileirados (`prepare`);
    - `POST /api/projetos/{pid}/{acao}`, com `acao` ∈ `settings | transcript | candidates | run | mark-posted | export-bundle | open-folder`;
  - sistema:
    - `POST /api/marcas {name, preset}`;
    - `GET|POST /api/risco/cooldown`, `POST /api/risco/pausar-fonte`;
    - `GET /api/db/status`, `GET /api/db/fontes`;
    - `GET /api/config`: o mesmo conteúdo do antigo, com `"token"`, sem os `ai_modes` e `vision_presets`, que agora vêm da taxonomia.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_estudio_api_acoes.py`:

```python
from fastapi.testclient import TestClient

import projects
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.services.fila import FilaEstudio
from estudio_fakes import cache_falso

H = {"X-Picorte-Token": "t", "Origin": "http://testserver"}


def _cliente(tmp_path, executar=lambda *a: 0):
    raiz = tmp_path / "projects"
    fila = FilaEstudio(raiz, executar=executar)
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d", fila=fila,
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()))
    return TestClient(app), raiz, fila


def test_config_entrega_o_token(tmp_path):
    c, _, _ = _cliente(tmp_path)
    dados = c.get("/api/config").json()
    assert dados["token"] == "t" and "defaults" in dados and "caption_presets" in dados


def test_criar_projeto_e_enfileirar(tmp_path):
    chamadas = []
    c, raiz, fila = _cliente(tmp_path, executar=lambda p, a, pr, pk: chamadas.append(a) or 0)
    r = c.post("/api/projetos", json={"source": "https://www.youtube.com/watch?v=abc"}, headers=H)
    assert r.status_code == 201
    pid = r.json()["id"]
    r = c.post(f"/api/projetos/{pid}/run", json={"action": "prepare"}, headers=H)
    assert r.status_code == 200 and r.json() == {"ok": True}
    fila._futuros[pid].result(timeout=5)
    assert chamadas == ["prepare"]


def test_projeto_ocupado_responde_409(tmp_path):
    import threading
    solta = threading.Event()
    c, raiz, fila = _cliente(tmp_path, executar=lambda *a: solta.wait(5) and 0)
    pid = c.post("/api/projetos", json={"source": "https://youtu.be/x"}, headers=H).json()["id"]
    c.post(f"/api/projetos/{pid}/run", json={"action": "prepare"}, headers=H)
    r = c.post(f"/api/projetos/{pid}/settings", json={"min_len": 20}, headers=H)
    assert r.status_code == 409
    solta.set()
    fila._futuros[pid].result(timeout=5)


def test_lote_valida_tamanho(tmp_path):
    c, _, _ = _cliente(tmp_path)
    assert c.post("/api/lote", json={"sources": []}, headers=H).status_code == 400
    r = c.post("/api/lote", json={"sources": ["https://youtu.be/a", "https://youtu.be/b"]}, headers=H)
    assert r.status_code == 201 and len(r.json()["projetos"]) == 2


def test_settings_grava_opcao_validada(tmp_path):
    c, raiz, _ = _cliente(tmp_path)
    pid = c.post("/api/projetos", json={"source": "https://youtu.be/x"}, headers=H).json()["id"]
    assert c.post(f"/api/projetos/{pid}/settings", json={"min_len": 20}, headers=H).status_code == 200
    assert projects.read_project(raiz / pid)["options"]["min_len"] == 20
    assert c.post(f"/api/projetos/{pid}/settings", json={"inventada": 1}, headers=H).status_code == 400


def test_acao_desconhecida_e_404(tmp_path):
    c, _, _ = _cliente(tmp_path)
    pid = c.post("/api/projetos", json={"source": "https://youtu.be/x"}, headers=H).json()["id"]
    assert c.post(f"/api/projetos/{pid}/apagar-tudo", json={}, headers=H).status_code == 404


def test_mark_posted_valida_rede(tmp_path):
    c, _, _ = _cliente(tmp_path)
    pid = c.post("/api/projetos", json={"source": "https://youtu.be/x"}, headers=H).json()["id"]
    r = c.post(f"/api/projetos/{pid}/mark-posted", json={"clip_stem": "01", "platform": "orkut"},
               headers=H)
    assert r.status_code == 400
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estudio_api_acoes.py -v`
Expected: FAIL (`/api/config` 404, `POST /api/projetos` 405).

- [ ] **Step 3: Implementar as ações de projeto**

Em `picorte/api/rotas_projetos.py`, acrescente aos imports `import re` e `from fastapi import Body`, `from fastapi.responses import JSONResponse`, `from picorte.services.job_lock import ProjetoOcupado`. Depois acrescente:

```python
REDES_MANUAIS = {"youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"}
ACOES_LIVRES = {"mark-posted", "open-folder", "export-bundle"}  # não editam o projeto
NOME_MARCA = re.compile(r"[a-zA-Z0-9_-]{1,60}")


def _corpo(corpo) -> dict:
    if not isinstance(corpo, dict):
        raise ValueError("Esperado um objeto JSON.")
    return corpo


@rotas.post("/api/projetos", status_code=201)
def criar(request: Request, corpo: dict = Body(...)):
    corpo = _corpo(corpo)
    return projects.create_project(request.app.state.raiz, corpo["source"], corpo.get("options", {}))


@rotas.post("/api/lote", status_code=201)
def lote(request: Request, corpo: dict = Body(...)):
    corpo = _corpo(corpo)
    fontes = corpo.get("sources")
    if (not isinstance(fontes, list) or not 1 <= len(fontes) <= 100
            or any(not isinstance(f, str) or not f.strip() for f in fontes)):
        raise ValueError("Envie de 1 a 100 fontes.")
    opcoes = projects.validate_options(corpo.get("options", {}))
    criados = []
    for fonte in fontes:
        estado = projects.create_project(request.app.state.raiz, fonte, opcoes)
        request.app.state.fila.enfileirar(estado["id"], "prepare")
        criados.append(estado)
    return {"projetos": criados}


@rotas.post("/api/projetos/{pid}/{acao}")
def acao_projeto(pid: str, acao: str, request: Request, corpo: dict = Body(default_factory=dict)):
    corpo = _corpo(corpo)
    raiz = request.app.state.raiz
    fila = request.app.state.fila
    path = projects.project_path(raiz, pid)
    estado = projects.read_project(path)
    if acao not in ACOES_LIVRES and fila.ocupado(pid):
        raise ProjetoOcupado("Espere o job deste projeto terminar antes de editar.")
    if acao == "settings":
        ajustes = dict(corpo)
        if "brand_name" in ajustes:
            nome = ajustes.pop("brand_name")
            if nome and (not isinstance(nome, str) or not NOME_MARCA.fullmatch(nome)):
                raise ValueError("Marca inválida.")
            ajustes["brand"] = str(raiz / "brands" / f"{nome}.json") if nome else None
        estado["options"] = projects.validate_options({**estado["options"], **ajustes})
        projects.save_project(path, estado)
    elif acao == "transcript":
        projects.edit_transcript(path, corpo["words"])
    elif acao == "candidates":
        duracao = projects.read_json(path / "transcript.json")["duration"]
        projects.atomic_json(path / "segments.json",
                             projects.validate_segments(corpo["candidates"], duracao))
    elif acao == "run":
        fila.enfileirar(pid, corpo.get("action", "prepare"), corpo.get("preview", False),
                        corpo.get("pick"))
    elif acao == "mark-posted":
        stem = str(corpo.get("clip_stem") or "").strip()
        rede = str(corpo.get("platform") or "").strip()
        if not stem or rede not in REDES_MANUAIS:
            raise ValueError("Informe um clip_stem e uma rede válidos.")
        from picorte.services.studio_service import StudioService
        pub = StudioService().record_manual_publication(
            project_id=pid, clip_stem=stem, platform=rede,
            external_url=str(corpo.get("external_url") or "").strip(),
            source_url=str(estado.get("source") or ""))
        return {"ok": True, "publication": pub}
    elif acao == "export-bundle":
        from dashboard import _open_in_file_manager
        from picorte.engine.publish_kit import export_daily_bundle
        stems = corpo.get("clip_stems")
        pacote = export_daily_bundle(path, clip_stems=stems if isinstance(stems, list) else None,
                                     out_root=corpo.get("out_root"),
                                     per_day=int(corpo.get("per_day") or 3))
        if corpo.get("open_folder", True):
            _open_in_file_manager(Path(pacote["bundle_dir"]))
        return {"ok": True, **pacote}
    elif acao == "open-folder":
        from dashboard import _open_in_file_manager
        nome = str(corpo.get("file") or "").strip()
        tipo = str(corpo.get("kind") or "clips").strip()
        tipo = tipo if tipo in PASTAS_MIDIA else "clips"
        alvo = ((path / tipo / nome) if nome else (path / tipo)).resolve()
        if not alvo.is_relative_to(path.resolve()):
            raise ValueError("Caminho inválido.")
        if not alvo.exists():
            alvo = (path / tipo).resolve()
        _open_in_file_manager(alvo)
        return {"ok": True, "path": str(alvo)}
    else:
        return JSONResponse({"erro": "Não encontrado."}, status_code=404)
    return {"ok": True}
```

O `create_app` já cria a pasta `brands` da raiz? Não. Acrescente em `create_app`, logo depois de `raiz.mkdir(...)`: `(raiz / "brands").mkdir(exist_ok=True)`. É uma pasta, não o `project.json`, o mesmo que o `dashboard.py` já fazia.

- [ ] **Step 4: Implementar config, marcas, risco e banco**

Em `picorte/api/rotas_sistema.py`, acrescente aos imports `import re` e `from fastapi import Body`. Depois acrescente:

```python
@rotas.get("/api/config")
def config(request: Request):
    import branding
    import projects
    import render_clips
    from picorte import config as picorte_config
    from picorte.engine.publish_kit import load_streamer_registry

    raiz = request.app.state.raiz
    marcas_legenda = {}
    for arquivo in (raiz / "brands").glob("*.json"):
        try:
            marca = branding.validate_brand(projects.read_json(arquivo), arquivo.parent)
        except (ValueError, OSError, KeyError):
            continue
        marcas_legenda[arquivo.stem] = {k: marca[k] for k in branding.CAPTION_FIELDS
                                        if marca[k] is not None}
    donos = [{"value": "proprio", "label": "Meu gameplay"}] + [
        {"value": str(s.get("slug")), "label": str(s.get("display_name") or s.get("slug"))}
        for s in load_streamer_registry().get("streamers") or [] if s.get("slug")]
    return {
        "token": request.app.state.token,
        "source_owners": donos,
        "defaults": projects.DEFAULT_OPTIONS,
        "brands": sorted(p.stem for p in (raiz / "brands").glob("*.json")),
        "caption_brands": marcas_legenda,
        "caption_presets": render_clips.CAPTION_STYLES,
        "caption_defaults": branding.CAPTION_DEFAULTS,
        "caption_aspects": {n: {"font_size": t, "margin": m}
                            for n, (_, _, t, m) in render_clips.ASPECTS.items()},
        "caption_power_words": sorted(render_clips.POWER_WORDS),
        "caption_emoji_rules": [{"words": list(s), "emoji": e} for s, e in render_clips.EMOJI_RULES],
        "detected_gpu": picorte_config.detect_gpu_profile(),
        "detected_vision_preset": picorte_config.resolve_vision_preset("auto"),
    }


@rotas.post("/api/marcas")
def salvar_marca(request: Request, corpo: dict = Body(...)):
    import branding
    import projects
    nome = corpo["name"]
    if not isinstance(nome, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", nome):
        raise ValueError("O nome da marca usa letras, números, - ou _.")
    destino = request.app.state.raiz / "brands" / f"{nome}.json"
    projects.atomic_json(destino, branding.validate_brand(corpo["preset"]))
    return {"name": nome, "path": str(destino)}


@rotas.get("/api/db/status")
def db_status():
    from picorte.services.studio_service import StudioService
    return StudioService().status_fila()


@rotas.get("/api/db/fontes")
def db_fontes():
    from picorte.services.studio_service import StudioService
    return {"sources": StudioService().list_sources()}


@rotas.get("/api/risco/cooldown")
def cooldown():
    from picorte.services.studio_service import StudioService
    return {"cooldowns": StudioService().risk_cooldown_status()}


@rotas.post("/api/risco/cooldown")
def mudar_cooldown(corpo: dict = Body(...)):
    from picorte.services.studio_service import StudioService
    svc = StudioService()
    rede = str(corpo.get("platform") or "")
    if corpo.get("clear"):
        return {"ok": True, "cooldown": svc.risk_clear_cooldown(rede)}
    return {"ok": True, "cooldown": svc.risk_set_cooldown(
        rede, hours=corpo.get("hours"), reason=str(corpo.get("reason") or "Resfriamento anti-spam"))}


@rotas.post("/api/risco/pausar-fonte")
def pausar_fonte(corpo: dict = Body(...)):
    from picorte.services.studio_service import StudioService
    res = StudioService().risk_pause_source(
        str(corpo.get("source_id") or ""),
        claim_type=str(corpo.get("claim_type") or "copyright_claim"),
        details=str(corpo.get("details") or ""), reason=str(corpo.get("reason") or ""))
    return {"ok": True, **res}
```

Nota C1: "só o cooldown manual pode ser limpo". A trava de liberar/despausar com base + evidência + motivo fica nas histórias 6.4 e 6.7 (Fontes/Escudo), onde a tela correspondente nasce. Aqui o comportamento antigo é portado sem mudança.

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_estudio_api_acoes.py -v`
Expected: 7 passed.

- [ ] **Step 6: Conferir (sem commit)**

Run: `git status --short picorte/api tests/test_estudio_api_acoes.py`

---

### Task 12: Teste de contrato A5, ponto de entrada `estudio.py` e verificação final

**Files:**
- Create: `estudio.py`, `tests/test_estudio_contrato_a5.py`
- Test: `tests/test_estudio_contrato_a5.py`

**Interfaces:**
- Consumes: tudo das tarefas anteriores.
- Produces: `python estudio.py [--pasta-projetos projects] [--porta 8770] [--sem-navegador]`.

- [ ] **Step 1: Escrever o teste de contrato que falha**

`tests/test_estudio_contrato_a5.py`:

```python
from fastapi.testclient import TestClient

from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.capacidades.sondas import ResultadoSonda
from estudio_fakes import _fixa, cache_falso

CAMPOS = {"id", "area", "titulo", "status", "tipo_motivo", "motivo", "falta", "fonte_dado",
          "origem", "escopo", "depende_de", "verificado_em", "ligou_em", "dados"}


def _tem_numero(valor) -> bool:
    if isinstance(valor, bool):
        return False
    if isinstance(valor, (int, float)):
        return True
    if isinstance(valor, dict):
        return any(_tem_numero(v) for v in valor.values())
    if isinstance(valor, list):
        return any(_tem_numero(v) for v in valor)
    return False


def _capacidades(tmp_path, cache):
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     capacidades=ServicoCapacidades(raiz, cache=cache))
    return TestClient(app).get("/api/capacidades").json()["capacidades"]


def test_toda_capacidade_segue_o_contrato(tmp_path):
    for cap in _capacidades(tmp_path, cache_falso()):
        assert set(cap) == CAMPOS, cap["id"]
        assert cap["status"] in {"ligado", "parcial", "travado"}
        assert cap["escopo"] in {"global", "projeto", "corte"}
        assert cap["verificado_em"], cap["id"]
        if cap["status"] != "ligado":
            assert cap["tipo_motivo"] in {"codigo", "config", "dado", "temporario", "escolha"}
            assert cap["motivo"], cap["id"]


def test_capacidade_travada_nunca_traz_numero_mesmo_com_sonda_cheia(tmp_path):
    cache = cache_falso(
        ollama=lambda: ResultadoSonda(False, "fora", {"host": "h", "modelos": [], "latencia_ms": 3}),
        claude=_fixa(False, caminho=None, tentativas=2),
        **{"yt-dlp": _fixa(False, tentativas=5)})
    for cap in _capacidades(tmp_path, cache):
        if cap["status"] == "travado":
            assert cap["dados"] is None, cap["id"]
            assert not _tem_numero(cap["dados"]), cap["id"]


def test_depende_de_aponta_para_ids_existentes(tmp_path):
    caps = _capacidades(tmp_path, cache_falso())
    ids = {c["id"] for c in caps}
    for cap in caps:
        assert set(cap["depende_de"]) <= ids, cap["id"]
```

Run: `python -m pytest tests/test_estudio_contrato_a5.py -v`
Expected: 3 passed. As tarefas 4 a 7 já implementam o contrato: este teste é o portão. Se falhar, a correção vai no módulo indicado pelo `id` que falhou, nunca no teste.

- [ ] **Step 2: Ponto de entrada**

`estudio.py`:

```python
"""Estúdio do Criador (Picorte): painel local em http://127.0.0.1:8770."""
import argparse
import webbrowser

import uvicorn

from picorte import config as picorte_config  # noqa: F401 - põe .venv/bin ou .venv/Scripts no PATH
from picorte.api import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Abre o Estúdio do Criador no seu computador.")
    parser.add_argument("--pasta-projetos", default="projects")
    parser.add_argument("--porta", type=int, default=8770)
    parser.add_argument("--sem-navegador", action="store_true")
    args = parser.parse_args()
    app = create_app(args.pasta_projetos, porta=args.porta)
    url = f"http://127.0.0.1:{args.porta}"
    print(f"Estúdio do Criador: {url}\nProjetos: {app.state.raiz}\nCtrl+C para parar.", flush=True)
    if not args.sem_navegador:
        webbrowser.open(url)
    uvicorn.run(app, host="127.0.0.1", port=args.porta, log_level="warning")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Fumaça real, numa cópia isolada (nunca sobre `projects/`)**

A outra sessão processa `projects/`. Abrir o Estúdio ali não escreve `project.json`, mas a fumaça usa uma pasta vazia do scratchpad mesmo assim:

Run (bash, em segundo plano): `python estudio.py --pasta-projetos "$SCRATCH/estudio-fumaca" --porta 8771 --sem-navegador`, onde `$SCRATCH` é o diretório de scratchpad da sessão.

Depois:
- Run: `curl -s -H "Host: 127.0.0.1:8771" http://127.0.0.1:8771/api/capacidades | python -c "import json,sys; d=json.load(sys.stdin); print(d['resumo']); print([ (c['id'], c['status']) for c in d['capacidades'] if c['id'].startswith('SIS')])"`. Expected: o resumo com as 82 capacidades somadas, e `SIS-6`/`SIS-8`/`SIS-11` refletindo a máquina real (Ollama no ar ou não, etc.).
- Run: `curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8771/api/projetos`. Expected: `403`.
- Run: `curl -s http://127.0.0.1:8771/ | head -3`. Expected: a página "A casca do Estúdio ainda não foi construída" (até o plano 6.3-B).

Pare o servidor ao terminar.

- [ ] **Step 4: Suíte completa**

Run: `python -m pytest tests -q`
Expected: tudo passa, exceto falhas já existentes antes desta história. Para saber quais existiam, rode a suíte **antes** da Task 1 e guarde a saída em `$SCRATCH/pytest-antes.txt`. Qualquer falha nova é desta história e precisa ser corrigida.

- [ ] **Step 5: Conferir (sem commit) e relatar ao dono**

Run: `git status --short`
Expected: só os arquivos do "Mapa de arquivos" acima, mais `.job.lock` **não** aparecendo, porque o lock fica dentro de `projects/<id>/`, que já é ignorado. Confirme que nada em `projects/` nem em `benchmarks/` mudou.

Relate:
- os testes que passaram;
- o resumo real de `/api/capacidades` na máquina;
- os arquivos alterados.

Não commite: o dono decide.

---

## Self-review (feito ao escrever)

- **Cobertura da história 6.3:**
  - AC1: Tasks 1, 3, 10 e 11 (Range/206, token, CSP, Host/Origin, fila serial, SPA, nunca escrever ao ler);
  - AC2: Tasks 2 e 3;
  - AC3: Tasks 4 a 7 (campos, sondas com cache, MCP);
  - AC4: Task 8;
  - AC5: Tasks 3 e 9 (progresso e capacidades);
  - AC6: Tasks 4 e 12;
  - AC7: casca React, no plano 6.3-B.
- **Fora daqui, de propósito:**
  - B1–B6 e B10, na história 6.4;
  - C1 na tela, nas 6.4 e 6.7;
  - "sinal não medido sai `null`" nos dados de corte (REV-2/B2), na 6.4. Aqui o contrato A5 cobre as capacidades.
- **Tipos coerentes entre tarefas:**
  - `FilaEstudio.ocupado/estado/listar/enfileirar`;
  - `ServicoCapacidades.atual`;
  - `listar_capacidades(raiz, cache)`;
  - `Barramento.assinar/cancelar/publicar`;
  - `create_app(..., fila, barramento, capacidades)`.
