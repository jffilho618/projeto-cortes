# Handoff — Sessão 04 → Sessão do Painel Web "Estúdio do Criador" (Épico 6)

**Data:** 2026-11-21 · **De:** sessão da história 3.6.1 (Claude Code) · **Para:** a nova sessão (Claude Code ou Gemini/Antigravity)
**Missão da nova sessão:** mapear tudo o que o Picorte já faz e o que ainda vai fazer, e criar o **painel web final completo**: único, profissional, moderno, suave, com cada componente pensado para a melhor experiência. O que funciona fica ligado. O que não funciona fica visível e travado.

---

## 1. Contexto em 1 minuto

- **Picorte** (repo `projeto-cortes`) é uma máquina **local e de uso próprio** de cortes de lives e VODs de games para Shorts, YouTube Longo, TikTok, Reels e Facebook. Primeiro canal: **Bomba Clips**. **Não é SaaS:** nada de multi-tenant, billing, onboarding de clientes nem landing page.
- **Ambiente:** Windows 11 (RTX 4060 Ti 8 GB) e Linux (notebook). Python global, sem `.venv`. Node 22 e npm 10 instalados. Todo código precisa funcionar nos dois sistemas (AD-11: `pathlib`, `filelock`).
- **Regras do `CLAUDE.md` que pesam aqui:**
  - conversar em PT-BR;
  - nunca commitar, dar push ou apagar sem pedido explícito;
  - nada de ferramenta paga;
  - redes só por OAuth;
  - toda etapa com custo tem estimativa antes;
  - skill de terceiros só com aprovação (regra 9).
- **Pilares** em `_bmad-output/planning-artifacts/pilares.md` (`P1 > P2 > P3 > P4 > P5` e `A1`–`A5`). O **A5** (nada de estimativa disfarçada de dado real) é a base da política de travas.
- **Quem lidera:** mapeamento e especificação com o **BMAD**; visual com o **impeccable** (e as demais skills de design abaixo); implementação com o **superpowers** (TDD).

## 2. A visão do painel (decisões do dono, 2026-11-21)

1. **Painel final, não protótipo.** O objetivo é a UI definitiva do Picorte, com todas as áreas do produto: fila, revisão de cortes, fontes e permissões (P1), escudo anti-strike, saúde do motor, benchmark, publicação, campanhas, métricas e aprendizado. A meta é acertar o máximo possível agora, sabendo que não sai 100%.
2. **Ligado × travado:**
   - **o que já funciona no backend fica ligado** ao front;
   - **o que não funciona** (OAuth das 5 redes, publicação automática, monitor de claims, métricas 1h/24h/7d, Bandit e o que mais estiver no papel) aparece **travado** e pronto, para ligar depois sem refazer a tela.
   - Exemplo do dono: "não vou ligar OAuth nas redes agora; deixamos tudo preparado e ligamos ao front depois".
3. **Travado é travado, nunca falso.** Esta condição é inegociável (pilar A5):
   - nenhum número de exemplo, gráfico de mentira ou botão que finge funcionar;
   - o travado aparece com cadeado ou em cinza, com uma linha dizendo o que falta para destravar;
   - foi o padrão "done no papel, desligado no pipeline" que machucou o projeto no E3 e no E4.
4. **Quem decide o que está travado é o backend.** Um endpoint único (ex.: `GET /api/capacidades`) devolve o status calculado de cada função: `ligado` / `parcial` / `travado` + motivo + o que falta. Exemplos:
   - OAuth: sem token, travado;
   - Sismógrafo: sem chat medido, aviso;
   - benchmark: sem gabarito, vazio.

   O painel **destrava sozinho** quando o backend ficar pronto. Isso segue a convenção da arquitetura **"sinal só vale se medido"** (`picorte/engine/health.py` → `engine_health.json`).
5. **Visual único, fora do padrão genérico.** O `DESIGN.md`, os tokens e a pasta `design/` de hoje **NÃO são restrição**. O dono não está satisfeito com eles. Se surgir direção melhor (cores, tipografia, identidade), ela substitui a atual.
6. **A tela não fixa listas que ainda vão mudar.** O Épico 3.6 vai mexer em:
   - arquétipos (10 → 12: `nobada_vacilo`, `mico_constrangimento`);
   - a regra do tier ouro (2 sinais);
   - a nota `confianca_projeto`;
   - a nota `standalone`.

   O painel lê essas listas dos dados.

## 3. Stack escolhida (pesquisa `bmad-deep-recon`, 37 fontes)

Relatório completo, com matriz de decisão e fichas: `_bmad-output/planning-artifacts/research/technical-stack-painel-estudio-do-criador-2026-11-21/research.md`.

| Camada | Escolha (versão e licença) | Observação |
|---|---|---|
| Base | **React 19.3 + Vite 8.3 + Tailwind 4.3** (MIT) | ecossistema de agentes forte; o SvelteKit custou mais a agentes em teste público |
| Componentes | **Base UI 1.9** (MIT), via **shadcn CLI v4** e depois `eject` para virar código nosso | sem visual imposto. Segunda opção: React Aria (Apache-2.0) |
| Movimento | **Motion 14** (MIT, base) + **View Transitions** (93% dos navegadores) + **transitions.dev** (CSS com padrões de app) + **AutoAnimate** (listas) | |
| Movimento complexo | **GSAP 3.15**: incluído por decisão do dono | licença proprietária, grátis e revogável pela Webflow; isolar nos pontos que precisam (timelines, SplitText) |
| Efeitos pontuais | **react-bits** (MIT + Commons Clause) | só em pontos isolados, nunca como base |
| Vídeo e corte | **Video.js v10** (`@videojs/react` 10.6, Apache-2.0) + **wavesurfer.js 8.1** (BSD-3, Regions para início e fim) | o v10 substitui Vidstack e Media Chrome |
| Gráficos | **Recharts 3.11** (MIT); **ECharts 6.1** (Apache-2.0) onde houver muito dado | visx e Nivo parados; Tremor abandonado |
| Dados no front | **TanStack Query 5** + **Zustand 5** | |
| Backend | **FastAPI 0.165 com SSE nativo** no lugar do `http.server` do `dashboard.py` | |
| Tipografia candidata | Geist e Geist Mono, Mona Sans (OFL, ativas) | a decidir na direção visual; o Inter está parado |

**Pendências técnicas já conhecidas:**
- peaks da waveform calculados no servidor (há VODs de 4 a 11 h);
- Range/206 no FastAPI para o seek do vídeo;
- fallback de SPA (o `StaticFiles` não faz).

## 4. Ferramentas de design instaladas (regra 9 cumprida; aprovadas pelo dono)

Ficam em `.claude/skills/`. O Antigravity lê a mesma pasta via `.agents/skills.json`.

| Ferramenta | Como usar | Cuidados |
|---|---|---|
| **impeccable** 4.10 (Paul Bakaus, Apache-2.0) | **líder do visual.** Usar o **modo Operate**: o estilo entra só com **tipo, paleta, densidade e um movimento-assinatura**; layout, navegação e controles continuam familiares. Comandos úteis: `critique`, `audit`, `polish`, `typeset`, `animate`, `harden`, `visualize` | instalado **sem hooks**; telemetria off (`.impeccable/config.json`); modo live travado (`IMPECCABLE_LIVE_COPY_AGENT=chat`, variável de usuário). O lançador baixa um binário para `~/.impeccable/bin` no primeiro uso (aprovado) |
| **Skills do Emil Kowalski** (MIT, só texto) | para o "suave": `emil-design-eng`, `animate`, `choreograph`, `gestures`, `review-animations`, `improve-animations`, `find-animation-opportunities`, `remove-animations`, `animation-performance`, `animation-vocabulary`, `break-ui`, `pick-ui-library`, `learn-taste`, `prototype` | nenhum |
| **Playwright MCP** (Microsoft, escopo local) | o agente abre e vê a tela no navegador para iterar no visual e testar | só aparece numa sessão nova |
| **frontend-design** (Anthropic, `example-skills:frontend-design`) | guia anti-genérico (plano de tokens → revisão → build → autocrítica) | só texto |
| **taste-skill** (`design-taste-frontend` 2.5.1, Leonxlnx, MIT) | instalada a pedido do dono, **mesmo sem uso previsto**. Foco: sites de empresa e landing | **não usar no painel sem pedido explícito**: a descrição dela se oferece para qualquer projeto React/Tailwind e pode disputar com o impeccable. Roda scripts Node e Chrome headless e acessa Google Fonts, Wikimedia e jsDelivr. Está fora do git (`.git/info/exclude`, 39 MB) |
| **bmad-cis-design-thinking** | opcional, para mapear a experiência (empatia, jornada) | não gera visual |
| **Descartados** | 21st.dev (pago, regras 2 e 6) e Figma MCP (pede seat pago; não usamos Figma) | |

**Diretrizes anti-genérico achadas na pesquisa:**
- uma fonte display com personalidade mais uma de texto;
- cor semântica (tokens pela função);
- raio como hierarquia;
- densidade quebrada (o principal maior);
- **telas de vazio, carregando, erro e travado desenhadas**;
- motion só onde tem função;
- revelação progressiva.

O "visual de IA" vem de aceitar os padrões.

## 5. O mapeamento (primeira tarefa da sessão)

**Objetivo:** um inventário do Picorte inteiro que vira o mapa do painel. Para cada função:
- tela e área;
- **status real** (`ligado` / `parcial` / `travado`), medido pelo que roda de verdade e não pelo "done" do papel;
- o que falta para destravar;
- de onde vem o dado (arquivo, banco, endpoint);
- épico e história de origem.

**Fontes para cruzar:**
- `_bmad-output/specs/spec-picorte/SPEC.md`: capacidades CAP-x (o que o produto deve fazer).
- `_bmad-output/planning-artifacts/epics.md` e `_bmad-output/implementation-artifacts/sprint-status.yaml`. Status em 2026-11-21:
  - E1, E2, E3, E3.5 e E4 `done`;
  - **E3.6 `in-progress`** (3.6.1 em andamento);
  - E3.7, E5, E6 e E7 `backlog`.
- `_bmad-output/implementation-artifacts/auditoria-e3-done-vs-ligado-2026-11-20.md` (o padrão "done mas desligado") e `deferred-work.md` (pendências W-x).
- `_bmad-output/planning-artifacts/architecture.md` e `visao.md`.
- **O que roda de fato:**
  - `engine_health.json` de cada projeto;
  - `picorte.db` (tabelas: `sources`, `videos`, `clips`, `publications`, `metrics_snapshots`, `claims_events`, `bandit_state`, `dataset_samples`…);
  - o servidor MCP `picorte_mcp`;
  - o `dashboard.py` atual (`http.server`, fila serial; ver com o Playwright).
- **Dados novos da 3.6.1:**
  - `benchmarks/<data>.json` (Precision@K por VOD contra o acaso);
  - `benchmarks/gabaritos/`;
  - `benchmarks/conjunto.json` (o conjunto de prova).

**O que o painel já tem dado real para mostrar:**
- fila e projetos;
- cortes com arquétipo, tier, título e motivo;
- saúde do motor por sinal;
- Precision@K do motor;
- fontes e permissões P1 (cadastro de streamers em `assets/streamers/registry.json`);
- verdict do escudo P1 (Selo Verde, YPP, música).

**Travado hoje:**
- OAuth e publicação nas 5 redes;
- monitor de claims (6.2);
- métricas 1h/24h/7d e Bandit (E7);
- radar e monitor de lives (E5).

Confirmar tudo no mapeamento.

**Novidades pedidas para o painel** (nota de 2026-11-21 na história 6.3):
- painel "Saúde do motor" (W9);
- `confianca_projeto` (vem na 3.6.5);
- **botões 👍/👎 por corte**, que viram rótulo para a 3.6.6 e o E7.

## 6. Ordem de trabalho sugerida

1. **`bmad-brainstorming`** → o mapeamento da seção 5. Usar o Playwright MCP para abrir o painel atual.
2. **`cortes-pilares` (Julgar)** sobre a mudança de ordem (painel completo antes de terminar o E3.6 e o E5). A expectativa é SEGUE, se a condição "travado nunca é falso" estiver escrita.
3. **`bmad-correct-course`** para ampliar a história 6.3 ("painel final completo com travas + endpoint de capacidades") e, se preciso, quebrar em várias histórias. Depois o **`bmad-ux`** (`EXPERIENCE.md`: telas, fluxos e estados).
4. **Direção visual:** o **impeccable (Operate)** gera **2–3 direções** com dados reais do Picorte. Cada uma tem tipo, paleta, densidade e um movimento-assinatura. Sugestão a explorar, não decidida: o "sismógrafo do chat" ou a "curva do mais repetido" como assinatura.
   - O dono escolhe.
   - O `frontend-design` e as skills do Emil revisam.
   - O Playwright valida.
   - O `DESIGN.md` novo substitui o atual.
5. **Implementação** pelo **superpowers** (TDD), num **branch separado**: FastAPI + endpoint de capacidades + SPA React. Espelhos raiz ↔ `picorte/engine/` só valem para `score_clips`, `projects`, `ingest`, `render_clips`, `chopify` e `download_and_transcribe`. O `dashboard.py` já diverge e vai ser substituído.

## 7. O que está acontecendo na outra sessão (não mexer)

- A sessão da 3.6.1 continua cuidando da **fila do conjunto de prova** (lives do BisteconeLive) e do **baseline final de Precision@K**.
- **Não mexa** em `projects/`, `benchmarks/`, `picorte/engine/benchmark.py`, `picorte/ai/llm_router.py` nem nos projetos em processamento.
- **Contexto da 3.6.1 útil para o painel:**
  - a cota do Gemini acabou (429, volta em ~4 dias), por isso o conjunto de prova usa o **Qwen local** (`qwen3.5:9b` via Ollama, instalado em 2026-11-21);
  - o YouTube bloqueou o IP como robô uma vez (resolvido reiniciando o modem);
  - o motor hoje acerta ~2× a 4× o acaso no top 5/10 (1–2 VODs; ainda não é confiável).
- **Commit:** a 3.6.1 (código, testes, benchmarks, pesquisa e skills) foi commitada em 2026-11-21 a pedido do dono. A nova sessão começa limpa.
