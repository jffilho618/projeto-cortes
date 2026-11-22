# Product

<!-- impeccable:product-schema 1 -->

## Platform

web + local GPU engine

Só desktop (decisão do dono, 2026-11-21): o painel roda local no computador, em Windows 11 (PC de mesa, alvo 2560×1440) e Linux (notebook). Não há layout de celular. Substitui a decisão de 2026-11-16 (desktop e celular).

## Stack

Arquitetura híbrida local-first (definida na E3.5 em 2026-11-18 e detalhada na E5):
- **Motor de Vídeo e IA (Python na GPU — RTX 4060 Ti 8 GB):** chassi baseado no `mehbul/chopify` (MIT: `faster-whisper`, `opencv-python`/YuNet, `numpy`, `yt-dlp`, `FFmpeg/NVENC` com legendas `.ass`), turbinado com módulos transplantados do `fralapo/clippyme` (MIT: `live_monitor.py` para lives ao vivo na Twitch/Kick/YouTube) e do `FujiwaraChoki/supoclip` (`reaction_layout.py` para Facecam + Jogo, `social/` para publicação OAuth e `mcp/` para controle por agente), mais detectores próprios de **Visão Computacional** (HUD/Killfeed, micro-expressões na facecam, Sniper Crop, Detector de React Perigoso, Fábrica de Thumbnails) e **Cirurgia de Áudio** (`Demucs` seletivo + Selo Verde 15s).
- **Cérebro e Persistência (banco local `picorte.db`, SQLite; PostgreSQL opcional — decisão do dono, 2026-11-21):** banco relacional para fontes, políticas por publisher/jogo, campanhas pagas de clipping, vídeos/lives, cortes, publicações, snapshots de métricas (1h/24h/7d), claims e pesos do Bandit.
- **Frontend ("Estúdio do Criador"):** painel web só desktop (Windows e Linux), React + FastAPI, onde cada função aparece com o status real decidido pelo backend (ligado, parcial, travado; travado nunca é falso). Visual definido em `DESIGN.md`.

## Users

**Único usuário (Escopo Total):** o próprio dono (Bomba), operador de vários canais de cortes separados por nicho, começando em **games** com o canal **Bomba Clips**. Ele não edita vídeo à mão. O trabalho dele é supervisionar a máquina (ou comandá-la via Claude / Gemini), mudar o status de permissão das fontes, cadastrar campanhas pagas de clipping, revisar cortes quando a revisão estiver ligada e acompanhar o retorno.

**Fora de escopo:** SaaS, venda de assinaturas, multi-tenant (`workspace_id`), billing e onboarding de terceiros (decisão de 2026-11-18: foco 100% em lucrar com os próprios cortes).

## Product Purpose

O **Picorte** (pico + corte) transforma vídeos longos (VODs, lives gravadas), **lives ao vivo** e **clipes virais de terceiros** em cortes de altíssima retenção para YouTube Shorts, YouTube Longo (3–5 min com thumbnail automática), TikTok, Instagram Reels e Facebook. Ele detecta momentos por **Chat + Áudio + Visão Computacional + Texto**, aplica engenharia de retenção (Cold Open Reverso 1,5s, Faixa de Contexto 2s, Seamless Loop, Funil Short → Vídeo Longo), publica, mede e **aprende o que está dando views e dinheiro agora** (em qualquer variável: jogo, streamer, formato, rede, assunto, horário, campanha paga), passando a cortar mais disso e esquecendo rápido o que esfriou — tudo protegido por um **Escudo Anti-Strike (P1)** intransponível.

Visão completa: `_bmad-output/planning-artifacts/visao.md`.

## Positioning

Ferramentas pagas de autoclip (Opus Clip, Cortaí) cobram mensalidade por minuto, olham quase só para o texto e param no arquivo `.mp4`. Clones open-source puros (`chopify`, `supoclip`, `clippyme`) entregam boas peças mecânicas, mas não têm inteligência de mercado nem blindagem de copyright. O **Picorte** funde o melhor motor open-source local com **Visão Computacional de Games**, **Sismógrafo do Chat da Live**, **Escudo Anti-Strike (P1)** e um **Cérebro Bandit + Radar de Alta (P3)**, operando a custo zero de assinatura na própria GPU.

## Operating Context

- O sistema evolui em 7 Épicos práticos, começando pelo clone rodando na GPU (Épico 1) e controle via Claude/Gemini (Épico 2) até o ciclo autônomo completo (Épico 7).
- Uma fonte com status `desconhecida` **não publica e nem é baixada** até o operador mudar o status. Se ela estiver em alta no Radar, o sistema avisa o que falta para liberá-la.
- Os 8 GB de VRAM da RTX 4060 Ti são gerenciados em fila serializada (um modelo pesado por vez), com **Modo Madrugada** para lotes pesados (VODs de +2h, `Demucs`, treino de modelos próprios).
- Cada rede tem suas regras e limites (cotas de upload, auditoria pendente = publicação privada ou assistida). A interface diz o que cada rede permite de verdade.
- Datas gravadas em UTC e mostradas no fuso de Brasília.

## Capabilities and Constraints

- **Ingestão 360º:** VODs longas em blocos de áudio (`chopify`), **Lives Ao Vivo** (`streamlink` + `live_monitor.py`) e **Clipes Virais de Terceiros** (avaliados e re-transformados).
- **Detecção Multimodal 4D:** Sismógrafo do Chat da Live (`msgs/s` + emotes) + Áudio 1 Hz (`evidence.py`) + Visão Computacional 2 fps (Micro-expressões na facecam, HUD/Killfeed do jogo, ação visual) + Texto (LLM local Ollama ou API Claude/Gemini).
- **Engenharia de Retenção e Formato:** Cold Open Reverso (1,5s), Faixa de Contexto (2s), Seamless Loop, Troca Dinâmica de Layout (Facecam + Jogo), Sniper Crop, Compilação Cross-Streamer, 1º Comentário Fixado "Isca de Debate", e **Funil Short Isca → Vídeo Longo (3–5 min) + Fábrica Automática de Thumbnail**.
- **Escudo Anti-Strike (P1):** status da fonte, políticas por publisher/jogo, cirurgia de música com `Demucs` seletivo, Selo Verde 15s (sem violência gráfica + micro-bleep de palavrão), Detector de React Perigoso, Score de Transformação YPP, Deduplicação `pHash`, crédito automático e pausa global ao 1º claim.
- **Aprendizado Contínuo (P3):** snapshots de 1h/24h/7d, Radar de Tendências + Calendário, Multiplicador de Campanhas Pagas (CPM), Bandit com esquecimento, Reciclagem A/B de Gancho ("Segunda Vida") e Autocaptura de Dataset Rotulado (*Active Learning*).
- **Excluído por decisão do usuário:** Jump-Cut de Tempos Mortos + Compressor de Áudio; SaaS / multi-tenant.

## Brand Commitments

- Nome da ferramenta: **Picorte** (pico + corte).
- Canal de cortes de games: **Bomba Clips** (independente e sem ligação visível com a marca Picorte — P1).
- Identidade visual (redefinida em 2026-11-21): acabamento de app de sistema (referência do dono: apps do macOS), cinzas neutros e uma única cor de marca, o laranja do logotipo; mundo "Álbum de figurinhas" discreto (numeração Nº dos cortes e o encaixe "colar a figurinha"); peça de dado: o pico de origem. Detalhes em `DESIGN.md`. O logotipo (`design/brand/`) continua o mesmo.
- Voz: português do Brasil, direto e honesto.

## Evidence on Hand

- Pilares e anti-pilares aprovados e revisados na E3.5: `_bmad-output/planning-artifacts/pilares.md`.
- Visão consolidada e mapa completo de capacidades: `_bmad-output/planning-artifacts/visao.md`.
- Auditoria de código dos 10 clones open-source (`referencias/`) e mapa de transplante: `_bmad-output/planning-artifacts/concorrentes.md`.
- Sessão completa de Brainstorming BMAD: `_bmad-output/brainstorming/brainstorm-mapa-funcionalidades-picorte-2026-11-18/brainstorm.html`.

## Product Principles

1. **O canal vem antes do alcance (P1).** Todo estado de risco é visível, explicado e nunca contornável.
2. **Os dados de agora decidem (P3).** A interface mostra por que o sistema escolheu um corte (chat, áudio, visão, radar, campanha ativa) e o que mudou desde ontem.
3. **Autônomo por padrão (P5).** O operador supervisiona (via painel ou via Claude/Gemini), não edita corte a corte.
4. **Honestidade sobre o que cada rede e o próprio hardware conseguem fazer.**
5. **Português claro antes de termo técnico.**

## Accessibility & Inclusion

WCAG 2.1 AA: contraste AA, navegação completa por teclado e **status nunca indicado só por cor** (crítico nos alertas de risco e nos estados da fila).
