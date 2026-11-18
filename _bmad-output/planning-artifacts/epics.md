---
title: 'Épicos e Histórias — Picorte (Plano Mestre Evolutivo v2)'
status: final
created: '2026-11-18'
updated: '2026-11-18'
sources:
  - ../specs/spec-picorte/SPEC.md
  - ./architecture.md
  - ./pilares.md
  - ./concorrentes.md
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

## Epic 4: Escudo Anti-Strike e Anti-Desmonetização (P1 Inegociável)

**Objetivo:** Implementar todos os portões automáticos de segurança do pilar **P1**: bloqueio de fonte `desconhecida`, políticas por publisher/jogo (ex.: Rockstar/GTA 6), cirurgia seletiva de música com `Demucs` na GPU, filtro "Selo Verde 15s" (micro-bleep + visão), detector visual de "React Perigoso", Score mínimo YPP (`>=70`) e deduplicação perceptual `pHash`.
**Capacidades cobertas:** `CAP-10`, `CAP-11`, `CAP-12`, `CAP-13`.
**Regras de Arquitetura:** `AD-3`, `AD-5`.

### Story 4.1: Portão de Status da Fonte e Políticas por Publisher/Jogo (`policy_gate.py`)

**Descrição:**
Como operador, quero que o sistema recuse baixar ou publicar qualquer fonte `desconhecida`, expirada ou na lista negra e aplique as regras da tabela `publisher_policies` (janela de spoiler, cutscenes proibidas, flag de rádio licenciada).

**Critérios de Aceite (AC):**
1. `policy_gate.assert_can_ingest` bloqueia 100% das chamadas de download para fontes com `permission_status` não autorizado ou campanha vencida.
2. Políticas pré-cadastradas (incluindo Rockstar/GTA 6) barram candidatos fora da janela de spoiler ou de categorias proibidas pelo publisher.

### Story 4.2: Cirurgia Seletiva de Música com `Demucs` na GPU (`music_surgeon.py`)

**Descrição:**
Como operador, quero que trechos do corte que contenham música de fundo licenciada (ex.: rádio de carro no GTA) passem por separação neural `htdemucs` na GPU apenas nos segundos afetados, removendo a música e preservando a voz limpa do streamer sem alterar pitch ou velocidade (A2).

**Critérios de Aceite (AC):**
1. `music_surgeon.py` detecta os intervalos com música sob a fala e executa `htdemucs` sob o `vram_runner.py`.
2. O áudio resultante substitui apenas o intervalo musical pelo stem `vocals` com crossfade suave de 150 ms, mantendo o áudio original do jogo no restante do corte.

### Story 4.3: Filtro "Selo Verde 15s", Detector de "React Perigoso" e Guardião YPP + `pHash`

**Descrição:**
Como operador, quero que os primeiros 15 segundos de todo corte recebam micro-bleep (`0,2s`) e `***` em palavrões severos e verificação visual contra violência gráfica, que trechos de react de navegador/terceiros sejam bloqueados e que apenas cortes com `ypp_score >= 70` e sem duplicidade de `pHash` entrem na fila.

**Critérios de Aceite (AC):**
1. `green_seal_15s.py` aplica atenuação/bleep nos timestamps de profanidade severa entre `0s` e `15s` e substitui a palavra por `***` na legenda `.ass`.
2. `react_guard.py` detecta e bloqueia trechos onde a tela principal exibe navegador ou player de vídeo de terceiros (YouTube/TikTok).
3. `ypp_guard.py` bloqueia cortes com `ypp_transform_score < 70` ou com similaridade `pHash`/transcrição `> 0.85` contra cortes anteriores no banco.

---

## Epic 5: Olho para Fora — Radar de Alta, Monitor de Lives Ao Vivo e Caçador de Clipes Virais

**Objetivo:** Tornar o Picorte ativo na busca de oportunidades: monitorar o que está em alta na Twitch e no YouTube Gaming + Calendário de Eventos + Campanhas Pagas (CPM), vigiar e cortar **lives ao vivo** enquanto acontecem, caçar e re-transformar clipes virais de terceiros e detectar menções cruzadas (*Treta / Pingue-Pongue*).
**Capacidades cobertas:** `CAP-2`, `CAP-3`, `CAP-17`.
**Regras de Arquitetura:** `AD-1`, `AD-5`, `AD-9`.

### Story 5.1: Radar de Tendências, Calendário de Eventos, Campanhas CPM e Limpeza de 30 Dias

**Descrição:**
Como operador, quero um radar que consulte Twitch Top Games/Streams e YouTube Gaming em alta, cruze com o calendário de eventos e com as campanhas pagas de clipping (`campaigns`), alerte sobre fontes em alta ainda `desconhecidas` e expurgue dados de terceiros em até 30 dias.

**Critérios de Aceite (AC):**
1. `trend_radar.py` atualiza as tendências usando apenas as ordenações oficiais das APIs (sem criar métricas derivadas proibidas sobre canais de terceiros).
2. Fontes em alta com status `desconhecida` geram alerta explicando o que falta para liberá-las, sem baixar nenhum vídeo delas.
3. Job diário purga registros de terceiros com `expires_at <= now()` (regra III.E.4.d).

### Story 5.2: Monitor de Lives Ao Vivo e Feeds de VODs (`live_monitor.py`)

**Descrição:**
Como operador, quero monitorar canais autorizados na Twitch, Kick e YouTube e capturar segmentos deslizantes de 3–5 minutos quando entrarem ao vivo, enviando imediatamente para corte os blocos em que o Sismógrafo do Chat + Áudio disparar.

**Origem do código (`referencias/`):**
- `referencias/fralapo_clippyme/src/clippyme/monitoring/live_monitor.py` + `integrations/` (`twitch_client.py`, `kick_client.py`, `youtube_feed.py`).

**Critérios de Aceite (AC):**
1. `live_monitor.py` adaptado ao PostgreSQL e ao `policy_gate.py` captura segmentos de lives e novos VODs com reconexão automática.
2. Segmentos de live com explosão no chat/áudio são processados prioritariamente pelo pipeline dos Épicos 3 e 4.

### Story 5.3: Caçador de Clipes de Terceiros (`clip_hunter.py`) e Detector de Treta (`storyline_detector.py`)

**Descrição:**
Como operador, quero buscar automaticamente *Twitch Clips* virais recentes das fontes autorizadas (extraindo da VOD limpa quando disponível e re-transformando por completo) e detectar quando um streamer menciona outro na transcrição para sugerir cortes de resposta.

**Critérios de Aceite (AC):**
1. `clip_hunter.py` importa candidatos, localiza o offset no VOD limpo quando existente e exige passagem completa pelo Escudo P1 e pelo Score de Transformação YPP (`>= 70`).
2. `storyline_detector.py` identifica citações nominais entre streamers cadastrados e agrupa os trechos relacionados para compilação.

---

## Epic 6: Publicação Assistida e OAuth nas 5 Redes, Disjuntor de Claims e Painel "Estúdio do Criador"

**Objetivo:** Entregar o fluxo de **Publicação Assistida Inicial** (pacote pronto + botões de copiar em 1 clique + vínculo de URL publicada) e os **Publicadores OAuth Oficiais** para as 5 redes (YouTube Shorts, YouTube Longo com Thumbnail e *Related Video*, TikTok, Instagram Reels e Facebook), o **Disjuntor Global de Claims (`claim_breaker.py`)** e o painel web responsivo **Estúdio do Criador** (PC e celular) seguindo o `DESIGN.md`.
**Capacidades cobertas:** `CAP-14`, `CAP-15`, `CAP-16`.
**Regras de Arquitetura:** `AD-1`, `AD-4`, `AD-6`, `AD-7`, `AD-8`, `AD-9`, `AD-10`.

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

### Story 6.3: Painel Web "Estúdio do Criador" (Desktop e Celular — `DESIGN.md`)

**Descrição:**
Como operador, quero operar a fila, o Seletor de IA (`Ollama` / `Claude` / `Gemini` / `Dupla`), os cartões de Publicação Assistida, as fontes/campanhas e os alertas de risco tanto no PC quanto no celular com o visual aprovado em `DESIGN.md` e `design/mock/fila.html`.

**Skill líder de visual:** `impeccable`.

**Critérios de Aceite (AC):**
1. Interface aplica `design/tokens/tokens.css`, logos de `design/brand/` e fontes `Antonio`, `Archivo` e `JetBrains Mono`, com layouts dedicados para desktop e celular.
2. Inclui o Seletor de Motor de IA (4 modos), visualização das 4 notas do corte com a "Curva do Mais Repetido", botões de 1 clique da Publicação Assistida e estados de risco acessíveis (nunca indicados só por cor — WCAG AA).

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

### Story 7.2: Bandit Contextual com Esquecimento Temporal e Reciclagem A/B de Gancho

**Descrição:**
Como operador, quero que o Bandit aprenda separadamente o peso de cada variável (`jogo`, `streamer`, `tipo_momento`, `formato`, `duração`, `rede`, `horário`) dando menos peso ao passado ($\gamma$ diário), e que cortes com ótima retenção após 5s mas *swipe-away* alto nos 3s ganhem automaticamente uma "Segunda Vida" com novo Cold Open e novo título.

**Critérios de Aceite (AC):**
1. `contextual_bandit.py` atualiza `bandit_state` com decaimento exponencial $\gamma \in [0.85, 0.92]$, reserva ~20% para exploração e reordena a fila de produção.
2. `ab_recycler.py` detecta cortes com retenção pós-5s alta e retenção 3s baixa e cria automaticamente o job `ab_variant = 2` trocando o Cold Open de 1,5s, a faixa de contexto e o título.

### Story 7.3: Autocaptura de Dataset Rotulado (`active_learning.py`) e Treino Local na RTX 4060 Ti

**Descrição:**
Como operador, quero que cortes campeões (`>= 2.5x` mediana) e fracassos (`<= 0.35x` mediana) tenham seus vetores multimodais e keyframes salvos automaticamente em `dataset_rotulado/` e que `train_local_scorer.py` treine nosso modelo próprio na RTX 4060 Ti para calibrar os pesos do pontuador.

**Critérios de Aceite (AC):**
1. `active_learning.py` exporta `features.npz`, `keyframes/` e `label.json` para `dataset_rotulado/<clip_id>/` e registra em `dataset_samples`.
2. `train_local_scorer.py` roda sob o `vram_runner.py` (preferencialmente no Modo Madrugada), treina o classificador local sobre os exemplos acumulados e atualiza os pesos usados pelo `score_clips.py`.
