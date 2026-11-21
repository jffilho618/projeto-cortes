---
title: 'Pesquisa técnica: stack do painel web "Estúdio do Criador"'
type: 'technical'
topic: 'stack de front-end e ferramentas de design para o painel web local do Picorte'
decision: 'escolher a stack de front-end e as skills/ferramentas de design para o painel final, único e moderno'
source: 'run (3 pesquisadores em paralelo + rodada 2 do líder)'
status: complete
preset: 'standard'
validation: 'normal'
created: '2026-11-21'
updated: '2026-11-21'
claims_verified: 4
claims_unverified: 7
---

# Pesquisa técnica: stack do painel web "Estúdio do Criador"

**Decisão:** escolher a stack de front-end e as skills de design para o painel final do Picorte. O painel é local, de uso próprio, e deve ser único, moderno, suave e profissional. A identidade visual atual (`DESIGN.md`) **não** é restrição, por decisão do dono em 2026-11-21.

## Resumo executivo

**Recomendação:**
- **Base e interface:** **React 19 + Vite 8 + Tailwind 4**, com componentes sem estilo próprio da **Base UI**, distribuídos pela CLI do **shadcn** e depois "ejetados" para código nosso.
- **Movimento:** **Motion**, **View Transitions** e transições **CSS no estilo transitions.dev**.
- **Peças do Picorte:** **Video.js v10** com **wavesurfer.js 8** para o vídeo e a marcação de corte; **Recharts 3** para gráficos (**ECharts 6** só onde houver muito dado).
- **Backend e tempo real:** **FastAPI** com **SSE nativo**, mais TanStack Query e Zustand.
- **Design:** a skill **impeccable em modo Operate** dá a direção visual. A **frontend-design** (já disponível) e as **skills do Emil Kowalski** cuidam do anti-genérico e do movimento. O **Playwright MCP** deixa o agente ver a tela e iterar.

**O que decide:**
1. **"Único" não vem da biblioteca, vem das decisões.** Todas as bases sem estilo estão vivas e com licença aberta [4][5][6]. O visual genérico nasce de aceitar os padrões: fonte sem escolha, raios e espaçamentos iguais, falta de telas de vazio e erro [8]. A ferramenta que ataca isso diretamente é o modo **Operate** do impeccable: o "mundo" visual empresta só tipo, paleta, densidade e **um movimento-assinatura**, e os controles continuam familiares [27].
2. **O ecossistema de agentes converge em React + Tailwind:** shadcn MCP [30], react-bits [11], Video.js React [19]. Há indício de que o agente gasta mais com Svelte recém-atualizado [16][36]. Isso não foi medido para React.
3. **Licenças:** o **GSAP** é grátis, mas proprietário e revogável pela Webflow [9]. Fica fora como base, porque o Motion (MIT) cobre o mesmo uso [10]. react-bits e Animate UI usam Commons Clause: servem para uso próprio, mas não são licenças OSI [11].

**Maior ressalva:** **ninguém mede "visual mais bonito"**. Não existe comparação independente entre skills de design nem entre bibliotecas de gráficos pela estética [F4, F5]. A recomendação de design se apoia no método (impeccable Operate, frontend-design), não em benchmark. Por isso o painel deve nascer com **2–3 direções visuais comparadas lado a lado** antes de construir.

## F1 — Base (framework, build, API)

- **React 19.3.1** [1], **Vite 8.3.8**, **Svelte 5.59 / SvelteKit 3.4** e **Solid 2.0.3** [2] estão todos ativos e são MIT.
- O **SvelteKit 3** (out/2026) e o **Solid 2.0** (nov/2026) trouxeram quebras de API recentes [2]. Os LLMs tendem a gerar código da versão antiga [36].
- Num teste com Claude Code, o SvelteKit custou US$ 4,28 contra cerca de US$ 2,7 dos três primeiros colocados, porque o agente voltava sempre à documentação. **O teste não mediu React** [16] (confiança média, n=5).
- **FastAPI 0.165** tem **SSE nativo** desde a 0.135: `EventSourceResponse`, ping de 15 s, `id`/`retry` [15]. Serve o build do Vite com `StaticFiles(html=True)`. A documentação **não cobre** o fallback de SPA nem Range/206 para pular no vídeo [17]: isso é trabalho nosso.
- **Tailwind 4.3.5** está ativo. Em set/2026 o Tailwind anunciou a entrada na Shopify, com impacto ainda desconhecido [18].

## F2 — Componentes e direção visual

- Desde **jul/2026, o shadcn usa Base UI como padrão**. O Radix continua suportado (`init -b radix`). A CLI v4 trouxe `preset`, `apply` e `eject` e os estilos Luma, Sera e Rhea [3].
- Na prática, o shadcn virou **distribuidor de código** (registry e eject), não um visual obrigatório [3].
- Bases sem estilo e ativas: **Base UI 1.9 (MIT)** [4], **React Aria 1.22 (Apache-2.0)** [5], **Ark UI 5.40 (MIT)** e **Radix 1.8 (MIT, ritmo mais lento)** [6].
- **Mantine** e **HeroUI** já vêm estilizados [7]: ruins para visual próprio.
- **Anti-genérico** [8]: uma fonte display com personalidade mais uma de texto; cor semântica; raio como hierarquia; densidade quebrada (o principal maior); telas de vazio, carregando e erro desenhadas; motion só onde tem função.
- **Tipografia livre e ativa:** Geist e Geist Mono (OFL), Mona Sans (OFL, GitHub) [35]. O Inter está com o repositório parado desde nov/2024 [35]. Paletas em **OKLCH** (o Tailwind 4 já usa) [18]. O Radix Colors está estável e parado desde 2023 [6].
- **Não pesquisado:** referências de painéis admirados (Linear, Vercel, Raycast) e galerias de inspiração.

## F3 — Movimento e microinterações

| Candidato | Licença | Saúde | Uso no painel |
|---|---|---|---|
| **Motion** 14.14 [10] | MIT | muito ativo | base do movimento em React (layout, presença, gestos) |
| **View Transitions API** [13] | padrão web | Chrome 111+, Firefox 144+, Safari 18+ (93%) | troca de telas e de estados; no painel local só importa o navegador do dono |
| **transitions.dev** [12] | uso pessoal e comercial permitido; CLI e agente MIT | ativo | **CSS puro com padrões de app** (modal, painel, badge, shake de erro, check de sucesso), com `prefers-reduced-motion` em cada um; o mais alinhado a painel |
| **AutoAnimate** 0.10 [14] | MIT | ativo | listas e filas (entrada, saída, reordenação) com zero configuração |
| **react-bits** [11] | MIT + Commons Clause | ativo | efeitos pontuais (texto, fundo); não é base |
| **GSAP** 3.15 [9] | proprietária, revogável | ativo | **incluído por decisão do dono (2026-11-21)** para animações complexas (timelines, SplitText); ressalva: licença não OSI e revogável pela Webflow, então o Motion continua como base e o GSAP fica isolado nos pontos que precisam dele |
| Rive / dotLottie [F3] | runtime MIT | ativos | ilustrações animadas (estado vazio, sucesso), se houver |

## F4 — Peças do Picorte

- **Player:** o **Video.js v10** está estável (GA) desde out/2026: uma reescrita que **substitui Vidstack, Media Chrome e Mux Player** [19]. `@videojs/react` 10.6.0 é Apache-2.0 [19]. A `TimeSlider` é componível, o que serve para a régua de corte. O Vidstack está só em manutenção de segurança [19] (confiança média).
- **Waveform e marcação de corte:** **wavesurfer.js 8.1** (BSD-3, ativo) [20]. As **Regions** ganharam auto-scroll, `minLength`/`maxLength` e `avoidOverlapping`, que é exatamente o ajuste de início e fim de corte.
- **Pendência crítica:** waveform de VODs de 4 a 11 h exige **peaks pré-calculados no backend**. Decodificar no navegador não é viável. Não verificado nesta rodada.
- **Gráficos:** **Recharts 3.11 (MIT)** e **ECharts 6.1 (Apache-2.0)** estão saudáveis [22]. **visx** está parado há ~5 meses, **Nivo** sem release há 18 meses e **Tremor** abandonado [22].
- **Peso** (tabela de um concorrente, a TanStack): Recharts ~100 kB, ECharts ~160 kB, visx 49 kB [21].
- **Nenhuma fonte avalia a estética dos gráficos.**
- **Tempo real:** **SSE do FastAPI** (a fila é de mão única, servidor para painel) [15] com **TanStack Query 5.108** e **Zustand 5.1** [23]. O padrão SSE com invalidação de cache não foi confirmado em fonte primária.

## F5 — Skills e ferramentas de IA para design (fichas da regra 9)

| Ferramenta | Faz | Origem / mantenedor | Licença / custo | O que executa | Veredito |
|---|---|---|---|---|---|
| **frontend-design** [28] | guia anti-genérico com processo plano → revisão → build → autocrítica | anthropics/skills · Anthropic | Apache-2.0 · grátis | **nada** (só texto) | **usar**: já está disponível na sessão |
| **impeccable** [26][27] | ~40 comandos (critique, audit, polish, typeset, animate…), detector de 62 regras de "slop" sem LLM, **modo Operate para telas de trabalho** | pbakaus/impeccable · Paul Bakaus | Apache-2.0 · grátis | **hooks** (a cada edição e no fim, no Claude e no Gemini); binário em `~/.impeccable/bin`; rede para impeccable.style; telemetria desligável; modo `live` pode chamar `claude`/`codex` **sem permissões** se não travado | **usar, com cuidado**: instalar sem hooks ou com `IMPECCABLE_LIVE_COPY_AGENT=chat` e telemetria off; pedir aprovação (regra 9) |
| **skills do Emil Kowalski** [29] | design engineering e animação: estados, timing, coreografia, auditoria de animações | emilkowalski/skills | MIT · grátis | **nada** (só `.md`) | **usar** para o "suave" |
| **Playwright MCP** [32] | dá ao agente um navegador para ver e testar a tela | microsoft/playwright-mcp · Microsoft | Apache-2.0 · grátis | processo Node local e navegador; rede livre por padrão | **usar** para iterar no visual |
| **shadcn MCP** [30] | o agente busca e instala componentes de registries | shadcn (Vercel) | MIT · grátis | `npx shadcn mcp` local; rede só para registries | opcional: vale se usarmos a CLI do shadcn |
| **taste-skill** [24] | direção de arte para **sites de empresa e landing** | Leonxlnx | MIT · grátis | ~10 scripts Node, Chrome headless, **Stop hook** e cópia de assets; instala via `npx skills` (telemetria on) [25] | **não usar**: alvo errado (landing, não painel) |
| **21st MCP** [31] | componentes e geração por IA | 21st.dev | serviço pago (US$ 6–60 por mês) | remoto com chave | **descartar** (regras 2 e 6) |
| **Chrome DevTools MCP** [33] | debug e performance no Chrome | Google | Apache-2.0 · grátis | estatísticas ligadas por padrão | alternativa ao Playwright, com `--no-usage-statistics` |
| **bmad-cis-design-thinking** | facilitação de design thinking (empatia, ideação) | BMAD (já instalada) | — | nada | opcional para mapear a experiência; não gera visual |

**Evidência de qualidade:** só vitrines dos autores e rankings de popularidade [34]. A Snyk aponta prompt injection em 36% das skills analisadas, sem metodologia no artigo [37]. Isso reforça a regra 9: preferir skills que são **só texto**.

## Insights que só a combinação mostra

1. **A escolha de React é ganho composto:** as skills e ferramentas de agente (shadcn MCP, react-bits, Video.js React, exemplos de Motion) e o indício de custo maior em Svelte apontam todos para o mesmo lado. A vantagem não é técnica do framework, é do ecossistema de agentes.
2. **O diferencial está na fase de direção, não na de componentes:** as bibliotecas são neutras. Quem decide se o painel fica "único" é o processo de design (Operate com movimento-assinatura, telas de vazio e erro, tipografia escolhida de propósito). Ou seja, o investimento vai para uma **fase de direção visual** antes de codar.
3. **Painel de trabalho tem pouca oferta de skills:** quase tudo mira landing page (taste-skill e muitas coleções). O impeccable Operate e o frontend-design (que trata dashboard como contraste) são as exceções achadas.
4. **O formato de VOD longo puxa requisitos de backend:** waveform de horas exige peaks no servidor e o seek de vídeo exige Range/206. São decisões de API (FastAPI), não de front.

## Matriz de decisão (re-pesável)

Notas de 1 a 5. Pesos: visual único 30%, suavidade 20%, saúde 15%, IA gera bem 15%, acessibilidade 10%, manutenção 10%. Acessibilidade entre bases sem estilo **não foi comparada**, então todas levam nota igual (4).

**Framework**

| Candidato | Visual | Suavidade | Saúde | IA | A11y | Manut. | **Total** |
|---|---|---|---|---|---|---|---|
| **React 19 + Vite** | 4 | 5 | 5 | 5 | 5 | 4 | **4,60** |
| Svelte 5 / SvelteKit 3 | 4 | 4 | 5 | 3 | 3 | 4 | 3,90 |
| Solid 2 | 4 | 3 | 4 | 2 | 3 | 3 | 3,30 |

**Base de componentes**

| Candidato | Visual | Suavidade | Saúde | IA | A11y | Manut. | **Total** |
|---|---|---|---|---|---|---|---|
| **Base UI via shadcn (eject)** | 5 | 4 | 5 | 5 | 4 | 4 | **4,60** |
| React Aria Components | 5 | 4 | 5 | 3 | 4 | 4 | 4,30 |
| Radix | 5 | 4 | 3 | 4 | 4 | 4 | 4,15 |
| Mantine | 2 | 4 | 5 | 4 | 4 | 5 | 3,65 |

**Escolha:** React + Base UI. **Segundo colocado:** React Aria. Ele vence se a acessibilidade virar prioridade máxima ou se a Base UI ficar mais lenta. **Argumento mais forte contra:** o mesmo caminho (shadcn + Tailwind) que deixa a IA produtiva é o que produz o "visual genérico" quando os padrões são aceitos [8]. A mitigação é a fase de direção visual e o `eject`. **Plano B barato:** isolar a camada visual em tokens CSS e componentes nossos, de modo que trocar a base sem estilo afete só os primitivos.

## Recomendações

1. **Stack** (alimenta a arquitetura do painel / história 6.3): React 19 + Vite 8 + Tailwind 4 + Base UI (via shadcn, ejetado) + Motion + View Transitions + CSS de transições; **GSAP** (decisão do dono, isolado em animações complexas); Video.js v10 + wavesurfer.js 8; Recharts 3 (ECharts onde houver volume); TanStack Query + Zustand; **FastAPI com SSE** no lugar do `http.server`. Confiança alta em versões e licenças; média no "IA gera melhor em React" [16].
2. **Processo de design antes do código:**
   - impeccable em modo **Operate** gera 2–3 direções (tipo, paleta, densidade, movimento-assinatura) com dados reais do Picorte;
   - o dono escolhe;
   - o frontend-design e as skills do Emil revisam;
   - o Playwright MCP valida a tela.

   Confiança média: método sem benchmark.
3. **Instalar com aprovação** (regra 9): impeccable (sem hooks automáticos ou com o modo `live` travado e telemetria off), skills do Emil (só texto) e Playwright MCP. **Não instalar** taste-skill nem 21st.
4. **"Travado é travado":** cada função do painel lê o próprio status de um endpoint de capacidades. Isso é uma condição de arquitetura, não um achado desta pesquisa: é a convenção "sinal só vale se medido".
5. **Backend do VOD longo:** peaks de waveform calculados no servidor, Range/206 e fallback de SPA no FastAPI.

## Perguntas em aberto

- **Acessibilidade comparada** entre Base UI, React Aria e Ark: ler as docs de a11y e auditorias.
- **Peso real** de cada lib (bundlephobia) e desempenho do Motion num painel denso.
- **Peaks pré-calculados** no wavesurfer para VODs de 4–11 h (formato, `audiowaveform`), e Range/206 no Starlette.
- **Benchmark de código gerado por LLM** com React incluído (não achado).
- **Referências de painéis** (Linear, Vercel, Raycast) e **tipografia em alta** além de Geist, Mona Sans e Inter.
- **Governança do Tailwind** após a entrada na Shopify.
- Licença do `vercel-labs/agent-skills` (`web-design-guidelines`) e conteúdo do UI/UX Pro Max.

## Fontes

| # | Achado | Publicador | Data pub. | Acessado | Confiança |
|---|---|---|---|---|---|
| [1] | React 19.3.1 MIT | [npm](https://registry.npmjs.org/react) | 2026-10-14 | 2026-11-21 | alta |
| [2] | Solid 2.0 estável com quebra de API; SvelteKit 3 | [AlternativeTo](https://alternativeto.net/news/2026/11/solid-2-0-reaches-stable-after-five-years-rebuilding-async-into-its-reactive-core/) | 2026-11 | 2026-11-21 | média |
| [3] | shadcn: Base UI como padrão, CLI v4, eject | [shadcn](https://ui.shadcn.com/docs/changelog/2026-07-base-ui-default) | 2026-07 | 2026-11-21 | alta |
| [4] | Base UI 1.9.0 MIT, ativo | [npm](https://registry.npmjs.org/@base-ui/react) | 2026-10-09 | 2026-11-21 | alta |
| [5] | React Aria Components 1.22.1 Apache-2.0 | [npm](https://registry.npmjs.org/react-aria-components) | 2026-10-09 | 2026-11-21 | alta |
| [6] | Radix 1.8.1; Radix Colors parado desde 2023 | [npm](https://registry.npmjs.org/radix-ui) | 2026-10-12 | 2026-11-21 | alta |
| [7] | Mantine 9.8 e HeroUI 3.2 já estilizados | [npm](https://registry.npmjs.org/@mantine/core) | 2026-11-20 | 2026-11-21 | alta |
| [8] | Sinais do visual "default de IA" e correções | [Kosta Canatselis](https://world.hey.com/kostac/spot-the-slop-a-ui-designer-s-guide-to-fixing-ai-defaults-4c448c9c) | 2026-07-23 | 2026-11-21 | média |
| [9] | Licença GSAP proprietária e revogável | [GSAP/Webflow](https://gsap.com/standard-license) | 2025-05-30 | 2026-11-21 | alta |
| [10] | Motion 14.14.0 MIT | [npm](https://registry.npmjs.org/motion) | 2026-11-13 | 2026-11-21 | alta |
| [11] | react-bits: MIT + Commons Clause | [GitHub](https://github.com/DavidHDev/react-bits) | 2026-11-19 | 2026-11-21 | alta |
| [12] | transitions.dev: CSS puro, padrões de app | [README](https://cdn.jsdelivr.net/gh/jakubantalik/transitions.dev@main/README.md) | 2026-11-19 | 2026-11-21 | alta |
| [13] | Suporte a View Transitions | [caniuse](https://caniuse.com/view-transitions) | contínuo | 2026-11-21 | alta |
| [14] | AutoAnimate 0.10.2 MIT | [npm](https://registry.npmjs.org/@formkit/auto-animate) | 2026-11-06 | 2026-11-21 | alta |
| [15] | SSE nativo no FastAPI | [FastAPI docs](https://fastapi.tiangolo.com/tutorial/server-sent-events/) | 0.135+ | 2026-11-21 | alta |
| [16] | Custo de agente por stack (SvelteKit mais caro) | [The Register](https://www.theregister.com/a/5307249) | 2026-11-03 | 2026-11-21 | média |
| [17] | StaticFiles sem fallback de SPA nem Range | [Starlette](https://starlette.dev/staticfiles/) | s.d. | 2026-11-21 | alta |
| [18] | Tailwind 4.3; entrada na Shopify | [Tailwind blog](https://tailwindcss.com/blog) | 2026-09-09 | 2026-11-21 | alta |
| [19] | Video.js v10 GA; @videojs/react 10.6.0 | [Mux](https://www.mux.com/blog/video-js-v10-is-ready-for-your-mux-videos) · [npm](https://registry.npmjs.org/@videojs/react) | 2026-11-18 / 2026-11-20 | 2026-11-21 | alta |
| [20] | wavesurfer.js 8 (Regions, Timeline) | [GitHub releases](https://github.com/katspaugh/wavesurfer.js/releases) | 2026-09-23 | 2026-11-21 | alta |
| [21] | Peso das libs de gráficos | [TanStack](https://tanstack.com/charts/latest/docs/framework/react/comparison) | 2026 | 2026-11-21 | média |
| [22] | Recharts, ECharts, visx, Nivo, Tremor: versões e saúde | [npm](https://registry.npmjs.org/recharts) | 2026-11-17 | 2026-11-21 | alta |
| [23] | TanStack Query 5.108, Zustand 5.1 | [npm](https://registry.npmjs.org/@tanstack/react-query) | 2026-11-20 | 2026-11-21 | alta |
| [24] | taste-skill: foco em sites de empresa; Stop hook | [GitHub](https://github.com/Leonxlnx/taste-skill) | 2026-11-07 | 2026-11-21 | alta |
| [25] | `npx skills` (Vercel): telemetria ligada | [GitHub](https://github.com/vercel-labs/skills) | 2026-11-16 | 2026-11-21 | alta |
| [26] | impeccable: hooks, binário, modo live | [GitHub](https://github.com/pbakaus/impeccable) | 2026-11-18 | 2026-11-21 | alta |
| [27] | impeccable: modo Operate | [mode-operate.md](https://github.com/pbakaus/impeccable/blob/main/.agent/skills/impeccable/reference/mode-operate.md) | 2026-11 | 2026-11-21 | alta |
| [28] | frontend-design (Anthropic) | [GitHub](https://github.com/anthropics/skills/tree/main/skills/frontend-design) | 2026-09-03 | 2026-11-21 | alta |
| [29] | skills do Emil Kowalski, só texto | [GitHub](https://github.com/emilkowalski/skills) | 2026-11-15 | 2026-11-21 | alta |
| [30] | shadcn MCP | [shadcn](https://ui.shadcn.com/docs/mcp) | s.d. | 2026-11-21 | média |
| [31] | 21st: preços | [21st.dev](https://21st.dev/pricing) | s.d. | 2026-11-21 | média |
| [32] | Playwright MCP | [GitHub](https://github.com/microsoft/playwright-mcp) | 2026-11-18 | 2026-11-21 | alta |
| [33] | Chrome DevTools MCP: estatísticas ligadas | [GitHub](https://github.com/ChromeDevTools/chrome-devtools-mcp) | 2026-11-20 | 2026-11-21 | alta |
| [34] | Ranking de skills de design (popularidade) | [claudemarketplaces](https://claudemarketplaces.com/best/skills/design-ui) | 2026-11-21 | 2026-11-21 | média |
| [35] | Geist, Geist Mono, Mona Sans (OFL); Inter parado | [GitHub](https://github.com/github/mona-sans) | 2026-11-13 | 2026-11-21 | alta |
| [36] | LLMs geram Svelte desatualizado | [svelte-evals](https://sveltethemes.dev/nkwib/svelte-evals) | s.d. | 2026-11-21 | média |
| [37] | ToxicSkills: 36% com prompt injection | [Snyk](https://snyk.io/articles/top-claude-skills-ui-ux-engineers/) | 2026-03-02 | 2026-11-21 | baixa |

## Mapa de validade

Calculado pelo `recon_kit.py staleness` a partir do ledger. Janelas: versão e licença, 1 mês; ecossistema, 6 meses; panorama de IA, 3 meses; padrão, 24 meses.

| Afirmação | Classe | Reconferir até |
|---|---|---|
| Video.js v10, wavesurfer 8, View Transitions, impeccable (hooks e modo live) | versão | **2026-12-01** (a mais próxima) |
| shadcn com Base UI como padrão; licença do GSAP | versão | **reconferir antes de instalar**: a página-fonte é antiga, embora tenha sido lida hoje |
| custo de agente por stack; foco da taste-skill | panorama | 2027-02 |
| Commons Clause (react-bits) | ecossistema | 2027-05 |
| SSE no FastAPI; modo Operate | padrão | 2028-11 |

**Reconferir primeiro em 2026-12-01.** O `Refresh` do bmad-deep-recon faz isso. Uma pesquisa de seleção com mais de dois trimestres deve ser refeita antes de virar decisão.
