# Deferred Work — Picorte

## Deferred from: code review of epics.md (2026-11-20)

- **W1 · Duplicação de arquivos espelho entre raiz e `picorte/engine/`** (`render_clips.py`, `projects.py`, `ingest.py`, `score_clips.py`, `chopify.py`) — pré-existente desde o Épico 1 (`AD-1`); mantidos sincronizados por SHA-256 até refatoração de empacotamento.
- **W2 · Escopo de cadência/Cool-Down por `social_account_id` (múltiplos canais por rede) e migração para tabela de banco** — `social_accounts` entra em uso real com OAuth no Épico 6; no Épico 4 o estado fica em arquivo runtime (`work/cadence_state.json`) protegido por `FileLock` + escrita atômica e evolui para `social_account_id` no Épico 6 (Story 6.1, que continua depois do E5 pela mudança de 2026-11-21).

## Descobertos ao aplicar a Onda 1 do code review do Épico 4 (2026-11-20)

- **W3 · Cold Open Reverso não é renderizado no vídeo** — `build_cold_open_plan` (Épico 3, `3.4`) só gera o plano; nenhuma etapa do render monta o teaser no 0:00. O Selo Verde já entrega `cold_open_bleeps` + `cold_open_censored_words` na linha do tempo do teaser, prontos para quando o render existir. Enquanto isso, o veredito P1 usa `has_cold_open=False`.
- **W4 · ✅ Resolvido em 2026-11-20** — `clean_music_in_render` roda em todo corte final e o `demucs 4.1.0` foi instalado no Python global do PC de mesa (torch `2.6.0+cu124` intacto, RTX 4060 Ti). Validação real com voz sintetizada + acorde: música −33 a −44 dB, correlação com a voz 0,43 → 0,90, ~8s por 11s de áudio. Notas: áudio sai mono quando há cirurgia; trecho só de música (sem voz) cai em `human_review` ("quase mudo"), o que é intencional. No notebook Linux, instalar com `python -m pip install demucs` (opcional, como YOLO/HSEmotion).
- **W5 · Projetos preparados antes do D1 não têm `source_gate`** — o Pacote do Dia barra a exportação deles (`source_unlinked`). Basta rodar o `prepare` de novo para o portão registrar a fonte. **Nota 2026-11-21:** a Story 6.8 mostra esses projetos como "rodar o prepare de novo", em vez de falha muda.
- **W7 · Chat da Twitch para o Sismógrafo → Épico 5 (Story 5.2, monitor de lives)** — até 2026-11-20 o dono só usou fontes do YouTube, cujos VODs são uploads comuns sem chat. Ao construir o monitor de lives ao vivo, capturar o chat da Twitch junto (escolher ferramenta com aprovação, regra 9). Ver `auditoria-e3-done-vs-ligado-2026-11-20.md` (A2). Instalado em 2026-11-20 só o `yt-dlp-ejs` 0.8.0 (+ `--js-runtimes node` via `ytdlp_base_cmd`); mesmo assim os replays de live testados do YouTube não têm chat salvo. Reavaliar no E5 os extras do `yt-dlp[default]` que podem servir para lives: `websockets` e `pycryptodomex` (brotli/certifi/mutagen sem ganho para o uso atual).
- **W8 · Keyframes (LLM vê 3 frames) com Gemini** — Gemini sem cota em 2026-11-20; testar o mesmo fluxo quando voltar e comparar fidelidade/consumo com o Sonnet (A6 da auditoria).
- **W9 · Painel "Saúde do motor" → ✅ absorvido pela Story 6.7 (2026-11-21, `sprint-change-proposal-2026-11-21-painel.md`)** — o canário semanal e a atualização diária do `yt-dlp` aparecem na 6.7 como capacidades travadas até existirem. Texto original: decisão do dono em 2026-11-20. Mostrar, por projeto, o estado de cada parte do motor (✅ funcionou · ➖ não se aplica · ⚠️ falhou + motivo): download, transcrição, portão P1, Editor-Chefe/LLM (incl. lote parcial), Full-VOD Scout, visão de games (proxy/MAR/HUD), prosódia, comentários, chat, heatmap/capítulos, dossiê/exemplos ouro, thumbnail, render e escudo P1. Somar atualização diária do `yt-dlp` (`yt-dlp[default]`) e um canário semanal contra um VOD conhecido que alerta quando um sinal que funcionava para. Motivo: a visão de games ficou desligada em todos os projetos sem nenhum aviso (A1 da auditoria). Os dados de saúde devem ser gravados no `project.json` desde já, para o painel do E6 só exibir.
- **W6 · Falso positivo do detector de sangue em cenas dominadas por vermelho-escuro saturado** — a thumbnail falha fechada (sem thumb automática) nesses casos. Aceito por P1 > P3; revisitar com modelo próprio no Épico 7.

## Do brainstorming 2b do motor de seleção, sem destino na leva 1 (2026-11-21)

Fonte: `_bmad-output/brainstorming/brainstorm-arquetipos-e-motor-de-selecao-2026-11-21/` e `sprint-change-proposal-2026-11-21.md`.

- **W10** — Arquétipos `wholesome` (momento fofo, gratidão, marco de inscritos) e `licao_dica` (dica/tutorial para Longo): avaliar com o gabarito da 3.6.1 se estão sendo perdidos.
- **W11** — Arquétipo `perda_dramatica` (perde o personagem do RP, run de anos): hoje cai em `rage_tilt`/`clutch_fail`; criar só se o gabarito mostrar perda.
- **W12** — Separar o riso do streamer do riso de convidado/jogo (diarização leve) na prosódia.
- **W13** — Casar fala com chat: detectar quando o streamer lê uma mensagem do chat em voz alta (sinal de `chat_trolagem` ou filtro de leitura chata).
- **W14** — Cota de diversidade por arquétipo por canal/dia na fila de publicação (Épico 6).
- **W15** — Telas de morte/WASTED/game over no dossiê de cada jogo como sinal visual de nobada.

## Pesquisa de ferramentas de vídeo programático (2026-11-21)

- **W16 · HyperFrames para efeitos animados do Épico 3.7 (candidato; Remotion como 2ª opção)** — pesquisa pedida pelo dono.
  - **O que é:** o [HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen, Apache-2.0) transforma HTML + CSS + GSAP em vídeo.
  - **Como renderiza:** Chrome invisível quadro a quadro + FFmpeg, com NVENC via `--gpu`. Exporta com transparência (WebM VP9 / ProRes 4444).
  - **Requisitos:** Windows e Linux, Node 22+ e FFmpeg. Tem player embutível (`@hyperframes/player`).
  - **Decisão:**
    - **não** substitui o render principal (FFmpeg + NVENC + `.ass` é mais rápido para o corte inteiro);
    - **não** entra no painel (a stack do painel já está decidida).
  - **Uso proposto — modelo híbrido nas histórias 3.7.1 e 3.7.5:**
    - renderizar só os 2–3 s de cada efeito (transição do Cold Open, faixa 2s animada, freeze + seta, variação de template por arquétipo; talvez a tipografia da thumbnail) com fundo transparente;
    - o FFmpeg sobrepõe, como hoje.
  - **Por que HyperFrames e não Remotion:**
    - licença open source de verdade (o Remotion é grátis para pessoa física, mas tem licença própria e uma mudança anunciada para a versão 5.0);
    - usa GSAP, que já está na stack.
    - O Remotion só ganharia se quiséssemos compartilhar componentes React entre o painel e o vídeo.
  - **Cuidados se adotar:**
    - as skills de agente que vêm com o HyperFrames só entram com aprovação (regra 9);
    - desligar a telemetria da CLI (`HYPERFRAMES_NO_TELEMETRY=1`, `HYPERFRAMES_NO_UPDATE_CHECK=1`);
    - o render passa pela fila serial (`vram_runner`, AD-3);
    - custo R$ 0.
  - **Não confirmado:** a versão atual e a data do primeiro lançamento (o GitHub mostrou cerca de 87 mil estrelas; conferir).
  - **Próximo passo ao iniciar o 3.7:** prova de conceito de ~1 h na 4060 Ti (faixa 2s + freeze/seta com transparência), medindo o tempo por efeito antes de decidir.
