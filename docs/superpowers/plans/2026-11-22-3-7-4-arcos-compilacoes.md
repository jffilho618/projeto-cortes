# 3.7.4 — Arcos de 2 atos e compilação por arquétipo renderizados — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** arcos "promessa → desfecho" e compilações por arquétipo (incl. "TOP VACILOS DA LIVE") viram vídeo de verdade.

**Architecture:**
- **`select` → `_add_composites`** (fora do `hunt_mode=deep`). Os segmentos compostos saem com `formato` `arco_2_atos` ou `compilacao` e a lista `trechos`, no fim do `segments.json`, sem `rank`.
  - **Arco:** o `detect_two_act_arcs` só vale se o **ato 2 cair dentro de um Short selecionado** (filtro de ruído, já que o detector é só léxico). Cada ato ganha a frase vizinha de contexto; total ≤ 180 s; no máximo 2 arcos por VOD.
  - **Compilação:** o `compile_by_archetype` sobre os Shorts selecionados (≥ 4 do mesmo arquétipo, 90–240 s), com o título de `ARCHETYPE_COMPILATION_TITLES`.
- **`render_clips.render_composite`:**
  - renderiza **cada trecho pelo `render` normal** (layout, legenda e Selo Verde por trecho);
  - um trecho que o P1 barra (`PolicyViolationError`) sai;
  - se sobrarem menos de 2 trechos (arco) ou 4 (compilação), o composto não sai e o motivo é registrado;
  - emenda tudo com `concat` (fps 30, áudio 48 kHz) e, no arco, um cartão de 1,5 s com o texto da ponte (fundo preto + ASS, sem depender de fonte instalada);
  - apaga os pedaços temporários.
- **`projects`:**
  - segmento composto → `render_composite`, sem Cold Open;
  - música, veredito P1 e thumbnail rodam no vídeo final como num corte normal.

**Spec:** `epics.md` → Story 3.7.4.

## Global Constraints

- Espelhos: `score_clips.py`, `projects.py` e `render_clips.py`.
- Os compostos obedecem à opção `formatos_extras` da 3.7.3 e ficam fora do modo cego. É menos volume, como pede o A2.
- AD-11: comandos FFmpeg em lista, cartão em ASS e caminhos com `pathlib`.
- O crédito ao canal e o P1 valem no vídeo final (`.meta.json` e veredito), e o Selo Verde vale em cada trecho.

### Testes
- **Arco:**
  - só com o ato 2 dentro de um Short selecionado;
  - atos com a frase vizinha;
  - ≤ 180 s;
  - no máximo 2.
- **Compilação:** 4 vacilos → "TOP VACILOS DA LIVE"; 3 → nenhuma.
- **`render_composite`** com um renderizador falso:
  - trecho barrado pelo P1 sai;
  - composto curto demais não sai;
  - o arco leva o cartão da ponte;
  - os pedaços são apagados.
- **ffmpeg de verdade:** 2 pedaços sintéticos + cartão → duração ≈ soma.
- **`render_params_for`:** composto sem Cold Open.

## Resultado (2026-11-22)

- `picorte/engine/composites.py`:
  - arcos (filtro "desfecho dentro de um Short selecionado", atos com a frase vizinha, ≤ 180 s, até 2 por VOD);
  - compilações (só Shorts ≤ 60 s);
  - `render_composite`: cada trecho pelo render normal, trecho barrado pelo P1 sai, mínimo de 2 ou 4 trechos, cartão de ponte em ASS, emenda com `concat`, pedaços apagados;
  - `concat_parts` e `make_bridge_card`.
- O `select` gera os compostos (com `formatos_extras`, fora do modo cego). O `projects` renderiza pelo `render_composite`, sem Cold Open, e o veredito P1 sai no vídeo final.
- **Render real:** compilação de teste com 4 trechos de 12 s (48 s) e arco de 10 + 1,5 + 10 s (21,5 s), ambos 1080×1920 no layout de games; cartão conferido no quadro.
- **Olhada nas 4 lives:** 9 arcos brutos → 1 válido (W38); nenhuma compilação, porque os cortes atuais passam de 60 s (W39). Daí veio a correção "só Shorts ≤ 60 s na compilação".
- Suíte: 823 passam; 1 falha conhecida, só de ambiente, na worktree.
