# Proposta de Mudança de Sprint — Épico 3.5 (Motor de Caça Extraordinária de Cortes)

- **Data:** 2026-11-19
- **Projeto:** `projeto-cortes` (**Picorte** / canal **Bomba Clips**)
- **Workflow:** `bmad-correct-course` (Modo Incremental) + Portão `cortes-pilares` (Julgar)
- **Veredito dos Pilares (`P1 > P2 > P3 > P4 > P5` e `A1–A5`):** **SEGUE** ✅
- **Classificação de Escopo:** **Moderado (Moderate)** — reorganização de backlog (inserção do Épico 3.5 entre Épico 3 e Épico 4 + enriquecimento direcionado dos Épicos 5, 6 e 7) sem reescrever arquitetura ou pilares.
- **Insumo de origem:** Sessão autônoma de brainstorming [`brainstorm-deteccao-cortes-extraordinarios-games-2026-11-19`](../brainstorming/brainstorm-deteccao-cortes-extraordinarios-games-2026-11-19/brainstorm.html) (112 ideias em 9 técnicas / 7 domínios, 124 entradas no `.memlog.md`).

---

## Seção 1: Resumo do Problema (Trigger)

### 1.1. O que disparou a mudança
Após concluir o Épico 3 e estabilizar a execução local no PC desktop (Windows 11 + RTX 4060 Ti 8 GB, commit local `fd0e93c`), o operador (Bomba) identificou que o motor atual de detecção de cortes ainda falha em capturar **cortes extraordinários e sutis** do nicho gamer — justamente os momentos que mais retêm audiência e diferenciam um canal de cortes de alto nível.

### 1.2. Exemplo-âncora e cobertura desejada
- **Exemplo-âncora:** Short do Alanzoka (`https://www.youtube.com/shorts/E_x5lh7uPCA`) em que ele entra silenciosamente numa cozinha no jogo e testa se a Rockstar corrigiu a animação de pegar um item da geladeira, comparando com o trailer de GTA 6 onde o item "spawna" na mão do Jason — uma **piada oculta / callback cultural** com baixo volume de voz, zero grito e altíssimo valor viral.
- **Cobertura completa desejada:** garantir que **nenhum material extraordinário fique de fora**, cobrindo desde callbacks culturais silenciosos até caos cooperativo, desabafos sérios/importantes, opiniões polêmicas, rage/tilt clássico, descobertas de detalhes, clutches/fails, sustos, ironia *deadpan* / karma instantâneo e trocas hilárias com o chat.

### 1.3. Causas-raiz comprovadas no código e nos logs reais
1. **Funil único enviesado por volume (`score_clips.py`):** a pré-seleção usa uma soma ponderada única que favorece áudio alto e envia apenas `deduped[:30]` para `LLMRouter.rerank_candidates()`, descartando momentos sutis, culturais ou sérios antes de a IA sequer lê-los.
2. **Prompt genérico e cego de contexto (`picorte/ai/llm_router.py`):** `COMPANION_SYSTEM_PROMPT` tem apenas 4 linhas genéricas, sem taxonomia de arquétipos, sem exemplos ouro (*few-shot*), sem metadados do vídeo (título/canal/capítulos), sem dossiê cultural do jogo e sem `pre_context`/`post_context`.
3. **Penalização indevida de dêiticos visuais (`score_clips.py`):** `ANAPHORIC_OPENERS` penaliza falas começando com `"olha isso"`, `"espera"`, `"ele"`, que em lives de games são pistas de ouro apontando algo na tela.
4. **Bugs estruturais observados em produção (`19059a3dc07d`):**
   - `[vision 1/12 .. 12/12]` processou **11 janelas sobrepostas do mesmo minuto (`1609s–1649s`)** porque a deduplicação temporal (NMS) não rodava antes do loop de visão (`score_clips.py:1824`);
   - `hud_detector.py` pontua detecções COCO da classe `PERSON` como evento de HUD, saturando `hud_score = 10.0` em cenas comuns.
5. **Descarte de sinais gratuitos do YouTube (`ingest.py`):** `probe_source` ignora `heatmap` (*Most Replayed*) e `chapters` já retornados pelo `yt-dlp`.

---

## Seção 2: Análise de Impacto

### 2.1. Veredito do Portão de Pilares (`cortes-pilares` — Modo Julgar)
- **P1 (Escudo Anti-Strike):** preservado integralmente. Nenhum download de fonte `desconhecida`; comentários e `heatmap` são opcionais e só para fontes autorizadas; Épico 4 continua obrigatório antes de qualquer publicação.
- **P2 (Qualidade/Transformação Real):** fortemente fortalecido — eleva a taxa de descoberta de momentos genuínos e adapta a narrativa/visual ao arquétipo.
- **P3 (Cérebro que Aprende):** fortalecido — introduz a taxonomia canônica de 10 arquétipos + 3 tiers que alimentará `bandit_state` e `dataset_rotulado/` no Épico 7.
- **P4 (Autonomia com Controle):** preservado — modos *Query-Driven* e *Deep Hunt* dão controle direto via CLI/MCP/UI sem criar atrito na operação padrão.
- **P5 (Local/Grátis Primeiro + Multiplataforma AD-11 + VRAM Serial AD-3):** preservado — sinais leves em CPU, LLM via roteador existente (`Ollama`/`Claude`/`Gemini`/`Dupla`), zero ferramenta paga de autoclip, compatível com Windows 11 e Linux Ubuntu.
- **Anti-pilares (`A1–A5`):** nenhuma violação (zero SaaS, zero Jump-Cut + Compressor, zero automação com senha, zero disfarce de copyright).
- **Decisão:** **SEGUE** ✅.

### 2.2. Impacto nos Épicos e Histórias
| Épico | Impacto | Resumo |
|---|---|---|
| **Épicos 1, 2, 3** | Sem rollback | Trabalho concluído e verificado (`376 passed`, commit `fd0e93c`) permanece intacto como base. |
| **Novo Épico 3.5** | **Adicionado** (antes do Épico 4) | 5 histórias divididas em **Onda 1** (`3.5.1`–`3.5.3`, impacto imediato) e **Onda 2** (`3.5.4`–`3.5.5`, precisão avançada + narrativa) + documento técnico dedicado [`epic-3-5-motor-caca-extraordinaria.md`](epic-3-5-motor-caca-extraordinaria.md). |
| **Épico 4** | Sem alteração de escopo | Continua intacto logo após o Épico 3.5 como portão P1 obrigatório pré-publicação. |
| **Épico 5** | **Enriquecido (Onda 3)** | Stories `5.1` e `5.3` ampliadas + nova Story `5.4` (`streamer_profiles.py`), incorporando Tendências 48h, Modo Day-1 (72h) + auto-atualizador de dossiês, Consenso Cross-Streamer do Mesmo Dia e Memória de Piadas Internas. |
| **Épico 6** | **Enriquecido (Onda 3)** | Story `6.3` ampliada com filtros/badges acessíveis de 10 arquétipos + 3 tiers, UI de *Query-Driven Clipping* e *Deep Hunt*, galeria de `_thumb.png` e curadoria de `golden_examples.json` / `game_dossiers/`. |
| **Épico 7** | **Enriquecido (Onda 3)** | Stories `7.2` e `7.3` atualizadas para usar `archetype` (10) e `tier` (3) em `bandit_state`, adaptar `ab_recycler.py` ao tom do arquétipo, sugerir campeões para `golden_examples.json` e treinar Pré-Classificador Local de Arquétipos em `train_local_scorer.py`. |

### 2.3. Artefatos a Criar / Atualizar
1. **Criar:** `_bmad-output/planning-artifacts/epic-3-5-motor-caca-extraordinaria.md` (blueprint técnico completo do Épico 3.5 cobrindo os 16→10 arquétipos, sinais, contratos JSON, prompts, correções e plano de testes).
2. **Atualizar:** `docs/plano-mestre.md` (inserir Épico 3.5, adicionar Onda 3 nos Épicos 5, 6 e 7, atualizar resumo de decisões).
3. **Atualizar:** `_bmad-output/planning-artifacts/epics.md` (inserir Epic 3.5 com Stories `3.5.1`–`3.5.5` e atualizar Epics 5, 6 e 7).
4. **Atualizar:** `_bmad-output/specs/spec-picorte/companion-pipeline-multimodal.md` (atualizar Seção 2 `CAP-4`/`CAP-5` e nota de estilo na Seção 4).
5. **Atualizar:** `_bmad-output/implementation-artifacts/sprint-status.yaml` (inserir `epic-3-5` + `3-5-1`..`3-5-5` + `5-4`).

### 2.4. Impacto Técnico
- **Espelhamento obrigatório:** alterações em `ingest.py`, `score_clips.py`, `render_clips.py`, `projects.py`, `chopify.py` devem manter sincronia com `picorte/engine/*.py`.
- **VRAM e Multiplataforma (`AD-3`, `AD-11`):** todos os novos módulos em CPU pura ou serializados sob `vram_runner.py`; caminhos via `pathlib.Path`; zero dependência exclusiva de Linux ou Windows.
- **Compatibilidade retroativa:** banco SQLite/Postgres e formatos `.meta.json` existentes continuam válidos (novos campos `archetype`, `tier`, `scout_reason`, `context_window` com fallback seguro).

---

## Seção 3: Abordagem Recomendada

- **Caminho escolhido:** **Ajuste Direto com Divisão em 3 Ondas** — zero rollback do Épico 3, inserção do **Épico 3.5** (Ondas 1 e 2) imediatamente antes do Épico 4, e distribuição explícita da **Onda 3** nos Épicos 5, 6 e 7 para que **100% das 112 ideias válidas do brainstorming tenham destino garantido** sem inflar o escopo atual nem desperdiçar trabalho.
- **Justificativa:** testar e tunar o motor de descoberta *antes* de construir o Escudo P1 (Épico 4) e a automação de caça/publicação (Épicos 5–6) garante que o pipeline já produza cortes extraordinários de ponta a ponta desde o primeiro VOD real.
- **Esforço e risco:**
  - **Onda 1 (`3.5.1`–`3.5.3`):** risco baixo, impacto imediato (já resolve os bugs reais e captura o caso Alanzoka/GTA 6 + todos os 10 arquétipos).
  - **Onda 2 (`3.5.4`–`3.5.5`):** risco baixo-médio (visão seletiva + áudio avançado opcional com fallback limpo se YAMNet/PANNs não estiver instalado).
  - **Onda 3 (Épicos 5–7):** risco zero agora — nasce organicamente quando cada épico correspondente for executado.

---

## Seção 4: Propostas Detalhadas Aprovadas (Modo Incremental)

Todas as 5 propostas foram revisadas individualmente e **aprovadas** pelo operador em 2026-11-19:

### Proposta 1/5 — Novo Épico 3.5 + Documento Técnico Dedicado (`APROVADA` ✅)
- **Alvos:** `docs/plano-mestre.md`, `_bmad-output/planning-artifacts/epics.md`, novo `_bmad-output/planning-artifacts/epic-3-5-motor-caca-extraordinaria.md`.
- **Taxonomia canônica (16 arquétipos do brainstorm operacionalizados em 10 arquétipos + 3 tiers):**
  - Arquétipos: `callback_oculto`, `caos_coop`, `rage_tilt`, `serio_realtalk`, `polemica_hottake`, `descoberta_detalhe`, `clutch_fail`, `susto_tensao`, `deadpan_karma`, `chat_trolagem`.
  - Tiers: `ouro`, `forte`, `experimental`.
- **Onda 1 (Fundação de Precisão + Caça Completa):**
  - **Story `3.5.1`:** Correções estruturais (NMS temporal pré-visão, remoção de `PERSON` no `hud_detector.py`, revisão de `ANAPHORIC_OPENERS`) + ingestão de `heatmap` (*Most Replayed*) e `chapters` no `ingest.py`.
  - **Story `3.5.2`:** Recall Multi-Pista com 5 pistas de cota reservada + *Payoff-First Rewind* + **Full-VOD Narrative Scout (`llm_scout.py`)** retornando `sentence_id` + escada de durações flexíveis (`8–14s`, `15–59s`, `60–120s`, `120–300s`).
  - **Story `3.5.3`:** **Editor-Chefe v2** (`llm_router.py`) com prompt dos 10 arquétipos/3 tiers, `golden_examples.json`, `game_dossiers/` (incluindo `gta6.json`), `pre_context`/`post_context`, diversificação MMR e validação contra o caso-âncora.
- **Onda 2 (Sensores Ricos + Narrativa Avançada):**
  - **Story `3.5.4`:** Visão seletiva (3 keyframes em dêiticos visuais), mineração opcional de timestamps em comentários do YouTube, prosódia avançada (ritmo de risada, silêncio pré-explosão, classificador acústico opcional YAMNet/PANNs com fallback), facecam rica (`gaze-to-camera`, mão no rosto/facepalm) e segmentação de atividade do VOD.
  - **Story `3.5.5`:** Arcos narrativos de 2 atos (*setup → payoff* separados), compilação por arquétipo, adaptação de estilo/faixa de contexto por arquétipo, **Busca por Pergunta Livre (*Query-Driven Clipping*)**, **Modo Caça Profunda (*Deep Hunt*)** e auto-atualizador CLI/MCP de `game_dossiers/`.

### Proposta 2/5 — Atualização do Épico 5: Olho para Fora (`APROVADA` ✅)
- **Alvos:** `docs/plano-mestre.md` (Épico 5), `_bmad-output/planning-artifacts/epics.md` (Stories `5.1`, `5.3` e nova `5.4`).
- **Mudanças:**
  - `trend_radar.py` (`5.1`): Cruzamento com Tendências Externas (48h) injetadas no Scout + Detector de Momentos Históricos Day-1 (janela 72h) acoplado ao Auto-Atualizador de `game_dossiers/`.
  - `storyline_detector.py` (`5.3`): Consenso Cross-Streamer do Mesmo Dia (3+ fontes reagindo ao mesmo detalhe/cena em 24h → boost automático + sugestão de compilação).
  - Novo `streamer_profiles.py` (`5.4`): Perfis Adaptativos e Memória de Piadas Internas (*running gags*, bordões, baseline por fonte autorizada) injetados no Scout e Editor-Chefe.

### Proposta 3/5 — Atualização do Épico 6: Painel "Estúdio do Criador" (`APROVADA` ✅)
- **Alvos:** `docs/plano-mestre.md` (Épico 6, Item 4), `_bmad-output/planning-artifacts/epics.md` (Story `6.3`).
- **Mudanças:**
  - Badges e filtros acessíveis (ícone + texto, WCAG AA) dos **10 arquétipos** e **3 tiers (`Ouro / Forte / Experimental`)** na Fila e Revisão Rápida.
  - Interface de **Busca por Pergunta Livre (*Query-Driven Clipping*)** e alternador de **Modo Caça Profunda (*Deep Hunt*)**.
  - Galeria de Thumbnails (`_thumb.png`), botão de 1 clique **"Salvar como Exemplo Ouro"** (`golden_examples.json`) e editor enxuto para `game_dossiers/` e `streamer_profiles`.

### Proposta 4/5 — Atualização do Épico 7: O Cérebro que Aprende (`APROVADA` ✅)
- **Alvos:** `docs/plano-mestre.md` (Épico 7, Itens 3–5), `_bmad-output/planning-artifacts/epics.md` (Stories `7.2`, `7.3`).
- **Mudanças:**
  - `contextual_bandit.py` (`7.2`): substitui `tipo_momento` genérico por `archetype` (os 10 arquétipos) e `tier` em `bandit_state`; `ab_recycler.py` respeita o tom editorial do arquétipo na Segunda Vida.
  - `active_learning.py` + `train_local_scorer.py` (`7.3`): grava `archetype`/`tier` em `dataset_rotulado/`, sugere campeões (`>= 2.5x` mediana) para `golden_examples.json` e treina **Pré-Classificador Local de Arquétipos** na RTX 4060 Ti (Modo Madrugada) para alimentar o `score_clips.py`.

### Proposta 5/5 — Atualização da Spec (`companion-pipeline-multimodal.md`) e `sprint-status.yaml` (`APROVADA` ✅)
- **Alvos:** `_bmad-output/specs/spec-picorte/companion-pipeline-multimodal.md` (Seção 2 e nota na Seção 4), `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- **Mudanças:**
  - Sincroniza `CAP-4` e `CAP-5` com Recall Multi-Pista (5 pistas), NMS pré-visão, HUD limpo, `heatmap`/`chapters`, Full-VOD Narrative Scout, 10 arquétipos + 3 tiers, `golden_examples.json`, `game_dossiers/`, durações flexíveis (`8–14s` até `120–300s`), visão seletiva, *Query-Driven* e *Deep Hunt*.
  - Registra `epic-3-5` + `3-5-1`..`3-5-5` + `5-4` em `sprint-status.yaml`.

---

## Seção 5: Handoff para Implementação

- **Classificação de Escopo:** **Moderado (Moderate)**.
- **Fluxo de responsabilidade (conforme `CLAUDE.md`):**
  1. **Planejamento / Documentação (BMAD — concluído após aprovação final desta proposta):** gravar `epic-3-5-motor-caca-extraordinaria.md` e aplicar todas as atualizações sincronizadas em `docs/plano-mestre.md`, `epics.md`, `companion-pipeline-multimodal.md` e `sprint-status.yaml`.
  2. **Execução das Histórias (`superpowers`):** seguir estritamente **`writing-plans` → `test-driven-development` → `verification-before-completion`**, começando pela **Onda 1 (`3.5.1` → `3.5.2` → `3.5.3`)** e validando num VOD real antes de avançar para a **Onda 2 (`3.5.4` → `3.5.5`)**.
- **Critérios de Sucesso do Épico 3.5:**
  1. Todos os 376 testes existentes continuam passando + novos testes TDD cobrindo cada história `3.5.1`–`3.5.5`.
  2. Em teste com transcrição/VOD contendo momento silencioso de callback cultural (tipo Alanzoka/GTA 6 geladeira) misturado a momentos de grito/caos, o motor retorna o callback classificado como `callback_oculto` (`ouro`) junto aos demais arquétipos diversificados via MMR.
  3. Zero regressão de tempo de visão (NMS pré-visão garante janelas temporalmente distintas) e zero falso positivo de `PERSON` no `hud_detector.py`.
  4. Compatibilidade 100% preservada entre Windows 11 (RTX 4060 Ti) e Linux Ubuntu (`AD-11`).
