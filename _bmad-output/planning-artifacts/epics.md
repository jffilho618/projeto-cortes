---
title: 'Épicos e Histórias — Picorte (Plano Mestre Evolutivo v2)'
status: final
created: '2026-11-18'
updated: '2026-11-21'
sources:
  - ../specs/spec-picorte/SPEC.md
  - ./architecture.md
  - ./pilares.md
  - ./concorrentes.md
  - ./epic-3-5-motor-caca-extraordinaria.md
  - ./sprint-change-proposal-2026-11-19.md
  - ./sprint-change-proposal-2026-11-21.md
  - ./sprint-change-proposal-2026-11-21-painel.md
---

# Épicos e Histórias — Picorte (`projeto-cortes`)

> Cada Épico entrega o sistema rodando na máquina em um patamar superior ao anterior. A implementação de cada história segue o ciclo do `superpowers` (`writing-plans` → `test-driven-development` → `verification-before-completion`).

---

## Epic 1: Clone Base Rodando na Máquina e Gerando Cortes (MVP Zero)

**Objetivo:** Transplantar o chassi principal do `mehbul/chopify` (MIT) para a estrutura `picorte/engine/`, configurar o ambiente local (FFmpeg com `libass` e `h264_nvenc`, `faster-whisper`, `opencv-python` YuNet, `yt-dlp`) e gerar os primeiros cortes `.mp4` (9:16 e 16:9) com legenda `.ass` palavra a palavra a partir de um vídeo de gameplay real.
**Capacidades cobertas:** `CAP-1` (base), `CAP-5` (base), `CAP-7` (legendas base).
**Regras de Arquitetura:** `AD-1`, `AD-3`, `AD-7`.

### Story 1.1: Ambiente Local, Diagnóstico de GPU e Transplante do Chassi Chopify

**Descrição:**
Como operador, quero o chassi do `mehbul/chopify` e o diagnóstico de GPU do `artbyjazi/autoclip` estruturados no pacote `picorte/` com ambiente virtual `.venv` e `ffmpeg` validados, para que o pipeline rode localmente tanto na GTX 1650 (4 GB) quanto na RTX 4060 Ti (8 GB).

**Origem do código (`referencias/`):**
- `referencias/mehbul_chopify/` (`chopify.py`, `ingest.py`, `sections.py`, `download_and_transcribe.py`, `evidence.py`, `visual.py`, `score_clips.py`, `render_clips.py`, `captions.py`, `branding.py`, `tighten.py`, `projects.py`, `dashboard.py`, `tests/`).
- `referencias/artbyjazi_autoclip/backend/autoclip/cuda.py`.

**Critérios de Aceite (AC):**
1. Ambiente Python `.venv` configurado e `ffmpeg`/`ffprobe` verificados com suporte a `libass` e `h264_nvenc` (com fallback automático para `libx264` quando NVENC não estiver ativo).
2. `picorte/config.py` e `cuda.py` detectam automaticamente a GPU presente e selecionam o perfil seguro de VRAM (`GTX 1650 4GB` → `faster-whisper base/small int8`; `RTX 4060 Ti 8GB` → `faster-whisper large-v3-turbo int8_float16`).
3. Suíte de testes unitários base do chassi (`pytest`) executa e passa 100% verde.

### Story 1.2: Pipeline Ponta a Ponta de Corte 9:16 e 16:9 com Área Segura Unificada

**Descrição:**
Como operador, quero processar um vídeo de gameplay real (arquivo local ou VOD em blocos de áudio de 30m) e exportar cortes verticais (`1080x1920`) e horizontais (`1920x1080`) com legendas `.ass` queimadas dentro da Área Segura Unificada (`AD-7`), para já ter os primeiros cortes prontos para postagem.

**Origem do código (`referencias/`):**
- `referencias/mehbul_chopify/ingest.py`, `sections.py`, `captions.py`, `render_clips.py`.

**Critérios de Aceite (AC):**
1. Fontes longas (+2h) usam o caminho de áudio em blocos de 30 minutos (`sections.py`) e só baixam o vídeo das seções aprovadas.
2. As legendas `.ass` nos cortes `9:16` respeitam obrigatoriamente a caixa segura universal (`x` entre `80px` e `920px`, `margin_v = 450px` da base).
3. O processamento de um vídeo real de teste gera na pasta de saída o `.mp4` renderizado, o poster `.png` e o arquivo `.meta.json` com título, descrição e hashtags.

---

## Epic 2: Banco PostgreSQL, Fila Serializada de VRAM, Roteador de IA na UI e Controle por Agente (MCP)

**Objetivo:** Substituir o estado solto em arquivos JSON pelo banco **PostgreSQL local** (`AD-2`), garantir a execução serializada na VRAM com Modo Madrugada (`AD-3`), implementar o **Seletor de IA de 4 Modos na UI (`Ollama` / `Claude` / `Gemini` / `Dupla`)** (`AD-4`) e expor tudo via **Servidor MCP + Skill** para o Claude Code e o Gemini Antigravity (`AD-10`).
**Capacidades cobertas:** `CAP-5` (roteador IA), `CAP-14`.
**Regras de Arquitetura:** `AD-2`, `AD-3`, `AD-4`, `AD-10`.

### Story 2.1: Schema Canônico PostgreSQL e Camada de Repositórios

**Descrição:**
Como operador, quero o banco PostgreSQL local rodando com as 10 tabelas canônicas (`sources`, `publisher_policies`, `campaigns`, `videos`, `clips`, `publications`, `metrics_snapshots`, `claims_events`, `bandit_state`, `dataset_samples`) e seus repositórios em `picorte/db/`, para guardar todo o histórico e estado do sistema.

**Critérios de Aceite (AC):**
1. `picorte/db/schema.sql` e migração inicial criam todas as 10 tabelas sem colunas de multi-tenant (`workspace_id`).
2. Todo job de vídeo e todo corte gerado pelo motor passam a ser gravados e atualizados em `videos` e `clips` no PostgreSQL.
3. Testes de repositório cobrem CRUD e transações atômicas no PostgreSQL.

### Story 2.2: Orquestrador Serial de VRAM (`vram_runner.py`) e Modo Madrugada

**Descrição:**
Como operador, quero que cada etapa pesada de GPU rode de forma estritamente serializada com limpeza explícita de memória e suporte a janela de Modo Madrugada, para nunca sofrer *CUDA Out of Memory* nos 8 GB da RTX 4060 Ti (nem nos 4 GB da GTX 1650).

**Critérios de Aceite (AC):**
1. `vram_runner.py` aplica `gpu_stage_lock` garantindo que transcrição, visão, separação de áudio e LLM local nunca fiquem alocados simultaneamente na VRAM.
2. Jobs pesados em lote marcados para o Modo Madrugada aguardam a janela de horário configurada ou ociosidade da GPU, podendo ser forçados manualmente quando desejado.

### Story 2.3: Roteador de IA de 4 Modos (`llm_router.py`) com Seletor na UI

**Descrição:**
Como operador, quero escolher diretamente na interface web (e por job) se a inteligência textual usa **Ollama local**, **Claude** (via CLI `claude -p` da assinatura mensal ou API), **Gemini** (via CLI `agy -p` da assinatura mensal ou API) ou o **Modo Dupla ("Um Filtrando + Outro Acompanhando/Lapidando")**.

**Origem do código (`referencias/`):**
- `referencias/artbyjazi_autoclip/backend/autoclip/providers/` + adaptadores CLI (`claude -p`, `agy -p`).

**Critérios de Aceite (AC):**
1. `picorte/ai/llm_router.py` implementa os 4 modos (`ollama`, `claude`, `gemini`, `dupla`) com fallback seguro se um provedor estiver indisponível.
2. No modo `dupla`, o `filter_provider` escolhido faz a triagem inicial dos candidatos e o `companion_provider` escolhido revisa, seleciona os campeões e redige título, faixa de contexto de 2s, texto da thumbnail e 1º comentário.
3. A UI exibe o seletor de motor de IA (modo único ou dupla `Filtro → Acompanhamento`) e grava em `clips.llm_mode_used` qual configuração gerou cada corte.

### Story 2.4: Servidor MCP (`picorte_mcp`) e Skill `picorte-operador`

**Descrição:**
Como operador, quero controlar o Picorte conversando com o Claude Code ou com o Gemini no Antigravity através de ferramentas MCP e da skill `picorte-operador`.

**Origem do código (`referencias/`):**
- `referencias/FujiwaraChoki_supoclip/mcp/src/supoclip_mcp/server.py` + `referencias/mehbul_chopify/docs/AGENT-API.md`.

**Critérios de Aceite (AC):**
1. Servidor MCP expõe ferramentas para listar/alterar fontes, enfileirar vídeos (escolhendo o modo de IA), inspecionar candidatos e suas notas parciais, re-renderizar cortes e checar alertas.
2. Skill `.claude/skills/picorte-operador/SKILL.md` instalada e visível com `/` tanto no Claude Code quanto no Antigravity.

---

## Epic 3: Upgrade Multimodal 4D, Visão Computacional de Games e Engenharia de Retenção

**Objetivo:** Adicionar ao motor de corte o **Sismógrafo do Chat da Live**, os detectores de **Visão Computacional de Games** (Facecam, Micro-Expressões MAR, HUD/Killfeed, Troca Dinâmica de Layout e Sniper Crop) e toda a **Engenharia de Retenção e Formatos** (Cold Open Reverso 1,5s, Faixa de Contexto 2s, Seamless Loop, Compilação Cross-Streamer, Par Short Isca → Corte Longo 3–5 min + Fábrica Automática de Thumbnail e 1º Comentário Fixado).
**Capacidades cobertas:** `CAP-4`, `CAP-5`, `CAP-6`, `CAP-7`, `CAP-8`, `CAP-9`.
**Regras de Arquitetura:** `AD-1`, `AD-3`, `AD-4`, `AD-7`.

### Story 3.1: Sismógrafo do Chat da Live (`chat_seismic.py`)

**Descrição:**
Como operador, quero que o sistema analise o replay/fluxo do chat da live (Twitch, Kick, YouTube) e comentários com timestamp em menos de 2s de CPU para achar explosões de mensagens/segundo e reações (`KKKK`, `LUL`, `CLIP`, `MENTIRA`, `???`).

**Critérios de Aceite (AC):**
1. `chat_seismic.py` calcula a série temporal a 1 Hz de `vel_zscore` e `emote_burst` sobre logs de chat.
2. Picos com `vel_zscore > 3.5` entram automaticamente na lista de candidatos mesmo quando não há diálogo no áudio.

### Story 3.2: Visão Computacional de Games — Micro-Expressões (MAR) e Detector de HUD/Killfeed

**Descrição:**
Como operador, quero que a análise visual detecte automaticamente a abertura da boca/expressão do streamer na facecam (MAR) e eventos de *Kill / Victory / Wasted / Clutch* no HUD do jogo, somando essas notas ao pontuador 4D e ajustando as bordas do corte às pausas da fala.

**Origem do código (`referencias/`):**
- `referencias/mehbul_chopify/visual.py`, `score_clips.py`.
- `referencias/FujiwaraChoki_supoclip/backend/src/media/face_detection.py` (`YuNet`).
- `referencias/AgriciDaniel_claude-shorts/scripts/snap_boundaries.py`.

**Critérios de Aceite (AC):**
1. `visual_games.py` mede `MAR` (*Mouth Aspect Ratio*) e deslocamento brusco da cabeça na região da facecam.
2. `hud_detector.py` detecta eventos de interface de jogo nas regiões de HUD/killfeed/centro da tela.
3. `score_clips.py` combina `S_chat + S_audio + S_visao + S_texto` e aplica `snap_boundaries.py` para nunca cortar palavras ao meio.

### Story 3.3: Enquadramento 9:16 de Games — Layout Facecam+Jogo, Troca Dinâmica e Sniper Crop

**Descrição:**
Como operador, quero que os cortes verticais de gameplay detectem a webcam do streamer no canto da tela e alternem dinamicamente entre os layouts História (`70/30`), Reação (`Split 640px + 1280px`) e Ação (`100% Jogo + PiP`), aplicando zoom suave (*Sniper Crop*) no quadrante onde a ação ocorreu.

**Origem do código (`referencias/`):**
- `referencias/FujiwaraChoki_supoclip/backend/src/media/reaction_layout.py` (`find_reactor_face`).
- `referencias/louisedesadeleer_clipify/scripts/build_pan.py`.

**Critérios de Aceite (AC):**
1. `reframe_games.py` detecta a facecam estacionária com `find_reactor_face` e aplica histerese mínima de 3s nas trocas de layout dentro do mesmo corte.
2. O recorte da região do jogo segue o centroide suavizado do mapa de movimento/saliência (*Sniper Crop*) sem trepidação.

### Story 3.4: Engenharia de Retenção — Cold Open Reverso 1,5s, Contexto 2s, Seamless Loop e Cross-Streamer

**Descrição:**
Como operador, quero que todo corte vertical saia com Cold Open de 1,5s do clímax em `0:00`, faixa de contexto nos primeiros 2s, ponto final conectado em Seamless Loop e suporte a Compilação Cross-Streamer quando múltiplos streamers reagirem ao mesmo evento.

**Origem do código (`referencias/`):**
- `referencias/fralapo_clippyme/src/clippyme/editing/hook_overlay.py`, `banner.py`.
- `referencias/louisedesadeleer_clipify/scripts/audio_align.py`.

**Critérios de Aceite (AC):**
1. `retention_engine.py` insere o ápice de 1,5s em `0:00` e renderiza a pílula de contexto nos primeiros 2s (`y` entre `240px` e `360px`).
2. `cross_streamer.py` alinha por áudio/imagem 2 ou mais vídeos do mesmo evento e gera um corte compilado multi-reação.

### Story 3.5: Par Short Isca + Corte Longo (3–5 min) e Fábrica Automática de Thumbnail

**Descrição:**
Como operador, quero que arcos densos gerem tanto o Corte Longo `16:9` (3–5 min) quanto o Short Isca `9:16` vinculado, acompanhados de uma Thumbnail `1280x720` gerada automaticamente com o frame de maior expressão do streamer recortado (`rembg`), o frame de ação do jogo e tipografia do `DESIGN.md`.

**Critérios de Aceite (AC):**
1. O Short Isca grava `parent_long_clip_id` apontando para o Corte Longo correspondente no PostgreSQL.
2. `thumbnail_factory.py` gera o arquivo `thumbnail.png` (`1280x720`) combinando o frame de maior MAR da facecam (sem fundo via `rembg`), o frame de ação do jogo e texto curto de 2–3 palavras nas fontes `Antonio`/`Archivo`.

---

## Epic 3.5: Motor de Caça Extraordinária — 10 Arquétipos, Recall Multi-Pista, Full-VOD Scout e Editor-Chefe v2

**Objetivo:** Tunar o motor de descoberta do Épico 3 para capturar **todos os 16→10 arquétipos de cortes extraordinários em lives de games** (incluindo callbacks culturais silenciosos como o caso *Alanzoka / geladeira GTA 6*, caos co-op, rage/tilt, real-talk sério, polêmicas, descobertas de detalhe, clutches/fails, sustos, ironia *deadpan* / instant karma e trocas com o chat), corrigindo os gargalos observados em produção e classificando cada candidato em 3 tiers (`ouro`, `forte`, `experimental`).
**Blueprint técnico completo:** [`epic-3-5-motor-caca-extraordinaria.md`](epic-3-5-motor-caca-extraordinaria.md).
**Capacidades cobertas:** `CAP-1` (enriquecida), `CAP-4`, `CAP-5`, `CAP-7`.
**Regras de Arquitetura:** `AD-1`, `AD-3`, `AD-4`, `AD-10`, `AD-11`.

### Story 3.5.1: Correções de Precisão, Heatmap/Capítulos do YouTube, NMS Pré-Visão e HUD Limpo (Onda 1)

**Descrição:**
Como operador, quero persistir `heatmap` (*Most Replayed*) e `chapters` na ingestão, executar NMS temporal antes do loop `[vision 1/12]`, remover falsos positivos `PERSON` do `hud_detector.py` e transformar `ANAPHORIC_OPENERS` em detector de dêiticos visuais, eliminando os gargalos comprovados do motor atual.

**Critérios de Aceite (AC):**
1. `ingest.py::probe_source()` persiste `heatmap`, `chapters`, `title`, `channel` e `detected_game` no `source_meta` e promove picos do *Most Replayed* como sementes candidatas obrigatórias.
2. `temporal_nms()` roda antes do loop `[vision]` em `score_clips.py`, garantindo janelas temporalmente distintas (IoU `<= 0.35`).
3. `hud_detector.py` ignora a classe COCO `person` e a caixa da facecam, eliminando saturação artificial em `hud_score = 10.0`.
4. Dêiticos visuais (`"olha isso"`, `"olha a mão"`, `"espera"`, `"repara"`) deixam de ser penalizados e passam a acionar expansão de setup + marcação `has_visual_deictic=True`.

### Story 3.5.2: Recall Multi-Pista (5 Pistas), Payoff-First Rewind, Full-VOD Narrative Scout e Durações Flexíveis (Onda 1)

**Descrição:**
Como operador, quero acabar com a porta estreita enviesada por volume (`deduped[:30]`) usando 5 pistas com cota reservada, filtro anti-lixo, léxico PT-BR + TF-IDF local + Silêncio Magnético, descoberta *Payoff-First Rewind*, um **Full-VOD Narrative Scout (`llm_scout.py`)** que lê a live inteira por `sentence_id` (com Map-Reduce em lives 4h+) e durações flexíveis (`8–14s`, `15–59s`, `60–120s`, `120–300s`).

**Critérios de Aceite (AC):**
1. `multitrack.py` reserva cotas garantidas nas 5 pistas (Energia/Chat/Heatmap, Full-VOD Scout, Sério/Polêmica/Silêncio Magnético, Dêiticos/Detetive/Callbacks, Caos Co-op/Payoff Rewind), impedindo que momentos silenciosos morram antes do LLM.
2. `llm_scout.py` numera blocos por `sentence_id`, suporta Map-Reduce em VODs longos e converte `start_sid`/`end_sid` em timestamps reais sem alucinar segundos.
3. O motor suporta durações flexíveis incluindo micro-clipes (`8–14s`) e verticais estendidos (`60–120s`), além de filtrar leitura longa de subs/patrocínios/intervalos.

### Story 3.5.3: Editor-Chefe v2, 10 Arquétipos/3 Tiers, `golden_examples.json`, `game_dossiers/` e MMR (Onda 1)

**Descrição:**
Como operador, quero um Editor-Chefe v2 no `llm_router.py` guiado pelo Conselho de 4 Caçadores Especialistas, alimentado por `golden_examples.json`, `game_dossiers/<jogo>.json` (`gta6.json` inicial) e `pre_context`/`post_context`, com diversificação MMR por tempo e arquétipo.

**Critérios de Aceite (AC):**
1. `llm_router.py` classifica candidatos nos **10 arquétipos canônicos** e **3 tiers (`ouro`, `forte`, `experimental`)**, devolvendo `context_banner_2s` (Tradutor de Piada Oculta sem Spoiler), `tone`, `rewatchability`, `shareability` e ajuste fino de bordas.
2. `picorte/ai/golden_examples.json` e `picorte/ai/game_dossiers/gta6.json` são carregados automaticamente (multiplataforma `pathlib.Path`) e injetados no prompt com `pre_context` (20s) e `post_context` (15s).
3. Diversificação MMR garante cobertura distribuída na timeline e variedade de arquétipos no ranking final, e o teste "Benchmark Geladeira do Alanzoka" classifica o caso-âncora como `callback_oculto` (`ouro`).

### Story 3.5.4: Visão Seletiva (3 Keyframes), Comentários do YouTube, Prosódia Avançada, Facecam Rica e Segmentação de Atividade (Onda 2)

**Descrição:**
Como operador, quero validação multimodal seletiva (3 keyframes em dêiticos visuais), mineração opcional de timestamps em comentários do YouTube, detecção em CPU de riso rítmico (`3–6 Hz`), susto (`>18 dB`) e taxa de fala/F0 (com hook opcional YAMNet/PANNs), `gaze-to-camera` / facepalm na facecam e segmentação de atividade do VOD.

**Critérios de Aceite (AC):**
1. `multimodal_keyframes.py` extrai 3 frames em candidatos com dêitico visual ou nota limítrofe e degrada limpo quando o provedor ativo é somente texto.
2. `comments_miner.py` (opcional, respeitando P1) extrai timestamps `mm:ss`/`hh:mm:ss` e descrições humanas de comentários do VOD.
3. `prosody_events.py` e `visual_games.py` expõem riso pulsado `3–6 Hz`, assinatura de susto `>18 dB`, `gaze-to-camera`, facepalm/fuga de quadro e inspeção visual; `activity_segmenter.py` classifica blocos de atividade do VOD.

### Story 3.5.5: Arcos de 2 Atos, Compilação por Arquétipo, Estilo Adaptado, Query-Driven, Deep Hunt e Auto-Atualizador de Dossiês (Onda 2)

**Descrição:**
Como operador, quero montar arcos de 2 atos (*setup → payoff* distantes), compilações temáticas por arquétipo da mesma live, adaptar o estilo de badge/Cold Open ao tom do arquétipo, buscar cortes por pergunta livre (`--query`), alternar entre `Fast Radar` e `Deep Hunt` (`--hunt-mode`) e atualizar `game_dossiers/` via CLI/MCP.

**Critérios de Aceite (AC):**
1. `two_act_arc.py` e `archetype_compiler.py` montam cortes compostos via FFmpeg compatível com Windows e Linux (`AD-11`).
2. `retention_engine.py` / `render_clips.py` adaptam o visual e o Cold Open ao arquétipo (ex.: `susto_tensao` sem spoiler; `serio_realtalk` editorial sóbrio).
3. `--query "..."`, `--hunt-mode fast|deep` e `dossier_updater.py` funcionam via CLI e ferramentas MCP.

---

## Epic 3.6: Motor Calibrado e Medido — Sismógrafo 2.0, Nobada/Mico, Bordas e Juiz Confiável (Leva 1)

**Objetivo:** corrigir a calibração do motor de seleção com base em evidência (auditoria E3 de 2026-11-20, pesquisa 2a e medição própria do atraso do chat de 2026-11-21) e **provar a melhora com números** antes de retomar o Épico 5.
**Origem:** [`sprint-change-proposal-2026-11-21.md`](sprint-change-proposal-2026-11-21.md) (veredito dos pilares: SEGUE).
**Regras de Arquitetura:** `AD-1`, `AD-4`, `AD-11` + convenção "Sinal só vale se medido".
**Ordem obrigatória:** a 3.6.1 (baseline) vem antes de qualquer outra; cada história re-mede a Precision@K ao terminar.

### Story 3.6.1: Gabarito Automático e Baseline de Precision@K

**Descrição:**
Como operador, quero medir quantos dos cortes escolhidos pelo motor batem com os momentos que o público marcou (comentários com horário e heatmap do YouTube), para saber se cada mudança melhora ou piora a seleção.

**Critérios de Aceite (AC):**
1. `picorte/engine/benchmark.py` monta um gabarito fraco por VOD a partir de `comment_seeds.json` e do heatmap (sem anotação manual) e calcula Precision@K (K=5,10) contra o acaso (K/N).
2. Baseline gravado **antes** de qualquer mudança do Épico 3.6 em 3 VODs reais já processados e re-medido ao fim de cada história; resultado em `benchmarks/<data>.json`.
3. VOD sem comentários com horário nem heatmap é marcado "sem gabarito" e fica fora da média.
4. Custo zero: só dados já baixados; nenhuma chamada nova a LLM. O gabarito de cada VOD processado fica guardado para a 3.6.6.

### Story 3.6.2: Sismógrafo 2.0 — Atraso Compensado, Anti-Ruído e Tipo de Reação

**Descrição:**
Como operador, quero que o pico do chat aponte para o momento que o causou (não para a reação ~30 s depois), ignore bots e sorteios e diga que tipo de reação foi, para que os cortes semeados pelo chat comecem no lance certo.

**Critérios de Aceite (AC):**
1. Para cada pico de chat em t, a causa é procurada em [t−45 s, t−15 s], ancorada no evento de prosódia mais forte da faixa; a semente e `score_chat_window` usam essa janela deslocada (hoje `[pico−6 s, pico+8 s]`, `chat_seismic.py:148`).
2. Auto-calibração por VOD: correlação cruzada prosódia↔chat no `discover`, limitada a 15–45 s; atraso usado e força da correlação vão para `engine_health.json` (fraca = "chat pouco confiável"; sem correlação usa 30 s, medido em 2026-11-21 no VOD `x50ONQrBPRM`).
3. Anti-ruído: descarta comandos (`!sorteio`, `!pix`…), links e mensagens idênticas repetidas; o pico pesa mais quando vem de muitos autores e quando as mensagens são curtas e parecidas (concordância).
4. Tipo de reação por pico via léxico de emotes/palavras PT-BR (riso, hype, susto, cringe, luto/F, amor), salvo no pico e repassado ao Editor-Chefe; pedido explícito de corte no chat ("CLIPA", "clip it", "corta essa") é o tipo de maior peso.
5. Chat com menos de 20 msg/min: Sismógrafo desliga e a saúde registra "chat pequeno demais".
6. Teste com o chat real de `x50ONQrBPRM`; Precision@K re-medido.

### Story 3.6.3: Arquétipos `nobada_vacilo` e `mico_constrangimento` (10 → 12 rótulos)

**Descrição:**
Como operador, quero que o motor reconheça vacilos bobos e micos/constrangimentos, tipos de momento que viralizam em lives e que não existem entre os 16 tipos do brainstorming de 2026-11-19 (o `clutch_fail` busca o fail cinematográfico).

**Critérios de Aceite (AC):**
1. `CANONICAL_ARCHETYPES` passa de 10 para 12 com `nobada_vacilo` (erro bobo de execução) e `mico_constrangimento` (vergonha social, piada que não colou, silêncio constrangedor); prompt do Editor-Chefe, `golden_examples.json` (≥ 2 exemplos de cada) e validação atualizados.
2. Nova pista "Vacilo" no `multitrack.py` com cota própria, semeada por léxico PT-BR autodepreciativo ("burro demais", "não acredito que eu fiz isso", "volta, volta", "que vergonha"), pelo streamer anunciando o corte ("isso vai virar corte", "clipa isso", "manda pro TikTok"), "silêncio de choque" (1–3 s sem fala após evento forte, seguido de riso), riso do streamer na prosódia e pico de chat do tipo riso/cringe (3.6.2).
3. Mapa emote/palavra → arquétipo também nos comentários com horário ("kkkk 12:34" → nobada; "que vergonha 1:02:10" → mico).
4. Silêncio só conta como mico/choque se precedido de fala/evento e seguido de reação.
5. Só sinais baratos já medidos; keyframes (opcional) só confirmam candidatos a nobada. Nenhum custo novo por padrão.
6. Testes com transcrições sintéticas dos dois casos + Precision@K re-medido.

### Story 3.6.4: Bordas por Frase, Fim Após o Riso e Editor-Chefe sem Viés de Ordem

**Descrição:**
Como operador, quero que os cortes comecem no setup e terminem depois da reação, e que a nota do Editor-Chefe não dependa da ordem em que os candidatos chegam.

**Critérios de Aceite (AC):**
1. Editor-Chefe ajusta bordas por frases (`extend_sentences_before/after`) em vez de segundos (`expand_start_sec`/`expand_end_sec`); o motor converte pelos timestamps de palavra do Whisper (como o `llm_scout` faz com `sentence_id`).
2. Pré-roll de setup: semente de reação (chat, riso, susto) recua até o começo da frase do setup, 3–8 s antes da causa.
3. Fim nunca no meio de um riso: riso cruzando o fim avança o fim até o riso terminar (+1 s), respeitando a duração máxima do formato.
4. Ordem dos candidatos embaralhada (semente gravada para reproduzir) em toda passada; 2ª passada, com outra ordem, só nos ~15 finalistas. Diferença de nota > 1,5 entre passadas marca `confianca_baixa` e impede `ouro`.
5. Custo da 2ª passada: +1 chamada por VOD com ~15 candidatos (~6–10 mil tokens de entrada); Gemini dentro da cota gratuita; Claude (assinatura) ~US$ 0,05–0,15 de limite por VOD; modo `heuristic` sem chamadas.
6. Testes: conversão frase→tempo, riso cruzando o fim, reprodutibilidade da ordem; Precision@K re-medido.

### Story 3.6.5: Detector de Silêncio Digital, Tier Ouro com 2 Sinais e Nota de Confiança

**Descrição:**
Como operador, quero que o motor não escolha trechos mudos (música removida pelo YouTube ou queda da live), que o tier ouro exija prova de mais de um sinal e que cada projeto diga quanto dá para confiar na seleção.

**Critérios de Aceite (AC):**
1. Trechos de silêncio digital (≤ −90 dB por ≥ 2 s) são marcados; candidato com > 20% de silêncio digital é descartado e a saúde registra "trecho mutado/sem áudio" (P1).
2. Silêncio digital seguido de chat "caiu"/"travou"/"F" vira a tag `falha_tecnica` em `chat_trolagem` (#16 bastidores ao vivo), sem arquétipo novo.
3. Tier `ouro` exige ≥ 2 sinais independentes medidos concordando; senão `forte`.
4. Nota `standalone` (0–10) do Editor-Chefe ("dá para entender sem conhecer o streamer?"); abaixo de 5 o corte não vai para Short isolado (fica para Longo/compilação).
5. `engine_health.json` ganha `confianca_projeto` (quais sinais rodaram de verdade) para o painel do Épico 6 (W9).
6. Heatmap ("mais repetidos") rebaixado a bônus fraco em Shorts (hoje +1,2 e semente obrigatória) e usado principalmente para escolher o miolo do Longo de 3–5 min (a pesquisa mostrou que é ruidoso).
7. Testes com áudio sintético mudo e candidatos de 1 vs 2 sinais.

### Story 3.6.6: Pesos Calibrados pelo Gabarito (degrau 2)

**Descrição:**
Como operador, quero trocar os pesos escolhidos "a olho" por pesos aprendidos dos momentos que o público marcou, quando houver dados suficientes, sem nunca piorar a seleção.

**Critérios de Aceite (AC):**
1. Só começa quando houver **≥ 20 VODs com gabarito** acumulados pela 3.6.1.
2. Regressão logística por pares (trecho marcado pelo público × trecho comum do mesmo VOD) sobre os sinais já medidos, local em CPU, com pesos legíveis por sinal.
3. Validação cruzada por VOD; os pesos novos só entram se ganharem do baseline em Precision@K; senão ficam os atuais.
4. Pesos versionados (`weights/<data>.json`) com o resultado da medição; o Bandit do Épico 7 (degrau 3: desempenho real dos cortes publicados) parte deles.

---

## Epic 3.7: Formato que Retém — Cold Open, Loop, Layout Dinâmico, Par Short↔Longo e Arcos (Leva 2)

**Objetivo:** renderizar de verdade as alavancas de formato que a auditoria achou só planejadas (A8, A9, A11, A12). **Só começa depois do Épico 3.6 medido**, para separar o efeito da seleção do efeito do formato. Critérios de aceite detalhados escritos ao iniciar a leva.
**Origem:** [`sprint-change-proposal-2026-11-21.md`](sprint-change-proposal-2026-11-21.md).

### Story 3.7.1: Cold Open Reverso 1,5s e Seamless Loop renderizados de verdade (A9)
### Story 3.7.2: Layout dinâmico + Sniper Crop ligados ao render de games (A8)
### Story 3.7.3: Par Short↔Longo só com sobreposição real + versão TikTok 60–75s do mesmo momento (A11)
Ressalva do portão de pilares (A2): replay em câmera lenta só como recurso editorial pontual, nunca no corte inteiro.
### Story 3.7.4: Renderizar arcos de 2 atos e compilação por arquétipo, incl. "top vacilos" (A12)
### Story 3.7.5: Variação de template por arquétipo + freeze/seta no momento-chave (P2: regra do YouTube de 2026-10 contra "template em massa")
**Nota (2026-11-21):** candidato para a camada de efeitos animados (freeze/seta, faixa 2s, transição do Cold Open da 3.7.1, variação por arquétipo): **HyperFrames** (HeyGen, Apache-2.0), em modelo híbrido.
- O HyperFrames renderiza só os 2–3 s do efeito com fundo transparente (WebM VP9 / ProRes 4444).
- O FFmpeg sobrepõe, como hoje.

Antes de adotar, uma prova de conceito na 4060 Ti mede o tempo por efeito. Detalhes em `deferred-work.md` (W16).

---

## Epic 4: Escudo Anti-Strike, Anti-Desmonetização e Anti-Bloqueio (P1 Inegociável — Ampliado)

**Objetivo:** Implementar o escudo completo em quarentena granular por rede (`RiskVerdict`) cobrindo todos os portões automáticos do pilar **P1**: bloqueio Pre-Ingest/Pre-Export de fonte `desconhecida`/campanha vencida, políticas declarativas por publisher/jogo (`assets/policies/publishers.json` + DB), Disjuntor de Fonte, Copy Hygiene por rede (TikTok/Reels/Shorts), Cadência Anti-Spam + Cool-Down 48h, pontuação dupla YPP (`>=70`) + TikTok Originality + deduplicação híbrida `pHash`, cirurgia seletiva de música `Demucs` na GPU, Selo Verde 15s (áudio + visão + Cold Open + Thumbnail), React Guard com exceção de UI in-game, Raio-X na UI e ferramentas MCP.
**Capacidades cobertas:** `CAP-10`, `CAP-11`, `CAP-12`, `CAP-13`.
**Regras de Arquitetura:** `AD-3`, `AD-5`, `AD-11`.

### Story 4.1: Portão de Fontes, Políticas de Publisher e Disjuntor de Emergência (Onda 4A)

**Descrição:**
Como operador, quero sincronizar o cadastro de streamers com o banco, bloquear 100% de downloads/exports de fontes `desconhecida`, expiradas ou na lista negra, aplicar políticas declarativas por publisher/jogo (Rockstar/GTA 6, Nintendo, Riot, Valve, Sony) e acionar pausa global de fonte em caso de claim.

**Critérios de Aceite (AC):**
1. `policy_gate.assert_can_ingest` e `assert_can_export` bloqueiam fontes não autorizadas ou campanhas com `expires_at` vencido, sem flag de bypass.
2. `assets/policies/publishers.json` é carregado e sincronizado com `publisher_policies`, barrando spoilers/leaks e jogos embargados.
3. `source_breaker.pause_source_globally(source_id, reason)` marca a fonte como `pausada_por_claim` e trava imediatamente novos exports/Pacote do Dia.

### Story 4.2: Copy Hygiene por Rede, Cadência Anti-Spam, YPP/TikTok Score e Deduplicação `pHash` (Onda 4A)

**Descrição:**
Como operador, quero sanitizar automaticamente legendas/títulos por plataforma (impedindo links concorrentes e `#shorts` no TikTok + alertando palavras de ícone amarelo), controlar cadência diária com Cool-Down 48h, auditar originalidade separadamente para YouTube YPP (`>=70`) e TikTok FYP, e bloquear cortes duplicados por `pHash` + texto.

**Critérios de Aceite (AC):**
1. `copy_guard.py` limpa/valida copy por plataforma (`youtube_shorts`, `tiktok`, `instagram_reels`, `facebook_reels`), removendo URLs rivais/`#shorts` no TikTok e sinalizando termos desmonetizáveis.
2. `cadence_guard.py` consulta `publications`, aplica teto diário/espaçamento mínimo e respeita `cooldown_until` (48h) por rede.
3. `ypp_guard.py` emite `ypp_score`, `tiktok_originality_score` (penalizando frames estáticos `> 4s` e marcas d'água), `audit_trail` JSON e deduplicação híbrida (`pHash` visual + 3-gramas de texto `> 0.85`, exceto `ab_variant` explícito).

### Story 4.3: Cirurgia Seletiva de Música com `Demucs` na GPU (Onda 4B)

**Descrição:**
Como operador, quero detectar em CPU intervalos musicais (`>= 2,5s`) sob a fala e rodar `htdemucs` sob `vram_runner.py` apenas nessas janelas (chunks `<= 30s`), preservando a voz limpa com crossfade de `150 ms`, validação de SNR, cache de stems e degradação segura.

**Critérios de Aceite (AC):**
1. `music_surgeon.py` detecta intervalos musicais em CPU sem carregar GPU quando não há música.
2. Em janelas musicais, executa `htdemucs` via `vram_runner.py`, aplica crossfade `150 ms` + limiter `-1,5 dBTP` e reutiliza cache por hash do trecho; sem `demucs` instalado, marca `NEEDS_HUMAN_AUDIO_CHECK` explicitamente.

### Story 4.4: Selo Verde 15s (Áudio + Visão + Cold Open + Thumbnail) & Detector de React Perigoso (Onda 4B)

**Descrição:**
Como operador, quero aplicar censura cirúrgica (bleep/soft-mute com fade `15 ms` + `***`) em palavrões severos entre `0s` e `15s` e no teaser do Cold Open, barrar frames com gore/nudez nos primeiros 15s e na thumbnail, e bloquear trechos de react de navegador/player externo sem confundir menus/celular internos do jogo.

**Critérios de Aceite (AC):**
1. `green_seal_15s.py` aplica bleep/mute + `***` em léxico PT-BR/EN de 3 camadas com allowlist (sem falsos positivos como *"computador"*), protege o teaser do Cold Open e expõe scorer visual anti-gore/nudez consumido também por `thumbnail_factory.py`.
2. `react_guard.py` detecta navegador/player externo nas bordas do 16:9 persistindo `>= 2,5s`, preservando menus e celulares in-game.

### Story 4.5: Orquestrador `RiskShield`, Raio-X na UI, MCP e Suíte Adversarial (Onda 4B)

**Descrição:**
Como operador, quero um orquestrador único (`RiskVerdict` por rede) integrado a `ingest.py`, `render_clips.py`/`projects.py`, `publish_kit.py` e `dashboard.py`, com selos visuais na UI, controle de Cool-Down 48h, ferramentas MCP de auditoria/pausa e suíte adversarial de portões P1.

**Critérios de Aceite (AC):**
1. `orchestrator.py` produz `RiskVerdict` completo e persiste `risk_status`, `ypp_transform_score` e `phash_signature` no banco.
2. UI exibe selo visual de risco + breakdown por portão + Cool-Down 48h por rede; MCP expõe `picorte_auditar_risco`, `picorte_politicas_jogo` e `picorte_pausar_fonte`.
3. Suíte adversarial valida todos os 7 portões P1 ponta a ponta em Windows e Linux (`AD-11`).

---

## Epic 5: Olho para Fora — Radar de Alta, Monitor de Lives Ao Vivo e Caçador de Clipes Virais

**Objetivo:** Tornar o Picorte ativo na busca de oportunidades: monitorar o que está em alta na Twitch e no YouTube Gaming + Calendário de Eventos + Campanhas Pagas (CPM), vigiar e cortar **lives ao vivo** enquanto acontecem, caçar e re-transformar clipes virais de terceiros e detectar menções cruzadas (*Treta / Pingue-Pongue*).
**Capacidades cobertas:** `CAP-2`, `CAP-3`, `CAP-17`.
**Regras de Arquitetura:** `AD-1`, `AD-5`, `AD-9`.

### Story 5.1: Radar de Tendências, Calendário de Eventos, Tendências 48h, Modo Day-1, Campanhas CPM e Limpeza de 30 Dias

**Descrição:**
Como operador, quero um radar que consulte Twitch Top Games/Streams e YouTube Gaming em alta, cruze com o calendário de eventos e com as campanhas pagas de clipping (`campaigns`), injete tendências externas (48h) e Modo Day-1 (72h) no Scout e no auto-atualizador de `game_dossiers/`, alerte sobre fontes em alta ainda `desconhecidas` e expurgue dados de terceiros em até 30 dias.

**Critérios de Aceite (AC):**
1. `trend_radar.py` atualiza as tendências usando apenas as ordenações oficiais das APIs (sem criar métricas derivadas proibidas sobre canais de terceiros).
2. Fontes em alta com status `desconhecida` geram alerta explicando o que falta para liberá-las, sem baixar nenhum vídeo delas.
3. Job diário purga registros de terceiros com `expires_at <= now()` (regra III.E.4.d).
4. Termos/memes em alta das últimas 48h são injetados como pistas semânticas no Scout (`Épico 3.5`), e lançamentos/patches nas primeiras 72h do Calendário ativam prioridade Day-1 e disparam atualização do respectivo `game_dossiers/<jogo>.json`.

### Story 5.2: Monitor de Lives Ao Vivo e Feeds de VODs (`live_monitor.py`)

**Descrição:**
Como operador, quero monitorar canais autorizados na Twitch, Kick e YouTube e capturar segmentos deslizantes de 3–5 minutos quando entrarem ao vivo, enviando imediatamente para corte os blocos em que o Sismógrafo do Chat + Áudio disparar.

**Origem do código (`referencias/`):**
- `referencias/fralapo_clippyme/src/clippyme/monitoring/live_monitor.py` + `integrations/` (`twitch_client.py`, `kick_client.py`, `youtube_feed.py`).

**Critérios de Aceite (AC):**
1. `live_monitor.py` adaptado ao PostgreSQL e ao `policy_gate.py` captura segmentos de lives e novos VODs com reconexão automática.
2. Segmentos de live com explosão no chat/áudio são processados prioritariamente pelo pipeline dos Épicos 3 e 4.

### Story 5.3: Caçador de Clipes de Terceiros (`clip_hunter.py`), Detector de Treta e Consenso Cross-Streamer (`storyline_detector.py`)

**Descrição:**
Como operador, quero buscar automaticamente *Twitch Clips* virais recentes das fontes autorizadas (extraindo da VOD limpa quando disponível e re-transformando por completo), detectar quando um streamer menciona outro na transcrição e identificar Consenso Cross-Streamer do Mesmo Dia (3+ fontes reagindo ao mesmo detalhe/cena em 24h).

**Critérios de Aceite (AC):**
1. `clip_hunter.py` importa candidatos, localiza o offset no VOD limpo quando existente e exige passagem completa pelo Escudo P1 e pelo Score de Transformação YPP (`>= 70`).
2. `storyline_detector.py` identifica citações nominais entre streamers cadastrados e agrupa os trechos relacionados para compilação.
3. Quando 3 ou mais fontes monitoradas reagem ao mesmo evento/detalhe do jogo em 24h, `storyline_detector.py` aplica boost automático de prioridade na fila e sugere compilação cross-streamer.

**Nota (2026-11-21, correct-course):** a treta **entre streamers** fica nesta história; treta dentro da mesma live continua no arquétipo `rage_tilt`. Quando a fonte for a Twitch, os clipes criados por espectadores (API oficial `Get Clips`, `vod_offset`) também alimentam o gabarito da 3.6.1.

### Story 5.4: Perfis Adaptativos e Memória de Piadas Internas (`streamer_profiles.py`)

**Descrição:**
Como operador, quero manter um perfil adaptativo por fonte autorizada contendo bordões, piadas internas (*running gags*), referências da comunidade e baseline de energia/ritmo, para que o Scout e o Editor-Chefe v2 (Épico 3.5) reconheçam ironias e referências sutis de cada streamer.

**Critérios de Aceite (AC):**
1. `streamer_profiles.py` persiste e consulta o perfil por `source_id` no PostgreSQL e injeta automaticamente suas piadas internas e tom habitual no prompt do Scout e do Editor-Chefe v2.
2. Permite cadastrar/editar piadas internas via CLI/MCP e sugerir novas entradas de forma incremental a partir de cortes aprovados.


**Nota (2026-11-21, correct-course):** bordões e piadas internas (`lore_bordao`) e o perfil do streamer ficam aqui; incluir os emotes próprios do canal (7TV/BTTV/canal) no perfil, alimentando o léxico do Sismógrafo 2.0 (3.6.2).
---

## Epic 6: Publicação Assistida e OAuth nas 5 Redes, Disjuntor de Claims e Painel "Estúdio do Criador"

**Objetivo:** Entregar o fluxo de **Publicação Assistida Inicial** (pacote pronto + botões de copiar em 1 clique + vínculo de URL publicada) e os **Publicadores OAuth Oficiais** para as 5 redes (YouTube Shorts, YouTube Longo com Thumbnail e *Related Video*, TikTok, Instagram Reels e Facebook), o **Disjuntor Global de Claims (`claim_breaker.py`)** e o **painel web final "Estúdio do Criador"**. O painel é só desktop (Windows e Linux) e mostra cada função com o status real decidido pelo backend (ligado, parcial ou travado; travado nunca é falso). O visual sai da direção escolhida com o impeccable (Operate); o `DESIGN.md` atual não é restrição.
**Capacidades cobertas:** `CAP-14`, `CAP-15`, `CAP-16`.
**Regras de Arquitetura:** `AD-1`, `AD-4`, `AD-6`, `AD-7`, `AD-8`, `AD-9`, `AD-10`, `AD-11` + convenção "Travado nunca é falso".
**Origem da mudança (2026-11-21):** [`sprint-change-proposal-2026-11-21-painel.md`](sprint-change-proposal-2026-11-21-painel.md) (pilares: AJUSTAR → SEGUE com C1–C4).

**Ordem:**
1. Pré-passo: `bmad-ux` + direção visual.
2. Painel: 6.3 → 6.4 → 6.5 → 6.6 → 6.7 → 6.8, antes do 3.6.2+ e do E5.
3. A 6.1 e a 6.2 vêm depois do E5.

**Valem em todas as histórias do painel (6.3–6.8):**
- **Condições dos pilares:**
  - **C1:** só o cooldown manual pode ser limpo; liberar fonte exige base de permissão + evidência;
  - **C2:** corte exportado sem link publicado vira pendência visível;
  - **C3:** 👍/👎 é opcional;
  - **C4:** Windows e Linux.
- **Convivência com a sessão do motor:** não editar `score_clips.py`, `llm_router.py`, `benchmark.py`, `projects/` nem `benchmarks/`. As histórias do motor não editam `picorte/api/`, `picorte/web/` nem o `studio_service.py`.

### Story 6.1: Pacote de Publicação Assistida (`export_pack.py`) e Cofre OAuth + Publicadores das 5 Redes

**Descrição:**
Como operador, quero que cada corte aprovado gere imediatamente o pacote pronto para postagem manual assistida (para operar desde o Dia 1 sem depender das auditorias da T1) e também suporte publicação direta via OAuth cifrado nas 5 redes (incluindo Thumbnail, *Related Video* Short→Longo, crédito automático e 1º Comentário Fixado).

**Origem do código (`referencias/`):**
- `referencias/FujiwaraChoki_supoclip/backend/src/social/` (`base.py`, `youtube.py`, `tiktok.py`, `instagram.py`) + `fralapo_clippyme/src/clippyme/integrations/social_publisher.py`.

**Critérios de Aceite (AC):**
1. Todo corte aprovado gera `exports/<clip_id>/` com vídeo, thumbnail e metadados prontos por rede, permitindo registrar na UI a URL/ID publicada manualmente.
2. Tokens OAuth são cifrados em AES-256-GCM (`crypto_vault.py`).
3. O publicador do YouTube (`youtube.py`) respeita a cota diária, envia a Thumbnail do vídeo longo, vincula o Short ao Vídeo Longo e posta o 1º Comentário Fixado.

### Story 6.2: Monitor de Claims e Disjuntor Global Automático (`claim_breaker.py`)

**Descrição:**
Como operador, quero que qualquer claim de bloqueio ou strike detectado via API (ou reportado no painel) pause imediatamente e em uma única transação todos os cortes daquela fonte em todas as 5 redes.

**Critérios de Aceite (AC):**
1. `claim_breaker.trip(source_id, reason)` altera `sources.permission_status = 'pausada_por_claim'` e muda todas as publicações pendentes da fonte nas 5 redes para `pausada_emergencia`.
2. Teste automatizado P0 simula um claim e verifica que nenhum corte da fonte pode ser publicado após o disparo.

### Story 6.3: Base do Estúdio — FastAPI, Contrato de Capacidades e Casca da SPA

**Descrição:**
Como operador, quero um backend novo que diga o status real de cada função do Picorte e uma casca de painel que mostre isso, para que nada na tela finja funcionar.

**Insumo:** mapa de capacidades em [`brainstorm-intent.md`](../brainstorming/brainstorm-mapa-painel-estudio-do-criador-2026-11-21/brainstorm-intent.md); stack em [`research.md`](research/technical-stack-painel-estudio-do-criador-2026-11-21/research.md).

**Critérios de Aceite (AC):**
1. O FastAPI substitui o `http.server` do `dashboard.py` e porta: Range/206, token anti-CSRF, CSP, checagem Host/Origin, fila serial única e fallback de SPA. Abrir ou ler nunca escreve em `project.json`.
2. Lock por projeto entre processos (`filelock`): só vira "interrompido" o job cujo lock está livre (B9).
3. `GET /api/capacidades`:
   - cada função do mapa traz: status `ligado|parcial|travado`, `tipo_motivo` (`codigo|config|dado|temporario|escolha`), motivo, o que falta, fonte do dado, origem (épico/história/CAP), escopo (global/projeto/corte), `depende_de`, `verificado_em` e `ligou_em`;
   - sondas com cache: Ollama e modelo, `agy` (429), Claude CLI, `yt-dlp`, `node`, `demucs`, GPU/VRAM e disco;
   - a mesma função vira a ferramenta MCP `picorte_capacidades` (AD-10).
4. `GET /api/taxonomia` (arquétipos, tiers, redes, modos de IA, presets): o front não fixa listas.
5. SSE `/api/eventos`: progresso dos jobs e mudanças de capacidade.
6. Teste de contrato A5: nenhum número sai para capacidade travada; sinal não medido sai `null`.
7. Casca React (stack da pesquisa) com navegação e os estados vazio, carregando, erro e travado desenhados.

### Story 6.4: Verdade no Banco — Sinais Medidos, Veredito P1, Fonte e Reconciliação

**Descrição:**
Como operador, quero que o banco guarde só o que foi medido de verdade e esteja ligado à fonte, para que o painel e o MCP leiam números reais.

**Critérios de Aceite (AC):**
1. **B1:** `videos.source_id` gravado a partir do `source_gate` do projeto (hoje NULL em 12/12).
2. **B2:** notas por sinal (chat, áudio/prosódia, visual, texto) gravadas quando medidas e `NULL` quando não medidas; migração dos 0.0 existentes.
3. **B3:** `risk_status`, `ypp_transform_score` e `phash_signature` persistidos a partir do `risk_verdict` (AC1 da 4.5).
4. **B4:** reconciliação banco × disco. Vídeos e cortes de projetos apagados viram arquivados, sem perder o rastreio dos cortes publicados (P1).
5. **B6:** `assets/policies/publishers.json` sincronizado com `publisher_policies` no boot.
6. **B5 (fila única):** `picorte_enfileirar_video` cria o projeto real na fila do Estúdio, chamando a mesma função do painel.

### Story 6.5: Lives — Página Inicial (Ao Vivo, Em Alta, Recentes) e "Na Sua Mesa"

**Descrição:**
Como operador, quero abrir o Picorte numa vitrine de lives e vídeos dos streamers cadastrados, no estilo das plataformas de vídeo, e cortar dali, com as pendências do dia à vista.

**Critérios de Aceite (AC):**
1. Abas **Ao vivo / Em alta / Recentes**:
   - **Recentes** lista os vídeos recentes dos canais cadastrados pela API oficial (custo R$ 0, dentro da cota);
   - cache de thumbs e metadados de no máximo 30 dias (AD-9).
2. **Ao vivo** mostra quem está ao vivo quando houver credencial de app da Twitch configurada (grátis e revogável); sem ela, fica travada (`config`). Cortar a live ao vivo fica travado até a 5.2; **Em alta** fica travada até a 5.1. O backend escolhe a aba aberta por padrão (a primeira ligada).
3. Clicar num vídeo abre a **Sala do vídeo**: uma página com endereço próprio (decisão do dono no `bmad-ux`), com o player e o painel de corte:
   - o portão P1 responde antes de enfileirar;
   - escolha do formato;
   - motor de IA com a disponibilidade real;
   - preview do enquadramento sobre uma imagem real do vídeo (nunca um mock).
4. Faixa **"Na sua mesa"**: revisões pendentes, links pendentes (C2), jobs rodando e falhas com o próximo passo.
5. O selo "AO VIVO" e o número de espectadores só aparecem com dado da API oficial + `verificado_em` (A5).

### Story 6.6: Fila e Revisão de Cortes — Player, Waveform, Sinais e Rótulos

**Descrição:**
Como operador, quero revisar os cortes com o vídeo, a forma de onda e os sinais que realmente foram medidos, ensinar o motor com 1 toque e aprovar rápido pelo teclado.

**Critérios de Aceite (AC):**
1. **Fila:** título real do vídeo, streamer, jogo e estágio em PT-BR. Falha com ação (trocar motor e retomar, cadastrar fonte, retomar). O conjunto de prova (`benchmark_blind`) fica separado da produção.
2. **Revisão em 3 colunas:**
   - lista de cortes;
   - player + waveform (peaks calculados no servidor) com ajuste de início e fim;
   - arquétipo, tier, títulos, faixa 2s, 1º comentário, motivo, sinais ("não medido" no lugar de zero) e veredito P1 por rede ("sem veredito — re-auditar" quando faltar).
3. 👍/👎 com motivo opcional gravado (B10), sem ser obrigatório para o corte seguir (C3); botão "Salvar como Exemplo Ouro" (`golden_examples.json`).
4. **Filtros e ordem:** filtros por arquétipo, tier, sinal medido e status P1, vindos da taxonomia; ordem padrão por tier + sinais concordantes, não pela nota geral saturada.
5. **Extras:** atalhos de teclado (próximo/anterior, play, 👍/👎, início/fim); editor de transcrição e legenda recolhido por padrão; Caça Profunda e busca por pergunta.
6. **Motor padrão:** o último que funcionou; o determinístico exige escolha consciente, com aviso do que deixa de rodar.

### Story 6.7: Fontes, Escudo, Saúde do Motor, Benchmark e Configurações

**Descrição:**
Como operador, quero gerir fontes e permissões, ver o escudo P1, a saúde do motor e o placar de acerto, e configurar o sistema, tudo com dado real.

**Critérios de Aceite (AC):**
1. **Fontes:**
   - lista e cadastro;
   - mudança de permissão só com base + evidência (C1);
   - tentativas barradas pelo portão;
   - políticas por jogo;
   - cadastro de campanhas;
   - pausas com histórico;
   - editor de dossiês de jogo.
2. **Escudo:**
   - cooldowns por rede com contagem regressiva; só o cooldown criado pelo operador pode ser limpo (C1);
   - claim registrado à mão aciona a pausa da fonte;
   - o monitor automático aparece travado até a 6.2.
3. **Saúde do motor (W9):**
   - matriz projeto × parte do motor (`engine_health.json`) com o motivo de cada `na`/`failed`;
   - frase-resumo do projeto;
   - `confianca_projeto` travada até a 3.6.5.
4. **Benchmark:**
   - Precision@K por versão, contra o acaso e com o n de VODs;
   - aviso de amostra pequena;
   - progresso "x de 20 VODs com gabarito" para a 3.6.6.
5. **Configurações:** motor de IA (disponibilidade real), preset de visão, marca e legendas, Modo Madrugada (parcial) e custos (parcial, regra 6).

### Story 6.8: Publicação Assistida e Áreas que Ainda Não Existem

**Descrição:**
Como operador, quero publicar à mão com tudo pronto e sem perder o rastreio, e ver desde já, travado e honesto, o que o Picorte ainda vai fazer.

**Critérios de Aceite (AC):**
1. **Pacote do Dia:**
   - cartões por rede;
   - copiar em 1 clique (título, descrição + crédito, hashtags, 1º comentário) e abrir a pasta;
   - cadência respeitada;
   - projetos anteriores ao portão aparecem como "rodar o prepare de novo" (W5).
2. **Links publicados:**
   - colar a URL publicada no cartão do corte;
   - exportado sem link vira pendência em "Na sua mesa" (C2);
   - YouTube Longo aceito (B11).
3. **Áreas travadas desenhadas, com o que falta e o `depende_de`:** contas OAuth das 5 redes, publicação automática, claims automático, métricas 1h/24h/7d, Bandit, dataset e Radar. Os contadores que já são reais (👍/👎, publicações com link) aparecem; nenhum número de exemplo.

---

## Epic 7: O Cérebro que Aprende — Snapshots 1h/24h/7d, Bandit com Esquecimento, Reciclagem A/B e Active Learning

**Objetivo:** Fechar o ciclo autônomo (P3 e P4): coletar as métricas reais (1h, 24h, 7d) dos cortes publicados (via OAuth ou URL colada no modo assistido), calcular a recompensa anti-clickbait ponderada por retenção e campanhas CPM, atualizar o Bandit Contextual com esquecimento do passado, acionar a Reciclagem A/B de Gancho ("Segunda Vida") e capturar automaticamente o `dataset_rotulado/` para treinar nosso classificador próprio na RTX 4060 Ti.
**Capacidades cobertas:** `CAP-18`.
**Regras de Arquitetura:** `AD-2`, `AD-3`, `AD-8`.

### Story 7.1: Coletor de Snapshots (1h / 24h / 7d) e Recompensa Anti-Clickbait (`reward.py`)

**Descrição:**
Como operador, quero que o sistema colete automaticamente views, likes, comentários e retenção em 1h, 24h e 7d após cada publicação e calcule a recompensa normalizada pela mediana recente do canal, penalizando clickbait de baixa retenção e aplicando o multiplicador de campanhas pagas ativas.

**Critérios de Aceite (AC):**
1. `metrics_collector.py` agenda e grava os snapshots de `1h`, `24h` e `7d` em `metrics_snapshots`.
2. `reward.py` calcula $Y$ ponderado por $Q_{\text{ret}}$ e $M_{\text{camp}}$ conforme especificado no `companion-cerebro-bandit.md`.

### Story 7.2: Bandit Contextual por Arquétipo/Tier com Esquecimento Temporal e Reciclagem A/B de Gancho

**Descrição:**
Como operador, quero que o Bandit aprenda separadamente o peso de cada variável (`jogo`, `streamer`, `archetype` dos 10 arquétipos canônicos, `tier`, `formato`, `duração`, `rede`, `horário`) dando menos peso ao passado ($\gamma$ diário), e que cortes com ótima retenção após 5s mas *swipe-away* alto nos 3s ganhem automaticamente uma "Segunda Vida" com novo Cold Open e novo título respeitando o tom editorial do arquétipo.

**Critérios de Aceite (AC):**
1. `contextual_bandit.py` atualiza `bandit_state` usando `archetype` (os 10 arquétipos do Épico 3.5) e `tier` com decaimento exponencial $\gamma \in [0.85, 0.92]$, reserva ~20% para exploração e reordena a fila de produção.
2. `ab_recycler.py` detecta cortes com retenção pós-5s alta e retenção 3s baixa e cria automaticamente o job `ab_variant = 2` trocando o Cold Open de 1,5s, a faixa de contexto e o título sem violar o estilo editorial do arquétipo.

**Nota (2026-11-21, correct-course):** passa a usar os **12** arquétipos (3.6.3) e parte dos pesos calibrados pela 3.6.6 (degrau 2) quando existirem.

### Story 7.3: Autocaptura de Dataset Rotulado (`active_learning.py`) e Pré-Classificador Local de Arquétipos na RTX 4060 Ti

**Descrição:**
Como operador, quero que cortes campeões (`>= 2.5x` mediana) e fracassos (`<= 0.35x` mediana) tenham seus vetores multimodais, `archetype`, `tier` e keyframes salvos automaticamente em `dataset_rotulado/`, que campeões sejam sugeridos para `golden_examples.json` e que `train_local_scorer.py` treine nosso calibrador e um Pré-Classificador Local de Arquétipos na RTX 4060 Ti.

**Critérios de Aceite (AC):**
1. `active_learning.py` exporta `features.npz`, `keyframes/` e `label.json` (incluindo `archetype` e `tier`) para `dataset_rotulado/<clip_id>/`, registra em `dataset_samples` e gera sugestão de promoção de campeões para `golden_examples.json`.
2. `train_local_scorer.py` roda sob o `vram_runner.py` (preferencialmente no Modo Madrugada), treina o calibrador de pesos e o **Pré-Classificador Local de Arquétipos** sobre os exemplos acumulados e atualiza os pesos/probabilidades consumidos pelo `score_clips.py`.

**Nota (2026-11-21, correct-course):** o dataset rotulado também consome o gabarito automático da 3.6.1 e os 👍/👎 do Estúdio (6.3).
