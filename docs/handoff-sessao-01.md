# Handoff — Sessão 01 (2026-11-16)

Você está assumindo um projeto que começou em outra sessão. Leia tudo antes de agir. Responda sempre em português do Brasil.

## 1. O que estamos construindo

Uma ferramenta nova (codinome **projeto-cortes**; nome final ainda será escolhido numa etapa própria de naming) que:

1. **Gera cortes automaticamente** a partir de vídeos longos (podcasts, lives, entrevistas): transcrição → detecção de ganchos/trechos bons → corte → reenquadramento 9:16 com rastreamento de rosto → legenda.
2. **Avalia e importa cortes já existentes** (feitos por terceiros/outras ferramentas), dá nota e coloca na fila.
3. **Publica em várias redes ao mesmo tempo**: YouTube Shorts, YouTube (cortes longos de 3–5 min), TikTok, Instagram Reels, Facebook.
4. **Aprende o que performa** (módulo de inteligência): coleta métricas, descobre que temas/ganchos/durações/horários dão resultado e passa a gerar mais disso.

Objetivo do usuário: ganhar dinheiro com cortes. **Decisão firme do usuário: não pagar nenhuma ferramenta de autoclip (Opus Clip, Klap etc.). Vamos construir a detecção de bons cortes nós mesmos, inclusive treinando modelos próprios se necessário.**

## 2. Decisões e conclusões já tomadas

### Modelo de negócio / risco de direitos autorais
- Canais de cortes existem porque: têm autorização do criador; o Content ID redireciona a receita ao dono; ganham fora do YouTube (campanhas de clipping pagas por mil views, contratos com criadores); ou foram aprovados no YPP por agregar edição real. Há viés de sobrevivência.
- O usuário aceita o risco de postar cortes, **mas exige gestão de risco completa**. Requisito obrigatório — "módulo de segurança":
  - cadastro da fonte com status de permissão (liberado publicamente / contrato / campanha de clipping / desconhecido);
  - crédito automático ao canal original;
  - monitor de reivindicações/strikes nos vídeos publicados;
  - **pausa automática** de todos os cortes de uma fonte em todas as redes ao primeiro claim de bloqueio/strike;
  - lista negra de fontes;
  - não concentrar tudo num só canal (separar por nicho);
  - transformação real nos cortes (gancho/título próprio, legenda, contexto) — ajuda no YPP e na retenção;
  - termos de uso transferindo responsabilidade, se virar SaaS.
- Campanhas de clipping são uma fonte de receita a integrar.

### Restrições técnicas já identificadas
- YouTube Data API: upload custa 1600 unidades de 10.000/dia (~6 uploads/dia/projeto); app não auditado publica só como privado.
- TikTok Content Posting API: sem auditoria, só posta privado.
- Instagram/Facebook: exige conta Business/Creator ligada a Página; Reels via Graph API; limite diário.
- Baixar vídeo do YouTube via yt-dlp viola os ToS do YouTube (registrar como risco a decidir).
- Nunca guardar senhas das redes — sempre OAuth/tokens.
- O "cérebro" precisa de volume de dados; proposta inicial: multi-armed bandit (Thompson sampling) sobre características (tema × tipo de gancho × duração × horário × rede), recompensa = performance normalizada pela mediana do canal, ~20% de exploração. LLM gera/rotula cortes; bandit decide prioridade.

### Arquitetura preliminar (a ser validada pelo arquiteto do BMAD)
Frontend → API (Node) → Supabase (Postgres + Storage) → fila de jobs → workers: vídeo (Python: faster-whisper, ffmpeg, MediaPipe, LLM), publicador (OAuth por rede, retry), métricas (snapshots 1h/24h/7d). Tabelas: fontes → cortes → publicacoes → metricas.

## 3. Processo de modelagem escolhido

O usuário quer algo equivalente ao repositório `Donchitos/Claude-Code-Game-Studios` (pilares, anti-pilares, art bible, fases com portões), mas para uma ferramenta/SaaS. Escolhemos o **BMAD Method**.

Divisão de responsabilidades (precisa ir para o CLAUDE.md, para evitar que frameworks disputem o controle — o brainstorming do superpowers tenta assumir qualquer trabalho criativo):
- **BMAD** lidera descoberta, planejamento e arquitetura (product brief, PRD, UX, arquitetura, épicos/histórias).
- **impeccable** lidera marca, paleta, design system (papel do "art bible").
- **Skills próprias** (criadas com o BMad Builder / skill-creator) para o que nenhum framework cobre:
  1. pilares e anti-pilares do produto;
  2. pipeline de ML (dataset, rotulagem "corte bom × ruim" a partir de métricas reais, métricas de avaliação, experimentos);
  3. integrações por plataforma (OAuth, cotas, auditoria, limites);
  4. módulo de segurança/risco de direitos autorais;
  5. naming e marca (critérios, domínio, INPI).
- **superpowers** lidera a implementação (planos, TDD, subagentes, code review, verificação).
- **claude-api** para o módulo de IA.

A modelagem fica em **Markdown dentro do repositório**. Se precisar mostrar a terceiros, gera-se uma versão compartilhável depois.

## 4. Estado atual do repositório

- Pasta: `/home/bomba/Área de trabalho/FRELA/projeto-cortes` — `git init` feito, **nenhum commit ainda**.
- **BMAD v6.12.4** (estável; v7 ainda em preview — não usar) instalado com módulos: bmm (Method), bmb (Builder 2.2.2), cis (Creative Intelligence 0.3.2), tea (Test Architect 1.27.2), bmad-loop (0.13.2). Fora: gds (jogos), automator e wds (descontinuados). O módulo "Founder" só existe na v7.
- 57 skills em `.claude/skills`. Config em `_bmad/config.toml` (docs em português) e `_bmad/config.user.toml` (comunicação em português, nível intermediário).
- **Pendente:** `bmad-loop-setup` — adiado de propósito para a fase de implementação (instala orquestrador e hooks).
- `.gitignore` criado (configs pessoais do BMAD, .env, node_modules).

## 5. Legado (ReSocial)

**Versão de referência (confirmada pelo usuário):** `/home/bomba/Área de trabalho/FRELA/ReSocial_sem_firebase`. Repositório git próprio; último commit `d5091e2 feat: build de demonstração pronto para hospedar`.

> A cópia em `~/Downloads/ReSocial_sem_firebase` é **obsoleta** (julho; HTML/JS solto, SQLite × Supabase, senhas em texto puro). Ignore-a. As críticas feitas a ela na sessão 01 **não se aplicam** à versão de FRELA, que já é OAuth/credenciais revogáveis, cifra segredos e tem agendador durável.

### O que a versão de FRELA já tem
- **Monorepo npm workspaces** (Node ≥ 24): `shared/` (regras de redes e datas, com testes), `web/`, `server/`. Docker, docker-compose (Postgres), Makefile, `vercel.json`, scripts de smoke (`scripts/smoke-*.mjs`).
- **Backend** `server/`: TypeScript + **Fastify 5** + **PostgreSQL** (`pg`, migrações próprias em `db/migrate.ts`), Vitest com ~15 suítes. Módulos: `auth` (sessão, reset de senha, mailer), `accounts` (contas conectadas), `media` (storage + `encolher` para redimensionar imagem), `analytics`, `posts`. **Agendador durável** (`scheduler/worker.ts`, `cleanup.ts`) e **coletor de métricas** (`scheduler/coletor.ts`). Publicadores plugáveis (`publishers/registry.ts`, `types.ts`): **Telegram e Bluesky reais**, demais simulados. Segredos cifrados (`lib/crypto.ts`).
- **Frontend** `web/`: **Vite 8 + React 19 + React Router 7**. Telas: Landing, Home, Compose, Review, Agenda, PostDetail, Accounts, Results (com gráfico de evolução), Profile, EditProfile, Legal. Modo demonstração e modo servidor pelo mesmo contrato (`web/src/data/api.js`). Design tokens em `web/src/styles/tokens.css`.
- **Documentação**: `PRODUCT.md` e `DESIGN.md` (formato do impeccable, `.impeccable/design.json`), README de 50 KB, spec e plano do backend feitos com superpowers em `docs/superpowers/`.

### Atenção ao contexto do ReSocial
O `PRODUCT.md` descreve o ReSocial como **projeto escolar, sem fins lucrativos**, para pequenos vendedores postarem produtos, priorizando redes gratuitas sem revisão de app (Telegram, Bluesky). A ferramenta nova é **comercial**, focada em **vídeo/cortes**, e precisa das redes que exigem revisão (YouTube, TikTok, Meta). Ou seja: público, redes prioritárias, marca e identidade (roxo do ReSocial) **não** se herdam.

### O que provavelmente se reaproveita (validar na modelagem/arquitetura)
- Arquitetura do backend: Fastify + Postgres, módulos auth/accounts/media, agendador durável, coletor de métricas, registro de publicadores plugáveis, cifragem de segredos, padrão de testes e smoke tests.
- Infra: Docker/compose, Makefile, workspaces.
- Fluxo compor → revisar → agendar → acompanhar resultados, e o padrão demo/servidor no front.
- Princípios do `PRODUCT.md` que continuam valendo: "conectar, não coletar" (nunca pedir senha de rede), "nada sai errado" (revisão antes de publicar), honestidade sobre o que cada rede permite, pt-BR claro.
- **Não** se reaproveita: nome, paleta, logotipo, `DESIGN.md` (a ferramenta nova terá identidade própria, feita com impeccable).

Observação: `server/.env` e `web/.env.local` existem nessa pasta — não copiar segredos para o projeto novo.

## 6. Próximos passos (nesta ordem)

1. Ler: este arquivo, `_bmad/config.toml`, a lista de skills em `.claude/skills`, e `PRODUCT.md`, `DESIGN.md` e o README do ReSocial em FRELA.
2. Confirmar ao usuário, em poucas linhas, o que entendeu, e tirar dúvidas pendentes.
3. Escrever o **CLAUDE.md** do projeto com: visão do produto em um parágrafo, divisão de liderança por fase (seção 3), idioma, regra de não commitar sem pedir, requisitos firmes (módulo de risco, nada de autoclip pago, OAuth).
4. Escrever o **Plano Mestre** em `docs/plano-mestre.md`: cada etapa, do nome à conclusão — naming → pilares/anti-pilares → marca/design system → product brief → PRD → UX → arquitetura → ML → integrações → módulo de risco → épicos/histórias → implementação → testes → lançamento. Para cada etapa: skill/agente responsável (dos instalados ou outros, sempre procurando os melhores), documento gerado (com caminho), critério de saída para a próxima etapa.
5. Só então começar a executar a primeira etapa.

## 7. Preferências do usuário

- Fala português; quer explicações diretas e honestas, inclusive quando a resposta não é a que ele quer ouvir.
- Quer documentação detalhada de ponta a ponta antes de codar.
- Quer as melhores skills para cada etapa, não só as que já estão instaladas.
- Commits e ações irreversíveis só com autorização.
