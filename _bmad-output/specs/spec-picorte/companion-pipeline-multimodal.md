# Companion 1 — Pipeline Multimodal 4D, Visão Computacional de Games e Engenharia de Retenção

> Parte integrante do contrato `SPEC-picorte` (`CAP-1` a `CAP-9`). Define as regras de domínio e o mapeamento técnico dos módulos de ingestão, detecção 4D, enquadramento e retenção.

---

## 1. Ingestão 360º (VODs Longas, Lives Ao Vivo e Clipes de Terceiros)

| Modo de Entrada | Base de Código (`referencias/`) | Regra de Operação |
|---|---|---|
| **VODs Longas (+2h) e Arquivos Locais** (`CAP-1`) | `mehbul_chopify/ingest.py`, `sections.py`, `download_and_transcribe.py` | Fontes com mais de 2h ou >8 GB baixam inicialmente apenas a faixa de áudio mono 16 kHz + histórico de chat, divididos em blocos de 30 min com overlap de 30s (`transcript.partNNN.json`). O vídeo em alta resolução só é baixado nos intervalos exatos dos candidatos aprovados (com margem de segurança), economizando banda e disco. |
| **Monitor de Lives Ao Vivo** (`CAP-2`) | `fralapo_clippyme/src/clippyme/monitoring/live_monitor.py` + `integrations/twitch_client.py`, `kick_client.py`, `youtube_feed.py` | Vigia canais com status `liberada`, `contrato` ou `campanha_ativa`. Quando a live inicia, captura segmentos deslizantes de 3 a 5 min via `streamlink`/`FFmpeg` junto com o stream de chat IRC/WebSocket. Se o Sismógrafo do Chat + Áudio disparar, o segmento entra no topo da fila para sair enquanto a live ainda está no ar. |
| **Caçador de Clipes Virais de Terceiros** (`CAP-3`) | Novo módulo `clip_hunter.py` sobre `twitch_client.py` / YouTube API | Consulta de hora em hora os *Twitch Clips* mais vistos das fontes autorizadas. Sempre que o VOD de origem estiver disponível, extrai o trecho direto do VOD limpo (usando o `vod_offset` do clipe ou alinhamento de áudio via `louisedesadeleer_clipify/scripts/audio_align.py`) para evitar overlays/marcas d'água de terceiros e aplicar nossa própria janela de corte, Cold Open, contexto e legenda. |

---

## 2. Detecção Multimodal 4D (`CAP-4`, `CAP-5`)

O pontuador unificado (`score_clips.py`) avalia cada janela candidata (na escada de durações: `15s, 30s, 45s, 60s` para curtos e `180s, 240s, 300s` para longos) combinando 4 dimensões sincronizadas a 1 Hz:

```
Nota_Final(t0, t1) = w_chat * S_chat + w_audio * S_audio + w_visao * S_visao + w_texto * S_texto
```

### 2.1. Dimensão 1 — Sismógrafo do Chat da Live (`S_chat`)
- **Entrada:** JSON de replay do chat (Twitch/Kick/YouTube) ou comentários com timestamp (`\b\d{1,2}:\d{2}\b`).
- **Métricas a 1 Hz:**
  - `vel_zscore(t)`: taxa de mensagens/segundo normalizada pela mediana e desvio absoluto mediano (MAD) dos últimos 10 minutos da própria live;
  - `emote_burst(t)`: proporção de mensagens contendo padrões de risada/choque (`KKKK+`, `LUL`, `OMEGALUL`, `CLIP`, `MENTIRA`, `CARACA`, `WTF`, `???`, `F`, `GG`).
- **Papel:** pré-filtro ultrarrápido em CPU (<1s para 6h de live). Picos onde `vel_zscore > 3.5` garantem que o trecho entre na lista de candidatos mesmo se o streamer estiver calado.

### 2.2. Dimensão 2 — Evidência Acústica (`S_audio`)
- **Base:** `mehbul_chopify/evidence.py` (`AudioTimeline` em `audio_features.npz`) + `louisedesadeleer_clipify/scripts/detect_transients.py`.
- **Métricas a 1 Hz:** energia RMS em dB acima da linha de base móvel, fluxo espectral (*spectral flux*), taxa de cruzamento por zero (ZCR) e energia na banda aguda (`>= 4000 Hz`, que captura gritos, risadas agudas e explosões).

### 2.3. Dimensão 3 — Visão Computacional de Games (`S_visao`)
- **Base:** `mehbul_chopify/visual.py` evoluído para `visual_games.py` + `FujiwaraChoki_supoclip/backend/src/media/face_detection.py` (`YuNet`).
- **Sub-detectores rodando em frames amostrados (2 fps para varredura geral; 10 fps nos candidatos pré-selecionados):**
  1. **Termômetro de Micro-Expressões na Facecam:**
     - Localiza a caixa estacionária da webcam (`find_reactor_face` do `supoclip`).
     - Extrai landmarks faciais (`MediaPipe FaceMesh` / `YuNet`) e calcula:
       - **MAR (*Mouth Aspect Ratio*):** abertura vertical/horizontal da boca (grito, susto, gargalhada);
       - **Deslocamento brusco da cabeça:** variação rápida do centroide do rosto (streamer caindo para trás na cadeira, levantando ou levando as mãos ao rosto).
  2. **Detector Visual de HUD / Killfeed (`hud_detector.py`):**
     - Monitora as zonas periféricas de interface (canto superior direito, centro-inferior e centro da tela) usando OCR leve / templates / detector YOLO nano para identificar banners de evento (*Kill*, *Eliminated*, *Victory*, *Wasted*, *Busted*, *Clutch*, *Defeat*, conquistas).
  3. **Ação e Corte Visual no Gameplay:**
     - Diferença de histograma e fluxo óptico denso na região do jogo (fora da facecam) para medir intensidade de ação.

### 2.4. Dimensão 4 — Análise Semântica, Roteador de IA na UI e Ajuste de Bordas (`S_texto`)
- **Base:** `mehbul_chopify/score_clips.py` + `artbyjazi_autoclip/backend/autoclip/providers/` + `AgriciDaniel_claude-shorts/scripts/snap_boundaries.py`.
- **Seletor de Motor de IA na UI (`llm_router.py`):**
  Na interface do "Estúdio do Criador" (e por parâmetro no CLI/MCP), o operador escolhe livremente entre **4 modos de operação** para a etapa de IA textual:
  1. **Só `Ollama` (100% Local na GPU, ex.: `qwen2.5:7b`):** roda localmente na RTX 4060 Ti (ou `qwen2.5:3b` na GTX 1650).
  2. **Só `Claude`:** executa via CLI local autenticada na assinatura mensal do Claude Code (`claude -p --output-format json`, custo R$ 0 de API) ou via `ANTHROPIC_API_KEY` se configurada.
  3. **Só `Gemini`:** executa via CLI local autenticada na assinatura mensal do Antigravity (`agy -p --output-format json`, custo R$ 0 de API) ou via `GOOGLE_API_KEY` se configurada.
  4. **Modo Dupla / Pipeline ("Um Filtrando + Outro Acompanhando/Lapidando"):** o operador seleciona o **Motor 1 (Filtro/Triagem)** e o **Motor 2 (Acompanhamento/Decisão Final e Copywriting)**. Exemplos:
     - `Ollama` filtra os 40 candidatos brutos para os top 8 → `Claude` (ou `Gemini`) escolhe os campeões e escreve os títulos magnéticos, a faixa de contexto de 2s, as 3 palavras da thumbnail e o 1º comentário;
     - `Claude` + `Gemini` trabalhando juntos (um propõe os cortes e títulos, o outro revisa/acompanha e dá o veredito final).
- **Operação:** o motor recebe os candidatos pré-selecionados com a transcrição + resumo dos picos de chat/áudio/visão, classifica o tipo de momento (`engraçado`, `jogada_épica`, `polêmica_treta`, `susto_reação`, `história_curiosidade`), avalia se o trecho se sustenta sozinho e escreve o título, a faixa de contexto de 2s e o 1º comentário de debate.
- **Snap de Bordas:** `snap_boundaries.py` ajusta o timestamp inicial e final para coincidir com pausas de silêncio ou fim de pontuação, nunca cortando palavras no meio.

---

## 3. Reenquadramento 9:16 de Games (`CAP-6`)

Baseado na fusão de `FujiwaraChoki_supoclip/backend/src/media/reaction_layout.py` com `mehbul_chopify/render_clips.py`:

1. **Detecção Automática da Facecam (`find_reactor_face`):**
   - Identifica a região da webcam nos cantos/bordas da transmissão 16:9.
2. **Troca Dinâmica de Layout no Mesmo Corte (*Dynamic Layout Switching*):**
   - A cada sub-segmento do corte (com histerese mínima de 3s para evitar cortes frenéticos), o renderizador escolhe entre 3 composições 1080×1920:
     - **Modo História (`70% Facecam / 30% Jogo`):** quando o streamer está conversando/narrando e o movimento no jogo é baixo;
     - **Modo Reação Padrão (`Split 640px Facecam no topo / 1280px Jogo na base`):** quando há fala/reação simultânea à ação no jogo;
     - **Modo Ação / Cutscene (`100% Jogo com Facecam em PiP num canto seguro`):** quando a ação visual ou cutscene do jogo domina e o streamer está apenas reagindo.
3. **Sniper Crop (Zoom Dinâmico na Ação do Jogo):**
   - Em vez de recortar estaticamente o centro `(x = width/2)` da área 16:9 do jogo, calcula o centroide suavizado (filtro passa-baixa / média móvel exponencial) do mapa de movimento/saliência da cena, deslocando suavemente a janela de recorte para mostrar o quadrante onde o evento aconteceu.

---

## 4. Engenharia de Retenção e Formatos (`CAP-7`, `CAP-8`, `CAP-9`)

1. **Cold Open Reverso (Primeiros 1,5s):**
   - Localiza o pico máximo de `S_audio + S_visao` dentro do corte (desde que ocorra após os primeiros 6s), extrai uma fatia de `1,2s a 1,8s` desse clímax e a insere em `t = 0:00` seguida de transição seca para o início real do corte.
2. **Faixa de Contexto Instantâneo (Primeiros 2,0s):**
   - Renderiza no topo seguro do vídeo, durante os primeiros 2,0s após o Cold Open, uma pílula visual de alto contraste (`DESIGN.md`) com até 8 palavras explicando o contexto imediato (gerado pelo LLM a partir dos 5–10 minutos anteriores da transcrição).
3. **Seamless Loop (Encerramento Conectado):**
   - Nos cortes verticais (<60s), ajusta o corte final na última pausa de fala ou cria uma ponte verbal/visual com a primeira frase pós-Cold Open para favorecer o replay automático.
4. **Compilação Cross-Streamer (`CAP-8`):**
   - Usa alinhamento de fingerprint acústico (`louisedesadeleer_clipify/scripts/audio_align.py`) ou de histograma visual para encontrar o mesmo evento de jogo/trailer em múltiplos VODs/clipes e monta uma sequência cronológica ou em grade das reações.
5. **Funil "Short Isca (<60s) → Corte Longo (3–5 min 16:9)" + Fábrica de Thumbnail (`CAP-9`):**
   - Quando um arco de gameplay sustenta 3 a 5 minutos de interesse contínuo, o sistema exporta:
     - O **Corte Longo 16:9 (1920×1080, 3–5 min)** para o YouTube principal;
     - O **Short Isca 9:16 (1080×1920, 35–55s)** contendo o melhor momento daquele arco, configurado para apontar seu campo `Related Video` para o Corte Longo;
     - A **Thumbnail Automática 1280×720 (`thumbnail_factory.py`):** seleciona o frame com maior score de expressão facial (MAR) do streamer, remove o fundo da facecam (`rembg`), sobrepõe em destaque sobre o frame de maior ação do jogo e aplica de 2 a 3 palavras em caixa alta com a fonte `Antonio` (`DESIGN.md`), seguindo as regras da skill `youtube-thumbnail-design`.
