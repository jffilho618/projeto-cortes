# CLAUDE.md — projeto-cortes

> Codinome provisório. O nome final sai da etapa de naming (ver `docs/plano-mestre.md`).

## Visão do produto

Ferramenta que transforma vídeos longos (podcasts, lives, entrevistas) em cortes prontos para redes sociais e aprende o que dá resultado. Ela transcreve, encontra ganchos e trechos bons, corta, reenquadra para 9:16 com rastreamento de rosto e legenda. Também importa e dá nota a cortes feitos por terceiros. Publica ao mesmo tempo em YouTube Shorts, YouTube (cortes longos de 3–5 min), TikTok, Instagram Reels e Facebook. Depois coleta métricas e usa um módulo de inteligência (bandit sobre tema × gancho × duração × horário × rede) para priorizar o que performa. O primeiro operador é o próprio dono, com vários canais. O sistema já nasce **arquitetado para virar SaaS**, mas cobrança, planos e onboarding de clientes ficam fora do MVP.

A visão do dono, nas palavras dele, com a leitura técnica, está em `_bmad-output/planning-artifacts/visao.md`. Ela guia o PRD e a arquitetura.

## Idioma

- Converse sempre em **português do Brasil**: direto, honesto, inclusive quando a resposta não for a esperada.
- Documentos em português do Brasil. Código, identificadores e mensagens de commit podem ser em inglês ou em português, desde que sigam a convenção que a arquitetura definir.

## Regras que não mudam sem conversa

1. **Nunca commitar, dar push, apagar ou fazer qualquer ação irreversível sem pedido explícito.** Uma autorização vale só para aquela ação.
2. **Nada de ferramenta de autoclip paga** (Opus Clip, Klap e afins). A detecção de bons cortes é nossa, inclusive com modelos próprios treinados.
3. **Redes só por OAuth/tokens revogáveis.** Nunca pedir nem guardar senha de rede social. Segredos sempre cifrados no banco.
4. **O módulo de risco de direitos autorais é obrigatório** e faz parte do MVP:
   - cada fonte tem status de permissão (liberada publicamente / contrato / campanha de clipping / desconhecida);
   - crédito automático ao canal original;
   - monitor de reivindicações e strikes nos vídeos publicados;
   - **pausa automática** de todos os cortes de uma fonte, em todas as redes, ao primeiro claim de bloqueio ou strike;
   - lista negra de fontes;
   - canais separados por nicho, sem concentrar tudo num só;
   - transformação real em cada corte (gancho/título próprio, legenda, contexto).
5. **Multi-tenant desde o primeiro dia:** toda tabela de domínio tem `workspace_id` (tenant), e as conexões OAuth são por workspace.
6. **Toda etapa que custa dinheiro tem estimativa de custo** escrita antes de ser executada (API de LLM, GPU alugada, hospedagem, domínio, INPI etc.). Gasto recorrente precisa de um teto mensal definido.
7. **Local/grátis primeiro.** O PC de mesa (RTX 4060 Ti 8 GB) é o worker inicial: whisper, ffmpeg/NVENC, rosto, treino leve. O notebook (GTX 1650 4 GB) é só para desenvolvimento. GPU alugada só entra quando o volume passar do que o PC aguenta, e sem mudar o desenho (o worker puxa da fila).
8. **Nunca copiar `.env` nem segredos** do ReSocial ou de qualquer outro lugar.
9. **Skill de terceiros só se instala com aprovação.** Antes de pedir, mostrar: o que ela faz, de onde vem, quem mantém e o que executa (scripts, hooks).

## Quem lidera cada fase

Há vários frameworks instalados. Para que não disputem o controle, cada fase tem **um** líder:

| Fase | Líder | Observação |
|---|---|---|
| Descoberta, planejamento, PRD, UX, arquitetura, épicos/histórias | **BMAD** (`bmad-*`) | Fonte da verdade do planejamento. |
| Marca, paleta, tipografia, design system (o "art bible") | **impeccable** | Gera `PRODUCT.md` / `DESIGN.md` próprios; nada herdado do ReSocial. |
| Pilares/anti-pilares, ML, integrações por plataforma, risco/direitos, naming | **Skills próprias** (BMad Builder / skill-creator) | Criadas quando a etapa começar; ver Plano Mestre. |
| Implementação: planos, TDD, subagentes, code review, verificação | **superpowers** | Executa as histórias que o BMAD gerou. |
| Módulo de IA (chamadas a LLM, prompts, custos) | **claude-api** | Consultar sempre antes de escolher modelo ou estimar preço. |
| Estratégia de testes, NFR, rastreabilidade | **BMAD TEA** (`bmad-testarch-*`) | Desenha; o superpowers executa o TDD. |

**Pilares como portão:** depois de aprovados (E1), os pilares em `_bmad-output/planning-artifacts/pilares.md` são o critério de decisão do produto. Rode a skill `cortes-pilares` no modo Julgar ao validar o PRD, a arquitetura, cada épico e toda proposta do `bmad-correct-course`. Um veredito **contra** bloqueia até você decidir.

**Regra anti-conflito:** em descoberta e planejamento, **não** acionar `superpowers:brainstorming` nem `superpowers:writing-plans`. O trabalho criativo de produto passa pelas skills do BMAD (`bmad-brainstorming`, `bmad-forge-idea`, `bmad-product-brief` etc.). O superpowers só assume a partir da fase de implementação, partindo das histórias do BMAD.

## Onde ficam as coisas

- `CLAUDE.md` (este arquivo): na raiz.
- `docs/plano-mestre.md`: as etapas do nome ao lançamento, com responsáveis, entregáveis e critérios de saída. **Consultar antes de começar qualquer etapa.**
- `docs/handoff-sessao-NN.md`: passagem de bastão entre sessões. Escrever um ao fim de cada sessão longa.
- `_bmad-output/planning-artifacts/`: artefatos do BMAD e das skills próprias (pilares, brief, PRD, UX, arquitetura, specs de domínio, épicos).
- `_bmad-output/implementation-artifacts/`: histórias e status de sprint.
- `_bmad-output/test-artifacts/`: artefatos do TEA.
- `skills/`: código-fonte das skills próprias (saída do BMad Builder), antes de serem instaladas em `.claude/skills/`.
- Config do BMAD: overrides do projeto em `_bmad/custom/config.toml`; overrides pessoais em `_bmad/config.user.toml` e `_bmad/custom/config.user.toml` (fora do git). Não editar `_bmad/config.toml` (o instalador sobrescreve).

## Legado: ReSocial

A referência é `/home/bomba/Área de trabalho/FRELA/ReSocial_sem_firebase`. A cópia em `~/Downloads` é obsoleta e deve ser ignorada.

- **Intenção:** fazer um fork do backend e da infra (Fastify 5 + Postgres, auth, accounts, media, agendador durável, coletor de métricas, publicadores plugáveis, `lib/crypto.ts`, Vitest, Docker, Makefile, workspaces). **Quem decide é a etapa de arquitetura**, que precisa justificar o que entra e o que sai.
- **Não se herda:** nome, marca, paleta, `DESIGN.md`, público, prioridade de redes nem o frontend.
- **Princípios que continuam valendo:** conectar sem coletar senha; nada sai errado (revisão antes de publicar); honestidade sobre o que cada rede permite; pt-BR claro; datas gravadas em UTC e mostradas no fuso de Brasília.

## Restrições externas conhecidas

- YouTube Data API: um upload custa 1.600 das 10.000 unidades diárias (~6 uploads/dia por projeto GCP). App não auditado só publica como privado.
- TikTok Content Posting API: sem auditoria, só posta privado.
- Instagram/Facebook: exige conta Business/Creator ligada a uma Página; Reels pela Graph API; limites diários; App Review e verificação de empresa.
- As auditorias exigem política de privacidade, termos e domínio próprio **mesmo para uso próprio**, e demoram. Ver a trilha paralela T1 no Plano Mestre.
- Baixar do YouTube com yt-dlp viola os ToS do YouTube. É um risco em aberto, que a etapa de risco precisa decidir.
