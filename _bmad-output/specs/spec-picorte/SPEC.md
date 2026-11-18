---
id: SPEC-picorte
companions:
  - companion-pipeline-multimodal.md
  - companion-escudo-risco.md
  - companion-integracoes-redes.md
  - companion-cerebro-bandit.md
  - ../planning-artifacts/pilares.md
  - ../planning-artifacts/concorrentes.md
  - ../../DESIGN.md
  - ../../PRODUCT.md
sources:
  - ../planning-artifacts/visao.md
---

> **Contrato canônico.** Este `SPEC.md` e os arquivos listados em `companions:` formam o contrato completo, validado contra os pilares (`P1 > P2 > P3 > P4 > P5`), para construir, testar e validar o **Picorte**.

# Picorte — Máquina Autônoma de Cortes de Alta Retenção

## Why

O operador (**Bomba**) quer maximizar a receita própria com canais de cortes separados por nicho (começando em **games** com o canal **Bomba Clips**) sem pagar ferramentas comerciais de autoclip (Opus Clip, Cortaí, Klap) e sem perder canais por strikes ou desmonetização. Ferramentas prontas cobram por minuto, selecionam trechos olhando quase apenas para a transcrição textual (perdendo momentos visuais e reações de gameplay), não protegem o canal contra Content ID ou políticas de publishers e não aprendem com o desempenho real dos vídeos publicados. O **Picorte** parte de uma base open-source local em Python (`mehbul/chopify` + transplantes de `fralapo/clippyme` e `FujiwaraChoki/supoclip`) rodando na própria GPU (**RTX 4060 Ti 8 GB**) e evolui até um sistema autônomo que caça tendências, lives ao vivo e clipes virais, detecta momentos por chat + áudio + visão computacional + texto, aplica engenharia de retenção para formatos curtos (<60s) e longos (3–5 min), blinda direitos autorais e aprende continuamente o que gera visualizações agora.

## Capabilities

- **CAP-1**
  - **intent:** O sistema ingere vídeos longos locais ou URLs de VODs (+2h) por meio de blocos de áudio e download seletivo de seções para descobrir candidatos sem baixar o vídeo completo antecipadamente.
  - **success:** Dado um VOD de mais de 2 horas, o sistema extrai e processa o áudio em blocos de 30 minutos e baixa apenas os segmentos de vídeo correspondentes aos cortes aprovados, retomando do último bloco salvo se interrompido.
- **CAP-2**
  - **intent:** O sistema monitora canais autorizados na Twitch, Kick e YouTube e captura segmentos deslizantes de transmissões ao vivo e novos VODs assim que entram no ar.
  - **success:** Quando um canal monitorado e autorizado fica ao vivo, o monitor captura segmentos de 3 a 5 minutos sem queda do processo e despacha para avaliação os blocos que superarem o limiar de reação.
- **CAP-3**
  - **intent:** O sistema busca clipes curtos já criados por terceiros (Twitch Clips e Shorts em alta das fontes autorizadas), avalia sua qualidade pelo motor multimodal e os re-transforma em obras próprias.
  - **success:** Um clipe de terceiro importado passa pelos mesmos portões de pontuação e risco que um VOD, recebe novo enquadramento, Cold Open, contexto e legenda nativa sem marca d'água alheia e atinge o Score mínimo de Transformação YPP antes de ir para a fila.
- **CAP-4**
  - **intent:** O sistema analisa a velocidade de mensagens e a densidade de emotes/reações do chat da live (e comentários com timestamp) para localizar em segundos os picos de atenção da audiência.
  - **success:** Dado o log de chat de uma live, o Sismógrafo do Chat identifica em menos de 2 segundos de CPU todos os intervalos onde a taxa de mensagens por segundo supera 4x a mediana móvel acompanhada de tokens de reação (`KKKK`, `LUL`, `CLIP`, `MENTIRA`, `???`).
- **CAP-5**
  - **intent:** O sistema pontua candidatos a corte combinando sincronizadamente sinais de Chat, Áudio (1 Hz), Visão Computacional de Games (2 fps: micro-expressões na facecam, eventos no HUD/Killfeed e ação visual) e Texto (LLM), permitindo ao operador escolher na UI qual motor de IA atua sozinho ou em dupla (Ollama, Claude, Gemini, ou um filtrando e outro acompanhando/lapidando) e ajustando início e fim às pausas naturais da fala.
  - **success:** O pontuador produz candidatos mesmo em trechos de gameplay sem diálogo, executa a etapa textual conforme o modo selecionado na UI (`Ollama`, `Claude`, `Gemini` ou pipeline `Filtro → Acompanhamento/Finalização`), registra a nota individual de cada um dos 4 sinais no banco e nunca corta uma palavra ao meio nas bordas do clipe.
- **CAP-6**
  - **intent:** O sistema reenquadra vídeos de gameplay para 9:16 separando automaticamente a webcam do streamer da tela do jogo, alternando dinamicamente o layout conforme o momento e aplicando zoom suave (*Sniper Crop*) na região da ação.
  - **success:** Em um corte vertical de live com facecam, o vídeo final alterna sem trepidação entre foco na facecam (narrativa), split-screen (facecam no topo + jogo embaixo) e tela cheia com PiP (ação intensa/cutscene), centralizando o quadrante de maior movimento do jogo.
- **CAP-7**
  - **intent:** O sistema aplica engenharia de retenção nos cortes verticais inserindo Cold Open Reverso (1,5s do ápice em `0:00`), Faixa de Contexto Instantâneo nos primeiros 2s, legendas dinâmicas palavra a palavra dentro da área segura de cada rede e Seamless Loop no final.
  - **success:** O arquivo `.mp4` vertical exportado inicia com o flash de 1,5s do clímax, exibe a faixa de contexto nos primeiros 2s, mantém 100% das legendas dentro das margens seguras da rede de destino e termina em um ponto de corte que conecta com o início.
- **CAP-8**
  - **intent:** O sistema alinha e compila automaticamente as reações de múltiplos streamers autorizados a um mesmo momento, trailer ou evento em um único corte multi-reação.
  - **success:** Dados 2 ou mais vídeos contendo o mesmo trecho de áudio/imagem de referência do jogo ou trailer, o sistema sincroniza os timestamps e renderiza um corte compilado com a transição entre as reações.
- **CAP-9**
  - **intent:** O sistema exporta pares formados por um Corte Curto Isca (<60s, 9:16) e um Corte Longo (3–5 min, 16:9), gerando automaticamente a thumbnail de alto CTR do vídeo longo com Visão Computacional.
  - **success:** Para cada corte longo de 3–5 min gerado, existe um Short vertical vinculado no banco e uma imagem PNG 1280×720 composta pelo frame de maior expressão facial da facecam (recortado do fundo), o frame de ação do jogo e até 3 palavras na tipografia do `DESIGN.md`.
- **CAP-10**
  - **intent:** O sistema bloqueia o download, o processamento e a publicação de qualquer fonte com status `desconhecida`, expirada ou na lista negra, bem como de trechos que violem as políticas cadastradas do publisher/jogo.
  - **success:** Tentativas de ingerir ou publicar uma fonte `desconhecida` ou um trecho marcado com violação de política do publisher (ex.: spoiler bloqueado) falham imediatamente no portão de entrada com registro do motivo no banco.
- **CAP-11**
  - **intent:** O sistema detecta música licenciada ao fundo do corte e remove seletivamente a música via separação neural de voz (`Demucs`) apenas nos segundos afetados, preservando a fala limpa do streamer.
  - **success:** Em um corte onde há música de fundo em parte do trecho, o áudio exportado mantém a voz inteligível do streamer nos segundos afetados sem música audível e sem alteração de tom (*pitch*) ou velocidade.
- **CAP-12**
  - **intent:** O sistema garante o "Selo Verde" nos primeiros 15 segundos de cada corte (aplicando micro-bleep e `***` em palavrões severos e barrando violência gráfica explícita na abertura) e bloqueia trechos onde o streamer assiste a vídeos protegidos de terceiros (*React Perigoso*).
  - **success:** Cortes com profanidade severa nos primeiros 15s saem com micro-bleep de 0,2s no timestamp exato da palavra e `***` na legenda; trechos com navegador/player de vídeo de terceiros aberto na tela principal são reprovados pelo detector visual.
- **CAP-13**
  - **intent:** O sistema calcula o Score de Transformação YPP (P2) e verifica a impressão digital perceptual (`pHash` visual + similaridade textual) de cada corte antes de aprová-lo para a fila de publicação.
  - **success:** Cortes sem elementos mínimos de transformação ou cujo `pHash`/transcrição colida com um corte já existente no banco são bloqueados automaticamente antes de entrar na fila de publicação.
- **CAP-14**
  - **intent:** O operador controla todo o ciclo de vida do sistema tanto por conversa com agentes (Claude Code e Gemini Antigravity via MCP e Skill) quanto pelo painel web responsivo "Estúdio do Criador" no desktop e no celular.
  - **success:** Todas as operações de gestão de fontes, disparo de cortes, inspeção de notas multimodais, revisão da fila e leitura de alertas de risco funcionam via ferramentas MCP e pelo painel web nas resoluções desktop e mobile.
- **CAP-15**
  - **intent:** O sistema publica (ou entrega pacote pronto no modo assistido pré-auditoria) em YouTube Shorts, YouTube Longo, TikTok, Instagram Reels e Facebook com título e legenda próprios por rede, crédito automático à fonte, vínculo *Related Video* (Short → Longo) e 1º Comentário Fixado "Isca de Debate".
  - **success:** Cada publicação registrada no banco possui título/descrição/crédito específicos da rede, comentário inicial de debate gerado e, no YouTube Shorts, referência preenchida para o vídeo longo correspondente quando existir.
- **CAP-16**
  - **intent:** O sistema monitora continuamente reivindicações de direitos autorais (claims) e strikes nos vídeos publicados e aciona um disjuntor global imediato ao primeiro problema.
  - **success:** Ao detectar ou simular um claim de bloqueio ou strike em qualquer corte de uma fonte, o sistema muda o status da fonte para `pausada_por_claim` e suspende em menos de 1 minuto todos os cortes pendentes daquela fonte nas 5 redes.
- **CAP-17**
  - **intent:** O sistema monitora tendências externas (Twitch Top Games/Streams, YouTube Gaming em alta e Calendário de Eventos), detecta menções cruzadas entre streamers (*Treta / Pingue-Pongue*) e multiplica a prioridade de fontes com Campanhas Pagas de Clipping (CPM) ativas.
  - **success:** O Radar atualiza a lista de assuntos/jogos em alta respeitando a expiração de 30 dias de dados de terceiros, alerta sobre fontes em alta ainda `desconhecidas`, sinaliza menções entre streamers mapeados e eleva o score de prioridade de fontes com campanha paga vigente.
- **CAP-18**
  - **intent:** O sistema coleta snapshots de métricas em 1h, 24h e 7d, atualiza um Bandit Contextual/Hierárquico com esquecimento do passado para priorizar o que dá views agora, recicla ganchos de cortes com boa retenção interna (*Reciclagem A/B*) e salva automaticamente vetores de cortes extremos para treinar modelos próprios na GPU.
  - **success:** Com snapshots gravados no Postgres, o Bandit reduz o peso de variáveis antigas em favor das recentes, agenda re-renderização de abertura para cortes com retenção pós-5s >70% e *swipe-away* ruim nos 3s, e grava os vetores de cortes `>3x` ou `<0.3x` da mediana em `dataset_rotulado/`.

## Constraints

- **Hierarquia estrita de pilares (`P1 > P2 > P3 > P4 > P5`):** nenhuma configuração, pico de tendência ou comando de publicação rápida pode contornar os portões de risco do **P1** ou o requisito de transformação real do **P2**.
- **Orçamento de VRAM serializado (8 GB na RTX 4060 Ti / 4 GB na GTX 1650):** modelos pesados de GPU (`faster-whisper`, detectores de visão, `Demucs`, `rembg`, `Ollama`) nunca rodam simultaneamente na VRAM; o executor carrega um estágio por vez e libera a memória antes do próximo, reservando lotes pesados para o **Modo Madrugada / Ocioso**.
- **Zero ferramentas pagas de autoclip e zero truques de evasão (A2):** proibido usar APIs pagas de corte/transcrição/agendamento (Opus Clip, Klap, AssemblyAI pago, Zernio pago) e proibido disfarçar conteúdo com espelhamento de imagem ou alteração de tom/velocidade de áudio.
- **Autenticação oficial e segredos cifrados (A4):** conexões com redes sociais usam exclusivamente OAuth oficial com tokens cifrados em AES-GCM no PostgreSQL; proibido pedir senhas ou usar automação de navegador (headless browser) para publicar.
- **Conformidade com a YouTube Data API v3:** dados não autorizados de canais de terceiros nunca são retidos por mais de 30 dias (III.E.4.d) e nunca são agregados para criar métricas derivadas comparativas entre canais de terceiros (III.E.2.a / III.E.4.h).
- **Estimativa prévia e teto de custo:** toda chamada opcional a API paga de LLM exige cálculo prévio de custo por hora de vídeo e respeito ao teto mensal definido pelo operador, com fallback automático para `Ollama` local (custo R$ 0).

## Non-goals

- **Sem SaaS e sem multi-tenant:** não construir `workspace_id`, isolamento de clientes, planos de assinatura, gateway de pagamento (Stripe), termos de uso para clientes nem painel administrativo multiusuário.
- **Não é um editor manual quadro a quadro (A1):** não construir timeline multipista estilo Premiere/CapCut; toda edição é algorítmica, cabendo ao operador apenas aprovar, ajustar início/fim simples ou trocar o gancho/legenda.
- **Não é um agendador genérico de posts (A3):** não suportar postagens avulsas de texto ou imagem sem corte de vídeo.
- **Sem Jump-Cut de Tempos Mortos + Compressor de Áudio:** funcionalidade explicitamente descartada pelo operador na decisão da E3.5.

## Success signal

Dado um canal monitorado e autorizado (ou VOD de gameplay com facecam), o **Picorte** rodando localmente na RTX 4060 Ti identifica os melhores momentos cruzando chat, áudio, visão computacional e texto, passa os candidatos pelo Escudo Anti-Strike (P1), renderiza o par Short 9:16 (com Cold Open 1,5s, Contexto 2s, Layout Dinâmico, Sniper Crop e Loop) + Corte Longo 16:9 (3–5 min com Thumbnail automática), publica (ou entrega o pacote pronto pré-auditoria) com 1º comentário de debate, recolhe as métricas de 1h/24h/7d no PostgreSQL e reordena sozinho a prioridade dos próximos cortes pelo Bandit sem tomar nenhum claim não tratado.

## Assumptions

- No lançamento inicial da operação (e enquanto as auditorias da Trilha Paralela T1 estiverem pendentes), a publicação opera em **modo assistido/manual**: o sistema gera o pacote completo (`.mp4` + `thumbnail.png` + `.meta.json` com título, descrição, crédito e 1º comentário prontos para copiar com 1 clique no painel web), e o operador cola o link/ID publicado para o coletor medir as views de 1h/24h/7d.
- O roteador de LLM (`llm_router.py`) suporta invocar **Claude** e **Gemini** tanto via CLI local autenticada na assinatura mensal do operador (`claude -p` e `agy -p`, custo R$ 0 de API) quanto via chaves de API opcionais, além do **Ollama** local na GPU (`http://localhost:11434`).

