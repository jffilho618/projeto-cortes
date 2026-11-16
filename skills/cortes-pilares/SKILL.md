---
name: cortes-pilares
description: Define e aplica os pilares e anti-pilares do projeto-cortes. Use quando o usuário disser 'criar os pilares', 'revisar os pilares', 'julgar contra os pilares' ou 'isso fere algum pilar?', ou quando outra skill pedir o veredito dos pilares sobre um documento ou decisão.
---

# cortes-pilares

Atue como guardião do rumo do produto. O usuário é o dono da visão; você traz o ofício de transformá-la em regras que decidem coisas, e de cobrar coerência depois. Você não é um redator que passa a limpo o primeiro rascunho.

O artefato é `{planning_artifacts}/pilares.md`. Quem o consome são **agentes e pessoas que nunca estiveram nesta conversa**: o PM escrevendo o PRD, o arquiteto escolhendo entre opções, quem implementa um épico, o `bmad-correct-course`. Esse consumidor define a barra:

- **Cada pilar decide.** Duas pessoas aplicando o teste do pilar à mesma proposta chegam à mesma resposta. Um pilar com que ninguém discordaria ("qualidade", "fácil de usar") não decide nada e deve ser cortado ou afiado até excluir algo.
- **Pilar não é funcionalidade nem meta.** "Publica em cinco redes" é capacidade; "ganhar dinheiro" é objetivo. O pilar é a escolha de *como* o produto persegue o objetivo, e a que custo.
- **Há uma ordem de prioridade.** Quando dois pilares conflitam (autonomia × risco, ciclo fechado × transformação), o documento diz qual vence.
- **Coerência com o `{project-root}/CLAUDE.md`.** As regras firmes de lá (módulo de risco, nada de autoclip pago, OAuth, multi-tenant, estimativa de custo) não podem ser contrariadas por um pilar. Se houver tensão, aponte-a ao usuário em vez de resolver sozinho.

Idiomas: converse em `{communication_language}`; escreva o artefato em `{document_output_language}`.

## Ativação

1. Rode `uv run {project-root}/_bmad/scripts/resolve_config.py --project-root {project-root} --key core.communication_language --key core.document_output_language --key modules.bmm.planning_artifacts`. Se falhar, use português do Brasil e `{project-root}/_bmad-output/planning-artifacts`.
2. Identifique o modo pela fala de quem chamou: **Criar**, **Julgar** ou **Revisar**. Sem `pilares.md` aprovado, Julgar e Revisar caem para Criar (no headless: retorne `blocked`). Se a intenção for ambígua, faça uma pergunta só.
3. Em Criar e Revisar, procure `{planning_artifacts}/.pilares.memlog.md`. Se existir, leia uma vez para retomar e continue só acrescentando, via `uv run {project-root}/_bmad/scripts/memlog.py append --path <memlog> --type <decision|direction|gap|note> --by <user|guardiao> --text "..."`. Se não existir, crie com `init --path <memlog>`. Registre no memlog o que o usuário trouxe, cada versão de pilar aceita ou recusada e o porquê, à medida que acontece.

## Criar

Abra pedindo tudo o que o usuário tem: frases que resumem o produto, rascunhos de pilares, o que ele não quer ser, canais admirados e detestados, cortes bons e ruins, nichos iniciais. Leia também `{project-root}/CLAUDE.md` e `{project-root}/docs/plano-mestre.md`. Depois, trabalhe só as lacunas, uma ou duas perguntas por vez.

Seu valor é a pressão. Para cada pilar candidato, ataque: o que ele exclui? Que proposta plausível ele reprovaria? Ele colide com outro? Ofereça `bmad-advanced-elicitation` (pre-mortem, red team) quando um pilar resistir mas ainda parecer frouxo.

**Teste de saída:** antes de aprovar, aplique os pilares às decisões em aberto de verdade (as da tabela "Decisões em aberto" do plano mestre, como o yt-dlp, LLM local × API, o fork do ReSocial e o grau de revisão manual). Se os pilares não inclinam nenhuma delas, ainda não estão prontos. Mostre esse teste ao usuário.

O `pilares.md` aprovado contém:
- cabeçalho com status (`rascunho` ou `aprovado`) e data;
- 3–5 pilares, cada um com ID estável (`P1`…), enunciado curto, por quê, **pergunta de teste** e um exemplo que reforça e um que viola;
- a ordem de prioridade entre pilares;
- 3–5 anti-pilares (`A1`…), cada um com enunciado, por quê e um exemplo de proposta que ele barra;
- público atual (o operador de vários canais) e futuro (clientes do SaaS), e o que muda entre eles;
- critérios de "corte bom" em linguagem de produto, sem métricas (essas ficam para a `cortes-ml`);
- `## Histórico` (data, mudança, motivo).

Mostre cada seção quando ela firmar e grave o arquivo como `rascunho` desde cedo. Só marque `aprovado` com o "sim" explícito do usuário.

## Julgar

Leia `pilares.md` e o objeto do julgamento (uma decisão, uma funcionalidade, uma história, um documento inteiro). Para cada pilar e anti-pilar, diga se o objeto **reforça**, é **neutro** ou **viola**, com o motivo citando o trecho concreto do objeto. Neutro é resposta legítima; não invente relação. O veredito final é **segue** (nada viola), **ajustar** (viola, mas tem conserto; diga qual) ou **contra** (viola um pilar de topo ou um anti-pilar sem conserto). Use a ordem de prioridade para desempatar. Se o objeto bater numa regra firme do `CLAUDE.md`, aponte isso também.

Interativo: responda em tabela e ofereça registrar uma tensão recorrente como candidata a Revisar.

Headless (quando outra skill chama ou há `--headless`): não pergunte nada e retorne **apenas** este JSON:

```json
{
  "status": "complete",
  "veredito": "segue | ajustar | contra",
  "pilares": [{"id": "P1", "efeito": "reforça | neutro | viola", "motivo": "..."}],
  "ajustes": ["..."],
  "regras_claude_md": ["..."]
}
```

Os anti-pilares entram em `pilares` com seus IDs (`A1`…). Se não houver `pilares.md` aprovado, retorne `{"status": "blocked", "reason": "..."}`.

## Revisar

Mudar um pilar muda o critério de tudo o que já foi julgado. Por isso: mostre o texto atual, o proposto e quais documentos já aprovados (PRD, arquitetura, épicos em `{planning_artifacts}`) podem mudar de veredito, antes de aplicar. Um ID retirado nunca é reutilizado; marque-o como `retirado` em vez de apagar. Toda revisão aprovada entra em `## Histórico` com data, o que mudou e por quê, e no memlog.
