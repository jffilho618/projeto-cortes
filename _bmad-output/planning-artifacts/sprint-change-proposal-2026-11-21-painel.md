# Proposta de Mudança de Sprint — Painel Final "Estúdio do Criador" (Épico 6, histórias 6.3 a 6.8)

- **Data:** 2026-11-21
- **Projeto:** `projeto-cortes` (**Picorte** / canal **Bomba Clips**)
- **Workflow:** `bmad-correct-course` (modo incremental, 6 propostas aprovadas uma a uma) + portão `cortes-pilares` (Julgar)
- **Status:** **APROVADA** pelo dono em 2026-11-21 (6 propostas uma a uma + proposta completa)
- **Veredito dos pilares:** **AJUSTAR → SEGUE**, com as condições C1–C4 aceitas pelo dono (Seção 6)
- **Classificação de escopo:** **Moderado** — a 6.3 vira 6 histórias; o painel passa à frente do 3.6.2+ e do E5. Sem rollback e sem revisão do MVP.
- **Insumos:**
  - [`brainstorm-intent.md`](../brainstorming/brainstorm-mapa-painel-estudio-do-criador-2026-11-21/brainstorm-intent.md) (mapa de capacidades);
  - [`handoff-sessao-04.md`](../../docs/handoff-sessao-04.md);
  - [pesquisa da stack](research/technical-stack-painel-estudio-do-criador-2026-11-21/research.md);
  - [`auditoria-e3-done-vs-ligado-2026-11-20.md`](../implementation-artifacts/auditoria-e3-done-vs-ligado-2026-11-20.md).

---

## 1. Resumo do problema

**Gatilho.** Em 2026-11-21 o dono decidiu fazer agora o **painel web final**, completo, em vez do painel pequeno da 6.3. As regras:
- o que funciona fica ligado;
- o que não funciona fica visível e travado, nunca com dado falso (A5);
- o backend decide o status de cada função.

O mapeamento (`bmad-brainstorming`, 110 ideias) mediu o que roda de verdade e achou três coisas.

1. **O banco faria o painel mentir.** Em leitura do `picorte.db`:
   - `score_chat/audio/visual` = 0.0 em 199/199 cortes (o zero finge medição);
   - `ypp_transform_score` = 0 e `phash_signature` vazio em todos; `risk_status` = `pending`;
   - `videos.source_id` = NULL em 12/12;
   - 12 vídeos e 199 cortes de projetos já apagados (só existem 6 pastas em `projects/`);
   - `publisher_policies` vazia;
   - o MCP `picorte_enfileirar_video` grava uma linha que ninguém consome.
2. **O painel atual não serve de base:**
   - ainda tem a marca chopify e textos em inglês;
   - o título do projeto é a URL;
   - o padrão é o modo determinístico (no qual nada do E3.5 roda);
   - o selo "199 cortes" é dado podre;
   - abrir o painel **escreve** em `project.json` (marca como `interrupted` o job de outra sessão).
3. **A 6.3 atual está desatualizada:**
   - pede celular (o dono decidiu: só desktop);
   - fixa o `DESIGN.md` antigo (o dono decidiu: não é restrição);
   - fixa 10 arquétipos (a 3.6.3 leva para 12);
   - não tem a página de Lives pedida pelo dono.

**Tipo:** requisito novo do dono + evidência medida (padrão "done no papel, desligado no pipeline" no banco).

**Decisões do dono nesta sessão:**
- painel **só PC** (Windows e Linux);
- banco **fica no SQLite**;
- **fila única** (B5);
- **página Lives** (Ao vivo / Em alta / Recentes) como candidata a página inicial;
- condições C1–C4 aceitas.

## 2. Análise de impacto

| Épico | Impacto |
|---|---|
| 1, 2, 3, 3.5, 4 | Sem rollback. Continuam `done`. Os gaps do banco (2.1, 4.5) são corrigidos na 6.4. |
| 3.6 | A 3.6.1 continua na outra sessão. A 3.6.2 a 3.6.6 vão para depois do painel. |
| 3.7 | Sem mudança de escopo. Continua depois do 3.6. |
| 5 | Continua pausado. A aba "Ao vivo" e o "Em alta" ficam travados até a 5.2 e a 5.1. |
| **6** | A 6.3 vira 6.3 a 6.8 (painel). A 6.1 e a 6.2 ficam como estão, depois do E5. |
| 7 | Sem mudança. O painel desenha as áreas travadas e já coleta 👍/👎. |

**Artefatos:**
- `epics.md`;
- `SPEC.md` (CAP-14 + Non-goals);
- `architecture.md` (AD-2, AD-8, AD-10, AD-11, convenção nova e Stack);
- `CLAUDE.md` e `AGENTS.md`;
- `sprint-status.yaml`;
- `docs/plano-mestre.md`;
- `deferred-work.md`.

Não há documento de UX ainda: o `EXPERIENCE.md` nasce no `bmad-ux`, antes da 6.3.

**Técnico:**
- **código novo:** `picorte/api/` (FastAPI), `picorte/web/` (SPA React), o serviço de capacidades em `picorte/services/`, a tabela de rótulos 👍/👎 e a ferramenta MCP `picorte_capacidades`;
- **código alterado:** `studio_service.py` (sync com `source_id`, sinais e veredito P1), `picorte/mcp/server.py` (fila única) e migração do banco;
- **o `dashboard.py`** é substituído.

## 3. Abordagem recomendada

**Ajuste direto.** As histórias novas ficam dentro do Épico 6. Esforço **alto** (6 histórias); risco **médio**, por dois motivos:
- a outra sessão segue mexendo no motor; a regra de convivência da Seção 4.2 controla isso;
- as APIs de terceiros da página Lives (cota e ToS).

**Custo** (regra 6): **R$ 0**. A stack é grátis; as APIs oficiais (YouTube Data API, Twitch Helix) ficam dentro da cota grátis. A GSAP tem licença proprietária grátis e revogável (Webflow) e fica isolada.

## 4. Propostas detalhadas (todas aprovadas)

### 4.1 `epics.md` — Épico 6: a 6.3 vira as histórias 6.3 a 6.8 (Proposta 1)

**Valem em todas:**
- condições C1–C4;
- não editar `score_clips.py`, `llm_router.py`, `benchmark.py`, `projects/` nem `benchmarks/`;
- o visual sai da direção escolhida com o impeccable (Operate).

**6.3 · Base do Estúdio: FastAPI, contrato de capacidades e casca da SPA**
1. O FastAPI substitui o `http.server` e porta: Range/206, token anti-CSRF, CSP, checagem Host/Origin, fila serial única e fallback de SPA. Abrir ou ler nunca escreve em `project.json`.
2. Lock por projeto entre processos (`filelock`): só vira "interrompido" o job cujo lock está livre (B9).
3. `GET /api/capacidades`:
   - cada função do mapa traz: status `ligado|parcial|travado`, `tipo_motivo` (`codigo|config|dado|temporario|escolha`), motivo, o que falta, fonte do dado, origem (épico/história/CAP), escopo (global/projeto/corte), `depende_de`, `verificado_em` e `ligou_em`;
   - sondas com cache: Ollama e modelo, `agy` (429), Claude CLI, `yt-dlp`, `node`, `demucs`, GPU/VRAM e disco;
   - a mesma função vira a ferramenta MCP `picorte_capacidades`.
4. `GET /api/taxonomia` (arquétipos, tiers, redes, modos de IA, presets): o front não fixa listas.
5. SSE `/api/eventos`: progresso dos jobs e mudanças de capacidade.
6. Teste de contrato A5: nenhum número sai para capacidade travada; sinal não medido sai `null`.
7. Casca React (stack da pesquisa) com navegação e os estados vazio, carregando, erro e travado desenhados.

**6.4 · Verdade no banco**
1. B1: `videos.source_id` gravado a partir do `source_gate`.
2. B2: notas por sinal medidas, `NULL` quando não medido; migração dos 0.0 existentes.
3. B3: `risk_status`, YPP e pHash persistidos a partir do veredito P1.
4. B4: banco × disco reconciliados; órfãos arquivados, sem perder o rastreio dos 2 publicados (P1).
5. B6: políticas de publisher sincronizadas no boot.
6. B5 (fila única): `picorte_enfileirar_video` cria o projeto real na fila do Estúdio.

**6.5 · Lives: a página inicial**
1. Abas **Ao vivo / Em alta / Recentes**:
   - **Recentes** lista os vídeos dos canais cadastrados pela API oficial (R$ 0, dentro da cota);
   - cache de thumbs e metadados de no máximo 30 dias (AD-9).
2. **Ao vivo** mostra quem está ao vivo quando houver credencial de app da Twitch configurada (grátis e revogável); sem ela, fica travada (`config`). Cortar a live ao vivo fica travado até a 5.2; **Em alta** fica travada até a 5.1. O backend escolhe a aba aberta por padrão.
3. Clicar num vídeo abre o modal de corte:
   - o portão P1 responde antes de enfileirar;
   - escolha do formato;
   - motor de IA com a disponibilidade real;
   - preview do enquadramento sobre uma imagem real do vídeo.
4. Faixa **"Na sua mesa"**: revisões, links pendentes (C2), jobs e falhas com o próximo passo.
5. O selo "AO VIVO" e os espectadores só aparecem com dado da API + `verificado_em`.

**6.6 · Fila e Revisão de cortes**
1. **Fila:** título real, streamer, jogo e estágio em PT-BR. Falha com ação (trocar motor e retomar, cadastrar fonte, retomar). O conjunto de prova fica separado.
2. **Revisão em 3 colunas:**
   - lista de cortes;
   - player + waveform (peaks no servidor) com ajuste de início e fim;
   - arquétipo, tier, títulos, motivo, sinais ("não medido" no lugar de zero) e veredito P1 por rede ("sem veredito — re-auditar" quando faltar).
3. 👍/👎 com motivo opcional (B10), sem ser obrigatório (C3); "Salvar como Exemplo Ouro".
4. **Filtros e ordem:** filtros vindos da taxonomia; ordem padrão por tier + sinais concordantes, não pela nota saturada.
5. **Extras:** atalhos de teclado; editor de transcrição e legenda recolhido; Caça Profunda e busca por pergunta.
6. **Motor padrão:** o último que funcionou; o determinístico exige escolha consciente, com aviso.

**6.7 · Fontes, Escudo, Saúde e Configurações**
1. **Fontes:**
   - cadastro e permissão com base + evidência (C1);
   - tentativas barradas;
   - políticas por jogo;
   - campanhas;
   - pausas com histórico;
   - dossiês.
2. **Escudo:** cooldowns com contagem regressiva; só o cooldown manual pode ser limpo (C1). Claim registrado à mão aciona a pausa; o monitor automático fica travado até a 6.2.
3. **Saúde (W9):**
   - matriz projeto × parte do motor, com o motivo de cada `na`/`failed`;
   - frase-resumo do projeto;
   - `confianca_projeto` travada até a 3.6.5.
4. **Benchmark:**
   - P@K por versão, contra o acaso e com o n de VODs;
   - aviso de amostra pequena;
   - progresso "x de 20 gabaritos" para a 3.6.6.
5. **Configurações:** motor de IA, preset de visão, marca e legendas, Modo Madrugada (parcial), custos (parcial, regra 6).

**6.8 · Publicação assistida e áreas que ainda não existem**
1. **Pacote do Dia:**
   - cartões por rede;
   - copiar em 1 clique e abrir a pasta;
   - cadência respeitada.
2. **Links publicados:**
   - colar a URL no cartão;
   - exportado sem link vira pendência em "Na sua mesa" (C2);
   - YouTube Longo aceito (B11).
3. **Áreas travadas desenhadas, com o que falta e o `depende_de`:** OAuth das 5 redes, publicação automática, claims automático, métricas 1h/24h/7d, Bandit, dataset e Radar. Os contadores que já são reais (👍/👎, publicações com link) aparecem.

### 4.2 Ordem e `sprint-status.yaml` (Proposta 2)

**Ordem:**
1. A 3.6.1 continua na outra sessão.
2. Pré-passo, sem virar história: `bmad-ux` (`EXPERIENCE.md`) + direção visual com o impeccable (o dono escolhe uma entre 2–3).
3. Painel: 6.3 → 6.4 → 6.5 → 6.6 → 6.7 → 6.8.
4. Depois: 3.6.2 → 3.6.6 → 3.7 → E5 → 6.1 e 6.2 → E7.

O `epic-6` vira `in-progress` quando a 6.3 começar.

**Regra de convivência:**
- as histórias do painel não editam `score_clips.py`, `llm_router.py`, `benchmark.py`, `projects/` nem `benchmarks/`;
- as histórias do motor não editam `picorte/api/`, `picorte/web/` nem o `studio_service.py`;
- se a 6.4 precisar de um campo novo do motor, isso vira um pedido para a sessão do motor.

**`sprint-status`:** a chave `6-3-painel-web-estudio-do-criador-desktop-e-celular-design-md` é trocada por (todas em `backlog`):
- `6-3-base-do-estudio-fastapi-contrato-de-capacidades-e-casca-da-spa`
- `6-4-verdade-no-banco-sinais-medidos-veredito-p1-fonte-e-reconciliacao`
- `6-5-lives-pagina-inicial-ao-vivo-em-alta-recentes-e-na-sua-mesa`
- `6-6-fila-e-revisao-de-cortes-player-waveform-sinais-e-rotulos`
- `6-7-fontes-escudo-saude-do-motor-benchmark-e-configuracoes`
- `6-8-publicacao-assistida-e-areas-travadas-oauth-claims-metricas-bandit-radar`

### 4.3 `SPEC.md` (Proposta 3)

**CAP-14, intent.**
- **Antes:** "…painel web responsivo "Estúdio do Criador" no desktop e no celular."
- **Depois:** "…painel web "Estúdio do Criador" no computador (Windows e Linux), que mostra cada função com o status real decidido pelo backend (ligado, parcial ou travado)."

**CAP-14, success.**
- **Antes:** "…pelo painel web nas resoluções desktop e mobile."
- **Depois:** "…disparo de cortes (inclusive a partir da vitrine de lives e vídeos recentes dos streamers cadastrados)… pelo painel web no desktop. Toda função ainda não pronta aparece travada com o que falta para destravar, e nenhuma tela exibe número de exemplo ou estimativa como se fosse dado real."

**Non-goals, novo item:** "**Sem layout de celular:** o painel roda local e é usado só no computador; não construir versão móvel nem responsividade para telas de celular."

### 4.4 `architecture.md` (Proposta 4)

- **AD-2:**
  - passa a "Banco Local Único como Fonte da Verdade (SQLite; PostgreSQL opcional)", com `picorte.db` via `picorte/db/connection.py` e Postgres 16 opcional por `DATABASE_URL`;
  - o diagrama e o título do ERD mudam junto;
  - datas em UTC ISO 8601 (`TIMESTAMPTZ` quando for Postgres).
- **Convenção nova "Travado nunca é falso" (2026-11-21):**
  - o status vem de `GET /api/capacidades` (`picorte/services/`) e o front nunca decide;
  - nenhum número para função travada; sinal não medido é `NULL`, nunca `0`;
  - ler nunca escreve estado;
  - um teste de contrato garante tudo isso.
- **AD-10:** a ferramenta MCP `picorte_capacidades` sai da mesma função; enfileirar pelo MCP usa a mesma função da fila do painel.
- **AD-11:** lock de projeto entre processos (`filelock`); "só PC" vale para Windows e Linux.
- **AD-8:** exportado sem URL publicada fica como pendência visível até o link ser colado.
- **Stack:**
  - SQLite 3 (padrão) · PostgreSQL 16 (opcional); `psycopg` opcional;
  - FastAPI 0.165 (SSE nativo);
  - Node 22; React 19.3, Vite 8.3, Tailwind 4.3, Base UI 1.9;
  - Motion 14 e GSAP 3.15 (isolado);
  - Video.js 10 e wavesurfer.js 8.1;
  - Recharts 3.11 e ECharts 6.1;
  - TanStack Query 5 e Zustand 5.

### 4.5 `CLAUDE.md` e `AGENTS.md` (Proposta 5; os dois arquivos iguais)

- **Linha 11:** "banco PostgreSQL local" → "banco local (SQLite, `picorte.db`; PostgreSQL opcional)".
- **Linha 15:** "banco Postgres" → "banco local".
- **Linha 19:** "painel web do nosso `DESIGN.md`" → "painel web "Estúdio do Criador" (só desktop, Windows e Linux), onde cada função aparece com o status real decidido pelo backend: o que não está pronto fica travado, nunca com dado falso".
- **Linha 61:** o `DESIGN.md`, o `PRODUCT.md` e o `design/` são a primeira versão e não são restrição; o impeccable lidera no modo Operate e substitui o `DESIGN.md` pela direção que o dono escolher.

**Fora desta proposta:** o exemplo do P4 nos pilares ("nosso banco Postgres") só muda pelo `cortes-pilares` Revisar.

### 4.6 `plano-mestre.md` e `deferred-work.md` (Proposta 6)

- **Plano mestre, Épico 6:**
  - objetivo só desktop, com status decidido pelo backend e sem o `DESIGN.md` antigo como restrição;
  - o item 4 vira a lista das histórias 6.3–6.8 + o pré-passo `bmad-ux`/direção visual;
  - critério de saída: painel aprovado no desktop (Windows e Linux), teste "travado nunca é falso" passando e todas as áreas do mapa presentes;
  - skills de apoio: impeccable (Operate) + skills do Emil + Playwright.
- **Plano mestre, linha do tempo:**
  - nota "⏩ 2026-11-21: painel (6.3–6.8) antes de terminar o 3.6 e o 5";
  - o Épico 4 passa a ✅;
  - o título do Épico 3.6 vira "⏳ em andamento (3.6.1); 3.6.2+ depois do painel".
- **Plano mestre, tabela de decisões:** nova linha de 2026-11-21 com as decisões desta proposta.
- **`deferred-work.md`:**
  - W9 absorvido pela 6.7;
  - W5 com nota para a 6.8 (projetos antigos mostrados como "rodar o prepare de novo");
  - W2 continua com a 6.1.

## 5. Handoff de implementação

- **Escopo:** Moderado.
- **Próximos passos:**
  1. Aplicar as edições da Seção 4 nos artefatos.
  2. `bmad-ux` → `EXPERIENCE.md` (páginas, fluxos e estados; a home é a vitrine de Lives com "Na sua mesa").
  3. **Direção visual com o impeccable (Operate):** 2–3 direções com dados reais; o dono escolhe; o `frontend-design` e as skills do Emil revisam; o Playwright valida; o `DESIGN.md` novo substitui o atual.
  4. **Implementação com o `superpowers`** (TDD), num branch separado, 6.3 → 6.8, com `bmad-code-review` ao fim do épico.
- **Pré-requisito prático:** registrar o Playwright MCP também no escopo `c:/Dev/projeto-cortes` (minúsculo) para a validação visual. Exige editar o `~/.claude.json`, então só com o ok do dono.
- **Critérios de sucesso:**
  - o teste de contrato A5 passando;
  - nenhum dado podre na tela (reconciliação B4 feita);
  - toda função do mapa presente, ligada ou travada com o que falta;
  - painel aprovado pelo dono no Windows e no Linux;
  - as condições C1–C4 verificadas.

## 6. Veredito dos pilares (`cortes-pilares`, Julgar)

| Pilar | Efeito | Motivo |
|---|---|---|
| P1 | reforça | Raio-X no cartão do corte, fontes barradas visíveis, B1/B3. Risco corrigido pela C1 (cooldown automático sem botão; liberar fonte exige base + evidência). |
| P2 | neutro | Mostra o kit por rede; Cold Open e Loop aparecem travados com honestidade. |
| P3 | reforça | 👍/👎, P@K por versão, sinais reais. Risco corrigido pela C2 (exportado sem link vira pendência). |
| P4 | reforça | Rótulos, gabarito e sinais no nosso banco. |
| P5 | neutro | Corrigido pela C3: a revisão e o 👍/👎 são opcionais. |
| A1 | neutro | A waveform só ajusta início e fim; não há timeline. |
| A2 | neutro | O Pacote do Dia respeita a cadência. |
| A3 | neutro | — |
| A4 | reforça | OAuth travado; publicação manual como plano B legítimo. |
| A5 | reforça forte | Contrato de capacidades + teste de contrato + limpeza do dado podre. |

**Condições aceitas:**
- **C1 (P1):** só o cooldown manual pode ser limpo; liberar fonte exige base + evidência.
- **C2 (P3):** exportado sem link vira pendência visível.
- **C3 (P5):** 👍/👎 opcional.
- **C4 (regra 7 / AD-11):** Windows e Linux.

Veredito final: **SEGUE**.
