---
title: Mapa de capacidades do Picorte para o painel "Estúdio do Criador"
date: 2026-11-21
source: .memlog.md (mesma pasta) — 155 entradas, 110 ideias, modo autônomo
feeds: cortes-pilares (Julgar), bmad-correct-course (6.3), bmad-ux (EXPERIENCE.md), contrato GET /api/capacidades
---

# Mapa de capacidades do Picorte (status medido em 2026-11-21)

**Método:** status medido pelo que roda de verdade, não pelo "done" do papel. As fontes cruzadas foram:
- a SPEC, o `epics.md`, o `sprint-status` e a auditoria E3;
- o `deferred-work`;
- os 6 `project.json` e `engine_health.json`;
- o `picorte.db` (lido só em modo leitura);
- os `benchmarks/*.json`;
- o `dashboard.py`, aberto no navegador numa cópia isolada.

**Status:** `ligado` funciona de ponta a ponta · `parcial` funciona em parte, ou o código existe mas falta tela ou dado · `travado` ainda não existe.
**Tipo do motivo** (decide o desenho da trava): `codigo` · `config` · `dado` · `temporario` · `escolha`.

## Decisões do dono nesta sessão

- **Painel só para PC.** Roda local e nunca vai rodar no celular. Isso muda o CAP-14 da SPEC e a história 6.3 ("Desktop e Celular"), e vai para o `correct-course`.
- Valem as regras do handoff:
  - travado nunca mostra dado falso;
  - o backend decide o status;
  - o `DESIGN.md` atual não é restrição;
  - o impeccable (modo Operate) lidera o visual.

## O banco não está pronto para o painel (achados críticos)

Se o painel ler o banco como ele está hoje, vai mentir do jeito que o A5 proíbe:

| # | Achado no `picorte.db` | Efeito | Correção (pré-requisito) |
|---|---|---|---|
| B1 | `videos.source_id` = NULL em 12/12. O `sync_studio_project` grava `None` mesmo com `source_gate.source_id` no projeto | não existe o elo fonte → vídeo → corte, nem o disjuntor por fonte no banco | gravar o `source_id` do `source_gate` |
| B2 | `score_chat/audio/visual` = 0.0 em 199/199; `score_text` = nota geral | o zero finge uma medição; o CAP-5 não está ligado | gravar o sinal medido e NULL quando não foi medido; migrar os 0.0 |
| B3 | `ypp_transform_score` = 0, `phash_signature` vazio, `risk_status` = `pending` (exceto os 2 manuais) | o veredito P1 só existe no `.meta.json`; a AC1 da 4.5 não roda | persistir o `risk_verdict` no banco |
| B4 | 12 vídeos e 199 cortes de projetos já apagados (inclusive `/home/bomba/...`); só existem 6 pastas | o selo atual "199 cortes" é dado podre | reconciliar banco × disco, arquivar os órfãos e manter o rastreio dos 2 publicados (P1) |
| B5 | MCP `picorte_enfileirar_video` só insere `videos.queued`; ninguém consome | ferramenta falsamente ligada | **fila única** (decisão do dono): o MCP cria o projeto real na mesma fila do painel |
| B6 | `publisher_policies` = 0 linhas (sincroniza só quando alguém consulta) | a tela de políticas sairia vazia | sincronizar no boot |

Outros pré-requisitos:
- **B7:** endpoint de taxonomia (arquétipos, tiers, redes, modos de IA), para o front não fixar listas (3.6.3: 10 → 12).
- **B8:** sondas de provedor e ferramenta, com cache.
- **B9:** lock de projeto entre processos. Hoje o `Studio.__init__` reescreve `project.json` e marcaria como `interrupted` um job da outra sessão.
- **B10:** armazenamento dos 👍/👎.
- **B11:** `mark-posted` com YouTube Longo.
- **B12:** registro de gastos (regra 6).

Mais dois pontos:
- **Banco:** roda em **SQLite**, não em PostgreSQL como diz o AD-2. Recomendação: seguir no SQLite e expor o motor de banco como uma capacidade. O dono confirma.
- **Gemini:** está sem cota (429, volta em ~4 dias). Isso é estado `temporario` e não pode parecer igual a "não existe".

## Inventário por área

### 1. Hoje / Sistema (cockpit)

| ID | Função | Status | Falta | Dado | Origem |
|---|---|---|---|---|---|
| SIS-1 | GPU detectada e preset de visão | ligado | — | `config.detect_gpu_profile` (`/api/config`) | 1.1 |
| SIS-2 | Fila serial de jobs (1 por vez) | parcial (`codigo`) | lock entre processos (B9) | `dashboard.Studio` | E1/E2 |
| SIS-3 | Lock de estágio de VRAM | ligado | — | `vram_runner.py` | 2.2 |
| SIS-4 | Modo Madrugada | parcial (`codigo`) | agendador e controle na tela; só existe `is_in_night_window` | `vram_runner.py` | 2.2 |
| SIS-5 | Banco | parcial (`dado`) | B1–B4, B6; SQLite × AD-2 | `picorte.db` | 2.1 |
| SIS-6 | Motor de IA: Ollama (`qwen3.5:9b`) | ligado | sonda B8 | `llm_router` | 2.3 |
| SIS-7 | Motor de IA: Gemini (`agy`) | parcial (`temporario`) | cota (429 desde 21/11) | health `editor` / erro do projeto | 2.3 |
| SIS-8 | Motor de IA: Claude CLI | ligado | sonda B8 | keyframes (A6) | 2.3 |
| SIS-9 | Modo Dupla | parcial (`dado`) | nenhum uso real registrado | `llm_router` | 2.3 |
| SIS-10 | Modo determinístico (padrão da tela atual) | ligado (`escolha`) | aviso: nada do E3.5 roda nesse modo | — | auditoria E3 |
| SIS-11 | yt-dlp + ejs + node, demucs | ligado | atualização diária do `yt-dlp` e canário (W9) | sondas | W4, W9 |
| SIS-12 | Servidor MCP (11 ferramentas) | parcial (`codigo`) | B5; ferramenta `picorte_capacidades` | `picorte/mcp/server.py` | 2.4 |
| SIS-13 | Custos e teto mensal | travado (`codigo`) | registro de gastos (B12) | — | regra 6 |

### 2. Fila e Projetos

| ID | Função | Status | Falta | Dado | Origem |
|---|---|---|---|---|---|
| FIL-1 | Criar projeto (URL ou arquivo; lote de 1–100) | ligado | — | `POST /api/projects`, `/api/batch` | E1 |
| FIL-2 | Portão P1 antes de baixar | ligado | mostrar o veredito **antes** de enfileirar | `project.json.source_gate` (`c433780dc1e0` barrado) | 4.1 |
| FIL-3 | Estágio, progresso e log | parcial (`codigo`) | textos em PT-BR; resumo do log; título real (`source_meta.title`) no lugar da URL | `project.json`, `job.log` | E1 |
| FIL-4 | VOD longo em blocos de 30 min e por seções | ligado | — | `*.partNNN.json`, `sections/` | 1.2 |
| FIL-5 | Falha do Editor-Chefe com próximo passo | parcial (`codigo`) | ação "trocar motor e retomar"; hoje mostra o comando cru | `project.error` | auditoria 1b |
| FIL-6 | Separar conjunto de prova da produção | parcial (`codigo`) | filtro na tela (hoje 4 de 6 projetos são de prova) | `options.benchmark_blind` | 3.6.1 |
| FIL-7 | Caça profunda e busca por pergunta | parcial (`codigo`) | controles na tela; hoje só CLI/MCP | `hunt_mode`, `picorte_buscar_por_pergunta` | 3.5.5 |

### 3. Revisão de cortes (o coração)

| ID | Função | Status | Falta | Dado | Origem |
|---|---|---|---|---|---|
| REV-1 | Arquétipo, tier, título, faixa 2s, 1º comentário, motivo | ligado (modo com IA) | taxonomia vinda do backend (B7) | `segments.json`, `selection.json`, `.meta.json` | 3.5.3 |
| REV-2 | Sinais por corte (riso, susto, chat, comentário, facecam, HUD) | parcial (`dado`) | B2; mostrar "não medido", nunca zero | campo `sinais` (A4), `engine_health.json` | 3.2, 3.5.4 |
| REV-3 | Ajustar início/fim; editar transcrição e legenda | ligado | waveform com peaks calculados no servidor | `/candidates`, `/transcript` | E1 |
| REV-4 | Preview 480p e render final | ligado | — | `run` (preview/render) | E1 |
| REV-5 | Thumbnail automática | ligado | — | `*_thumb.png` | 3.5 |
| REV-6 | Faixa de contexto 2s no vídeo | ligado | — | `render_clips.py:726` | 3.4 |
| REV-7 | Keyframes (o LLM vê 3 frames) | ligado (`escolha`, desligado por padrão) | custo ~US$ 0,26 por VOD (Sonnet) | `options.keyframes` | 3.5.4 / A6 |
| REV-8 | 👍/👎 por corte | travado (`codigo`) | B10 + endpoint | — | nota da 6.3 |
| REV-9 | Salvar como Exemplo Ouro | travado (`codigo`) | endpoint de gravação | `golden_examples.json` | 6.3 AC3 |
| REV-10 | Cold Open e Seamless Loop | travado (`codigo`) | render | plano em `retention_engine` | 3.7.1 (A9) |
| REV-11 | Layout dinâmico e Sniper Crop | travado (`codigo`) | ligar ao render; o layout estático de games está ligado | `reframe_games` | 3.7.2 (A8) |
| REV-12 | Par Short ↔ Longo | travado (`codigo`) | corrigir o bug A11; `parent_long_clip_id` é NULL em 100% | `clips` | 3.7.3 |
| REV-13 | Arcos de 2 atos e compilação por arquétipo | parcial (`codigo`) | render; hoje só gera JSON no modo `deep` | `two_act_arc`, `archetype_compiler` | 3.7.4 (A12) |
| REV-14 | Compilação cross-streamer | travado (`codigo`) | Épico 5 | — | A10 |
| REV-15 | nobada/mico, `standalone`, bordas por frase, ouro com 2 sinais | travado (`codigo`) | 3.6.3–3.6.5 | — | E3.6 |

### 4. Fontes e Permissões (P1)

| ID | Função | Status | Falta | Dado | Origem |
|---|---|---|---|---|---|
| FON-1 | Lista de fontes com status e base da permissão | ligado (sem tela) | tela | `sources` (5 liberadas, `tolerancia_publica`) + `assets/streamers/registry.json` | 4.1 |
| FON-2 | Cadastrar fonte e mudar permissão | ligado (só MCP) | tela | `StudioService.create_source` / `update_source_permission` | 2.4, 4.1 |
| FON-3 | Tentativas barradas (ex.: BisteconeLive) | parcial (`dado`) | registro próprio; hoje só no erro do projeto | `project.error` `[P1:pre_ingest]` | 4.1 |
| FON-4 | Elo fonte → vídeos → cortes | travado (`dado`) | B1 | `videos.source_id` | 2.1 |
| FON-5 | Políticas por publisher/jogo | parcial (`dado`) | B6 | `assets/policies/publishers.json` | 4.1 |
| FON-6 | Campanhas CPM | parcial (`codigo`) | tela de cadastro (tabela vazia; o portão já lê) e radar | `campaigns` | 4.1, 5.1 |
| FON-7 | Pausar fonte (disjuntor manual) | ligado | histórico na tela | `/api/risk/pause-source`, MCP | 4.1 |
| FON-8 | Dossiês de jogo | ligado (só MCP/CLI; 1 dossiê) | editor na tela | `picorte/ai/game_dossiers/gta6.json` | 3.5.5 |
| FON-9 | Perfis e piadas internas | travado (`codigo`) | 5.4 | — | E5 |

### 5. Escudo (Raio-X P1)

| ID | Função | Status | Falta | Dado | Origem |
|---|---|---|---|---|---|
| ESC-1 | Veredito por corte e por rede | parcial (`dado`) | nenhum corte atual tem veredito (o `2501be513575` é anterior ao E4); B3; estado "sem veredito — re-auditar" | `.meta.json.risk_verdict`, `risk_seal.js` | 4.5 |
| ESC-2 | Selo Verde 15s (bleep e `***`) | ligado | — | render | 4.4 |
| ESC-3 | Remoção de música com Demucs | ligado | — | `clean_music_in_render` | 4.3, W4 |
| ESC-4 | React Guard | ligado no veredito | ainda sem corte real auditado | orquestrador | 4.4 |
| ESC-5 | YPP, originalidade TikTok e pHash | parcial (`dado`) | B3 | `.meta.json` | 4.2 |
| ESC-6 | Limpeza de texto por rede (copy hygiene) | ligado | — | `publish_kit` (4 redes) | 4.2 |
| ESC-7 | Cadência e cooldown de 48h | ligado | — | `work/cadence_state.json`, `/api/risk/cooldown` | 4.2 |
| ESC-8 | Registrar claim manual → pausa | parcial (`codigo`) | formulário; o pause-source já aceita `claim_type` | `claims_events` (0) | 4.1 |
| ESC-9 | Monitor automático de claims | travado (`codigo`) | 6.2 | — | CAP-16 |

### 6. Saúde do motor e Benchmark

| ID | Função | Status | Falta | Dado | Origem |
|---|---|---|---|---|---|
| SAU-1 | Saúde por projeto e por parte (13 partes) | ligado (sem tela) | tela; frase-resumo montada pelo backend | `engine_health.json` | 1b / W9 |
| SAU-2 | `confianca_projeto` | travado (`codigo`) | 3.6.5 | — | 3.6.5 |
| SAU-3 | Precision@K com lift contra o acaso | ligado, n=1 | aviso de amostra pequena; histórico por label | `benchmarks/*.json` (P@5 0,40 vs 0,094) | 3.6.1 |
| SAU-4 | Gabaritos acumulados para a 3.6.6 | ligado (1 de 20) | barra real de progresso | `benchmarks/gabaritos/` | 3.6.1 → 3.6.6 |
| SAU-5 | Canário semanal e `yt-dlp` diário | travado (`codigo`) | W9 | — | W9 |

### 7. Publicação

| ID | Função | Status | Falta | Dado | Origem |
|---|---|---|---|---|---|
| PUB-1 | Pacote do Dia | ligado | projetos anteriores ao portão são barrados (W5) | `export-bundle` | 4.5 |
| PUB-2 | Kit por rede, copiar em 1 clique | ligado (dado) | — | `.meta.json.publish_kit` | 4.2 / 6.1 |
| PUB-3 | Registrar a URL publicada | ligado (4 redes, 2 registros) | — | `publications` | 6.1 (adiantado) |
| PUB-4 | YouTube Longo e Related Video | travado (`codigo`) | B11 + 3.7.3 | — | CAP-15 |
| PUB-5 | Contas OAuth das 5 redes | travado (`codigo`) | 6.1 (`crypto_vault`) + apps aprovados (T1) | `social_accounts` (0) | 6.1 |
| PUB-6 | Publicação automática | travado (`codigo`) | 6.1 + auditorias | — | 6.1 |

### 8. Métricas e Aprendizado — tudo travado (`codigo`)

| ID | Função | Falta | Origem |
|---|---|---|---|
| MET-1 | Snapshots 1h/24h/7d (hoje 0 linhas) | 7.1 | CAP-18 |
| MET-2 | Recompensa anti-clickbait | 7.1 | CAP-18 |
| MET-3 | Bandit com esquecimento | 7.2 | CAP-18 |
| MET-4 | Reciclagem A/B do gancho | 7.2 | CAP-18 |
| MET-5 | Dataset rotulado e treino local | 7.3 | CAP-18 |
| MET-6 | Pesos calibrados pelo gabarito (≥ 20 VODs) | 3.6.6 | 3.6.6 |

O **contador de rótulos 👍/👎** pode ser real desde o primeiro dia, assim que a B10 existir.

### 9. Radar (Épico 5) — área inteira travada (`codigo`)

| ID | Função | Origem |
|---|---|---|
| RAD-1 | Tendências e calendário | 5.1 |
| RAD-2 | Monitor de lives ao vivo, com chat da Twitch (W7) | 5.2 |
| RAD-3 | Caçador de clipes de terceiros | 5.3 |
| RAD-4 | Detector de treta e consenso entre streamers | 5.3 |
| RAD-5 | Limpeza de dados de terceiros em 30 dias | 5.1 |

### 10. Lives (pedido do dono, 2026-11-21) — candidata a página inicial

Uma vitrine no estilo das plataformas de vídeo e live, com as thumbs dos streamers cadastrados. É o que tira a ferramenta do modelo "caixa de colar link + Find clips". O dono quer esta página **excepcional**.

| ID | Aba ou função | Status hoje | Falta | Dado | Origem |
|---|---|---|---|---|---|
| LIV-1 | **Ao vivo**: streamers cadastrados transmitindo agora | travado (`codigo` + `config`) | consulta oficial de "está ao vivo" (Twitch Helix `Get Streams` com app token grátis e revogável; YouTube Data API; Kick a pesquisar) | `sources` + API oficial | 5.2 |
| LIV-2 | Abrir a live (modal ou página) com o player ao vivo e as opções de corte | travado (`codigo`) | player embutido oficial (embed da Twitch/YouTube, liberado na CSP) + captura da live | — | 5.2 |
| LIV-3 | **Em alta** | travado (`codigo`) | radar com a ordenação oficial das APIs, sem ranking próprio entre canais de terceiros (YouTube III.E.2.a) | — | 5.1 |
| LIV-4 | **Recentes**: lives e VODs recentes dos streamers cadastrados | **parcial (pode ligar já)** | listar os vídeos recentes dos canais do `registry.json` (YouTube Data API `playlistItems`: 1 unidade por chamada, cota grátis; ou `yt-dlp`, com a ressalva de ToS do `CLAUDE.md`) | `registry.json` + API | E1 (ingestão) + novo |
| LIV-5 | Cortar um VOD (modal com formatos, motor de IA e preview do enquadramento) | **parcial** | o modal; a ingestão e o portão P1 já estão ligados; o preview do layout usa uma imagem real do vídeo (thumb ou frame), nunca um mock | `POST /api/projects` | E1 + 6.3 |
| LIV-6 | Selo "AO VIVO", espectadores, duração | travado | só com dado da API oficial, com `verificado_em`; nunca badge fixo (A5) | API | 5.2 |

Regras desta página:
- **Thumbs e listas de terceiros** ficam em cache com **validade de no máximo 30 dias** (YouTube III.E.4.d).
- **Custo** estimado em R$ 0: APIs oficiais dentro da cota grátis (regra 6).
- **Aba aberta por padrão:** o backend decide, pela primeira aba ligada (Recentes enquanto o E5 não chega), para a página não abrir num vazio travado.
- **Página inicial:** proposta da sessão para o dono avaliar no `bmad-ux`. A vitrine de Lives é a home, com uma faixa compacta **"Na sua mesa"** no topo: cortes esperando revisão, links pendentes (C2), jobs rodando e falhas. A condição C2 exige que as pendências apareçam na página de abertura.

## Contrato `GET /api/capacidades` (proposta)

```json
{ "id": "PUB-5", "area": "publicacao", "titulo": "Contas OAuth",
  "status": "ligado|parcial|travado", "tipo_motivo": "codigo|config|dado|temporario|escolha",
  "motivo": "…", "falta": ["6.1 cofre de tokens", "app aprovado por rede"],
  "fonte_dado": "social_accounts", "origem": {"epico": "6", "historia": "6.1", "cap": "CAP-15"},
  "escopo": "global|projeto|corte", "depende_de": ["…"], "verificado_em": "…", "ligou_em": null }
```

- **Uma fonte só para painel e agentes:** a mesma função alimenta o endpoint e a ferramenta MCP `picorte_capacidades`.
- **Sondas com cache e TTL:** cada sonda guarda o resultado por um tempo (ex.: Ollama 30 s; `yt-dlp` 1 dia).
- **SSE `/api/eventos`:** empurra a mudança de capacidade e o progresso dos jobs.
- **Teste de contrato A5:** nenhum endpoint de dado devolve número quando a capacidade está travada.
- **`depende_de`:** faz o "o que falta" apontar a causa raiz (ex.: Bandit ← snapshots ← publicação com URL).

## Escopo da primeira entrega (MoSCoW)

- **Must:**
  - backend: endpoint de capacidades + SSE + taxonomia + B1, B2, B3, B4, B7, B8, B9, B10;
  - telas: Hoje, Fila e Projetos, Revisão (player + waveform, sinais medidos, P1 no cartão, 👍/👎), Fontes e Permissões, Saúde e Benchmark, Publicação Assistida;
  - áreas travadas desenhadas: OAuth, claims automático, métricas, Bandit e dataset, Radar.
- **Should:** B6, B11, Exemplo Ouro, editor de dossiê, atalhos de teclado (J/K, 1/2, I/O), minimapa do VOD só com as camadas medidas, card de custos, notificação do Windows.
- **Could:** paleta Ctrl+K, arrastar cortes para os dias da semana, modo foco, histórico de decisões por corte, B12 completo.
- **Won't agora:** layout de celular, publicar via OAuth, Bandit funcionando, Radar funcionando (ficam travados e prontos).

## Do painel atual (`dashboard.py`)

- **Portar para o FastAPI:**
  - Range/206;
  - token anti-CSRF;
  - CSP e checagem de Host/Origin;
  - fila serial;
  - `project_detail`;
  - `mark-posted` e `export-bundle`;
  - `open-folder`;
  - `/api/config` (presets de legenda, aspectos, marca);
  - `risk_seal`.
- **Não portar:**
  - escrever em `project.json` ao abrir;
  - marca chopify e hero de landing;
  - textos em inglês;
  - "Determinístico" como padrão silencioso;
  - nota geral saturada (10.0) como ordem principal.

## Veredito dos pilares (`cortes-pilares`, Julgar, 2026-11-21)

**Objeto julgado:** fazer o painel final completo (6.3 ampliada + `/api/capacidades` + B1–B4 e B7–B10) antes de terminar o E3.6 e o E5.

**Veredito: AJUSTAR → SEGUE com as 4 condições abaixo escritas na 6.3.** Nenhuma violação é estrutural; duas ideias do mapa feririam P1 e P3 se fossem implementadas como estão.

| Condição | Pilar | Regra |
|---|---|---|
| C1 | P1 | Só o cooldown que o próprio operador criou pode ser limpo pela tela. O cooldown automático (cadência, claim) não tem botão de limpar. Toda pausa ou limpeza é registrada com motivo. Liberar uma fonte barrada exige base de permissão e evidência; nunca é 1 clique. |
| C2 | P3 | Corte exportado no Pacote do Dia sem URL publicada vira pendência visível no "Hoje" até o link ser colado. Não existe "postei" sem ID rastreável. |
| C3 | P5 | 👍/👎 e a revisão são opcionais: corte aprovado pelos portões entra no Pacote do Dia sem depender de 👍. |
| C4 | regra 7 / AD-11 | "Só PC" quer dizer desktop no **Windows e no Linux**. Nada é exclusivo do Windows: a notificação tem equivalente nos dois sistemas ou é opcional. |

**Condições C1–C4 aceitas pelo dono em 2026-11-21.**

**Também:** o `CLAUDE.md`, a `architecture.md` (AD-2) e o exemplo do P4 ainda falam em Postgres. O `correct-course` atualiza o texto para o SQLite decidido; o pilar não muda.

## Para o dono decidir

1. ~~**B5:** worker para `picorte_enfileirar_video` ou descontinuar a ferramenta.~~ **Decidido pelo dono (2026-11-21): fila única.** A ferramenta MCP cria o projeto de verdade e o coloca na mesma fila do painel, chamando a mesma função de enfileirar do backend novo. Pedir pelo chat ou clicar no painel dá o mesmo resultado, e o job aparece no painel.
2. ~~**Banco:** seguir no SQLite ou migrar para Postgres antes do painel.~~ **Decidido pelo dono (2026-11-21): fica no SQLite.** O `correct-course` deve registrar o desvio do AD-2.
3. **Desktop only:** confirmar a mudança do CAP-14 e da 6.3 no `correct-course`.
