# Épico 1 (MVP Zero — Chassi Chopify + Perfil de GPU + Área Segura 9:16) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transplantar o chassi do `mehbul/chopify` e o detector CUDA do `artbyjazi/autoclip` para o pacote `picorte/`, implementar a seleção automática de perfil de VRAM (GTX 1650 4 GB vs RTX 4070 Ti / 4060 Ti), aplicar a Área Segura Unificada 9:16 (`AD-7`) nas legendas `.ass` e gerar os primeiros cortes `.mp4` reais com todos os testes passando.

**Architecture:** Copiamos os módulos testados de `referencias/mehbul_chopify/` para a raiz/pacote `picorte/engine/` mantendo compatibilidade com os imports dos testes originais, adicionamos `picorte/config.py` + `picorte/engine/cuda.py` para escolher automaticamente o modelo e quantização do `faster-whisper` conforme a VRAM detectada, e ajustamos `render_clips.py` para respeitar as margens seguras de Shorts/TikTok/Reels (`MarginL=80`, `MarginR=160`, `MarginV=450` em `1080x1920`).

**Tech Stack:** Python 3.12, `pytest`, `faster-whisper`, `opencv-python` (YuNet), `numpy`, `yt-dlp`, `ffmpeg` (`libass`, `libx264` / `h264_nvenc`).

## Global Constraints

- **AD-1 (Zero Reinvenção):** partir dos arquivos de `referencias/mehbul_chopify/` e `referencias/artbyjazi_autoclip/backend/autoclip/cuda.py`.
- **AD-3 (Orçamento de VRAM):** GPUs com `<= 4096 MiB` (ex.: GTX 1650) usam perfil `small` com `compute_type="int8"`; GPUs com `>= 8000 MiB` (ex.: RTX 4060 Ti / 4070 Ti) usam perfil `large-v3-turbo` com `compute_type="int8_float16"`; sem GPU usa `base` + `int8` em CPU.
- **AD-7 / R-08 (Área Segura Unificada 9:16):** em `1080x1920`, o estilo `.ass` deve usar `MarginL=80`, `MarginR=160` e `MarginV=450` por padrão para nunca colidir com os botões laterais nem com a descrição inferior das redes verticais.

---

### Task 1: Diagnóstico Automático de GPU/VRAM (`picorte/config.py` e `picorte/engine/cuda.py`)

**Files:**
- Create: `picorte/__init__.py`
- Create: `picorte/engine/__init__.py`
- Create: `picorte/engine/cuda.py`
- Create: `picorte/config.py`
- Test: `tests/test_gpu_profile.py`

**Interfaces:**
- Produces:
  - `picorte.config.detect_gpu_profile(vram_mib: int | None = None, gpu_name: str | None = None) -> dict` retornando `{"device": str, "whisper_model": str, "compute_type": str, "vram_mib": int, "tier": str}`
  - `picorte.engine.cuda.ensure_cuda_libraries() -> list[Path]`

- [ ] **Step 1: Write the failing test (`tests/test_gpu_profile.py`)**
- [ ] **Step 2: Run test to verify it fails (`pytest tests/test_gpu_profile.py -v`)**
- [ ] **Step 3: Implement `picorte/engine/cuda.py` and `picorte/config.py`**
- [ ] **Step 4: Run test to verify it passes**

---

### Task 2: Transplante do Chassi `chopify` e Área Segura Unificada 9:16 (`AD-7` / `R-08`)

**Files:**
- Create/Copy from `referencias/mehbul_chopify/`: `chopify.py`, `ingest.py`, `sections.py`, `download_and_transcribe.py`, `evidence.py`, `visual.py`, `score_clips.py`, `render_clips.py`, `captions.py`, `branding.py`, `tighten.py`, `projects.py`, `dashboard.py` e suíte `tests/test_*.py`
- Modify: `render_clips.py` (aplicar `ASPECTS["9:16"] = (1080, 1920, 96, 450)` e `MarginR = 160` para `9:16` em `build_ass`)
- Modify: `download_and_transcribe.py` (usar `detect_gpu_profile()` como padrão quando `--model`/`--device` não forem forçados)
- Test: `tests/test_safe_zone_captions.py`

**Interfaces:**
- Consumes: `picorte.config.detect_gpu_profile`
- Produces: `render_clips.build_ass(...)` gerando `.ass` com `MarginL=80, MarginR=160, MarginV=450` em `9:16` (`1080x1920`).

- [ ] **Step 1: Transplant `referencias/mehbul_chopify` modules and write failing test `tests/test_safe_zone_captions.py` (`R-08`)**
- [ ] **Step 2: Run `pytest tests/test_safe_zone_captions.py -v` and watch it fail on old margins (`300` / `80`)**
- [ ] **Step 3: Update `render_clips.py` and `download_and_transcribe.py` to satisfy `AD-7` and `AD-3`**
- [ ] **Step 4: Run full `pytest` suite to verify both new tests and original `chopify` tests pass**

---

### Task 3: Instalação de Dependências (`ffmpeg` + `.venv`) e Geração do Primeiro Corte `.mp4` Real (`Story 1.2`)

**Files:**
- Create: `requirements.txt`
- Verify: `clips/` (primeiro corte `.mp4` `9:16` + `.png` + `.meta.json` gerado de ponta a ponta)

- [ ] **Step 1: Configurar `.venv` e garantir `ffmpeg` com `libass` e `libx264`/`h264_nvenc` disponível**
- [ ] **Step 2: Executar toda a suíte `pytest` (incluindo integração com `ffmpeg`)**
- [ ] **Step 3: Gerar um vídeo sintético/amostra de gameplay com fala e rodar o pipeline completo (`chopify.py`) gerando o primeiro corte `.mp4` `9:16` legendado**
