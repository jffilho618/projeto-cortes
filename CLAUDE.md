# CLAUDE.md — projeto-cortes (Picorte)

> Nome da ferramenta: **Picorte** (pico + corte), escolhido na E2 em 2026-11-16 (`_bmad-output/planning-artifacts/naming.md`). Primeiro canal de games: **Bomba Clips** (`naming-canais.md`). O repositório continua com o nome `projeto-cortes`.
> **Nota multi-agente:** este arquivo é lido tanto pelo **Claude Code** (`CLAUDE.md`) quanto pelo **Google Antigravity / Gemini** (via symlink `AGENTS.md` e `.agents/skills.json`). Mantenha ambos sincronizados e nunca quebre a compatibilidade entre os dois ambientes.

## Visão do produto (Atualizada na E3.5 em 2026-11-18)

Máquina autônoma de uso próprio (focada 100% em **lucrar com os próprios canais de cortes**, sem SaaS) que transforma vídeos longos (VODs, lives gravadas), **lives ao vivo** (Twitch, Kick, YouTube) e **clipes virais de terceiros** em cortes de alta retenção para **YouTube Shorts, YouTube Longo (3–5 min com thumbnail automática), TikTok, Instagram Reels e Facebook**.

**Estratégia Evolutiva (decidida na E3.5):**
Em vez de construir o cortador do zero, **partimos da base open-source local auditada em `referencias/`** — tendo o **`mehbul/chopify` (MIT, Python)** como chassi principal do motor de vídeo, somado a peças transplantadas do **`fralapo/clippyme` (MIT)** (monitor de lives ao vivo e integrações Twitch/Kick/YT) e do **`FujiwaraChoki/supoclip`** (layout automático Facecam + Jogo em `reaction_layout.py`, publicadores OAuth diretos em `social/` e servidor MCP) — mais um **banco PostgreSQL local** para guardar fontes, políticas de risco, cortes, publicações, snapshots de métricas (1h/24h/7d), campanhas pagas e pesos do Bandit.

O sistema evolui em camadas:
1. Primeiro funciona como clone local na GPU gerando os primeiros cortes `.mp4`;
2. Depois ganha controle direto pelo Claude e pelo Gemini (via Skill + MCP + banco Postgres);
3. Depois recebe **Visão Computacional de Games** (Facecam + Jogo, Troca Dinâmica de Layout, Sniper Crop, HUD/Killfeed, Micro-expressões), **Sismógrafo do Chat da Live** e **Engenharia de Retenção** (Cold Open Reverso 1,5s, Faixa de Contexto 2s, Seamless Loop, Compilação Cross-Streamer, Funil Short Isca → Vídeo Longo de 3–5 min + Thumbnail automática, 1º Comentário Fixado);
4. Ganha o **Escudo Anti-Strike (P1)** (status da fonte, políticas por publisher/jogo, remoção seletiva de música via `Demucs` na GPU, Selo Verde nos primeiros 15s, Detector de React Perigoso, Score de Transformação YPP, Deduplicação `pHash` e pausa global automática ao primeiro claim);
5. Ganha o **Olho para Fora** (Radar de alta na Twitch/YouTube + Calendário de eventos + Monitor de Lives ao Vivo + Caçador de clipes virais de terceiros + Detector de Treta/Pingue-Pongue + Multiplicador de Campanhas Pagas CPM);
6. Publica sozinho nas 5 redes via OAuth com o painel web do nosso `DESIGN.md` ("Estúdio do Criador");
7. Fecha o ciclo com o **Cérebro que Aprende (P3)** (snapshots 1h/24h/7d, Bandit contextual/hierárquico com esquecimento do passado, Reciclagem A/B de Gancho e Autocaptura de Dataset Rotulado para treinar modelos próprios na RTX 4060 Ti).

A visão detalhada e completa está em `_bmad-output/planning-artifacts/visao.md` e a auditoria de código dos clones está em `_bmad-output/planning-artifacts/concorrentes.md`.

## Idioma

- Converse sempre em **português do Brasil**: direto, honesto, inclusive quando a resposta não for a esperada.
- Documentos em português do Brasil. Código, identificadores e mensagens de commit podem ser em inglês ou em português, desde que sigam a convenção que a arquitetura definir.

## Regras que não mudam sem conversa

1. **Nunca commitar, dar push, apagar ou fazer qualquer ação irreversível sem pedido explícito.** Uma autorização vale só para aquela ação.
2. **Nada de ferramenta de autoclip paga** (Opus Clip, Klap, Zernio pago, AssemblyAI pago e afins). A base parte de código open-source local (`chopify`, `clippyme`, `supoclip`) e a inteligência de seleção é nossa, rodando localmente e evoluindo com modelos próprios treinados nos nossos dados.
3. **Redes só por OAuth/tokens revogáveis.** Nunca pedir nem guardar senha de rede social. Segredos sempre cifrados no banco.
4. **O módulo de risco de direitos autorais (P1) é obrigatório:**
   - cada fonte tem status de permissão (`liberada` / `contrato` / `campanha ativa`, que expira / `gameplay próprio`, que nasce autorizado / `desconhecida`); fonte `desconhecida` **não é baixada nem publicada**;
   - registro de políticas por publisher/jogo (spoilers, cutscenes proibidas, música licenciada);
   - remoção seletiva de música licenciada via `Demucs` na GPU (nunca disfarçar com pitch/speed — A2);
   - filtro "Selo Verde 15s" (sem violência gráfica e com micro-bleep em palavrões nos primeiros 15s) e Detector Visual de "React Perigoso" (vídeo de terceiro aberto na live);
   - crédito automático ao canal original;
   - monitor de reivindicações e strikes nos vídeos publicados;
   - **pausa automática** de todos os cortes de uma fonte, em todas as redes, ao primeiro claim de bloqueio ou strike;
   - lista negra de fontes e deduplicação perceptual (`pHash`);
   - canais separados por nicho, sem concentrar tudo num só;
   - transformação real em cada corte (Score mínimo YPP — P2).
5. **Foco 100% em uso próprio (SaaS fora de escopo):** não gastar tempo com multi-tenant (`workspace_id`), planos de assinatura, billing ou onboarding de clientes.
6. **Toda etapa que custa dinheiro tem estimativa de custo** escrita antes de ser executada (API de LLM, GPU alugada, hospedagem, domínio etc.). Gasto recorrente precisa de um teto mensal definido.
7. **Local/grátis primeiro.** O PC de mesa (**RTX 4060 Ti 8 GB**) é o worker principal (`faster-whisper`, `FFmpeg/NVENC`, Visão Computacional, `Demucs`, Ollama/treino leve — rodando modelos pesados em fila serializada para caber nos 8 GB de VRAM, com Modo Madrugada para lotes pesados). O notebook (**GTX 1650 4 GB**) é para desenvolvimento e testes leves.
8. **Nunca copiar `.env` nem segredos** do ReSocial ou de qualquer outro lugar.
9. **Skill de terceiros só se instala com aprovação.** Antes de pedir, mostrar: o que ela faz, de onde vem, quem mantém e o que executa (scripts, hooks).

## Quem lidera cada fase

Há vários frameworks instalados (disponíveis tanto no Claude Code quanto no Antigravity). Para que não disputem o controle, cada fase tem **um** líder:

| Fase | Líder | Observação |
|---|---|---|
| Descoberta, especificação (`bmad-spec`), arquitetura de fusão (`bmad-architecture`), épicos/histórias (`bmad-create-epics-and-stories`) | **BMAD** (`bmad-*`) | Fonte da verdade do planejamento. Em vez de Product Brief + PRD de SaaS, usamos `bmad-spec` + `bmad-architecture`. |
| Marca, paleta, tipografia, design system (o "art bible") e polimento de UI | **impeccable** | Já gerou `PRODUCT.md`, `DESIGN.md` e `design/`; lidera quando vestirmos o painel web. |
| Pilares/anti-pilares (`cortes-pilares`), naming (`cortes-naming`) e operação do Picorte | **Skills próprias** (`skills/` → `.claude/skills/`) | Criadas com BMad Builder / skill-creator. |
| Implementação dos Épicos 1 a 7: planos, TDD, subagentes, debugging, code review, verificação | **superpowers** | Executa as histórias de cada Épico (`writing-plans` → `test-driven-development` → `verification-before-completion`). |
| Módulo de IA (chamadas a LLM por API vs Ollama local, prompts, custos) | **claude-api** | Consultar sempre antes de escolher modelo pago ou estimar preço de tokens. |
| Estratégia de testes dos portões críticos (P1 risco, deduplicação, OAuth) | **BMAD TEA** (`bmad-testarch-*`) | Desenha os testes de sistema; o `superpowers` executa o TDD. |

**Pilares como portão:** os pilares aprovados em `_bmad-output/planning-artifacts/pilares.md` (`P1 > P2 > P3 > P4 > P5` e `A1`–`A5`) são o critério de decisão do sistema. Rode a skill `cortes-pilares` no modo Julgar ao validar a Spec (E4), a Arquitetura de Fusão (E5), os Épicos (E6) e qualquer mudança de rumo. Um veredito **contra** bloqueia até o dono decidir.

**Regra anti-conflito:** em descoberta e planejamento (Fases A e B), **não** acionar `superpowers:brainstorming` nem `superpowers:writing-plans`. O trabalho de concepção passa pelas skills do BMAD (`bmad-brainstorming`, `bmad-spec`, `bmad-architecture`, `bmad-create-epics-and-stories`). O `superpowers` assume na Fase C (Implementação dos Épicos 1 a 7), partindo das histórias geradas pelo BMAD.

## Onde ficam as coisas

- `CLAUDE.md` (e symlink `AGENTS.md`): na raiz.
- `docs/plano-mestre.md`: **Versão 2 (Plano Mestre Evolutivo)** — o mapa completo da E0 ao Épico 7, com arquivos de origem dos clones, skills responsáveis, entregáveis e critérios de saída. **Consultar sempre antes de começar qualquer etapa.**
- `docs/handoff-sessao-NN.md`: passagem de bastão entre sessões (`handoff-sessao-01.md`, `handoff-sessao-02.md`). Ler o mais recente ao iniciar uma sessão nova no Claude ou no Gemini.
- `referencias/`: clones open-source baixados para auditoria e transplante de código (`mehbul_chopify`, `fralapo_clippyme`, `FujiwaraChoki_supoclip`, `AgriciDaniel_claude-shorts`, `louisedesadeleer_clipify`, `artbyjazi_autoclip`). Fora do git (`.git/info/exclude`).
- `_bmad-output/planning-artifacts/`: artefatos de planejamento (`pilares.md`, `visao.md`, `naming.md`, `naming-canais.md`, `concorrentes.md`, `specs/spec-picorte/SPEC.md`, `architecture.md`, `epics.md`).
- `_bmad-output/brainstorming/`: sessões e memlogs do `bmad-brainstorming` (incluindo `brainstorm-mapa-funcionalidades-picorte-2026-11-18/`).
- `_bmad-output/implementation-artifacts/`: histórias e `sprint-status.yaml`.
- `_bmad-output/test-artifacts/`: artefatos do TEA.
- `skills/`: código-fonte das skills próprias, instaladas em `.claude/skills/` (e lidas pelo Antigravity via `.agents/skills.json`).

## Restrições externas conhecidas

- **YouTube Data API:** um upload custa 1.600 das 10.000 unidades diárias (~6 uploads/dia por projeto GCP). App não auditado só publica como privado. Armazenamento de dados de terceiros expira em 30 dias (III.E.4.d); métricas derivadas exigem permissão III.L na auditoria.
- **TikTok Content Posting API:** sem auditoria, só posta privado.
- **Instagram/Facebook:** exige conta Business/Creator ligada a uma Página; Reels pela Graph API; limites diários; App Review.
- **Auditorias (Trilha Paralela T1):** exigem política de privacidade, termos e domínio próprio mesmo para uso próprio, e demoram. Enquanto não saem, o sistema gera os arquivos `.mp4` + metadados prontos para publicação assistida/manual (respeitando A4: zero automação de navegador com senha).
- **Download via `yt-dlp`:** viola os ToS do YouTube; mitigado pelo portão P1 (nunca baixar fonte `desconhecida`, usar modo áudio/seções sob demanda do `chopify` e priorizar fontes com permissão/campanha/gameplay próprio).
