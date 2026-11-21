# Proposta de Mudança de Sprint — Motor Calibrado e Medido (Épicos 3.6 e 3.7)

- **Data:** 2026-11-21
- **Projeto:** `projeto-cortes` (**Picorte** / canal **Bomba Clips**)
- **Workflow:** `bmad-correct-course` (modo incremental, 6 propostas aprovadas uma a uma) + portão `cortes-pilares` (Julgar)
- **Status:** **APROVADA** pelo dono em 2026-11-21 (6 propostas uma a uma + 2 acréscimos + história 3.6.6)
- **Veredito dos pilares:** **SEGUE** ✅ (Seção 6)
- **Classificação de escopo:** **Moderado** — dois épicos novos inseridos antes do Épico 5 (pausado) e notas nos Épicos 5, 6 e 7, sem rollback nem revisão de MVP.
- **Insumos:** auditoria [`auditoria-e3-done-vs-ligado-2026-11-20.md`](../implementation-artifacts/auditoria-e3-done-vs-ligado-2026-11-20.md) · pesquisa [`research/technical-motor-selecao-cortes-2026-11-21/research.md`](research/technical-motor-selecao-cortes-2026-11-21/research.md) · brainstorming [`brainstorm-arquetipos-e-motor-de-selecao-2026-11-21/brainstorm-intent.md`](../brainstorming/brainstorm-arquetipos-e-motor-de-selecao-2026-11-21/brainstorm-intent.md)

---

## 1. Resumo do problema

**Gatilho.** O code review do Épico 4 achou muitos bugs, e o dono pausou o Épico 5 para endurecer o motor de seleção (E3/E3.5), o coração do produto. A auditoria (etapa 1) achou o padrão "done no papel, desligado no pipeline" (visão nunca rodou em VOD longo, chat nunca baixado, Editor-Chefe caía em silêncio para o modo heurístico) — corrigido na etapa 1b (commits `e85993e`, `2dd349b`).

**O que a evidência mostrou depois da 1b:**
1. **O chat chega ~30 s atrasado e o motor não compensa.** Medição própria no VOD `x50ONQrBPRM` (52 min, 10.815 mensagens): o chat sobe a partir de +20 s e tem pico em +25 a +35 s depois do salto de áudio (riso no chat: ~35 s). A literatura dá 20–27 s (Lightor). O Sismógrafo monta a janela em `[pico − 6 s, pico + 8 s]` (`picorte/engine/chat_seismic.py:148`): o corte começa ~25 s depois do lance que causou o pico.
2. **Faltam tipos de momento que viralizam.** Os clipes mais vistos da Twitch são de reação humana; o modelo treinado em ~2 mi de clipes separa falha, constrangedor e vergonhoso. Entre os 16 tipos do brainstorming de 19/11 (agrupados em 10 rótulos) não há **vacilo bobo (nobada)** nem **mico/constrangimento** — o `clutch_fail` busca o fail *cinematográfico* (killfeed, POG/CLUTCH).
3. **Não existe medição de acerto.** Os pesos foram escolhidos "a olho" e nenhuma mudança no motor foi medida antes/depois.
4. **Bordas e juiz:** início e fim são o fator que mais pesa na qualidade (HIVE: gancho 0,71 → 0,28 com bordas aleatórias); o Editor-Chefe ajusta bordas em segundos e recebe os candidatos sempre na mesma ordem (rerank por LLM é sensível à ordem).
5. **Silêncio digital:** o VOD medido tinha de 10 a 89 s mudos a cada 3 min — provável música removida pelo YouTube; o motor não distingue isso.

**Tipo:** abordagem falha (calibração) + requisito novo vindo de evidência.

## 2. Análise de impacto

| Épico | Impacto |
|---|---|
| 1, 2, 3, 3.5, 4 | Sem rollback. Continuam `done`. |
| **3.6 (novo)** | **Leva 1 — seleção:** gabarito e baseline, Sismógrafo 2.0, nobada/mico, bordas e juiz sem viés, silêncio digital e confiança. |
| **3.7 (novo)** | **Leva 2 — formato:** pendências A8, A9, A11, A12 da auditoria + versão TikTok 60–75 s + variação de template. Só começa depois do 3.6 medido. |
| 5 | Continua pausado; notas em 5.3, 5.4 e 5.x (sem mudar escopo). |
| 6 | Nota em 6.3 (painel de saúde, confiança do projeto, 👍/👎). |
| 7 | Notas em 7.2/7.3 (12 arquétipos, consumo do gabarito). |

**Artefatos:** `epics.md`, `architecture.md` (convenção nova), `sprint-status.yaml`, `docs/plano-mestre.md`. Não há PRD (a fonte é `specs/spec-picorte/SPEC.md`, sem conflito: a mudança refina CAP-1/CAP-4/CAP-5). UI fica para o E6.

**Técnico:** `chat_seismic.py`, `prosody_events.py`, `multitrack.py`, `score_clips.py` (+ espelho em `picorte/engine/`), `llm_router.py`, `golden_examples.json`, `health.py`; módulo novo `picorte/engine/benchmark.py`.

## 3. Caminho recomendado

**Ajuste direto** (Opção 1). Rollback não se aplica (o trabalho existente é a base). Revisão de MVP não se aplica (uso próprio, sem MVP comercial).

- **Esforço:** Épico 3.6 ≈ 5 histórias médias; Épico 3.7 ≈ 5 histórias médias.
- **Risco:** baixo a médio — mexe no coração do motor, mitigado pela medição antes/depois (3.6.1) e pelo registro de saúde.
- **Prazo:** o Épico 5 só volta depois do 3.6 (e do 3.7, se o dono mantiver a ordem).
- **Custo (regra 6):** tudo local e grátis, exceto a 2ª passada do Editor-Chefe (3.6.4): +1 chamada por VOD com ~15 candidatos (~6–10 mil tokens de entrada) — Gemini dentro da cota gratuita; Claude (assinatura) ~US$ 0,05–0,15 de limite por VOD; modo `heuristic` sem chamadas.

**Decisões do dono nesta etapa (2026-11-21):**
- Treta continua em `rage_tilt`; treta entre streamers fica com o Detector de Treta do 5.3.
- Viés de ordem: 1 passada embaralhada em tudo + 2ª passada só no top 15.
- Formato vira a leva 2 (Épico 3.7), depois da seleção medida.
- Gabarito da leva 1 = comentários com horário + heatmap do YouTube (os clipes da Twitch apontam para o VOD da Twitch, não para o upload do YouTube; ficam para quando a fonte for a Twitch).
- Glitch, doação/TTS e momento fora do jogo **já estão cobertos** (`descoberta_detalhe` e `chat_trolagem`); `falha_tecnica` vira tag em `chat_trolagem`; `perda_dramatica` só depois de medir.

## 4. Propostas detalhadas (aprovadas)

### 4.1. `epics.md` — novo Épico 3.6

```
## Epic 3.6: Motor Calibrado e Medido — Sismógrafo 2.0, Nobada/Mico, Bordas e Juiz Confiável (Leva 1)
```
Objetivo: corrigir a calibração do motor de seleção com base em evidência e provar a melhora com números, antes de retomar o Épico 5.

**Story 3.6.1 — Gabarito Automático e Baseline de Precision@K.** AC:
1. `picorte/engine/benchmark.py` monta gabarito fraco por VOD a partir de `comment_seeds.json` e do heatmap (sem anotação manual) e calcula Precision@K (K=5,10) contra o acaso (K/N).
2. Baseline gravado **antes** de qualquer mudança do 3.6 em 3 VODs reais já processados e re-medido ao fim de cada história; resultado em `benchmarks/<data>.json`.
3. VOD sem comentários com horário nem heatmap é marcado "sem gabarito" e fica fora da média.
4. Custo zero: só dados já baixados; nenhuma chamada nova a LLM.

**Story 3.6.2 — Sismógrafo 2.0: Atraso Compensado, Anti-Ruído e Tipo de Reação.** AC:
1. Para cada pico de chat em t, a causa é procurada em [t−45 s, t−15 s], ancorada no evento de prosódia mais forte da faixa; a semente e `score_chat_window` usam essa janela deslocada (hoje `[pico−6 s, pico+8 s]`, `chat_seismic.py:148`).
2. Auto-calibração por VOD: correlação cruzada prosódia↔chat no `discover`, limitada a 15–45 s; atraso usado e força da correlação vão para `engine_health.json` (fraca = "chat pouco confiável"; sem correlação usa 30 s, medido em 2026-11-21).
3. Anti-ruído: descarta comandos (`!sorteio`, `!pix`…), links e mensagens idênticas repetidas; o pico pesa mais quando vem de muitos autores e quando as mensagens são curtas e parecidas (concordância).
4. Tipo de reação por pico via léxico de emotes/palavras PT-BR (riso, hype, susto, cringe, luto/F, amor), salvo no pico e repassado ao Editor-Chefe. Pedido explícito de corte no chat ("CLIPA", "clip it", "corta essa") é o tipo de maior peso.
5. Chat com menos de 20 msg/min: Sismógrafo desliga e a saúde registra "chat pequeno demais".
6. Teste com o chat real de `x50ONQrBPRM`; Precision@K re-medido.

**Story 3.6.3 — Arquétipos `nobada_vacilo` e `mico_constrangimento` (10 → 12 rótulos).** AC:
1. `CANONICAL_ARCHETYPES` passa de 10 para 12 com `nobada_vacilo` (erro bobo de execução) e `mico_constrangimento` (vergonha social, piada que não colou, silêncio constrangedor); prompt do Editor-Chefe, `golden_examples.json` (≥ 2 exemplos de cada) e validação atualizados.
2. Nova pista "Vacilo" no `multitrack.py` com cota própria, semeada por léxico PT-BR autodepreciativo ("burro demais", "não acredito que eu fiz isso", "volta, volta", "que vergonha") e pelo streamer anunciando o corte ("isso vai virar corte", "clipa isso", "manda pro TikTok"), "silêncio de choque" (1–3 s sem fala após evento forte, seguido de riso), riso do streamer na prosódia e pico de chat do tipo riso/cringe.
3. Mapa emote/palavra → arquétipo também nos comentários com horário.
4. Silêncio só conta como mico/choque se precedido de fala/evento e seguido de reação.
5. Só sinais baratos já medidos; keyframes (opcional) só confirmam candidatos a nobada. Nenhum custo novo por padrão.
6. Testes com transcrições sintéticas dos dois casos + Precision@K re-medido.

**Story 3.6.4 — Bordas por Frase, Fim Após o Riso e Editor-Chefe sem Viés de Ordem.** AC:
1. Editor-Chefe ajusta bordas por frases (`extend_sentences_before/after`) em vez de segundos (`expand_start_sec`/`expand_end_sec`); o motor converte pelos timestamps de palavra do Whisper (como o `llm_scout` faz com `sentence_id`).
2. Pré-roll de setup: semente de reação (chat, riso, susto) recua até o começo da frase do setup, 3–8 s antes da causa.
3. Fim nunca no meio de um riso: riso cruzando o fim avança o fim até o riso terminar (+1 s), respeitando a duração máxima.
4. Ordem dos candidatos embaralhada (semente gravada) em toda passada; 2ª passada, com outra ordem, só nos ~15 finalistas. Diferença de nota > 1,5 marca `confianca_baixa` e impede `ouro`.
5. Custo estimado da 2ª passada conforme Seção 3.
6. Testes: conversão frase→tempo, riso cruzando o fim, reprodutibilidade da ordem; Precision@K re-medido.

**Story 3.6.5 — Detector de Silêncio Digital, Tier Ouro com 2 Sinais e Nota de Confiança.** AC:
1. Trechos de silêncio digital (≤ −90 dB por ≥ 2 s) são marcados; candidato com > 20% de silêncio digital é descartado e a saúde registra "trecho mutado/sem áudio" (P1).
2. Silêncio digital seguido de chat "caiu"/"travou"/"F" vira tag `falha_tecnica` em `chat_trolagem` (#16), sem arquétipo novo.
3. Tier `ouro` exige ≥ 2 sinais independentes medidos concordando; senão `forte`.
4. Nota `standalone` (0–10) do Editor-Chefe; abaixo de 5 o corte não vai para Short isolado (fica para Longo/compilação).
5. `engine_health.json` ganha `confianca_projeto` (quais sinais rodaram de verdade) para o painel do E6 (W9).
6. Heatmap ("mais repetidos") rebaixado a bônus fraco em Shorts (hoje +1,2 e semente obrigatória) e usado principalmente para escolher o miolo do Longo de 3–5 min — a pesquisa mostrou que é ruidoso (YTMR500).
7. Testes com áudio sintético mudo e candidatos de 1 vs 2 sinais.

**Story 3.6.6 — Pesos Calibrados pelo Gabarito (degrau 2).** AC:
1. Só começa quando houver **≥ 20 VODs com gabarito** acumulados pela 3.6.1 (o uso normal vai acumulando).
2. Regressão logística por pares (trecho marcado pelo público × trecho comum do mesmo VOD) sobre os sinais já medidos, local em CPU, com pesos legíveis por sinal.
3. Validação cruzada por VOD (treina em uns, mede em outros); os pesos novos só entram se ganharem do baseline em Precision@K; senão ficam os atuais.
4. Pesos versionados (`weights/<data>.json`) com o resultado da medição; o Bandit do Épico 7 (degrau 3, desempenho real dos cortes publicados) parte deles.

**Anotados no `deferred-work.md` (sem destino nesta leva):** arquétipos `wholesome` e `licao_dica`; separar riso do streamer do riso de convidado; casar fala com chat (leitura de mensagem); cota de diversidade por canal/dia na publicação; telas de morte no dossiê do jogo.

### 4.2. `epics.md` — novo Épico 3.7 (leva 2, ACs detalhados ao iniciar)

```
## Epic 3.7: Formato que Retém — Cold Open, Loop, Layout Dinâmico, Par Short↔Longo e Arcos (Leva 2)
Story 3.7.1: Cold Open Reverso 1,5s e Seamless Loop renderizados de verdade (A9)
Story 3.7.2: Layout dinâmico + Sniper Crop ligados ao render de games (A8)
Story 3.7.3: Par Short↔Longo só com sobreposição real + versão TikTok 60–75s do mesmo momento (A11)
Story 3.7.4: Renderizar arcos de 2 atos e compilação por arquétipo, incl. "top vacilos" (A12)
Story 3.7.5: Variação de template por arquétipo + freeze/seta no momento-chave (P2)
```

### 4.3. `epics.md` — notas nos épicos futuros (sem mudar escopo)

- **5.3:** treta entre streamers fica aqui; treta dentro da live continua `rage_tilt`.
- **5.4:** bordões e piadas internas (`lore_bordao`) e perfil do streamer já cobertos; incluir emotes do canal.
- **5.x:** clipes da Twitch como gabarito quando a fonte for a Twitch.
- **6.3:** painel "Saúde do motor" (W9) + `confianca_projeto` + botões 👍/👎 por corte, que viram rótulo.
- **7.2 / 7.3:** 12 arquétipos; consomem o gabarito do 3.6.1.

### 4.4. `architecture.md` — convenção nova

> **Sinal só vale se medido.** Todo sinal do motor de seleção registra `ok`/`na`/`failed` em `engine_health.json` e só chega ao Editor-Chefe quando foi medido. Toda mudança no motor de seleção exige Precision@K antes e depois (`picorte/engine/benchmark.py`).

### 4.5. `sprint-status.yaml` e `docs/plano-mestre.md`

`epic-3-6` (3-6-1 … 3-6-6) e `epic-3-7` (3-7-1 … 3-7-5) em `backlog`, antes do `epic-5`; plano-mestre com a ordem E3.6 → E3.7 → E5.

## 5. Handoff

- **Escopo:** Moderado → backlog reorganizado aqui; implementação pelo `superpowers` (TDD), história a história, começando obrigatoriamente pela 3.6.1 (baseline).
- **Depois da implementação:** etapa 4 do plano (code review dirigido do E3/E3.5 + Épico 3.6, de preferência no Gemini) e etapa 5 (correções).
- **Critérios de sucesso:** Precision@K do motor depois do 3.6 ≥ baseline em pelo menos 2 dos 3 VODs; nenhum sinal sem registro de saúde; suíte de testes verde; espelhos raiz ↔ `picorte/engine/` idênticos.

## 6. Veredito dos pilares

Portão `cortes-pilares` (modo Julgar), contra `pilares.md` aprovado (2026-11-16, revisões até 2026-11-18).

| ID | Efeito | Motivo (trecho do objeto) |
|---|---|---|
| **P1** | reforça | 3.6.5 descarta trechos com silêncio digital ("trecho mutado/sem áudio", provável música removida pelo YouTube) e registra na saúde; o gabarito (3.6.1) usa só `comment_seeds.json`/heatmap já coletados de fontes que passaram no portão; nenhum download novo nem fonte nova. |
| **P2** | reforça | 3.7.5 (variação de template por arquétipo, freeze/seta) responde à regra de 2026-10 contra "template em massa"; nota `standalone` (3.6.5) materializa o critério "se entende sozinho"; 3.7.3 gera a versão TikTok 60–75 s com contexto próprio, não um reupload. |
| **P3** | reforça | Baseline e Precision@K antes/depois (3.6.1); auto-calibração do atraso do chat **por VOD** (3.6.2) usa o dado de agora em vez de um número fixo; 👍/👎 e gabarito alimentam o E7. |
| **P4** | reforça | Benchmark, Sismógrafo, léxico, pistas e regras de borda são locais; o LLM continua peça trocável via roteador (Gemini/Claude/Ollama/heurístico), e a 2ª passada só reduz o viés dele. |
| **P5** | neutro | Nenhum passo manual obrigatório: gabarito automático; 👍/👎 é opcional (E6). |
| **A1** | neutro | Nenhuma timeline de edição. |
| **A2** | neutro | Nada de volume extra nem disfarce. Cuidado na 3.7.3: o replay em câmera lenta deve ser recurso editorial pontual, nunca aplicado ao corte inteiro para alterar a assinatura do vídeo. |
| **A3** | neutro | — |
| **A4** | neutro | Clipes da Twitch via API oficial ficaram para o E5; nada de automação de navegador. |
| **A5** | reforça | Precision@K é número real contra o acaso; VOD "sem gabarito" fica fora da média; `confianca_projeto` mostra o que rodou de fato, sem estimativa disfarçada. |

**Regras do `CLAUDE.md`:** regra 6 (custo) atendida na Seção 3; regra 2 (nada de autoclip pago) e AD-11 (Windows + Linux) sem conflito. Nenhuma tensão nova.

**Veredito: SEGUE ✅** (nenhuma violação; uma ressalva de implementação na 3.7.3, registrada acima).
