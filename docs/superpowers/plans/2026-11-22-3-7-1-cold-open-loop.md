# 3.7.1 — Cold Open Reverso 1,5s e Seamless Loop renderizados de verdade — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o corte abre com 1,5 s do clímax medido e termina num fim de frase que emenda com o começo.

**Architecture:**
- **Clímax:** escolhido no `projects.py`, na hora do render, pelo sinal medido com horário: pico de chat (causa) ou o fim da punchline (`hook_quote` nas palavras). Sem sinal → sem Cold Open.
- **Teaser:** sai do **próprio mp4 renderizado** (já com enquadramento, legenda e faixa), num pós-processo FFmpeg: `trim` do teaser + `xfade`/`acrossfade` de 0,25 s + o corte inteiro, com os bleeps do Selo Verde próprios do teaser.
- **Loop:** no `select`, depois do fim-após-o-riso, o fim vai para um fim de frase em `[fim−3, fim+1,5]` cujo volume mais se parece com o do começo (`audio_features.npz`). Se o riso estendeu o fim, só pode avançar.

**Tech Stack:** Python 3.12 global, FFmpeg (`libx264`, como o render atual), pytest.

**Spec:** `_bmad-output/planning-artifacts/epics.md` → Story 3.7.1 + regras comuns do Épico 3.7.

## Global Constraints

- Espelhos: `score_clips.py`, `projects.py` e `render_clips.py` (raiz) = `picorte/engine/`.
- AD-11: comando FFmpeg em lista de argumentos, sem shell, e caminhos com `pathlib`.
- Medido ou desligado: sem clímax medido, sem teaser; sem frase no intervalo, o fim fica como está.
- P1: o teaser recebe os `cold_open_bleeps`; o escudo passa a usar o `has_cold_open` real (fecha o W3).
- **Limitação assumida:** o "emendar" do loop é medido pelo volume, não pela imagem. Comparar quadros exigiria decodificar o vídeo no `select`. Fica registrado.
- O `tighten` muda a linha do tempo do mp4, então com ele ligado não há teaser (motivo registrado). O mesmo vale para o preview.
- Custo: R$ 0. Só o re-encode do corte (+ alguns segundos por corte).

---

### Task 1: escolher o clímax (AC1)

**Files:** `picorte/engine/retention_engine.py`, `tests/test_e37_cold_open_loop.py`

**Produz:** `pick_climax(seg, words, chat_peaks, *, min_lead=3.0) -> dict | None` → `{"t": float, "fonte": "chat" | "punchline"}`.
- **Chat:** o pico com maior `vel_zscore` cuja `cause_second` cai em `[start+3, end−0,5]`.
- **Punchline:** senão, o fim da sequência de palavras do `hook_quote` dentro do corte, menos 0,5 s.
- Senão, `None`.

`cold_open_for_segment(seg, words, chat_peaks, *, max_len=None, xfade=0.25) -> dict` faz o plano completo:
- sem clímax → `{"enabled": False, "motivo": ...}`;
- com clímax → o plano do `build_cold_open_plan` com `peak_t`, respeitando a política do arquétipo;
- **`max_len` (AC5):** se `dur + teaser − xfade` passar do `max_len`, o começo do corte avança pelo excesso (`novo_inicio`), desde que fique ≥ 1 s antes do teaser. Senão, sem Cold Open.

### Task 2: montar o teaser no vídeo (AC1, AC3)

**Files:** `picorte/engine/retention_engine.py`, `render_clips.py` (+ espelho), `projects.py` (+ espelho), `picorte/risk_shield/pipeline.py`

**Produz:**
- `cold_open_ffmpeg_cmd(in_path, out_path, rel_start, dur, bleeps, *, xfade=0.25) -> list[str]`: o filtro com `trim`/`atrim` do teaser, soft-mute dos bleeps (−36 dB, como o Selo Verde), `xfade=fade` e `acrossfade`.
- `prepend_cold_open(mp4, plan, clip_start, bleeps, *, runner=subprocess.run) -> bool`: troca o arquivo em lugar e devolve `True` quando renderiza.

**No `render_clips.render`:**
- o `_apply_green_seal` guarda os `cold_open_bleeps` em `seg["_cold_open_bleeps"]`;
- depois do `subprocess.run` principal, se `seg["cold_open"]["enabled"]` e não for preview nem tighten, chama o `prepend_cold_open`;
- grava `seg["cold_open"]["rendered"] = True` e acrescenta `{"nome": "cold_open", ...}` em `seg["transformacoes"]`;
- `write_meta` passa a levar `transformacoes`.

**No `projects.py`:** troca o `build_cold_open_plan` direto pelo `cold_open_for_segment` (com os picos do `chat_seismic.json` e o `max_len`). Se o plano pedir `novo_inicio`, o `enriched_seg` usa esse início.

**No `pipeline.py`:** `has_cold_open = bool((meta.get("cold_open") or {}).get("rendered"))`.

### Task 3: Seamless Loop (AC4)

**Files:** `picorte/engine/retention_engine.py`, `score_clips.py` (+ espelho)

**Produz:** `seamless_loop_end(sentences, start, end, *, rms=None, back=3.0, fwd=1.5, only_forward=False, max_len=None) -> float`.
- Os candidatos são os fins de frase em `[end−back, end+fwd]` (só `≥ end` se `only_forward`), respeitando o `max_len`.
- Vence o fim de frase cujo volume (dB por segundo) mais se parece com o do 1º segundo; no empate, o mais perto do fim atual.
- Sem candidatos, mantém o fim.

`select` → `_apply_seamless_loop(workdir, segments, max_len)`:
- usa `only_forward` quando `evidence.end_after_laugh_s` existe;
- grava `transformacoes += seamless_loop` quando o fim muda;
- saúde `seamless_loop`.

### Testes (AC6)

- clímax pelo chat; clímax pela punchline; sem sinal → sem Cold Open;
- arquétipo sem Cold Open (`mico_constrangimento`);
- `max_len` avança o começo, ou desliga quando o clímax está cedo demais;
- comando FFmpeg com `trim`/`xfade` e bleep no teaser;
- **integração real e curta:** vídeo sintético de 6 s (lavfi) → teaser de 1,5 s → duração final ≈ 6 + 1,5 − 0,25;
- loop: escolhe o fim de frase com volume parecido, mantém o fim sem candidatos e só avança depois do riso;
- o escudo usa o `has_cold_open` real.

## Resultado (2026-11-22)

- O teaser é colado **de verdade** no mp4 renderizado (`prepend_cold_open`), com o Selo Verde próprio. O escudo P1 passa a usar o `has_cold_open` real (W3 fechado). O teste de ponta a ponta com render real confere `cold_open.rendered` e `transformacoes`.
- O clímax é medido: pico de chat ou punchline (busca aproximada, ≥ 60% das palavras e sem acento, porque o Editor parafraseia). O prompt passou a pedir o `hook_quote` literal.
- Seamless Loop no `select` (fim de frase com volume parecido com o começo; recuo de 1,5 s em vez de 3 s, W34).
- **Furo da 3.6.4 achado aqui:** `test_editor_chief_receives_only_measured_nonverbal_signals` dependia da posição e falhava em metade das rodadas (ordem sorteada). Corrigido; a suíte rodou 2 vezes seguidas sem falha.
- **Olhada nas 4 lives:** 12 de 92 cortes ganhariam Cold Open (W33).
- Suíte: 785 passam; 1 falha conhecida, só de ambiente, na worktree.
