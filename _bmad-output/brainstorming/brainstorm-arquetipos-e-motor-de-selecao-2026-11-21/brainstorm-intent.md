# Intenção — Etapa 2b: arquétipos novos e melhorias do motor de seleção (2026-11-21)

Fonte: `.memlog.md` desta pasta (104 ideias, modo autônomo, 4 técnicas). Insumos: pesquisa 2a (`planning-artifacts/research/technical-motor-selecao-cortes-2026-11-21/research.md`, R1–R10 + medição do atraso do chat) e auditoria E3 (A7–A12). Próximo consumidor: `bmad-correct-course` + `cortes-pilares` (etapa 2c).

## Insights centrais

1. **Nobada sai de sinais baratos que já temos:** fala autodepreciativa + riso na prosódia + riso no chat ~35 s depois. Visão/keyframes só confirmam.
2. **Auto-calibrar o atraso do chat por VOD** (correlação prosódia↔chat, limitada a 15–45 s) resolve o atraso variável e ainda vira métrica de saúde.
3. **Silêncio digital une três frentes:** falha técnica, mico/choque e P1 (trecho mutado por copyright — o VOD medido tinha vários).
4. **Medir o baseline antes de mexer** é a vacina contra o padrão do E4 ("done" sem prova).
5. **Bordas valem mais que a nota:** atraso do chat, pré-roll de contexto e fim após o riso são uma feature só.

## MUST — etapa 3

| # | Item | Liga com |
|---|---|---|
| M1 | Arquétipo **`nobada_vacilo`**: léxico PT-BR autodepreciativo ("burro demais", "não acredito que eu fiz isso", "volta, volta"), "silêncio de choque" após morte, riso do streamer, riso no chat atrasado, tela de morte do dossiê quando houver | R1, `clutch_fail` |
| M2 | Arquétipo **`mico_constrangimento`**: silêncio após fala/piada + chat "cringe"/💀/"vergonha alheia" | R1 |
| M3 | Mapa **emote/léxico → arquétipo** no chat e nos comentários (KEKW/kkk→nobada, monkaS→susto, Pog→clutch, F/Sadge→perda, ❤️→wholesome, 💀→mico) | R1, comentários |
| M4 | **Sismógrafo 2.0:** pico de chat em t → procurar a causa em t−45..t−15 ancorando na prosódia; auto-calibração do atraso por VOD; filtro de bots/comandos/duplicatas; peso por diversidade de autores e concordância | R2, medição própria |
| M5 | **Bordas:** Editor-Chefe devolve índices de frase (não segundos); fim do corte após o término do riso; pré-roll de 3–8 s do setup | R6, R7 |
| M6 | **Ordem embaralhada** dos candidatos ao Editor-Chefe (divergência = baixa confiança) | R3 |
| M7 | **Baseline de Precision@K** do motor atual em 3 VODs com gabarito automático (clipes da Twitch / comentários com timestamp) **antes** de mexer, e de novo depois | R4 |
| M8 | **Detector de silêncio digital**: descartar/avisar trecho mutado (P1) e marcar falha técnica | P1 |

## SHOULD

- Arquétipos `perda_dramatica`, `falha_tecnica`, `bug_sorte_absurda`, `fora_do_jogo` (IRL).
- Nota **standalone** ("entende sem conhecer o streamer?") — se não, vai para Longo/compilação.
- Tier **ouro exige 2 sinais independentes** concordando.
- **Nota de confiança do projeto** = quantos sinais rodaram de verdade (dados para o painel W9).
- **Variação de template por arquétipo** + freeze/seta no momento-chave (P2: "template em massa" não conta como transformação).
- **Versão TikTok 60–75 s** do mesmo momento (Short seco 15 s + versão com contexto e replay).

## COULD

`wholesome`, `lore_bordao`, `licao_dica`, `doacao_lida`, `interacao_chat`; casamento fala↔chat; torneio por pares nos top 10; perfil do streamer; detector de virada (arcos A12); compilação "top vacilos".

## WON'T agora

Pesos aprendidos (Bandit, E7 — depende do gabarito); emotes por embeddings; micro-expressões novas; botões 👍/👎 no Estúdio (UI do E6, junto com W9).

## Perguntas para a 2c

- `rage_tilt` cobre treta com alvo externo ou separa em `treta`?
- Cotas por arquétipo: nobada entra com cota própria no Multi-Track Recall?
- Embaralhar a ordem custa chamadas extras ao LLM: 1 ou 2 passadas por lote?
- Frente de formato (A8, A9, A11, A12) entra junto com M5 ou em leva separada?
