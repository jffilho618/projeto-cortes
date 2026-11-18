# Concorrentes e Referências Open-Source (Base de Código)

> Atualizado na E3.5 em 2026-11-18 com a auditoria de código-fonte dos 10 repositórios baixados em `referencias/` (pasta ignorada no git via `.git/info/exclude`).

---

## 1. Concorrente Comercial de Referência: Cortaí (`https://cortai.pro`)

Registrado em 2026-11-16 como referência visual e de funcionalidades básicas do mercado brasileiro:
- **O que faz bem (e nós também fazemos localmente de graça):**
  - Recebe links do YouTube, VODs da Twitch e do Kick, ou upload de MP4/MOV;
  - Corta lives durante a transmissão (monitor de live);
  - Detecta momentos combinando transcrição + picos de áudio + fim de frase;
  - Layout de gameplay (webcam em cima + jogo embaixo) e legendas fora do HUD com palavra ativa destacada;
  - Linha do tempo com forma de onda do áudio e trechos marcados.
- **Onde o Picorte supera o Cortaí por completo:**
  1. **Custo R$ 0 de assinatura:** roda na nossa própria GPU (RTX 4060 Ti) em vez de cobrar R$ 119,90/mês por créditos;
  2. **Detecção Multimodal avançada:** além de texto e volume de áudio, lê o **Sismógrafo do Chat da Live**, **Visão Computacional no HUD/Killfeed**, **Micro-Expressões na Facecam**, **Sniper Crop** e **Troca Dinâmica de Layout**;
  3. **Engenharia de Retenção e RPM Alto:** **Cold Open Reverso (1,5s)**, **Seamless Loop**, **Compilação Cross-Streamer** e **Funil Short Isca → Vídeo Longo de 3–5 min com Thumbnail automática**;
  4. **Escudo Anti-Strike (P1):** status de fonte, políticas de publisher (ex.: GTA 6), remoção neural de música (`Demucs`), Selo Verde 15s e Detector de React Perigoso;
  5. **Cérebro que Aprende (P3):** Radar de alta + Multiplicador de Campanhas Pagas + Bandit com esquecimento + Autocaptura de Dataset para treinar modelos próprios.

---

## 2. Auditoria de Código dos 10 Clones Open-Source (`referencias/`)

Em 2026-11-18 clonamos e inspecionamos o código-fonte de 10 projetos open-source que replicam ou substituem o Opus Clip localmente.

> **Como restaurar a pasta `referencias/` em qualquer máquina nova:**
> ```bash
> mkdir -p referencias && cd referencias
> git clone --depth 1 https://github.com/mehbul/chopify.git mehbul_chopify
> git clone --depth 1 https://github.com/fralapo/clippyme.git fralapo_clippyme
> git clone --depth 1 https://github.com/FujiwaraChoki/supoclip.git FujiwaraChoki_supoclip
> git clone --depth 1 https://github.com/AgriciDaniel/claude-shorts.git AgriciDaniel_claude-shorts
> git clone --depth 1 https://github.com/louisedesadeleer/clipify.git louisedesadeleer_clipify
> git clone --depth 1 https://github.com/artbyjazi/autoclip.git artbyjazi_autoclip
> ```

### Tabela Comparativa (Verificada no Código-Fonte)

| Repositório (`referencias/`) | Licença | Tamanho / Stack | Roda 100% Local? | O que tem de melhor no código | Papel no Picorte |
|---|---|---|---|---|---|
| **`mehbul_chopify`**<br>(`mehbul/chopify`) | **MIT** | **30 arquivos `.py`** (5,4 MB)<br>`faster-whisper`, `opencv-python`, `numpy`, `yt-dlp`, `ffmpeg` | **SIM (nativo, zero chave de API)** | • `evidence.py`: análise acústica a 1 Hz (RMS, picos, fluxo espectral, gritos >4kHz, explosões).<br>• `visual.py`: análise visual a 2 fps (movimento, cortes de cena/UI, presença e movimento de rosto).<br>• `score_clips.py`: combina texto + áudio + visão e aceita rerank via Ollama local (`--llm`).<br>• `ingest.py` / `sections.py`: modo automático para lives/VODs longas (+2h), baixando áudio em blocos de 30 min e só baixando vídeo dos trechos aprovados.<br>• `render_clips.py` / `captions.py`: exporta `9:16`, `16:9` e `1:1`, durações de `15s` a `300s (5 min)`, rastreamento facial **OpenCV YuNet**, split-screen de 2 regiões e **13 estilos de legenda `.ass`**. <br>• `dashboard.py` + `docs/AGENT-API.md`: painel web local em `127.0.0.1:8765` + CLI para agentes. | 🥇 **CHASSI PRINCIPAL DO MOTOR DE VÍDEO.** Leve, limpo, 100% Python, fácil de modificar e já nasce com a arquitetura de somar Áudio + Visão + Texto. |
| **`fralapo_clippyme`**<br>(`fralapo/clippyme`) | **MIT** | **234 arquivos `.py`** (7,8 MB)<br>FastAPI + React + Docker | Parcial (usa Gemini/Deepgram/Zernio por padrão) | • `src/clippyme/monitoring/live_monitor.py`: **Monitor completo de Lives Ao Vivo e VODs** para **Twitch, Kick e YouTube**, capturando blocos da transmissão ao vivo com retry e fila.<br>• `src/clippyme/integrations/`: `twitch_client.py`, `kick_client.py`, `youtube_feed.py`, `social_publisher.py` (`SmartScheduler` de horários nobres e espaçamento entre posts).<br>• `src/clippyme/editing/`: `hook_overlay.py`, `banner.py` (crédito/atribuição), `compose.py`. | 🥈 **DOADOR #1 (Lives Ao Vivo + Integrações Twitch/Kick/YT + Overlays).** Transplantamos `live_monitor.py`, os clientes de Twitch/Kick/YouTube e o gerador de banner de crédito/hook. |
| **`FujiwaraChoki_supoclip`**<br>(`FujiwaraChoki/supoclip`) | **AGPL-3.0** *(uso próprio local permitido)* | **421 arquivos `.py`** + 492 `.ts/.tsx` (60 MB)<br>FastAPI + Postgres + Redis + Next.js | Parcial (padrão é AssemblyAI pago; tem fallback Whisper/Ollama) | • `backend/src/media/reaction_layout.py`: **Detector automático de Facecam de canto (`find_reactor_face`)** que separa a webcam estática do streamer (`640px` topo) da ação do vídeo principal (`1280px` base) em 9:16.<br>• `backend/src/media/speaker_framing.py` & `interview_layout.py`: heurísticas maduras de estabilização de câmera.<br>• `backend/src/social/`: clientes OAuth diretos e oficiais em Python para **YouTube (`youtube.py`), TikTok (`tiktok.py`) e Instagram (`instagram.py`)**, incluindo coleta de estatísticas (`PostMetrics`).<br>• `mcp/src/supoclip_mcp/server.py`: servidor MCP pronto para controle via Claude/Gemini. | 🥉 **DOADOR #2 (Layout Facecam+Jogo, Publicadores OAuth Diretos e MCP).** Não usamos como chassi por ter muito peso morto de SaaS (billing, affiliate, PostHog), mas transplantamos `reaction_layout.py`, `social/` e o padrão do `mcp/`. |
| **`AgriciDaniel_claude-shorts`** | **MIT** | 4 arquivos `.py` + Remotion | Sim | • `scripts/snap_boundaries.py`: ajuste fino de início/fim do corte nas pausas de áudio/fala.<br>• `references/scoring-rubric.md` & `platform-specs.md`: rubrica detalhada de pontuação e limites por rede. | **Doador complementar:** lógica de `snap_boundaries.py` e rubricas de plataforma. |
| **`louisedesadeleer_clipify`** | **MIT** | 5 arquivos `.py` | Sim | • `scripts/analyze.py` & `build_pan.py`: cálculo de energia de movimento por região de interesse (ROI) e expressões matemáticas de `crop` dinâmico no FFmpeg.<br>• `scripts/detect_transients.py`: detecção rápida de transientes de áudio. | **Doador complementar:** expressões de pan/crop no FFmpeg e detecção de transientes. |
| **`artbyjazi_autoclip`** | **MIT** | 57 arquivos `.py` | Sim (Whisper + Ollama/API) | • `backend/autoclip/providers/`: abstração limpa de provedores de LLM (`ollama_provider.py`, `anthropic_provider.py`, `gemini_provider.py`, `openai_provider.py`).<br>• `backend/autoclip/cuda.py`: checagem e diagnóstico de GPU/VRAM. | **Doador complementar:** camada `providers/` para alternar facilmente entre Ollama local, Claude e Gemini, mais diagnóstico `cuda.py`. |
| **Demais 4 repositórios** (`m-hoseyny_teek`, `osbytes_reelsaw`, `SamurAIGPT`, `video-to-shorts-skill`) | MIT / AGPL | Variado | Variado | `reelsaw` é 100% TypeScript (mas tem boa suíte de `eval/baselines/` para testar cortes); `teek` é versão antiga do SupoClip; `SamurAIGPT` e `video-to-shorts-skill` são scripts básicos já superados pelo `chopify`. | **Apenas consulta pontual** (ex.: ideias de `eval/` do `reelsaw`). |

---

## 3. Mapa de "Transplante de Órgãos": De onde vem cada arquivo do nosso sistema

Esta tabela serve de guia exato para as sessões de arquitetura (E5) e implementação (Épicos 1 a 7):

| Módulo do Picorte | Base de Código / Arquivo de Origem em `referencias/` | O que vamos adicionar / modificar em cima |
|---|---|---|
| **1. Ingestão de VODs Longas (+2h) e Transcrição GPU** | `referencias/mehbul_chopify/ingest.py`, `sections.py`, `download_and_transcribe.py` | Integrar com o portão de risco (só baixa se a fonte não for `desconhecida`) e serializar o uso da VRAM (`faster-whisper` int8/float16). |
| **2. Monitor de Lives Ao Vivo e Feeds de Canais** | `referencias/fralapo_clippyme/src/clippyme/monitoring/live_monitor.py` + `integrations/twitch_client.py`, `kick_client.py`, `youtube_feed.py` | Conectar ao Sismógrafo do Chat da Live em tempo real e disparar o pipeline do `chopify` sobre os blocos capturados. |
| **3. Sinais de Áudio (`1 Hz`)** | `referencias/mehbul_chopify/evidence.py` + `referencias/louisedesadeleer_clipify/scripts/detect_transients.py` | Manter RMS, fluxo espectral e banda aguda (>4kHz de gritos/risadas) e cruzar com os picos do chat. |
| **4. Sinais de Visão Computacional (`2 fps` + Facecam + HUD)** | `referencias/mehbul_chopify/visual.py` + `referencias/FujiwaraChoki_supoclip/backend/src/media/face_detection.py` (YuNet) | Substituir o Haar Cascade antigo do `visual.py` pelo **YuNet/MediaPipe**; adicionar cálculo de **Micro-Expressões (MAR / abertura da boca)**, **Detector de HUD/Killfeed (YOLO/OCR leve)** e **Detector de React Perigoso**. |
| **5. Pontuador Multimodal + Seleção por LLM** | `referencias/mehbul_chopify/score_clips.py` + `referencias/artbyjazi_autoclip/backend/autoclip/providers/` + `referencias/AgriciDaniel_claude-shorts/scripts/snap_boundaries.py` | Somar notas de **Chat + Áudio + Visão + Texto**, suportar tanto Ollama local quanto Claude/Gemini API e ajustar bordas com `snap_boundaries.py`. |
| **6. Enquadramento 9:16 de Games (Facecam + Jogo + Layout Dinâmico + Sniper Crop)** | `referencias/FujiwaraChoki_supoclip/backend/src/media/reaction_layout.py` + `referencias/mehbul_chopify/render_clips.py` | Integrar `find_reactor_face` do `supoclip` no `render_clips.py` do `chopify`, adicionando **Troca Dinâmica de Layout** (70% facecam / split 640+1280 / tela cheia PiP) e **Sniper Crop** (zoom no quadrante de maior movimento do jogo). |
| **7. Engenharia de Retenção (Cold Open 1,5s + Contexto 2s + Seamless Loop)** | `referencias/mehbul_chopify/render_clips.py` + `referencias/fralapo_clippyme/src/clippyme/editing/hook_overlay.py` & `banner.py` | Inserir concatenação FFmpeg do ápice de 1,5s no início (Cold Open), overlay da faixa de contexto nos primeiros 2s, banner de crédito automático e corte final emendado para Seamless Loop. |
| **8. Legendas Dinâmicas `.ass` e Exportação Curta/Longa (3–5 min)** | `referencias/mehbul_chopify/captions.py` & `render_clips.py` | Ajustar margens (`caption_margin_v`) para as **áreas seguras** de Shorts, TikTok e Reels, aplicar **Selo Verde 15s** (bleep + `***` em palavrões na abertura) e gerar o par **Short (<60s) + Longo (3–5 min 16:9)** com **Thumbnail automática**. |
| **9. Controle por Agente (Claude Code e Gemini Antigravity)** | `referencias/mehbul_chopify/docs/AGENT-API.md` + `referencias/FujiwaraChoki_supoclip/mcp/src/supoclip_mcp/server.py` | Expor servidor MCP local + skill `.claude/skills/picorte-operador/SKILL.md` para comandar fila, cortes, risco e métricas pelo chat. |
| **10. Publicação OAuth nas 5 Redes e Coleta de Métricas** | `referencias/FujiwaraChoki_supoclip/backend/src/social/` (`youtube.py`, `tiktok.py`, `instagram.py`, `base.py`) + publicador Facebook Graph API | Adaptar para gravar no nosso banco PostgreSQL, preencher *Related Video* (Short → Longo), postar o **1º Comentário Fixado**, monitorar claims (disjuntor P1) e coletar snapshots de 1h/24h/7d. |
