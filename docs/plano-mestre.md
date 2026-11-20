# Plano Mestre — projeto-cortes (Picorte)

> **Versão 2.1 (Plano Mestre Evolutivo + Épico 3.5) · 2026-11-19** · Mantido em `docs/plano-mestre.md`.
> Substitui a Versão 1 (modelo em cachoeira focado em SaaS) após a decisão da **E3.5**: **foco 100% em lucrar com os próprios canais de cortes** (começando pelo **Bomba Clips** em games), partindo dos clones open-source auditados em `referencias/` e evoluindo camada por camada até o sistema autônomo completo. Atualizado em **2026-11-19** via `bmad-correct-course` para incluir o **Épico 3.5 (Motor de Caça Extraordinária)** e a alocação da Onda 3 nos Épicos 5, 6 e 7.

---

## 0. Instruções para Qualquer Sessão Futura (Claude Code ou Gemini Antigravity)

Se você é um agente assumindo este projeto em uma nova sessão, **leia nesta ordem antes de agir**:
1. `CLAUDE.md` (ou `AGENTS.md`, que é symlink para `CLAUDE.md`);
2. Este arquivo (`docs/plano-mestre.md`) — identifique qual etapa/épico está marcada como `⏳ PRÓXIMA` abaixo;
3. O último `docs/handoff-sessao-NN.md`;
4. `_bmad-output/planning-artifacts/pilares.md`, `visao.md` e `concorrentes.md`.

### Regras gerais de execução
- **Compatibilidade Claude Code ↔ Antigravity (Gemini):**
  - Skills do projeto ficam em `skills/<nome>/` e são instaladas via symlink em `.claude/skills/<nome>/`. O Antigravity lê `.claude/skills/` automaticamente através de `.agents/skills.json`.
  - Skills globais (`superpowers`, `impeccable`, `claude-api`, `skill-creator`, `find-skills`, `youtube-thumbnail-design`) já estão instaladas tanto em `~/.claude/` quanto em `~/.gemini/config/plugins/`.
- **Orçamento de VRAM (Regra de Ouro da RTX 4060 Ti 8 GB / Notebook GTX 1650 4 GB):**
  - **Nunca carregar dois modelos pesados de GPU ao mesmo tempo.** O worker deve executar em **fila serializada com limpeza explícita de VRAM (`torch.cuda.empty_cache()` / subprocesso isolado)** entre estágios:
    1. Transcrição (`faster-whisper` int8/float16) → descarrega;
    2. Visão Computacional (`YuNet` / `MediaPipe` / `YOLO-HUD` / `rembg`) → descarrega;
    3. Cirurgia de áudio (`Demucs` seletivo só nos segundos com música) → descarrega;
    4. LLM local (`Ollama` 7B/8B) se usado localmente → descarrega;
    5. Renderização `FFmpeg` (`h264_nvenc`).
- **O que foi explicitamente EXCLUÍDO do escopo pelo dono (não implementar):**
  1. **SaaS / Multi-tenant (`workspace_id`), billing, planos ou onboarding de terceiros.**
  2. **Jump-Cut de Tempos Mortos + Compressor de Áudio** (único item descartado no brainstorming da E3.5).

---

## 1. Visão Geral da Nova Linha do Tempo

```
FASE A — FUNDAÇÃO, IDENTIDADE E AJUSTE DE RUMO (Concluída ✅)
  E0 Fundação ✅ ─► E1 Pilares ✅ ─► E2 Naming ✅ ─► E3 Marca/Design ✅ ─► E3.5 Ajuste de Rumo + Brainstorming ✅
                                                                              │
                                                                              └──► T1 Trilha Paralela: Contas Dev + Auditorias (corre até o Épico 6)

FASE B — ESPECIFICAÇÃO UNIFICADA E ARQUITETURA DE FUSÃO (Concluída ✅)
  E4 Spec Unificada (`bmad-spec`) ✅
   │
   ▼
  E5 Arquitetura de Fusão + Estratégia de Testes (`bmad-architecture` + `bmad-testarch-test-design`) ✅
   │
   ▼
  E6 Quebra nos 7 Épicos e Sprint Status (`bmad-create-epics-and-stories` + `bmad-sprint-planning`) ✅

FASE C — CONSTRUÇÃO EVOLUTIVA (Liderada pelo `superpowers` — cada Épico entrega o sistema rodando num patamar acima)
  Épico 1 (MVP Zero): Clone Base (`chopify`) instalado e gerando os primeiros cortes .mp4 na GPU ✅
   │
   ▼
  Épico 2: Controle por Agente (Skill + MCP para Claude/Gemini) + Banco PostgreSQL local + Gerenciador de Fila/VRAM + Seletor de IA na UI ✅
   │
   ▼
  Épico 3: Upgrade Multimodal 4D (Sismógrafo do Chat + Áudio + Visão Computacional de Games: Facecam/HUD/Micro-expressões) ✅
           + Engenharia de Retenção (Cold Open 1,5s, Contexto 2s, Seamless Loop, Layout Dinâmico, Sniper Crop,
             Compilação Cross-Streamer, Cortes Longos 3-5 min + Fábrica de Thumbnail)
   │
   ▼
  Épico 3.5: Motor de Caça Extraordinária (10 Arquétipos + 3 Tiers + Recall Multi-Pista + Full-VOD Scout + ✅
             Editor-Chefe v2 + golden_examples + game_dossiers + Keyframes Seletivos + Query-Driven + Deep Hunt)
   │
   ▼
  Épico 4: Escudo Anti-Strike P1 (Status da fonte, Políticas por Publisher/GTA 6, Cirurgia de Música com Demucs seletivo, ⏳ PRÓXIMO
           Selo Verde 15s, Detector Visual de React Perigoso, Score YPP, Deduplicação pHash)
   │
   ▼
  Épico 5: Olho para Fora (Radar Twitch/YouTube + Tendências 48h + Modo Day-1 72h + Calendário + Campanhas CPM +
           Monitor de Lives AO VIVO + Caçador de Clipes + Consenso Cross-Streamer + Memória de Piadas Internas)
   │
   ▼
  Épico 6: Publicação Autônoma nas 5 Redes (Shorts + Related Video -> Longo, YT Longo, TikTok, Reels, FB + 1º Comentário Fixado)
           + Monitor de Claims com Disjuntor Global + Painel Web "Estúdio do Criador" (`DESIGN.md`, 10 Arquétipos/3 Tiers, Query-Driven/Deep Hunt)
   │
   ▼
  Épico 7: O Cérebro que Aprende (Coletor de Snapshots 1h/24h/7d + Bandit Contextual por Arquétipo/Tier com Esquecimento +
           Reciclagem A/B de Gancho "Segunda Vida" + Active Learning + Pré-Classificador Local de Arquétipos na 4060 Ti)
```

---

## 2. FASE A — Fundação, Identidade e Ajuste de Rumo (Concluída ✅)

### E0 · Fundação ✅ (commit `0a076f1`)
- **Entregáveis:** BMAD v6.12.4 instalado; `_bmad/custom/config.toml`; `CLAUDE.md`; `.gitignore`.

### E1 · Pilares e anti-pilares ✅ (aprovado em 2026-11-16, revisado em 2026-11-18)
- **Skill líder:** `cortes-pilares` (`.claude/skills/cortes-pilares/SKILL.md`).
- **Entregáveis:** `_bmad-output/planning-artifacts/pilares.md` e `_bmad-output/planning-artifacts/visao.md`.

### E2 · Naming ✅ (aprovado em 2026-11-16)
- **Skill líder:** `cortes-naming` (`.claude/skills/cortes-naming/SKILL.md`).
- **Entregáveis:** `_bmad-output/planning-artifacts/naming.md` (**Picorte**) e `naming-canais.md` (**Bomba Clips**).

### E3 · Marca e Design System ✅ (aprovado em 2026-11-16)
- **Skill líder:** `impeccable`.
- **Entregáveis:** `PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`, `design/brand/`, `design/tokens/tokens.css`, `design/fonts/`, `design/mock/fila.html`.

### E3.5 · Auditoria de Clones Open-Source, Brainstorming de Alavancas e Ajuste de Rumo ✅ (2026-11-18)
- **Skills usadas:** `systematic-debugging`, `bmad-brainstorming` (modo Autônomo), `cortes-pilares` (modos Revisar e Julgar).
- **O que foi feito:**
  1. Sincronização completa de skills e plugins entre **Claude Code** e **Antigravity (Gemini)** (`.agents/skills.json`, `AGENTS.md`, `~/.gemini/config/plugins/`).
  2. Download e auditoria do código-fonte de 10 clones open-source em `referencias/` (`mehbul_chopify`, `fralapo_clippyme`, `FujiwaraChoki_supoclip`, `AgriciDaniel_claude-shorts`, `louisedesadeleer_clipify`, `artbyjazi_autoclip`, etc.), documentada em `_bmad-output/planning-artifacts/concorrentes.md`.
  3. Sessão de brainstorming (`_bmad-output/brainstorming/brainstorm-mapa-funcionalidades-picorte-2026-11-18/brainstorm.html` e `.memlog.md`) e aprovação de todas as alavancas de retenção, visão computacional, comunidade, blindagem e receita (exceto Jump-Cut + Compressor).
  4. Retirada do escopo de SaaS/multi-tenant e reescrita de `pilares.md`, `visao.md`, `concorrentes.md`, `CLAUDE.md`, `PRODUCT.md`, `docs/plano-mestre.md` e `docs/handoff-sessao-02.md`.

### T1 · Trilha Paralela — Contas de Desenvolvedor e Auditorias das APIs ⏱️ (Corre em paralelo até o Épico 6)
- **Objetivo:** destravar a publicação pública direta via OAuth em YouTube, TikTok e Meta (Instagram Reels + Facebook) antes de chegar no Épico 6.
- **Passos:**
  1. Criar projeto no Google Cloud (YouTube Data API v3, tela de consentimento OAuth), app no TikTok for Developers (Content Posting API) e app no Meta for Developers (Instagram Graph API + Pages API).
  2. Verificar se YouTube/TikTok/Meta aceitam domínio gratuito (`*.vercel.app` / `*.pages.dev`) para as URLs públicas de Política de Privacidade e Termos de Uso; se exigirem domínio próprio, registrar `picorte.com.br` (~R$ 40/ano) e subir página estática simples.
  3. Quando o publicador OAuth estiver ligado (Épico 6), gravar o vídeo de demonstração e submeter as auditorias (incluindo permissão III.L no YouTube se aplicável a métricas derivadas).
  4. **Plano B enquanto a auditoria não sai (respeitando A4):** o Picorte gera na pasta de saída o `.mp4` final + thumbnail + arquivo `.meta.json` com título, descrição, crédito, hashtags e o texto do 1º comentário prontos para o operador publicar em 30 segundos pelo celular ou PC, informando depois a URL/ID publicado para o coletor medir as views.

---

## 3. FASE B — Especificação Unificada e Arquitetura de Fusão (Concluída ✅)

> **Por que mudamos a Fase B:** como descartamos o SaaS e já temos o código dos clones em `referencias/` e o mapa completo aprovado em `visao.md` e `concorrentes.md`, não faz sentido escrever um `Product Brief` de mercado nem um `PRD` burocrático do zero. Usamos o fluxo moderno do BMAD v6.12.4: **`bmad-spec` → `bmad-architecture` → `bmad-create-epics-and-stories`**.

### E4 · Especificação Unificada (`SPEC.md` + Companions) ✅ (2026-11-18, commit `216e5ed`)
- **Líder:** skill **`bmad-spec`** (`.claude/skills/bmad-spec/SKILL.md`).
- **Apoio:** `cortes-pilares` (modo Julgar ao finalizar).
- **O que entra (fontes obrigatórias para ler na ativação):**
  - `_bmad-output/planning-artifacts/pilares.md`
  - `_bmad-output/planning-artifacts/visao.md`
  - `_bmad-output/planning-artifacts/concorrentes.md`
  - `_bmad-output/brainstorming/brainstorm-mapa-funcionalidades-picorte-2026-11-18/.memlog.md`
  - `PRODUCT.md` e `DESIGN.md`
- **O que foi feito:**
  1. Rodados os scripts de ativação do BMAD (`resolve_customization.py`, `resolve_config.py`) e inicializado o memlog da spec em `_bmad-output/specs/spec-picorte/`.
  2. Destilada toda a visão e o mapa aprovado num **`SPEC.md`** enxuto (Why, Capabilities `CAP-1` a `CAP-18` com `intent` e `success`, Constraints, Non-goals, Success signal) mais **4 arquivos companheiros (`companions:`)**:
     - `companion-pipeline-multimodal.md`: especificações do Sismógrafo do Chat, Áudio 1 Hz, Visão Computacional 2 fps (Facecam, HUD/Killfeed, Micro-expressões, Sniper Crop, Layout Dinâmico), **Seletor de IA de 4 Modos na UI (`Ollama` / `Claude` / `Gemini` / `Dupla: Filtro + Acompanhamento`)** e Engenharia de Retenção (Cold Open 1,5s, Contexto 2s, Seamless Loop, Cross-Streamer, Funil Short→Longo 3–5 min + Thumbnail);
     - `companion-escudo-risco.md`: máquina de estados de permissão da fonte, matriz de políticas por publisher/jogo (ex.: Rockstar/GTA 6), cirurgia de música com `Demucs` seletivo, Selo Verde 15s (visão + bleep), Detector de React Perigoso, Score YPP, `pHash` e disjuntor de claims;
     - `companion-integracoes-redes.md`: cotas, formatos, áreas seguras de legenda, OAuth, *Related Video* (Shorts → Longo), 1º comentário fixado e regras de armazenamento da API do YouTube (III.E.4.d / III.L) para YouTube Shorts, YouTube Longo, TikTok, Instagram Reels e Facebook;
     - `companion-cerebro-bandit.md`: modelo contextual/hierárquico que separa variáveis (`jogo × streamer × tipo de momento × formato × duração × horário × rede`), fator de esquecimento temporal, fórmula de recompensa ponderada por retenção (sem clickbait), multiplicador de campanhas pagas (CPM), reciclagem A/B de gancho e autocaptura de dataset rotulado (*Active Learning*).
  3. Rodados os dois passes de `Self-Validate` do `bmad-spec` (Coherence + Preservation) e o modo Julgar do `cortes-pilares` (veredito **segue**).
- **Entregáveis gerados:** `_bmad-output/specs/spec-picorte/SPEC.md` + os 4 companions + `.memlog.md`.

### E5 · Arquitetura de Fusão e Estratégia de Testes ✅ (2026-11-18, commit `216e5ed`)
- **Líder:** **`bmad-architecture`** (Winston) + **`bmad-testarch-test-design`** (Murat / TEA) + **`claude-api`**.
- **O que foi feito:**
  1. Definida a **Estrutura Definitiva de Pastas do Código (`picorte/`)** e as 10 decisões arquiteturais invioláveis (`AD-1` a `AD-10`), validadas com `0 findings` pelo linter `lint_spine.py`.
  2. Definido o **Schema PostgreSQL Local** (10 tabelas canônicas sem multi-tenant: `sources`, `publisher_policies`, `campaigns`, `videos`, `clips`, `publications`, `metrics_snapshots`, `claims_events`, `bandit_state`, `dataset_samples`).
  3. Definidos o **Orquestrador Serial de VRAM (`vram_runner.py` — `AD-3`)**, o **Roteador de IA de 4 Modos (`llm_router.py` — `AD-4`)** e o **Fluxo de Publicação Assistida Inicial (`export_pack.py` — `AD-8`)**.
  4. Definida a **Matriz de Testes dos Riscos P0/P1 (`R-01` a `R-10`)**.
- **Entregáveis gerados:** `_bmad-output/planning-artifacts/architecture.md`, `_bmad-output/planning-artifacts/architecture/architecture-projeto-cortes-2026-11-18/ARCHITECTURE-SPINE.md` e `_bmad-output/test-artifacts/test-design-picorte.md`.

### E6 · Quebra nos 7 Épicos, Histórias e Prontidão ✅ (2026-11-18, commit `216e5ed`)
- **Líder:** **`bmad-create-epics-and-stories`** → **`bmad-sprint-planning`**.
- **Entregáveis gerados:** `_bmad-output/planning-artifacts/epics.md` (7 Épicos e 22 Histórias detalhadas) e `_bmad-output/implementation-artifacts/sprint-status.yaml`.

---

## 4. FASE C — Construção Evolutiva em 7 Épicos (Mão na Massa)

> **Como cada Épico é executado:** liderado pelo **`superpowers`** (`writing-plans` → `test-driven-development` → `subagent-driven-development` → `systematic-debugging` → `verification-before-completion`), com **`bmad-code-review`** nos épicos críticos (Épicos 4 e 6) e **`impeccable`** no frontend (Épico 6).
> **Regra de ouro:** ao terminar cada Épico, o sistema inteiro precisa estar **rodando e testado na máquina**, entregando valor real antes de abrir o próximo.
> **Onde desenvolver e rodar (Notebook GTX 1650 4 GB vs PC de Mesa RTX 4070 Ti / 4060 Ti):** todos os Épicos 1 a 7 podem ser desenvolvidos e testados com vídeos curtos (2–15 min) no **Notebook (GTX 1650 4 GB)** graças ao perfil automático de GPU (`cuda.py`) e ao uso de Claude/Gemini no Seletor de IA. A mudança para o **PC de Mesa (RTX 4070 Ti / 4060 Ti)** só é necessária na hora de rodar **produção pesada em volume** (VODs brutos de 4–6h, monitor de múltiplas lives ao vivo simultâneas, Ollama 7B/8B/14B local e treinamento do modelo próprio no Épico 7).

---

### ÉPICO 1 (MVP Zero) · O Clone Base (`chopify`) Rodando na Máquina e Gerando Cortes ✅ (2026-11-18)
- **Objetivo:** ter o motor base do `mehbul/chopify` instalado dentro do nosso projeto, rodando com GPU (`faster-whisper` + `FFmpeg` + `OpenCV YuNet`) e gerando os primeiros cortes `.mp4` legendados (9:16 e 16:9) a partir de um vídeo real de gameplay.
- **De onde vem o código:**
  - Copiar a base de `referencias/mehbul_chopify/` (`chopify.py`, `ingest.py`, `sections.py`, `download_and_transcribe.py`, `evidence.py`, `visual.py`, `score_clips.py`, `render_clips.py`, `captions.py`, `branding.py`, `tighten.py`, `projects.py`, `dashboard.py` e `tests/`) para a estrutura definida na E5.
  - Copiar o utilitário de diagnóstico de GPU de `referencias/artbyjazi_autoclip/backend/autoclip/cuda.py`.
- **O que será feito:**
  1. Verificar/instalar `ffmpeg` (com `libass` e `h264_nvenc`), criar o ambiente Python (`.venv` via `uv` ou `venv`) e instalar as dependências base (`faster-whisper`, `opencv-python`, `numpy`, `yt-dlp`).
  2. Adaptar a configuração de modelo do `faster-whisper` para escolher automaticamente o tamanho e quantização ideais conforme a VRAM disponível (`int8` na GTX 1650 de 4 GB do notebook; `large-v3` ou `turbo` `float16`/`int8_float16` na RTX 4060 Ti de 8 GB do PC de mesa).
  3. Rodar a suíte de testes existente do `chopify` (`pytest`) e processar o primeiro vídeo de teste de games de ponta a ponta (transcrição → pontuação acústica/visual/textual → renderização 9:16 com legenda `.ass` queimada e 16:9).
- **Critério de saída do Épico 1:** comando CLI e painel local (`http://127.0.0.1:8765`) gerando cortes `.mp4` reais com legenda sincronizada palavra a palavra e testes passando.

---

### ÉPICO 2 · Controle por Agente (Claude & Gemini via MCP/Skill) + Banco PostgreSQL + Fila de VRAM ✅ (2026-11-18)
- **Objetivo:** fazer o motor conversar diretamente com o **Claude Code** e com o **Gemini (Antigravity)** e substituir o controle solto em arquivos JSON por um banco **PostgreSQL local** com gerenciador de fila que respeita o limite de VRAM e possui **Modo Madrugada**.
- **De onde vem o código:**
  - Base de contrato para agente: `referencias/mehbul_chopify/docs/AGENT-API.md`.
  - Base do servidor MCP: `referencias/FujiwaraChoki_supoclip/mcp/src/supoclip_mcp/server.py`.
  - Abstração de provedores de LLM (Ollama local + Claude + Gemini): `referencias/artbyjazi_autoclip/backend/autoclip/providers/`.
- **O que será feito:**
  1. Subir o banco **PostgreSQL local** (via `docker-compose.yml` leve contendo apenas Postgres, ou serviço local) com as migrações das tabelas definidas na E5 (`sources`, `publisher_policies`, `campaigns`, `videos`, `clips`, `publications`, `metrics_snapshots`, `claims_events`, `bandit_state`, `dataset_samples`).
  2. Construir o **Gerenciador de Fila e VRAM (`vram_runner.py`)**: garante execução estritamente sequencial de modelos pesados na GPU (liberando memória entre etapas) e implementa o **Modo Madrugada / Ocioso** (processa lotes pesados automaticamente quando a GPU/CPU está livre ou no horário configurado).
  3. Construir o **Servidor MCP do Picorte (`picorte_mcp`)** e a skill própria **`.claude/skills/picorte-operador/SKILL.md`**, expondo ferramentas diretas para o Claude e para o Gemini:
     - `picorte_status_fila` (ver jobs, estado do worker, uso de GPU);
     - `picorte_Fontes` (cadastrar/listar fontes e mudar status de permissão);
     - `picorte_cortar_video` (enfileirar vídeo/VOD com parâmetros);
     - `picorte_listar_cortes` (listar candidatos gerados com suas notas parciais de chat/áudio/visão/texto);
     - `picorte_re_renderizar` (ajustar gancho, layout ou legenda de um corte).
- **Critério de saída do Épico 2:** você consegue pedir em linguagem natural aqui no chat (tanto no Gemini quanto no Claude) para cadastrar uma fonte, cortar um vídeo e consultar os cortes gravados no PostgreSQL.

---

### ÉPICO 3 · Upgrade Multimodal 4D (Chat + Áudio + Visão Computacional de Games) e Engenharia de Retenção ✅ (2026-11-18)
- **Objetivo:** transformar o cortador básico em um especialista em **Lives de Games**, capaz de enxergar o jogo e o streamer, ler a explosão do chat, gerar **cortes curtos (<60s)** e **cortes longos (3–5 min com Thumbnail automática)** e aplicar todas as travas de retenção dos primeiros 2 segundos e do loop final.
- **De onde vem o código (transplantes + código próprio):**
  - Detecção de Facecam de canto e layout dividido: `referencias/FujiwaraChoki_supoclip/backend/src/media/reaction_layout.py` (`find_reactor_face`) e `face_detection.py` (YuNet).
  - Ajuste fino de bordas na pausa da fala: `referencias/AgriciDaniel_claude-shorts/scripts/snap_boundaries.py`.
  - Expressões de pan/crop dinâmico no FFmpeg: `referencias/louisedesadeleer_clipify/scripts/build_pan.py`.
  - Overlays de gancho e banner: `referencias/fralapo_clippyme/src/clippyme/editing/hook_overlay.py` e `banner.py`.
  - Base de áudio e visão: `evidence.py`, `visual.py`, `score_clips.py` e `render_clips.py` do `chopify`.
- **O que será feito (passo a passo):**
  1. **Sismógrafo do Chat da Live (`chat_seismic.py`):**
     - Parser de chat de lives/VODs (Twitch, Kick, YouTube Chat Replay) e de comentários com timestamp (`04:12`) / curva *Most Replayed*.
     - Calcula a série temporal (1 Hz) de `mensagens/segundo` normalizada pela mediana móvel da live e a densidade de tokens de reação (`"KKKK"`, `"LUL"`, `"OMEGALUL"`, `"CLIP"`, `"MENTIRA"`, `"???"`, `"CARACA"`, `"WTF"`). Gera picos candidatos em <1s de CPU.
  2. **Upgrade de Visão Computacional em Games (`visual_games.py`):**
     - **Termômetro de Micro-Expressões na Facecam:** sobre o recorte da webcam detectado pelo `find_reactor_face`, usa `MediaPipe FaceMesh` / `YuNet` para medir abertura de boca (*MAR — Mouth Aspect Ratio*), olhos arregalados e velocidade brusca de movimento da cabeça (streamer pulando da cadeira / mão na cabeça).
     - **Detector Visual de HUD / Killfeed (`hud_detector.py`):** analisa as regiões típicas de HUD/killfeed/centro da tela (via OCR rápido / template / YOLO leve) buscando gatilhos de evento (*Kill*, *Eliminated*, *Victory*, *Wasted*, *Busted*, *Clutch*, tela de morte ou conquista).
  3. **Fusão no Pontuador Multimodal 4D (`score_clips.py`):**
     - Combina os 4 sinais sincronizados segundo a segundo: **Nota Chat + Nota Áudio (`evidence.py`) + Nota Visão (`visual_games.py`) + Nota Semântica/Texto (LLM local ou API)**, usando `snap_boundaries.py` para cravar o início e o fim em pausas limpas.
  4. **Enquadramento Inteligente de Games (`reframe_games.py`):**
     - Incorpora o `reaction_layout.py` do `supoclip` e adiciona:
       - **Troca Dinâmica de Layout no mesmo corte:** alterna os keyframes do FFmpeg entre modo **História** (70% facecam / 30% jogo quando o streamer fala sem ação no jogo), modo **Reação** (split 640px facecam no topo + 1280px jogo embaixo) e modo **Ação/Cutscene** (jogo 100% com facecam em PiP);
       - **Sniper Crop (Zoom Dinâmico):** calcula o centro de massa do movimento/saliência dentro da área do jogo e move suavemente a janela de recorte para focar no quadrante onde a jogada/bug aconteceu.
  5. **Engenharia de Retenção e Formatos (`retention_engine.py`):**
     - **Cold Open Reverso (1,5s):** recorta automaticamente o ápice de 1,5s (maior soma de áudio + expressão facial do corte) e concatena em `0:00` com flash/corte seco antes do início da narrativa;
     - **Faixa de Contexto Instantâneo (2s):** gera uma frase curta situada nos primeiros 2s lendo a transcrição imediatamente anterior ao corte;
     - **Seamless Loop (Loop Infinito):** nos cortes verticais (<60s), ajusta o ponto de corte final para conectar ritmicamente/gramaticalmente com o início;
     - **Compilação Cross-Streamer (`cross_streamer.py`):** quando 2 ou mais vídeos tiverem o mesmo evento/trailer/momento (alinhado por fingerprinting de áudio `audio_align.py` do `clipify` ou similaridade visual), monta automaticamente um corte multi-reação;
     - **Par "Short Isca (<60s) + Corte Longo (3–5 min 16:9)" + Fábrica Automática de Thumbnail (`thumbnail_factory.py`):** quando um bloco tem densidade alta por 3–5 minutos, exporta o corte longo 16:9 + o Short vertical de 45s (isca), e gera a **Thumbnail 1280×720** escolhendo o frame de maior MAR/expressão da facecam (recortado com `rembg`) sobre o frame mais intenso do jogo, aplicando contraste e 2–3 palavras de impacto com a tipografia `Antonio`/`Archivo` do nosso `DESIGN.md` (guiado pela skill `youtube-thumbnail-design`).
     - **1º Comentário Fixado "Isca de Debate":** gera no `.meta.json` e no banco a pergunta polarizadora sobre o lance.
- **Critério de saída do Épico 3:** dado um VOD de live de game com facecam, o motor detecta momentos pelo chat+áudio+visão+texto, gera o Short 9:16 (com Cold Open 1,5s, Contexto 2s, Layout Dinâmico, Sniper Crop e Loop) e o Corte Longo 16:9 (3–5 min) com sua Thumbnail PNG pronta.

---

### ÉPICO 3.5 · Motor de Caça Extraordinária — 10 Arquétipos, Recall Multi-Pista, Full-VOD Scout e Editor-Chefe v2 ✅ (2026-11-19)
- **Objetivo:** tunar o motor de descoberta do Épico 3 para que **nenhum corte extraordinário fique de fora** — capturando desde piadas ocultas/callbacks culturais silenciosos (ex.: *Alanzoka testando a animação da geladeira do GTA 6*) até caos co-op, rage/tilt, real-talk sério, polêmicas, descobertas, clutches/fails, sustos, ironia *deadpan* / instant karma e trocas com o chat — eliminando os gargalos reais observados em produção.
- **Blueprint técnico completo:** `_bmad-output/planning-artifacts/epic-3-5-motor-caca-extraordinaria.md` (cobrindo os 16→10 arquétipos, sinais, contratos JSON, prompts e matriz TDD) + `_bmad-output/planning-artifacts/sprint-change-proposal-2026-11-19.md`.
- **Taxonomia Canônica:** 10 arquétipos (`callback_oculto`, `caos_coop`, `rage_tilt`, `serio_realtalk`, `polemica_hottake`, `descoberta_detalhe`, `clutch_fail`, `susto_tensao`, `deadpan_karma`, `chat_trolagem`) + 3 tiers (`ouro`, `forte`, `experimental`).
- **O que será feito (em 2 ondas):**
  - **Onda 1 (Impacto Imediato — Histórias `3.5.1` a `3.5.3`):**
    1. **Correções Estruturais + Sinais Gratuitos do YouTube (`3.5.1`):** persistir `heatmap` (*Most Replayed*) e `chapters` no `ingest.py`; aplicar **NMS temporal obrigatório antes do loop `[vision 1/12]`** em `score_clips.py`; filtrar falsos positivos COCO `person` no `hud_detector.py`; converter `ANAPHORIC_OPENERS` em detector de **Dêiticos Visuais** (`"olha isso"`, `"olha a mão"`, `"espera"`).
    2. **Recall Multi-Pista (5 Pistas), Payoff-First Rewind, Full-VOD Narrative Scout e Durações Flexíveis (`3.5.2`):** substituir a porta estreita única por 5 pistas com cota reservada (`multitrack.py`), filtro anti-lixo, léxico PT-BR + TF-IDF local + Silêncio Magnético, **Full-VOD Narrative Scout (`llm_scout.py`)** com Map-Reduce e saída por `sentence_id` (zero timestamp alucinado), *Payoff-First Rewind* e faixas flexíveis (`8–14s`, `15–59s`, `60–120s`, `120–300s`).
    3. **Editor-Chefe v2 + Contexto Cultural + Diversificação MMR (`3.5.3`):** novo prompt com Conselho de 4 Caçadores Especialistas em `llm_router.py`, biblioteca editável `picorte/ai/golden_examples.json`, dossiês por jogo `picorte/ai/game_dossiers/` (`gta6.json` inicial), injeção de `pre_context`/`post_context`, Tradutor de Piada Oculta sem Spoiler e diversificação MMR por tempo e arquétipo.
  - **Onda 2 (Sensores Ricos + Narrativa Avançada — Histórias `3.5.4` e `3.5.5`):**
    4. **Visão Seletiva, Comentários, Prosódia Avançada e Facecam Rica (`3.5.4`):** extração de 3 keyframes em dêiticos visuais (`multimodal_keyframes.py`), mineração opcional de timestamps em comentários do YouTube (`comments_miner.py`), prosódia em CPU (riso pulsado `3–6 Hz`, susto `>18 dB`, taxa de fala/F0, contraste voz×jogo, hook opcional YAMNet/PANNs com fallback), `gaze-to-camera` / facepalm / inspeção visual no `visual_games.py` e segmentação de atividade (`activity_segmenter.py`).
    5. **Narrativa Avançada & Modos Sob Demanda (`3.5.5`):** arcos de 2 atos (*setup → payoff* distantes em `two_act_arc.py`), compilação automática por arquétipo (`archetype_compiler.py`), estilo de badge e Cold Open adaptados ao arquétipo (`susto_tensao` sem spoiler, `serio_realtalk` sóbrio), **Busca por Pergunta Livre (`--query`)**, **Modo Caça Profunda (`--hunt-mode fast|deep`)** e auto-atualizador CLI/MCP de dossiês (`dossier_updater.py`).
- **Critério de saída do Épico 3.5:** suíte completa verde (376 testes anteriores + novos testes TDD `3.5.1`–`3.5.5`), benchmark do caso geladeira do Alanzoka classificado como `callback_oculto` (`ouro`), e validação em VOD real sem repetição de janelas no `[vision]` nem saturação no `hud_detector`.

---

### ÉPICO 4 · Escudo Anti-Strike e Anti-Desmonetização (P1 Inegociável) ⏳ PRÓXIMO
- **Objetivo:** blindar 100% da operação antes que qualquer vídeo vá para a fila de publicação, garantindo que nenhuma fonte proibida, música com copyright, spoiler vedado, react cruzado ou abertura desmonetizável passe.
- **Skills de apoio:** `cortes-pilares` (validação de regras P1) e `bmad-code-review` (revisão adversarial obrigatória neste épico).
- **O que será feito (`risk_shield/`):**
  1. **Portão de Status da Fonte e Políticas de Publisher (`policy_gate.py`):**
     - Bloqueia no `ingest.py` qualquer tentativa de baixar ou processar uma fonte com status `desconhecida` ou na `lista_negra`.
     - Verifica se a permissão de `campanha_ativa` ainda está dentro da data de validade.
     - Consulta a tabela `publisher_policies` (já pré-populada com regras conhecidas, ex.: Rockstar/GTA 6 — bloqueio de final, vazamentos, janela de spoiler pós-lançamento) e barra candidatos que violem as restrições do jogo.
  2. **Cirurgia Seletiva de Música com `Demucs` na GPU (`music_surgeon.py`):**
     - Detecta segmentos do corte onde há música de fundo misturada à fala (ex.: rádio de veículo em GTA ou música de lobby).
     - Em vez de perder o corte ou usar truques proibidos pelo A2 (pitch/speed), roda o modelo `htdemucs` na GPU **somente nos segundos onde a música foi detectada**, extraindo a faixa `vocals` limpa do streamer e substituindo apenas aquele trecho de áudio.
  3. **Filtro "Selo Verde 15s" (`green_seal_15s.py`):**
     - **Áudio/Legenda:** varre as palavras dos primeiros 15 segundos; se encontrar termos da lista de desmonetização/profanidade severa, aplica um micro-bleep/mute cirúrgico de `0,2s` nos timestamps exatos da palavra no áudio e substitui por `***` no arquivo `.ass`.
     - **Visão Computacional:** analisa os frames dos primeiros 15 segundos procurando padrões de sangue/gore/violência gráfica explícita; se detectar, desloca o ponto de abertura ou aplica desfoque localizado.
  4. **Detector Visual de "React Perigoso" (`react_guard.py`):**
     - Detecta quando a área principal da live deixa de ser o jogo e passa a exibir interface de navegador, player do YouTube/TikTok/X ou TV aberta (streamer assistindo conteúdo de terceiros), marcando o trecho como bloqueado por risco de direitos de terceiros.
  5. **Score Mínimo de Transformação YPP + Deduplicação Perceptual (`ypp_guard.py`):**
     - Calcula uma pontuação auditável de transformação real (P2: layout alterado + legenda `.ass` + Cold Open/Contexto + metadados próprios) e bloqueia se estiver abaixo do mínimo.
     - Calcula o hash perceptual (`pHash` visual + similaridade de texto da transcrição) contra os cortes já existentes no PostgreSQL para nunca publicar o mesmo lance duas vezes.
- **Critério de saída do Épico 4:** suíte de testes automatizados (P0/P1) comprovando que: (a) fonte `desconhecida` é barrada antes do download, (b) trecho com música tem a música removida pelo `Demucs` mantendo a voz, (c) palavrão nos primeiros 15s recebe bleep + `***`, (d) react de navegador é detectado, e (e) corte duplicado é barrado pelo `pHash`.

---

### ÉPICO 5 · Olho para Fora — Radar de Alta, Monitor de Lives Ao Vivo e Caçador de Clipes Virais
- **Objetivo:** fazer o Picorte deixar de ser passivo (esperar você colar um link) e passar a **caçar sozinho** os jogos, streamers, lives ao vivo, clipes da comunidade e campanhas pagas que estão explodindo agora.
- **De onde vem o código:**
  - Monitor assíncrono de lives e feeds: `referencias/fralapo_clippyme/src/clippyme/monitoring/live_monitor.py`.
  - Clientes de plataforma: `referencias/fralapo_clippyme/src/clippyme/integrations/` (`twitch_client.py`, `kick_client.py`, `youtube_feed.py`).
- **O que será feito (`hunter/`):**
  1. **Radar de Tendências, Calendário de Eventos, Tendências 48h e Modo Day-1 (`trend_radar.py`):**
     - Consulta periodicamente a **API oficial da Twitch** (`Get Top Games`, `Get Streams`) e a **YouTube Data API v3** (`videos.list?chart=mostPopular&videoCategoryId=20` — Gaming) para medir quais jogos e streamers estão em pico de audiência **hoje**.
     - Cruza com a tabela de **Calendário de Eventos** (lançamentos de jogos, atualizações, campeonatos de e-sports) e com a tabela de **Campanhas Pagas de Clipping (`campaigns`)** (aplicando o multiplicador de CPM).
     - **Cruzamento com Tendências Externas (48h) + Modo Day-1 (72h):** injeta termos e memes em alta nas últimas 48h como pistas semânticas no Scout do Épico 3.5; nas primeiras 72h de um lançamento/patch grande do Calendário, ativa prioridade Day-1 (primeiras reações, detalhes, callbacks e bugs) e dispara o **Auto-Atualizador de Dossiê Cultural (`game_dossiers/`)**.
     - Se detectar um streamer/fonte explodindo de audiência que ainda está com status `desconhecida`, gera uma notificação clara no painel/agente: *"Fonte X está em alta em [Jogo], mas está bloqueada (status: desconhecida). O que falta para liberar: [verificar campanha / permissão]."*
     - Limpa automaticamente dados brutos de canais de terceiros com mais de 30 dias (cumprindo a regra III.E.4.d da API do YouTube).
  2. **Monitor de Lives AO VIVO e VODs (`live_monitor.py` transplantado e evoluído):**
     - Vigia as fontes autorizadas na Twitch, Kick e YouTube.
     - Quando uma fonte entra **ao vivo**, captura segmentos contínuos de 3 a 5 minutos via `streamlink`/`FFmpeg` junto com o fluxo do chat ao vivo.
     - Se o **Sismógrafo do Chat + Áudio** disparar acima do limiar de explosão, envia o segmento imediatamente para a fila prioritária dos Épicos 3, 3.5 e 4, gerando o corte minutos depois do lance acontecer ao vivo.
  3. **Caçador e Transformador de Clipes Já Prontos de Terceiros (`clip_hunter.py`):**
     - Busca os *Twitch Clips* mais vistos das últimas horas nas categorias/streamers autorizados.
     - Baixa o trecho original limpo (da VOD correspondente, quando disponível, para ter qualidade máxima e zero overlay) ou o próprio clipe, passa pelo pontuador 4D + Caça Extraordinária (Épicos 3/3.5) e pelo Escudo Anti-Strike (Épico 4), e aplica transformação completa (Cold Open, Contexto 2s, Layout Dinâmico, legenda nossa) para virar obra própria (P2).
  4. **Detector de "Treta / Pingue-Pongue" e Consenso Cross-Streamer do Mesmo Dia (`storyline_detector.py`):**
     - Varre as transcrições procurando menções aos nomes/apelidos dos outros streamers monitorados. Quando o Streamer A fala do Streamer B, busca nos clipes/VODs recentes do Streamer B menções de volta e sugere a montagem de um corte combinado.
     - **Consenso Cross-Streamer do Mesmo Dia:** quando **3 ou mais fontes monitoradas** reagem ao mesmo detalhe, cena ou assunto do jogo em 24h, eleva automaticamente a prioridade na fila e sugere compilação cross-streamer.
  5. **Perfis Adaptativos e Memória de Piadas Internas (`streamer_profiles.py`):**
     - Mantém perfil vivo por fonte autorizada (`streamer_profiles` no PostgreSQL) com bordões, *running gags* (piadas recorrentes), referências da comunidade e baseline de voz/energia do streamer, injetado no Scout e no Editor-Chefe v2 (Épico 3.5) para reconhecer ironias e piadas internas com alta precisão.
- **Critério de saída do Épico 5:** o Radar lista os jogos/streamers em alta agora, emite alerta para fontes não liberadas, o `live_monitor` captura e corta um segmento de teste de live/VOD e o `clip_hunter` importa e re-transforma um clipe curto dentro das regras P1/P2.

---

### ÉPICO 6 · Publicação Autônoma nas 5 Redes + Disjuntor de Claims + Painel "Estúdio do Criador" (`DESIGN.md`)
- **Objetivo:** conectar o Picorte às 5 redes via OAuth oficial (ou modo assistido enquanto alguma auditoria da T1 estiver pendente), ligar o monitor de claims com pausa automática global e vestir o painel web (PC e celular) com o nosso Design System aprovado na E3.
- **De onde vem o código:**
  - Clientes OAuth de publicação e leitura de métricas: `referencias/FujiwaraChoki_supoclip/backend/src/social/` (`base.py`, `registry.py`, `youtube.py`, `tiktok.py`, `instagram.py`).
  - Agendador de horários e espaçamento (`SmartScheduler`): `referencias/fralapo_clippyme/src/clippyme/integrations/social_publisher.py` e `publishing/publish_service.py`.
  - Tokens e referência visual: `DESIGN.md`, `design/tokens/tokens.css`, `design/brand/` e `design/mock/fila.html`.
- **Skills de apoio:** **`impeccable`** (para construir/polir o frontend desktop e mobile seguindo `DESIGN.md` e `craft-floor.md`) e **`bmad-code-review`** (segurança OAuth e cifragem de tokens).
- **O que será feito:**
  1. **Cofre de Credenciais OAuth (`crypto_vault.py`):**
     - Cifragem AES-GCM dos tokens OAuth e refresh tokens no PostgreSQL (nunca texto puro, nunca senha de rede — Regra #3).
  2. **Publicadores Nativos das 5 Redes (`publishers/`):**
     - **YouTube Shorts** e **YouTube Longo (3–5 min):** via `youtube.py` transplantado do `supoclip`, adicionando: (a) upload da Thumbnail gerada no Épico 3 (`thumbnails.set`) para os vídeos longos, (b) vínculo automático do Short para o Vídeo Longo via metadado *Related Video*, (c) postagem automática do **1º Comentário Fixado "Isca de Debate"** (`commentThreads.insert`), e (d) controle rigoroso da cota diária de 10.000 unidades (1.600 por upload).
     - **TikTok:** via `tiktok.py` (Content Posting API).
     - **Instagram Reels:** via `instagram.py` (Graph API).
     - **Facebook Reels / Vídeo:** via Graph API de Página.
     - **Crédito automático à fonte** injetado no template de descrição de cada rede.
  3. **Monitor de Claims e Disjuntor Global Automático (`claim_breaker.py` — P1):**
     - Verifica periodicamente o status de direitos/restrições dos vídeos publicados nas APIs (ex.: `videos.list?part=status,contentDetails` no YouTube para detectar `rejectionReason`, `uploadStatus`, `licensedContent` / bloqueios de Content ID).
     - **Gatilho P1 imediato:** ao detectar o primeiro claim de bloqueio ou strike em qualquer corte de uma fonte, muda o status da fonte para `pausada_por_claim`, **cancela/pausa imediatamente todos os cortes agendados daquela fonte em todas as 5 redes** e dispara alerta máximo no painel e no agente.
  4. **Painel Web "Estúdio do Criador" (Desktop + Mobile Nativo — `DESIGN.md`):**
     - Evolui o `dashboard.py` / `design/mock/fila.html` com os tokens de `design/tokens/tokens.css` (`#FF4D1C` laranja-brasa, `#F59E0B` âmbar para "pede você", fontes `Antonio`, `Archivo` e `JetBrains Mono`).
     - Telas enxutas para PC e para uso rápido de uma mão no celular:
       - **Fila e Revisão Rápida:** player vertical/horizontal com o motivo da escolha (notas de chat/áudio/visão/texto, campanha ativa, Curva do Mais Repetido), **badges e filtros acessíveis (ícone + texto, WCAG AA) dos 10 arquétipos e 3 tiers (`Ouro / Forte / Experimental`)**, galeria de thumbnails (`_thumb.png`), botões de 1 toque para aprovar, trocar gancho, pausar fonte ou **"Salvar como Exemplo Ouro"** (`golden_examples.json`);
       - **Caça Sob Demanda & Curadoria Cultural:** campo de **Busca por Pergunta Livre (*Query-Driven Clipping*)**, alternador **Modo Caça Profunda (*Deep Hunt*)** e editor simples para **`game_dossiers/`** e **piadas internas (`streamer_profiles`)**;
       - **Fontes, Campanhas e Escudo P1:** gestão de permissões, políticas por jogo e estado do disjuntor;
       - **Saúde das Redes e da GPU:** cotas restantes do dia, status das auditorias (T1) e fila da RTX 4060 Ti.
- **Critério de saída do Épico 6:** publicação ponta a ponta (em modo privado/teste ou público conforme T1) funcionando com tokens cifrados, disjuntor de claim testado (simulando um claim e verificando a pausa imediata em todas as redes) e painel web aprovado no desktop e no celular.

---

### ÉPICO 7 · O Cérebro que Aprende — Métricas (1h/24h/7d), Bandit com Esquecimento, Reciclagem A/B e Active Learning
- **Objetivo:** fechar o ciclo autônomo (P3 e P4): fazer o sistema medir o resultado real de cada corte publicado, aprender rápido o que está dando views **agora** (esquecendo o que esfriou), reciclar cortes bons que perderam no gancho inicial e acumular nosso dataset rotulado para treinar modelos próprios na RTX 4060 Ti.
- **O que será feito (`brain/`):**
  1. **Coletor de Snapshots 1h / 24h / 7d (`metrics_collector.py`):**
     - Busca automaticamente nas APIs das redes (usando `get_post_metrics` de `social/` e YouTube Analytics API dos nossos próprios canais) as visualizações, likes, comentários, tempo médio assistido e taxa de retenção nos primeiros 3s (*viewed vs swiped away*) exatamente 1h, 24h e 7d após a publicação.
  2. **Fórmula de Recompensa Anti-Clickbait (`reward.py`):**
     - Calcula a recompensa de cada corte combinando **views normalizadas pela mediana recente do canal** ponderadas pela **retenção** (penalizando cortes onde as pessoas clicam mas abandonam logo após os primeiros segundos) e multiplicadas pelo fator financeiro se fizer parte de uma **Campanha Paga ativa (CPM)**.
  3. **Bandit Contextual / Hierárquico com Esquecimento (`contextual_bandit.py`):**
     - Modela separadamente o efeito de cada variável: `jogo`, `streamer/fonte`, **`archetype` (os 10 arquétipos canônicos do Épico 3.5)**, **`tier` (`ouro`, `forte`, `experimental`)**, `formato` (Micro/Short <60s vs Vertical Estendido 60–120s vs Longo 3–5 min vs Cross-Streamer), `duração`, `horário` e `rede`.
     - Assim, se *"GTA 6 com `callback_oculto` está explodindo no YouTube Shorts independente do streamer"*, os pesos de `jogo=GTA_6` e `archetype=callback_oculto` sobem sozinhos e já priorizam cortes similares de um streamer novo!
     - Aplica **fator de desconto temporal ($\gamma$ diário / janela deslizante)** sobre observações antigas: quando um assunto esfria, o peso dele cai rápido e o sistema muda de foco em dias, reservando ~20% da cota diária para **exploração controlada** de novas apostas vindas do Radar (Épico 5).
  4. **Reciclagem A/B de Gancho — "Segunda Vida" (`ab_recycler.py`):**
     - Identifica cortes onde a retenção do corpo do vídeo (após 5s) ficou no quartil superior (>70%), mas o *swipe-away* nos primeiros 3s foi ruim.
     - Envia automaticamente um job de re-renderização trocando o **Cold Open de 1,5s**, a **Faixa de Contexto** e o **Título** (sempre preservando o **tom editorial do arquétipo**, ex.: sóbrio em `serio_realtalk`, sem spoiler em `susto_tensao`) para testar uma segunda versão (em outra rede ou após janela de respiro).
  5. **Autocaptura de Dataset Rotulado e Treino Local na RTX 4060 Ti (`active_learning.py`):**
     - Sempre que um corte fecha o snapshot de 24h/7d como **campeão** (`>=2.5x` a mediana de recompensa do canal) ou **fracasso claro** (`<=0.35x` a mediana), salva automaticamente um pacote leve em `dataset_rotulado/` contendo os vetores extraídos daquele trecho (curva do chat, curva de áudio 1 Hz, vetores de visão 2 fps, features de texto, **`archetype`**, **`tier`** e rótulo real `y`), e **sugere automaticamente campeões para enriquecer o `golden_examples.json`**.
     - Inclui script `train_local_scorer.py` (XGBoost / MLP leve / LoRA em PyTorch na 4060 Ti) que treina, além do calibrador de pesos de `score_clips.py`, um **Pré-Classificador Local de Arquétipos** que atribui probabilidades por arquétipo antes do LLM.
- **Critério de saída do Épico 7:** ciclo fechado rodando de ponta a ponta — snapshots sendo gravados no Postgres, Bandit atualizando prioridades com decaimento temporal, reciclador A/B gerando segunda versão para corte de alta retenção interna e `train_local_scorer.py` treinando sobre `dataset_rotulado/`.

---

## 5. Resumo de Decisões Tomadas (Registro Histórico)

| Data | Decisão | Impacto no Plano |
|---|---|---|
| 2026-11-16 | Nada de ferramenta paga de autoclip; OAuth sempre; módulo de risco P1 obrigatório; local/grátis primeiro na RTX 4060 Ti. | Regras pétreas do `CLAUDE.md`. |
| 2026-11-16 | Naming definido: **Picorte** (ferramenta) e **Bomba Clips** (canal de games). Design system "Estúdio do Criador" aprovado em `DESIGN.md`. | Fase A concluída. |
| 2026-11-18 | **Foco 100% em lucrar com os próprios cortes; SaaS descartado.** | Remove `workspace_id`, cobrança, termos de SaaS e E17. Simplifica o banco Postgres e libera o estudo/uso de qualquer referência open-source local. |
| 2026-11-18 | **Estratégia Evolutiva a partir de Clones Open-Source (`referencias/`).** | `mehbul/chopify` (MIT) escolhido como chassi do motor de vídeo, somado a transplantes do `fralapo/clippyme` (MIT: `live_monitor.py` e integrações) e `FujiwaraChoki/supoclip` (`reaction_layout.py`, `social/` e `mcp/`). |
| 2026-11-18 | **Incorporação das alavancas do Brainstorming BMAD (exceto Jump-Cut + Compressor).** | Entram no mapa: Sismógrafo do Chat, Cold Open 1,5s, Contexto 2s, Seamless Loop, Compilação Cross-Streamer, Sniper Crop, Layout Dinâmico, HUD/Killfeed, Micro-expressões Facecam, Funil Short→Longo 4min + Thumbnail automática, 1º Comentário Fixado, Multiplicador de Campanhas Pagas CPM, Selo Verde 15s, Demucs seletivo, Detector de React Perigoso, Score YPP, `pHash`, Reciclagem A/B de Gancho, Autocaptura de Dataset Active Learning e Modo Madrugada GPU. |
| 2026-11-19 | **Inclusão do Épico 3.5 (Motor de Caça Extraordinária) + Onda 3 nos Épicos 5, 6 e 7 (`bmad-correct-course` + `cortes-pilares`: SEGUE).** | Garante captura de momentos sutis e todos os 16→10 arquétipos gamers + 3 tiers (ex.: callback cultural tipo geladeira do GTA 6), corrige NMS pré-visão e `hud_detector`, cria `llm_scout.py`, Multi-Pista (5 pistas), `golden_examples.json`, `game_dossiers/`, Keyframes Seletivos, Query-Driven/Deep Hunt, e distribui Tendências 48h/Day-1/Consenso/Piadas Internas (Épico 5), UI de Arquétipos/Tiers (Épico 6) e Bandit por Arquétipo + Pré-Classificador Local (Épico 7). Blueprint em `_bmad-output/planning-artifacts/epic-3-5-motor-caca-extraordinaria.md`. |
