# Handoff — Sessão 05 → Sessão do Code Review do Motor (Épicos 3, 3.5, 3.6 e 3.7)

**Data:** 2026-11-22 · **De:** sessão do motor (Claude Code, worktree `motor-3-6-2`) · **Para:** a nova sessão de code review
**Missão da nova sessão:** revisar **todo o motor de corte**, do Épico 3 (início) até a Story 3.7.5, achar defeitos reais e corrigir o que o dono aprovar. Não é para implementar funcionalidade nova.

---

## 1. Contexto em 1 minuto

- **Picorte** (repo `projeto-cortes`) é uma máquina **local e de uso próprio** que transforma lives e VODs de games em cortes para Shorts, YouTube Longo, TikTok, Reels e Facebook. Primeiro canal: **Bomba Clips**. **Não é SaaS.**
- **Ambiente:** Windows 11 (RTX 4060 Ti 8 GB) e Linux (notebook). **Python global, sem `.venv`.** Node 22. Todo código roda nos dois sistemas (`AD-11`: `pathlib`, `filelock`, filtros FFmpeg iguais).
- **Regras do `CLAUDE.md` que pesam aqui:**
  - conversar em **português do Brasil**, direto e honesto;
  - **nunca commitar, dar push ou apagar sem pedido explícito** do dono (uma autorização vale só para aquela ação);
  - nada de ferramenta de autoclip paga;
  - toda etapa que custa dinheiro tem **estimativa antes**;
  - skill de terceiros só com aprovação (regra 9);
  - o **P1** (risco de direitos autorais) é portão obrigatório e inegociável.
- **Pilares:** `_bmad-output/planning-artifacts/pilares.md` (`P1 > P2 > P3 > P4 > P5`, anti-pilares `A1`–`A5`).
- **Convenção da arquitetura:** **"sinal só vale se medido"**. Nada pode falhar em silêncio: cada parte grava em `engine_health.json` (`picorte/engine/health.py`) com `ok` / `na` / `failed` + motivo.

## 2. Estado do repositório

| | |
|---|---|
| **`main` local** | `6f5de7f` — tem **tudo**: motor (3.6.2–3.6.5, 3.7.1–3.7.5) + painel (6.3–6.8) + correção AD-10 |
| **`origin/main`** | `d6974ba` — **nada foi empurrado**; o `main` local está 27 commits à frente |
| **Branches do motor** | `motor/3-6-2` … `motor/3-7-5`, `integracao/motor-painel` (todos já dentro do `main`) |
| **Branch do painel** | `painel/estudio-6-3-a-6-6` (já dentro do `main`) |
| **Worktree** | `.claude/worktrees/motor-3-6-2` — usada pela sessão do motor; o checkout principal `C:/Dev/projeto-cortes` está no branch do painel |

**Suíte de testes no `main`: 1027 passam, 1 falha.**
A única falha é **de ambiente, só na worktree**: `test_skill_picorte_operador_exists_and_is_linked`. Na worktree os symlinks de `.claude/skills/` viram arquivos de texto de 26 bytes; no checkout principal são links de verdade e o teste passa. **Não tente "consertar" isso no código.**

Rodar a suíte: `python -m pytest tests -q` (leva ~2 min; alguns testes usam GPU e FFmpeg de verdade).

## 3. O que o motor faz hoje (mapa por etapa)

O caminho de um VOD é: **baixar → transcrever → `discover` → `select` → `render`**. Os dois arquivos grandes são `score_clips.py` (2.687 linhas, descoberta e seleção) e `render_clips.py` (1.398 linhas, render), com `projects.py` (811) orquestrando.

**Descoberta (`score_clips.discover`):**
1. evidências de áudio por segundo (`evidence.py` → `audio_features.npz`);
2. candidatos por frase e por mídia, com escada de durações;
3. **Sismógrafo do chat v2** (`chat_seismic.py`): anti-spam por autor, tipo de reação, atraso do chat calibrado por correlação com o áudio, janela da causa;
4. sementes de heatmap do YouTube e de comentários com horário (`comments_miner.py`);
5. visão de games (`visual_games.py`, `hud_detector.py`, `reaction_layout.py`): facecam, MAR, HUD;
6. fusão 4D + snap de bordas; prosódia (riso/susto, `prosody_events.py`);
7. **silêncio digital** (`confidence.py`): trecho mudo não vira corte (P1); falha técnica marcada pelo chat.

**Seleção (`score_clips.select`):**
1. **Recall multi-pista** (`multitrack.py`): 6 pistas com cota (batedor, vacilo/mico, detetive, sério, coop, energia) para o momento quieto não ser esmagado pelo barulhento;
2. **Full-VOD Scout** (`llm_scout.py`): a IA lê a transcrição inteira em blocos;
3. **Editor-Chefe v2** (`llm_router.py`): 12 arquétipos, 3 tiers, bordas por frase, ordem embaralhada com 2ª passada;
4. **regra do ouro com 2 sinais** e `standalone` (`confidence.py`);
5. **fim após o riso** e **Seamless Loop** (`prosody_events.py`, `retention_engine.py`);
6. **formatos irmãos** (`formats.py`): versão TikTok 60–75 s e proposta de Longo 16:9;
7. **compostos** (`composites.py`): arcos de 2 atos e compilações por arquétipo.

**Render (`render_clips.render`):**
1. enquadramento 9:16 com **layout dinâmico** História/Reação/Ação + Sniper Crop (`reframe_games.py`);
2. legenda `.ass`, faixa de contexto 2 s, selo de título;
3. **Selo Verde 15s** (P1, `risk_shield/green_seal_15s.py`): bleep de palavrão;
4. **freeze + seta** no momento-chave (`edit_effects.py`);
5. **Cold Open** colado no 0:00 (`retention_engine.py`);
6. thumbnail, remoção de música (`Demucs`) e **veredito P1** (`risk_shield/pipeline.py`).

## 4. O que cada épico entregou

- **Épico 3** — multimodal 4D, visão de games, engenharia de retenção (3.1–3.5).
- **Épico 3.5** — motor de caça extraordinária: 10 arquétipos, recall multi-pista, Full-VOD Scout, Editor-Chefe v2, arcos e compilações (3.5.1–3.5.5).
- **Auditoria de 2026-11-20** (`_bmad-output/implementation-artifacts/auditoria-e3-done-vs-ligado-2026-11-20.md`): achou o padrão **"done no papel, desligado no pipeline"** (A1–A12). Parte foi religada na etapa 1b; o resto virou os Épicos 3.6 e 3.7.
- **Épico 3.6 (seleção calibrada e medida)** — 3.6.1 gabarito automático e Precision@K; 3.6.2 Sismógrafo 2.0; 3.6.3 arquétipos `nobada_vacilo` e `mico_constrangimento`; 3.6.4 bordas por frase, fim após o riso e Editor sem viés de ordem; 3.6.5 silêncio digital, ouro com 2 sinais e nota de confiança. **A 3.6.6 (pesos calibrados) foi adiada** porque o gabarito é fraco.
- **Épico 3.7 (formato que retém)** — 3.7.1 Cold Open e Seamless Loop renderizados; 3.7.2 layout dinâmico e Sniper Crop; 3.7.3 par Short↔Longo com sobreposição real e versão TikTok; 3.7.4 arcos e compilações renderizados; 3.7.5 freeze e seta. **Épico 3.7 concluído.**

Os planos de cada história estão em `docs/superpowers/plans/2026-11-2*.md`, **cada um com uma seção "Resultado"** no fim, onde estão os desvios de critério e o que a olhada nas lives mostrou. **Leia-os antes de julgar uma decisão de desenho:** vários "pareceres estranhos" já têm motivo escrito lá.

## 5. Decisões do dono que o review deve respeitar

1. **Sem re-medição de Precision@K a cada história** (2026-11-22). A régua de comentários é fraca; a medição de verdade vem das métricas pós-publicação (Épico 7).
2. **Layouts de games = "jogo protagonista"**: História 640 px de rosto, Reação 960, Ação em tela cheia com PiP.
3. **HyperFrames** (efeitos animados) **não entra nos cortes normais**; vai para a **Story 5.5** (formatos especiais de evento, Épico 5). A prova de conceito deu ~10–13 s por efeito.
4. **Ordem de trabalho:** este code review vem **depois** do 3.7 e **antes** do Épico 5.
5. **Arquivos espelho:** `score_clips`, `projects`, `ingest`, `render_clips`, `chopify` e `download_and_transcribe` existem na raiz **e** em `picorte/engine/`, e precisam ficar **idênticos** (`cmp`). O `dashboard.py` diverge de propósito. Isso é dívida conhecida (W1), não um achado novo.

## 6. Fraquezas já conhecidas (não gaste o review re-achando)

Todas estão em `_bmad-output/implementation-artifacts/deferred-work.md`, com detalhe e número. Resumo do que é do motor:

| | |
|---|---|
| **Medição** | W17 (3.6.2 sem ganho medido), W20 (gabarito fraco), W26 (live longa com P@5 0), W31 (regra do ouro rebaixa 70% no modo cego) |
| **Editor-Chefe / IA** | W18 (lote de 28 candidatos, Qwen 16% na CPU), W19 (JSON inválido determinístico), W22 (batedor sem teto de custo), W23 (stderr do Gemini escondido), W29 (2ª passada custa 2–3 min) |
| **Sinais** | W21 (chat gigante sem picos), W25 (Whisper traduz cutscene), W27 (pista vacilo acha pouco), W28 (riso no fim quase não dispara), W30 (silêncio digital pega noise gate), W35 (layout decide por movimento, não expressão) |
| **Formato** | W33 (Cold Open em 12 de 92 cortes), W34 (loop mede só volume), W36 (família pHash depende de quem registra), W37 (sem replay lento), W38 (arco de 2 atos ruidoso), W39 (compilação precisa de Shorts curtos), W40 (seta aponta o centro) |
| **Resolvidas** | W3 (Cold Open renderizado, 3.7.1), W4, W9, W41 |

## 7. Missão do review

**Escopo:** o motor, do Épico 3 até a 3.7.5. Cerca de **12,7 mil linhas** em:

```
score_clips.py (2687)          render_clips.py (1398)      projects.py (811)
ingest.py (590)                picorte/ai/llm_router.py (822)   picorte/ai/llm_scout.py (363)
picorte/engine/: benchmark (619), evidence (570), multitrack (497), retention_engine (453),
  reframe_games (443), chat_seismic (422), visual_games (345), prosody_events (274),
  reaction_layout (242), sections (211), composites (200), multimodal_keyframes (199),
  comments_miner (190), hud_detector (186), confidence (166), snap_boundaries (143),
  edit_effects (133), tighten (133), formats (99), two_act_arc (97), activity_segmenter (93),
  semantic (94), archetype_compiler (75), captions (72), health (66)
```

**Fora do escopo:** `picorte/web/`, `picorte/api/`, `picorte/services/` e `estudio.py` (painel, Épico 6 — tem review próprio); `picorte/risk_shield/` só onde o motor o chama.

**O que procurar, em ordem de importância:**
1. **Defeito que faz o motor escolher ou cortar errado** (bordas, índices, unidades de tempo, divisão por zero, ordenação instável).
2. **Falha em silêncio** — qualquer `except` que engole erro sem gravar na saúde. Essa é a doença crônica do projeto (A1 da auditoria).
3. **Portão P1 contornável** — um caminho que gere ou exporte corte sem veredito, sem Selo Verde ou de fonte não autorizada. Prioridade máxima.
4. **Quebra de multiplataforma (AD-11)** — caminho fixo, `fcntl`, shell, filtro FFmpeg que só roda no Windows.
5. **Espelhos fora de sincronia** (`cmp` nos 6 pares).
6. **Teste que não prova nada** — que passa com o código quebrado, ou depende de ordem e de sorte (já achamos 2 assim: ver 3.7.1).
7. **Custo sem teto** — chamada de LLM paga sem estimativa (regra 6).

## 8. Como fazer (skills)

O `CLAUDE.md` diz que **o `superpowers` lidera a implementação dos épicos, incluindo code review**. O plano do motor (memória `plano-qualidade-motor-e3`) marcou a etapa 4 como **`bmad-code-review`**. Sugestão de uso:

1. **`bmad-code-review`** — dispara vários revisores independentes em paralelo e tria os achados. É o carro-chefe aqui, porque o escopo é grande demais para uma leitura só. Rode **por fatia** (sugestão: descoberta → seleção/IA → render/formato → P1 e testes), e não tudo de uma vez.
2. **`superpowers:systematic-debugging`** — obrigatória antes de propor conserto de qualquer defeito. Nada de "acho que é isso".
3. **`superpowers:test-driven-development`** — todo conserto nasce de um teste que falha antes e passa depois.
4. **`superpowers:verification-before-completion`** — nada é declarado pronto sem a saída do comando colada.
5. **`cortes-pilares` (modo Julgar)** — se o review propuser mudança de rumo (ex.: desligar um sinal, mudar o P1).
6. **`bmad-testarch-test-review` / `bmad-testarch-trace`** — para julgar a qualidade da suíte e a cobertura dos portões críticos.
7. **`claude-api`** — antes de qualquer decisão sobre modelo pago, prompt ou custo de token.

**Opção do dono:** `/code-review ultra` roda uma revisão multiagente na nuvem. **Só o dono pode disparar** (é cobrada); a sessão não deve tentar.

**Atenção à GPU:** o PC tem uma placa de 8 GB. Se a sessão do painel estiver rodando, **não** rode a suíte completa nem nada de GPU ao mesmo tempo (memória `nao-competir-com-sessao-do-motor`). Confira com `nvidia-smi` e `ollama ps`.

## 9. Entrega esperada

1. **Relatório triado** por gravidade, com arquivo e linha, o que quebra na prática e como reproduzir. Separar: **defeito real** × **dívida conhecida (W…)** × **gosto pessoal**.
2. **Nada de conserto sem aprovação do dono.** Mostre a lista, deixe ele escolher o que entra.
3. **Consertos por TDD**, um commit por tema, **só quando o dono pedir o commit**.
4. **Pendência nova** vai para o `deferred-work.md` como `W42`, `W43`…
5. Ao fim, atualizar `sprint-status.yaml` e escrever o `handoff-sessao-06.md`.

## 10. Primeiros comandos

```bash
cd C:/Dev/projeto-cortes          # checkout principal (está no branch do painel)
git switch main                   # main = 6f5de7f, tudo junto
python -m pytest tests -q         # esperado: 1028 passam (no principal o teste de skill passa)
cmp score_clips.py picorte/engine/score_clips.py   # e os outros 5 pares
```

Leia antes de começar: este handoff, `_bmad-output/implementation-artifacts/deferred-work.md`, a auditoria de 2026-11-20 e os planos em `docs/superpowers/plans/2026-11-2*.md` (as seções "Resultado").
