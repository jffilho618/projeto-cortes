# Épico 3 (Presets CV `auto`/`low`/`high` + Multimodal 4D + Visão Computacional de Games + Retenção + Thumbnail) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o sistema de presets de Visão Computacional (`auto` / `low` / `high` estilo gráficos de jogo — `AD-12`), visibilidade na UI dos dados do E2/E3, e todo o pipeline multimodal 4D + Visão Computacional de Games + Engenharia de Retenção + Par Short/Longo + Fábrica de Thumbnail (`Stories 3.1` a `3.5`).

**Architecture:** Cada módulo vive em `picorte/engine/` respeitando `AD-3` (`vram_runner.py`), `AD-11` (Windows 11 + Linux Ubuntu) e `AD-12` (presets `low` e `high` com `resolve_vision_preset`), com degradação limpa caso pesos pesados opcionais ainda não estejam baixados na máquina de 4 GB.

**Tech Stack:** Python 3.12, `opencv-python` (YuNet + Optical Flow), `numpy`, `ffmpeg` (`libass`, `sendcmd`, `h264_nvenc`/`libx264`), adaptadores modulares para `MediaPipe`, `HSEmotion`, `RapidOCR`, `YOLO11n` (`ultralytics`), `rembg` (`u2netp` / `BiRefNet`).

---

### Task 1: Presets Gráficos de Visão Computacional (`AD-12`) + Visibilidade UI (`auto`/`low`/`high` + dados E2)

**Files:**
- Modify: `picorte/config.py` (`VISION_PRESETS`, `resolve_vision_preset`)
- Modify: `projects.py`, `dashboard.py`, `assets/studio/index.html`, `assets/studio/app.js`
- Test: `tests/test_vision_presets.py`

### Task 2: Sismógrafo do Chat da Live (`Story 3.1` — `picorte/engine/chat_seismic.py`)

**Files:**
- Create: `picorte/engine/chat_seismic.py`
- Test: `tests/test_chat_seismic.py`

### Task 3: Visão Computacional de Games (`MAR` + `HUD/Killfeed` + `Sniper Crop`) & Fusão 4D + `snap_boundaries` (`Story 3.2`)

**Files:**
- Create: `picorte/engine/visual_games.py`
- Create: `picorte/engine/hud_detector.py`
- Create: `picorte/engine/snap_boundaries.py` (transplantado de `AgriciDaniel_claude-shorts`)
- Modify: `score_clips.py` (fusão 4D `S_chat + S_audio + S_visao + S_texto` + snap de bordas)
- Test: `tests/test_visual_games_and_4d.py`

### Task 4: Reenquadramento 9:16 de Games — Facecam + Jogo, Troca Dinâmica de Layout e Sniper Crop (`Story 3.3`)

**Files:**
- Create: `picorte/engine/reaction_layout.py` (transplantado de `FujiwaraChoki_supoclip`)
- Create: `picorte/engine/reframe_games.py`
- Test: `tests/test_reframe_games.py`

### Task 5: Engenharia de Retenção (Cold Open 1,5s, Contexto 2s, Seamless Loop, Cross-Streamer) + Par Short/Longo + Fábrica de Thumbnail (`Stories 3.4` & `3.5`)

**Files:**
- Create: `picorte/engine/audio_align.py` (transplantado de `louisedesadeleer_clipify`)
- Create: `picorte/engine/retention_engine.py`
- Create: `picorte/engine/thumbnail_factory.py` (seguindo `youtube-thumbnail-design` + `DESIGN.md`)
- Test: `tests/test_retention_and_thumbnail.py`
