# 3.6.5 — Silêncio Digital, Ouro com 2 Sinais e Nota de Confiança — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o motor não escolhe trechos mudos, o tier `ouro` exige prova de mais de um sinal, cada corte diz se se entende sozinho, e cada projeto diz quanto dá para confiar na seleção.

**Architecture:**
- Um módulo novo, `picorte/engine/confidence.py`, concentra 4 funções puras: os trechos de silêncio digital, a fração de silêncio de um corte, os sinais independentes de um candidato e a confiança do projeto.
- O `score_clips.discover` descarta candidatos mudos e marca a falha técnica.
- O `score_clips.select` aplica a regra do ouro, separa os cortes que não se entendem sozinhos e grava a confiança do projeto na saúde.
- O heatmap vira bônus fraco nos Shorts e bônus forte no vídeo longo.

**Tech Stack:** Python 3.12 global, numpy (já usado), pytest.

**Spec:** `_bmad-output/planning-artifacts/epics.md` → Story 3.6.5.

## Global Constraints

- Espelhos: `score_clips.py` (raiz) = `picorte/engine/score_clips.py`.
- AD-11; "sinal só vale se medido".
- **P1:** trecho mutado (música removida pelo YouTube, queda da live) não vira corte; a saúde registra "trecho mutado/sem áudio".
- **Desvio de medida (achado no mapeamento):** o AC1 fala em "≤ −90 dB", mas o cache de áudio (`evidence.SILENCE_DB = −80`) trava o volume em −80 dB, e nenhum segundo fica abaixo disso. Silêncio digital passa a ser "colado no piso" (≤ −79,5 dB) por ≥ 2 s, que é o mesmo fenômeno (áudio zerado). O áudio real de gameplay fica bem acima: o mínimo na `4Lo5m9WlD6w` foi −52 dB.
- Custo novo: zero. O campo `standalone` vai na mesma resposta do Editor-Chefe.
- Sem re-medição de P@K por história (decisão do dono, 2026-11-22).

---

### Task 1: silêncio digital (AC1)

**Interfaces — produz** (`confidence.py`):
- `digital_silence_ranges(rms_db, *, floor_db=-79.5, min_s=2.0) -> list[tuple[float, float]]`;
- `silence_fraction(start, end, ranges) -> float`;
- `DIGITAL_SILENCE_MAX_FRACTION = 0.20`.

**No `discover`:**
- os trechos vêm do `timeline.rms` já medido;
- candidato com > 20% de silêncio digital é descartado;
- grava `digital_silence.json` (os trechos);
- saúde `silencio_digital`: "ok" com "N trechos mutados/sem áudio; M candidatos descartados (P1)", ou "na" quando não há trecho mudo.

- [ ] Testes:
  - rms sintético com 3 s no piso → 1 trecho;
  - 1 s no piso → nenhum;
  - fração exata;
  - a função de filtro descarta 25% e mantém 10%.

### Task 2: falha técnica (AC2)

**Interfaces — produz:** `tag_technical_failures(candidates, ranges, chat_messages, delay_s) -> list`. Um candidato que contém o **fim** de um silêncio digital, e cujo chat em `[fim, fim+delay+30]` traz "caiu", "travou", "F" (sozinho), "lag" ou "voltou", ganha `tags += ["falha_tecnica"]` e `archetype_hint = "chat_trolagem"` (sem arquétipo novo; #16 bastidores ao vivo).

- [ ] Testes: com chat "caiu a live?" → tag; sem chat → sem tag; o chat "F" sozinho conta.

### Task 3: ouro com 2 sinais + confiança do projeto (AC3, AC5)

**Interfaces — produz:**
- `independent_signals(cand) -> list[str]`, sobre o que foi medido:
  - `riso`: laugh ≥ `LAUGH_MIN`;
  - `susto`: jumpscare_db > 0;
  - `chat`: chat_measured e (chat ≥ 6 ou chat_reaction);
  - `visao`: vision_measured e visual_games ≥ 6,5;
  - `hud`: hud ≥ 5;
  - `comentario`: comment_hint;
  - `heatmap`: seed `heatmap_peak` ou `near_heatmap`;
  - `batedor`: track `full_vod_scout`;
  - `fala`: track léxico (detetive, sério, coop, vacilo) ou `archetype_hint`.
- `enforce_gold_rule(cands) -> int`: `ouro` com < 2 sinais vira `forte` (`ouro_rebaixado` traz o motivo). Devolve quantos caíram.
- `project_confidence(health) -> dict`: `{"sinais_ok": [...], "sinais_ausentes": [...], "sinais_falhos": [...], "nota": 0–1}`, sobre as partes de sinal da saúde (transcrição, prosódia, chat, visão, comentários, heatmap, Editor-Chefe e batedor). Fica gravado em `engine_health.json` como `confianca_projeto`, com o mesmo formato das outras partes e o detalhe em JSON.

- [ ] Testes:
  - ouro com só a nota do Editor → `forte`;
  - ouro com chat e riso → mantém;
  - confiança com 3 ok e 1 falho → nota e listas certas.

### Task 4: `standalone` (AC4)

- Prompt: `"standalone": float 0–10 ("dá para entender sem conhecer o streamer?")`.
- `_apply_entries` grava esse valor.
- No `select`: um corte com `standalone < 5` sai do `segments.json` (Short isolado) e vai para `longo_compilacao.json`, com o motivo. Sem o campo, nada muda.

- [ ] Testes: o parser guarda o campo, e a separação move só os < 5.

### Task 5: heatmap rebaixado (AC6)

- Semente `heatmap_peak`: overall `7.4 + 1.5·v` → `6.6 + 0.6·v` (bônus fraco; deixa de dominar a pista de energia).
- `multitrack`: bônus de proximidade do heatmap de **+0,3 em Short** (< 180 s) e **+1,2 no Longo** (≥ 180 s, para escolher o miolo); grava `near_heatmap`.

- [ ] Testes: a nota da semente do heatmap ficou mais baixa; o bônus em Short é 0,3 e no Longo é 1,2.

### Task 6: verificação

- [ ] Suíte, espelhos, sprint-status 3.6.5 → `done`, olhada do dono (trechos mudos e ouros rebaixados das 4 lives, sem IA), commit só com pedido.

## Resultado (2026-11-22)

- `picorte/engine/confidence.py` com silêncio digital, falha técnica, sinais independentes, regra do ouro, `standalone` e confiança do projeto; tudo ligado no `discover` e no `select`; a saúde ganhou `silencio_digital`, `ouro_2_sinais`, `confianca_projeto` e o `ok` do `full_vod_scout`.
- **Furo de desenho achado pelo teste da geladeira:** os sinais eram contados pela pista que pegou o candidato, e o achado do batedor perdia a fala de detetive e o heatmap. Agora a fala é medida pelo conteúdo, e os achados do batedor também são marcados perto do heatmap. O callback quieto volta a ser ouro, com 3 sinais.
- **Furo da 3.6.4 corrigido aqui:** os campos `confianca_baixa` e `ordem_ajustes` não chegavam ao `segments.json` (a lista de campos permitidos não os tinha). Entraram junto com `standalone`, `sinais_independentes`, `ouro_rebaixado`, `tags` e `archetype_hint`.
- **Olhada nas 4 lives (sem IA):** silêncio digital em 2 lives (~3% da live; 3 cortes atuais cairiam, W30); a regra do ouro rebaixaria 23 de 31 ouros no modo cego (W31); confiança do projeto entre 0,43 e 0,57.
- Suíte: 765 passam (19 novos); 1 falha conhecida, só de ambiente, na worktree.
