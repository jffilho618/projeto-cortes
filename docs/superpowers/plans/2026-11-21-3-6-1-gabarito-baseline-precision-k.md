# Story 3.6.1 — Gabarito Automático e Baseline de Precision@K — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** medir o motor de seleção ATUAL contra um gabarito fraco e automático (comentários com horário + heatmap "mais repetidos"), com Precision@K (K=5,10) comparada ao acaso, sem mudar nada na seleção.

**Architecture:** módulo novo `picorte/engine/benchmark.py` (só no engine; não é arquivo espelho). Funções puras (gabarito, acerto, acaso exato, avaliação por VOD) + carga de projeto + `run_benchmark` que grava `benchmarks/<data>.json` e `benchmarks/gabaritos/<video_id>.json`. Um subcomando `fetch-labels` (rede, só metadados) completa o gabarito de projetos antigos passando pelo portão P1 real (`gate_project_source`). O minerador de comentários ganha o campo `timestamp_s` (aditivo).

**Tech Stack:** Python 3.12 global, pytest, `pathlib`, `filelock` via `health.record` (AD-11).

**Spec:** `_bmad-output/planning-artifacts/epics.md` → Story 3.6.1; `_bmad-output/planning-artifacts/sprint-change-proposal-2026-11-21.md`; `research/technical-motor-selecao-cortes-2026-11-21/research.md` (b).

## Global Constraints

- Nada no motor de seleção muda (score_clips, multitrack, llm_router intocados).
- Custo zero: nenhuma chamada a LLM; rede só no `fetch-labels`, explícito, só metadados (`--skip-download`).
- P1: `fetch-labels` usa `gate_project_source`; fonte não cadastrada/pausada não é minerada.
- VOD sem comentários com horário nem heatmap = `sem_gabarito`, fora da média.
- AD-11: `pathlib.Path`, escrita atômica, nada de `fcntl`.
- "Sinal só vale se medido": cada projeto avaliado registra `benchmark_gabarito` em `engine_health.json`.

## Definições

- **Momento do gabarito:** intervalo `[a, b]`. Comentário: `a = b = timestamp_s`. Heatmap: pico de `ingest.extract_heatmap_peaks` (`a = start`, `b = end` do bin).
- **Acerto:** clipe `[s, e]` acerta se algum momento cruza `[s − tol, e + tol]` (tol padrão 10 s).
- **Top-K:** clipes de `segments.json` ordenados por `rank` (1 = melhor). Se o motor deu menos de K, `k_efetivo < K` e a precisão divide por `k_efetivo`.
- **Precision@K:** acertos / k_efetivo. **Acaso da precisão:** média, sobre os clipes do top-K, da probabilidade exata de um clipe do mesmo tamanho posto uniformemente em `[0, D − L]` acertar algum momento (medida da união de `[a − L − tol, b + tol] ∩ [0, D − L]` dividida por `D − L`).
- **Recall@K:** fração dos momentos cobertos pelo top-K. **Acaso do recall:** média sobre momentos de `1 − Π(1 − p_i)` com `p_i` a chance do clipe aleatório i cobrir o momento (equivale ao K/N da literatura para janelas iguais).
- **Lift:** precisão / acaso.
- **Vazamento:** clipe do top-K com `seed_kind` em `{comment_timestamp, heatmap_peak}` nasceu do próprio gabarito → contado em `semeados_pelo_gabarito`.

---

### Task 1: `timestamp_s` nas sementes de comentário

**Files:** Modify `picorte/engine/comments_miner.py` (`mine_youtube_comments`); Test `tests/test_e36_benchmark.py`.

- [ ] Teste: `mine_youtube_comments` com runner falso devolvendo JSON com comentário "12:34 caiu kkk" → semente tem `timestamp_s == 754.0`.
- [ ] Rodar → FAIL (KeyError). Implementar `"timestamp_s": t` no dict. Rodar → PASS.

### Task 2: Gabarito, acerto e acaso (funções puras)

**Files:** Create `picorte/engine/benchmark.py`; Test `tests/test_e36_benchmark.py`.

**Produces:**
- `comment_moments(seeds: list[dict]) -> list[dict]` — `{"fonte": "comentario", "a", "b", "t", "likes", "texto"}`; sem `timestamp_s` infere `start + 12` (start > 0) ou `max(0, end − 22)`.
- `heatmap_moments(heatmap: list[dict]) -> list[dict]` — `{"fonte": "heatmap", "a", "b", "t", "valor"}`.
- `build_gabarito(seeds, heatmap) -> dict` — `{"status": "ok"|"sem_gabarito", "momentos": [...], "fontes": {"comentarios": n, "heatmap": n}}`.
- `clip_hits(start, end, moments, tol=10.0) -> bool`
- `chance_hit(length, duration, moments, tol=10.0) -> float`
- `chance_cover(lengths, duration, moment, tol=10.0) -> float`

Testes (valores calculados à mão):
- gabarito vazio → `sem_gabarito`; só heatmap → `ok`.
- inferência do horário sem `timestamp_s` (start 88 → 100; start 0/end 30 → 8).
- acerto dentro, na borda da tolerância, fora.
- `chance_hit(L=30, D=1000, momento em 500, tol=10)`: s ∈ [460, 510] → 50/970.
- dois momentos sobrepostos não contam em dobro (união).
- `D <= L` → 1.0 com momento, 0.0 sem.

### Task 3: Avaliação de um VOD

**Produces:** `evaluate_vod(segments, gabarito, duration, ks=(5, 10), tol=10.0) -> dict` com, por K: `k_efetivo, acertos, precisao, precisao_acaso, lift, recall, recall_acaso, semeados_pelo_gabarito`.

Testes: 10 clipes sintéticos, gabarito com 3 momentos, top-5 com 2 acertos → precisão 0,4; ordenação por `rank` (não por posição); `k_efetivo` quando há menos clipes; vazamento contado; `sem_gabarito` devolve `status` sem métricas.

### Task 4: Carga de projetos, deduplicação e `run_benchmark`

**Produces:**
- `youtube_id(url) -> str | None`
- `load_project(workdir) -> dict | None` (precisa de `segments.json`; heatmap de `source_meta.heatmap`, senão `<projeto>/heatmap.json`)
- `run_benchmark(projects_dir, out_dir, *, date=None, label=None, ks=(5,10), tol=10.0) -> dict` → grava `out_dir/<date>[-<label>].json` e `out_dir/gabaritos/<video_id>.json`; dedup por vídeo ficando com o `updated` mais recente; média só dos VODs com gabarito; `health.record(workdir, "benchmark_gabarito", "ok"|"na", ...)`.

Testes com `tmp_path`: dois projetos do mesmo vídeo (fica o mais novo), um sem gabarito (fora da média, listado), arquivo de saída e gabarito gravados, saúde registrada.

### Task 5: `fetch_labels` (rede sob pedido) + CLI

**Produces:** `fetch_labels(workdir, *, runner=None, gate=None) -> dict` — passa pelo `gate_project_source`; executa o yt-dlp do minerador uma vez (comentários + heatmap no mesmo JSON); grava `comment_seeds.json` (se ainda não existe) e `heatmap.json`; nunca toca `project.json`, `candidates.json`, `segments.json`. CLI: `python -m picorte.engine.benchmark run|fetch-labels`.

Testes: runner falso → arquivos gravados e seleção intocada; portão bloqueando → nada gravado, status `bloqueado_p1`.

### Task 6: Verificação

- [ ] `python -m pytest -q` (esperado: 594 + novos, todos verdes).
- [ ] `python -m picorte.engine.benchmark run --label baseline` nos projetos reais.
- [ ] Sem commit (regra 1 do CLAUDE.md): só com pedido do dono.
