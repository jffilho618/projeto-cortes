# 6.3-B — Casca do Estúdio (SPA React) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar a casca do painel "Estúdio do Criador" em React (história 6.3, AC 7): navegação pela sidebar autorretrátil com o estado do sistema no pé e os estados vazio, carregando, erro e travado desenhados, tudo lendo o backend 6.3-A, sem nenhum dado falso.

**Architecture:** Projeto Vite em `picorte/web/`, com build em `picorte/web/dist/`, que o FastAPI da 6.3-A já serve com fallback de SPA (`DIST_PADRAO`). O front lê `GET /api/capacidades` e `GET /api/projetos` com TanStack Query e assina `/api/eventos` (SSE) para invalidar o cache e acompanhar o progresso numa loja Zustand. Cada área do mapa vira uma rota. Até a sua história chegar, a página da área mostra um poço "chega na história X" e a lista real das funções dela, com o status medido pelo backend.

**Tech Stack:**
- React 19.3.1, react-router 8.5.2, Vite 8.3.8, Tailwind 4.3.5 (`@tailwindcss/vite`), Base UI 1.9.0 (`@base-ui/react`), TanStack Query 5.108.2, Zustand 5.1.0, TypeScript 6.0.3;
- testes: Vitest 5.1.1, Testing Library (react 16.3.3, dom 10.4.2, jest-dom 8.0.0) e jsdom 31.0.1;
- verificação visual: playwright-core 1.65.1 com o Edge (`channel: "msedge"`).

**Spec:**
- `_bmad-output/planning-artifacts/epics.md`, Story 6.3, AC 7;
- `_bmad-output/planning-artifacts/ux-designs/ux-projeto-cortes-2026-11-21/EXPERIENCE.md`: IA, Sidebar, Contrato de Travas, Component Patterns › Global, State Patterns, Interaction Primitives, Accessibility, Responsive;
- `DESIGN.md` (raiz): tokens, sidebar, poço travado e botões;
- protótipos em `design/estudio/` (`estudio.css` e `fonte/comum.html`);
- stack em `_bmad-output/planning-artifacts/research/technical-stack-painel-estudio-do-criador-2026-11-21/research.md`.

## Global Constraints

- **Não editar** `projects/`, `benchmarks/`, `score_clips.py`, `picorte/ai/llm_router.py` nem `benchmark.py`: outra sessão está cuidando deles.
- **Não commitar** (pedido do dono, 2026-11-22). O passo "Commit" de cada tarefa vira "sem commit".
- **"Travado nunca é falso":** o front nunca decide se uma função funciona. O status vem de `/api/capacidades`. Capacidade que faltar ou não puder ser lida aparece como **"Indisponível agora · não consegui ler o status"**, **nunca como ligada por padrão**. Função travada não mostra número, gráfico nem exemplo.
- **Vocabulário fixo:** Ligado · Parcial · Travado · Indisponível agora · Desligado por você.
- **Status nunca só por cor:** sempre ícone + palavra.
- **CSP do backend** (`default-src 'self'; style-src 'self'; script-src 'self'`):
  - nada de `<script>` ou `<style>` inline nem atributo `style=""` no HTML;
  - nada de `data:` em imagem (`assetsInlineLimit: 0`).

  Estilos dinâmicos só via a prop `style` do React (CSSOM), que a CSP permite.
- **Windows e Linux (C4):** caminhos com `node:url`/`pathlib` e scripts npm sem comandos de shell.
- **Só desktop:** abaixo de 1280 px aparece "Use uma janela maior."
- **Interface em PT-BR**, com numerais tabulares em contagens e tempos.
- **Estado do tema:** `data-theme` em `<html>` e `localStorage["picorte-tema"]`, a mesma chave dos protótipos.

## Fora deste plano (fica para as histórias seguintes)

- Conteúdo real de cada página (Lives, Sala, Fila, Revisão…): 6.5–6.8.
- Marcador **Novo** por `ligou_em` (Contrato, regra 4): 6.5, junto com a faixa "Na sua mesa".
- Contagens de Revisão e Publicação na sidebar: vêm do endpoint da faixa "Na sua mesa" (6.5). **Nesta casca só a Fila tem contagem**, porque é a única com dado real hoje: projetos `queued`/`running`.
- Paleta de comandos (`Ctrl+K`) e lista de atalhos (`?`): ficam para depois.
- Motion e GSAP: a casca usa só transição CSS (o "colar a figurinha" entra quando houver card).
- **CLI do shadcn:** não é usada. Os componentes já nascem nossos, que é o efeito do `eject`; o Base UI entra direto como primitivo.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `picorte/web/package.json`, `package-lock.json` | Dependências fixas e scripts `dev`, `build`, `test`, `check`. |
| `picorte/web/vite.config.ts` | Build em `dist/`, proxy `/api` e `/media` para a 8770, `fs.allow` da raiz do repo (fontes e logo) e configuração do Vitest. |
| `picorte/web/tsconfig.json` | TypeScript estrito, só `src/`. |
| `picorte/web/index.html` | Raiz `#raiz` e o script externo de tema. |
| `picorte/web/public/tema-inicial.js` | Aplica o tema salvo antes do React, sem script inline. |
| `picorte/web/public/favicon.svg` | Cópia de `design/brand/picorte-icone.svg`. |
| `picorte/web/LEIAME.md` | Como rodar, testar e construir. |
| `picorte/web/src/main.tsx` | QueryClient, roteador e montagem. |
| `picorte/web/src/estilos/tokens.css` | Fontes Onest e tokens dos dois temas (cópia fiel de `design/estudio/estudio.css`). |
| `picorte/web/src/estilos/app.css` | Tailwind 4, `@theme` com os nossos tokens e as classes de componente portadas dos protótipos. |
| `picorte/web/src/api/tipos.ts` | Tipos do contrato (Capacidade, ListaCapacidades, Projeto, Progresso). |
| `picorte/web/src/api/cliente.ts` | `pedir<T>()` e `ErroApi` (`desligado`, `http`, `formato`). |
| `picorte/web/src/api/capacidades.ts` | `useCapacidades`, `rotuloDoStatus`, `capacidadePorId` (ilegível, nunca ligado), `capacidadesDaArea`, `areaTravada`. |
| `picorte/web/src/api/projetos.ts` | `useProjetos`, `contarNaFila`, `projetoRodando`. |
| `picorte/web/src/tempo-real/loja.ts` | Zustand: conexão SSE e progresso por projeto. |
| `picorte/web/src/tempo-real/eventos.ts` | `ligarEventos(fonte, invalidar)` e `useEventos()`. |
| `picorte/web/src/ui/tempo.ts` | `verificadoHa(iso, agora)`. |
| `picorte/web/src/ui/Icone.tsx` | Ícones de linha (os traços do sprite dos protótipos). |
| `picorte/web/src/ui/StatusRotulo.tsx` | Ícone + palavra do vocabulário fixo. |
| `picorte/web/src/ui/PocoTravado.tsx` | Contrato de Travas (codigo, config, dado, temporario, escolha). |
| `picorte/web/src/ui/Estados.tsx` | `Carregando`, `Vazio`, `ErroCarregar` (Base UI Collapsible), `PicorteDesligado`, `detectarPlataforma`. |
| `picorte/web/src/casca/areas.ts` | As 10 áreas: rota, rótulo, ícone, tecla do `g`, áreas de capacidade e história. |
| `picorte/web/src/casca/tema.ts` | `temaAtual`, `alternarTema`. |
| `picorte/web/src/casca/useSidebar.ts` | Abertura com intenção (150 ms para abrir, 120 ms para fechar), foco, alfinete lembrado e empurrar só a partir de 1920 px. |
| `picorte/web/src/casca/atalhos.ts` | `g` + letra (até 1 s), `[` para fixar; nada dispara dentro de campo de texto. |
| `picorte/web/src/casca/EstadoSistema.tsx` | Pé da sidebar: GPU com anel real, Ollama, Gemini, Claude, tempo real e alerta de ambiente. |
| `picorte/web/src/casca/Sidebar.tsx` | Itens, contagem da Fila, cadeado de área travada, tema, alfinete e Configurações. |
| `picorte/web/src/casca/Casca.tsx` | Layout, eventos, atalhos, "Picorte desligado" e "janela pequena". |
| `picorte/web/src/paginas/PaginaArea.tsx` | Poço "chega na história X" e lista real das funções da área nos 4 estados. |
| `picorte/web/src/paginas/NaoEncontrada.tsx` | Rota desconhecida. |
| `picorte/web/src/rotas.tsx` | `ROTAS` (usadas pelo browser router e pelos testes). |
| `picorte/web/src/testes/preparar.ts` | jest-dom, limpeza, stubs de `matchMedia`, `ResizeObserver`, `getAnimations` e `EventSource`. |
| `picorte/web/src/testes/fonte-falsa.ts` | `FonteFalsa`, o EventSource de teste. |
| `picorte/web/src/testes/fabrica.ts` | `cap()`, `lista()`, `LISTA_PADRAO`, `renderizar()`. |
| `.gitignore` | `+ picorte/web/dist/`. |

---

### Task 1: Esqueleto do projeto web, tokens e primeira unidade (`verificadoHa`)

**Files:**
- Create: `picorte/web/package.json`
- Create: `picorte/web/vite.config.ts`
- Create: `picorte/web/tsconfig.json`
- Create: `picorte/web/index.html`
- Create: `picorte/web/public/tema-inicial.js`
- Create: `picorte/web/public/favicon.svg` (cópia de `design/brand/picorte-icone.svg`)
- Create: `picorte/web/LEIAME.md`
- Create: `picorte/web/src/main.tsx` (provisório; a Task 7 substitui)
- Create: `picorte/web/src/estilos/tokens.css`
- Create: `picorte/web/src/estilos/app.css`
- Create: `picorte/web/src/testes/preparar.ts`
- Create: `picorte/web/src/testes/fonte-falsa.ts`
- Create: `picorte/web/src/ui/tempo.ts`
- Test: `picorte/web/src/ui/tempo.test.ts`
- Modify: `.gitignore` (acrescentar `picorte/web/dist/`)

**Interfaces:**
- Produces: `verificadoHa(iso: string | null, agora?: Date): string`; `FonteFalsa` (classe com `url`, `fechada`, `close()`, `static ultimas: FonteFalsa[]`, herda `EventTarget`); classes CSS de `app.css` usadas pelas tarefas seguintes: `app`, `side`, `marca`, `marca-nome`, `it`, `rot`, `cont`, `cad`, `sep`, `sist`, `sl`, `anel`, `mk ok|av|trav`, `tema`, `principal`, `pagina`, `cabeca`, `secao`, `linhas`, `linha`, `pocos`, `espaco`, `tt`, `estado`, `falta`, `depende`, `pilula`, `pilula sec`, `esqueleto`, `vazio`, `erro-carregar`, `detalhe`, `link-fraco`, `comando`, `desligado`, `janela-pequena`, `sr`, `num`, `ic`, `ic-p`.

- [ ] **Step 1: Criar `package.json`**

```json
{
  "name": "picorte-estudio",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run",
    "check": "tsc --noEmit -p tsconfig.json"
  },
  "dependencies": {
    "@base-ui/react": "1.9.0",
    "@tanstack/react-query": "5.108.2",
    "react": "19.3.1",
    "react-dom": "19.3.1",
    "react-router": "8.5.2",
    "zustand": "5.1.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "4.3.5",
    "@testing-library/dom": "10.4.2",
    "@testing-library/jest-dom": "8.0.0",
    "@testing-library/react": "16.3.3",
    "@types/react": "19.3.0",
    "@types/react-dom": "19.3.0",
    "@vitejs/plugin-react": "6.3.0",
    "jsdom": "31.0.1",
    "tailwindcss": "4.3.5",
    "typescript": "6.0.3",
    "vite": "8.3.8",
    "vitest": "5.1.1"
  }
}
```

- [ ] **Step 2: Criar `vite.config.ts`, `tsconfig.json`, `index.html` e `public/`**

`picorte/web/vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const raizRepo = fileURLToPath(new URL("../..", import.meta.url));
const backend = "http://127.0.0.1:8770";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsInlineLimit: 0, // a CSP do backend não aceita data: em imagem nem fonte
    modulePreload: { polyfill: false }, // sem script inline
  },
  server: {
    port: 5173,
    strictPort: true,
    fs: { allow: [raizRepo] }, // assets/fonts e design/brand ficam fora de picorte/web
    proxy: {
      "/api": { target: backend, changeOrigin: true },
      "/media": { target: backend, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/testes/preparar.ts"],
    css: false,
  },
});
```

`picorte/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "types": ["vite/client"]
  },
  "include": ["src"]
}
```

`picorte/web/index.html`:

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Picorte · Estúdio do Criador</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <script src="/tema-inicial.js"></script>
  </head>
  <body>
    <div id="raiz"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`picorte/web/public/tema-inicial.js`:

```js
// Aplica o tema salvo antes do React montar (arquivo externo: a CSP não aceita script inline).
(function () {
  try {
    var tema = localStorage.getItem("picorte-tema");
    if (tema === "light" || tema === "dark") document.documentElement.setAttribute("data-theme", tema);
  } catch (e) {
    /* navegador sem armazenamento: fica o tema do sistema */
  }
})();
```

Copie o ícone: `cp design/brand/picorte-icone.svg picorte/web/public/favicon.svg`.

- [ ] **Step 3: Criar `tokens.css` e `app.css`**

`picorte/web/src/estilos/tokens.css`: copie de `design/estudio/estudio.css`:
- os dois `@font-face` (com `src` trocado para `url("../../../../assets/fonts/onest-latin-ext.woff2")` e `url("../../../../assets/fonts/onest-latin.woff2")`);
- os três blocos de tokens (`:root`, `@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){…}}` e `:root[data-theme="light"]{…}`), sem mudar nenhum valor.

Nada além disso nesse arquivo.

`picorte/web/src/estilos/app.css`:

```css
@import "tailwindcss";
@import "./tokens.css";

/* Só os nossos tokens: nada da paleta, dos raios nem das fontes padrão do Tailwind. */
@theme inline {
  --color-*: initial;
  --color-transparent: transparent;
  --color-current: currentColor;
  --color-fundo: var(--fundo);
  --color-folha: var(--folha);
  --color-folha-2: var(--folha-2);
  --color-poco: var(--poco);
  --color-fio: var(--fio);
  --color-fio-forte: var(--fio-forte);
  --color-tinta: var(--tinta);
  --color-tinta-2: var(--tinta-2);
  --color-tinta-3: var(--tinta-3);
  --color-marca: var(--marca);
  --color-acao: var(--acao);
  --color-acao-hover: var(--acao-hover);
  --color-acao-tinta: var(--acao-tinta);
  --color-acao-texto: var(--acao-texto);
  --color-selecao: var(--selecao);
  --color-capsula: var(--capsula);
  --color-capsula-tinta: var(--capsula-tinta);
  --color-alerta-fundo: var(--alerta-fundo);
  --color-ok: var(--ok);
  --color-aviso: var(--aviso);
  --color-barrado: var(--barrado);
  --radius-*: initial;
  --radius-raio: var(--raio);
  --radius-p: var(--raio-p);
  --radius-ctrl: var(--raio-ctrl);
  --radius-rotulo: 5px;
  --radius-pilula: var(--pilula);
  --font-sans: Onest, system-ui, -apple-system, "Segoe UI Variable", sans-serif;
}

@layer base {
  html { font: 14px/1.45 var(--font-sans); background: var(--fundo); color: var(--tinta); -webkit-font-smoothing: antialiased; }
  body { min-height: 100vh; background: var(--fundo); }
  ::selection { background: var(--selecao); }
  :focus-visible { outline: 3px solid var(--foco); outline-offset: 1px; border-radius: 7px; }
  * { scrollbar-width: thin; scrollbar-color: var(--fio-forte) transparent; }
  kbd { font: inherit; font-size: 11.5px; font-weight: 600; padding: 0 5px; border-radius: 5px; background: var(--capsula); color: var(--capsula-tinta); }
}

@layer components {
  .num { font-variant-numeric: tabular-nums; }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .ic { width: 18px; height: 18px; flex: none; stroke: currentColor; stroke-width: 1.6; fill: none; stroke-linecap: round; stroke-linejoin: round; }
  .ic-p { width: 13px; height: 13px; }

  /* ---------- casca ---------- */
  .app { display: grid; grid-template-columns: 72px minmax(0, 1fr); min-height: 100vh; }
  .app[data-empurra="true"] { grid-template-columns: 264px minmax(0, 1fr); }
  .principal { grid-column: 2; padding: 20px 32px 40px; display: flex; flex-direction: column; gap: 18px; min-width: 0; }

  .side { position: fixed; inset: 0 auto 0 0; width: 72px; z-index: 20; background: var(--trilho);
    -webkit-backdrop-filter: blur(30px) saturate(180%); backdrop-filter: blur(30px) saturate(180%);
    border-right: .5px solid var(--fio-forte); display: flex; flex-direction: column; padding: 12px 8px; gap: 1px; overflow: hidden;
    transition: width .2s cubic-bezier(.2, .8, .2, 1), box-shadow .2s; }
  .side[data-aberta="true"] { width: 264px; box-shadow: var(--sombra); }
  .app[data-empurra="true"] .side { box-shadow: none; }
  .side .rot, .side .marca-nome { opacity: 0; transition: opacity .15s; }
  .side[data-aberta="true"] :is(.rot, .marca-nome) { opacity: 1; }
  .side .marca { display: flex; align-items: center; gap: 11px; padding: 2px 10px 14px; white-space: nowrap; }
  .side .marca img { width: 34px; height: 34px; border-radius: var(--raio-p); }
  .side .marca-nome { font-weight: 650; font-size: 15px; }
  .it { position: relative; display: flex; align-items: center; gap: 12px; height: 36px; padding: 0 16px; border-radius: 8px; color: var(--tinta-2); white-space: nowrap; font-weight: 500; }
  .it .ic { color: var(--tinta-3); }
  .it:hover { background: var(--capsula); }
  .it[aria-current="page"] { background: var(--selecao); color: var(--tinta); }
  .it[aria-current="page"] .ic { color: var(--marca); }
  .it .cont { position: absolute; left: 33px; top: 3px; min-width: 17px; height: 17px; padding: 0 5px; border-radius: var(--pilula); background: var(--capsula); color: var(--capsula-tinta); font-size: 11px; font-weight: 600; display: grid; place-items: center; font-variant-numeric: tabular-nums; }
  .it .cad { position: absolute; left: 32px; top: 19px; width: 11px; height: 11px; color: var(--tinta-3); }
  .side[data-aberta="true"] .it .cont { left: auto; right: 10px; top: 9px; }
  .side[data-aberta="true"] .it .cad { left: auto; right: 12px; top: 12px; }
  .side .sep { height: .5px; background: var(--fio-forte); margin: 8px 10px; }
  .sist { margin-top: auto; display: flex; flex-direction: column; gap: 1px; }
  .sl { display: flex; align-items: center; gap: 12px; height: 28px; padding: 0 18px; border-radius: 8px; color: var(--tinta-3); white-space: nowrap; font-size: 12.5px; }
  a.sl:hover { background: var(--capsula); }
  .sl b { font-weight: 600; color: var(--tinta-2); }
  .anel { width: 18px; height: 18px; border-radius: 50%; flex: none; background: conic-gradient(var(--marca) var(--p, 0%), var(--fio-forte) 0); display: grid; place-items: center; }
  .anel::after { content: ""; width: 12px; height: 12px; border-radius: 50%; background: var(--fundo); }
  .mk { width: 18px; height: 18px; flex: none; display: grid; place-items: center; }
  .mk.ok { color: var(--ok); }
  .mk.av { color: var(--aviso); }
  .mk.trav { color: var(--tinta-3); }
  .tema { display: flex; align-items: center; gap: 12px; height: 32px; padding: 0 18px; border-radius: var(--raio-ctrl); color: var(--tinta-3); white-space: nowrap; }
  .tema:hover { color: var(--tinta); background: var(--capsula); }

  /* ---------- páginas ---------- */
  .pagina { display: flex; flex-direction: column; gap: 18px; max-width: 1400px; }
  .cabeca h1 { font-size: 23px; font-weight: 650; line-height: 1.2; letter-spacing: -.015em; }
  .secao { font-size: 13px; font-weight: 600; color: var(--tinta-3); }
  .linhas { list-style: none; padding: 0; background: var(--folha); border-radius: var(--raio); box-shadow: 0 0 0 .5px var(--fio), 0 1px 2px rgba(0, 0, 0, .06); }
  .linha { display: grid; grid-template-columns: minmax(220px, 1.2fr) 190px minmax(0, 2fr) 150px; align-items: center; gap: 16px; min-height: 44px; padding: 8px 18px; }
  .linha + .linha { border-top: .5px solid var(--fio); }
  .pocos { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 18px; }

  /* ---------- estados ---------- */
  .espaco { border-radius: var(--raio); padding: 18px 20px; display: flex; flex-direction: column; gap: 5px; color: var(--tinta-2); background: var(--poco); box-shadow: inset 0 0 0 .5px var(--fio); }
  .espaco .tt { display: flex; align-items: center; gap: 7px; color: var(--tinta); font-weight: 600; font-size: 17px; }
  .espaco .tt .ic { width: 14px; height: 14px; color: var(--tinta-3); }
  .espaco .falta { font-size: 13.5px; }
  .espaco .depende { font-size: 12.5px; color: var(--tinta-3); }
  .espaco .pilula { align-self: flex-start; margin-top: 8px; height: 30px; }
  .pilula { display: inline-flex; align-items: center; gap: 7px; height: 34px; padding: 0 16px; border-radius: var(--raio-ctrl); background: var(--acao); color: var(--acao-tinta); font-weight: 600; box-shadow: inset 0 .5px 0 rgba(255, 255, 255, .22), 0 1px 2px rgba(0, 0, 0, .2); transition: background .15s; }
  .pilula:hover { background: var(--acao-hover); }
  .pilula.sec { background: var(--folha); color: var(--tinta); box-shadow: 0 0 0 .5px var(--fio-forte), 0 1px 1px rgba(0, 0, 0, .08); }
  .pilula.sec:hover { background: var(--folha-2); }
  .esqueleto { background: var(--capsula); border-radius: var(--raio-ctrl); animation: pulsar 1.6s ease-in-out infinite; }
  .vazio { padding: 18px 20px; color: var(--tinta-2); display: flex; flex-direction: column; gap: 10px; }
  .erro-carregar { display: flex; flex-direction: column; gap: 10px; padding: 18px 20px; background: var(--folha); border-radius: var(--raio); box-shadow: 0 0 0 .5px var(--fio), 0 1px 2px rgba(0, 0, 0, .06); }
  .detalhe { white-space: pre-wrap; font-size: 12.5px; color: var(--tinta-3); background: var(--poco); padding: 10px 12px; border-radius: var(--raio-ctrl); max-height: 240px; overflow: auto; }
  .link-fraco { color: var(--acao-texto); font-weight: 500; align-self: flex-start; }
  .comando { font-size: 15px; padding: 10px 14px; background: var(--folha-2); border-radius: var(--raio-ctrl); color: var(--tinta); align-self: flex-start; }
  .desligado { max-width: 640px; gap: 10px; }
  .desligado h1 { font-size: 23px; font-weight: 650; line-height: 1.2; color: var(--tinta); }

  /* só desktop */
  .janela-pequena { display: none; }
  @media (max-width: 1279px) {
    .app { display: none; }
    .janela-pequena { display: grid; place-items: center; min-height: 100vh; padding: 32px; color: var(--tinta-2); font-size: 15px; }
  }
}

@keyframes pulsar { 50% { opacity: .55; } }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
```

- [ ] **Step 4: Criar o `main.tsx` provisório, a preparação dos testes e o `.gitignore`**

`picorte/web/src/main.tsx` (provisório; a Task 7 substitui):

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./estilos/app.css";

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <p className="principal">Picorte</p>
  </StrictMode>,
);
```

`picorte/web/src/testes/fonte-falsa.ts`:

```ts
/** EventSource de teste: os testes disparam eventos com dispatchEvent(new MessageEvent(...)). */
export class FonteFalsa extends EventTarget {
  static ultimas: FonteFalsa[] = [];
  url: string;
  fechada = false;

  constructor(url: string) {
    super();
    this.url = url;
    FonteFalsa.ultimas.push(this);
  }

  close(): void {
    this.fechada = true;
  }

  emitir(tipo: string, dados: unknown = {}): void {
    this.dispatchEvent(new MessageEvent(tipo, { data: JSON.stringify(dados) }));
  }
}
```

`picorte/web/src/testes/preparar.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { FonteFalsa } from "./fonte-falsa";

afterEach(() => {
  cleanup();
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  FonteFalsa.ultimas = [];
});

// O jsdom não tem estas APIs do navegador.
if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (consulta: string) => ({
      matches: false, media: consulta, onchange: null,
      addEventListener: () => {}, removeEventListener: () => {},
      addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    }),
  });
}
if (!("ResizeObserver" in window)) {
  (window as unknown as { ResizeObserver: unknown }).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
if (!Element.prototype.getAnimations) {
  Element.prototype.getAnimations = () => [];
}
(globalThis as unknown as { EventSource: unknown }).EventSource = FonteFalsa;
```

No `.gitignore` da raiz, logo depois de `node_modules/`, acrescente:

```
picorte/web/dist/
```

`picorte/web/LEIAME.md`:

````markdown
# Estúdio do Criador (front)

React + Vite + Tailwind. O backend é o FastAPI de `picorte/api/` (`python estudio.py`, porta 8770), que serve o build de `dist/`.

```
npm --prefix picorte/web install      # uma vez
npm --prefix picorte/web run build    # gera picorte/web/dist (o estudio.py serve)
npm --prefix picorte/web test         # testes (Vitest)
npm --prefix picorte/web run check    # tipos
npm --prefix picorte/web run dev      # desenvolvimento em http://127.0.0.1:5173, com o estudio.py rodando
```

Regra: o front nunca decide se uma função funciona. O status vem de `GET /api/capacidades`; o que não puder ser lido aparece "Indisponível agora", nunca ligado.
````

- [ ] **Step 5: Escrever o teste de `verificadoHa` (falhando)**

`picorte/web/src/ui/tempo.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { verificadoHa } from "./tempo";

const AGORA = new Date("2026-11-22T12:00:00Z");

describe("verificadoHa", () => {
  it("sem data ou com data ilegível", () => {
    expect(verificadoHa(null, AGORA)).toBe("nunca verificado");
    expect(verificadoHa("ontem", AGORA)).toBe("nunca verificado");
  });
  it("menos de um minuto", () => {
    expect(verificadoHa("2026-11-22T11:59:30Z", AGORA)).toBe("verificado agora");
  });
  it("minutos e horas", () => {
    expect(verificadoHa("2026-11-22T11:55:00+00:00", AGORA)).toBe("verificado há 5 min");
    expect(verificadoHa("2026-11-22T09:00:00Z", AGORA)).toBe("verificado há 3 h");
  });
  it("dias, inclusive a data sem hora do catálogo", () => {
    expect(verificadoHa("2026-11-21", AGORA)).toBe("verificado há 1 dia");
    expect(verificadoHa("2026-11-19T12:00:00Z", AGORA)).toBe("verificado há 3 dias");
  });
});
```

- [ ] **Step 6: Instalar e ver falhar**

Run: `npm --prefix picorte/web install` e depois `npm --prefix picorte/web test`
Expected: FAIL (`Failed to resolve import "./tempo"`).

- [ ] **Step 7: Implementar `tempo.ts`**

`picorte/web/src/ui/tempo.ts`:

```ts
/** "verificado há X" (Contrato de Travas, regra 5). */
export function verificadoHa(iso: string | null, agora: Date = new Date()): string {
  if (!iso) return "nunca verificado";
  const quando = new Date(iso);
  if (Number.isNaN(quando.getTime())) return "nunca verificado";
  const segundos = Math.max(0, Math.round((agora.getTime() - quando.getTime()) / 1000));
  if (segundos < 60) return "verificado agora";
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) return `verificado há ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `verificado há ${horas} h`;
  const dias = Math.floor(horas / 24);
  return `verificado há ${dias} ${dias === 1 ? "dia" : "dias"}`;
}
```

- [ ] **Step 8: Rodar testes, tipos e build**

Run: `npm --prefix picorte/web test`, `npm --prefix picorte/web run check` e `npm --prefix picorte/web run build`
Expected:
- 4 testes passando;
- `check` sem erros;
- `picorte/web/dist/index.html` gerado, com `/assets/*.js` e `/assets/*.css`;
- em `dist/assets`, os `.woff2` da Onest como arquivos próprios, não `data:`.

Confira que o `index.html` gerado não tem `<script>` sem `src`: `grep -c "<script>" picorte/web/dist/index.html` deve dar `0`.

- [ ] **Step 9: Sem commit** (pedido do dono).

---

### Task 2: Cliente da API, tipos e regras de capacidade

**Files:**
- Create: `picorte/web/src/api/tipos.ts`
- Create: `picorte/web/src/api/cliente.ts`
- Create: `picorte/web/src/api/capacidades.ts`
- Create: `picorte/web/src/api/projetos.ts`
- Test: `picorte/web/src/api/cliente.test.ts`
- Test: `picorte/web/src/api/capacidades.test.ts`

**Interfaces:**
- Consumes: nada das tarefas anteriores.
- Produces:
  - `pedir<T>(caminho: string, init?: RequestInit): Promise<T>`;
  - `class ErroApi extends Error { tipo: "desligado" | "http" | "formato"; detalhe: string; status: number }`;
  - tipos `Status`, `TipoMotivo`, `Capacidade`, `ListaCapacidades`, `Progresso`, `Projeto`;
  - `CHAVE_CAPACIDADES`, `PRAZO_CAPACIDADES_MS`, `useCapacidades()`;
  - `type Rotulo`, `rotuloDoStatus(c)`, `ilegivel(id)`;
  - `capacidadePorId(lista | undefined, id): Capacidade`, `capacidadesDaArea(lista | undefined, areas): Capacidade[]`, `areaTravada(caps): boolean`;
  - `CHAVE_PROJETOS`, `useProjetos()`, `contarNaFila(projetos?)`, `projetoRodando(projetos?)`.

- [ ] **Step 1: Criar os tipos**

`picorte/web/src/api/tipos.ts`:

```ts
/** Contrato do backend 6.3-A (picorte/capacidades/modelo.py e picorte/services/fila.py). */
export type Status = "ligado" | "parcial" | "travado";
export type TipoMotivo = "codigo" | "config" | "dado" | "temporario" | "escolha";

export interface Capacidade {
  id: string;
  area: string;
  titulo: string;
  status: Status;
  tipo_motivo: TipoMotivo | null;
  motivo: string;
  falta: string[];
  fonte_dado: string;
  origem: { epico: string | null; historia: string | null; cap: string | null };
  escopo: "global" | "projeto" | "corte";
  depende_de: string[];
  verificado_em: string | null;
  ligou_em: string | null;
  dados: Record<string, unknown> | null;
}

export interface ListaCapacidades {
  gerado_em: string;
  capacidades: Capacidade[];
  resumo: Record<Status, number>;
}

export interface Progresso {
  stage?: string;
  done?: number;
  total?: number;
  detail?: string;
}

export interface Projeto {
  id: string;
  status: string;
  stage?: string | null;
  progress?: Progresso | null;
  error?: string | null;
  na_fila?: boolean;
  created?: number;
}
```

- [ ] **Step 2: Escrever os testes (falhando)**

`picorte/web/src/api/cliente.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { pedir } from "./cliente";

function responder(status: number, corpo: string) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(corpo, { status })));
}

afterEach(() => vi.unstubAllGlobals());

describe("pedir", () => {
  it("devolve o JSON", async () => {
    responder(200, '{"ok":1}');
    await expect(pedir("/api/x")).resolves.toEqual({ ok: 1 });
  });
  it("usa a mensagem {erro} do backend", async () => {
    responder(409, '{"erro":"Este projeto já está na fila ou rodando."}');
    await expect(pedir("/api/x")).rejects.toMatchObject({
      tipo: "http", status: 409, message: "Este projeto já está na fila ou rodando.",
    });
  });
  it("falha de rede vira 'desligado'", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(pedir("/api/x")).rejects.toMatchObject({ tipo: "desligado" });
  });
  it("proxy sem backend (502) também vira 'desligado'", async () => {
    responder(502, "");
    await expect(pedir("/api/x")).rejects.toMatchObject({ tipo: "desligado" });
  });
  it("corpo ilegível vira 'formato'", async () => {
    responder(200, "<html>");
    await expect(pedir("/api/x")).rejects.toMatchObject({ tipo: "formato" });
  });
});
```

`picorte/web/src/api/capacidades.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { cap, lista } from "../testes/fabrica";
import { areaTravada, capacidadePorId, capacidadesDaArea, rotuloDoStatus } from "./capacidades";
import { contarNaFila, projetoRodando } from "./projetos";

describe("rotuloDoStatus (vocabulário fixo)", () => {
  it("ligado vence qualquer tipo", () => {
    expect(rotuloDoStatus({ status: "ligado", tipo_motivo: "escolha" })).toBe("Ligado");
  });
  it("temporario e escolha qualificam o motivo", () => {
    expect(rotuloDoStatus({ status: "parcial", tipo_motivo: "temporario" })).toBe("Indisponível agora");
    expect(rotuloDoStatus({ status: "travado", tipo_motivo: "escolha" })).toBe("Desligado por você");
  });
  it("parcial e travado", () => {
    expect(rotuloDoStatus({ status: "parcial", tipo_motivo: "config" })).toBe("Parcial");
    expect(rotuloDoStatus({ status: "travado", tipo_motivo: "codigo" })).toBe("Travado");
  });
});

describe("capacidadePorId (regra 6: ilegível nunca é ligado)", () => {
  it("acha a capacidade", () => {
    expect(capacidadePorId(lista([cap({ id: "SIS-6" })]), "SIS-6").status).toBe("ligado");
  });
  it("sem lista ou sem o id: Indisponível agora", () => {
    for (const c of [capacidadePorId(undefined, "SIS-6"), capacidadePorId(lista([]), "SIS-6")]) {
      expect(rotuloDoStatus(c)).toBe("Indisponível agora");
      expect(c.motivo).toBe("não consegui ler o status");
      expect(c.dados).toBeNull();
    }
  });
});

describe("áreas", () => {
  const l = lista([
    cap({ id: "MET-1", area: "metricas", status: "travado", tipo_motivo: "codigo" }),
    cap({ id: "MET-2", area: "metricas", status: "travado", tipo_motivo: "dado" }),
    cap({ id: "SAU-1", area: "saude" }),
    cap({ id: "SIS-1", area: "sistema" }),
  ]);
  it("filtra por uma ou mais áreas", () => {
    expect(capacidadesDaArea(l, ["saude", "sistema"]).map((c) => c.id)).toEqual(["SAU-1", "SIS-1"]);
    expect(capacidadesDaArea(undefined, ["saude"])).toEqual([]);
  });
  it("área travada só quando todas as funções estão travadas", () => {
    expect(areaTravada(capacidadesDaArea(l, ["metricas"]))).toBe(true);
    expect(areaTravada(capacidadesDaArea(l, ["saude"]))).toBe(false);
    expect(areaTravada([])).toBe(false);
  });
});

describe("projetos", () => {
  const projetos = [
    { id: "a", status: "running", progress: { done: 4, total: 17 } },
    { id: "b", status: "queued" },
    { id: "c", status: "complete" },
    { id: "d", status: "interrupted" },
  ];
  it("conta só o que está na fila ou rodando", () => {
    expect(contarNaFila(projetos)).toBe(2);
    expect(contarNaFila(undefined)).toBe(0);
  });
  it("acha o job rodando", () => {
    expect(projetoRodando(projetos)?.id).toBe("a");
    expect(projetoRodando([])).toBeUndefined();
  });
});
```

E a fábrica de dados de teste, `picorte/web/src/testes/fabrica.ts` (a parte de `renderizar` entra na Task 3):

```ts
import type { Capacidade, ListaCapacidades } from "../api/tipos";

export function cap(p: Partial<Capacidade> & Pick<Capacidade, "id">): Capacidade {
  return {
    area: "sistema", titulo: p.id, status: "ligado", tipo_motivo: null, motivo: "", falta: [],
    fonte_dado: "teste", origem: { epico: "6", historia: "6.3", cap: null }, escopo: "global",
    depende_de: [], verificado_em: "2026-11-22T11:00:00+00:00", ligou_em: null, dados: null,
    ...p,
  };
}

export function lista(capacidades: Capacidade[]): ListaCapacidades {
  const resumo = { ligado: 0, parcial: 0, travado: 0 };
  for (const c of capacidades) resumo[c.status] += 1;
  return { gerado_em: "2026-11-22T12:00:00+00:00", capacidades, resumo };
}
```

- [ ] **Step 3: Ver falhar**

Run: `npm --prefix picorte/web test`
Expected: FAIL (imports `./cliente`, `./capacidades` e `./projetos` não resolvem).

- [ ] **Step 4: Implementar**

`picorte/web/src/api/cliente.ts`:

```ts
export type TipoErro = "desligado" | "http" | "formato";

export class ErroApi extends Error {
  tipo: TipoErro;
  detalhe: string;
  status: number;

  constructor(tipo: TipoErro, mensagem: string, detalhe = "", status = 0) {
    super(mensagem);
    this.name = "ErroApi";
    this.tipo = tipo;
    this.detalhe = detalhe;
    this.status = status;
  }
}

const SEM_BACKEND = new Set([502, 503, 504]); // o proxy do Vite responde assim quando o estudio.py está parado

export async function pedir<T>(caminho: string, init?: RequestInit): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(caminho, { ...init, headers: { Accept: "application/json", ...init?.headers } });
  } catch (erro) {
    throw new ErroApi("desligado", "O Picorte não está rodando neste computador.", String(erro));
  }
  const texto = await resposta.text();
  if (SEM_BACKEND.has(resposta.status)) {
    throw new ErroApi("desligado", "O Picorte não está rodando neste computador.", texto.slice(0, 2000), resposta.status);
  }
  let corpo: unknown = null;
  try {
    corpo = texto ? JSON.parse(texto) : null;
  } catch {
    corpo = null;
  }
  if (!resposta.ok) {
    const mensagem = (corpo as { erro?: string } | null)?.erro ?? `O servidor respondeu ${resposta.status}.`;
    throw new ErroApi("http", mensagem, texto.slice(0, 2000), resposta.status);
  }
  if (corpo === null) {
    throw new ErroApi("formato", "A resposta do servidor veio vazia ou ilegível.", texto.slice(0, 2000), resposta.status);
  }
  return corpo as T;
}
```

`picorte/web/src/api/capacidades.ts`:

```ts
import { useQuery } from "@tanstack/react-query";
import { pedir } from "./cliente";
import type { Capacidade, ListaCapacidades } from "./tipos";

export const CHAVE_CAPACIDADES = ["capacidades"] as const;
export const PRAZO_CAPACIDADES_MS = 2 * 60 * 1000; // EXPERIENCE.md, Contrato regra 5 (valor inicial)

export function useCapacidades() {
  return useQuery({
    queryKey: CHAVE_CAPACIDADES,
    queryFn: () => pedir<ListaCapacidades>("/api/capacidades"),
    staleTime: PRAZO_CAPACIDADES_MS,
    refetchInterval: PRAZO_CAPACIDADES_MS,
  });
}

export type Rotulo = "Ligado" | "Parcial" | "Travado" | "Indisponível agora" | "Desligado por você";

export function rotuloDoStatus(c: Pick<Capacidade, "status" | "tipo_motivo">): Rotulo {
  if (c.status === "ligado") return "Ligado";
  if (c.tipo_motivo === "temporario") return "Indisponível agora";
  if (c.tipo_motivo === "escolha") return "Desligado por você";
  return c.status === "parcial" ? "Parcial" : "Travado";
}

/** Contrato, regra 6: status ilegível nunca vira ligado. */
export function ilegivel(id: string): Capacidade {
  return {
    id, area: "", titulo: id, status: "travado", tipo_motivo: "temporario",
    motivo: "não consegui ler o status", falta: [], fonte_dado: "/api/capacidades",
    origem: { epico: null, historia: null, cap: null }, escopo: "global", depende_de: [],
    verificado_em: null, ligou_em: null, dados: null,
  };
}

export function capacidadePorId(lista: ListaCapacidades | undefined, id: string): Capacidade {
  return lista?.capacidades.find((c) => c.id === id) ?? ilegivel(id);
}

export function capacidadesDaArea(lista: ListaCapacidades | undefined, areas: readonly string[]): Capacidade[] {
  return lista ? lista.capacidades.filter((c) => areas.includes(c.area)) : [];
}

export function areaTravada(caps: Capacidade[]): boolean {
  return caps.length > 0 && caps.every((c) => c.status === "travado");
}
```

`picorte/web/src/api/projetos.ts`:

```ts
import { useQuery } from "@tanstack/react-query";
import { pedir } from "./cliente";
import type { Projeto } from "./tipos";

export const CHAVE_PROJETOS = ["projetos"] as const;
const NA_FILA = new Set(["queued", "running"]);

export function useProjetos() {
  return useQuery({
    queryKey: CHAVE_PROJETOS,
    queryFn: () => pedir<{ projetos: Projeto[] }>("/api/projetos"),
    staleTime: 30_000,
  });
}

export function contarNaFila(projetos?: Projeto[]): number {
  return (projetos ?? []).filter((p) => NA_FILA.has(p.status)).length;
}

export function projetoRodando(projetos?: Projeto[]): Projeto | undefined {
  return projetos?.find((p) => p.status === "running");
}
```

- [ ] **Step 5: Rodar**

Run: `npm --prefix picorte/web test` e `npm --prefix picorte/web run check`
Expected: todos passam (4 + 5 + 9 = 18 testes); tipos sem erro.

- [ ] **Step 6: Sem commit.**

---

### Task 3: Primitivos de UI — ícone, rótulo de status, poço travado e estados

**Files:**
- Create: `picorte/web/src/ui/Icone.tsx`
- Create: `picorte/web/src/ui/StatusRotulo.tsx`
- Create: `picorte/web/src/ui/PocoTravado.tsx`
- Create: `picorte/web/src/ui/Estados.tsx`
- Modify: `picorte/web/src/testes/fabrica.ts` (acrescentar `renderizar`)
- Test: `picorte/web/src/ui/PocoTravado.test.tsx`
- Test: `picorte/web/src/ui/Estados.test.tsx`

**Interfaces:**
- Consumes: `Capacidade`, `ListaCapacidades`, `Projeto` (`api/tipos.ts`); `rotuloDoStatus`, `Rotulo`, `CHAVE_CAPACIDADES` (`api/capacidades.ts`); `CHAVE_PROJETOS` (`api/projetos.ts`); `cap`, `lista` (`testes/fabrica.ts`).
- Produces:
  - `type NomeIcone`; `<Icone nome pequeno? className? />`;
  - `<StatusRotulo capacidade />`;
  - `<PocoTravado capacidade nomesDependencias? onTentarDeNovo? />`;
  - `<Carregando linhas? rotulo? />`, `<Vazio frase>{children}</Vazio>`, `<ErroCarregar frase detalhe? onTentarDeNovo />`, `<PicorteDesligado plataforma? />`;
  - `detectarPlataforma(ua?): "windows" | "linux"`;
  - `renderizar(ui, { rota?, capacidades?, projetos? }) → { cliente, roteador, ...render }`.

- [ ] **Step 1: Acrescentar `renderizar` à fábrica**

Acrescente a `picorte/web/src/testes/fabrica.ts`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { CHAVE_CAPACIDADES } from "../api/capacidades";
import { CHAVE_PROJETOS } from "../api/projetos";
import type { Projeto } from "../api/tipos";

interface OpcoesRender {
  rota?: string;
  capacidades?: ListaCapacidades;
  projetos?: Projeto[];
}

/** Renderiza dentro de QueryClient + roteador de memória, com o cache já preenchido (sem rede). */
export function renderizar(ui: ReactElement, { rota = "/", capacidades, projetos }: OpcoesRender = {}) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (capacidades) cliente.setQueryData(CHAVE_CAPACIDADES, capacidades);
  if (projetos) cliente.setQueryData(CHAVE_PROJETOS, { projetos });
  const roteador = createMemoryRouter([{ path: "*", element: ui }], { initialEntries: [rota] });
  const resultado = render(
    <QueryClientProvider client={cliente}>
      <RouterProvider router={roteador} />
    </QueryClientProvider>,
  );
  return { cliente, roteador, ...resultado };
}
```

Renomeie o arquivo para `fabrica.tsx`, porque agora ele tem JSX. Atualize o import em `api/capacidades.test.ts` (`from "../testes/fabrica"` continua valendo, sem extensão).

- [ ] **Step 2: Escrever os testes (falhando)**

`picorte/web/src/ui/PocoTravado.test.tsx`:

```tsx
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { cap, renderizar } from "../testes/fabrica";
import { PocoTravado } from "./PocoTravado";

const travada = (p: Parameters<typeof cap>[0]) => cap({ status: "travado", ...p });

describe("PocoTravado (Contrato de Travas)", () => {
  it("codigo: diz a história e o que falta", () => {
    renderizar(<PocoTravado capacidade={travada({
      id: "REV-8", titulo: "👍/👎 por corte", tipo_motivo: "codigo", falta: ["B10 + endpoint"],
      origem: { epico: "6", historia: "6.6", cap: null },
    })} />);
    expect(screen.getByText("👍/👎 por corte")).toBeInTheDocument();
    expect(screen.getByText("Travado")).toBeInTheDocument();
    expect(screen.getByText("Chega na história 6.6.")).toBeInTheDocument();
    expect(screen.getByText("Falta: B10 + endpoint")).toBeInTheDocument();
  });
  it("codigo com história fora do padrão não inventa número de história", () => {
    renderizar(<PocoTravado capacidade={travada({
      id: "SIS-13", tipo_motivo: "codigo", origem: { epico: "6", historia: "regra 6", cap: null },
    })} />);
    expect(screen.getByText("Ainda não foi construído.")).toBeInTheDocument();
  });
  it("config: leva direto às Configurações", () => {
    renderizar(<PocoTravado capacidade={travada({
      id: "LIV-1", tipo_motivo: "config", falta: ["credencial de app da Twitch"],
    })} />);
    expect(screen.getByText("Falta configurar: credencial de app da Twitch.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Configurar" })).toHaveAttribute("href", "/config");
  });
  it("dado: diz quando aparece", () => {
    renderizar(<PocoTravado capacidade={travada({ id: "MET-1", tipo_motivo: "dado", falta: ["houver publicação com link"] })} />);
    expect(screen.getByText("Ainda sem dados: aparece quando houver publicação com link.")).toBeInTheDocument();
  });
  it("temporario: Indisponível agora com Tentar de novo", () => {
    const tentar = vi.fn();
    renderizar(<PocoTravado onTentarDeNovo={tentar} capacidade={travada({
      id: "SIS-7", tipo_motivo: "temporario", motivo: "sem cota do Gemini desde 21/11",
    })} />);
    expect(screen.getByText("Indisponível agora")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(tentar).toHaveBeenCalledOnce();
  });
  it("depende_de mostra os nomes, da função até a raiz", () => {
    renderizar(<PocoTravado nomesDependencias={{ "MET-1": "Métricas 1h/24h/7d", "PUB-3": "Links publicados" }}
      capacidade={travada({ id: "MET-3", tipo_motivo: "codigo", depende_de: ["MET-1", "PUB-3"] })} />);
    expect(screen.getByText("Depende de: Métricas 1h/24h/7d ← Links publicados")).toBeInTheDocument();
  });
  it("A5: nunca mostra os dados de uma função travada", () => {
    const { container } = renderizar(<PocoTravado capacidade={travada({
      id: "SIS-1", tipo_motivo: "config", dados: { vram_mib: 8188 },
    })} />);
    expect(container.textContent).not.toContain("8188");
  });
});
```

`picorte/web/src/ui/Estados.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Carregando, detectarPlataforma, ErroCarregar, PicorteDesligado, Vazio } from "./Estados";

describe("estados desenhados", () => {
  it("Carregando é um status com nome", () => {
    render(<Carregando rotulo="Carregando as funções" />);
    expect(screen.getByRole("status", { name: "Carregando as funções" })).toBeInTheDocument();
  });
  it("Vazio mostra a frase e a ação", () => {
    render(<Vazio frase="Nada na fila."><button type="button">Cortar</button></Vazio>);
    expect(screen.getByText("Nada na fila.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cortar" })).toBeInTheDocument();
  });
  it("ErroCarregar: frase, Tentar de novo e detalhe técnico recolhido", () => {
    const tentar = vi.fn();
    render(<ErroCarregar frase="Não consegui ler o status." detalhe="HTTP 500: Traceback" onTentarDeNovo={tentar} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Não consegui ler o status.");
    expect(screen.queryByText("HTTP 500: Traceback")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "ver detalhe técnico" }));
    expect(screen.getByText("HTTP 500: Traceback")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(tentar).toHaveBeenCalledOnce();
  });
  it("PicorteDesligado dá o comando certo para cada sistema", () => {
    const { unmount } = render(<PicorteDesligado plataforma="windows" />);
    expect(screen.getByText("O Picorte não está rodando neste computador.")).toBeInTheDocument();
    expect(screen.getByText("python estudio.py")).toBeInTheDocument();
    unmount();
    render(<PicorteDesligado plataforma="linux" />);
    expect(screen.getByText("python3 estudio.py")).toBeInTheDocument();
  });
  it("detectarPlataforma", () => {
    expect(detectarPlataforma("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")).toBe("windows");
    expect(detectarPlataforma("Mozilla/5.0 (X11; Ubuntu; Linux x86_64)")).toBe("linux");
  });
});
```

- [ ] **Step 3: Ver falhar**

Run: `npm --prefix picorte/web test`
Expected: FAIL (`./PocoTravado` e `./Estados` não existem).

- [ ] **Step 4: Implementar**

`picorte/web/src/ui/Icone.tsx` (traços do sprite de `design/estudio/fonte/comum.html`, mais o alfinete):

```tsx
import type { ReactNode } from "react";

const DESENHOS = {
  lives: <><rect x="3" y="5" width="18" height="12" rx="3" /><path d="M8 21h8M10 9.5l4 1.5-4 1.5z" /></>,
  fila: <path d="M4 6h16M4 12h16M4 18h10" />,
  revisao: <><rect x="4" y="3" width="16" height="18" rx="3" /><path d="M10 9l5 3-5 3z" /></>,
  publicacao: <path d="M12 15V4M7 9l5-5 5 5M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3" />,
  fontes: <><circle cx="9" cy="8" r="3.5" /><path d="M3 20c.6-3.4 3-5.5 6-5.5s5.4 2.1 6 5.5M16 4.5a3.5 3.5 0 0 1 0 7M18.5 14.8c1.4.9 2.3 2.6 2.5 5.2" /></>,
  escudo: <><path d="M12 3l7 3v5c0 4.6-3 8.3-7 10-4-1.7-7-5.4-7-10V6z" /><path d="M9 12l2 2 4-4" /></>,
  saude: <path d="M3 12h4l2-5 4 10 2-5h6" />,
  aprend: <path d="M4 19V5M4 19h16M8 15l3-4 3 2 5-6" />,
  radar: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><path d="M12 12l5-5" /></>,
  config: <><path d="M10.3 3h3.4l.5 2.6 1.9 1.1 2.5-.9 1.7 2.9-2 1.7v2.2l2 1.7-1.7 2.9-2.5-.9-1.9 1.1-.5 2.6h-3.4l-.5-2.6-1.9-1.1-2.5.9-1.7-2.9 2-1.7v-2.2l-2-1.7 1.7-2.9 2.5.9 1.9-1.1z" /><circle cx="12" cy="12" r="3" /></>,
  cad: <><rect x="5" y="11" width="14" height="10" rx="2.5" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></>,
  ok: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  av: <><path d="M12 4l9 16H3z" /><path d="M12 10v4M12 17v.5" /></>,
  traco: <path d="M7 12h10" />,
  vivo: <><circle cx="12" cy="12" r="3" /><path d="M6.3 6.3a8 8 0 0 0 0 11.4M17.7 6.3a8 8 0 0 1 0 11.4" /></>,
  sol: <><circle cx="12" cy="12" r="4" /><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" /></>,
  pino: <><path d="M9 4h6l-1 5 3 3H7l3-3z" /><path d="M12 15v5" /></>,
} satisfies Record<string, ReactNode>;

export type NomeIcone = keyof typeof DESENHOS;

export function Icone({ nome, pequeno = false, className = "" }: { nome: NomeIcone; pequeno?: boolean; className?: string }) {
  return (
    <svg className={["ic", pequeno ? "ic-p" : "", className].filter(Boolean).join(" ")}
      viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {DESENHOS[nome]}
    </svg>
  );
}
```

`picorte/web/src/ui/StatusRotulo.tsx`:

```tsx
import { rotuloDoStatus, type Rotulo } from "../api/capacidades";
import type { Capacidade } from "../api/tipos";
import { Icone, type NomeIcone } from "./Icone";

export const ICONE_DO_ROTULO: Record<Rotulo, NomeIcone> = {
  Ligado: "ok", Parcial: "av", Travado: "cad", "Indisponível agora": "av", "Desligado por você": "traco",
};
export const TOM_DO_ROTULO: Record<Rotulo, "ok" | "av" | "trav"> = {
  Ligado: "ok", Parcial: "av", Travado: "trav", "Indisponível agora": "av", "Desligado por você": "trav",
};
const COR: Record<"ok" | "av" | "trav", string> = { ok: "text-ok", av: "text-aviso", trav: "text-tinta-3" };

/** Status sempre com ícone + palavra do vocabulário fixo (nunca só cor). */
export function StatusRotulo({ capacidade }: { capacidade: Pick<Capacidade, "status" | "tipo_motivo"> }) {
  const rotulo = rotuloDoStatus(capacidade);
  return (
    <span className="inline-flex items-center gap-1.5 font-medium text-tinta">
      <Icone nome={ICONE_DO_ROTULO[rotulo]} pequeno className={COR[TOM_DO_ROTULO[rotulo]]} />
      {rotulo}
    </span>
  );
}
```

`picorte/web/src/ui/PocoTravado.tsx`:

```tsx
import { Link } from "react-router";
import type { Capacidade } from "../api/tipos";
import { Icone } from "./Icone";
import { StatusRotulo } from "./StatusRotulo";

interface Props {
  capacidade: Capacidade;
  nomesDependencias?: Record<string, string>;
  onTentarDeNovo?: () => void;
}

const HISTORIA = /^\d+(\.\d+)*$/;

function fraseDoMotivo(c: Capacidade): string {
  const falta = c.falta.join("; ");
  switch (c.tipo_motivo) {
    case "codigo":
      return c.origem.historia && HISTORIA.test(c.origem.historia)
        ? `Chega na história ${c.origem.historia}.`
        : "Ainda não foi construído.";
    case "config":
      return `Falta configurar: ${falta || c.motivo}.`;
    case "dado":
      return `Ainda sem dados: aparece quando ${falta || c.motivo}.`;
    case "escolha":
      return "Desligado por você.";
    default:
      return c.motivo;
  }
}

/** Espaço impresso esperando a figurinha: diz o que falta e de que depende; nunca mostra dados (A5). */
export function PocoTravado({ capacidade: c, nomesDependencias = {}, onTentarDeNovo }: Props) {
  const dependencias = c.depende_de.map((id) => nomesDependencias[id] ?? id);
  const falta = c.falta.join("; ");
  return (
    <section className="espaco" aria-label={c.titulo}>
      <p className="tt"><Icone nome="cad" pequeno />{c.titulo}</p>
      <p className="estado"><StatusRotulo capacidade={c} /></p>
      <p className="falta">{fraseDoMotivo(c)}</p>
      {c.tipo_motivo === "codigo" && falta && <p className="depende">Falta: {falta}</p>}
      {dependencias.length > 0 && <p className="depende">Depende de: {dependencias.join(" ← ")}</p>}
      {c.tipo_motivo === "config" && <Link className="pilula sec" to="/config">Configurar</Link>}
      {c.tipo_motivo === "temporario" && onTentarDeNovo && (
        <button type="button" className="pilula sec" onClick={onTentarDeNovo}>Tentar de novo</button>
      )}
    </section>
  );
}
```

`picorte/web/src/ui/Estados.tsx`:

```tsx
import { Collapsible } from "@base-ui/react/collapsible";
import type { ReactNode } from "react";

/** Esqueleto só para dado real a caminho (nunca em travado). */
export function Carregando({ linhas = 3, rotulo = "Carregando" }: { linhas?: number; rotulo?: string }) {
  return (
    <div role="status" aria-label={rotulo} className="flex flex-col gap-2">
      {Array.from({ length: linhas }, (_, i) => <div key={i} className="esqueleto h-9" />)}
    </div>
  );
}

export function Vazio({ frase, children }: { frase: string; children?: ReactNode }) {
  return (
    <div className="vazio">
      <p>{frase}</p>
      {children}
    </div>
  );
}

interface PropsErro {
  frase: string;
  detalhe?: string;
  onTentarDeNovo: () => void;
}

/** Erro técnico vira frase + próximo passo; o detalhe cru fica recolhido. */
export function ErroCarregar({ frase, detalhe, onTentarDeNovo }: PropsErro) {
  return (
    <div role="alert" className="erro-carregar">
      <p className="font-semibold text-tinta">{frase}</p>
      <button type="button" className="pilula sec self-start" onClick={onTentarDeNovo}>Tentar de novo</button>
      {detalhe && (
        <Collapsible.Root>
          <Collapsible.Trigger className="link-fraco">ver detalhe técnico</Collapsible.Trigger>
          <Collapsible.Panel>
            <pre className="detalhe">{detalhe}</pre>
          </Collapsible.Panel>
        </Collapsible.Root>
      )}
    </div>
  );
}

export type Plataforma = "windows" | "linux";

export function detectarPlataforma(ua: string = navigator.userAgent): Plataforma {
  return /windows/i.test(ua) ? "windows" : "linux";
}

/** Global: o backend não responde. Nada de dado em cache fingindo estar vivo. */
export function PicorteDesligado({ plataforma = detectarPlataforma() }: { plataforma?: Plataforma }) {
  const comando = plataforma === "windows" ? "python estudio.py" : "python3 estudio.py";
  return (
    <section className="espaco desligado" role="alert">
      <h1>O Picorte não está rodando neste computador.</h1>
      <p>Abra um terminal na pasta do projeto e rode:</p>
      <pre className="comando num">{comando}</pre>
      <p className="depende">Esta página volta sozinha quando o Picorte responder.</p>
    </section>
  );
}
```

- [ ] **Step 5: Rodar**

Run: `npm --prefix picorte/web test` e `npm --prefix picorte/web run check`
Expected: todos passam (18 + 7 + 5 = 30); tipos sem erro.

- [ ] **Step 6: Sem commit.**

---

### Task 4: Tempo real — loja e ligação ao SSE

**Files:**
- Create: `picorte/web/src/tempo-real/loja.ts`
- Create: `picorte/web/src/tempo-real/eventos.ts`
- Test: `picorte/web/src/tempo-real/eventos.test.ts`

**Interfaces:**
- Consumes: `CHAVE_CAPACIDADES`, `CHAVE_PROJETOS`, `Progresso`, `FonteFalsa`.
- Produces:
  - `type Conexao = "conectando" | "conectado" | "reconectando"`;
  - `useTempoReal` (Zustand: `conexao`, `progresso: Record<string, Progresso & { em: number }>`, `definirConexao`, `registrarProgresso`);
  - `ESTADO_INICIAL_TEMPO_REAL`;
  - `ligarEventos(fonte: EventSource, invalidar: (chave: readonly string[]) => void): () => void`;
  - `useEventos(criar?: () => EventSource): void`.

- [ ] **Step 1: Escrever o teste (falhando)**

`picorte/web/src/tempo-real/eventos.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CHAVE_CAPACIDADES } from "../api/capacidades";
import { CHAVE_PROJETOS } from "../api/projetos";
import { FonteFalsa } from "../testes/fonte-falsa";
import { ligarEventos } from "./eventos";
import { ESTADO_INICIAL_TEMPO_REAL, useTempoReal } from "./loja";

beforeEach(() => useTempoReal.setState(ESTADO_INICIAL_TEMPO_REAL));

function ligar() {
  const fonte = new FonteFalsa("/api/eventos");
  const invalidar = vi.fn();
  const desligar = ligarEventos(fonte as unknown as EventSource, invalidar);
  return { fonte, invalidar, desligar };
}

describe("ligarEventos", () => {
  it("'ola' marca conectado e relê capacidades e projetos", () => {
    const { fonte, invalidar } = ligar();
    expect(useTempoReal.getState().conexao).toBe("conectando");
    fonte.emitir("ola", { resumo: { ligado: 1, parcial: 0, travado: 0 } });
    expect(useTempoReal.getState().conexao).toBe("conectado");
    expect(invalidar).toHaveBeenCalledWith(CHAVE_CAPACIDADES);
    expect(invalidar).toHaveBeenCalledWith(CHAVE_PROJETOS);
  });
  it("'capacidades' relê as capacidades; 'job' relê os projetos", () => {
    const { fonte, invalidar } = ligar();
    fonte.emitir("capacidades", { mudaram: [{ id: "SIS-6", de: "ligado", para: "travado" }] });
    expect(invalidar).toHaveBeenLastCalledWith(CHAVE_CAPACIDADES);
    fonte.emitir("job", { projeto: "abc", fase: "fim", acao: "render", ok: true });
    expect(invalidar).toHaveBeenLastCalledWith(CHAVE_PROJETOS);
  });
  it("'progresso' guarda o progresso real por projeto", () => {
    const { fonte } = ligar();
    fonte.emitir("progresso", { projeto: "abc", stage: "render 4/17", done: 4, total: 17, detail: "" });
    expect(useTempoReal.getState().progresso.abc).toMatchObject({ done: 4, total: 17 });
  });
  it("progresso sem projeto ou ilegível é ignorado", () => {
    const { fonte } = ligar();
    fonte.dispatchEvent(new MessageEvent("progresso", { data: "{quebrado" }));
    fonte.emitir("progresso", { done: 1 });
    expect(useTempoReal.getState().progresso).toEqual({});
  });
  it("erro de conexão vira 'reconectando'; desligar fecha a fonte", () => {
    const { fonte, desligar } = ligar();
    fonte.emitir("ola");
    fonte.dispatchEvent(new Event("error"));
    expect(useTempoReal.getState().conexao).toBe("reconectando");
    desligar();
    expect(fonte.fechada).toBe(true);
    fonte.emitir("ola");
    expect(useTempoReal.getState().conexao).toBe("reconectando");
  });
});
```

- [ ] **Step 2: Ver falhar**

Run: `npm --prefix picorte/web test`
Expected: FAIL (`./eventos` e `./loja` não existem).

- [ ] **Step 3: Implementar**

`picorte/web/src/tempo-real/loja.ts`:

```ts
import { create } from "zustand";
import type { Progresso } from "../api/tipos";

export type Conexao = "conectando" | "conectado" | "reconectando";

interface EstadoTempoReal {
  conexao: Conexao;
  progresso: Record<string, Progresso & { em: number }>;
  definirConexao: (conexao: Conexao) => void;
  registrarProgresso: (projeto: string, progresso: Progresso) => void;
}

export const ESTADO_INICIAL_TEMPO_REAL = { conexao: "conectando" as Conexao, progresso: {} };

export const useTempoReal = create<EstadoTempoReal>((set) => ({
  ...ESTADO_INICIAL_TEMPO_REAL,
  definirConexao: (conexao) => set({ conexao }),
  registrarProgresso: (projeto, progresso) =>
    set((s) => ({ progresso: { ...s.progresso, [projeto]: { ...progresso, em: Date.now() } } })),
}));
```

`picorte/web/src/tempo-real/eventos.ts`:

```ts
import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { CHAVE_CAPACIDADES } from "../api/capacidades";
import { CHAVE_PROJETOS } from "../api/projetos";
import type { Progresso } from "../api/tipos";
import { useTempoReal } from "./loja";

type Invalidar = (chave: readonly string[]) => void;

function lerDados(evento: Event): Record<string, unknown> | null {
  try {
    const dados = JSON.parse(String((evento as MessageEvent).data));
    return dados && typeof dados === "object" ? dados : null;
  } catch {
    return null;
  }
}

/** Liga o SSE /api/eventos à loja e ao cache. Devolve a função que desliga tudo. */
export function ligarEventos(fonte: EventSource, invalidar: Invalidar): () => void {
  const { definirConexao, registrarProgresso } = useTempoReal.getState();
  const ouvintes: Record<string, (e: Event) => void> = {
    ola: () => {
      definirConexao("conectado");
      invalidar(CHAVE_CAPACIDADES); // ao (re)conectar, relê tudo: eventos podem ter se perdido
      invalidar(CHAVE_PROJETOS);
    },
    capacidades: () => invalidar(CHAVE_CAPACIDADES),
    job: () => invalidar(CHAVE_PROJETOS),
    progresso: (e) => {
      const dados = lerDados(e);
      if (!dados || typeof dados.projeto !== "string") return;
      const { projeto, ...resto } = dados;
      registrarProgresso(projeto, resto as Progresso);
    },
    error: () => definirConexao("reconectando"),
  };
  for (const [tipo, ouvinte] of Object.entries(ouvintes)) fonte.addEventListener(tipo, ouvinte);
  return () => {
    for (const [tipo, ouvinte] of Object.entries(ouvintes)) fonte.removeEventListener(tipo, ouvinte);
    fonte.close();
  };
}

export function useEventos(criar: () => EventSource = () => new EventSource("/api/eventos")): void {
  const cliente = useQueryClient();
  // a fonte nasce uma vez por montagem (criar fica fora das dependências de propósito)
  useEffect(() => ligarEventos(criar(), (chave) => void cliente.invalidateQueries({ queryKey: chave })), [cliente]);
}
```

- [ ] **Step 4: Rodar**

Run: `npm --prefix picorte/web test` e `npm --prefix picorte/web run check`
Expected: todos passam (30 + 5 = 35); tipos sem erro.

- [ ] **Step 5: Sem commit.**

---

### Task 5: Sidebar autorretrátil e estado do sistema no pé

**Files:**
- Create: `picorte/web/src/casca/areas.ts`
- Create: `picorte/web/src/casca/tema.ts`
- Create: `picorte/web/src/casca/useSidebar.ts`
- Create: `picorte/web/src/casca/EstadoSistema.tsx`
- Create: `picorte/web/src/casca/Sidebar.tsx`
- Modify: `picorte/web/src/testes/fabrica.tsx` (acrescentar `LISTA_PADRAO`)
- Test: `picorte/web/src/casca/useSidebar.test.ts`
- Test: `picorte/web/src/casca/EstadoSistema.test.tsx`
- Test: `picorte/web/src/casca/Sidebar.test.tsx`

**Interfaces:**
- Consumes:
  - `capacidadePorId`, `capacidadesDaArea`, `areaTravada`, `rotuloDoStatus`, `contarNaFila`, `projetoRodando`;
  - `ListaCapacidades`, `Projeto`;
  - `useTempoReal`, `ESTADO_INICIAL_TEMPO_REAL`;
  - `Icone`, `NomeIcone`, `ICONE_DO_ROTULO`, `TOM_DO_ROTULO`;
  - `renderizar`, `cap`, `lista`.
- Produces:
  - `interface Area { chave; rota; rotulo; icone; tecla; areasCapacidade; historia }`, `AREAS`, `CONFIGURACOES`, `TODAS_AREAS`;
  - `temaAtual()`, `alternarTema()`;
  - `ATRASO_ABRIR_MS = 150`, `ATRASO_FECHAR_MS = 120`;
  - `useSidebar(): { fixa; aberta; empurra; alternarFixa; eventos: { onMouseEnter; onMouseLeave; onFocus; onBlur } }`;
  - `<EstadoSistema capacidades? projetos? desligado />`;
  - `<Sidebar aberta fixa eventos alternarFixa capacidades? projetos? desligado />`;
  - `LISTA_PADRAO`.

- [ ] **Step 1: Criar `areas.ts` e `tema.ts` (sem lógica a testar além do uso)**

`picorte/web/src/casca/areas.ts`:

```ts
import type { NomeIcone } from "../ui/Icone";

/** As áreas do painel (EXPERIENCE.md › Information Architecture), na ordem da sidebar. */
export interface Area {
  chave: string;
  rota: string;
  rotulo: string;
  icone: NomeIcone;
  tecla: string; // g + tecla
  areasCapacidade: readonly string[]; // valores de Capacidade.area
  historia: string; // história que constrói a página
}

export const AREAS: readonly Area[] = [
  { chave: "lives", rota: "/", rotulo: "Lives", icone: "lives", tecla: "l", areasCapacidade: ["lives"], historia: "6.5" },
  { chave: "fila", rota: "/fila", rotulo: "Fila", icone: "fila", tecla: "f", areasCapacidade: ["fila"], historia: "6.6" },
  { chave: "revisao", rota: "/revisao", rotulo: "Revisão", icone: "revisao", tecla: "r", areasCapacidade: ["revisao"], historia: "6.6" },
  { chave: "publicacao", rota: "/publicacao", rotulo: "Publicação", icone: "publicacao", tecla: "p", areasCapacidade: ["publicacao"], historia: "6.8" },
  { chave: "fontes", rota: "/fontes", rotulo: "Fontes", icone: "fontes", tecla: "o", areasCapacidade: ["fontes"], historia: "6.7" },
  { chave: "escudo", rota: "/escudo", rotulo: "Escudo", icone: "escudo", tecla: "e", areasCapacidade: ["escudo"], historia: "6.7" },
  { chave: "saude", rota: "/saude", rotulo: "Saúde", icone: "saude", tecla: "s", areasCapacidade: ["saude", "sistema"], historia: "6.7" },
  { chave: "aprendizado", rota: "/aprendizado", rotulo: "Aprendizado", icone: "aprend", tecla: "a", areasCapacidade: ["metricas"], historia: "6.8" },
  { chave: "radar", rota: "/radar", rotulo: "Radar", icone: "radar", tecla: "d", areasCapacidade: ["radar"], historia: "6.8" },
];

export const CONFIGURACOES: Area = {
  chave: "config", rota: "/config", rotulo: "Configurações", icone: "config", tecla: "c", areasCapacidade: [], historia: "6.7",
};

export const TODAS_AREAS: readonly Area[] = [...AREAS, CONFIGURACOES];
```

`picorte/web/src/casca/tema.ts`:

```ts
export type Tema = "light" | "dark";
const CHAVE = "picorte-tema"; // a mesma dos protótipos e do public/tema-inicial.js

export function temaAtual(): Tema {
  const definido = document.documentElement.getAttribute("data-theme");
  if (definido === "light" || definido === "dark") return definido;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function alternarTema(): Tema {
  const novo: Tema = temaAtual() === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", novo);
  try {
    localStorage.setItem(CHAVE, novo);
  } catch {
    /* navegador sem armazenamento: vale só nesta aba */
  }
  return novo;
}
```

Acrescente a `picorte/web/src/testes/fabrica.tsx`:

```tsx
export const LISTA_PADRAO = lista([
  cap({ id: "SIS-1", motivo: "RTX 4060 Ti com 8188 MiB", dados: { gpu_name: "RTX 4060 Ti", vram_mib: 8188 } }),
  cap({ id: "SIS-6", titulo: "Motor de IA: Ollama", dados: { modelos: ["qwen3.5:9b"] } }),
  cap({ id: "SIS-7", titulo: "Motor de IA: Gemini (agy)", status: "parcial", tipo_motivo: "temporario", motivo: "o Gemini falhou num job" }),
  cap({ id: "SIS-8", titulo: "Motor de IA: Claude CLI" }),
  cap({ id: "SIS-11", titulo: "yt-dlp, node e demucs" }),
  cap({ id: "SIS-14", titulo: "Espaço livre em disco", motivo: "57.0 GiB livres" }),
  cap({ id: "FIL-1", area: "fila", titulo: "Criar projeto" }),
  cap({ id: "LIV-4", area: "lives", titulo: "Recentes pelo yt-dlp", status: "parcial", tipo_motivo: "config", motivo: "sem chave da YouTube Data API" }),
  cap({ id: "LIV-3", area: "lives", titulo: "Em alta", status: "travado", tipo_motivo: "codigo", falta: ["radar com a ordenação oficial"], origem: { epico: "5", historia: "5.1", cap: null } }),
  cap({ id: "MET-1", area: "metricas", titulo: "Snapshots de métricas", status: "travado", tipo_motivo: "codigo", origem: { epico: "7", historia: "7.1", cap: null } }),
  cap({ id: "RAD-1", area: "radar", titulo: "Tendências", status: "travado", tipo_motivo: "codigo", origem: { epico: "5", historia: "5.1", cap: null } }),
]);
```

- [ ] **Step 2: Escrever os testes (falhando)**

`picorte/web/src/casca/useSidebar.test.ts`:

```ts
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ATRASO_ABRIR_MS, ATRASO_FECHAR_MS, useSidebar } from "./useSidebar";

const matchMediaOriginal = window.matchMedia;
function telaLarga(larga: boolean) {
  window.matchMedia = ((consulta: string) => ({
    matches: larga && consulta.includes("min-width: 1920px"), media: consulta, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {},
    dispatchEvent: () => false,
  })) as typeof window.matchMedia;
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  window.matchMedia = matchMediaOriginal;
});

describe("useSidebar", () => {
  it("abre só depois do atraso de intenção e fecha com atraso curto", () => {
    const { result } = renderHook(() => useSidebar());
    act(() => result.current.eventos.onMouseEnter());
    act(() => vi.advanceTimersByTime(ATRASO_ABRIR_MS - 1));
    expect(result.current.aberta).toBe(false);
    act(() => vi.advanceTimersByTime(1));
    expect(result.current.aberta).toBe(true);
    act(() => result.current.eventos.onMouseLeave());
    act(() => vi.advanceTimersByTime(ATRASO_FECHAR_MS));
    expect(result.current.aberta).toBe(false);
  });
  it("cruzar rápido não abre", () => {
    const { result } = renderHook(() => useSidebar());
    act(() => result.current.eventos.onMouseEnter());
    act(() => vi.advanceTimersByTime(80));
    act(() => result.current.eventos.onMouseLeave());
    act(() => vi.advanceTimersByTime(500));
    expect(result.current.aberta).toBe(false);
  });
  it("foco por teclado abre na hora", () => {
    const { result } = renderHook(() => useSidebar());
    act(() => result.current.eventos.onFocus());
    expect(result.current.aberta).toBe(true);
  });
  it("alfinete é lembrado e só empurra a tela a partir de 1920 px", () => {
    telaLarga(false);
    const { result } = renderHook(() => useSidebar());
    act(() => result.current.alternarFixa());
    expect(result.current.fixa).toBe(true);
    expect(localStorage.getItem("picorte-sidebar-fixa")).toBe("1");
    expect(result.current.empurra).toBe(false);
    expect(result.current.aberta).toBe(false);

    telaLarga(true);
    const larga = renderHook(() => useSidebar());
    expect(larga.result.current.fixa).toBe(true);
    expect(larga.result.current.empurra).toBe(true);
    expect(larga.result.current.aberta).toBe(true);
  });
});
```

`picorte/web/src/casca/EstadoSistema.test.tsx`:

```tsx
import { act, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { ESTADO_INICIAL_TEMPO_REAL, useTempoReal } from "../tempo-real/loja";
import { cap, LISTA_PADRAO, lista, renderizar } from "../testes/fabrica";
import { EstadoSistema } from "./EstadoSistema";

beforeEach(() => useTempoReal.setState(ESTADO_INICIAL_TEMPO_REAL));

const link = (nome: RegExp) => screen.getByRole("link", { name: nome });

describe("EstadoSistema (pé da sidebar)", () => {
  it("provedores com marca de forma e texto, do backend", () => {
    renderizar(<EstadoSistema capacidades={LISTA_PADRAO} projetos={[]} desligado={false} />);
    expect(link(/Ollama/)).toHaveTextContent("Ollama · Ligado · qwen3.5:9b");
    expect(link(/Gemini/)).toHaveTextContent("Gemini · Indisponível agora · o Gemini falhou num job");
    expect(link(/Claude/)).toHaveTextContent("Claude · Ligado");
    expect(link(/GPU/)).toHaveTextContent("GPU · Livre · RTX 4060 Ti");
  });
  it("capacidades ilegíveis nunca aparecem como ligadas (regra 6)", () => {
    renderizar(<EstadoSistema capacidades={undefined} projetos={[]} desligado={false} />);
    expect(link(/Ollama/)).toHaveTextContent("Ollama · Indisponível agora · não consegui ler o status");
    expect(screen.queryByText(/Ligado/)).not.toBeInTheDocument();
  });
  it("anel da GPU com o progresso real, atualizado pelo SSE", () => {
    renderizar(<EstadoSistema capacidades={LISTA_PADRAO} desligado={false}
      projetos={[{ id: "abc", status: "running", progress: { done: 4, total: 17 } }]} />);
    expect(screen.getByRole("img", { name: "Progresso do job: 24%" })).toBeInTheDocument();
    expect(link(/GPU/)).toHaveTextContent("GPU · Job rodando 4/17");
    act(() => useTempoReal.getState().registrarProgresso("abc", { done: 8, total: 17 }));
    expect(screen.getByRole("img", { name: "Progresso do job: 47%" })).toBeInTheDocument();
  });
  it("tempo real mostra reconectando", () => {
    useTempoReal.setState({ conexao: "reconectando" });
    renderizar(<EstadoSistema capacidades={LISTA_PADRAO} projetos={[]} desligado={false} />);
    expect(screen.getByText(/reconectando…/)).toBeInTheDocument();
  });
  it("alerta de ambiente só aparece quando algo não está ligado", () => {
    const disco = lista([
      ...LISTA_PADRAO.capacidades.filter((c) => c.id !== "SIS-14"),
      cap({ id: "SIS-14", status: "parcial", tipo_motivo: "temporario", motivo: "3.1 GiB livres (abaixo de 20.0 GiB)" }),
    ]);
    const { unmount } = renderizar(<EstadoSistema capacidades={LISTA_PADRAO} projetos={[]} desligado={false} />);
    expect(screen.queryByRole("link", { name: /Sistema/ })).not.toBeInTheDocument();
    unmount();
    renderizar(<EstadoSistema capacidades={disco} projetos={[]} desligado={false} />);
    expect(link(/Sistema/)).toHaveTextContent("Sistema · 3.1 GiB livres (abaixo de 20.0 GiB)");
    expect(link(/Sistema/)).toHaveAttribute("href", "/saude");
  });
  it("Picorte desligado: nada de status velho", () => {
    renderizar(<EstadoSistema capacidades={LISTA_PADRAO} projetos={[]} desligado />);
    expect(screen.getByRole("status")).toHaveTextContent("Picorte · desligado");
    expect(screen.queryByText(/Ollama/)).not.toBeInTheDocument();
  });
});
```

`picorte/web/src/casca/Sidebar.test.tsx`:

```tsx
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LISTA_PADRAO, renderizar } from "../testes/fabrica";
import { Sidebar } from "./Sidebar";

const eventos = { onMouseEnter: vi.fn(), onMouseLeave: vi.fn(), onFocus: vi.fn(), onBlur: vi.fn() };

function montar(opcoes: { rota?: string; desligado?: boolean; aberta?: boolean } = {}) {
  return renderizar(
    <Sidebar aberta={opcoes.aberta ?? false} fixa={false} eventos={eventos} alternarFixa={vi.fn()}
      capacidades={LISTA_PADRAO} desligado={opcoes.desligado ?? false}
      projetos={[{ id: "a", status: "running" }, { id: "b", status: "queued" }, { id: "c", status: "complete" }]} />,
    { rota: opcoes.rota ?? "/" },
  );
}

describe("Sidebar", () => {
  it("as 10 áreas na ordem da IA, com as inteiramente travadas marcadas", () => {
    const { container } = montar();
    const rotulos = [...container.querySelectorAll(".it .rot")].map((e) => e.textContent);
    expect(rotulos).toEqual([
      "Lives", "Fila · 2 na fila", "Revisão", "Publicação", "Fontes", "Escudo", "Saúde",
      "Aprendizado · travado", "Radar · travado", "Configurações",
    ]);
  });
  it("marca a página atual", () => {
    montar({ rota: "/fila" });
    expect(screen.getByRole("link", { name: /^Fila/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /^Lives/ })).not.toHaveAttribute("aria-current");
  });
  it("contagem real só na Fila", () => {
    const { container } = montar();
    expect([...container.querySelectorAll(".it .cont")].map((e) => e.textContent)).toEqual(["2"]);
  });
  it("desligado: sem contagens nem cadeados vindos de dado velho", () => {
    const { container } = montar({ desligado: true });
    expect(container.querySelectorAll(".it .cont")).toHaveLength(0);
    expect(container.querySelectorAll(".it .cad")).toHaveLength(0);
  });
  it("expõe o estado aberto para o CSS", () => {
    montar({ aberta: true });
    expect(screen.getByRole("navigation", { name: "Navegação principal" })).toHaveAttribute("data-aberta", "true");
  });
});
```

- [ ] **Step 3: Ver falhar**

Run: `npm --prefix picorte/web test`
Expected: FAIL (`./useSidebar`, `./EstadoSistema` e `./Sidebar` não existem).

- [ ] **Step 4: Implementar**

`picorte/web/src/casca/useSidebar.ts`:

```ts
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type FocusEvent } from "react";

const CHAVE_FIXA = "picorte-sidebar-fixa";
export const ATRASO_ABRIR_MS = 150; // intenção: não abre quando o cursor só cruza
export const ATRASO_FECHAR_MS = 120;
const LARGURA_EMPURRA = 1920; // abaixo disso o alfinete não fixa (EXPERIENCE.md › Responsive)

function lerFixa(): boolean {
  try {
    return localStorage.getItem(CHAVE_FIXA) === "1";
  } catch {
    return false;
  }
}

function useLarguraMinima(px: number): boolean {
  const consulta = `(min-width: ${px}px)`;
  return useSyncExternalStore(
    (avisar) => {
      const mql = window.matchMedia(consulta);
      mql.addEventListener("change", avisar);
      return () => mql.removeEventListener("change", avisar);
    },
    () => window.matchMedia(consulta).matches,
  );
}

export function useSidebar() {
  const [fixa, setFixa] = useState(lerFixa);
  const [intencao, setIntencao] = useState(false);
  const relogio = useRef<number | undefined>(undefined);
  const larga = useLarguraMinima(LARGURA_EMPURRA);

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE_FIXA, fixa ? "1" : "0");
    } catch {
      /* sem armazenamento: o alfinete vale só nesta aba */
    }
  }, [fixa]);
  useEffect(() => () => window.clearTimeout(relogio.current), []);

  const agendar = useCallback((valor: boolean, ms: number) => {
    window.clearTimeout(relogio.current);
    relogio.current = window.setTimeout(() => setIntencao(valor), ms);
  }, []);

  const alternarFixa = useCallback(() => setFixa((f) => !f), []);
  const empurra = fixa && larga;

  return {
    fixa,
    aberta: intencao || empurra,
    empurra,
    alternarFixa,
    eventos: {
      onMouseEnter: () => agendar(true, ATRASO_ABRIR_MS),
      onMouseLeave: () => agendar(false, ATRASO_FECHAR_MS),
      onFocus: () => {
        window.clearTimeout(relogio.current);
        setIntencao(true);
      },
      onBlur: (e?: FocusEvent<HTMLElement>) => {
        if (e && e.currentTarget.contains(e.relatedTarget as Node | null)) return;
        agendar(false, ATRASO_FECHAR_MS);
      },
    },
  };
}
```

`picorte/web/src/casca/EstadoSistema.tsx`:

```tsx
import type { CSSProperties } from "react";
import { Link } from "react-router";
import { capacidadePorId, rotuloDoStatus } from "../api/capacidades";
import { projetoRodando } from "../api/projetos";
import type { ListaCapacidades, Progresso, Projeto } from "../api/tipos";
import { useTempoReal } from "../tempo-real/loja";
import { Icone } from "../ui/Icone";
import { ICONE_DO_ROTULO, TOM_DO_ROTULO } from "../ui/StatusRotulo";

const PROVEDORES = [["SIS-6", "Ollama"], ["SIS-7", "Gemini"], ["SIS-8", "Claude"]] as const;
const AMBIENTE = ["SIS-11", "SIS-14"] as const; // itens da Saúde › Sistema medidos por sonda

interface Props {
  capacidades?: ListaCapacidades;
  projetos?: Projeto[];
  desligado: boolean;
}

function primeiroModelo(dados: Record<string, unknown> | null): string {
  const modelos = dados?.modelos;
  return Array.isArray(modelos) && typeof modelos[0] === "string" ? modelos[0] : "";
}

export function EstadoSistema({ capacidades, projetos, desligado }: Props) {
  const conexao = useTempoReal((s) => s.conexao);
  const progresso = useTempoReal((s) => s.progresso);

  if (desligado) {
    return (
      <div className="sl" role="status">
        <span className="mk av"><Icone nome="av" pequeno /></span>
        <span className="rot"><b>Picorte</b> · desligado</span>
      </div>
    );
  }

  const gpu = capacidadePorId(capacidades, "SIS-1");
  const rodando = projetoRodando(projetos);
  const p: Progresso = rodando ? { ...(rodando.progress ?? {}), ...(progresso[rodando.id] ?? {}) } : {};
  const total = Number(p.total ?? 0);
  const feito = Number(p.done ?? 0);
  const pct = rodando && total > 0 ? Math.min(100, Math.round((feito / total) * 100)) : 0;
  const bruto = gpu.dados?.gpu_name;
  const nomeGpu = typeof bruto === "string" ? bruto : "";
  const textoGpu = rodando
    ? total > 0 ? `Job rodando ${feito}/${total}` : "Job rodando"
    : gpu.status === "ligado" ? `Livre${nomeGpu ? ` · ${nomeGpu}` : ""}` : `${rotuloDoStatus(gpu)} · ${gpu.motivo}`;
  const ambiente = AMBIENTE.map((id) => capacidadePorId(capacidades, id)).filter((c) => c.status !== "ligado");

  return (
    <>
      <Link className="sl" to="/fila" aria-live="polite">
        <span className="anel" style={{ "--p": `${pct}%` } as CSSProperties} role="img"
          aria-label={rodando ? `Progresso do job: ${pct}%` : "GPU sem job"} />
        <span className="rot"><b>GPU</b> · <span className="num">{textoGpu}</span></span>
      </Link>
      {PROVEDORES.map(([id, nome]) => {
        const c = capacidadePorId(capacidades, id);
        const rotulo = rotuloDoStatus(c);
        const extra = rotulo === "Ligado" ? primeiroModelo(c.dados) : c.motivo;
        return (
          <Link key={id} className="sl" to="/config">
            <span className={`mk ${TOM_DO_ROTULO[rotulo]}`}><Icone nome={ICONE_DO_ROTULO[rotulo]} pequeno /></span>
            <span className="rot"><b>{nome}</b> · {rotulo}{extra ? ` · ${extra}` : ""}</span>
          </Link>
        );
      })}
      <div className="sl">
        <span className={`mk ${conexao === "conectado" ? "ok" : "av"}`}><Icone nome="vivo" pequeno /></span>
        <span className="rot">
          <b>Tempo real</b> · {conexao === "conectado" ? "conectado" : conexao === "reconectando" ? "reconectando…" : "conectando…"}
        </span>
      </div>
      {ambiente.length > 0 && (
        <Link className="sl" to="/saude">
          <span className="mk av"><Icone nome="av" pequeno /></span>
          <span className="rot"><b>Sistema</b> · {ambiente[0].motivo}</span>
        </Link>
      )}
    </>
  );
}
```

`picorte/web/src/casca/Sidebar.tsx`:

```tsx
import type { FocusEvent } from "react";
import { Link, NavLink } from "react-router";
import iconePicorte from "../../../../design/brand/picorte-icone.svg";
import { areaTravada, capacidadesDaArea } from "../api/capacidades";
import { contarNaFila } from "../api/projetos";
import type { ListaCapacidades, Projeto } from "../api/tipos";
import { Icone } from "../ui/Icone";
import { AREAS, CONFIGURACOES, type Area } from "./areas";
import { EstadoSistema } from "./EstadoSistema";
import { alternarTema } from "./tema";

interface Props {
  aberta: boolean;
  fixa: boolean;
  eventos: {
    onMouseEnter: () => void;
    onMouseLeave: () => void;
    onFocus: () => void;
    onBlur: (e?: FocusEvent<HTMLElement>) => void;
  };
  alternarFixa: () => void;
  capacidades?: ListaCapacidades;
  projetos?: Projeto[];
  desligado: boolean;
}

function ItemNav({ area, contagem, travada }: { area: Area; contagem: number; travada: boolean }) {
  return (
    <NavLink className="it" to={area.rota} end={area.rota === "/"}>
      <Icone nome={area.icone} />
      {contagem > 0 && <span className="cont num" aria-hidden="true">{contagem}</span>}
      {travada && <Icone nome="cad" className="cad" />}
      <span className="rot">
        {area.rotulo}
        {travada ? " · travado" : ""}
        {contagem > 0 ? ` · ${contagem} na fila` : ""}
      </span>
    </NavLink>
  );
}

export function Sidebar({ aberta, fixa, eventos, alternarFixa, capacidades, projetos, desligado }: Props) {
  const naFila = desligado ? 0 : contarNaFila(projetos);
  return (
    <nav className="side" data-aberta={aberta} aria-label="Navegação principal" {...eventos}>
      <Link className="marca" to="/">
        <img src={iconePicorte} alt="" />
        <span className="marca-nome">Picorte</span>
      </Link>
      {AREAS.map((area) => (
        <ItemNav key={area.chave} area={area}
          contagem={area.chave === "fila" ? naFila : 0}
          travada={!desligado && areaTravada(capacidadesDaArea(capacidades, area.areasCapacidade))} />
      ))}
      <div className="sist" role="group" aria-label="Estado do sistema">
        <div className="sep" />
        <EstadoSistema capacidades={capacidades} projetos={projetos} desligado={desligado} />
        <button className="tema" type="button" onClick={() => alternarTema()}>
          <Icone nome="sol" /><span className="rot">Tema claro / escuro</span>
        </button>
        <button className="tema" type="button" aria-pressed={fixa} onClick={alternarFixa}>
          <Icone nome="pino" /><span className="rot">{fixa ? "Soltar a barra" : "Fixar a barra aberta"} <kbd>[</kbd></span>
        </button>
        <ItemNav area={CONFIGURACOES} contagem={0} travada={false} />
      </div>
    </nav>
  );
}
```

Nota: o texto do item da Fila ("Fila · 2 na fila") fica dentro de `.rot`, que some recolhido (opacidade 0) mas continua no nome acessível. A cápsula visual (`.cont`) é `aria-hidden`, para o número não ser lido duas vezes.

- [ ] **Step 5: Rodar**

Run: `npm --prefix picorte/web test` e `npm --prefix picorte/web run check`
Expected: todos passam (35 + 4 + 6 + 5 = 50); tipos sem erro.

- [ ] **Step 6: Sem commit.**

---

### Task 6: Atalhos globais (`g` + letra e `[`)

**Files:**
- Create: `picorte/web/src/casca/atalhos.ts`
- Test: `picorte/web/src/casca/atalhos.test.tsx`

**Interfaces:**
- Consumes: `TODAS_AREAS`.
- Produces: `ehCampoDeTexto(alvo: EventTarget | null): boolean`; `useAtalhosGlobais({ irPara: (rota: string) => void, alternarFixa: () => void }): void`.

- [ ] **Step 1: Escrever o teste (falhando)**

`picorte/web/src/casca/atalhos.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useAtalhosGlobais } from "./atalhos";

function Sonda(props: { irPara: (r: string) => void; alternarFixa: () => void }) {
  useAtalhosGlobais(props);
  return <input aria-label="campo" />;
}

function montar() {
  const irPara = vi.fn();
  const alternarFixa = vi.fn();
  render(<Sonda irPara={irPara} alternarFixa={alternarFixa} />);
  return { irPara, alternarFixa };
}

afterEach(() => vi.restoreAllMocks());

describe("atalhos globais", () => {
  it("g + letra vai para a área", () => {
    const { irPara } = montar();
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "s" });
    expect(irPara).toHaveBeenCalledWith("/saude");
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "l" });
    expect(irPara).toHaveBeenLastCalledWith("/");
  });
  it("a letra só vale até 1 s depois do g", () => {
    let agora = 1_000;
    vi.spyOn(Date, "now").mockImplementation(() => agora);
    const { irPara } = montar();
    fireEvent.keyDown(window, { key: "g" });
    agora = 2_500;
    fireEvent.keyDown(window, { key: "f" });
    expect(irPara).not.toHaveBeenCalled();
  });
  it("letra sem g antes não faz nada", () => {
    const { irPara } = montar();
    fireEvent.keyDown(window, { key: "f" });
    expect(irPara).not.toHaveBeenCalled();
  });
  it("[ fixa a sidebar; com Ctrl não", () => {
    const { alternarFixa } = montar();
    fireEvent.keyDown(window, { key: "[" });
    fireEvent.keyDown(window, { key: "[", ctrlKey: true });
    expect(alternarFixa).toHaveBeenCalledOnce();
  });
  it("dentro de um campo de texto nenhuma tecla de letra única dispara", () => {
    const { irPara, alternarFixa } = montar();
    const campo = screen.getByLabelText("campo");
    fireEvent.keyDown(campo, { key: "g" });
    fireEvent.keyDown(campo, { key: "s" });
    fireEvent.keyDown(campo, { key: "[" });
    expect(irPara).not.toHaveBeenCalled();
    expect(alternarFixa).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Ver falhar**

Run: `npm --prefix picorte/web test`
Expected: FAIL (`./atalhos` não existe).

- [ ] **Step 3: Implementar**

`picorte/web/src/casca/atalhos.ts`:

```ts
import { useEffect } from "react";
import { TODAS_AREAS } from "./areas";

const JANELA_G_MS = 1000;

export function ehCampoDeTexto(alvo: EventTarget | null): boolean {
  if (!(alvo instanceof HTMLElement)) return false;
  return alvo.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(alvo.tagName);
}

/** g + letra (até 1 s) navega; [ fixa a sidebar. Desligados com foco em campo de texto. */
export function useAtalhosGlobais({ irPara, alternarFixa }: { irPara: (rota: string) => void; alternarFixa: () => void }) {
  useEffect(() => {
    let gEm = 0;
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || ehCampoDeTexto(e.target)) return;
      if (e.key === "[") {
        e.preventDefault();
        alternarFixa();
        return;
      }
      if (gEm && Date.now() - gEm <= JANELA_G_MS) {
        gEm = 0;
        const area = TODAS_AREAS.find((a) => a.tecla === e.key.toLowerCase());
        if (area) {
          e.preventDefault();
          irPara(area.rota);
        }
        return;
      }
      gEm = e.key === "g" ? Date.now() : 0;
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [irPara, alternarFixa]);
}
```

- [ ] **Step 4: Rodar**

Run: `npm --prefix picorte/web test` e `npm --prefix picorte/web run check`
Expected: todos passam (50 + 5 = 55); tipos sem erro.

- [ ] **Step 5: Sem commit.**

---

### Task 7: Páginas, rotas, casca e montagem

**Files:**
- Create: `picorte/web/src/paginas/PaginaArea.tsx`
- Create: `picorte/web/src/paginas/NaoEncontrada.tsx`
- Create: `picorte/web/src/casca/Casca.tsx`
- Create: `picorte/web/src/rotas.tsx`
- Modify: `picorte/web/src/main.tsx` (substituir o provisório)
- Test: `picorte/web/src/paginas/PaginaArea.test.tsx`
- Test: `picorte/web/src/rotas.test.tsx`

**Interfaces:**
- Consumes:
  - `useCapacidades`, `capacidadesDaArea`, `useProjetos`, `ErroApi`;
  - `useEventos`, `useSidebar`, `useAtalhosGlobais`, `Sidebar`;
  - `PocoTravado`, `StatusRotulo`, `Carregando`, `Vazio`, `ErroCarregar`, `PicorteDesligado`, `verificadoHa`, `Icone`;
  - `AREAS`, `TODAS_AREAS`, `type Area`;
  - `renderizar`, `LISTA_PADRAO`, `FonteFalsa`.
- Produces: `<PaginaArea area />`, `<NaoEncontrada />`, `<Casca />`, `ROTAS: RouteObject[]`.

- [ ] **Step 1: Escrever os testes (falhando)**

`picorte/web/src/paginas/PaginaArea.test.tsx`:

```tsx
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AREAS, CONFIGURACOES } from "../casca/areas";
import { LISTA_PADRAO, renderizar } from "../testes/fabrica";
import { PaginaArea } from "./PaginaArea";

const LIVES = AREAS[0];

afterEach(() => vi.unstubAllGlobals());

describe("PaginaArea", () => {
  it("diz em que história a página chega", () => {
    renderizar(<PaginaArea area={LIVES} />, { capacidades: LISTA_PADRAO });
    expect(screen.getByRole("heading", { level: 1, name: "Lives" })).toBeInTheDocument();
    expect(screen.getByText("Esta página chega na história 6.5")).toBeInTheDocument();
  });
  it("lista as funções reais da área: ligadas/parciais em linha, travadas em poço", () => {
    renderizar(<PaginaArea area={LIVES} />, { capacidades: LISTA_PADRAO });
    const linha = screen.getByText("Recentes pelo yt-dlp").closest("li")!;
    expect(linha).toHaveTextContent("Parcial");
    expect(linha).toHaveTextContent("sem chave da YouTube Data API");
    const poco = screen.getByRole("region", { name: "Em alta" });
    expect(poco).toHaveTextContent("Chega na história 5.1.");
  });
  it("carregando: esqueleto com nome", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    renderizar(<PaginaArea area={LIVES} />);
    expect(screen.getByRole("status", { name: "Carregando as funções" })).toBeInTheDocument();
  });
  it("erro: frase, detalhe recolhido e Tentar de novo", async () => {
    const buscar = vi.fn(async () => new Response('{"erro":"falhou"}', { status: 500 })); // um Response novo por chamada
    vi.stubGlobal("fetch", buscar);
    renderizar(<PaginaArea area={LIVES} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não consegui ler o status das funções.");
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    await waitFor(() => expect(buscar).toHaveBeenCalledTimes(2));
  });
  it("vazio: área sem funções medidas", () => {
    renderizar(<PaginaArea area={CONFIGURACOES} />, { capacidades: LISTA_PADRAO });
    expect(screen.getByText("Nenhuma função medida nesta área ainda.")).toBeInTheDocument();
  });
});
```

`picorte/web/src/rotas.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ROTAS } from "./rotas";
import { ESTADO_INICIAL_TEMPO_REAL, useTempoReal } from "./tempo-real/loja";
import { FonteFalsa } from "./testes/fonte-falsa";
import { LISTA_PADRAO } from "./testes/fabrica";

function backend() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.startsWith("/api/capacidades")) return new Response(JSON.stringify(LISTA_PADRAO));
    if (url.startsWith("/api/projetos")) return new Response(JSON.stringify({ projetos: [] }));
    return new Response('{"erro":"Não encontrado."}', { status: 404 });
  }));
}

function montar(rota = "/") {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const roteador = createMemoryRouter(ROTAS, { initialEntries: [rota] });
  render(<QueryClientProvider client={cliente}><RouterProvider router={roteador} /></QueryClientProvider>);
  return roteador;
}

beforeEach(() => useTempoReal.setState(ESTADO_INICIAL_TEMPO_REAL));
afterEach(() => vi.unstubAllGlobals());

describe("casca", () => {
  it("abre em Lives com a sidebar, as funções reais e o SSE ligado", async () => {
    backend();
    montar("/");
    expect(await screen.findByRole("heading", { level: 1, name: "Lives" })).toBeInTheDocument();
    expect(await screen.findByText("Recentes pelo yt-dlp")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Navegação principal" })).toBeInTheDocument();
    expect(FonteFalsa.ultimas.at(-1)?.url).toBe("/api/eventos");
  });
  it("g + s vai para Saúde", async () => {
    backend();
    const roteador = montar("/");
    await screen.findByRole("heading", { level: 1, name: "Lives" });
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "s" });
    expect(await screen.findByRole("heading", { level: 1, name: "Saúde" })).toBeInTheDocument();
    expect(roteador.state.location.pathname).toBe("/saude");
  });
  it("backend fora do ar: Picorte desligado, sem dado velho", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    montar("/fila");
    expect(await screen.findByText("O Picorte não está rodando neste computador.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Fila" })).not.toBeInTheDocument();
  });
  it("rota desconhecida", async () => {
    backend();
    montar("/nao-existe");
    expect(await screen.findByText("Esta página não existe.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para Lives" })).toHaveAttribute("href", "/");
  });
});
```

- [ ] **Step 2: Ver falhar**

Run: `npm --prefix picorte/web test`
Expected: FAIL (`./PaginaArea` e `./rotas` não existem).

- [ ] **Step 3: Implementar**

`picorte/web/src/paginas/PaginaArea.tsx`:

```tsx
import type { ReactNode } from "react";
import { capacidadesDaArea, useCapacidades } from "../api/capacidades";
import { ErroApi } from "../api/cliente";
import type { Capacidade } from "../api/tipos";
import type { Area } from "../casca/areas";
import { Carregando, ErroCarregar, Vazio } from "../ui/Estados";
import { Icone } from "../ui/Icone";
import { PocoTravado } from "../ui/PocoTravado";
import { StatusRotulo } from "../ui/StatusRotulo";
import { verificadoHa } from "../ui/tempo";

function LinhaCapacidade({ capacidade: c }: { capacidade: Capacidade }) {
  return (
    <li className="linha">
      <span className="font-semibold text-tinta">{c.titulo}</span>
      <StatusRotulo capacidade={c} />
      <span className="text-tinta-2">{c.status === "ligado" ? "" : c.motivo}</span>
      <span className="text-tinta-3 num">{verificadoHa(c.verificado_em)}</span>
    </li>
  );
}

/** Página de uma área até a sua história chegar: diz quando chega e mostra as funções reais dela. */
export function PaginaArea({ area }: { area: Area }) {
  const caps = useCapacidades();
  const funcoes = capacidadesDaArea(caps.data, area.areasCapacidade);
  const nomes = Object.fromEntries((caps.data?.capacidades ?? []).map((c) => [c.id, c.titulo]));
  const travadas = funcoes.filter((c) => c.status === "travado");
  const outras = funcoes.filter((c) => c.status !== "travado");
  const tentar = () => void caps.refetch();

  let corpo: ReactNode;
  if (caps.isPending) {
    corpo = <Carregando linhas={4} rotulo="Carregando as funções" />;
  } else if (caps.isError) {
    const detalhe = caps.error instanceof ErroApi ? caps.error.detalhe || caps.error.message : String(caps.error);
    corpo = <ErroCarregar frase="Não consegui ler o status das funções." detalhe={detalhe} onTentarDeNovo={tentar} />;
  } else if (funcoes.length === 0) {
    corpo = <Vazio frase="Nenhuma função medida nesta área ainda." />;
  } else {
    corpo = (
      <>
        {outras.length > 0 && (
          <ul className="linhas">{outras.map((c) => <LinhaCapacidade key={c.id} capacidade={c} />)}</ul>
        )}
        {travadas.length > 0 && (
          <div className="pocos">
            {travadas.map((c) => (
              <PocoTravado key={c.id} capacidade={c} nomesDependencias={nomes} onTentarDeNovo={tentar} />
            ))}
          </div>
        )}
      </>
    );
  }

  return (
    <div className="pagina">
      <header className="cabeca"><h1>{area.rotulo}</h1></header>
      <section className="espaco" aria-label="Página em construção">
        <p className="tt"><Icone nome="cad" pequeno />Esta página chega na história {area.historia}</p>
        <p className="falta">Por enquanto, esta é a lista real das funções desta área, com o status que o backend mediu.</p>
      </section>
      <h2 className="secao">Funções desta área</h2>
      {corpo}
    </div>
  );
}
```

`picorte/web/src/paginas/NaoEncontrada.tsx`:

```tsx
import { Link } from "react-router";
import { Vazio } from "../ui/Estados";

export function NaoEncontrada() {
  return (
    <div className="pagina">
      <Vazio frase="Esta página não existe.">
        <Link className="link-fraco" to="/">Voltar para Lives</Link>
      </Vazio>
    </div>
  );
}
```

`picorte/web/src/casca/Casca.tsx`:

```tsx
import { useCallback } from "react";
import { Outlet, useNavigate } from "react-router";
import { useCapacidades } from "../api/capacidades";
import { ErroApi } from "../api/cliente";
import { useProjetos } from "../api/projetos";
import { useEventos } from "../tempo-real/eventos";
import { PicorteDesligado } from "../ui/Estados";
import { useAtalhosGlobais } from "./atalhos";
import { Sidebar } from "./Sidebar";
import { useSidebar } from "./useSidebar";

const desligou = (erro: unknown) => erro instanceof ErroApi && erro.tipo === "desligado";

export function Casca() {
  const navegar = useNavigate();
  const sidebar = useSidebar();
  const caps = useCapacidades();
  const projetos = useProjetos();
  useEventos();
  const irPara = useCallback((rota: string) => void navegar(rota), [navegar]);
  useAtalhosGlobais({ irPara, alternarFixa: sidebar.alternarFixa });
  const desligado = desligou(caps.error) || desligou(projetos.error);

  return (
    <>
      <div className="app" data-empurra={sidebar.empurra}>
        <Sidebar aberta={sidebar.aberta} fixa={sidebar.fixa} eventos={sidebar.eventos}
          alternarFixa={sidebar.alternarFixa} capacidades={caps.data}
          projetos={projetos.data?.projetos} desligado={desligado} />
        <main className="principal" id="conteudo">
          {desligado ? <PicorteDesligado /> : <Outlet />}
        </main>
      </div>
      <div className="janela-pequena">Use uma janela maior: o Estúdio precisa de pelo menos 1280 px de largura.</div>
    </>
  );
}
```

`picorte/web/src/rotas.tsx`:

```tsx
import type { RouteObject } from "react-router";
import { TODAS_AREAS } from "./casca/areas";
import { Casca } from "./casca/Casca";
import { NaoEncontrada } from "./paginas/NaoEncontrada";
import { PaginaArea } from "./paginas/PaginaArea";

export const ROTAS: RouteObject[] = [
  {
    path: "/",
    element: <Casca />,
    children: [
      ...TODAS_AREAS.map((area): RouteObject =>
        area.rota === "/"
          ? { index: true, element: <PaginaArea area={area} /> }
          : { path: area.rota.slice(1), element: <PaginaArea area={area} /> }),
      { path: "*", element: <NaoEncontrada /> },
    ],
  },
];
```

`picorte/web/src/main.tsx` (substitui o provisório):

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";
import "./estilos/app.css";
import { ROTAS } from "./rotas";

const cliente = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } } });
const roteador = createBrowserRouter(ROTAS);

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <QueryClientProvider client={cliente}>
      <RouterProvider router={roteador} />
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 4: Rodar**

Run: `npm --prefix picorte/web test`, `npm --prefix picorte/web run check` e `npm --prefix picorte/web run build`
Expected:
- todos passam (55 + 5 + 4 = 64);
- tipos sem erro;
- build sem aviso de erro;
- `grep -c "<script>" picorte/web/dist/index.html` dá `0`.

- [ ] **Step 5: Sem commit.**

---

### Task 8: Verificação no navegador real e fechamento

**Files:**
- Create (scratchpad, fora do repo): `estudio-olhar.mjs` (playwright-core + Edge)
- Modify: `C:\Users\jffil\.claude\projects\c--Dev-projeto-cortes\memory\painel-estudio-do-criador.md` (estado da 6.3-B)

**Interfaces:**
- Consumes: o build de `picorte/web/dist` e o `estudio.py` (6.3-A).
- Produces: capturas de tela verificadas; suíte Python do Estúdio sem regressão.

- [ ] **Step 1: Subir o Estúdio numa pasta isolada**

Run (em segundo plano), com `<scratchpad>` sendo o diretório de scratchpad da sessão:

```
python estudio.py --pasta-projetos <scratchpad>/projetos-vazios --porta 8771 --sem-navegador
```

Antes, para ter um projeto rodando, crie à mão (só no scratchpad) `<scratchpad>/projetos-vazios/aaaaaaaaaaaa/project.json` com:

```json
{"id": "aaaaaaaaaaaa", "status": "complete", "stage": "complete", "created": 1, "progress": {}}
```

Expected: `curl -s http://127.0.0.1:8771/ | grep -c 'id="raiz"'` dá `1`, e `curl -s http://127.0.0.1:8771/fila` também devolve o `index.html` (fallback de SPA).

- [ ] **Step 2: Capturar as telas com o Edge**

`<scratchpad>/estudio-olhar.mjs` (rodar com `node` numa pasta do scratchpad com `npm install playwright-core@1.65.1`):

```js
import { chromium } from "playwright-core";

const base = "http://127.0.0.1:8771";
const saida = process.argv[2];
const navegador = await chromium.launch({ channel: "msedge" });
const erros = [];

async function tela(nome, caminho, { largura = 2560, altura = 1440, tema = "dark", acao } = {}) {
  const pagina = await navegador.newPage({ viewport: { width: largura, height: altura } });
  pagina.on("console", (m) => m.type() === "error" && erros.push(`${nome}: ${m.text()}`));
  pagina.on("pageerror", (e) => erros.push(`${nome}: ${e.message}`));
  await pagina.addInitScript((t) => localStorage.setItem("picorte-tema", t), tema);
  await pagina.goto(base + caminho, { waitUntil: "networkidle" });
  if (acao) await acao(pagina);
  await pagina.waitForTimeout(400);
  await pagina.screenshot({ path: `${saida}/${nome}.png` });
  await pagina.close();
}

await tela("lives-escuro", "/");
await tela("lives-claro", "/", { tema: "light" });
await tela("sidebar-aberta", "/", { acao: (p) => p.hover("nav.side") });
await tela("saude", "/saude");
await tela("aprendizado-travado", "/aprendizado");
await tela("config-vazio", "/config");
await tela("janela-pequena", "/", { largura: 1200, altura: 800 });
await navegador.close();
console.log(erros.length ? erros.join("\n") : "sem erros no console");
```

Run: `node <scratchpad>/estudio-olhar.mjs <scratchpad>/telas`
Expected: `sem erros no console`. **Nenhum erro de CSP** (`Refused to …`). As 7 imagens existem.

- [ ] **Step 3: Olhar as telas (Read em cada PNG) e conferir**

Checklist, com correção na hora do que falhar:
- fonte Onest carregada (não a do sistema);
- sidebar de 72 px recolhida, com ícones, a contagem só quando há job e cadeado em Aprendizado e Radar;
- aberta: 264 px por cima do conteúdo, com rótulos e pé com GPU, Ollama, Gemini, Claude, tempo real "conectado" e alerta de Sistema **se** o disco estiver abaixo do limite;
- poço "Esta página chega na história X" rebaixado, e funções em linhas com ícone + palavra;
- travadas em poço sem nenhum número de dado;
- tema claro com cinzas neutros e laranja só como sinal;
- 1200 px mostra só "Use uma janela maior…".

- [ ] **Step 4: Testar o estado "desligado" no navegador**

Com a página aberta em `/fila` (script parecido, mantendo a página viva), pare o servidor da 8771 e espere a próxima leitura (focar a janela dispara `refetchOnWindowFocus`, ou use `page.evaluate(() => window.dispatchEvent(new Event("focus")))`).

Expected:
- aparece "O Picorte não está rodando neste computador." com `python estudio.py`;
- o pé da sidebar mostra "Picorte · desligado".

Suba o servidor de novo e confirme que a página volta sozinha (o SSE reconecta, chega o `ola` e tudo é relido).

- [ ] **Step 5: Regressão do backend e da suíte web**

Run:
- `npm --prefix picorte/web test` e `npm --prefix picorte/web run check`;
- `python -m pytest tests/test_estudio_*.py -q`.

Expected: 64 testes web passando; tipos sem erro; os 75 testes Python do Estúdio passando.

Pare o servidor da 8771.

- [ ] **Step 6: Atualizar a memória do projeto**

Em `painel-estudio-do-criador.md`, acrescente:
- a 6.3-B implementada (sem commit), com o plano em `docs/superpowers/plans/2026-11-22-6-3b-casca-estudio-spa.md`;
- o front em `picorte/web/` (build em `dist/`, ignorado no git);
- os comandos do `LEIAME.md`;
- a pegadinha da CSP (sem inline e `assetsInlineLimit: 0`);
- os stubs do jsdom: `matchMedia`, `ResizeObserver`, `getAnimations` e `EventSource`.

- [ ] **Step 7: Sem commit.** Relatar ao dono: testes, capturas e o que ficou para a 6.5.

---

## Desvios na execução (2026-11-22)

1. **Versões:**
   - **O que mudou:** `react-router` 8.5.2 → **7.18.6** e `jsdom` 31.0.1 → **29.1.1**.
   - **Por quê:** os dois exigem Node ≥ 22.22, e esta máquina tem o 22.19.
   - **Efeito:** a API usada é a mesma.
2. **`npm --prefix picorte/web install` não funciona:**
   - **O que acontece:** o npm lê o `package.json` da pasta atual.
   - **Correção:** instalar com `cd picorte/web && npm install`. O `LEIAME.md` já diz isso.
3. **Vitest com o drive minúsculo:**
   - **O problema:** no Windows, com o terminal em `c:\` (VS Code), o Vitest 5 carrega duas cópias de si e falha com "failed to find the current suite".
   - **Correção:** o script `test` passou a ser `node scripts/vitest.mjs run`. Esse lançador roda o Vitest com a letra do drive maiúscula; no Linux ele não faz nada.
4. **Pé da sidebar:**
   - **O problema:** o texto da GPU passava da borda.
   - **Correção:** reticências em `.sl .rot` e o texto completo no `title`.
5. **Poço travado:**
   - **O problema:** o cadeado aparecia duas vezes.
   - **Correção:** ele saiu do título e ficou só na linha de status, como diz o `DESIGN.md`.
6. **Linhas ligadas:** passaram a mostrar o `motivo` medido pela sonda (por exemplo "57.0 GiB livres"). Antes ele sumia.
7. **Defeito achado no navegador:**
   - **O problema:** com o servidor fora do ar, o "Picorte desligado" levava até 2 min para aparecer. A detecção dependia do `refetchInterval`, e o TanStack Query 5 não escuta o evento `focus`.
   - **Correção:** o `error` do SSE agora relê as capacidades na hora (há teste para isso).
   - **Medido no Edge:** "desligado" em cerca de 5 s; a página volta sozinha cerca de 13 s depois que o servidor sobe.

## Autoavaliação (feita ao escrever o plano)

**Cobertura da AC 7 e das regras:**

| Requisito | Onde está |
|---|---|
| Navegação | Tasks 5 e 7: sidebar, `ROTAS` e `g` + letra |
| Vazio, carregando, erro e travado desenhados | Tasks 3 e 7: `Vazio`, `Carregando`, `ErroCarregar` e `PocoTravado` em `PaginaArea` |
| Picorte desligado | Tasks 3 e 7 |
| Capacidades ilegíveis | Task 2 (`ilegivel`) e Task 5 (pé da sidebar) |
| Sidebar autorretrátil, sem empurrar, alfinete `[` lembrado | Task 5 |
| Estado do sistema no pé (anel real e marcas de forma) | Task 5 |
| Tempo real e "Reconectando…" | Tasks 4 e 5 |
| Status nunca só por cor | Tasks 3 e 5 |
| `aria-live` no progresso | Task 5 |
| Reduced motion | Task 1 (CSS) |
| Só desktop (< 1280 px) | Tasks 1 e 7 |
| CSP | Tasks 1, 7 e 8 |
| C4 (Windows e Linux) | `PicorteDesligado` e comandos npm sem shell |

**Sem marcadores pendentes:** todo passo de código tem código.

**Tipos consistentes:**
- `Capacidade`/`ListaCapacidades`/`Projeto` iguais em todas as tarefas;
- `useSidebar().eventos` bate com `Sidebar.Props.eventos`;
- `ICONE_DO_ROTULO`/`TOM_DO_ROTULO` exportados na Task 3 e usados na Task 5;
- `renderizar`/`LISTA_PADRAO` definidos nas Tasks 3 e 5 antes do uso nas Tasks 5 e 7;
- `fabrica.ts` vira `fabrica.tsx` na Task 3.
