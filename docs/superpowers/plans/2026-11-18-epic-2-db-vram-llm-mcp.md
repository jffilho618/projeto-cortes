# Épico 2 (Banco Canônico, Fila Serial de VRAM, Seletor de IA 4 Modos na UI e Controle MCP/Skill) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar as 10 tabelas canônicas e repositórios transacionais (`AD-2`), o orquestrador serial de VRAM multiplataforma com Modo Madrugada (`AD-3`, `AD-11`, `R-06`), o Roteador de IA de 4 Modos com Seletor na UI (`Ollama` / `Claude` / `Gemini` / `Dupla: Filtro + Acompanhamento` — `AD-4`, `R-07`) e o Servidor MCP + Skill `picorte-operador` (`AD-10`).

**Architecture:** Camada `picorte/db/` provê o schema SQL das 10 tabelas (compatível com PostgreSQL 16 via `DATABASE_URL` + `docker-compose.yml` e fallback local imediato em `picorte.db`), `picorte/engine/vram_runner.py` serializa estágios de GPU via `filelock` (Windows + Linux), `picorte/ai/llm_router.py` roteia chamadas entre Ollama local, Claude CLI/API, Gemini CLI/API e pipeline Dupla (`Filtro -> Acompanhamento`), e `picorte/services/` expõe a mesma lógica para a UI (`dashboard.py`) e para o servidor MCP (`picorte/mcp/server.py`).

**Tech Stack:** Python 3.12, PostgreSQL 16 / SQLite3, `filelock`, `pytest`, CLI `claude` / `agy`, Ollama HTTP API.

## Global Constraints

- **AD-2:** 10 tabelas canônicas (`sources`, `publisher_policies`, `campaigns`, `videos`, `clips`, `publications`, `metrics_snapshots`, `claims_events`, `bandit_state`, `dataset_samples`), zero `workspace_id`.
- **AD-3 & AD-11 (R-06):** `vram_runner.py` deve usar `filelock.FileLock` (nunca `fcntl`, para funcionar no Windows 11 e no Ubuntu), garantir limpeza explícita de memória entre estágios e suportar verificação da janela do Modo Madrugada.
- **AD-4 (R-07):** `llm_router.py` deve suportar os 4 modos (`ollama`, `claude`, `gemini`, `dupla`) selecionáveis na UI (`assets/studio/index.html` + `app.js` + `dashboard.py`) e gravar `llm_mode_used` no corte.
- **AD-10:** `picorte/services/studio_service.py` concentra as operações chamadas tanto pelo `dashboard.py` quanto pelo `picorte/mcp/server.py`.

---

### Task 1: Schema Canônico das 10 Tabelas e Repositórios (`Story 2.1`)

**Files:**
- Create: `docker-compose.yml`
- Create: `picorte/db/__init__.py`
- Create: `picorte/db/schema.sql`
- Create: `picorte/db/connection.py`
- Create: `picorte/db/repositories.py`
- Test: `tests/test_db_repositories.py`

- [ ] **Step 1: Write the failing test `tests/test_db_repositories.py`**
- [ ] **Step 2: Run test to verify it fails (RED)**
- [ ] **Step 3: Implement `docker-compose.yml`, `schema.sql`, `connection.py`, and `repositories.py`**
- [ ] **Step 4: Run test to verify it passes (GREEN)**

---

### Task 2: Orquestrador Serial de VRAM e Modo Madrugada (`Story 2.2` / `R-06`)

**Files:**
- Create: `picorte/engine/vram_runner.py`
- Test: `tests/test_vram_runner_serialization.py`

- [ ] **Step 1: Write the failing test `tests/test_vram_runner_serialization.py` (`R-06`)**
- [ ] **Step 2: Run test to verify it fails (RED)**
- [ ] **Step 3: Implement `picorte/engine/vram_runner.py` using `filelock` (Windows + Linux)**
- [ ] **Step 4: Run test to verify it passes (GREEN)**

---

### Task 3: Roteador de IA de 4 Modos (`llm_router.py`) e Seletor na UI (`Story 2.3` / `R-07`)

**Files:**
- Create: `picorte/ai/__init__.py`
- Create: `picorte/ai/llm_router.py`
- Modify: `score_clips.py` (integrar `llm_router` quando modo `ollama`/`claude`/`gemini`/`dupla` for selecionado)
- Modify: `projects.py`, `dashboard.py`, `assets/studio/index.html`, `assets/studio/app.js` (adicionar Seletor de Motor de IA: `Ollama`, `Claude`, `Gemini` ou `Dupla: Filtro + Acompanhamento`)
- Test: `tests/test_llm_router_four_modes.py`

- [ ] **Step 1: Write the failing test `tests/test_llm_router_four_modes.py` (`R-07`)**
- [ ] **Step 2: Run test to verify it fails (RED)**
- [ ] **Step 3: Implement `picorte/ai/llm_router.py` and integrate into `score_clips.py`, `projects.py`, `dashboard.py` and Studio UI**
- [ ] **Step 4: Run test to verify it passes (GREEN)**

---

### Task 4: Serviço Unificado (`AD-10`), Servidor MCP (`picorte_mcp`) e Skill `picorte-operador` (`Story 2.4`)

**Files:**
- Create: `picorte/services/__init__.py`
- Create: `picorte/services/studio_service.py`
- Create: `picorte/mcp/__init__.py`
- Create: `picorte/mcp/server.py`
- Create: `skills/picorte-operador/SKILL.md` (+ symlink `.claude/skills/picorte-operador`)
- Test: `tests/test_mcp_and_service.py`

- [ ] **Step 1: Write the failing test `tests/test_mcp_and_service.py`**
- [ ] **Step 2: Run test to verify it fails (RED)**
- [ ] **Step 3: Implement `studio_service.py`, `picorte/mcp/server.py`, and `skills/picorte-operador/SKILL.md`**
- [ ] **Step 4: Run full `pytest` suite to verify all tests pass (GREEN)**
