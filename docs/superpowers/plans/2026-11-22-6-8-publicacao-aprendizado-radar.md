# História 6.8 — Publicação assistida, Aprendizado e Radar (plano enxuto)

> **Para quem executa:** use o superpowers:executing-plans. É TDD nos serviços Python e nas regras do front. **Sem commit** até o dono pedir.

**Objetivo:** publicar à mão com tudo pronto e sem perder o rastreio (Pacote do Dia, links publicados, pendência C2 na faixa) e mostrar, travado e honesto, o que ainda não existe (contas OAuth, publicação automática, Aprendizado e Radar), com os contadores que já são reais.

**Arquitetura:**
- Um serviço `picorte/services/publicacao.py` monta o pacote a partir dos projetos e do banco, e reaproveita:
  - `export_daily_bundle` (exporta os arquivos, com o portão P1 pré-exportação);
  - `check_cadence` (calcula quando o corte sai em cada rede);
  - o veredito do `.meta.json`.
- Exportar grava uma publicação `exportado` por corte e por rede. É essa publicação que vira a pendência da C2.
- A pendência só sai de dois jeitos: com um link válido (vira `publicado`) ou com "Não vou postar" e um motivo (vira `nao_vou_postar`, com desfazer). Não existe "marcar como postado" sem link.

**Spec:** `_bmad-output/planning-artifacts/epics.md` (Story 6.8) e `ux-designs/ux-projeto-cortes-2026-11-21/EXPERIENCE.md` (seções Publicação, Aprendizado e State Patterns).

## Restrições globais

- C2: um corte exportado sem link vira pendência visível na faixa "Na sua mesa" e na Publicação.
- C3: o Pacote do Dia não depende de 👍 nem de passar pela Revisão.
- A5: travado nunca mostra dado falso; os contadores vêm do banco.
- Regra 3 e A4: nada de OAuth nem automação de navegador; as contas ficam travadas até a 6.1.
- C4: abrir a pasta usa o `_open_in_file_manager` (funciona em Windows e Linux).
- Não editar `projects/`, `benchmarks/` nem os arquivos da sessão do motor. Só testes leves.

## Contrato

- `GET /api/publicacao/pacote` devolve:
  - `prontos[]`: `{projeto, seg, stem, titulo, tier, risco, quando: {rede: "agora" | iso}}`;
  - `fora[]`: `{projeto, seg, titulo, motivo, acao?}`;
  - `cadencia`: `{rede: {status, proxima, motivo}}`.
- `POST /api/publicacao/exportar` com `{itens: [{projeto, stem}]}` devolve `{pastas, exportados, pulados}`.
- `GET /api/publicacao/links` devolve `links[]`: `{id, projeto, seg, titulo, rede, status, url, motivo, exportado_em, publicado_em, kit}`.
- `POST /api/publicacao/links/{id}` com `{url}` valida o link pela rede e grava `publicado` com `published_at`.
- `POST /api/publicacao/links/{id}/nao-vou-postar` com `{motivo}` e `POST /api/publicacao/links/{id}/desfazer`.
- `POST /api/publicacao/abrir` com `{pasta}` só abre pastas dentro de `prontos_para_postar/`.
- `GET /api/aprendizado/contadores` devolve `{rotulos: {bons, ruins}, publicacoes_com_link, gabaritos, meta}`.
- `/api/mesa` passa a devolver `links_pendentes` como número.
- **Banco:** a coluna `publications.motivo` (migração por `_ADDED_COLUMNS`). O disjuntor de claim também segura as publicações `exportado`, e a prévia passa a contá-las.

## Tarefas

1. `publicacao.py`: validação de link, pacote (prontos e fora, com motivo), exportados, link, não vou postar e desfazer, listar links, contadores; mais os testes.
2. Banco e disjuntor: coluna `motivo`; `exportado` conta como pendente no claim. Mais os testes.
3. Rotas `rotas_publicacao.py`, mesa com `links_pendentes`, capacidades (PUB-1 e PUB-3) e testes de API.
4. Front:
   - **Publicação:** abas Pacote do Dia, Links e Contas, com o cartão por rede (copiar em 1 clique, colar link, não vou postar);
   - **Aprendizado:** contadores reais e as seções travadas;
   - **Radar:** seções travadas;
   - chip de links pendentes na faixa e contagem na sidebar.

   Mais os testes Vitest.
5. Verificação no Edge com a cópia do banco e exportação num diretório do scratchpad; registro do resultado.

## Registro da execução (2026-11-22)

Status: as tarefas 1 a 5 estão feitas, **sem commit** (aguarda o pedido do dono).

- **Backend:**
  - `publicacao.py` e `rotas_publicacao.py`;
  - coluna `publications.motivo`; o `exportado` entra no disjuntor de claim e na prévia;
  - `/api/mesa` com `links_pendentes` real, que vira `None` com motivo se o banco não abrir;
  - PUB-1 e PUB-3 ligadas (`ligou_em` 2026-11-22).
- **Front:**
  - **Publicação:** Pacote do Dia com seleção, "quando sai" por rede, exportar e abrir a pasta, e a lista de quem ficou de fora, agrupada por VOD e motivo, com "Preparar de novo";
  - **Links:** cartão por corte, copiar em 1 clique, colar link validado por rede e "não vou postar" com motivo de 1 clique e desfazer;
  - **Contas** travada; **Aprendizado** com contadores reais e seções travadas; **Radar** travado;
  - contagem de links pendentes na sidebar.
- **Pedido do dono no meio da história:** ícones das redes no padrão do pacote. São desenhos de linha próprios, com o traço do sprite, dentro de um ladrilho arredondado; Shorts em pé e Longo deitado. Aparecem na Publicação e no Escudo.
- **Verificação:**
  - Vitest: 113 testes passando, check e build ok;
  - pytest leve: 221 testes;
  - Edge em 2560×1440 com a cópia do banco e a saída no scratchpad, sem erro no console. O pacote real está vazio e explica por quê: os 13 cortes do único VOD renderizado são anteriores ao portão. Os 2 links já publicados aparecem.
  - Nada foi exportado, ninguém clicou em "Preparar de novo" e o `projects/` está igual ao de antes.
- **Ao abrir o Estúdio de novo**, o `picorte.db` real ganha a coluna `motivo`. A migração é automática e só acrescenta.
- **Desvio de TDD:** `publicacao.ts` (as duas primeiras regras), `Publicacao.tsx`, `Aprendizado.tsx` e `IconeRede.tsx` foram escritos antes de verem o teste falhar.
