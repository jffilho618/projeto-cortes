# Visão do produto — projeto-cortes (Picorte)

**Data:** 2026-11-16 (atualizado na E3.5 em 2026-11-18) · **Consumidores:** Spec (`bmad-spec`, E4), Arquitetura de Fusão (`bmad-architecture`, E5), Épicos 1 a 7 (E6–E13). Os pilares (`pilares.md`) limitam esta visão; ela não os substitui.

## 1. Nas palavras do dono

> "A ferramenta é como uma rede neural aprendendo, sempre perseguindo visualizações. Ela percebe sozinha o que está dando certo, em qualquer variável: um estilo de corte, um streamer, um jogo, um formato (curto ou longo), uma rede, um assunto. Exemplos: 'cortes de GTA 6 estão dando bom, independente do streamer'; 'agora o que dá view é o novo jogo do El Gato'; 'mudou, agora são cortes do Coringa jogando'; 'semana que vem tem mundial de Free Fire, então nessa data o assunto é Free Fire'."

> **Expansão E3.5 (2026-11-18):** "A prioridade é ganhar dinheiro com cortes e não com vendas de assinaturas. O MVP imediato é colocar o clone open-source funcionando para trazer os primeiros cortes, depois conectar ao agente (Claude/Gemini), e ir evoluindo camada por camada até terminar sendo uma ferramenta 100% autêntica: sabe fugir dos strikes, busca streamers/jogos/assuntos em alta, busca clipes já prontos e virais de outras pessoas, assiste lives encerradas e lives ao vivo, detecta momentos engraçados/importantes/polêmicos pelo texto, pelo áudio, pelo vídeo e pelo chat, e publica sozinha."

---

## 2. Mapa Completo de Capacidades do Sistema (Consolidado na E3.5 + Brainstorming BMAD)

*Nota de escopo (decisão explícita do dono em 2026-11-18):* **Foco 100% em lucrar com os próprios canais de cortes** (começando pelo **Bomba Clips** em games). SaaS e multi-tenant (`workspace_id`) saem de cena. **Único item excluído do brainstorming:** *Jump-Cut de Tempos Mortos + Compressor de Áudio*. Todos os demais itens abaixo fazem parte do mapa oficial:

### A. Olho para Fora — Radar de Atenção, Lives Ao Vivo e Caçador de Clipes
1. **Radar de Tendências e Calendário de Eventos:**
   - Monitora pelas APIs oficiais o que está em alta **agora**: jogos e streamers com maior audiência na **Twitch**, vídeos em alta na categoria Games pela **YouTube Data API** (`videos.list?chart=mostPopular`), e um **calendário de lançamentos, atualizações e campeonatos** (ex.: lançamento de GTA 6, mundial de Free Fire).
   - Respeita as políticas da API do YouTube (dados de terceiros expiram em até 30 dias — regra III.E.4.d; usa o ranking que a própria API entrega sem criar métricas derivadas proibidas sobre canais alheios — III.E.2.a / III.E.4.h).
2. **Ingestão de Lives Encerradas (VODs) E Lives AO VIVO:**
   - **VODs / Vídeos longos:** processamento inteligente de vídeos longos (+2h), baixando inicialmente apenas o áudio + chat em blocos de 30 min para pontuar candidatos e baixando o vídeo pesado apenas nos trechos aprovados (padrão já existente no `mehbul/chopify`).
   - **Monitor de Lives AO VIVO (Twitch, Kick e YouTube):** inspirado e transplantado do `fralapo/clippyme` (`live_monitor.py`) com `streamlink` + `FFmpeg`. Vigia canais autorizados quando entram ao vivo, grava janelas deslizantes de 3–5 minutos e, quando detecta explosão em tempo real (chat + áudio + visão), gera o corte enquanto a live ainda está no ar para sair antes da concorrência.
3. **Caçador e Transformador de Clipes Já Prontos de Terceiros:**
   - Busca *Twitch Clips* e cortes que já estão começando a viralizar na hora/dia dentro dos jogos/streamers autorizados.
   - Passa pelo mesmo avaliador multimodal e aplica **re-transformação completa** (busca o trecho limpo na VOD quando disponível ou remove marcas d'água, aplica novo enquadramento, nova legenda, Cold Open próprio, faixa de contexto e título nativo — cumprindo o **P2**).
4. **Detector de "Treta / Pingue-Pongue" entre Streamers:**
   - Quando a transcrição da live do Streamer A cita o nome de outro streamer mapeado (Streamer B), o sistema sinaliza e busca na live/VOD recente do Streamer B a resposta ou reação para montar cortes combinados dos dois lados da história.
5. **Multiplicador de Campanhas Pagas de Clipping (Bounties / CPM):**
   - Cadastro de campanhas ativas (ex.: Whop, ações de lançamento ou contratos que pagam R$ X por 1.000 views), com valor de CPM, regras obrigatórias (hashtags, menções) e data de expiração. Enquanto ativa, a campanha multiplica a prioridade daquela fonte no Bandit.

### B. Detecção Multimodal de Momentos (Chat + Áudio + Visão Computacional + Texto)
1. **Sismógrafo do Chat da Live (Twitch / Kick / YouTube Chat Replay + "Most Replayed"):**
   - Antes de gastar GPU pesada, lê o histórico/stream do chat da live e comentários com timestamp (`04:12`). Picos de velocidade de mensagens por segundo (`msgs/s` > 4x a mediana) com explosão de risadas/reações (`"KKKK"`, `"LUL"`, `"CLIP IT"`, `"MENTIRA"`, `"???"`) identificam em 1 segundo de CPU os candidatos a corte.
2. **Sinais Acústicos (`evidence.py` do `chopify` tunado):**
   - Linha do tempo de áudio a 1 Hz medindo energia RMS, picos súbitos, fluxo espectral e banda aguda (>4 kHz para gritos, risadas e explosões), permitindo achar momentos épicos mesmo quando quase não há fala.
3. **Sinais de Visão Computacional (Especialidade do Dono + `visual.py` tunado):**
   - **Termômetro de Micro-Expressões na Facecam:** abertura da boca (*Mouth Aspect Ratio* — MAR), olhos arregalados e velocidade de deslocamento da cabeça/corpo (ex.: streamer caindo para trás na cadeira ou levando a mão à cabeça).
   - **Detector Visual de HUD / Killfeed:** detecção leve (YOLO / OCR / templates) nas regiões de interface do jogo para capturar eventos de *Kill*, *Victory*, *Wasted*, *Clutch*, conquistas ou placar mesmo quando o streamer fica em silêncio de tensão.
   - **Ação e Mudança Visual:** picos de movimento (*optical flow* / diferença de frames) e cortes de cena.
4. **Análise Semântica por Texto (LLM Local via Ollama ou API Claude/Gemini):**
   - Avalia os candidatos pré-filtrados pelos sinais acima para encontrar histórias fechadas, piadas, polêmicas, conselhos ou revelações, garantindo que o corte faça sentido sozinho e ajustando as bordas para pausas naturais da fala.

### C. Engenharia de Retenção, Enquadramento e Formato (Curto + Longo)
1. **Cold Open Reverso (In Media Res Automático — Primeiros 1,5s):**
   - Extrai 1,5s do ápice visual/sonoro do meio do corte e cola no segundo `0:00` com transição seca antes do início da história, travando o espectador para vencer a barreira do *swipe-away* nos primeiros 3s.
2. **Faixa de Contexto Instantâneo ("Narrador Invisível" nos Primeiros 2s):**
   - O LLM lê os minutos anteriores da live e gera uma faixa curta de contexto nos primeiros 2 segundos do vídeo (ex.: *"4ª hora tentando passar dessa missão sem morrer"*).
3. **Seamless Loop (Loop Infinito para Shorts/Reels/TikTok):**
   - Escolhe o ponto final do corte vertical de modo que a última frase ou ação se conecte com a primeira palavra do segundo `0:00`, induzindo replay automático e retenção acima de 100%.
4. **Enquadramento Inteligente de Games (Troca Dinâmica de Layout + Sniper Crop):**
   - Parte do detector de webcam de canto (`reaction_layout.py` do `supoclip` + YuNet/MediaPipe) e evoluído com Visão Computacional:
     - **Troca Dinâmica de Layout no mesmo corte:** alterna automaticamente entre foco maior na facecam (70% quando o streamer conta uma história), split-screen Facecam (`640px`) + Gameplay (`1280px`) na reação e tela cheia com PiP durante cutscenes/tiroteios intensos;
     - **Sniper Crop (Zoom Dinâmico):** usa o mapa de movimento/saliência do jogo para dar zoom suave no quadrante onde a ação aconteceu, em vez de recortar sempre o centro cego da tela 16:9.
5. **Compilação Cross-Streamer Automática:**
   - Em eventos grandes (trailers de GTA 6, anúncios, bugs famosos), alinha por áudio/imagem do jogo a reação de 3 a 5 streamers diferentes ao mesmo momento num único corte — blindagem máxima de transformação real no YPP (**P2**).
6. **Funil "Short Isca → Corte Longo de 3–5 min" + Fábrica Automática de Thumbnail:**
   - Gera tanto os cortes verticais (<60s para Shorts, TikTok, Reels e FB) quanto **cortes longos horizontais 16:9 de 3–5 min** para o YouTube (onde o RPM de AdSense é de 10x a 30x maior).
   - O Short publicado aponta automaticamente para o vídeo longo de 3–5 min através do campo nativo *Related Video* do YouTube Shorts.
   - **Fábrica Automática de Thumbnail (Visão Computacional):** para cada corte longo, seleciona automaticamente o frame de maior expressão facial na facecam + o frame mais impactante do jogo, recorta o streamer (`rembg` na GPU) e compõe uma thumbnail de alto CTR com até 3 palavras no estilo do nosso `DESIGN.md`.
7. **1º Comentário Fixado "Isca de Debate":**
   - Gera junto com cada corte uma pergunta polarizadora sobre o lance (*"Foi bug do jogo ou erro dele no 0:14?"*) para ser postada automaticamente no primeiro comentário, mantendo o vídeo rodando em loop enquanto o público debate.

### D. Escudo Anti-Strike e Anti-Desmonetização (P1 Inegociável)
1. **Portão de Status da Fonte e Políticas por Publisher/Jogo:**
   - Fonte `desconhecida` **não é baixada nem processada** até mudar de status (`liberada`, `contrato`, `campanha ativa`, `gameplay próprio`). Se estiver em alta no Radar, o sistema apenas emite alerta dizendo o que falta para liberá-la.
   - Aplica as regras cadastradas por publisher/jogo (ex.: Rockstar/GTA 6: bloqueio de final, compilações de cutscenes vazadas e janela de spoiler).
2. **Cirurgia Seletiva de Música com `Demucs` na GPU:**
   - Detecta trechos do corte onde há música licenciada ao fundo (ex.: rádio de carro no GTA). Em vez de descartar o corte ou usar truques proibidos (A2), roda separação neural de fonte (`Demucs`) **apenas nos segundos afetados**, removendo a música e preservando a voz limpa do streamer.
3. **Filtro "Selo Verde 15s" (Áudio + Visão Computacional):**
   - **Visão:** checa os primeiros 15 segundos contra sangue/violência gráfica explícita que causa desmonetização no YouTube; se detectar, desloca o gancho ou aplica blur localizado.
   - **Áudio/Texto:** se houver palavrão pesado nos primeiros 15s da transcrição, aplica micro-bleep/mute de `0,2s` na palavra e substitui por `***` na legenda queimada.
4. **Detector Visual de "React Perigoso":**
   - Classificador visual que identifica quando o streamer minimizou o jogo e abriu navegador/YouTube/TikTok de terceiros dentro da live, bloqueando cortes de react de conteúdo alheio protegido.
5. **Score Mínimo de Transformação YPP + Deduplicação Perceptual (`pHash`):**
   - Só aprova para a fila se atingir pontuação mínima de transformação (P2) e se o `pHash`/embedding confirmar que aquele momento já não foi postado antes (ex.: vindo de VOD e depois de Twitch Clip).
6. **Crédito Automático + Monitor de Claims com Disjuntor Global:**
   - Insere crédito automático à fonte na descrição de cada rede e monitora claims/strikes nos vídeos publicados. Ao primeiro claim de bloqueio ou strike, **pausa automaticamente todos os cortes daquela fonte em todas as redes**.

### E. Olho para Dentro — Aprendizado Contínuo, Reciclagem A/B e Treino Próprio
1. **Coleta de Snapshots (1h / 24h / 7d) e Bandit Contextual/Hierárquico com Esquecimento:**
   - Mede views, retenção média e taxa de *swipe-away* nos primeiros 3s.
   - O modelo separa o efeito de cada variável (`jogo × streamer × tipo de momento × formato curto/longo × duração × horário × rede`) e aplica fator de esquecimento para abandonar rápido o que esfriou e apostar no que está subindo, ponderado por retenção (sem premiar clickbait vazio) e pelo multiplicador de campanhas pagas ativas.
2. **Reciclagem A/B de Gancho ("Segunda Vida"):**
   - Se um corte teve ótima retenção após os 5s (>70%), mas perdeu público nos primeiros 3s (*swipe-away* alto), o sistema agenda automaticamente uma "segunda vida" re-renderizando apenas os primeiros 2 segundos (novo Cold Open + novo título) para teste A/B.
3. **Autocaptura de Dataset Rotulado (*Active Learning* na RTX 4060 Ti):**
   - Todo corte publicado que superar `3x` a mediana recente do canal (classe `positivo`) ou afundar nos primeiros 3s (classe `negativo`) tem seus vetores de áudio, visão, chat e texto salvos automaticamente em `dataset_rotulado/` para treinar e refinar nossos próprios classificadores locais na RTX 4060 Ti.
4. **Modo "Madrugada na 4060 Ti" (GPU Idle Worker):**
   - Gerencia a fila da GPU (8 GB VRAM) rodando um modelo pesado por vez (serializado) e priorizando tarefas pesadas (VODs longas, `Demucs`, re-treino de modelo) quando o PC de mesa estiver ocioso ou de madrugada.

---

## 3. Aderência aos Pilares (`cortes-pilares` — modo Julgar, 2026-11-18)

| Pilar / Anti-pilar | Efeito | Motivo |
|---|---|---|
| **P1 Canal protegido** | **reforça** | Soma portão de fonte `desconhecida`, políticas por publisher, remoção real de música com `Demucs` (sem truque), Selo Verde 15s, Detector de React Perigoso, Deduplicação `pHash` e pausa global automática. |
| **P2 Obra própria e nativa** | **reforça** | Cold Open, Faixa de Contexto 2s, Compilação Cross-Streamer, Layout Dinâmico + Sniper Crop, Score mínimo de Transformação YPP e títulos/áreas seguras por rede tornam cada corte inconfundivelmente transformado. |
| **P3 Dados de agora decidem** | **reforça** | Une Radar externo + Sismógrafo do Chat + Bandit com esquecimento + Multiplicador de Campanhas + Reciclagem A/B baseada na retenção real de 3s vs 30s. |
| **P4 Inteligência nossa** | **reforça** | Base open-source MIT local (`chopify` + `clippyme`) tunada com Visão Computacional própria e Autocaptura de Dataset Rotulado para treinar modelos próprios na 4060 Ti. |
| **P5 Autônomo** | **reforça** | Do radar e monitor de live até a publicação, 1º comentário e coleta de métricas, tudo opera sozinho com revisão opcional no PC/celular. |
| **A1 Editor manual** | **neutro** | Toda edição (Cold Open, Loop, Sniper Crop, Layout Dinâmico, Thumbnail) é 100% algorítmica; o painel só permite ajustes leves de revisão. |
| **A2 Fábrica de spam / truques** | **reforça** | `Demucs` remove a música de verdade (permitido pelo A2) em vez de alterar pitch/velocidade; Score de Transformação e `pHash` barram reupload cru e repetido. |
| **A3 Agendador genérico** | **neutro** | Foco exclusivo em cortes de vídeo (curtos e longos) e seus metadados. |
| **A4 Contornar APIs** | **neutro** | Publicação e leitura de métricas pelas APIs oficiais via OAuth; plano B manual documentado enquanto auditorias não saem. |
| **A5 Números inventados** | **neutro** | Sem SaaS/marketing de venda; painel exibe apenas métricas reais coletadas das redes. |

**Veredito final (`cortes-pilares`): SEGUE.**
