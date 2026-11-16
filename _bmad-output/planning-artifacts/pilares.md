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

### P3 · Os dados decidem o que cortar e quando
Tudo o que é publicado é medido, e a medição (somada aos sinais externos de tendência: lançamentos, categorias em alta, assuntos do momento) decide o que será cortado, em que rede e em que horário. Uma funcionalidade que não alimenta nem usa esse ciclo é secundária.

- **Por quê:** o valor do produto em relação a cortar à mão está em aprender o que performa e chegar no pico de interesse (ex.: a semana de lançamento de um jogo) antes de quem corta sem dados.
- **Pergunta de teste:** *esta proposta gera dados que o ciclo usa, ou usa os dados do ciclo para decidir?* Se nenhuma das duas, é secundária. Se ela impede a medição (ex.: publicação sem ID rastreável), viola.
- **Reforça:** o radar de tendências priorizar na fila os cortes de um jogo que acabou de entrar no topo da Twitch.
- **Viola:** permitir publicar por fora do sistema e "registrar depois", deixando cortes sem métricas ligadas a eles.

### P4 · A inteligência de seleção é nossa
Detectar, pontuar e decidir quais trechos viram corte é o núcleo do produto, e esse núcleo (critérios, dados rotulados, modelos, pesos do bandit) pertence ao projeto. Peças comuns podem vir de fora (transcrição, um LLM por API, bibliotecas de visão), desde que sejam trocáveis e não levem a decisão embora.

- **Por quê:** quem decide o corte é quem aprende. Se a seleção estiver numa ferramenta de terceiros, o aprendizado e a margem ficam com ela.
- **Pergunta de teste:** *se este fornecedor sumir amanhã, continuamos sabendo escolher cortes, com os mesmos dados e critérios?* Se não, viola.
- **Reforça:** guardar cada pontuação, rótulo e resultado no nosso banco, mesmo quando a pontuação veio de um LLM por API.
- **Viola:** mandar o vídeo para uma API de autoclip e publicar os trechos que ela escolher.

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

| | Atual (MVP) | Futuro (SaaS, fora do MVP) |
|---|---|---|
| Quem | O próprio dono, operador de vários canais separados por nicho, começando em **games** | *Hipótese:* operadores de canais de cortes, participantes de campanhas de clipping e criadores que querem cortes autorizados do próprio conteúdo |
| Fontes | Gameplay gravado por ele mesmo (menor risco), cortes de streamers com permissão, material oficial (alto risco de claim) | As fontes de cada cliente, com o status de permissão declarado pelo cliente |
| O que muda | — | Isolamento por workspace; responsabilidade sobre as fontes transferida por termos de uso; onboarding; os portões de risco continuam obrigatórios e não podem ser desligados pelo cliente (P1) |

## O que é um "corte bom"

Linguagem de produto; as métricas e os pesos ficam para a `cortes-ml` (E9). Os itens marcados com *(hipótese)* vêm de blogs e serão validados com dados reais.

**Todo corte bom:**
1. **Passa em todos os portões de risco** (P1): fonte com permissão, sem música licenciada audível, sem spoiler fora da janela, sem conteúdo barrado pela política do publisher, sem nada na abertura que custe a monetização.
2. **Entrega o momento rápido:** abre já na reação, na jogada ou no fato, sem intro nem saudação; o payoff chega antes que o espectador precise de contexto *(hipótese: gancho em 1–2 s, payoff em menos de 30 s)*.
3. **Se entende sozinho**, sem ter visto o vídeo original.
4. **Tem um momento marcante:** engraçado, inesperado, habilidoso, polêmico ou emocionante. Gameplay "normal" não é corte.
5. **Tem identidade própria** (P2): título específico (em games, com o nome do jogo e o que acontece), nunca genérico ou numerado ("melhores momentos #315"); legenda legível; crédito à fonte.
6. **É nativo da rede** (P2): título, legenda, duração e áreas seguras pensados para onde vai, sem marca d'água de outra rede *(hipótese: menos de 60 s nos formatos verticais)*.

**Em games, em particular** *(hipóteses)*: física quebrada, NPC absurdo e falha inesperada rendem; facecam com reação aumenta a retenção; o pico de interesse está na semana de lançamento e em grandes atualizações ou polêmicas.

**Sinais de corte ruim:** contexto longo antes do payoff; intro; ausência de momento marcante; título genérico; corte cru sem legenda; música com direitos.

## Histórico

| Data | Mudança | Motivo |
|---|---|---|
| 2026-11-16 | Primeira versão (rascunho), a partir do rascunho do usuário. Risco separado do antigo "autônomo com freio" e promovido a P1. Antigos P4 (todas as redes) e P5 (transformar) fundidos em P2. "Ciclo fechado" passa a incluir os sinais de tendência. | Pilar com dois assuntos não decide; o risco precisava estar no topo da prioridade; o radar de tendências é parte da decisão por dados. |
| 2026-11-16 | P1 ganha a regra de status: fonte `desconhecida` não publica até o status mudar; gameplay próprio e material de campanha ativa nascem autorizados (o da campanha expira com ela). | Decisão do usuário (opção "não publica" em vez de "publica com revisão"). |
| 2026-11-16 | Correção na Ordem de prioridade: fonte desconhecida em alta "não sai até o status ser alterado" (antes dizia "sem revisão", que descrevia a opção recusada). | Contradição com a decisão acima. |
| 2026-11-16 | P2 suavizado: exige título, legenda, duração e áreas seguras por rede e proíbe marca d'água de outra rede, mas permite o mesmo vídeo vertical em Shorts, Reels e TikTok; pergunta de teste e exemplos ajustados. | Exigir diferenças artificiais no vídeo beirava o disfarce de conteúdo barrado pelo A2. |
| 2026-11-16 | **Aprovado** pelo usuário. | — |
