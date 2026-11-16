# Plano Mestre — projeto-cortes

> Versão 1 · 2026-11-16 · Mantido em `docs/plano-mestre.md`. Atualize este arquivo quando uma etapa terminar ou quando uma decisão mudar a ordem.

Este plano cobre o caminho inteiro, do nome ao lançamento. Para cada etapa ele diz: **quem lidera** (skill ou agente), **o que entra**, **o que sai** (documento e caminho) e o **critério de saída**, que é a condição para começar a próxima. Uma etapa só termina quando você aprova o critério de saída.

Regras gerais (detalhes no `CLAUDE.md`):
- Toda etapa que custa dinheiro tem estimativa **antes** de ser executada. Os valores deste plano são ordens de grandeza para orçamento; preços de API, nuvem e taxas são confirmados com a fonte oficial no dia em que forem usados.
- **Ao entrar em cada etapa**, procurar skills de terceiros melhores do que as instaladas (`find-skills` e busca na web). Para cada candidata, apresentar uma ficha (o que faz, origem, mantenedor, o que executa) e instalar só com aprovação.
- **Skills próprias** são criadas na própria etapa que precisa delas, com `bmad-workflow-builder` (skills de processo) ou `bmad-agent-builder` (agente especialista). O fonte fica em `skills/` e a skill é instalada em `.claude/skills/`. Usar `skill-creator` / `bmad-eval-runner` para testar a skill antes de confiar nela.
- Ao fim de cada sessão longa: `docs/handoff-sessao-NN.md`.

---

## Visão geral

```
FASE A — FUNDAÇÃO E IDENTIDADE
  E0 Fundação ─► E1 Pilares ─► E2 Naming ─► E3 Marca/Design system
                                   │
                                   └──► T1 Trilha paralela: contas de dev + auditorias (corre até E15)
FASE B — PRODUTO
  E4 Product brief ─► E5 PRD ─► E6 UX
FASE C — ESPECIFICAÇÕES DE DOMÍNIO
  E7 Integrações ─► E8 Risco/direitos ─► E9 ML e inteligência
FASE D — ARQUITETURA E QUEBRA
  E10 Arquitetura ─► E11 Estratégia de testes ─► E12 Épicos/histórias + prontidão
FASE E — CONSTRUÇÃO
  E13 Implementação (por épico) ─► E14 Verificação/NFR
FASE F — OPERAÇÃO
  E15 Lançamento interno (canais próprios) ─► E16 Operação e aprendizado
FASE G — FUTURO (fora do MVP)
  E17 Abertura como SaaS
```

**Mudança em relação ao handoff:** o handoff colocava a arquitetura **antes** das especificações de ML, integrações e risco. Aqui elas vêm **antes** da arquitetura (Fase C). A arquitetura precisa conhecer as cotas e auditorias de cada rede, o fluxo de pausa automática do módulo de risco e o modelo de dados do ML (features, recompensa, snapshots). Se fosse desenhada antes, voltaria para retrabalho. Essas specs são de domínio (o quê e por quê); as decisões técnicas (como) continuam com a arquitetura.

---

## FASE A — Fundação e identidade

### E0 · Fundação ✅ (em curso nesta sessão)
- **Líder:** sessão principal (Claude Code).
- **Entregáveis:** BMAD v6.12.4 instalado; `_bmad/custom/config.toml` (pt-BR e artefatos do TEA em `_bmad-output/test-artifacts`); `CLAUDE.md`; este plano; `.gitignore`.
- **Saída:** você aprova `CLAUDE.md` e este plano → **primeiro commit** (só quando você pedir).
- **Custo:** zero.

### E1 · Pilares e anti-pilares
- **Líder:** skill própria **`cortes-pilares`**, criada com `bmad-workflow-builder`. Apoio: `bmad-forge-idea` (testar ideias sob pressão), `bmad-advanced-elicitation` (pre-mortem, red team) e `bmad-party-mode` (vários pontos de vista).
- **Entra:** handoff, requisitos firmes do `CLAUDE.md`, o que já se sabe dos cortes.
- **Sai:** `_bmad-output/planning-artifacts/pilares.md`, com:
  - 3–5 pilares (o que o produto **precisa** ser), cada um com o teste "isto reforça o pilar?";
  - 3–5 anti-pilares (o que ele **nunca** será, por exemplo "nunca publica sem a fonte ter status de permissão");
  - público-alvo atual (você, operador de vários canais) e futuro (SaaS);
  - critérios de "corte bom" em linguagem de produto (base para o ML).
- **Critério de saída:** toda decisão futura pode ser julgada contra os pilares; você aprova o documento.
- **Custo:** zero.

### E2 · Naming
- **Líder:** skill própria **`cortes-naming`** (critérios, geração, filtro, checagens). Apoio: `bmad-cis-agent-storyteller` (Sophia) e `bmad-brainstorming` para gerar nomes; `bmad-deep-recon` para pesquisar conflitos.
- **Entra:** `pilares.md`.
- **Sai:** `_bmad-output/planning-artifacts/naming.md`, com:
  - critérios (pronúncia em pt-BR, funciona em inglês, não descreve só "cortes" para não limitar o SaaS, curto);
  - lista longa → lista curta → finalista;
  - checagens do finalista: domínio `.com.br`/`.com`, @ nas cinco redes, busca de anterioridade no INPI (classes 9, 35, 42), busca na web.
- **Critério de saída:** nome escolhido, domínio registrado, @ reservados nas redes.
- **Custo:**
  - domínio `.com.br`: ~R$ 40/ano (registro.br); `.com`: ~US$ 10–15/ano;
  - INPI: **busca** de anterioridade é grátis. O **pedido** de registro tem taxas (há desconto para pessoa física/MEI); pode ser adiado até abrir como SaaS. Consultar a tabela vigente antes de pagar.

### T1 · Trilha paralela — contas de desenvolvedor e auditorias ⏱️
Começa assim que existir **nome + domínio** (fim da E2) e corre em paralelo até a E15. É a trilha mais lenta do projeto e não depende de código no início.

- **Líder:** skill própria **`cortes-integracoes`** (criada no início da T1, reutilizada na E7).
- **Passos:**
  1. **Agora (sem código):** projeto no Google Cloud com tela de consentimento OAuth; app de desenvolvedor no TikTok; app na Meta e conta Business. Iniciar a **verificação de empresa da Meta** (pode exigir CNPJ; avaliar se abrir um MEI vale a pena).
  2. **Página pública mínima no domínio:** política de privacidade e termos de uso simples, para uso próprio. **Atenção:** isso é diferente dos termos de SaaS (E17). As três plataformas exigem essas URLs mesmo para app de uso próprio.
  3. **Assim que o publicador real de cada rede funcionar (épico de integrações, E13):** gravar o vídeo de demonstração e submeter as auditorias: YouTube (verificação do escopo `youtube.upload` + auditoria de API para aumento de cota e publicação pública), TikTok (auditoria do Content Posting API) e Meta (App Review de `instagram_content_publish` e permissões de Página).
- **Sai:** `_bmad-output/planning-artifacts/auditorias.md`: checklist por rede, status, datas de submissão e respostas, e o que cada plataforma pediu.
- **Critério de saída (para a E15):** pelo menos YouTube aprovado para publicação pública; TikTok e Meta aprovados ou com plano B documentado (publicar manualmente o arquivo gerado).
- **Custo:** as auditorias são gratuitas. Domínio já pago. Hospedar a página estática: grátis (Vercel/Cloudflare Pages). MEI, se for aberto: DAS mensal (consultar o valor vigente).
- **Implicação no plano:** o épico de **publicação no YouTube** deve ser um dos primeiros da E13, para a auditoria começar cedo.

### E3 · Marca e design system
- **Líder:** **impeccable**. Apoio: `bmad-agent-ux-designer` (Sally) para alinhar com a UX.
- **Entra:** `pilares.md`, `naming.md`.
- **Sai (formato impeccable):** `PRODUCT.md` e `DESIGN.md` na raiz, `.impeccable/design.json`, logotipo em SVG, paleta, tipografia e tokens (`tokens.css`). Nada herdado do ReSocial.
- **Critério de saída:** design system aprovado, com um mock de tela-chave (fila de cortes) e o logotipo legível em 32 px.
- **Custo:** zero. As fontes devem ter licença livre (Google Fonts / OFL).

---

## FASE B — Produto

### E4 · Product brief
- **Líder:** `bmad-product-brief` (Mary, `bmad-agent-analyst`). Apoio: `bmad-deep-recon` para pesquisa de mercado (ferramentas de autoclip como referência de funcionalidade, campanhas de clipping pagas por mil views, economia de canais de cortes, regras de monetização do YPP para conteúdo reutilizado).
- **Entra:** pilares, naming, handoff.
- **Sai:** `_bmad-output/planning-artifacts/product-brief.md` e `_bmad-output/planning-artifacts/pesquisa-mercado.md`.
- **Critério de saída:** problema, público, proposta de valor, fontes de receita (YPP, campanhas de clipping, contratos com criadores) e metas mensuráveis do MVP aprovadas.
- **Custo:** zero (busca web da sessão).

### E5 · PRD
- **Líder:** `bmad-prd` (John, `bmad-agent-pm`). Validação: modo "validar" do `bmad-prd` + `bmad-review`.
- **Entra:** product brief.
- **Sai:** `_bmad-output/planning-artifacts/prd.md`: requisitos funcionais (gerar cortes, importar e avaliar, fila, revisão, publicar, métricas, inteligência, risco), requisitos não funcionais (custo, worker offline, multi-tenant, segurança), escopo do MVP × futuro (o SaaS fica explicitamente fora).
- **Critério de saída:** PRD validado, cada requisito rastreável a um pilar, MVP fechado.
- **Custo:** zero.

### E6 · UX
- **Líder:** `bmad-ux` (Sally). Visual: **impeccable** (aplica o design system nos fluxos).
- **Entra:** PRD, design system.
- **Sai:** `_bmad-output/planning-artifacts/ux-design.md`: jornadas (vídeo longo → cortes na fila → revisão → publicação → resultados; claim recebido → pausa → decisão), mapa de telas, estados vazios e de erro, mocks das telas principais.
- **Critério de saída:** todos os fluxos do MVP desenhados, inclusive o de risco; você aprova os mocks.
- **Custo:** zero.

---

## FASE C — Especificações de domínio

### E7 · Integrações por plataforma
- **Líder:** skill própria **`cortes-integracoes`** (criada na T1).
- **Entra:** PRD, `auditorias.md`, documentação oficial atual de cada API (pesquisada na hora, não de memória).
- **Sai:** `_bmad-output/planning-artifacts/spec-integracoes.md`. Para cada rede (YouTube, YouTube Shorts, TikTok, Instagram Reels, Facebook): fluxo OAuth por workspace, escopos, cotas e custo por chamada, limites diários, formatos aceitos (duração, resolução, tamanho), o que acontece sem auditoria, métricas que a API devolve (base do coletor), como detectar claims e strikes (base do módulo de risco), renovação de token, erros e retry.
- **Critério de saída:** tabela "o que cada rede permite" completa e honesta; cálculo de quantos uploads por dia cabem por canal e por projeto GCP; decisão sobre quantos projetos GCP usar.
- **Custo:** zero.

### E8 · Módulo de risco e direitos autorais
- **Líder:** skill própria **`cortes-risco`**. Apoio: `bmad-advanced-elicitation` (red team, pre-mortem) e `bmad-deep-recon` (políticas atuais de Content ID, reutilização de conteúdo e strikes de cada rede).
- **Entra:** PRD, spec de integrações, requisitos firmes do `CLAUDE.md`.
- **Sai:** `_bmad-output/planning-artifacts/spec-risco.md`:
  - ciclo de vida da fonte (status de permissão, lista negra) e ciclo de vida do claim;
  - regra de pausa automática (gatilhos, alcance "todas as redes", reversão manual);
  - crédito automático (formato por rede);
  - critérios mínimos de "transformação real" que todo corte precisa cumprir antes de ir para a fila;
  - separação de canais por nicho;
  - **decisão sobre o yt-dlp:** aceitar o risco, usar só arquivos fornecidos/autorizados ou um modo misto, com consequências escritas;
  - matriz de riscos (probabilidade × impacto × mitigação).
- **Critério de saída:** toda fonte e todo corte têm estado de risco definido; o fluxo de pausa está especificado de ponta a ponta; a decisão do yt-dlp está tomada por você.
- **Custo:** zero.

### E9 · ML e inteligência
- **Líder:** skill própria **`cortes-ml`** (dataset, rotulagem, métricas, experimentos). Apoio: **claude-api** (escolha de modelo, prompts, custo) e `bmad-deep-recon` (estado da arte em detecção de destaques e ganchos).
- **Entra:** PRD, pilares (critérios de corte bom), spec de integrações (métricas disponíveis).
- **Sai:** `_bmad-output/planning-artifacts/spec-ml.md`:
  - **pipeline de geração:** transcrição (faster-whisper large-v3) → segmentação → candidatos a gancho → pontuação → corte → reenquadramento (rastreamento de rosto) → legenda;
  - **avaliação de cortes de terceiros:** a mesma pontuação aplicada a cortes importados;
  - **comparação LLM API × LLM local 7–8B × híbrido** (o local faz a triagem, a API decide), com qualidade medida num conjunto de teste próprio. A 4060 Ti não roda o LLM local e o whisper ao mesmo tempo, então o pipeline serializa os dois;
  - **dataset e rotulagem:** rótulo "bom × ruim" derivado de métricas reais (retenção, views normalizadas pela mediana do canal), snapshots de 1h/24h/7d;
  - **bandit:** Thompson sampling sobre tema × tipo de gancho × duração × horário × rede, ~20% de exploração, recompensa normalizada; quando o volume justifica treinar modelos próprios (classificador, LoRA);
  - métricas de avaliação offline e online, e como rodar experimentos.
- **Critério de saída:** escolha do LLM (ou híbrido) justificada com números de qualidade e custo; **teto mensal** de gasto com LLM definido por você.
- **Custo (estimativa a fechar nesta etapa):**
  - 1 h de vídeo falado ≈ 9–10 mil palavras ≈ **20–40 mil tokens de entrada** (transcrição com timestamps) + alguns milhares de tokens de saída por passada;
  - custo por vídeo = tokens × preço vigente do modelo escolhido (consultado com `claude-api` na hora). Precisa sair desta etapa como **R$ por hora de vídeo** e **R$/mês** no volume previsto;
  - LLM local: zero de API, só energia (ver E13).

---

## FASE D — Arquitetura e quebra

### E10 · Arquitetura
- **Líder:** `bmad-architecture` (Winston, `bmad-agent-architect`). Apoio: **claude-api** (módulo de IA); `bmad-review` para revisão adversarial do documento.
- **Entra:** PRD, UX, specs E7–E9, código do ReSocial em FRELA (só leitura).
- **Sai:** `_bmad-output/planning-artifacts/architecture.md`, com as decisões:
  - **fork do ReSocial:** o que entra (provavelmente Fastify, Postgres, auth, accounts, media, agendador, coletor, registro de publicadores, crypto, Vitest, Docker, Makefile, workspaces) e o que sai, cada item justificado; sem `.env` nem segredos;
  - **topologia:** API, banco, storage e agendador na nuvem; **workers puxam jobs da fila** (o PC de mesa é o primeiro). Worker desligado = fila esperando, sem perda. Um worker com GPU alugada se encaixa sem mudar nada. Definir a fila (por exemplo, a tabela de jobs do agendador do ReSocial ou outra solução) e o protocolo de lease/heartbeat/retry;
  - **multi-tenant:** `workspace_id` em todas as tabelas de domínio, OAuth por workspace, isolamento por consulta ou RLS;
  - **storage de vídeo:** o original fica no worker; só os cortes sobem. Política de retenção;
  - Supabase × Postgres próprio (o ReSocial usa Postgres puro);
  - modelo de dados: workspaces → fontes → vídeos → cortes → publicações → métricas → claims;
  - frontend novo (stack e o padrão demonstração/servidor herdado);
  - convenções de código e de idioma do código.
- **Critério de saída:** a arquitetura passa no check de prontidão (`bmad-sprint-planning`, modo "check implementation readiness"); **planilha de custo mensal** do MVP aprovada.
- **Custo (estimativa a fechar nesta etapa):**
  - hospedagem de API + agendador: plano básico de PaaS, ~US$ 5–25/mês;
  - Postgres gerenciado: free tier no início; plano pago ~US$ 25/mês se precisar;
  - storage dos cortes: ~20–60 MB por corte. 1.000 cortes ≈ 20–60 GB; estimar a retenção;
  - energia do PC de mesa: ~250 W sob carga × 4 h/dia ≈ 30 kWh/mês ≈ **R$ 25–35/mês** (conferir a tarifa local);
  - GPU alugada: só acima da capacidade do PC. Ordem de US$ 0,30–0,80/h numa GPU de 24 GB (confirmar preços na hora). Definir o gatilho em vídeos/dia.

### E11 · Estratégia de testes
- **Líder:** BMAD TEA: `bmad-testarch-test-design` (nível de sistema), `bmad-testarch-framework`, `bmad-testarch-ci`.
- **Entra:** arquitetura, PRD.
- **Sai:** `_bmad-output/test-artifacts/test-design/…`, framework de testes configurado e pipeline de CI desenhado. Riscos P0/P1 mapeados, especialmente: pausa automática, isolamento de tenant, tokens cifrados e idempotência da publicação.
- **Critério de saída:** cada risco P0/P1 tem um teste planejado.
- **Custo:** CI no plano gratuito do GitHub Actions (os jobs de GPU não rodam no CI; usar mocks e fixtures pequenos).

### E12 · Épicos, histórias e prontidão
- **Líder:** `bmad-create-epics-and-stories` → `bmad-sprint-planning`.
- **Entra:** PRD, UX, arquitetura, specs, test design.
- **Sai:** `_bmad-output/planning-artifacts/epics.md` e `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- **Ordem sugerida dos épicos:** (1) fork e base multi-tenant; (2) **publicação no YouTube + página legal** (para destravar a T1); (3) fila e worker GPU; (4) pipeline de corte; (5) módulo de risco; (6) demais redes; (7) métricas; (8) inteligência/bandit; (9) frontend completo.
- **Decisão a tomar aqui:** usar ou não o orquestrador **bmad-loop** (`bmad-loop-setup` está adiado). A recomendação é **não** usá-lo no início, porque disputaria o controle com o superpowers. Reavaliar depois do primeiro épico.
- **Critério de saída:** prontidão aprovada pelo `bmad-sprint-planning`, sem lacunas entre PRD, UX e arquitetura.
- **Custo:** zero.

---

## FASE E — Construção

### E13 · Implementação (um ciclo por épico/história)
- **Líder:** **superpowers**. Ciclo por história:
  1. `superpowers:using-git-worktrees` (isolamento, branch por épico);
  2. `superpowers:writing-plans` (plano a partir da história do BMAD);
  3. `superpowers:test-driven-development` + `superpowers:subagent-driven-development`;
  4. `superpowers:systematic-debugging` quando algo falha;
  5. `superpowers:requesting-code-review` / `code-review` e `bmad-code-review` nos épicos críticos (risco, tenant, OAuth);
  6. `superpowers:verification-before-completion`;
  7. `superpowers:finishing-a-development-branch` (merge/PR **só com sua autorização**).
- **Apoio:** **claude-api** no módulo de IA; **impeccable** no frontend; `bmad-correct-course` se algo mudar o escopo; `bmad-retrospective` ao fim de cada épico.
- **Sai:** código, testes e `sprint-status.yaml` atualizado; uma retrospectiva por épico em `_bmad-output/implementation-artifacts/`.
- **Critério de saída (por épico):** testes verdes, revisão sem achados críticos, critérios de aceite da história demonstrados.
- **Custo:** a energia do PC (já estimada); tokens de LLM em testes reais do pipeline dentro do teto da E9.

### E14 · Verificação e NFR
- **Líder:** BMAD TEA: `bmad-testarch-automate`, `bmad-testarch-trace`, `bmad-testarch-nfr`, `bmad-testarch-test-review`; `bmad-qa-generate-e2e-tests` para E2E; `security-review` para segurança.
- **Sai:** relatório de rastreabilidade, auditoria de NFR (custo, desempenho do worker, segurança, isolamento de tenant) e E2E dos fluxos principais.
- **Critério de saída:** todos os requisitos do MVP rastreados a testes que passam; nenhum achado de segurança alto em aberto.
- **Custo:** zero.

---

## FASE F — Operação

### E15 · Lançamento interno (seus canais)
- **Líder:** sessão principal + `cortes-risco` (checklist de operação).
- **Pré-requisitos:** critério da T1 cumprido; módulo de risco ativo; fontes cadastradas com status de permissão; canais separados por nicho.
- **Sai:** `docs/runbook-operacao.md` (como subir o worker, o que fazer com um claim, como pausar e reativar, backup) e o primeiro lote de cortes publicado de forma controlada.
- **Critério de saída:** 2 semanas de operação sem incidente não tratado; coletor gravando snapshots de 1h/24h/7d.
- **Custo:** o custo mensal da E10 passa a ser real; acompanhar contra o teto.

### E16 · Operação e aprendizado contínuo
- **Líder:** `cortes-ml` (avaliar o bandit, decidir quando treinar modelos próprios). Ciclos de melhoria pelo fluxo E12→E13.
- **Sai:** relatórios mensais em `_bmad-output/implementation-artifacts/aprendizado-AAAA-MM.md` (o que performou, decisões do bandit, custo × receita).
- **Gatilhos:** volume acima do PC → GPU alugada (com estimativa); dados suficientes → treinar o classificador/LoRA na 4060 Ti.

---

## FASE G — Futuro (fora do MVP)

### E17 · Abertura como SaaS
Entra quando a operação própria provar que funciona. Passa de novo por BMAD (`bmad-correct-course` ou um PRD incremental):
- cobrança e planos (gateway de pagamento, com estimativa de taxas);
- onboarding de clientes e convites por workspace;
- **termos de uso para SaaS** (transferência de responsabilidade sobre as fontes), revisados por um advogado (custo a estimar);
- registro da marca no INPI (se adiado na E2);
- revisão das auditorias das plataformas para uso por terceiros (as cotas e escopos podem mudar);
- política de privacidade/LGPD completa.

---

## Skills próprias a criar

| Skill | Criada em | Ferramenta | Usada em |
|---|---|---|---|
| `cortes-pilares` | E1 | `bmad-workflow-builder` | E1, revisões de escopo |
| `cortes-naming` | E2 | `bmad-workflow-builder` | E2 |
| `cortes-integracoes` | T1 | `bmad-agent-builder` (especialista em APIs das redes) | T1, E7, épicos de publicação |
| `cortes-risco` | E8 | `bmad-workflow-builder` | E8, E15, operação |
| `cortes-ml` | E9 | `bmad-agent-builder` | E9, E16 |

## Decisões em aberto (e onde se resolvem)

| Decisão | Etapa |
|---|---|
| Nome final | E2 |
| Abrir MEI/CNPJ para a verificação da Meta | T1 |
| yt-dlp: aceitar o risco, banir ou modo misto | E8 |
| LLM: API, local ou híbrido; teto mensal | E9 |
| O que entra no fork do ReSocial | E10 |
| Supabase × Postgres próprio; tecnologia da fila | E10 |
| Usar o bmad-loop | E12 |
| Gatilho para alugar GPU | E10 / E16 |
