# Handoff — Sessão 02 (2026-11-18)

> Se você é o **Claude Code** ou o **Gemini (Antigravity)** assumindo o projeto, leia este arquivo e o `docs/plano-mestre.md` (Versão 2). Converse sempre em **português do Brasil**, de forma direta e honesta.

---

## 1. O que aconteceu nesta sessão (Resumo Executivo)

1. **Integração 100% entre Claude Code e Antigravity (Gemini):**
   - Configuramos `.agents/skills.json` (apontando para `.claude/skills`) e `AGENTS.md` (symlink para `CLAUDE.md`), ambos no `.git/info/exclude` para não sujar o git.
   - Importamos os plugins globais do Claude (`superpowers`, `example-skills`, `claude-global-skills` com `impeccable` e seus 4 subagentes, `superpowers-chrome`) para `~/.gemini/config/plugins/`. Nenhum arquivo de `.claude/` ou `~/.claude/` foi alterado.
2. **Mudança Estratégica Decidida pelo Dono (E3.5):**
   - **Esquecer SaaS e multi-tenant (`workspace_id`):** a prioridade absoluta é **ganhar dinheiro com os próprios canais de cortes** (começando pelo **Bomba Clips** em games), sem perder tempo com infraestrutura de venda de assinaturas.
   - **Estratégia Evolutiva em cima de Clones Open-Source:** em vez de programar o cortador do zero, baixamos e auditamos o código-fonte de 10 repositórios em `referencias/` (pasta ignorada no git).
3. **Resultado da Auditoria de Código dos Clones (`_bmad-output/planning-artifacts/concorrentes.md`):**
   - 🥇 **Chassi Principal do Motor de Vídeo:** **`mehbul/chopify`** (`referencias/mehbul_chopify`, licença **MIT**, 30 arquivos Python, apenas 4 dependências: `yt-dlp`, `faster-whisper`, `opencv-python`, `numpy` + `ffmpeg`). Já roda 100% local e grátis, já analisa Áudio a 1 Hz (`evidence.py`) + Visão a 2 fps (`visual.py`) + Texto (`score_clips.py`), já suporta lives longas (+2h em blocos de áudio), durações de 15s a 300s (5 min), 9:16 e 16:9, rastreamento facial OpenCV YuNet e 13 estilos de legenda `.ass`.
   - 🥈 **Doador #1 (Lives Ao Vivo e Feeds):** **`fralapo/clippyme`** (`referencias/fralapo_clippyme`, licença **MIT**). De lá transplantamos `src/clippyme/monitoring/live_monitor.py` e `src/clippyme/integrations/` (`twitch_client.py`, `kick_client.py`, `youtube_feed.py`) para vigiar e cortar lives ao vivo e VODs.
   - 🥉 **Doador #2 (Layout Facecam+Jogo, Publicadores OAuth e MCP):** **`FujiwaraChoki/supoclip`** (`referencias/FujiwaraChoki_supoclip`, AGPL-3.0 — livre para uso próprio local). De lá transplantamos `backend/src/media/reaction_layout.py` (`find_reactor_face`, que separa facecam `640px` no topo + jogo `1280px` embaixo), `backend/src/social/` (`youtube.py`, `tiktok.py`, `instagram.py`) e o padrão do servidor MCP (`mcp/`).
   - **Doadores complementares (MIT):** `AgriciDaniel/claude-shorts` (`snap_boundaries.py`), `louisedesadeleer/clipify` (`build_pan.py`, `audio_align.py`) e `artbyjazi/autoclip` (`providers/` e `cuda.py`).
4. **Brainstorming BMAD (`bmad-brainstorming`) e Mapa Definitivo de Funcionalidades:**
   - Rodamos sessão completa gravada em `_bmad-output/brainstorming/brainstorm-mapa-funcionalidades-picorte-2026-11-18/` (`.memlog.md` e `brainstorm.html`).
   - O dono aprovou **todas as alavancas geradas, EXCETO "Jump-Cut de Tempos Mortos + Compressor de Áudio"**.
   - Tudo o que foi aprovado já está consolidado em `_bmad-output/planning-artifacts/pilares.md`, `visao.md`, `concorrentes.md`, `CLAUDE.md`, `PRODUCT.md` e `docs/plano-mestre.md` (Versão 2).

---

## 2. Onde estamos e qual é o próximo passo imediato

- **Concluído:** Fase A inteira (`E0`, `E1`, `E2`, `E3` e `E3.5`).
- **Próxima etapa imediata (`⏳ PRÓXIMA` no `docs/plano-mestre.md`):**
  - **E4 · Especificação Unificada (`bmad-spec`)** → seguida de **E5 · Arquitetura de Fusão (`bmad-architecture`)** → **E6 · Quebra nos 7 Épicos (`bmad-create-epics-and-stories`)** → e início imediato do **Épico 1 (colocar o `chopify` rodando na máquina e gerando os primeiros cortes `.mp4`)**.
- **Nota sobre o hardware:**
  - Quando a sessão rodar no **notebook**, a GPU é uma **GTX 1650 (4 GB VRAM)**.
  - Quando rodar no **PC de mesa**, a GPU é uma **RTX 4060 Ti (8 GB VRAM)**.
  - Em ambos, modelos pesados de GPU devem rodar de forma serializada (um por vez na VRAM).
