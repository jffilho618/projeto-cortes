# 3.7.2 — Layout dinâmico + Sniper Crop ligados ao render de games — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** no `layout=games`, o vídeo vertical alterna entre História, Reação e Ação conforme o que acontece no corte, e na Ação o recorte do jogo segue a ação.

**Decisão do dono (2026-11-22): "jogo protagonista".**

| Layout | Tela (1080×1920) |
|---|---|
| História | rosto em cima ≈ 33% (640 px, igual ao layout fixo de hoje), jogo embaixo |
| Reação | rosto 50% (960 px), jogo 50% |
| Ação | jogo em tela cheia (recorte 9:16 que segue a ação) + rosto em PiP (360 px de largura) no canto superior direito, em y = 240 |

**Architecture:**
- **Amostragem:** `render_clips` (no ramo `games`, depois de achar a facecam) amostra 1 quadro por segundo do corte.
- **Movimento medido:** diferença entre quadros **dentro da facecam** (o rosto reagindo) e **na região do jogo** (ação), normalizada pelo próprio corte, com um piso absoluto. Isso vira os eventos `face_emotion` e `hud_action` do `compute_dynamic_layout_timeline` já existente (histerese de 3 s).
- **Sniper Crop:** o `compute_sniper_crop_track` (centroide óptico, ou YOLO no preset high) dá o x do recorte nos trechos de Ação, com velocidade máxima limitada.
- **Filtro:** um `split` por trecho → `trim` → arrumação do trecho → `concat` → legenda.

**Tech Stack:** Python 3.12, OpenCV, numpy, FFmpeg.

**Spec:** `epics.md` → Story 3.7.2 + regras comuns do Épico 3.7.

## Global Constraints

- Espelho: `render_clips.py` (raiz) = `picorte/engine/render_clips.py`.
- Medido ou desligado: sem facecam, sem quadros ou sem movimento medido, cai no layout fixo de hoje, e a saúde registra `layout_dinamico: na` com o motivo.
- **Áreas seguras:**
  - A legenda fica em y = 80% (dentro do jogo nas 3 arrumações).
  - A faixa de contexto (2 s) e o selo de título (3,5 s) dependem da emenda em 640 px, então o **1º trecho é sempre História por ≥ 3,5 s**.
  - O PiP da Ação fica em y = 240 (abaixo da área de interface da rede).
- O YOLO só entra pelo preset high, pela fila serial (AD-3); o padrão é CPU.

---

### Task 1: eventos medidos por segundo
`layout_events_from_motion(face_motion, game_motion, *, first_hold=3.5, floor=2.0) -> list[dict]`
- Normaliza cada série pelo p90 do corte (clip 0–1) e zera tudo se o p90 ficar abaixo do piso (cena parada).
- Os eventos antes de `first_hold` ficam de fora.

Testes:
- o rosto mexendo muito vira evento de reação;
- o jogo mexendo muito vira evento de ação;
- cena parada não gera eventos;
- não há evento antes de 3,5 s.

### Task 2: filtro por trechos
- `LAYOUT_RATIO_MAP` fica com História 640, Reação 960 e Ação `acao_pip` (PiP).
- `sniper_x_expr(centers, section_start, section_end, *, src_w, crop_w, max_speed=0.15) -> str`: expressão linear por partes em `t` (local ao trecho), com o deslocamento limitado a `max_speed·src_w` por segundo.
- `build_dynamic_games_filter(timeline, *, src_w, src_h, out_w, out_h, face_box, centers) -> str`: termina sem rótulo, para o render acrescentar `,setsar=1…` como hoje.

Testes:
- 3 trechos → `concat=n=3`;
- `trim` com os tempos certos;
- a Ação tem `overlay` do PiP e `x='if(` no crop;
- a expressão nunca anda mais que o limite por segundo;
- **ffmpeg de verdade:** o filtro roda sobre um `testsrc` 1920×1080 de 8 s e sai 1080×1920 com 8 s.

### Task 3: ligar no render
- No `render_clips.render`, ramo `games`: com `face_box`, amostra os quadros, mede o movimento, monta a linha do tempo e o Sniper Crop, e usa o filtro dinâmico.
- Uma linha do tempo de 1 trecho de História é igual ao layout de hoje.
- Exceção ou falta de dado → layout fixo, com motivo.
- `seg["layout_timeline"]` e `transformacoes += layout_dinamico` (quando há troca) vão para o `.meta.json`.

Teste: o render de ponta a ponta continua passando (o vídeo do teste não tem rosto → layout fixo, `layout_dinamico: na`).

## Resultado (2026-11-22)

- `plan_dynamic_games` → `build_dynamic_games_filter` ligados ao `render_clips` (ramo `games`). Sem facecam ou sem quadros, cai no layout fixo e a saúde registra `layout_dinamico: na`. `layout_timeline` e `transformacoes` vão para o `.meta.json`.
- **Render real** de um corte de 78 s da `5P8qh7jZti8`: as 3 arrumações conferidas quadro a quadro (História 640, Reação 960, Ação em tela cheia + PiP).
- **A olhada mudou o desenho:** eram 15 trocas em 78 s e um pedaço final de 0,9 s. Agora a atividade é suavizada em 3 s, cada arrumação fica ≥ 4 s e pedaço final < 2 s se junta ao anterior. Resultado: 10 trocas (W35).
- **Bug pego por teste:** `segments[-2]["end"] = segments.pop()["end"]` (o `pop` roda antes da atribuição).
- Suíte: 799 passam; 1 falha conhecida, só de ambiente, na worktree.
