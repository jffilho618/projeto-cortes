# Handoff — Sessão 03 (2026-11-18)

> Se você é o **Claude Code** ou o **Gemini (Antigravity)** assumindo o projeto no **PC de mesa (Windows 11)** ou no notebook, leia este arquivo, o `CLAUDE.md` (ou `AGENTS.md`) e o `docs/plano-mestre.md` (Versão 2). Converse sempre em **português do Brasil**, de forma direta e honesta.

---

## 1. O que foi concluído nesta sessão (Resumo Executivo)

1. **Épico 3 completo (`3.1` a `3.5`) + testes reais em vídeo 50 min de GTA 6:**
   - **Sismógrafo de chat e fronteiras:** `picorte/engine/chat_seismic.py`, `picorte/engine/snap_boundaries.py`.
   - **Visão computacional de games e enquadramento:** `picorte/engine/visual_games.py`, `picorte/engine/hud_detector.py`, `picorte/engine/reaction_layout.py` (priorizando webcams reais de canto em `_score_corner_facecam` e evitando rostos de NPCs), `picorte/engine/reframe_games.py` e `picorte/config.py` (`VISION_PRESETS` `auto`/`low`/`high`).
   - **Engenharia de retenção e alinhamento:** `picorte/engine/retention_engine.py`, `picorte/engine/audio_align.py`.
   - **Correções práticas validadas em vídeo real (`projects/4e036b8dfa84`):**
     - Bypass do bug `metadata_errors` do PyAV 19 via decodificação PCM `float32` com `ffmpeg`; detecção/fallback de CUDA em `picorte/engine/cuda.py` + `requirements-cuda.txt`.
     - Fim do deadlock interativo ao rodar pipeline via Estúdio (`--no-input` + `stdin=subprocess.DEVNULL` em `dashboard.py`).
     - Melhoria da seleção PT-BR em `score_clips.py` e `picorte/ai/llm_router.py` (amostragem distribuída na timeline e preservação de `proposed_title`, `context_banner_2s`, `thumbnail_words`, `pinned_comment_debate`), subindo de 1 corte longo para **12 cortes `<60s`**.
     - Acabamento visual e de legendas em `captions.py` / `render_clips.py`: filtro de idioma dominante para ignorar NPCs em inglês (`dominant_language`), detecção de borda interna da facecam (`_detect_overlay_border`), quebra de agrupamento em silêncios `>= 0.70s`, limite anti-sobreposição entre cues ASS e âncora fixa inferior em `82.5%` no layout `games`.
2. **Componente próprio de título em papel rasgado (`picorte/engine/title_badge.py`):**
   - `create_torn_paper_badge(...)` gera faixa RGBA orgânica multiplataforma (NumPy + OpenCV, `cv2.imencode` + `Path.write_bytes`), sobreposta exatamente na divisória facecam/jogo nos primeiros `6.0s`, com `ContextBanner` balanceado em 2 linhas em `Ubuntu Sans` (Linux) / `Impact` (Windows) e destaque automático em `#FFD400`.
3. **Fábrica automática de Thumbnails reformulada (`picorte/engine/thumbnail_factory.py`):**
   - Removido o fallback ruidoso de Otsu + contornos laranja sobre folhagem/HUD.
   - Composição cinematográfica `1280×720` com escurecimento gradual à esquerda/rodapé, card arredondado da facecam ampliada no topo direito (preservando safe zone do relógio no canto inferior direito) e tipografia PT-BR com acentos perfeitos via `ffmpeg` + `.ass`.
   - `projects.py` passa a gerar `_thumb.png` também nos renders de `preview=True`.
4. **Identidade Visual do Canal Bomba Clips (`@bombaclips`, separada do Picorte pela regra P1):**
   - Guia da marca em `canais/bomba-clips/BRAND.md`.
   - Mascote A aprovado, recorte transparente (`canais/bomba-clips/avatar/mascote-bomba-transparente.png`), avatar `800×800` (`canais/bomba-clips/avatar/avatar-bomba-clips-800x800.png`), banner YouTube `2560×1440` seguro na área `1546×423` com os 5 ícones + `@BOMBACLIPS` (`canais/bomba-clips/banner/banner-youtube-2560x1440.png`), capa Facebook `851×315` (`canais/bomba-clips/banner/capa-facebook-851x315.png`) e gerador `canais/bomba-clips/build_banner.py`.
   - Designs gerados na conta Canva do usuário (`DAHbUOqt9Zc`, `DAHbUEApA4g`) e mascote enviado (`MAHbUL8oniM`).

---

## 2. Regra crítica do novo ambiente no PC de mesa (Windows 11)

- **NÃO usar `.venv` no PC de mesa (decisão explícita do usuário em 2026-11-18):**
  - Instalar/rodar dependências direto no **Python global do Windows 11** (`python -m pip install -r requirements.txt -r requirements-cuda.txt`) e manter `ffmpeg` / `ffprobe` no `PATH` do Windows.
  - O código está preparado: `picorte/config.py::get_venv_bin_dir()` só adiciona `.venv/Scripts` ao `PATH` se a pasta `.venv` existir; sem `.venv`, `dashboard.py` e `chopify.py` usam `sys.executable` (Python global) normalmente.
- **Hardware do PC de mesa e preset de Visão:**
  - RTX 4060 Ti (8 GB) / RTX 4070 Ti: `picorte/config.py` detecta `> 6144 MiB` (`desktop_8gb_plus`) e seleciona automaticamente `vision_preset="high"` com Whisper `large-v3-turbo` (`int8_float16`).
  - Se quiser ativar também os modelos pesados opcionais (`YOLO11n`, `HSEmotion`, `BiRefNet`) no PC de mesa, instalar as libs opcionais (`ultralytics`, `hsemotion`, `rembg`) no Python global; sem elas, o fallback seguro continua funcionando sem quebrar.
- **Arquivos ignorados no Git (`.gitignore` e `.git/info/exclude`):**
  - **Não** são versionados no Git: `referencias/`, `projects/`, `clips/`, `work/`, `picorte.db`, `.env`, `.venv/`, `.agents/`, `AGENTS.md`.
  - Se migrar o projeto via repositório Git novo (ainda não há `remote` configurado aqui), copie manualmente `.env` (se tiver), `referencias/` e `projects/` se quiser manter os downloads em cache de GTA 6; no Windows, recrie o symlink ou cópia `AGENTS.md` ↔ `CLAUDE.md` se precisar do Antigravity lendo as regras.

---

## 3. Onde estamos e qual é o próximo passo imediato

- **Estado atual:** Épicos 1, 2 e 3 concluídos e commitados na branch `main` (`_bmad-output/implementation-artifacts/sprint-status.yaml` e `docs/plano-mestre.md` atualizados).
- **Próxima etapa imediata (`⏳ PRÓXIMO`):**
  - **Épico 4 · Escudo Anti-Strike e Anti-Desmonetização (P1 Inegociável)** (`_bmad-output/planning-artifacts/epics.md` — módulo `risk_shield/`: status de permissão por fonte, políticas por publisher/jogo, remoção seletiva de música via `Demucs` na GPU, Selo Verde 15s, Detector de React Perigoso, deduplicação `pHash`, Score YPP e pausa automática global ao 1º claim).
  - Seguir **superpowers** na execução (`writing-plans` → `test-driven-development` → `verification-before-completion`) + `cortes-pilares` e `bmad-code-review` como portões do P1.
