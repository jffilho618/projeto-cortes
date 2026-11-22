# 3.6.4 — Bordas por Frase, Fim Após o Riso e Editor-Chefe sem Viés de Ordem — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** os cortes começam no setup e terminam depois da reação, e a nota do Editor-Chefe deixa de depender da ordem em que os candidatos chegam.

**Architecture:**
- **Bordas por frase:** o Editor-Chefe ajusta as bordas contando **frases** (o contexto vai numerado) e o motor converte frase → tempo pelas frases do Whisper.
- **Pré-roll do setup:** a semente de pico de chat recua até o começo da frase do setup.
- **Fim após o riso:** no fim da seleção, a prosódia (riso 3–6 Hz) é medida em janelas curtas em volta do fim de cada corte, e o fim avança até o riso acabar.
- **Ordem:** os candidatos são embaralhados com semente gravada, e uma 2ª passada, com outra ordem, reavalia só os ~15 finalistas.

**Tech Stack:** Python 3.12 global, numpy (já usado na prosódia), pytest.

**Spec:** `_bmad-output/planning-artifacts/epics.md` → Story 3.6.4.

## Global Constraints

- Arquivos espelho: `score_clips.py` e `projects.py` (raiz) = `picorte/engine/`; editar a raiz e copiar.
- AD-11: `pathlib`, nada de caminho fixo.
- "Sinal só vale se medido": sem áudio, o fim do corte não muda; sem frases, as bordas não mudam.
- **Custo da 2ª passada (AC5):** +1 chamada por VOD com ~15 candidatos (~6–10 mil tokens de entrada).
  - Ollama local: R$ 0 e ~2–3 min a mais por VOD no `qwen3.5:9b`.
  - Claude pela assinatura: ~US$ 0,05–0,15 por VOD.
  - Gemini: dentro da cota gratuita.
  - Modo `heuristic`: nenhuma chamada.
- **Desvio aprovado pelo dono (2026-11-22):** sem re-medição de P@K a cada história; validação por TDD + olhada do dono.

---

### Task 1: bordas por frase (AC1)

**Files:** `picorte/ai/llm_router.py`, `tests/test_e36_bordas_ordem.py`

**Interfaces — produz:**
- `attach_neighbor_context` grava também `pre_sentences` e `post_sentences` (listas de `{"start","end","text"}`, no máximo 4 de cada lado, da mais próxima para a mais distante). O texto vai numerado em `pre_context` ("[-2] … [-1] …") e em `post_context` ("[+1] … [+2] …").
- Prompt: `extend_sentences_before` e `extend_sentences_after` (int 0–4) no lugar de `expand_start_sec` e `expand_end_sec`.
- `_apply_entries`: com N frases antes, `start = pre_sentences[N-1]["start"]`; com N frases depois, `end = post_sentences[N-1]["end"]`. Os campos antigos em segundos continuam aceitos só como reserva, caso algum provedor ainda mande segundos.

- [ ] Testes:
  - "estende 2 frases antes" → o início cai no começo exato da 2ª frase anterior;
  - "estende 1 depois" → o fim cai no fim da 1ª frase seguinte;
  - pedir 9 frases com só 3 disponíveis → usa a 3ª;
  - o contexto enviado vai numerado.

### Task 2: pré-roll do setup (AC2)

**Files:** `picorte/engine/snap_boundaries.py`, `score_clips.py` (+ espelho), `tests/test_e36_bordas_ordem.py`

**Interfaces — produz:** `setup_preroll_start(sentences, cause_s, *, min_back=3.0, max_back=8.0) -> float | None`. É o começo da frase mais antiga que começa em `[cause−8, cause−3]`. Se nenhuma frase começar ali, usa o começo da frase que cobre `cause−3`, desde que ele fique a até 15 s da causa. Sem frases, devolve `None`. A semente `chat_peak` usa esse valor como início (o fim não muda).

- [ ] Testes:
  - frase do setup começando 6 s antes da causa → início exato nela;
  - frase muito longa, começando 20 s antes → `None` (mantém a janela da 3.6.2);
  - a semente de chat usa o pré-roll.

### Task 3: fim nunca no meio do riso (AC3)

**Files:** `picorte/engine/prosody_events.py`, `score_clips.py` (+ espelho), `projects.py` (+ espelho), `tests/test_e36_bordas_ordem.py`

**Interfaces — produz:** `extend_end_past_laugh(segments, audio_path, *, max_len=None, source_duration=None, decoder=None, sample_rate=16000, max_extra=6.0) -> list[dict]`.
- Mede o riso (3–6 Hz) em janelas de 1,5 s com passo de 0,5 s, de `end−1` até `end+max_extra`.
- Se o riso está ativo no fim, o fim vira o fim da última janela com riso (antes da 1ª sem riso) + 1 s.
- Respeita `max_len`, a duração da fonte e `max_extra`. Grava `evidence.end_after_laugh_s`.
- Falha ao decodificar → o corte fica como está.

`select()` ganha `max_len=None`, que o `projects.py` passa a enviar.

- [ ] Testes (com um decodificador falso, sem ffmpeg):
  - riso cruzando o fim → o fim avança até o riso acabar + 1 s;
  - sem riso → o fim não muda;
  - riso que passaria do `max_len` → corta no limite;
  - erro do decodificador → nada muda.

### Task 4: Editor-Chefe sem viés de ordem (AC4)

**Files:** `picorte/ai/llm_router.py`, `score_clips.py` (+ espelho), `tests/test_e36_bordas_ordem.py`

**Interfaces — produz:**
- `LLMRouter.rerank_candidates(..., order_seed: int | None = None)`. Os candidatos vão ao Editor embaralhados por `random.Random(seed)`. Sem semente informada, ela é sorteada; no modo determinístico vale `BENCHMARK_SEED`. A semente usada volta em `result["ordem_semente"]`.
- 2ª passada: só nos ~15 finalistas (`SECOND_PASS_TOP = 15`), com a semente+1, num único lote. Para cada finalista avaliado nas duas: ajuste final = média das 2 passadas; diferença > 1,5 (`ORDER_DISAGREEMENT_MAX`) → `confianca_baixa = True`, e o tier `ouro` cai para `forte`. Os campos de texto (título, banner…) ficam os da 1ª passada.
- No modo Dupla: o embaralhamento vale nas 2 etapas, e a 2ª passada é feita pelo `companion_provider`.
- `select()` grava `ordem_semente` e o número de finalistas com `confianca_baixa` na saúde (`editor`).

- [ ] Testes (roteador falso, sem LLM):
  - mesma semente → mesma ordem enviada; sementes diferentes → ordens diferentes;
  - a 2ª passada só manda ≤ 15 candidatos;
  - discordância > 1,5 → `confianca_baixa` e sem `ouro`;
  - concordância → média aplicada e o `ouro` mantido;
  - o modo `heuristic` não faz nenhuma chamada.

### Task 5: verificação

- [ ] Suíte completa, espelhos idênticos, sprint-status 3.6.4 → `done` (só essa linha), olhada do dono, commit só com pedido.

## Resultado (2026-11-22)

- **Bordas por frase:** contexto numerado ([-2] … [+1]) e conversão frase → tempo exato; os segundos ficam só como reserva.
- **Pré-roll do setup:** a semente de pico de chat começa na frase do setup (`chat_seed_window` + `setup_preroll_start`).
- **Fim após o riso:** `extend_end_past_laugh` no fim da seleção; o `select()` recebe `max_len` do `projects.py`. Olhada em 3 lives sem IA: só 1 de 78 cortes seria estendido (W28).
- **Ordem:** embaralhamento com semente gravada (`ordem_semente`, determinística no conjunto de prova); 2ª passada nos 15 finalistas; média das 2 notas; discordância > 1,5 → `confianca_baixa`, sem `ouro`; a saúde do `editor` registra a semente e o total de finalistas com confiança baixa.
- **Defeito achado e corrigido:** no modo Dupla, a 2ª passada compararia a nota do filtro com a do Editor nos candidatos que o Editor não avaliou; agora o campo é limpo antes da etapa do Editor (há teste de regressão, conferido falhando sem a correção).
- **Testes antigos ajustados:** `test_llm_router_four_modes.py` assumia o viés de ordem (nota sempre para a posição 0); o roteador falso agora responde pelo conteúdo.
- Suíte: 746 passam (22 novos); 1 falha conhecida, só de ambiente, na worktree.
