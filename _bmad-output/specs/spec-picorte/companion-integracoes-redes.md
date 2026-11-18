# Companion 3 — Integrações por Plataforma, Áreas Seguras, Controle por Agente e Conformidade de API

> Parte integrante do contrato `SPEC-picorte` (`CAP-14`, `CAP-15`, `CAP-17`). Define os contratos das 5 redes sociais, áreas seguras de legenda, servidor MCP e regras de conformidade com APIs externas.

---

## 1. Matriz Técnica das 5 Redes Sociais (`CAP-15`)

Base de código para transplante: `referencias/FujiwaraChoki_supoclip/backend/src/social/` (`base.py`, `youtube.py`, `tiktok.py`, `instagram.py`) + módulo Facebook Graph API.

| Rede | Formato / Resolução | Duração Alvo | Cota / Limite da API Oficial | Comportamento sem Auditoria (T1) | Margens da Área Segura (1080×1920) para Legenda `.ass` |
|---|---|---|---|---|---|
| **YouTube Shorts** | `9:16` (`1080×1920`), H.264 + AAC | `15s a 58s` *(margem de segurança <60s)* | `videos.insert` = **1.600 unidades** de 10.000/dia (~6 uploads/dia por projeto GCP). `commentThreads.insert` = 50 unidades. | App não auditado posta apenas como `private`. Enquanto não auditado, usar publicação assistida ou solicitar auditoria logo no início. | Topo livre: `>= 220px`<br>Base livre: `>= 420px` (acima do título, canal e áudio)<br>Direita livre: `>= 150px` (botões like/comment) |
| **YouTube Longo (3–5 min)** | `16:9` (`1920×1080`), H.264 + AAC + **Thumbnail PNG `1280×720`** | `180s a 300s` (3 a 5 min) | `videos.insert` (1.600) + `thumbnails.set` (50) + `commentThreads.insert` (50) = **1.700 unidades**. | Mesmo limite acima. Vinculado como destino do campo *Related Video* do Short Isca correspondente. | `caption_margin_v = 95px` em `1920×1080`. |
| **TikTok** | `9:16` (`1080×1920`), H.264 + AAC | `15s a 60s` (ou até 10 min) | Content Posting API (`video.publish` / `video.upload`). Limite diário definido pela conta/app (~15 posts/dia). | Sem auditoria aprobada, posta apenas como `SELF_ONLY` (privado) ou envia para a caixa de entrada/rascunho do criador. | Topo livre: `>= 200px`<br>Base livre: `>= 440px` (descrição longa + som)<br>Direita livre: `>= 160px` |
| **Instagram Reels** | `9:16` (`1080×1920`), H.264 + AAC | `15s a 60s` (até 90s) | Instagram Graph API (`/media` → `/media_publish`). Exige conta Business ou Creator vinculada a uma Página. Até 25–50 posts/24h. | Exige App Review (`instagram_content_publish`, `instagram_basic`, `pages_read_engagement`). Modo assistido enquanto pendente. | Topo livre: `>= 220px`<br>Base livre: `>= 420px`<br>Direita livre: `>= 140px` |
| **Facebook Reels / Vídeo** | `9:16` (`1080×1920`) ou `16:9` (`1920×1080`) | `15s a 60s` (Reels) / `3–5 min` (Vídeo) | Facebook Pages Graph API (`/video_reels` / `/videos`). | Mesmo app Meta da aprovação do Instagram. | Mesma área segura unificada (`caption_margin_v >= 440px` da base). |

### Regra de Área Segura Unificada para Vídeo Vertical (`9:16`)
Para permitir que o **mesmo arquivo `.mp4` vertical** seja publicado em Shorts, TikTok, Reels e Facebook Reels (conforme autorizado pelo **P2**, trocando apenas título, descrição, hashtags e 1º comentário em cada rede), a zona segura universal de queima de legendas `.ass` em `1080×1920` é:
- **Horizontal (`x`):** entre `80px` e `920px` (deixando `160px` livres na direita para os ícones de engajamento de todas as redes);
- **Vertical (`y`):** centro das legendas posicionado entre `1150px` e `1420px` (ou seja, `caption_margin_v = 450px` a partir da borda inferior), nunca invadindo os `440px` inferiores nem os `220px` superiores (onde entra a Faixa de Contexto de 2s entre `y = 240px` e `y = 360px`).

---

## 2. Conformidade com as Políticas das APIs Externas (`CAP-17`, `CAP-18`)

1. **YouTube Data API v3 — Regra de 30 Dias para Dados de Terceiros (III.E.4.d):**
   - Todo dado obtido sobre canais ou vídeos de terceiros pelo **Radar de Tendências** (`videos.list?chart=mostPopular`, buscas de vídeos em alta) ou pelo **Caçador de Clipes** recebe um campo `expires_at = fetched_at + INTERVAL '30 days'`.
   - Um job diário de limpeza (`cleanup_external_cache.py`) apaga fisicamente ou atualiza registros vencidos antes de completarem 30 dias.
2. **YouTube Data API v3 — Proibição de Métricas Derivadas sobre Terceiros (III.E.2.a / III.E.4.h / III.L):**
   - O sistema **não** calcula rankings compostos nem métricas derivadas comparando canais de terceiros entre si; o Radar usa diretamente a ordenação que a própria API oficial entrega (`chart=mostPopular` no YouTube e `Get Top Games` / `Get Streams` na Twitch).
   - O cálculo de recompensa normalizada pela mediana do canal e os snapshots de 1h/24h/7d do Bandit são calculados **exclusivamente sobre os nossos próprios canais autorizados** (ex.: Bomba Clips). Na auditoria da T1, inclui-se o pedido da permissão **III.L** por segurança adicional.
3. **Twitch API e Kick:**
   - Uso da API oficial da Twitch (Helix: `Get Top Games`, `Get Streams`, `Get Clips`) via Client ID + OAuth App Access Token.

---

## 3. Controle por Agente (MCP + Skill) e Painel Web (`CAP-14`)

1. **Servidor MCP (`picorte_mcp`) e Skill (`.claude/skills/picorte-operador/SKILL.md`):**
   - Inspirado em `referencias/FujiwaraChoki_supoclip/mcp/src/supoclip_mcp/server.py` e `referencias/mehbul_chopify/docs/AGENT-API.md`.
   - Permite que tanto o **Claude Code** quanto o **Gemini (Antigravity)** executem todo o fluxo por conversa: consultar o Radar, cadastrar fontes/campanhas/políticas de publisher, disparar cortes de VOD ou live, inspecionar as 4 notas (chat/áudio/visão/texto), aprovar/rejeitar cortes e consultar o estado do Bandit.
2. **Painel Web "Estúdio do Criador" (`DESIGN.md`):**
   - Segue fielmente `DESIGN.md`, `design/tokens/tokens.css`, `design/brand/` e `design/mock/fila.html`.
   - Layout próprio para **Desktop** e para **Celular** (operação rápida de uma mão para aprovar fila, ver alertas âmbar "pede você" e alertas vermelhos do Escudo P1).
