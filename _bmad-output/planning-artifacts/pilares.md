# Pilares e anti-pilares — projeto-cortes

**Status:** aprovado · **Data:** 2026-11-16 · **Skill:** `cortes-pilares`

> **Objetivo do produto** (não é pilar): gerar receita com cortes de vídeo publicados em várias redes.
> Os pilares dizem **como** o produto persegue esse objetivo e **o que ele aceita perder** por isso.

## Pilares

### P1 · Canal protegido antes de alcance
O produto nunca troca segurança do canal por alcance. Claim, strike, desmonetização e banimento custam mais do que qualquer corte rende. As regras de risco (status de permissão da fonte, política do publisher/jogo, música licenciada, janela de spoiler, regras de monetização da rede, lista negra, pausa automática) são portões automáticos que nenhum modo, configuração ou pressa contorna.

- **Status da fonte:** fonte `desconhecida` **não publica** até o operador mudar o status, sem exceção por pico ou tendência. Duas origens nascem autorizadas: **gameplay gravado pelo próprio operador** e **material de campanha de clipping**, este só enquanto a campanha estiver ativa (o status expira com ela).
- **Por quê:** um único strike pode derrubar um canal inteiro e, com ele, todo o histórico que alimenta o ciclo de dados. Num nicho como games, com publishers agressivos (ex.: política da Rockstar para GTA 6) e músicas licenciadas dentro do jogo, o risco é diário, não excepcional.
- **Pergunta de teste:** *esta proposta pode fazer sair um corte que um portão de risco bloquearia, ou enfraquece a detecção ou a pausa?* Se sim, viola.
- **Reforça:** checar automaticamente se há violência gráfica na abertura de cortes de jogos violentos e mover o gancho para depois da janela que custa a monetização.
- **Viola:** um botão "publicar mesmo assim" que ignora o status "desconhecida" da fonte para aproveitar um pico de lançamento.

### P2 · O corte é obra própria e nativa de cada rede
Todo corte acrescenta algo que não estava na fonte (gancho e título próprios, legenda, contexto, crédito) e sai pensado para a rede onde vai ser publicado: **título, legenda, duração e áreas seguras** de cada rede. Nunca é um reupload cru e **nunca leva marca d'água de outra rede**. O mesmo vídeo vertical pode ir para Shorts, Reels e TikTok, desde que cada publicação tenha título e legenda próprios. Diferenças artificiais no vídeo não são exigidas; disfarçar conteúdo é barrado (A2).

- **Por quê:** a transformação real é o que sustenta a monetização de conteúdo reutilizado (YPP) e reduz o risco de direitos. Título, legenda e áreas seguras certos para cada rede é o que retém; marca d'água de outra rede derruba a distribuição.
- **Pergunta de teste:** *o que sai desta proposta poderia ser confundido com a fonte original, chega a uma rede com título ou legenda feitos para outra, invade as áreas seguras da rede ou leva marca d'água de outra rede?* Se sim, viola.
- **Reforça:** o mesmo vídeo vertical vai para Shorts, Reels e TikTok, cada um com título e legenda próprios e o texto queimado dentro da área segura de cada rede; o corte longo de 4 min do mesmo trecho ganha título e gancho próprios.
- **Viola:** baixar o corte já publicado no TikTok (com a marca d'água) e subir esse arquivo no Reels; ou um modo "publicação rápida" que sobe o trecho cru, sem legenda nem título próprio.

### P3 · Os dados de agora decidem o que cortar e quando
Tudo o que é publicado é medido, e a medição (somada aos sinais externos de tendência: lançamentos, campeonatos, categorias em alta, assuntos do momento) decide o que será cortado, em que rede e em que horário. **O que funcionou ontem pode não funcionar hoje:** o sistema dá menos peso aos resultados antigos e reage rápido quando o interesse muda. Ele aposta no que está subindo e abandona o que esfriou, mesmo que já tenha sido um sucesso. Uma funcionalidade que não alimenta nem usa esse ciclo é secundária.

- **Por quê:** o valor do produto em relação a cortar à mão está em perceber o que performa e chegar no pico de interesse (a semana de lançamento de um jogo, um campeonato, o streamer do momento) antes de quem corta sem dados. Em games, o interesse muda em dias; um sistema que confia no histórico chega atrasado.
- **Pergunta de teste:** *esta proposta gera dados que o ciclo usa, ou usa os dados do ciclo para decidir, dando mais peso ao recente?* Se não faz nenhuma das duas coisas, é secundária. Se ela impede a medição (ex.: publicação sem ID rastreável) ou trata um resultado antigo como se valesse tanto quanto um recente, viola.
- **Reforça:** o radar de tendências priorizar na fila os cortes de um jogo que acabou de entrar no topo da Twitch; o modelo reduzir a aposta num streamer cujos cortes caíram nas últimas semanas, apesar do bom histórico.
- **Viola:** permitir publicar por fora do sistema e "registrar depois", deixando cortes sem métricas ligadas a eles; ou um ranking "melhores assuntos de todos os tempos" que continua priorizando um jogo que esfriou.

### P4 · A inteligência de seleção é nossa
Detectar, pontuar e decidir quais trechos viram corte é o núcleo do produto, e esse núcleo (critérios, dados rotulados, modelos, pesos do bandit) pertence ao projeto. Partir de código open-source local (`mehbul/chopify`, `fralapo/clippyme`, padrões de `FujiwaraChoki/supoclip`) e usar peças comuns (transcrição, um LLM por API ou local via Ollama, bibliotecas de visão computacional e áudio) reforça este pilar, desde que rodem sob nosso controle, sejam trocáveis e não levem a decisão nem os dados embora.

- **Por quê:** quem decide o corte é quem aprende. Se a seleção estiver numa ferramenta paga de terceiros na nuvem, o aprendizado e a margem ficam com ela.
- **Pergunta de teste:** *se um fornecedor externo sumir amanhã, continuamos sabendo escolher cortes na nossa máquina, com os mesmos dados, modelos e critérios?* Se não, viola.
- **Reforça:** partir do motor local open-source do `chopify` (`evidence.py` + `visual.py` + `score_clips.py`), tunar com nossos detectores de visão computacional/chat e guardar cada pontuação, vetor (autocaptura de dataset rotulado) e resultado no nosso banco Postgres para treinar modelos próprios na RTX 4060 Ti.
- **Viola:** mandar o vídeo para uma API paga de autoclip (Opus Clip, Klap, etc.) e publicar os trechos que ela escolher.

### P5 · Autônomo por padrão, revisável por escolha
Da fonte à publicação, o sistema funciona sozinho. O operador pode ligar a revisão manual (por canal, por fonte ou por rede) e decidir corte a corte, mas a autonomia é o caminho padrão e nenhuma etapa obrigatória depende de trabalho manual.

- **Por quê:** o objetivo é escala com várias contas; um fluxo que exige uma pessoa por corte não escala. A revisão existe para dar confiança, não como muleta permanente.
- **Pergunta de teste:** *esta proposta cria um passo manual obrigatório no caminho normal?* Se sim, viola (a menos que o P1 exija).
- **Reforça:** uma fila de revisão opcional que, desligada, deixa os cortes aprovados pelos portões seguirem sozinhos.
- **Viola:** exigir que o operador escreva o título de cada corte antes de publicar.

## Ordem de prioridade

**P1 > P2 > P3 > P4 > P5**

- **P1 vence todos:** se o gancho ideal (P3, dados) cai numa janela que custa a monetização, o gancho muda de lugar. Se uma fonte desconhecida está em alta, ela não sai até o status ser alterado (P5 cede).
- **P2 vence P3:** se os dados mostrarem que o reupload cru performa melhor, ele continua proibido.
- **P3 vence P4:** se um componente de terceiros medir ou prever melhor, ele pode entrar como peça, desde que os dados e a decisão continuem nossos.
- **P4 vence P5:** autonomia não justifica entregar a decisão a uma ferramenta externa.

## Anti-pilares

### A1 · Não é um editor de vídeo manual
- **Por quê:** competir com CapCut ou Premiere desvia o produto do ciclo automático (P3, P5).
- **Barra:** uma timeline de edição quadro a quadro, camadas e efeitos. *Permitido:* ajustar início e fim de um corte e editar título e legenda na revisão.

### A2 · Não é uma fábrica de spam nem de truques
- **Por quê:** volume sem critério e evasão de detecção são o caminho mais curto para banimento (P1) e para a perda do YPP (P2).
- **Barra:** contas falsas; volume acima do que o ciclo justifica; reupload cru; **disfarçar conteúdo para escapar do Content ID** (espelhar a imagem, alterar o tom da música, acelerar). *Distinção:* **remover ou substituir** música licenciada é proteção legítima; **disfarçá-la** para não ser detectada é truque e está barrado.

### A3 · Não é um agendador genérico de posts
- **Por quê:** era o ReSocial. O produto é sobre cortes de vídeo; texto e imagem soltos dispersam o foco.
- **Barra:** um compositor de posts de texto e imagem para qualquer rede. *Permitido:* texto que acompanha um corte (título, descrição, comentário fixado).

### A4 · Não contorna as APIs oficiais
- **Por quê:** login com senha e automação de navegador violam os termos das redes e colocam as contas em risco (P1).
- **Barra:** um bot de navegador que publica como público enquanto a auditoria da API não sai. *Permitido como plano B:* o sistema gera o arquivo final e uma **pessoa** publica manualmente.

### A5 · Não inventa números nem promete ganhos
- **Por quê:** o ciclo de dados (P3) só vale se os números forem reais. Para o futuro SaaS, prometer receita é risco jurídico e de reputação.
- **Barra:** um painel que mostra estimativas ou dados de exemplo sem marcação clara; marketing com "ganhe R$ X por mês".

## Público

| | Operação Própria (Escopo Total do Projeto) |
|---|---|
| **Quem** | O próprio dono (Bomba), operador de vários canais separados por nicho, começando em **games** com o canal **Bomba Clips**. |
| **Fontes** | Gameplay gravado por ele mesmo (menor risco), lives/VODs de streamers com permissão, clipes virais de terceiros avaliados e re-transformados, e material de campanhas pagas de clipping (enquanto ativas). |
| **Diretriz sobre SaaS** | **Fora de escopo.** O foco é 100% lucrar com a operação dos próprios canais (AdSense/YPP em vídeos longos e curtos + campanhas pagas de clipping/CPM). Não se gasta tempo com multi-tenant (`workspace_id`), cobrança ou onboarding de terceiros. Se um dia no futuro decidir virar SaaS, isso será tratado lá na frente. |

## O que é um "corte bom"

Linguagem de produto; as métricas e os pesos ficam para a `cortes-ml` e o motor multimodal. Os itens marcados com *(hipótese)* serão validados e recalibrados continuamente com os dados reais dos canais.

**Todo corte bom:**
1. **Passa em todos os portões de risco** (P1): fonte com permissão, sem música licenciada audível (ou com música removida via separação neural de voz `Demucs` seletiva), sem spoiler fora da janela, sem conteúdo barrado pela política do publisher, sem "react perigoso" de vídeo de terceiro aberto pelo streamer, e com os primeiros 15 segundos limpos para monetização ("Selo Verde 15s": sem violência gráfica e com micro-bleep/censura automática em termos sensíveis).
2. **Trava o espectador nos primeiros 2 segundos:** usa **Cold Open Reverso** (1,5s do clímax visual/sonoro colado em `0:00` antes da história começar) + **Faixa de Contexto Instantâneo** nos primeiros 2s ("Narrador Invisível" situando o desafio/momento), entregando o payoff sem enrolação.
3. **Fecha em Loop Infinito (nos verticais):** em Shorts/Reels/TikTok, o ponto de corte final é ajustado para que a última frase/frame conecte com o segundo `0:00` (*Seamless Loop*), estimulando replay automático (>100% de retenção).
4. **Se entende sozinho**, sem ter visto o vídeo original.
5. **Tem um momento marcante (detectado por Texto + Áudio + Visão + Chat):** engraçado, inesperado, habilidoso, polêmico ou emocionante, confirmado pela convergência de sinais: explosão no **Sismógrafo do Chat da Live** (`msgs/s` e emotes), pico de áudio (grito/risada), **Visão Computacional** (micro-expressões na facecam, eventos de Kill/Victory/Wasted no HUD do jogo, ação intensa) e texto. Gameplay "normal" não é corte.
6. **Tem identidade e transformação real** (P2, Score YPP):
   - Título específico (em games, com o nome do jogo e o que acontece), nunca genérico ou numerado ("melhores momentos #315");
   - Enquadramento inteligente: **Troca Dinâmica de Layout** (alternando entre foco na facecam na história, split Facecam + Gameplay na reação e tela cheia com PiP na ação) + **Sniper Crop** (zoom suave no quadrante onde a ação ocorre);
   - Quando aplicável a grandes eventos/trailers/bugs: **Compilação Cross-Streamer** (reação de múltiplos streamers ao mesmo momento alinhado por imagem/áudio do jogo);
   - **1º Comentário Fixado "Isca de Debate"** gerado junto com o corte para segurar espectadores discutindo nos comentários;
   - **Funil Short Isca → Vídeo Longo (3–5 min):** quando o momento rende história maior, o Short vertical serve de isca ligada (via *Related Video*) ao corte longo 16:9 de 3–5 min acompanhado de **Thumbnail automática de alto CTR** (frame de maior expressão na facecam recortado + ação do jogo + 3 palavras).

**Sinais de corte ruim:** contexto longo antes do payoff; intro; ausência de momento marcante; título genérico; corte cru sem legenda ou abaixo do Score mínimo de Transformação YPP; música com direitos audível; streamer assistindo vídeo protegido de terceiro.

## Histórico

| Data | Mudança | Motivo |
|---|---|---|
| 2026-11-16 | Primeira versão (rascunho), a partir do rascunho do usuário. Risco separado do antigo "autônomo com freio" e promovido a P1. Antigos P4 (todas as redes) e P5 (transformar) fundidos em P2. "Ciclo fechado" passa a incluir os sinais de tendência. | Pilar com dois assuntos não decide; o risco precisava estar no topo da prioridade; o radar de tendências é parte da decisão por dados. |
| 2026-11-16 | P1 ganha a regra de status: fonte `desconhecida` não publica até o status mudar; gameplay próprio e material de campanha ativa nascem autorizados (o da campanha expira com ela). | Decisão do usuário (opção "não publica" em vez de "publica com revisão"). |
| 2026-11-16 | Correção na Ordem de prioridade: fonte desconhecida em alta "não sai até o status ser alterado" (antes dizia "sem revisão", que descrevia a opção recusada). | Contradição com a decisão acima. |
| 2026-11-16 | P2 suavizado: exige título, legenda, duração e áreas seguras por rede e proíbe marca d'água de outra rede, mas permite o mesmo vídeo vertical em Shorts, Reels e TikTok; pergunta de teste e exemplos ajustados. | Exigir diferenças artificiais no vídeo beirava o disfarce de conteúdo barrado pelo A2. |
| 2026-11-16 | **Aprovado** pelo usuário. | — |
| 2026-11-16 | **Revisão do P3** (modo Revisar): título passa a "Os dados de agora decidem…"; enunciado, pergunta de teste e exemplos explicitam que o passado perde peso e que o sistema reage rápido quando o interesse muda. Documento afetado: `visao.md` (veredito continua "segue"; a ressalva sobre esquecimento fica resolvida). | Pedido do usuário: "o que funcionou ontem pode não funcionar hoje" é o centro da visão do produto. |
| 2026-11-18 | **Revisão E3.5 (Ajuste de Rumo + Brainstorming):** (1) SaaS e multi-tenant retirados do escopo na seção Público — foco 100% em lucrar com os próprios canais de cortes; (2) P4 explicita o uso da base open-source local (`chopify`, `clippyme`, padrões de `supoclip`) sob controle local; (3) "O que é um corte bom" incorpora as alavancas aprovadas no brainstorming (Sismógrafo do Chat, Cold Open 1,5s, Seamless Loop, Contexto 2s, Cross-Streamer, Sniper Crop, Layout Dinâmico, HUD/Killfeed, Micro-expressões, Funil Short→Longo 4min + Thumbnail, Selo Verde 15s, Demucs seletivo, Detector de React Perigoso). Veredito `cortes-pilares` (modo Julgar) sobre o novo Plano Mestre Evolutivo: **segue**. | Decisão do usuário de priorizar lucro rápido e máximo com canais próprios partindo de clones open-source locais e evoluindo em camadas. |
