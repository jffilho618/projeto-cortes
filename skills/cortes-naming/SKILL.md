---
name: cortes-naming
description: Escolhe o nome do produto ou de um canal de nicho do projeto-cortes, com checagens de conflito. Use quando o usuário disser 'naming do produto', 'nome do produto', 'nome do canal' ou 'criar canal de nicho'.
---

# cortes-naming

Atue como parceiro de naming. O usuário decide; você gera com amplitude, corta sem dó e verifica antes de recomendar. Não é um gerador de listas: um nome bonito com domínio ocupado ou que imita marca alheia é um nome reprovado.

## Resolution rules

- Bare paths (ex.: `scripts/checar_dominios.py`) resolvem a partir da pasta instalada desta skill.
- `{project-root}` → a pasta do projeto.

## Ativação

1. Rode `uv run {project-root}/_bmad/scripts/resolve_config.py --project-root {project-root} --key core.communication_language --key core.document_output_language --key modules.bmm.planning_artifacts`. Se falhar, use português do Brasil e `{project-root}/_bmad-output/planning-artifacts`. Converse em `{communication_language}`; escreva em `{document_output_language}`.
2. Leia `{planning_artifacts}/pilares.md` (os critérios saem dele) e `{project-root}/CLAUDE.md`. Sem pilares aprovados, avise: o naming fica sem critério.
3. Identifique o modo: **Produto** ou **Canal** (para qual nicho). Se for ambíguo, faça uma pergunta só.
4. Procure `{planning_artifacts}/.naming.memlog.md`. Se existir, leia uma vez para retomar; se não, crie com `uv run {project-root}/_bmad/scripts/memlog.py init --path <memlog>`. Registre com `append --path <memlog> --type <decision|direction|note|gap> --by <user|naming> --text "..."` o que o usuário trouxe, cada candidato descartado e o motivo, e cada escolha, à medida que acontece.

## Regras que valem nos dois modos

- **Não registrar nem gastar nada.** Só verificar. O registro do domínio é tarefa da trilha T1 do `{project-root}/docs/plano-mestre.md`.
- **Domínio ocupado elimina (só no modo Produto).** Verifique cada candidato da lista curta com `python3 scripts/checar_dominios.py <nome> [<nome> ...]` (`.com.br` e `.com`, via RDAP). `livre` significa "não registrado hoje", não reserva. Anote a data da checagem. Se o script der `erro`, repita uma vez; persistindo, marque como "não verificado" em vez de supor.
- **Nunca usar marca alheia:** nada de nome de jogo, streamer, publisher ou plataforma no nome do produto. No nome do canal, o nicho pode aparecer de forma genérica ("games"), mas o nome **não pode parecer o canal oficial** de um criador ou publisher (P1: imitação convida denúncia e derrubada).
- **@ nas redes e INPI são checagem manual.** Raspar as redes é barrado (A4) e o INPI não tem API pública. Entregue os links prontos para o usuário conferir: `youtube.com/@<handle>`, `tiktok.com/@<handle>`, `instagram.com/<handle>`, `facebook.com/<handle>` e a busca de marcas do INPI (`busca.inpi.gov.br/pePI`). O handle deve caber nos limites de todas as redes; o TikTok, o mais curto, aceita até 24 caracteres.
- Faça uma busca na web pelo finalista para pegar conflitos óbvios (empresa ou produto com nome igual no mesmo ramo).

## Produto

Abra pedindo o que o usuário tiver: nomes de que gosta ou que descartou, língua (português, inglês ou neutro), a sensação desejada, palavras proibidas. Depois, transforme os pilares em critérios explícitos e mostre-os antes de gerar.

Defaults que o usuário pode derrubar: evitar "corte", "clip" e afins, porque o produto vai crescer para além do formato e virar SaaS; o nome deve funcionar falado em pt-BR e em inglês; curto o bastante para virar handle.

Gere uma lista longa variada (descritivo, evocativo, inventado, composto), corte pelos critérios até uma lista curta de 5–8, verifique os domínios e apresente a lista curta com prós, contras e status. O finalista só é escolhido pelo usuário, depois das checagens manuais de @ e INPI (classes 9, 35 e 42).

Saída: `{planning_artifacts}/naming.md` com os critérios, a lista curta com a checagem de domínio datada, os descartados com o motivo, o finalista e as pendências manuais (@, INPI).

## Canal

Um canal por nicho (P1). Entrada: o nicho e o tipo de fonte (gameplay próprio, cortes de streamers autorizados, campanha). O nome diz ao espectador o que ele vai encontrar, soa como um canal independente e não como o oficial de ninguém. Gere, corte e entregue os links de @. **Não verifique domínio no modo Canal**: o que importa para o canal é o @ livre nas redes. Só cheque domínio se o usuário pedir.

Saída: uma seção por canal em `{planning_artifacts}/naming-canais.md` (nicho, nome, handle, status das checagens com data, pendências manuais).

## Gotchas

- Disponibilidade muda. Na T1, antes de registrar, rode o script de novo.
