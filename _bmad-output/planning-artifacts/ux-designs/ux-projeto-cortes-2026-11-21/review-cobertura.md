---
title: Revisão de cobertura — EXPERIENCE.md do Estúdio do Criador
date: 2026-11-21
lente: cobertura (mecânica + julgamento)
alvo: EXPERIENCE.md (mesma pasta)
fontes: brainstorm-intent.md (áreas 1–10), epics.md (6.3–6.8), SPEC.md (CAP-14), .memlog.md
fora_do_escopo: DESIGN.md vazio de propósito (tokens e lado visual dos componentes = N/A)
---

# Revisão de cobertura — EXPERIENCE.md

## Veredito geral

O spine é sólido onde o dono mais vive (Lives, Sala do vídeo, Revisão, Publicação) e o Contrato de Travas é a melhor parte: dá a quem implementa uma regra única para todo travado. A cobertura cai nas áreas de gestão (Fontes, Escudo, Sistema, Configurações), que aparecem na IA mas não têm componentes, estados nem fluxo, e o critério de entrada no Pacote do Dia e de "link pendente" ainda deixa C2 e C3 abertos a interpretação. Não é bloqueante para a direção visual, mas as histórias 6.7 e 6.8 não são implementáveis só com este arquivo.

**Contagem:** 0 crítico · 10 alto · 27 médio · 7 baixo.

---

## 1. Cobertura de capacidades → superfícies — **fraco**

Só os IDs/ACs que faltam ou estão ambíguos. Os demais (SIS-6/7/8/10, FIL-2/3/5/6, REV-1/2/6/7/8, ESC-1/7/9, SAU-1/3, PUB-1/2/3/5, LIV-1/3/4/5/6, MET e RAD como área travada, AC 6.5.4/6.5.5, AC 6.6.1/6.6.2/6.6.6) têm superfície e componente/estado.

- **[alto]** A área 1 "Hoje / Sistema" do mapa ficou sem superfície. SIS-3 (lock de VRAM), SIS-5 (banco SQLite como capacidade), SIS-11 (yt-dlp, ejs, node, demucs), SIS-12 (servidor MCP, B5) e as sondas exigidas pela AC 6.3.3 (GPU/VRAM, disco, `yt-dlp`, `node`, `demucs`) não aparecem em nenhum lugar. A barra de status só cobre Ollama, Gemini e Claude (IA › Barra de status global). *Correção:* criar um bloco "Sistema" (no Motor ou nas Configurações) com uma linha por sonda/capacidade SIS-*, cada uma seguindo o Contrato de Travas, e dizer que a barra de status resume "N sondas com problema" levando a ele.
- **[alto]** Fontes tem só a "Linha de fonte". Faltam superfície e componente para os itens da AC 6.7.1: FON-3 tentativas barradas, FON-4 elo fonte → vídeos → cortes (travado `dado`), FON-5 políticas por jogo, FON-6 cadastro de campanhas (com expiração, que muda o status da fonte), FON-7 pausas com histórico, FON-8 editor de dossiê (Component Patterns; IA › Fontes). *Correção:* descrever as seções da página Fontes (abas ou blocos) com um componente por item e o estado vazio/travado de cada um.
- **[alto]** ESC-8 (claim registrado à mão → pausa da fonte, AC 6.7.2) não tem componente, formulário nem estado; a IA só diz "claims registrados" (IA › Escudo). É o caminho P1 mais importante que o operador executa à mão hoje. *Correção:* componente "Registrar claim" (rede, URL do vídeo afetado, tipo de claim, motivo) com a consequência escrita antes de confirmar ("pausa todos os cortes da fonte X em todas as redes") e o resultado mostrado no Escudo, nas Fontes e na Publicação.
- **[alto]** FIL-1 está `ligado` mas só tem entrada por card ou `Ctrl+V`. Criar projeto a partir de **arquivo local** (gameplay próprio, que nasce autorizado) e o **lote de 1–100** (`/api/batch`) não têm superfície (IA; Key Flows). *Correção:* definir onde se sobe um arquivo (arrastar na vitrine ou botão na Fila) e o lote, com o portão P1 respondendo também para arquivo ("gameplay próprio") e por item do lote.
- **[alto]** REV-10 a REV-15 (Cold Open/Loop, layout dinâmico/Sniper Crop, par Short↔Longo, arcos, cross-streamer, nobada/`standalone`/bordas) são travados `codigo`, mas o spine não diz onde ocupam "o lugar real" (Contrato de Travas, regra 1). Quem implementa não sabe se ficam no Painel de corte, na Ficha ou em lugar nenhum. *Correção:* listar cada um com o lugar: p. ex., Cold Open/Loop e layout dinâmico como opções travadas no Painel de corte (3) Enquadramento; par Short↔Longo na Ficha e no Cartão de publicação; arcos e compilação como seção travada na Revisão.
- **[médio]** Configurações (AC 6.7.5) aparece só na IA: não tem componente nem estado para credenciais de app (campo de segredo mascarado, regra 3), preset de visão, marca e legendas, Modo Madrugada (`parcial`, SIS-4), custos (`travado`/`parcial`, SIS-13) e notificações. O botão **Configurar** do contrato precisa "levar direto ao campo certo" e nada define esse endereço (Contrato de Travas; IA › Configurações). *Correção:* linha "Campo de credencial" e "Seção de configuração" em Component Patterns, com âncora por campo (ex.: `/configuracoes#twitch`) e os estados validando / recusada / salva.
- **[médio]** ESC-2 a ESC-6 (Selo Verde 15s, Demucs, React Guard, YPP/originalidade TikTok/pHash, limpeza de texto por rede) não têm forma definida: a Ficha só diz "Veredito P1 por rede" (Component Patterns › Ficha do corte). *Correção:* especificar que o veredito abre em linhas por verificação (cada uma aprovado / barrado / não verificado + motivo), igual aos sinais.
- **[médio]** AC 6.7.3 pede `confianca_projeto` travada até a 3.6.5 (SAU-2) e o mapa tem SAU-5 (canário/`yt-dlp` diário) travado; nenhum aparece. O progresso "x de 20 VODs com gabarito" (AC 6.7.4, SAU-4) não está no Placar de benchmark, só no estado "Área inteira travada" do Aprendizado (Component Patterns › Matriz de saúde / Placar). *Correção:* pôr `confianca_projeto` travada na frase-resumo da Matriz, SAU-5 no bloco Sistema e a barra x/20 no Placar (o Aprendizado pode só repetir o contador).
- **[médio]** AC 6.6.5 coloca Caça Profunda e busca por pergunta na Revisão (projeto já processado, `picorte_buscar_por_pergunta`); o spine só as tem no Painel de corte, antes de cortar (Component Patterns › Painel de corte (5)(6)). *Correção:* adicionar à Revisão "Caçar de novo (profunda)" e "Buscar por pergunta neste VOD", gerando novos cortes na mesma lista.
- **[médio]** Itens da Revisão sem componente: editor de transcrição e legenda "recolhido por padrão" (AC 6.6.5, REV-3); diferença entre preview 480p e render final (REV-4); thumbnail automática (REV-5); botão "Salvar como Exemplo Ouro" (AC 6.6.3, REV-9), que hoje só existe como tecla `E`. *Correção:* incluir na Ficha um botão visível de Exemplo Ouro, a seção recolhida de transcrição/legenda e o thumb; dizer o que o player toca (preview 480p) e quando o render final existe.
- **[médio]** LIV-2 (player da live embutido + captura) é travado `codigo`, mas a Sala promete "assistir a live ou o VOD" sem dizer se o player embutido está ligado. O que acontece ao clicar num card do **Ao vivo** com "Cortar ao vivo" travado também não está escrito (IA › Sala do vídeo; Flow 4). *Correção:* estado "Sala de uma live": player embutido (se a CSP já permitir) ou travado, painel de corte com "Cortar ao vivo — Chega na história 5.2" e, se existir, "Cortar o VOD quando a live acabar".
- **[médio]** AC 6.5.2 e a regra do mapa ("o backend escolhe a aba aberta por padrão, a primeira ligada") não estão no spine; só o Flow 1 mostra a vitrine abrindo em Recentes (IA › Lives). *Correção:* escrever a regra na linha da Lives ou num estado "Aba inicial".
- **[médio]** PUB-4/B11: a AC 6.8.2 aceita link do YouTube Longo, mas o Cartão não diz quais redes geram cartão (4 ou 5) e a falha do Flow 1 lista "YouTube, TikTok, Instagram ou Facebook". PUB-6 (publicação automática) não aparece como travada, embora a AC 6.8.3 a exija (Component Patterns › Cartão de publicação; IA › Publicação). *Correção:* listar as redes do cartão (YouTube Longo travado até a 3.7.3, link aceito via B11) e pôr "Publicar automaticamente — travado (6.1 + auditorias)" no próprio cartão.
- **[baixo]** Detalhes sem lugar: SIS-1 (GPU detectada), SIS-9 (Modo Dupla como opção do motor de IA), FIL-4 (progresso por bloco de 30 min), AC 6.6.4 (os quatro filtros: arquétipo, tier, sinal medido, status P1), MET-2/MET-4/MET-6 (seções do Aprendizado não nomeadas) e Kick no Ao vivo ("a pesquisar"). *Correção:* uma linha por item onde couber; para o Aprendizado, listar as seções travadas pelo nome do mapa.

## 2. Fluxos — **adequado**

Superfícies com fluxo: Lives, Sala, Revisão, Publicação, Fontes, Configurações. Sem fluxo: Fila, Escudo, Motor, Aprendizado (só citado), Radar, Paleta. Motor, Radar, Aprendizado e Paleta sem fluxo é aceitável. Fila e Escudo fazem falta.

- **[alto]** O gatilho de C2 não está definido e o Flow 1 se contradiz: o passo 1 mostra "Links pendentes (1)" e o clímax diz que "cai de 2 para 1", sem nenhum passo que crie a segunda pendência (Flow 1, passos 1, 6 e 7). Quem implementa não sabe se o corte vira pendente ao exportar o Pacote, ao copiar o título ou ao abrir a pasta. *Correção:* definir o evento ("exportado" = o corte entrou no Pacote do Dia exportado / o operador clicou em Copiar ou Abrir pasta) e corrigir o Flow 1 com o passo que gera a pendência.
- **[médio]** Não existe fluxo do Escudo: claim chega → operador registra → pausa a fonte em todas as redes → o Pacote do Dia e a Fila refletem. É o caminho P1 com mais consequências entre superfícies (IA › Escudo). *Correção:* Flow 5 "Chegou um claim" com protagonista, passos, clímax (todos os cortes da fonte somem do Pacote com o motivo) e falha (fonte não identificada pela URL).
- **[médio]** A Fila não tem fluxo, e a falha do Flow 2 não diz onde aparece (Fila? chip Falhas? notificação?) nem como se chega ao **Retomar** (Flow 2 › Falha). *Correção:* completar a falha do Flow 2 com o caminho (chip "Falhas (1)" → Fila filtrada → Retomar) ou criar um fluxo curto da Fila.
- **[médio]** O clímax do Flow 2 diz "Ele fecha o navegador; a notificação avisa". A API de notificação do navegador não dispara com o navegador fechado, o que contradiz Responsive & Platform ("o painel em segundo plano avisa") (Flow 2, passo 5). *Correção:* trocar por "deixa a aba em segundo plano" ou especificar outro canal que funcione igual em Windows e Linux (C4).
- **[médio]** No Flow 1, passo 5, "Renderizando 4/17" não diz se os renders entram na fila única serial (e aparecem na Fila e no chip "Na fila") nem se competem com um VOD enfileirado (Flow 1; Tempo real e concorrência). *Correção:* dizer que render é um job da fila única, com estágio próprio, visível na Fila.
- **[baixo]** O Flow 3 não tem caminho de falha (evidência vazia, link de evidência inválido, salvar falhou). O Flow 1 mostra "visão não medido: fonte só de áudio" enquanto o operador assiste ao vídeo no player, o que confunde (Flow 3; Flow 1, passo 3). *Correção:* acrescentar a falha "Sem evidência não dá para liberar" no Flow 3 e trocar o exemplo de sinal não medido no Flow 1 por um coerente (ex.: "chat: não medido — VOD sem chat").

## 3. Componentes — **adequado**

As 16 linhas existentes têm regras reais e boas. Faltam linhas para componentes citados em outras seções.

- **[médio]** A Barra de status global (IA) não tem linha: falta dizer o que mostra quando não há job, como trata provedor `temporario`, o "Reconectando…" e para onde cada item leva (IA › Barra de status global). *Correção:* linha própria em Component Patterns.
- **[médio]** A navegação da vitrine não tem linha: abas Ao vivo / Em alta / Recentes, prateleira por streamer com a alternativa "tudo por data", paginação "ver mais", o player da Sala e a colagem por `Ctrl+V` (Inspiration; Interaction Primitives; IA › Sala). *Correção:* linhas "Abas da vitrine", "Prateleira de streamer" e "Player da Sala".
- **[médio]** O formulário de permissão/cadastro de fonte (Flow 3; Linha de fonte; estado Fonte barrada) não tem linha. É o componente que garante C1 (*Correção:* linha com os campos: base da permissão, com os valores do CLAUDE.md, incluindo `campanha ativa` com data de expiração e `gameplay próprio`; evidência obrigatória; motivo registrado; canal pré-preenchido vindo da Sala).
- **[médio]** O Pacote do Dia como contêiner não tem linha, só o Cartão: faltam a ordem, como a cadência e o cooldown limitam o pacote, como se mostra por que um corte aprovado ficou fora e a ação de exportar (IA › Publicação; PUB-1). *Correção:* linha "Pacote do Dia".
- **[médio]** Atalhos de letra única (`J K I O D E R 1 2`) convivem com "textos editáveis no lugar" na Ficha, e não há regra de foco. Há também sobreposição `g r` × `R` e `g e` × `E` (Interaction Primitives; Ficha do corte). *Correção:* "atalhos de uma tecla ficam desligados com foco em campo editável; `g` abre um modo de 1 s esperando a segunda letra".
- **[baixo]** Sem linha própria: Sidebar (regras só em prosa na IA), Paleta de comandos, Lista de atalhos (`?`), aviso de desfazer do Descartar (prazo "alguns segundos" vago), contadores reais do Aprendizado e gaveta da Ficha (1280–1919 px). *Correção:* linhas curtas, ou mover as regras da sidebar para Component Patterns e fixar o prazo de desfazer.

## 4. Estados — **fraco**

Global, Lives (com credencial) e Revisão estão bem servidos. Fila, Publicação, Fontes, Escudo, Motor e Configurações quase não têm estados próprios.

| Superfície | Ausentes |
|---|---|
| Lives | primeira execução sem chave do YouTube; 0 streamers cadastrados; `Ctrl+V` com algo que não é link de vídeo |
| Sala | portão P1 respondendo; vídeo já cortado/na fila; fonte pausada; live (ver §1) |
| Fila | vazia; carregando; Interrompido sem ação definida |
| Revisão | nenhum projeto (`g r`); estado de render por corte; peaks indisponíveis |
| Publicação | Pacote vazio; corte fora por cadência/cooldown; fonte pausada; Publicados vazio |
| Fontes | sem fontes; sem barrados; políticas vazias (B6); campanhas vazias |
| Escudo | sem cooldown; sem claims |
| Motor | sem projetos; projeto sem `engine_health.json` |
| Configurações | validando/salvo; Modo Madrugada parcial; custos travado |

- **[alto]** Primeira execução sem chave da YouTube Data API: Recentes depende da API oficial, mas não existe o estado travado `config` dele. Com Ao vivo (`config`) e Em alta (`codigo`) também travados, a página inicial abre inteira travada, o que o mapa proíbe ("para a página não abrir num vazio travado") (State Patterns › Lives). *Correção:* estado "Primeira execução" com um único chamado para configurar a chave do YouTube (e a da Twitch), mais a "Na sua mesa" e a colagem de link funcionando.
- **[alto]** Fonte pausada (disjuntor manual ou por claim) não tem estado em nenhuma superfície: a Sala, a Linha da Fila, a Lista de cortes e o Pacote do Dia não dizem o que acontece com os cortes de uma fonte `pausada_por_claim` (State Patterns). *Correção:* estado "Fonte pausada" nas quatro superfícies: corte fica visível, marcado "pausado: claim em DD/MM", fora do Pacote e sem cópia de kit.
- **[médio]** Faltam os vazios da tabela acima (Fila, Revisão sem projeto, Pacote do Dia, Fontes, Escudo, Motor, Lives com 0 streamers). A AC 6.3.7 pede o estado vazio desenhado (State Patterns). *Correção:* uma linha de vazio por superfície, no tom da Voice and Tone ("Nada na fila.").
- **[médio]** Não há estado do corte depois da decisão: renderizando / renderizado / render falhou / descartado / exportado / publicado. Lista de cortes e Cartão de publicação dependem disso (Component Patterns › Lista de cortes). *Correção:* definir o ciclo de vida do corte e o marcador de cada estado na lista.
- **[médio]** O spine não diz o que o front desenha se o próprio `GET /api/capacidades` falhar ou vier sem uma capacidade. É exatamente o caso em que o front poderia "decidir" que algo funciona (Foundation › Regra-mãe). *Correção:* estado "Status desconhecido": a função aparece travada `temporario` com "Não consegui verificar" + Tentar de novo; nunca ligada por padrão.
- **[médio]** Dado velho está vago: os prazos são "minutos" e "horas", e não diz o que muda (aviso? ações desabilitadas?). Com o SSE caído, a barra de progresso de um job congela e pode parecer que ainda está rodando (Contrato de Travas, regra 5; Tempo real caiu). *Correção:* tabela de prazo por tipo (provedores 2 min, lista de vídeos 6 h, progresso de job 30 s) e tratamento ("velho" + progresso marcado "sem atualização há X").
- **[médio]** Sala: faltam o portão P1 "verificando…" (carregando), o vídeo já cortado ou já na fila (evitar duplicar o job) e o `Ctrl+V` com link inválido ou de plataforma sem suporte (State Patterns › Sala). *Correção:* três linhas de estado.
- **[baixo]** Configurações (validando, salvo, Madrugada parcial, custos travado) e Fila › Interrompido sem ação. *Correção:* linhas curtas; Interrompido → **Retomar**.

## 7. Consistência de nomes — **adequado**

- **[médio]** O spine faz da Sala do vídeo uma **página** (decisão do dono), mas a AC 6.5.3 e o LIV-5 dizem "modal de corte" e o LIV-2 diz "modal ou página" (IA › Sala; epics 6.5 AC3). *Correção:* registrar no memlog e pedir a atualização do texto da 6.5 no próximo correct-course, para o dev não seguir a história.
- **[médio]** "Motor" é ao mesmo tempo a superfície de saúde/benchmark e o motor de IA (estado "Motor indisponível", ação "Trocar motor e retomar", "motor de IA" no Painel de corte) (IA; State Patterns). *Correção:* renomear a superfície para "Saúde do motor" ou chamar o outro sempre de "motor de IA".
- **[médio]** A Voice and Tone fixa "3 palavras fixas: Ligado · Parcial · Travado", mas o contrato introduz "Desligado por você" (`escolha`) e "Indisponível agora" (`temporario`). A tabela também trata `escolha` como status, quando no mapa e na AC 6.3.3 ele é `tipo_motivo` (Voice and Tone; Contrato de Travas). *Correção:* declarar o vocabulário completo (3 status + rótulos por tipo de motivo) e corrigir a linha `escolha` para "`ligado`/`travado` · `escolha`".
- **[baixo]** Restam 2 marcas **[SUPOSIÇÃO]** (`←`/`→` 2 s; vitrine com 5–6 cards), mas as Open Questions dizem que "as 6 suposições foram confirmadas". O contador de gabaritos aparece no Motor (IA) e no Aprendizado (estados). A C2 da fonte fala em "Hoje", e aqui é "Na sua mesa" (equivalente, mas vale uma nota) (Open Questions; IA; State Patterns). *Correção:* resolver ou manter as 2 marcas explicitamente; dar um dono único ao contador; nota "Hoje (C2) = Na sua mesa".

## 8. Forma — **forte**

Todas as seções do exemplo estão presentes (Foundation, IA, Voice and Tone, Component Patterns, State Patterns, Interaction Primitives, Accessibility Floor, Responsive & Platform, Inspiration & Anti-patterns, Key Flows), mais extras úteis (Contrato de Travas, Tempo real, Dados de terceiros, Open Questions). Os fluxos têm protagonista, passos numerados e clímax em negrito.

- **[baixo]** Não há referência de composição (mockups/wireframes), prevista para depois no memlog. O frontmatter `sources` não cita o `handoff-sessao-04.md` nem o `research.md` da stack, citados no intake e na 6.3 (frontmatter). *Correção:* incluir as duas fontes; acrescentar o "→ Composition reference" quando os wireframes existirem.

## Condições C1–C4 e "nunca dado falso" — **adequado**

- **[alto]** C1: o spine não diz como se **despausa** uma fonte pausada (manual ou por claim). Sem regra, a implementação natural é um botão de 1 clique, o que equivale a liberar sem base + evidência. O spine também não define o registro de motivo ao **pausar** a fonte nem ao **limpar** o cooldown manual (exigido por C1), nem onde se cria um cooldown manual (Component Patterns › Cooldown / Linha de fonte). *Correção:* "reativar fonte pausada usa o mesmo formulário de permissão (base + evidência + motivo); pausar e limpar pedem motivo, gravado no histórico".
- **[alto]** C3: o spine não garante que um corte aprovado pelos portões entra no Pacote do Dia **sem passar pela Revisão**. O Flow 1 sugere que só entra depois de `R` na Revisão, o que tornaria a revisão obrigatória (Flow 1, passos 5–6; Cartão de publicação). *Correção:* escrever a regra de entrada no Pacote (portões P1 + cadência; render automático ou sob demanda) e dizer que 👍/👎 e a Revisão só refinam.
- **[médio]** C2: não existe saída para "decidi não postar" um corte exportado, então a pendência pode ficar para sempre e virar ruído. Também não está escrito que é proibido marcar como postado sem link (Estado Link pendente). *Correção:* ação "Não vou postar" com motivo, que tira a pendência e fica registrada; frase explícita "não existe 'postei' sem URL".
- **[médio]** A ordem padrão "tier + sinais concordantes" não diz como trata um sinal `null` (não medido). Se o front o tratar como 0 ou como discordante, recria o falso zero que o B2 corrige (Component Patterns › Lista de cortes). *Correção:* "sinal não medido não conta a favor nem contra; o corte mostra 'k de n sinais medidos'".
- **[baixo]** C4: a tela "Picorte desligado" mostra "o comando para iniciar", que é diferente no Windows e no Linux (`.venv/Scripts` × `.venv/bin`). O "abrir pasta" do Cartão de publicação também precisa funcionar nos dois sistemas (State Patterns › Picorte desligado; Cartão de publicação). *Correção:* mostrar o comando do sistema detectado (ou os dois) e citar a paridade do "abrir pasta".

Nenhum ponto do spine mostra dado de exemplo. As regras do skeleton, do destaque do topo, do selo AO VIVO e dos contadores reais estão corretas.
