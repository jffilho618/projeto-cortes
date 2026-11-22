# 6.4 — Verdade no Banco Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o `picorte.db` guardar só o que foi medido e ligar cada vídeo à sua fonte, para que o painel e o MCP leiam números reais (história 6.4, B1–B6).

**Architecture:**
- **Migração idempotente no `Database._migrate`:** as notas por sinal e o YPP passam a aceitar `NULL` ("não medido" ou "sem veredito"), e `videos` e `clips` ganham `archived_at`.
- **Reescrita de `StudioService.sync_studio_project`:**
  - grava o `source_id` do `source_gate`;
  - grava os sinais medidos (função pura em `picorte/services/sinais.py`);
  - grava o veredito P1 lido do `.meta.json`.
- **Novo `picorte/services/reconciliacao.py`:**
  - re-sincroniza as pastas de projeto existentes (só leitura) e arquiva o que não existe mais no disco;
  - `preparar_banco` junta migração, políticas e reconciliação, e roda no boot do `estudio.py` e do MCP.
- **Fila única (B5):** o `estudio.py` publica porta e token num arquivo local; o MCP chama a mesma rota `/api/lote` do painel.

**Tech Stack:** Python 3.12, SQLite (PostgreSQL opcional pelo `DATABASE_URL`), FastAPI 0.165, httpx 0.28, pytest.

**Spec:**
- `_bmad-output/planning-artifacts/epics.md`, Story 6.4 (AC 1–6);
- diagnóstico B1–B6 em `_bmad-output/brainstorming/brainstorm-mapa-painel-estudio-do-criador-2026-11-21/brainstorm-intent.md` (linhas 36–41 e 262);
- `CLAUDE.md`, regra 4 (P1 obrigatório e rastreio dos publicados).

## Global Constraints

- **Não editar:**
  - `projects/`, `benchmarks/`, `score_clips.py`, `picorte/engine/score_clips.py`, `picorte/ai/llm_router.py`, `benchmark.py`, `picorte/engine/benchmark.py`;
  - **e os arquivos que a worktree `motor/3-6-2` está mudando:** `ingest.py`, `picorte/engine/ingest.py`, `picorte/engine/chat_seismic.py`, `tests/test_chat_seismic.py`, `tests/test_e36_*`, `tests/test_e3_practical_e2e.py`.
- **Ler `projects/` só para leitura.** A reconciliação nunca escreve em `project.json` nem em nada de `projects/`.
- **Não commitar** (pedido do dono).
- **Testes nunca tocam o `picorte.db` real:** usam `Database(f"sqlite:///{tmp_path/'t.db'}")`, e o `conftest.py` já aponta o `DATABASE_URL` para um arquivo temporário.
- **Não medido = `NULL`, nunca 0.0 (A5).** Sem veredito = `risk_status = 'pending'` e `ypp_transform_score = NULL`.
- **Rastreio P1:** nada é apagado. Vídeo ou corte de projeto apagado vira arquivado (`archived_at`), e a publicação continua ligada.
- **Windows e Linux:** `pathlib`, sem caminhos fixos e sem shell.
- **`projects.py` e `picorte/engine/projects.py` são idênticos** e as duas cópias mudam juntas (conferir com `diff`).

## Mapa de arquivos

| Arquivo | Mudança |
|---|---|
| `picorte/db/schema.sql` | Notas por sinal e YPP sem `NOT NULL DEFAULT 0`; `archived_at` em `videos` e `clips`. |
| `picorte/db/connection.py` | `_ADDED_COLUMNS` com `archived_at`; `_tornar_anulaveis()`, que reconstrói `clips` no SQLite (`ALTER ... DROP NOT NULL` no Postgres) e anula os 0.0 falsos. |
| `picorte/db/repositories.py` | `create_clip` com sinais `None` por padrão; `list_clips(..., incluir_arquivados=False)`. |
| `picorte/services/sinais.py` (novo) | `sinais_medidos(seg)` e `veredito_do_corte(mp4)`. |
| `picorte/services/studio_service.py` | `sync_studio_project` (B1, B2, B3, mp4 por prefixo, thumbnail); `status_fila` sem arquivados; `enqueue_video` pela fila do Estúdio (B5); `record_manual_publication` liga ao corte do sync. |
| `picorte/risk_shield/pipeline.py` | `_compact` guarda `phash_signature`; `attach_risk_verdict(..., clip_id=None)` repassa para a deduplicação não comparar o corte com ele mesmo. |
| `projects.py` + `picorte/engine/projects.py` | Passam `clip_id` ao `attach_risk_verdict`; a sincronização com o banco usa `sincronizar_pasta` e, em falha, registra em `engine_health` (no lugar do `except: pass`). |
| `picorte/services/reconciliacao.py` (novo) | `sincronizar_pasta`, `reconciliar` e `preparar_banco`. |
| `picorte/services/estudio_conexao.py` (novo) | `gravar_conexao`, `ler_conexao`, `apagar_conexao`, `enfileirar_no_estudio` e `EstudioDesligado`. |
| `estudio.py` | `preparar_banco` no boot; grava o arquivo de conexão e o apaga ao sair. |
| `picorte/mcp/server.py` | Esquema e chamada do `picorte_enfileirar_video` (B5); políticas sincronizadas no boot do `main()`. |
| `picorte/capacidades/catalogo.py` | SIS-5, SIS-12, REV-2, FON-4 e FON-5 ligados; ESC-1 e ESC-5 com o "falta" novo. |
| `skills/picorte-operador/SKILL.md` | Descrição nova do `picorte_enfileirar_video`. |
| `.gitignore` | `+ .picorte/`. |
| Testes novos | `tests/test_banco_migracao.py`, `tests/test_banco_sinais.py`, `tests/test_banco_sync.py`, `tests/test_banco_reconciliacao.py`, `tests/test_banco_fila_unica.py`. |
| Testes ajustados | `tests/test_mcp_and_service.py` (B5 muda o comportamento de propósito), `tests/test_estudio_capacidades.py`. |

---

### Task 1: Migração — sinais e YPP anuláveis, `archived_at`

**Files:**
- Modify: `picorte/db/schema.sql`, `picorte/db/connection.py`, `picorte/db/repositories.py:220-283`
- Test: `tests/test_banco_migracao.py`

**Interfaces:**
- Produces: `Database.init_schema()` deixa `clips.score_chat|score_audio|score_visual|score_text|ypp_transform_score` anuláveis e `videos.archived_at` e `clips.archived_at` (TEXT, NULL = ativo); `ANULAVEIS` em `connection.py`; `ClipsRepository.list_clips(video_id=None, incluir_arquivados=False)`.

- [ ] **Step 1: Teste (falhando)**

`tests/test_banco_migracao.py`:

```python
import sqlite3

from picorte.db.connection import Database

DDL_ANTIGO = """
CREATE TABLE sources (id TEXT PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL, channel_handle TEXT NOT NULL,
  permission_status TEXT NOT NULL DEFAULT 'desconhecida', permission_evidence_url TEXT DEFAULT '',
  credit_template TEXT DEFAULT 'Créditos: @{handle}', default_game_slug TEXT DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE videos (id TEXT PRIMARY KEY, source_id TEXT REFERENCES sources(id), origin_type TEXT NOT NULL DEFAULT 'vod',
  source_url TEXT NOT NULL, game_slug TEXT NOT NULL DEFAULT '', duration_seconds REAL NOT NULL DEFAULT 0.0,
  workdir_path TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE clips (id TEXT PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id), parent_long_clip_id TEXT REFERENCES clips(id),
  format_type TEXT NOT NULL DEFAULT 'short_9_16', ab_variant INTEGER NOT NULL DEFAULT 1, start_sec REAL NOT NULL, end_sec REAL NOT NULL,
  score_chat REAL NOT NULL DEFAULT 0.0, score_audio REAL NOT NULL DEFAULT 0.0, score_visual REAL NOT NULL DEFAULT 0.0,
  score_text REAL NOT NULL DEFAULT 0.0, score_overall REAL NOT NULL DEFAULT 0.0, ypp_transform_score INTEGER NOT NULL DEFAULT 0,
  phash_signature TEXT NOT NULL DEFAULT '', llm_mode_used TEXT NOT NULL DEFAULT 'heuristic', risk_status TEXT NOT NULL DEFAULT 'pending',
  mp4_path TEXT NOT NULL DEFAULT '', thumbnail_path TEXT NOT NULL DEFAULT '', proposed_title TEXT NOT NULL DEFAULT '',
  context_banner_2s TEXT NOT NULL DEFAULT '', pinned_comment_debate TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE publications (id TEXT PRIMARY KEY, clip_id TEXT NOT NULL REFERENCES clips(id), social_account_id TEXT,
  platform TEXT NOT NULL, publish_mode TEXT NOT NULL DEFAULT 'assisted_manual', status TEXT NOT NULL DEFAULT 'fila',
  external_post_id TEXT NOT NULL DEFAULT '', external_url TEXT NOT NULL DEFAULT '', related_video_external_id TEXT NOT NULL DEFAULT '',
  scheduled_for TEXT, published_at TEXT, created_at TEXT NOT NULL);
INSERT INTO videos VALUES ('v1', NULL, 'vod', 'u', '', 0, '', 'complete', 't', 't');
INSERT INTO clips (id, video_id, start_sec, end_sec, score_text, score_overall, created_at) VALUES ('c1', 'v1', 0, 10, 9.5, 9.5, 't');
INSERT INTO publications (id, clip_id, platform, status, external_url, created_at) VALUES ('p1', 'c1', 'tiktok', 'publicado', 'https://x', 't');
"""


def _banco_antigo(tmp_path):
    arq = tmp_path / "antigo.db"
    con = sqlite3.connect(arq)
    con.executescript(DDL_ANTIGO)
    con.close()
    return Database(f"sqlite:///{arq}")


def _info(db, tabela):
    with db.connect() as c:
        return {r["name"]: r for r in c.execute(f"PRAGMA table_info({tabela})").fetchall()}


def test_banco_novo_ja_nasce_com_sinais_anulaveis(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'novo.db'}")
    db.init_schema()
    info = _info(db, "clips")
    for col in ("score_chat", "score_audio", "score_visual", "score_text", "ypp_transform_score"):
        assert info[col]["notnull"] == 0, col
    assert "archived_at" in info and "archived_at" in _info(db, "videos")


def test_banco_antigo_migra_anula_zeros_falsos_e_preserva_publicacao(tmp_path):
    db = _banco_antigo(tmp_path)
    db.init_schema()
    corte = db.fetch_one("SELECT * FROM clips WHERE id = 'c1'")
    assert corte["score_chat"] is None and corte["score_audio"] is None and corte["score_visual"] is None
    assert corte["score_text"] is None  # era a nota geral copiada, não um sinal medido
    assert corte["ypp_transform_score"] is None  # sem veredito
    assert corte["score_overall"] == 9.5
    pub = db.fetch_one("SELECT * FROM publications WHERE id = 'p1'")
    assert pub["clip_id"] == "c1" and pub["external_url"] == "https://x"
    with db.connect() as c:
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migracao_e_idempotente(tmp_path):
    db = _banco_antigo(tmp_path)
    db.init_schema()
    db.execute("UPDATE clips SET score_audio = 7.5 WHERE id = 'c1'")
    db.init_schema()
    assert db.fetch_one("SELECT score_audio FROM clips WHERE id = 'c1'")["score_audio"] == 7.5


def test_create_clip_sem_sinal_grava_null(tmp_path):
    from picorte.db.repositories import PicorteRepositories
    db = Database(f"sqlite:///{tmp_path / 'r.db'}")
    db.init_schema()
    repos = PicorteRepositories(db)
    vid = repos.videos.create_video(source_url="u")
    clip = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=10.0)
    assert clip["score_chat"] is None and clip["score_text"] is None


def test_list_clips_esconde_arquivados(tmp_path):
    from picorte.db.repositories import PicorteRepositories
    db = Database(f"sqlite:///{tmp_path / 'r.db'}")
    db.init_schema()
    repos = PicorteRepositories(db)
    vid = repos.videos.create_video(source_url="u")
    a = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=10.0)
    b = repos.clips.create_clip(video_id=vid["id"], start_sec=10.0, end_sec=20.0)
    db.execute("UPDATE clips SET archived_at = 't' WHERE id = ?", (b["id"],))
    assert [c["id"] for c in repos.clips.list_clips()] == [a["id"]]
    assert {c["id"] for c in repos.clips.list_clips(incluir_arquivados=True)} == {a["id"], b["id"]}
```

- [ ] **Step 2: Ver falhar.** Run: `python -m pytest tests/test_banco_migracao.py -q`. Expected: FAIL (`notnull == 1` e `archived_at` ausente).

- [ ] **Step 3: Implementar**

Em `picorte/db/schema.sql`:
- tabela `clips`: troque as cinco linhas de nota pelas versões anuláveis e acrescente `archived_at` antes de `created_at`:

  ```sql
      score_chat REAL,
      score_audio REAL,
      score_visual REAL,
      score_text REAL,
      score_overall REAL NOT NULL DEFAULT 0.0,
      ypp_transform_score INTEGER,
  ```

  e `archived_at TEXT,` logo antes de `created_at TEXT NOT NULL`;
- tabela `videos`: `archived_at TEXT,` antes de `created_at`.

Em `picorte/db/connection.py`, acrescente `import re`, a constante e a migração:

```python
ANULAVEIS = ("score_chat", "score_audio", "score_visual", "score_text", "ypp_transform_score")
```

```python
    _ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
        ("sources", "permission_basis", "TEXT NOT NULL DEFAULT 'explicita'"),
        ("videos", "archived_at", "TEXT"),
        ("clips", "archived_at", "TEXT"),
    )

    def _migrate(self) -> None:
        for table, column, ddl in self._ADDED_COLUMNS:
            if column in self.list_columns(table):
                continue
            self.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        self._tornar_anulaveis()

    def _tornar_anulaveis(self) -> None:
        """B2/B3 (história 6.4): nota não medida e YPP sem veredito viram NULL; os 0.0 antigos eram falsos."""
        anular = ", ".join(f"{c} = NULL" for c in ANULAVEIS[:4])
        if self.is_postgres:
            presos = [r["name"] for r in self.fetch_all(
                "SELECT column_name AS name FROM information_schema.columns "
                "WHERE table_name = 'clips' AND is_nullable = 'NO'") if r["name"] in ANULAVEIS]
            if presos:
                with self.connect() as conn:
                    for col in presos:
                        conn.execute(f"ALTER TABLE clips ALTER COLUMN {col} DROP NOT NULL")
                    conn.execute(f"UPDATE clips SET {anular}")
                    conn.execute("UPDATE clips SET ypp_transform_score = NULL WHERE ypp_transform_score = 0")
            return
        with self.connect() as conn:
            info = conn.execute("PRAGMA table_info(clips)").fetchall()
            ddl = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'clips'").fetchone()["sql"]
        if not any(r["name"] in ANULAVEIS and r["notnull"] for r in info):
            return
        novo = re.sub(r"\b(score_chat|score_audio|score_visual|score_text)\s+REAL\s+NOT\s+NULL\s+DEFAULT\s+0(\.0)?",
                      r"\1 REAL", ddl, flags=re.I)
        novo = re.sub(r"\bypp_transform_score\s+INTEGER\s+NOT\s+NULL\s+DEFAULT\s+0", "ypp_transform_score INTEGER",
                      novo, flags=re.I)
        novo = re.sub(r"^CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?\"?clips\"?", "CREATE TABLE clips_novo", novo, flags=re.I)
        conn = sqlite3.connect(str(self.sqlite_path), isolation_level=None)
        try:  # receita oficial do SQLite para mudar restrição de coluna: nova tabela, copiar, trocar
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("BEGIN")
            conn.execute(novo)
            conn.execute("INSERT INTO clips_novo SELECT * FROM clips")
            conn.execute(f"UPDATE clips_novo SET {anular}")
            conn.execute("UPDATE clips_novo SET ypp_transform_score = NULL WHERE ypp_transform_score = 0")
            conn.execute("DROP TABLE clips")
            conn.execute("ALTER TABLE clips_novo RENAME TO clips")
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Migração do banco quebraria referências; nada foi alterado.")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.close()
        with self.connect() as c:  # recria índices que viviam na tabela antiga
            c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
```

Em `picorte/db/repositories.py`:
- `create_clip`: os parâmetros `score_chat`, `score_audio`, `score_visual` e `score_text` passam a `float | None = None`;
- na tupla do INSERT, use `None if score_chat is None else float(score_chat)` (e o mesmo para os outros três);
- `list_clips`:

  ```python
      def list_clips(self, video_id: str | None = None, incluir_arquivados: bool = False) -> list[dict[str, Any]]:
          filtro = "" if incluir_arquivados else " AND archived_at IS NULL"
          if video_id:
              return self.db.fetch_all(
                  f"SELECT * FROM clips WHERE video_id = ?{filtro} ORDER BY score_overall DESC", (video_id,))
          return self.db.fetch_all(f"SELECT * FROM clips WHERE 1 = 1{filtro} ORDER BY created_at DESC")
  ```

- [ ] **Step 4: Rodar.** Run: `python -m pytest tests/test_banco_migracao.py tests/test_db_repositories.py tests/test_epic4_*.py -q`. Expected: tudo passa. Se algum teste antigo esperar `0.0` num sinal que não foi passado, ajuste o teste para `None` (é a regra A5), anotando o arquivo nos desvios.

- [ ] **Step 5: Sem commit.**

---

### Task 2: Sinais medidos e veredito por corte (funções puras)

**Files:**
- Create: `picorte/services/sinais.py`
- Modify: `picorte/risk_shield/pipeline.py:103-120` (`_compact` guarda `phash_signature`)
- Test: `tests/test_banco_sinais.py`

**Interfaces:**
- Produces:
  - `sinais_medidos(seg: dict) -> dict[str, float | None]`, com as chaves `score_chat`, `score_audio`, `score_visual`, `score_text`;
  - `veredito_do_corte(mp4: str | Path) -> dict | None`: `None` sem `.meta.json` ou sem `risk_verdict`; senão `{"risk_status", "ypp_transform_score" (int | None), "phash_signature" (str)}`;
  - `miniatura_do_corte(mp4) -> str` (`""` se não houver).

- [ ] **Step 1: Teste (falhando)**

`tests/test_banco_sinais.py`:

```python
import json

from picorte.services.sinais import miniatura_do_corte, sinais_medidos, veredito_do_corte


def test_sinais_medidos_de_um_candidato_real():
    seg = {"evidence": {"audio": 7.84, "visual": None, "chat": 2.58, "chat_measured": True,
                        "visual_games": 8.26, "hud": 0.0}, "score_parts": {"text_score": 6.1}}
    assert sinais_medidos(seg) == {"score_chat": 2.58, "score_audio": 7.84, "score_visual": None, "score_text": 6.1}


def test_chat_sem_marca_de_medido_nao_conta():
    seg = {"evidence": {"chat": 3.0, "audio": 5.0}}
    assert sinais_medidos(seg)["score_chat"] is None


def test_visual_games_so_vale_com_visao_medida():
    assert sinais_medidos({"evidence": {"visual": None, "visual_games": 8.0}})["score_visual"] is None
    assert sinais_medidos({"evidence": {"visual": None, "visual_games": 8.0, "vision_measured": True}})["score_visual"] == 8.0


def test_corte_do_scout_sem_evidencia_fica_todo_nao_medido():
    seg = {"evidence": {}, "score_parts": {"llm_scout": 1}, "overall": 10.0}
    assert set(sinais_medidos(seg).values()) == {None}


def test_tipos_estranhos_viram_nao_medido():
    seg = {"evidence": {"audio": "7", "chat": True, "chat_measured": True}, "score_parts": None}
    assert set(sinais_medidos(seg).values()) == {None}


def test_veredito_lido_do_meta(tmp_path):
    mp4 = tmp_path / "001-ab-x.mp4"
    (tmp_path / "001-ab-x.meta.json").write_text(json.dumps({
        "risk_status": "human_review", "thumbnail_1280x720": str(tmp_path / "t.png"),
        "risk_verdict": {"overall_status": "human_review", "ypp_score": 82, "phash_signature": "ab12"}}), encoding="utf-8")
    assert veredito_do_corte(mp4) == {"risk_status": "human_review", "ypp_transform_score": 82, "phash_signature": "ab12"}
    assert miniatura_do_corte(mp4) == str(tmp_path / "t.png")


def test_sem_meta_ou_sem_veredito_devolve_none(tmp_path):
    assert veredito_do_corte(tmp_path / "nao-existe.mp4") is None
    (tmp_path / "002-x.meta.json").write_text(json.dumps({"title": "x"}), encoding="utf-8")
    assert veredito_do_corte(tmp_path / "002-x.mp4") is None
    assert miniatura_do_corte(tmp_path / "002-x.mp4") == ""


def test_compact_do_pipeline_guarda_o_phash():
    from picorte.risk_shield.pipeline import _compact
    v = _compact({"overall_status": "pass", "ypp_score": 80, "phash_signature": "ff00", "gates": {}})
    assert v["phash_signature"] == "ff00"
```

- [ ] **Step 2: Ver falhar.** Run: `python -m pytest tests/test_banco_sinais.py -q`. Expected: FAIL (módulo ausente).

- [ ] **Step 3: Implementar**

`picorte/services/sinais.py`:

```python
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
```

Em `picorte/risk_shield/pipeline.py`, no `return` de `_compact`, acrescente a linha `"phash_signature": verdict.get("phash_signature") or "",` depois de `"tiktok_originality_score"`.

- [ ] **Step 4: Rodar.** Run: `python -m pytest tests/test_banco_sinais.py tests/test_epic4_pipeline_wiring.py -q`. Expected: tudo passa.

- [ ] **Step 5: Sem commit.**

---

### Task 3: `sync_studio_project` grava fonte, sinais e veredito (B1, B2, B3)

**Files:**
- Modify: `picorte/services/studio_service.py:132-229` (reescrever `sync_studio_project`), `:18-29` (`status_fila`), `:231-286` (`record_manual_publication`)
- Test: `tests/test_banco_sync.py`

**Interfaces:**
- Consumes: `sinais_medidos`, `veredito_do_corte`, `miniatura_do_corte` (Task 2); colunas da Task 1.
- Produces:
  - `sync_studio_project(state, *, segments, outputs, workdir, duration_seconds) -> {"video", "clips"}`;
  - o `clip_id` é `studio-<pid>:<NNN>`, onde `NNN` é o `seg["id"]` ou a ordem com 3 dígitos;
  - `status_fila()` ganha `"arquivados": {"videos": int, "clips": int}` e conta só ativos.

- [ ] **Step 1: Teste (falhando)**

`tests/test_banco_sync.py`:

```python
import json

import pytest

from picorte.db.connection import Database
from picorte.services.studio_service import StudioService


@pytest.fixture
def servico(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 's.db'}")
    db.init_schema()
    return StudioService(db)


def _fonte(servico):
    return servico.create_source(name="DAVY JONES", platform="youtube", channel_handle="@davyjones",
                                 permission_status="liberada")


def _estado(pid="abc123def456", **extra):
    return {"id": pid, "source": "https://www.youtube.com/watch?v=x", "status": "complete",
            "options": {"aspect": "9:16", "ai_mode": "ollama"},
            "source_meta": {"detected_game": "gta6"}, **extra}


def test_b1_grava_a_fonte_do_portao(servico):
    fonte = _fonte(servico)
    r = servico.sync_studio_project(_estado(source_gate={"source_id": fonte["id"]}), segments=[])
    assert r["video"]["source_id"] == fonte["id"]
    assert r["video"]["game_slug"] == "gta6" and r["video"]["origin_type"] == "vod"


def test_b1_fonte_que_nao_existe_no_banco_fica_nula_sem_quebrar(servico):
    r = servico.sync_studio_project(_estado(source_gate={"source_id": "nao-existe"}), segments=[])
    assert r["video"]["source_id"] is None


def test_b2_sinais_medidos_ou_null(servico, tmp_path):
    segs = [
        {"start": 0, "end": 30, "overall": 8.0,
         "evidence": {"audio": 7.0, "chat": 2.5, "chat_measured": True, "visual": None}, "score_parts": {"text_score": 6.0}},
        {"start": 40, "end": 70, "overall": 10.0, "evidence": {}, "score_parts": {"llm_scout": 1}},
    ]
    r = servico.sync_studio_project(_estado(), segments=segs, outputs=[])
    medido, scout = r["clips"]
    assert (medido["score_chat"], medido["score_audio"], medido["score_visual"], medido["score_text"]) == (2.5, 7.0, None, 6.0)
    assert (scout["score_chat"], scout["score_audio"], scout["score_visual"], scout["score_text"]) == (None, None, None, None)
    assert scout["score_overall"] == 10.0


def test_b3_veredito_do_meta_vai_para_o_banco_e_mp4_casa_pelo_prefixo(servico, tmp_path):
    clips = tmp_path / "clips"
    clips.mkdir()
    mp4_2 = clips / "002-bbbb-segundo.mp4"
    (clips / "002-bbbb-segundo.meta.json").write_text(json.dumps({
        "thumbnail_1280x720": "t2.png",
        "risk_verdict": {"overall_status": "pass", "ypp_score": 84, "phash_signature": "ab"}}), encoding="utf-8")
    segs = [{"start": 0, "end": 30, "overall": 8.0}, {"start": 40, "end": 70, "overall": 9.0}]
    r = servico.sync_studio_project(_estado(), segments=segs, outputs=[str(mp4_2)])  # só o 2º foi renderizado
    primeiro, segundo = r["clips"]
    assert primeiro["mp4_path"] == "" and primeiro["risk_status"] == "pending" and primeiro["ypp_transform_score"] is None
    assert segundo["mp4_path"] == str(mp4_2) and segundo["thumbnail_path"] == "t2.png"
    assert (segundo["risk_status"], segundo["ypp_transform_score"], segundo["phash_signature"]) == ("pass", 84, "ab")


def test_ressincronizar_sem_meta_nao_apaga_veredito_gravado(servico):
    segs = [{"start": 0, "end": 30, "overall": 8.0}]
    servico.sync_studio_project(_estado(), segments=segs)
    servico.db.execute("UPDATE clips SET risk_status = 'hard_block', ypp_transform_score = 40 WHERE id = ?",
                       ("studio-abc123def456:001",))
    r = servico.sync_studio_project(_estado(), segments=segs)
    assert r["clips"][0]["risk_status"] == "hard_block" and r["clips"][0]["ypp_transform_score"] == 40


def test_sync_reativa_projeto_arquivado(servico):
    servico.sync_studio_project(_estado(), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    servico.db.execute("UPDATE videos SET archived_at = 't'")
    servico.db.execute("UPDATE clips SET archived_at = 't'")
    r = servico.sync_studio_project(_estado(), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    assert r["video"]["archived_at"] is None and r["clips"][0]["archived_at"] is None


def test_status_fila_conta_so_ativos(servico):
    servico.sync_studio_project(_estado("aaaaaaaaaaaa"), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    servico.sync_studio_project(_estado("bbbbbbbbbbbb"), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    servico.db.execute("UPDATE videos SET archived_at = 't' WHERE id = 'studio-bbbbbbbbbbbb'")
    servico.db.execute("UPDATE clips SET archived_at = 't' WHERE video_id = 'studio-bbbbbbbbbbbb'")
    st = servico.status_fila()
    assert (st["total_videos"], st["total_clips"]) == (1, 1)
    assert st["arquivados"] == {"videos": 1, "clips": 1}


def test_publicacao_manual_liga_ao_corte_do_sync(servico):
    servico.sync_studio_project(_estado(), segments=[{"start": 0, "end": 30, "overall": 8.0}])
    pub = servico.record_manual_publication(project_id="abc123def456", clip_stem="001-2abd1b6f-titulo",
                                            platform="tiktok", external_url="https://tiktok.com/@x/video/1")
    assert pub["clip_id"] == "studio-abc123def456:001"
    assert servico.db.fetch_one("SELECT COUNT(*) AS n FROM clips")["n"] == 1
```

- [ ] **Step 2: Ver falhar.** Run: `python -m pytest tests/test_banco_sync.py -q`. Expected: FAIL (`source_id` None, sinais 0.0 etc.).

- [ ] **Step 3: Implementar**

Em `picorte/services/studio_service.py`:
- acrescente no topo `import re` e `from pathlib import Path`;
- troque `status_fila` e `sync_studio_project` por:

```python
    def status_fila(self) -> dict[str, Any]:
        sources = self.repos.sources.list_sources()
        videos = [v for v in self.repos.videos.list_videos() if not v.get("archived_at")]
        n_clips = self.db.fetch_one("SELECT COUNT(*) AS n FROM clips WHERE archived_at IS NULL")["n"]
        arq_v = self.db.fetch_one("SELECT COUNT(*) AS n FROM videos WHERE archived_at IS NOT NULL")["n"]
        arq_c = self.db.fetch_one("SELECT COUNT(*) AS n FROM clips WHERE archived_at IS NOT NULL")["n"]
        return {
            "gpu_profile": detect_gpu_profile(),
            "total_sources": len(sources),
            "total_videos": len(videos),
            "total_clips": int(n_clips),
            "queued_videos": sum(1 for v in videos if v.get("status") == "queued"),
            "blocked_p1": sum(1 for v in videos if v.get("status") == "blocked_p1"),
            "arquivados": {"videos": int(arq_v), "clips": int(arq_c)},
        }
```

```python
    def _fonte_existente(self, source_id: Any) -> str | None:
        sid = str(source_id or "").strip()
        if sid and self.db.fetch_one("SELECT id FROM sources WHERE id = ?", (sid,)):
            return sid
        return None

    def sync_studio_project(
        self,
        project_state: dict[str, Any],
        *,
        segments: list[dict[str, Any]] | None = None,
        outputs: list[str] | None = None,
        workdir: Any = "",
        duration_seconds: float = 0.0,
    ) -> dict[str, Any]:
        """Espelha um projeto nas tabelas videos e clips gravando só o que foi medido (história 6.4)."""
        from datetime import datetime, timezone

        from picorte.services.sinais import miniatura_do_corte, sinais_medidos, veredito_do_corte

        now = datetime.now(timezone.utc).isoformat()
        project_id = str(project_state["id"])
        video_id = f"studio-{project_id}"
        source_url = str(project_state.get("source") or project_state.get("video") or "")
        origin_type = "vod" if re.match(r"^https?://", source_url, re.I) else "local_file"
        status = str(project_state.get("status") or "queued")
        options = project_state.get("options") or {}
        aspect = options.get("aspect", "9:16")
        fmt = "short_9_16" if aspect == "9:16" else ("long_16_9" if aspect == "16:9" else "square_1_1")
        ai_mode = str(options.get("ai_mode") or ("ollama" if options.get("llm") else "heuristic"))
        source_id = self._fonte_existente((project_state.get("source_gate") or {}).get("source_id"))  # B1
        game_slug = str((project_state.get("source_meta") or {}).get("detected_game") or "")

        self.db.execute(
            """INSERT INTO videos (id, source_id, origin_type, source_url, game_slug, duration_seconds,
                                   workdir_path, status, archived_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
               ON CONFLICT(id) DO UPDATE SET source_id = excluded.source_id, origin_type = excluded.origin_type,
                 source_url = excluded.source_url, game_slug = excluded.game_slug,
                 duration_seconds = excluded.duration_seconds, workdir_path = excluded.workdir_path,
                 status = excluded.status, archived_at = NULL, updated_at = excluded.updated_at""",
            (video_id, source_id, origin_type, source_url, game_slug, float(duration_seconds), str(workdir),
             status, now, now),
        )

        por_prefixo = {Path(o).name.split("-", 1)[0]: str(o) for o in (outputs or [])}
        synced_clips = []
        for idx, seg in enumerate(segments or [], 1):
            seg_id = str(seg.get("id") or f"{idx:03}")
            clip_id = f"{video_id}:{seg_id}"
            mp4_path = por_prefixo.get(seg_id, "")
            s = sinais_medidos(seg)  # B2
            self.db.execute(
                """INSERT INTO clips (id, video_id, parent_long_clip_id, format_type, ab_variant, start_sec, end_sec,
                     score_chat, score_audio, score_visual, score_text, score_overall, ypp_transform_score,
                     phash_signature, llm_mode_used, risk_status, mp4_path, thumbnail_path, proposed_title,
                     context_banner_2s, pinned_comment_debate, archived_at, created_at)
                   VALUES (?, ?, NULL, ?, 1, ?, ?, ?, ?, ?, ?, ?, NULL, '', ?, 'pending', ?, ?, ?, ?, ?, NULL, ?)
                   ON CONFLICT(id) DO UPDATE SET format_type = excluded.format_type, start_sec = excluded.start_sec,
                     end_sec = excluded.end_sec, score_chat = excluded.score_chat, score_audio = excluded.score_audio,
                     score_visual = excluded.score_visual, score_text = excluded.score_text,
                     score_overall = excluded.score_overall, llm_mode_used = excluded.llm_mode_used,
                     mp4_path = excluded.mp4_path, thumbnail_path = excluded.thumbnail_path,
                     proposed_title = excluded.proposed_title, context_banner_2s = excluded.context_banner_2s,
                     pinned_comment_debate = excluded.pinned_comment_debate, archived_at = NULL""",
                (clip_id, video_id, fmt, float(seg.get("start") or 0.0), float(seg.get("end") or 0.0),
                 s["score_chat"], s["score_audio"], s["score_visual"], s["score_text"],
                 float(seg.get("overall") or 0.0), str(seg.get("llm_mode_used") or ai_mode), mp4_path,
                 miniatura_do_corte(mp4_path) if mp4_path else "",
                 str(seg.get("proposed_title") or seg.get("hook") or ""), str(seg.get("context_banner_2s") or ""),
                 str(seg.get("pinned_comment_debate") or ""), now),
            )
            veredito = veredito_do_corte(mp4_path) if mp4_path else None  # B3
            if veredito:
                self.db.execute(
                    "UPDATE clips SET risk_status = ?, ypp_transform_score = ?, phash_signature = ? WHERE id = ?",
                    (veredito["risk_status"], veredito["ypp_transform_score"], veredito["phash_signature"], clip_id),
                )
            synced_clips.append(self.db.fetch_one("SELECT * FROM clips WHERE id = ?", (clip_id,)))

        return {"video": self.db.fetch_one("SELECT * FROM videos WHERE id = ?", (video_id,)), "clips": synced_clips}
```

Em `record_manual_publication`, troque a linha `clip_id = f"{video_id}:{clip_stem}"` por:

```python
        prefixo = str(clip_stem).split("-", 1)[0]
        do_sync = f"{video_id}:{prefixo}"
        clip_id = do_sync if self.db.fetch_one("SELECT id FROM clips WHERE id = ?", (do_sync,)) \
            else f"{video_id}:{clip_stem}"
```

No INSERT de clip dentro dela, troque `0.0, 0.0, 0.0, 0.0, 0.0, 0,` por `None, None, None, None, 0.0, None,`: corte registrado à mão não tem sinal medido.

- [ ] **Step 4: Rodar.** Run: `python -m pytest tests/test_banco_sync.py tests/test_e2_practical_integration.py tests/test_mcp_and_service.py -q`. Expected:
- passam os da 6.4 e o `test_e2_practical_integration`;
- o `test_mcp_and_service` deve falhar só em `total_videos`/`enqueue` (a Task 6 ajusta).

- [ ] **Step 5: Sem commit.**

---

### Task 4: Render passa o `clip_id` à auditoria e a sincronização deixa de falhar em silêncio

**Files:**
- Create: `picorte/services/reconciliacao.py` (parte 1: `sincronizar_pasta`)
- Modify: `picorte/risk_shield/pipeline.py` (`attach_risk_verdict(..., clip_id=None)`), `projects.py` e `picorte/engine/projects.py` (chamada do `attach_risk_verdict` e bloco final de sincronização)
- Test: `tests/test_banco_reconciliacao.py` (parte 1)

**Interfaces:**
- Produces: `sincronizar_pasta(servico: StudioService, pasta: Path, estado: dict | None = None) -> dict` (lê `project.json` se `estado` for `None`, `segments.json` e `transcript.json`; nunca escreve em `pasta`); `attach_risk_verdict(..., clip_id: str | None = None)`.

- [ ] **Step 1: Teste (falhando)**

Crie `tests/test_banco_reconciliacao.py`:

```python
import json

import pytest

from picorte.db.connection import Database
from picorte.services.studio_service import StudioService


@pytest.fixture
def servico(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'r.db'}")
    db.init_schema()
    return StudioService(db)


def _projeto(raiz, pid, *, status="complete", segmentos=None, gate=None):
    pasta = raiz / pid
    pasta.mkdir(parents=True)
    (pasta / "project.json").write_text(json.dumps({
        "id": pid, "source": "https://www.youtube.com/watch?v=x", "status": status, "options": {"aspect": "9:16"},
        "source_gate": gate, "last_outputs": []}), encoding="utf-8")
    (pasta / "segments.json").write_text(json.dumps(segmentos or []), encoding="utf-8")
    (pasta / "transcript.json").write_text(json.dumps({"duration": 3600.0, "words": []}), encoding="utf-8")
    return pasta


def _foto(pasta):
    return {p.name: p.stat().st_mtime_ns for p in pasta.iterdir()}


def test_sincronizar_pasta_le_tudo_e_nao_escreve_na_pasta(servico, tmp_path):
    from picorte.services.reconciliacao import sincronizar_pasta
    pasta = _projeto(tmp_path / "projects", "aaaaaaaaaaaa", segmentos=[{"start": 0, "end": 30, "overall": 7.0}])
    antes = _foto(pasta)
    r = sincronizar_pasta(servico, pasta)
    assert r["video"]["duration_seconds"] == 3600.0 and len(r["clips"]) == 1
    assert _foto(pasta) == antes


def test_attach_risk_verdict_repassa_o_clip_id(monkeypatch, tmp_path):
    from picorte.risk_shield import pipeline
    visto = {}
    monkeypatch.setattr(pipeline, "audit_clip_risk", lambda db, **kw: visto.update(kw) or {
        "overall_status": "pass", "gates": {}, "per_platform": {}})
    monkeypatch.setattr(pipeline, "sample_clip_frames", lambda mp4: [])
    pipeline.attach_risk_verdict(None, meta_path=tmp_path / "x.meta.json", source_id=None, seg={},
                                 words=[], mp4_path=None, options={}, clip_id="studio-p:001")
    assert visto["clip_id"] == "studio-p:001"
```

- [ ] **Step 2: Ver falhar.** Run: `python -m pytest tests/test_banco_reconciliacao.py -q`. Expected: FAIL (módulo ausente; `clip_id` inesperado).

- [ ] **Step 3: Implementar**

`picorte/services/reconciliacao.py` (parte 1):

```python
"""Banco × disco (B4) e preparação do banco no boot (B6) — história 6.4. Nunca escreve em projects/."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picorte.services.studio_service import StudioService


def _ler_json(caminho: Path, padrao: Any) -> Any:
    try:
        return json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return padrao


def sincronizar_pasta(servico: StudioService, pasta: Path, estado: dict[str, Any] | None = None) -> dict[str, Any]:
    """Espelha uma pasta de projeto no banco lendo project.json, segments.json e transcript.json (só leitura)."""
    pasta = Path(pasta)
    estado = estado if estado is not None else _ler_json(pasta / "project.json", {})
    if not isinstance(estado, dict) or not estado.get("id"):
        raise ValueError(f"project.json ilegível em {pasta.name}")
    segmentos = _ler_json(pasta / "segments.json", [])
    transcricao = _ler_json(pasta / "transcript.json", {})
    duracao = float(transcricao.get("duration") or 0.0) if isinstance(transcricao, dict) else 0.0
    return servico.sync_studio_project(
        estado,
        segments=segmentos if isinstance(segmentos, list) else [],
        outputs=estado.get("last_outputs") or [],
        workdir=pasta,
        duration_seconds=duracao,
    )
```

Em `picorte/risk_shield/pipeline.py`:
- `attach_risk_verdict` ganha o parâmetro `clip_id: str | None = None` (depois de `cadence_state_path`);
- a chamada de `audit_clip_risk` recebe `clip_id=clip_id,`.

Em `projects.py` (e igual em `picorte/engine/projects.py`):

1. Na chamada `attach_risk_verdict(...)`, acrescente:

   ```python
                            clip_id=f"studio-{state['id']}:{segment['id']}",
   ```

2. Troque o bloco final de sincronização, que vai de `try:` / `from picorte.services.studio_service import StudioService` até `except Exception:` / `pass`, por:

   ```python
        try:
            from picorte.services.reconciliacao import sincronizar_pasta
            from picorte.services.studio_service import StudioService
            sincronizar_pasta(StudioService(), path, state)
        except Exception as db_exc:  # o banco não derruba o job, mas a falha fica visível na Saúde
            from picorte.engine import health as _health
            _health.record(path, "banco", "failed", f"{type(db_exc).__name__}: {db_exc}")
   ```

Confira: `diff projects.py picorte/engine/projects.py` vazio.

- [ ] **Step 4: Rodar.** Run: `python -m pytest tests/test_banco_reconciliacao.py tests/test_epic4_pipeline_wiring.py tests/test_epic4_p1_end_to_end.py -q`. Expected: tudo passa.

- [ ] **Step 5: Sem commit.**

---

### Task 5: Reconciliação banco × disco e preparo no boot (B4, B6)

**Files:**
- Modify: `picorte/services/reconciliacao.py` (parte 2), `estudio.py`, `picorte/mcp/server.py` (`main`)
- Test: `tests/test_banco_reconciliacao.py` (parte 2)

**Interfaces:**
- Consumes: `sincronizar_pasta` (Task 4), `sync_publisher_policies` (`picorte.risk_shield.policy_gate`).
- Produces: `reconciliar(db, raiz) -> {"ressincronizados": int, "arquivados": int, "reativados": int, "falhas": list[str]}`; `preparar_banco(db, raiz) -> {"politicas": int, **reconciliar}`.

- [ ] **Step 1: Teste (falhando)** — acrescente a `tests/test_banco_reconciliacao.py`:

```python
def test_reconciliar_arquiva_orfaos_sem_perder_publicados(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    raiz = tmp_path / "projects"
    _projeto(raiz, "aaaaaaaaaaaa", segmentos=[{"start": 0, "end": 30, "overall": 7.0}])
    db = servico.db
    db.execute("INSERT INTO videos (id, source_url, workdir_path, status, created_at, updated_at) "
               "VALUES ('studio-zzzzzzzzzzzz', 'u', '/home/bomba/projects/zzzzzzzzzzzz', 'complete', 't', 't')")
    db.execute("INSERT INTO clips (id, video_id, start_sec, end_sec, created_at) "
               "VALUES ('studio-zzzzzzzzzzzz:001', 'studio-zzzzzzzzzzzz', 0, 10, 't')")
    db.execute("INSERT INTO publications (id, clip_id, platform, status, external_url, created_at) "
               "VALUES ('p1', 'studio-zzzzzzzzzzzz:001', 'tiktok', 'publicado', 'https://x', 't')")
    r = reconciliar(db, raiz)
    assert r["ressincronizados"] == 1 and r["arquivados"] == 1 and r["falhas"] == []
    assert db.fetch_one("SELECT archived_at FROM videos WHERE id = 'studio-zzzzzzzzzzzz'")["archived_at"]
    assert db.fetch_one("SELECT archived_at FROM clips WHERE id = 'studio-zzzzzzzzzzzz:001'")["archived_at"]
    assert db.fetch_one("SELECT clip_id FROM publications WHERE id = 'p1'")["clip_id"] == "studio-zzzzzzzzzzzz:001"
    assert db.fetch_one("SELECT archived_at FROM videos WHERE id = 'studio-aaaaaaaaaaaa'")["archived_at"] is None


def test_reconciliar_reativa_quando_a_pasta_volta(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    raiz = tmp_path / "projects"
    servico.db.execute("INSERT INTO videos (id, source_url, workdir_path, status, archived_at, created_at, updated_at) "
                       "VALUES ('studio-bbbbbbbbbbbb', 'u', '', 'complete', 't', 't', 't')")
    _projeto(raiz, "bbbbbbbbbbbb")
    r = reconciliar(servico.db, raiz)
    assert servico.db.fetch_one("SELECT archived_at FROM videos WHERE id = 'studio-bbbbbbbbbbbb'")["archived_at"] is None
    assert r["arquivados"] == 0


def test_caminho_vazio_nao_conta_como_presente(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    servico.db.execute("INSERT INTO videos (id, source_url, workdir_path, status, created_at, updated_at) "
                       "VALUES ('mcp-antigo', 'u', '', 'queued', 't', 't')")
    assert reconciliar(servico.db, tmp_path / "projects")["arquivados"] == 1


def test_reconciliar_registra_falha_sem_parar(servico, tmp_path):
    from picorte.services.reconciliacao import reconciliar
    raiz = tmp_path / "projects"
    (raiz / "quebrado00000").mkdir(parents=True)
    (raiz / "quebrado00000" / "project.json").write_text("{", encoding="utf-8")
    _projeto(raiz, "cccccccccccc")
    r = reconciliar(servico.db, raiz)
    assert r["ressincronizados"] == 1 and r["falhas"] and "quebrado00000" in r["falhas"][0]


def test_preparar_banco_sincroniza_politicas_e_reconcilia(tmp_path):
    from picorte.services.reconciliacao import preparar_banco
    db = Database(f"sqlite:///{tmp_path / 'b.db'}")
    r = preparar_banco(db, tmp_path / "projects")
    assert r["politicas"] >= 1
    assert db.fetch_one("SELECT COUNT(*) AS n FROM publisher_policies")["n"] == r["politicas"]
```

- [ ] **Step 2: Ver falhar.** Run: `python -m pytest tests/test_banco_reconciliacao.py -q`. Expected: FAIL (`reconciliar` ausente).

- [ ] **Step 3: Implementar** — acrescente a `picorte/services/reconciliacao.py`:

```python
def _presente(video: dict[str, Any], raiz: Path) -> bool:
    workdir = str(video.get("workdir_path") or "").strip()
    if workdir and Path(workdir).is_dir():
        return True
    vid = str(video.get("id") or "")
    return vid.startswith("studio-") and (raiz / vid[len("studio-"):] / "project.json").is_file()


def reconciliar(db, raiz) -> dict[str, Any]:
    """B4: re-sincroniza as pastas existentes e arquiva (nunca apaga) o que sumiu do disco."""
    raiz = Path(raiz)
    servico = StudioService(db)
    ressincronizados, falhas = 0, []
    for arquivo in sorted(raiz.glob("*/project.json")):
        try:
            sincronizar_pasta(servico, arquivo.parent)
            ressincronizados += 1
        except Exception as exc:  # um projeto quebrado não impede os outros
            falhas.append(f"{arquivo.parent.name}: {type(exc).__name__}: {exc}")
    agora = datetime.now(timezone.utc).isoformat()
    arquivados = reativados = 0
    for video in db.fetch_all("SELECT id, workdir_path, archived_at FROM videos"):
        presente = _presente(video, raiz)
        if presente and video.get("archived_at"):
            db.execute("UPDATE videos SET archived_at = NULL WHERE id = ?", (video["id"],))
            db.execute("UPDATE clips SET archived_at = NULL WHERE video_id = ?", (video["id"],))
            reativados += 1
        elif not presente and not video.get("archived_at"):
            db.execute("UPDATE videos SET archived_at = ? WHERE id = ?", (agora, video["id"]))
            db.execute("UPDATE clips SET archived_at = ? WHERE video_id = ? AND archived_at IS NULL",
                       (agora, video["id"]))
            arquivados += 1
    return {"ressincronizados": ressincronizados, "arquivados": arquivados, "reativados": reativados,
            "falhas": falhas}


def preparar_banco(db, raiz) -> dict[str, Any]:
    """Boot do Estúdio: migração, políticas de publisher (B6) e reconciliação banco × disco (B4)."""
    from picorte.risk_shield.policy_gate import sync_publisher_policies

    db.init_schema()
    return {"politicas": sync_publisher_policies(db), **reconciliar(db, raiz)}
```

Em `estudio.py`, depois de `app = create_app(...)` e antes do `print`, acrescente:

```python
    try:
        from picorte.db.connection import get_default_db
        from picorte.services.reconciliacao import preparar_banco
        r = preparar_banco(get_default_db(), app.state.raiz)
        print(f"Banco: {r['ressincronizados']} projeto(s) sincronizado(s), {r['arquivados']} arquivado(s), "
              f"{r['politicas']} política(s).", flush=True)
        for falha in r["falhas"]:
            print(f"  aviso: {falha}", flush=True)
    except Exception as exc:  # banco com problema não impede o painel de abrir
        print(f"Banco: não consegui preparar ({type(exc).__name__}: {exc}).", flush=True)
```

Em `picorte/mcp/server.py`, no início de `main()`:

```python
    try:  # B6: políticas de publisher disponíveis desde o boot
        from picorte.risk_shield.policy_gate import sync_publisher_policies
        sync_publisher_policies(server.service.db)
    except Exception as exc:
        sys.stderr.write(f"picorte-mcp: políticas não sincronizadas ({exc})\n")
```

(logo depois de `server = PicorteMCPServer()`).

- [ ] **Step 4: Rodar.** Run: `python -m pytest tests/test_banco_reconciliacao.py -q`. Expected: 7 passam.

- [ ] **Step 5: Sem commit.**

---

### Task 6: Fila única — o MCP enfileira pelo Estúdio (B5)

**Files:**
- Create: `picorte/services/estudio_conexao.py`
- Modify: `estudio.py`, `picorte/services/studio_service.py` (`enqueue_video`), `picorte/mcp/server.py` (esquema e chamada), `skills/picorte-operador/SKILL.md`, `.gitignore`, `tests/test_mcp_and_service.py`
- Test: `tests/test_banco_fila_unica.py`

**Interfaces:**
- Produces:
  - `ARQUIVO_CONEXAO`;
  - `gravar_conexao(porta: int, token: str, arquivo=ARQUIVO_CONEXAO)`, `ler_conexao(arquivo=...) -> dict | None`, `apagar_conexao(arquivo=...)`;
  - `enfileirar_no_estudio(fontes: list[str], opcoes: dict | None = None, *, arquivo=..., post=httpx.post) -> dict`;
  - `class EstudioDesligado(RuntimeError)`;
  - `StudioService.enqueue_video(*, source_url: str, options: dict | None = None) -> dict`.

- [ ] **Step 1: Teste (falhando)**

`tests/test_banco_fila_unica.py`:

```python
import pytest
from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.services.estudio_conexao import (EstudioDesligado, apagar_conexao, enfileirar_no_estudio,
                                              gravar_conexao, ler_conexao)
from picorte.services.fila import FilaEstudio


def test_conexao_grava_le_e_apaga(tmp_path):
    arq = tmp_path / ".picorte" / "estudio.json"
    gravar_conexao(8770, "segredo", arquivo=arq)
    assert ler_conexao(arquivo=arq)["porta"] == 8770
    apagar_conexao(arquivo=arq)
    assert ler_conexao(arquivo=arq) is None


def test_sem_estudio_aberto_avisa_e_nao_cria_nada(tmp_path):
    with pytest.raises(EstudioDesligado, match="python estudio.py"):
        enfileirar_no_estudio(["https://www.youtube.com/watch?v=x"], arquivo=tmp_path / "nada.json")


def test_mcp_usa_a_mesma_rota_do_painel(tmp_path):
    raiz = tmp_path / "projects"
    chamadas = []
    fila = FilaEstudio(raiz, executar=lambda p, a, pr, pk: chamadas.append((p.name, a)) or 0)
    app = create_app(raiz, token="tok", dist=tmp_path / "d", fila=fila,
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()))
    arq = tmp_path / "estudio.json"
    gravar_conexao(8770, "tok", arquivo=arq)
    with TestClient(app) as cliente:
        r = enfileirar_no_estudio(["https://www.youtube.com/watch?v=x"], arquivo=arq, post=cliente.post)
        pid = r["projetos"][0]["id"]
        fila._futuros[pid].result(timeout=5)
    assert chamadas == [(pid, "prepare")]
    assert (raiz / pid / "project.json").is_file()


def test_erro_do_estudio_vira_mensagem_legivel(tmp_path):
    arq = tmp_path / "estudio.json"
    gravar_conexao(8770, "tok", arquivo=arq)

    class Resposta:
        status_code = 400
        content = b'{"erro":"Envie de 1 a 100 fontes."}'

        def json(self):
            return {"erro": "Envie de 1 a 100 fontes."}

    with pytest.raises(ValueError, match="Envie de 1 a 100 fontes."):
        enfileirar_no_estudio([], arquivo=arq, post=lambda *a, **k: Resposta())
```

- [ ] **Step 2: Ver falhar.** Run: `python -m pytest tests/test_banco_fila_unica.py -q`. Expected: FAIL (módulo ausente).

- [ ] **Step 3: Implementar**

`picorte/services/estudio_conexao.py`:

```python
"""Fila única (B5, história 6.4): o MCP enfileira pelo Estúdio aberto, na mesma rota do painel."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from picorte.api.seguranca import CABECALHO_TOKEN
from picorte.config import PROJECT_ROOT

ARQUIVO_CONEXAO = PROJECT_ROOT / ".picorte" / "estudio.json"
AVISO = "O Estúdio não está rodando. Abra com: python estudio.py (o job entra na mesma fila do painel)."


class EstudioDesligado(RuntimeError):
    pass


def gravar_conexao(porta: int, token: str, arquivo: Path = ARQUIVO_CONEXAO) -> None:
    arquivo = Path(arquivo)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps({"porta": int(porta), "token": token, "pid": os.getpid()}), encoding="utf-8")


def ler_conexao(arquivo: Path = ARQUIVO_CONEXAO) -> dict[str, Any] | None:
    try:
        dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dados if isinstance(dados, dict) and dados.get("porta") and dados.get("token") else None


def apagar_conexao(arquivo: Path = ARQUIVO_CONEXAO) -> None:
    Path(arquivo).unlink(missing_ok=True)


def enfileirar_no_estudio(fontes: list[str], opcoes: dict[str, Any] | None = None, *,
                          arquivo: Path = ARQUIVO_CONEXAO, post=httpx.post) -> dict[str, Any]:
    """Cria os projetos e enfileira o preparo pela rota /api/lote do Estúdio (o portão P1 roda antes de baixar)."""
    conexao = ler_conexao(arquivo)
    if not conexao:
        raise EstudioDesligado(AVISO)
    url = f"http://127.0.0.1:{int(conexao['porta'])}/api/lote"
    try:
        resposta = post(url, json={"sources": fontes, "options": opcoes or {}},
                        headers={CABECALHO_TOKEN: str(conexao["token"])}, timeout=30)
    except httpx.HTTPError as exc:
        raise EstudioDesligado(AVISO) from exc
    dados = resposta.json() if resposta.content else {}
    if resposta.status_code >= 400:
        raise ValueError(str(dados.get("erro") or f"O Estúdio respondeu {resposta.status_code}."))
    return dados
```

Em `estudio.py`:
- acrescente o import `from picorte.services.estudio_conexao import apagar_conexao, gravar_conexao`;
- troque a linha final `uvicorn.run(...)` por:

```python
    gravar_conexao(args.porta, app.state.token)
    try:
        uvicorn.run(app, host="127.0.0.1", port=args.porta, log_level="warning")
    finally:
        apagar_conexao()
```

Em `picorte/services/studio_service.py`, troque `enqueue_video` por:

```python
    def enqueue_video(self, *, source_url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fila única (B5): cria o projeto real na fila do Estúdio, o mesmo caminho do painel."""
        from picorte.services import estudio_conexao

        return estudio_conexao.enfileirar_no_estudio([source_url], options)
```

Em `picorte/mcp/server.py`:
1. Troque a definição do `picorte_enfileirar_video` por:

   ```python
            {
                "name": "picorte_enfileirar_video",
                "description": ("Cria o projeto e o coloca na fila única do Estúdio (o mesmo caminho do painel). "
                                "O Estúdio precisa estar aberto (python estudio.py); o portão P1 roda antes de baixar."),
                "inputSchema": {
                    "type": "object",
                    "required": ["source_url"],
                    "properties": {
                        "source_url": {"type": "string"},
                        "options": {"type": "object"},
                    },
                },
            },
   ```

2. Troque a chamada por:

   ```python
        if name == "picorte_enfileirar_video":
            return self.service.enqueue_video(source_url=args["source_url"], options=args.get("options"))
   ```

Em `tests/test_mcp_and_service.py`:
- no passo 3, envolva a chamada com `unittest.mock.patch("picorte.services.estudio_conexao.enfileirar_no_estudio", return_value={"projetos": [{"id": "abc123def456", "status": "queued"}]})`;
- troque `self.assertEqual(video["status"], "queued")` por `self.assertEqual(video["projetos"][0]["status"], "queued")`;
- troque o argumento para `{"source_url": "https://twitch.tv/videos/999"}`;
- no passo 4, `total_videos` passa a `0`, porque o MCP não cria mais uma linha fantasma.

`skills/picorte-operador/SKILL.md`, linha 14:

```
3. **`picorte_enfileirar_video`:** cria o projeto e o coloca na fila única do Estúdio (precisa do `python estudio.py` aberto; o portão P1 roda antes de baixar).
```

`.gitignore`: acrescente `.picorte/` depois de `picorte/web/dist/`.

- [ ] **Step 4: Rodar.** Run: `python -m pytest tests/test_banco_fila_unica.py tests/test_mcp_and_service.py -q`. Expected: tudo passa.

- [ ] **Step 5: Sem commit.**

---

### Task 7: Capacidades refletem a 6.4

**Files:**
- Modify: `picorte/capacidades/catalogo.py` (linhas de SIS-5, SIS-12, REV-2, FON-4, FON-5, ESC-1, ESC-5)
- Test: `tests/test_estudio_capacidades.py`

- [ ] **Step 1: Teste (falhando)** — acrescente:

```python
def test_historia_6_4_ligou_o_banco_o_mcp_e_os_sinais(tmp_path):
    caps = _por_id(listar_capacidades(tmp_path, cache_falso()))
    for i in ["SIS-5", "SIS-12", "REV-2", "FON-4", "FON-5"]:
        assert caps[i]["status"] == "ligado", i
        assert caps[i]["ligou_em"] == "2026-11-22", i
    for i in ["ESC-1", "ESC-5"]:
        assert caps[i]["status"] == "parcial" and "B3" not in caps[i]["motivo"], i
```

- [ ] **Step 2: Ver falhar.** Run: `python -m pytest tests/test_estudio_capacidades.py -q`.

- [ ] **Step 3: Implementar** — troque as sete linhas por:

```python
        _c("SIS-5", "sistema", "Banco", L, None, "", "picorte.db (B1–B4, B6 da história 6.4)", "2", "2.1", ligou_em="2026-11-22"),
        _c("SIS-12", "sistema", "Servidor MCP", L, None, "", "picorte/mcp/server.py (fila única, B5)", "2", "2.4", ligou_em="2026-11-22"),
        _c("REV-2", "revisao", "Sinais medidos por corte", L, None, "", "clips.score_* (NULL = não medido)", "3", "3.2/3.5.4", escopo="corte", ligou_em="2026-11-22"),
        _c("FON-4", "fontes", "Elo fonte → vídeos → cortes", L, None, "", "videos.source_id", "2", "2.1", ligou_em="2026-11-22"),
        _c("FON-5", "fontes", "Políticas por publisher/jogo", L, None, "", "publisher_policies (sincronizada no boot)", "4", "4.1", ligou_em="2026-11-22"),
        _c("ESC-1", "escudo", "Veredito por corte e por rede", P, "dado", "nenhum corte renderizado depois do Escudo ainda; renderize de novo para ter veredito", "clips.risk_status + .meta.json.risk_verdict", "4", "4.5", escopo="corte"),
        _c("ESC-5", "escudo", "YPP, originalidade TikTok e pHash", P, "dado", "aparece quando houver corte renderizado com veredito", "clips.ypp_transform_score, phash_signature", "4", "4.2", escopo="corte"),
```

- [ ] **Step 4: Rodar.** Run: `python -m pytest tests/test_estudio_*.py -q`. Expected: tudo passa.

- [ ] **Step 5: Sem commit.**

---

### Task 8: Verificação de ponta a ponta numa cópia do banco

- [ ] **Step 1: Suíte completa.** Run: `python -m pytest -q -p no:cacheprovider`. Expected: nenhuma falha nova em relação à linha de base de 2026-11-22 (735 + 75 + 64 web; os testes da worktree do motor não rodam aqui).
- [ ] **Step 2: Cópia do banco real** (o real fica intocado).

  Copie `picorte.db` para `<scratchpad>/picorte-copia.db` e rode:

  ```
  DATABASE_URL=sqlite:///<scratchpad>/picorte-copia.db python -c "from picorte.db.connection import get_default_db; from picorte.services.reconciliacao import preparar_banco; print(preparar_banco(get_default_db(), 'projects'))"
  ```

  Isso lê `projects/` sem escrever (confira com `git status projects` vazio e a data de modificação dos `project.json` igual). Expected:
  - os cortes órfãos e os vídeos de `/home/bomba` aparecem arquivados;
  - os 2 publicados continuam ligados às suas publicações;
  - os projetos com `source_gate` passam a ter `source_id`;
  - nenhum `score_chat` ou `score_audio` fica 0.0 sem medição (consulta: `SELECT COUNT(*) FROM clips WHERE score_chat = 0.0` deve dar 0 ou só valores que vieram medidos).
- [ ] **Step 3: Fumaça do MCP pelo Estúdio.**
  - Suba `python estudio.py --pasta-projetos <scratchpad>/p --porta 8771 --sem-navegador` e confira o arquivo `.picorte/estudio.json`.
  - Chame `PicorteMCPServer().call_tool("picorte_enfileirar_video", {"source_url": "<link de canal NÃO cadastrado>"})` e confira que o projeto aparece em `GET /api/projetos` e que o preparo falha no portão P1 ("Fonte desconhecida… Nada foi baixado"). Isso prova a fila única sem baixar nada.
  - Pare o servidor e confira que `.picorte/estudio.json` sumiu.
- [ ] **Step 4: Registrar** os desvios no fim deste plano e atualizar a memória do painel. **Sem commit.**

## Autoavaliação

**Cobertura das ACs:**

| AC | Tasks |
|---|---|
| AC1 (B1) | Tasks 3 e 5 |
| AC2 (B2) | Tasks 1, 2 e 3 |
| AC3 (B3) | Tasks 2, 3 e 4 |
| AC4 (B4) | Task 5 |
| AC5 (B6) | Task 5 |
| AC6 (B5) | Task 6 |

As capacidades ficam na Task 7 e a verificação na Task 8.

**P1 e deduplicação:** com o pHash agora persistido, um corte re-renderizado se compararia com ele mesmo. A Task 4 repassa o `clip_id`, que a deduplicação já sabe excluir. A duplicata entre projetos diferentes continua barrada (a lógica não mudou).

**Tipos consistentes:**
- `sincronizar_pasta(servico, pasta, estado=None)` é usada pelo `projects.py` e pelo `reconciliar`;
- `veredito_do_corte` devolve `ypp_transform_score` com o mesmo nome da coluna;
- `enqueue_video(source_url=, options=)` bate com a chamada do MCP.

## Desvios na execução (2026-11-22)

1. **B1 casa pela `@handle`:**
   - **O problema:** a cópia do banco real mostrou que o `source_id` gravado no `project.json` é um uuid de outro banco, porque a semeadura do registro gera ids novos em cada banco. Só 1 de 5 projetos ligava.
   - **Correção:** `_fonte_existente` virou `_fonte_do_portao`. Ela tenta o id e, se não existir, casa pela `channel_handle` do portão (há teste). Resultado: 5 de 5. O `2501be513575` é anterior ao Escudo e fica sem fonte.
2. **Publicações antigas religadas:**
   - **O problema:** as 2 publicações manuais anteriores à 6.4 apontavam para um corte criado pelo nome do arquivo (`studio-<pid>:003-<hash>-<título>`).
   - **Correção:** `reconciliar` agora religa ao corte do sync (`studio-<pid>:003`) e arquiva a duplicata, sem apagar nada (`publicacoes_religadas` no resultado, com teste).
3. **Postgres:** o padrão `LIKE` passou a ir como parâmetro, porque o psycopg leria um `%` literal como marcador.
4. **Arquivo de conexão velho:** quando o Estúdio é fechado à força, o `finally` não roda e o arquivo fica. Um teste garante que isso vira o aviso "O Estúdio não está rodando…", e não um erro.
5. **Erro meu na fumaça:**
   - **O que aconteceu:** chamei o `PicorteMCPServer()` sem `DATABASE_URL`, então o `init_schema` migrou o `picorte.db` **real** às 01:45:55.
   - **O efeito:** colunas de sinal e YPP anuláveis, os 248 valores falsos (0.0 e a nota geral copiada) virando NULL, e `archived_at` criado vazio. A reconciliação **não** rodou no banco real.
   - **Por que nada se perdeu:** a nota geral segue em `score_overall`, e os valores antigos são reconstruíveis (todos 0.0; `score_text` = `score_overall`). `integrity_check` = ok e chaves estrangeiras ok.
6. **Suíte completa adiada a pedido do dono:**
   - **O motivo:** ela competia com o job da outra sessão na GPU.
   - **O que rodou no lugar:** 150 testes leves (banco, Escudo sem Demucs, MCP e Estúdio).
   - **Ficaram de fora até o fim:** `test_epic4_music_*` (Demucs na GPU) e `test_epic4_p1_end_to_end.py`.
