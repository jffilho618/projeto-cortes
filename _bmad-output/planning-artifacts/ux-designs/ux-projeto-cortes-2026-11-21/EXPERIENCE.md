---
name: Picorte — Estúdio do Criador (experiência)
status: final
updated: 2026-11-21 (rev. 2: pico de origem, minimapa, Pede você, agrupar, Sai)
sources:
  - ../../../brainstorming/brainstorm-mapa-painel-estudio-do-criador-2026-11-21/brainstorm-intent.md
  - ../../sprint-change-proposal-2026-11-21-painel.md
  - ../../epics.md
  - ../../../specs/spec-picorte/SPEC.md
  - ../../pilares.md
  - ../../../../docs/handoff-sessao-04.md
  - ../../research/technical-stack-painel-estudio-do-criador-2026-11-21/research.md
---

# Picorte — Estúdio do Criador · Experiência

> **Escopo:**
> - Este arquivo é dono de *como funciona*. *Como parece* fica no `DESIGN.md` desta pasta, que nasce na etapa de direção visual com o impeccable (Operate). Os tokens de lá serão citados como `{caminho.do.token}`.
> - Em conflito com wireframes, mocks ou importações, vale este arquivo.
> - Todas as suposições do rascunho foram decididas pelo dono em 2026-11-21; os números marcados "valor inicial" são ajustáveis na implementação.
> - IDs como `FON-6` e `REV-12` são do mapa de capacidades; `AC 6.x.y` são critérios de aceite do `epics.md`.

## Foundation

- **Superfície única:** web local no navegador, servida pelo FastAPI em `127.0.0.1`.
  - **Só desktop:** Windows 11 (PC de mesa, alvo **2560×1440**) e Linux (notebook, secundário).
  - **Sem layout de celular** (Non-goal da SPEC).
- **Usuário único:** o operador (Bomba). Não há login, contas nem papéis.
- **UI system:** React + Base UI (via shadcn CLI v4, depois `eject`). Os componentes são nossos; o visual vem do `DESIGN.md` novo. Este arquivo especifica o comportamento.
- **Regra-mãe ("travado nunca é falso"):** o status de cada função vem de `GET /api/capacidades`. O front **nunca** decide se algo funciona (ver § Contrato de Travas).
- **Idioma:** PT-BR em toda a interface. Datas e horas no fuso de Brasília.

## Information Architecture

| Superfície | Como chega | Para quê | História |
|---|---|---|---|
| **Lives** (página inicial) | Abrir o painel · `g l` | Vitrine dos streamers cadastrados (abas **Ao vivo / Em alta / Recentes**) com a faixa **Na sua mesa** no topo | 6.5 |
| **Sala do vídeo** (página) | Card da vitrine · `Ctrl+V` com um link · arquivo arrastado | Assistir a live ou o VOD e configurar o corte | 6.5 |
| **Fila** | `g f` · chip "Na fila" ou "Falhas" | Projetos e jobs (cortes, renders), separados em Produção e Conjunto de prova; **Novo projeto** por arquivo local ou lote de links | 6.6 |
| **Revisão** (projeto) | Linha da Fila · chip "Revisar" · `g r` (último projeto) | Assistir e decidir corte a corte | 6.6 |
| **Publicação** | `g p` · chip "Links pendentes" | Pacote do Dia, cartões por rede, links publicados, publicados, contas e publicação automática (travadas) | 6.8 |
| **Fontes** | `g o` | Abas **Streamers · Barrados · Políticas por jogo · Campanhas · Pausas · Dossiês** | 6.7 |
| **Escudo** | `g e` | Cooldowns por rede, **Registrar claim**, histórico de claims, monitor automático (travado) | 6.7 |
| **Saúde** | `g s` | Abas **Motor** (saúde por projeto), **Benchmark** e **Sistema** (GPU/VRAM, disco, banco, ferramentas, MCP, Modo Madrugada) | 6.7 |
| **Aprendizado** | `g a` | Métricas 1h/24h/7d, recompensa, Bandit, reciclagem A/B, dataset, pesos calibrados (travados), com contadores reais | 6.8 |
| **Radar** | `g d` | Tendências, calendário, clipes de terceiros, treta, perfis e piadas internas: travado até o E5 | 6.8 |
| **Configurações** | `g c` · botões "Configurar" das travas | Motor de IA, preset de visão, marca e legendas, credenciais de app, Modo Madrugada, custos, notificações | 6.7 |
| **Paleta de comandos** | `Ctrl+K` | Ir a projeto, fonte ou ação pelo nome | 6.3 (Could) |

**Sidebar autorretrátil** (decisão do dono, 2026-11-21: "autorretrátil, suave e criativa, aproveitando o que o pacote traz"):
- **Ordem:** Lives · Fila · Revisão · Publicação · Fontes · Escudo · Saúde · Aprendizado · Radar · Configurações. Áreas inteiramente travadas **aparecem**, com o marcador de travado.
- **Recolhida por padrão:** ícones mais o que não pode sumir: contagem real (Revisão, Publicação, Fila), marcador **Novo** e marcador de travado.
- **Abrindo:** abre ao passar o mouse **com intenção** (atraso curto, para não abrir quando o cursor só cruza) e ao receber foco. Recolhe ao sair, com atraso curto.
- **Sem empurrar a tela:** aberta, passa **por cima** do conteúdo; o player e a waveform nunca mudam de tamanho por causa dela.
- **Fixar aberta:** alfinete ou `[`; lembrado no navegador.
- **Movimento:** candidato ao **movimento-assinatura**, definido na direção visual (Motion/GSAP). Com `prefers-reduced-motion`, sem animação.

**Estado do sistema no pé da sidebar** (decisão do dono, 2026-11-21): não há barra de status no topo.
- O job da GPU, os provedores de IA e o tempo real moram no rodapé da sidebar (ver Component Patterns › Estado do sistema).
- O conteúdo só recebe um aviso quando algo **impede uma ação ali**. Exemplo: na Sala, "Gemini indisponível" aparece na própria opção do motor.

**Modais:** no máximo 1 nível. A Sala do vídeo é **página**, com endereço próprio e o botão Voltar (decisão do dono; a AC 6.5.3 foi ajustada para "Sala do vídeo").

→ **Wireframes de baixa fidelidade** (só estrutura; cor, tipo e estilo virão do `DESIGN.md`):
- [`mockups/wf-lives.html`](mockups/wf-lives.html): Lives;
- [`mockups/wf-sala.html`](mockups/wf-sala.html): Sala do vídeo e fonte barrada;
- [`mockups/wf-revisao.html`](mockups/wf-revisao.html): Revisão em 3 colunas.

Em conflito, vale este arquivo.

## Contrato de Travas (capacidade → tela)

Toda função recebe do backend: `status` (`ligado` / `parcial` / `travado`), `tipo_motivo` (`codigo` / `config` / `dado` / `temporario` / `escolha`), `motivo`, `falta[]`, `depende_de[]`, `verificado_em` e `ligou_em`.

| Status · tipo | Rótulo e conteúdo | Ação |
|---|---|---|
| `ligado` | A função normal. | — |
| `parcial` | **Parcial** + uma linha com o limite ("Funciona só com fontes do YouTube"). | "por quê" |
| `travado` · `codigo` | **Travado** + "Chega na história X.Y" + o que falta. | nenhuma |
| `travado` · `config` | **Travado** + "Falta configurar: …". | **Configurar** (vai direto ao campo) |
| `travado` · `dado` | **Travado** + "Ainda sem dados: aparece quando …". | link para a ação que gera o dado, se existir |
| qualquer · `temporario` | **Indisponível agora** + motivo, desde quando e, se houver, a previsão. | **Tentar de novo** |
| qualquer · `escolha` | **Desligado por você.** | interruptor |

**Regras:**
1. **Travado ocupa o lugar real.** Ver § Onde ficam os travados.
2. **Nenhum número, gráfico, thumb ou nome de exemplo num travado.** O *skeleton* é só para dado real a caminho.
3. **`depende_de` aponta a raiz:** "Bandit ← métricas 1h/24h/7d ← publicação com link".
4. **Destravou, aparece sozinho** pelo SSE, com o marcador **Novo** até ser visto (`ligou_em`).
5. **Dado velho:** todo bloco mostra "verificado há X".
   - **Prazos:** provedores e capacidades 2 min; status de live 5 min; listas de vídeos 6 h. (valores iniciais, ajustáveis)
   - **Depois do prazo:** o bloco ganha o marcador **Desatualizado**, e ações que dependem dele (ex.: "Cortar" com o portão P1 velho) **verificam de novo antes de agir**.
6. **Capacidades ilegíveis:** se o próprio `GET /api/capacidades` falhar ou não trouxer uma função, ela é desenhada como **Indisponível agora · não consegui ler o status**. **Nunca como ligada por padrão.**

## Onde ficam os travados

| Função (ID) | Lugar real na tela | Travado até |
|---|---|---|
| Par Short↔Longo (REV-12) | Painel de corte › Formato, como opção | 3.7.3 |
| Cold Open e Seamless Loop (REV-10) | Painel de corte › seção **Efeitos de retenção** | 3.7.1 |
| Layout dinâmico e Sniper Crop (REV-11) | Painel de corte › Enquadramento, como opção | 3.7.2 |
| Arcos de 2 atos e compilação por arquétipo (REV-13) | Revisão › cabeçalho do projeto, aba **Compostos** (parcial: lista os JSON gerados no modo profundo; render travado) | 3.7.4 |
| Compilação cross-streamer (REV-14) | Revisão › aba **Compostos** | E5 |
| `standalone`, ouro com 2 sinais, bordas por frase (REV-15) | Ficha do corte (linha "Entende sozinho?") | 3.6.4–3.6.5 |
| `confianca_projeto` (SAU-2) | Revisão › cabeçalho + Saúde › Motor | 3.6.5 |
| Cortar a live ao vivo (LIV-2, captura) | Sala do vídeo › no lugar do botão "Cortar" quando é live | 5.2 |
| Canário semanal e `yt-dlp` diário (SAU-5) | Saúde › Sistema | W9 |
| Publicação automática (PUB-6) e contas OAuth (PUB-5) | Publicação › aba **Contas** + no cartão de cada rede | 6.1 |
| Monitor automático de claims (ESC-9) | Escudo › topo | 6.2 |
| Perfis e piadas internas (FON-9) | Fontes › Streamers › ficha do streamer | 5.4 |
| Elo fonte → vídeos → cortes (FON-4) | Fontes › Streamers › ficha do streamer ("vídeos e cortes desta fonte") | 6.4 (B1) |
| Métricas, recompensa, Bandit, A/B, dataset, pesos (MET-1–6) | Aprendizado, uma seção cada | 7.1–7.3, 3.6.6 |
| Radar (RAD-1–5) e Em alta (LIV-3) | Radar, uma seção cada · Lives › Em alta | 5.1–5.4 |

## Voice and Tone

Direto, em PT-BR, com verbos e contagens. A voz da marca fica no `DESIGN.md`.

| Fazer | Não fazer |
|---|---|
| "3 cortes esperando você" | "Você possui 3 itens pendentes de revisão." |
| "Nada esperando você." | "Tudo certo por aqui! 🎉" |
| "Sem cota do Gemini desde 21/11. Volta por volta de 25/11." | "Erro: CalledProcessError agy.exe…" |
| "BisteconeLive não está cadastrado. Nada foi baixado." | "Fonte inválida." |
| "Chega na história 6.1: cofre de tokens e app aprovado pela rede." | "Em breve!" |
| "Não medido: este vídeo não teve chat." | "Chat: 0" |
| "Renderizado antes do Escudo. Sem veredito — re-auditar." | Selo verde vazio |

**Vocabulário fixo:**
- **status:** **Ligado · Parcial · Travado**;
- **qualificadores de motivo:** **Indisponível agora** (`temporario`) e **Desligado por você** (`escolha`);
- **sinais:** **medido · não medido · falhou**;
- **P1:** **aprovado · barrado · sem veredito**.

Nada de sinônimos variando por tela.

**Erros técnicos** viram uma frase + o próximo passo; o detalhe cru fica atrás de "ver detalhe técnico".

**Estágios do job:** Na fila · Baixando · Transcrevendo · Escolhendo cortes · Renderizando · Pronto para revisar · Falhou · Interrompido.

**Ciclo do corte:**

| Etapa | Estados |
|---|---|
| Antes de renderizar | Candidato |
| Render | Renderizando · Renderizado · Render falhou |
| Destino | Descartado · No pacote · Exportado · Publicado (com link) · Não vou postar |

## Component Patterns

O comportamento fica aqui; o visual, no `DESIGN.md.Components`.

### Global

| Componente | Regras de comportamento |
|---|---|
| **Estado do sistema** (pé da sidebar) | Bloco fixo no rodapé da sidebar, acima de Configurações.<ul><li>**Recolhida:** o ícone da GPU com **anel de progresso real** do job atual (vazio quando a GPU está livre); um ícone por provedor (Ollama, Gemini, Claude) com **marca de forma**, nunca só cor (✓ ligado · ! indisponível ou parcial · cadeado travado); o ícone do tempo real (conectado / reconectando); e um ícone de alerta que **só aparece** quando algo da Saúde › Sistema não está ligado (ex.: disco com 4 GB livres).</li><li>**Aberta:** a mesma lista em texto: "GPU · Renderizando 4/17 · Davy Jones · GTA 6", "Gemini · Indisponível desde 21/11 (cota)", "Tempo real · conectado".</li><li>Cada linha leva ao detalhe (Fila, Saúde › Sistema ou Configurações).</li></ul>A contagem e o anel vêm do SSE. |
| **Sidebar** | Ver § IA. Contagens são reais e vêm do mesmo endpoint da faixa Na sua mesa. |
| **Paleta de comandos** | Busca por nome de projeto, fonte, vídeo ou ação. `Enter` executa; `Esc` fecha. |
| **Lista de atalhos** | `?` abre a lista; os atalhos de letra única ficam desligados enquanto o foco está num campo de texto. |
| **Aviso de desfazer** | Ações desfazíveis (descartar, "não vou postar") mostram "Desfazer" por **8 s** (valor inicial). |
| **Bloco travado** | Segue o Contrato; tem o mesmo tamanho do bloco ligado que vai substituir. |

### Lives e Sala do vídeo

| Componente | Regras de comportamento |
|---|---|
| **Abas da vitrine** | Ao vivo · Em alta · Recentes. A aba aberta por padrão é a **primeira ligada** segundo o backend (AC 6.5.2); a escolha manual fica lembrada até a próxima sessão. |
| **Destaque do topo** | **Faixa compacta** (decisão do dono): a thumb média ocupa cerca de 1/3 da largura e tem ~260 px de altura; título, streamer, jogo, P1 e **Abrir na Sala** ficam ao lado. A primeira prateleira aparece sem rolar em 2560×1440. Se alguém cadastrado está ao vivo, o destaque é essa live; se não, o vídeo recente mais novo ainda não cortado. Sem nenhum dos dois: vazio desenhado. Nunca um destaque de exemplo. |
| **Prateleira de Recentes** | Uma prateleira por streamer, rolando na horizontal, com "ver mais" (paginação). O alternador **Por streamer / Por jogo / Tudo por data** reagrupa as prateleiras (por jogo detectado) ou troca para uma grade cronológica. Mostra "verificado há X". |
| **Card de vídeo** | Thumb, streamer, título, jogo, duração e data, **tudo da API**. Status do Picorte sobre a thumb: já cortado · na fila · falhou · barrado P1 · fonte pausada. No Ao vivo: selo AO VIVO + espectadores (API + `verificado_em`). Clique abre a Sala. |
| **Faixa "Na sua mesa"** | Até 5 chips com contagem real: **Pede você (n)** (alertas P1: claim que pausou cortes, fonte barrada esperando decisão; vem primeiro e tem marcação de alerta) · **Revisar (n)** · **Links pendentes (n)** (C2) · **Na fila (n, estágio)** · **Falhas (n)**. Chip zerado some; tudo zerado mostra "Nada esperando você." Cada chip abre a superfície filtrada. |
| **Entrada por link ou arquivo** | `Ctrl+V` na vitrine com um link abre a Sala desse vídeo. Arrastar um arquivo de vídeo para a vitrine abre a Sala em modo **arquivo local**: o portão P1 pede o dono declarado (ex.: "meu gameplay", que nasce autorizado). |
| **Player da Sala** | Embed oficial (YouTube ou Twitch). Para live, o player embutido é **ligado**; só a **captura** ("Cortar ao vivo") é travada até a 5.2. Para arquivo local, toca o próprio arquivo. |
| **Painel de corte** | Em ordem:<ol><li>**Portão P1**, respondido ao abrir ("verificando…" enquanto responde);</li><li>Formato (o par Short↔Longo aparece travado);</li><li>Enquadramento (layout dinâmico aparece travado);</li><li>Motor de IA, cada opção com a disponibilidade real, incluindo **Dupla** (filtro + acompanhamento);</li><li>Caça Rápida/Profunda;</li><li>Busca por pergunta (opcional, recolhida);</li><li>**Efeitos de retenção** (Cold Open/Loop travados);</li><li>"LLM vê os frames", com o custo estimado escrito;</li><li>**Preview do enquadramento sobre uma imagem real do vídeo**;</li><li>**Depois de escolher:** *Renderizar sozinho os aprovados pelos portões* ou *Esperar minha revisão* (**padrão: "Renderizar sozinho"**, decisão do dono pelo P5);</li><li>**Cortar este vídeo**.</li></ol>Com a fonte barrada ou pausada, os passos 2 a 11 ficam desabilitados. Se o vídeo já foi cortado ou está na fila, o botão vira **Abrir projeto** (nunca duplica o job). |

### Fila e Revisão

| Componente | Regras de comportamento |
|---|---|
| **Linha da Fila** | Título real, streamer, jogo, tipo (corte ou render), estágio, progresso real (incluindo "bloco 3 de 8" nos VODs longos), motor, início. Falha traz a ação: *Trocar motor e retomar* · *Cadastrar fonte* · *Retomar*. Interrompido → **Retomar**. Job de outra sessão ou da CLI: "rodando fora do painel", só leitura. Renders entram nesta mesma fila serial (fila única). |
| **Novo projeto (Fila)** | Duas entradas:<ul><li>**Arquivo local:** escolher o arquivo + dono declarado;</li><li>**Lote:** colar de 1 a 100 links; cada linha recebe o veredito P1 **antes** de enfileirar, e as barradas ficam de fora com o motivo.</li></ul> |
| **Cabeçalho do projeto** | Título, streamer, jogo, número de cortes, motor, Produção ou Prova. Frase-resumo da saúde (do backend). `confianca_projeto` aparece travada até a 3.6.5. Ações: **Buscar de novo neste vídeo** (Caça Profunda ou busca por pergunta, em projeto já processado; AC 6.6.5) e aba **Compostos**. **Minimapa do VOD** logo abaixo: a curva de energia do áudio do vídeo inteiro com a posição real de cada corte (ouro destacado, selecionado em evidência); clicar num trecho vai para o corte. |
| **Lista de cortes** | Ordem padrão: tier, depois o número de **sinais medidos que concordam**. Sinal **não medido não conta a favor nem contra** (nunca vira zero). Cada item: título, arquétipo, tier, duração, estado do ciclo, 👍/👎, P1 resumido. Filtros: arquétipo, tier, sinal medido, status P1, 👍/👎 (valores da taxonomia). Controle **Agrupar: Nenhum / Jogo / Arquétipo**. Sem mini-curva por item (decisão do dono: em tamanho de lista ela não diferencia os cortes e aperta os títulos; o pico de origem fica no minimapa e na ficha). |
| **Player + waveform** | Vídeo + forma de onda (peaks do servidor) com alças de início e fim. Mostra se é **preview 480p da seção** ou **render final**. Velocidade 1× / 1,5× / 2×. **Avançar sozinho** ligado por padrão. Peaks indisponíveis: o player funciona e a waveform mostra "forma de onda indisponível". |
| **Ficha do corte** | Arquétipo, tier, título, faixa 2s, 1º comentário (editáveis no lugar), motivo do Editor-Chefe, **thumbnail automática** (quando houver). **Sinais** um por linha: medido / não medido + motivo / falhou. **P1 por rede**, expandível em cada portão: fonte, política do jogo, Selo Verde 15s, React Guard, música/Demucs, YPP, originalidade TikTok, pHash, limpeza de texto, cadência. "Entende sozinho?" aparece travado até a 3.6.5. Botão **Salvar como Exemplo Ouro**. |
| **Pico de origem** | Ficha do corte | Curva "de onde saiu": ±90 s ao redor do corte, trecho marcado, **cume** indicado com o horário. Camadas só quando **medidas**: energia do áudio (todo projeto tem), chat, comentários com horário e heatmap. Camada ausente não é desenhada, e uma linha diz quais não foram medidas. |
| **Editor de transcrição e legenda** | Recolhido por padrão, abaixo do player. Editar palavras e ajustar o estilo da legenda deste projeto. |
| **Rótulo 👍/👎** | Opcional (C3). Um toque grava; um segundo toque abre motivos de 1 clique (título ruim, borda errada, momento fraco, já publicado). Nunca muda o destino do corte. |
| **Descartar** | Ação separada do 👎 (decisão do dono): tira o corte do pacote, com desfazer. |

### Publicação

| Componente | Regras de comportamento |
|---|---|
| **Pacote do Dia** | Cortes **Renderizados** que passaram nos portões, em ordem de tier. Respeita o teto diário e o espaçamento de cada rede: um corte que ficou de fora mostra o motivo ("cooldown do TikTok até 14h"; "teto do dia atingido"). **Exportar pacote** gera os arquivos e marca os cortes como **Exportado**. Não depende de 👍 nem de passar pela Revisão (C3). Cada corte mostra **quando sai** em cada rede (horário previsto pela cadência). |
| **Cartão de publicação** | Um por corte × rede: **YouTube Shorts, YouTube Longo, TikTok, Instagram Reels e Facebook** (o YouTube Longo só aparece se houver corte longo). Copiar título, descrição + crédito, hashtags e 1º comentário (1 clique cada); abrir pasta (funciona em Windows e Linux). Campo **Colar link publicado**. |
| **Link pendente (C2)** | Um corte vira pendente **no momento em que é Exportado**. A pendência só sai de dois jeitos:<ul><li>colando um link válido da rede, e o corte vira **Publicado**;</li><li>escolhendo **Não vou postar** com um motivo de 1 clique, com desfazer. (aprovado pelo dono)</li></ul>**Não existe "marcar como postado" sem link.** |
| **Aba Contas** | Uma linha por rede, travada com o que falta (6.1). |

### Fontes

| Componente | Regras de comportamento |
|---|---|
| **Aba Streamers** | Linha por fonte: status, base da permissão, evidência, jogo padrão. A ficha do streamer mostra "vídeos e cortes desta fonte" (travado até B1/6.4) e "perfis e piadas" (travado até 5.4). |
| **Formulário de permissão** (C1) | Usado para cadastrar, mudar status e **despausar**. Campos obrigatórios:<ul><li>**status** (`liberada` / `contrato` / `campanha ativa` / `gameplay próprio` / `desconhecida`);</li><li>**base da permissão** (ex.: tolerância pública, explícita);</li><li>**evidência** (link ou nota);</li><li>**motivo** da mudança.</li></ul>Não existe liberar ou despausar em 1 clique. Tudo fica no histórico. |
| **Aba Barrados** | Tentativas barradas pelo portão (canal, quando, de onde veio). Cada linha tem **Cadastrar fonte**, que abre o formulário preenchido. |
| **Aba Políticas por jogo** | Leitura das políticas de publisher (janela de spoiler, cutscenes, música licenciada). Sem políticas sincronizadas: travado `dado` até B6/6.4. |
| **Aba Campanhas** | Cadastrar campanha (fonte, jogo, CPM, tags, início e **expiração**). Campanha vencida tira o status `campanha ativa` da fonte sozinha e aparece como **Vencida**. |
| **Aba Pausas** | Histórico de pausas e despausas (quem, quando, motivo, claim ligado). **Pausar fonte** exige motivo. |
| **Aba Dossiês** | Lista os dossiês de jogo e edita os campos: aliases, callbacks culturais, detalhes a observar, cuidados de spoiler. |

### Escudo

| Componente | Regras de comportamento |
|---|---|
| **Cooldowns** | Contagem regressiva por rede. **Limpar** só existe no cooldown criado pelo operador e exige motivo; o automático (cadência ou claim) mostra o motivo e quando termina, sem botão (C1). |
| **Registrar claim** (ESC-8) | Formulário: rede, link do vídeo afetado, tipo (claim de bloqueio, strike, desmonetização), motivo. Antes de confirmar, mostra a consequência por escrito: "Pausa a fonte X em todas as redes. N cortes saem do pacote e da fila." Confirmar aciona o disjuntor. |
| **Histórico de claims** | Lista dos claims registrados, com a fonte pausada e o link. |

### Saúde

| Componente | Regras de comportamento |
|---|---|
| **Aba Motor · matriz** | Linhas = projetos; colunas = partes do motor (`engine_health.json`). Célula com texto: ok · não se aplica · falhou. O motivo aparece ao focar; a frase-resumo fica no topo da linha. Projeto sem `engine_health.json`: "saúde não registrada (projeto anterior ao registro)". |
| **Aba Benchmark** | Precision@K por versão (baseline, 3.6.x…), com a faixa do acaso e **o n de VODs ao lado de cada número**. Abaixo de 3 VODs: aviso "amostra pequena". Progresso **"x de 20 VODs com gabarito"** rumo à 3.6.6. (limiar inicial) |
| **Aba Sistema** | Uma linha por item, com o rótulo do Contrato e "verificado há X":<ul><li>GPU/VRAM e preset de visão (SIS-1);</li><li>lock de VRAM (SIS-3);</li><li>disco livre;</li><li>banco (SQLite, SIS-5);</li><li>`yt-dlp` + ejs + `node`, `demucs` (SIS-11);</li><li>servidor MCP (SIS-12);</li><li>Modo Madrugada (parcial, SIS-4);</li><li>canário semanal e `yt-dlp` diário (travados, SAU-5).</li></ul> |

### Aprendizado e Configurações

| Componente | Regras de comportamento |
|---|---|
| **Seções do Aprendizado** | Snapshots 1h/24h/7d, recompensa, Bandit, reciclagem A/B, dataset e pesos calibrados, cada uma travada com o `depende_de`. Contadores reais no topo: 👍/👎 coletados, publicações com link, gabaritos x/20. |
| **Configurações** | Seções:<ul><li>**Motor de IA:** padrão e disponibilidade;</li><li>**Preset de visão:** auto / low / high;</li><li>**Marca e legendas:** presets de estilo;</li><li>**Credenciais de app:** Twitch e YouTube Data API; o segredo aparece mascarado e é gravado cifrado (regra 3). Estados: validando → aceito / recusado;</li><li>**Modo Madrugada:** janela de horário, parcial;</li><li>**Custos:** teto mensal (regra 6), travado `codigo` até existir o registro de gastos;</li><li>**Notificações.**</li></ul> |

## State Patterns

| Estado | Onde | Tratamento |
|---|---|---|
| **Abrindo o painel** | Lives | *Skeleton* só nos blocos com dado real a caminho; travados já aparecem travados. |
| **Primeira execução sem credenciais** | Lives | Recentes funciona **sem chave**, como **Parcial**: lista pelo `yt-dlp`, sem estatísticas. Com a chave da YouTube Data API, vira Ligado. Assim a home nunca abre inteira travada. A faixa mostra "Configure a chave do YouTube para listas completas." (aprovado pelo dono; respeita o P1, porque só lista canais liberados) |
| **Nenhum streamer cadastrado** | Lives | "Nenhum streamer cadastrado." + **Cadastrar fonte**. Colar link e arrastar arquivo continuam funcionando. |
| **Ao vivo sem credencial** | Lives › Ao vivo | Travado `config`: "Para ver quem está ao vivo, configure o app da Twitch (grátis)." + **Configurar**. |
| **Ninguém ao vivo** | Lives › Ao vivo | "Nenhum streamer cadastrado está ao vivo agora. Verificado há 2 min." + atalho para Recentes. |
| **Em alta antes do E5** | Lives › Em alta | Travado `codigo`: "Chega na história 5.1 (radar com a ordenação oficial das plataformas)." |
| **Recentes vazio** | Lives › Recentes | "Nenhum vídeo novo dos streamers cadastrados nos últimos N dias." A API falhou: Indisponível agora + Tentar de novo. |
| **Colou algo que não é vídeo** | Lives | "Isso não parece um link de vídeo do YouTube, Twitch ou Kick." Nada é aberto. |
| **Picorte desligado** | Global | "O Picorte não está rodando neste computador." + o comando **certo para o sistema** (Windows ou Linux). Nada de dado em cache fingindo estar vivo. |
| **Tempo real caiu** | Global | O ícone do tempo real no pé da sidebar mostra "Reconectando…". Barras de progresso congeladas mostram "sem atualização há X" (nunca parecem rodando). Ao voltar, tudo atualiza sem recarregar. |
| **Capacidades ilegíveis** | Global | Ver Contrato, regra 6. |
| **Portão respondendo** | Sala | "Verificando a fonte…" no passo 1; os passos 2 a 11 esperam. |
| **Fonte barrada** | Sala | "Este canal não está cadastrado. Nada foi baixado." + **Cadastrar fonte** (Fontes com o canal preenchido; C1). |
| **Fonte pausada** | Sala · Fila · Revisão · Publicação | "Fonte pausada por claim em data (motivo)." Na Sala, cortar fica desabilitado. Na Fila, jobs dessa fonte ficam em espera. Na Revisão, cortes visíveis mas sem Renderizar. Na Publicação, os cortes saem do Pacote do Dia com o motivo. Saída: Fontes › formulário de permissão (despausar com base, evidência e motivo). |
| **Já cortado ou na fila** | Sala | "Este vídeo já tem um projeto (status)." + **Abrir projeto**. |
| **Motor indisponível** | Sala · Configurações | Opção desabilitada com motivo e data (ex.: Gemini 429). O padrão vira o último motor que funcionou. |
| **Sem IA escolhido** | Sala | Aviso fixo: "Sem IA: arquétipos, tiers, Editor-Chefe e Scout não rodam." Confirmação na primeira vez. |
| **Fila vazia** | Fila | "Nada na fila. Corte um vídeo pela vitrine." |
| **Job falhou** | Fila · faixa (chip Falhas) · notificação | Frase + ação na linha; o chip **Falhas (n)** leva à Fila filtrada. |
| **Nenhum projeto aberto** | Revisão (`g r` sem histórico) | "Nenhum projeto para revisar ainda." + atalho para a Fila. |
| **Projeto sem cortes** | Revisão | "O motor não achou cortes acima da nota mínima." + **Buscar de novo neste vídeo**. |
| **Sinal não medido** | Revisão | Linha com "não medido" + motivo ("vídeo sem chat", "modo cego do conjunto de prova", "a visão não rodou"). |
| **Render falhou** | Revisão | Corte em **Render falhou** + **Renderizar de novo** + detalhe técnico recolhido. |
| **Corte sem veredito P1** | Revisão · Publicação | "Renderizado antes do Escudo. Sem veredito — re-auditar." Não entra no Pacote do Dia até ter veredito. |
| **Pacote vazio** | Publicação | "Nenhum corte pronto para hoje." + quantos estão esperando render ou revisão. |
| **Projeto antigo sem portão (W5)** | Publicação | "Rode o preparo de novo para o portão registrar a fonte." + **Preparar de novo**. |
| **Link pendente** | Publicação · faixa | Cartão marcado "postado? cole o link" desde a exportação (C2). |
| **Sem campanhas / políticas / barrados / pausas** | Fontes | Vazio por aba, numa linha. Políticas não sincronizadas = travado `dado` (B6). |
| **Sem cooldown / sem claims** | Escudo | "Nenhuma rede em cooldown." · "Nenhum claim registrado." |
| **Sem projetos** | Saúde | "A saúde aparece depois do primeiro corte." |
| **Benchmark com amostra pequena** | Saúde › Benchmark | "n = 1 VOD · amostra pequena". |
| **Credencial validando / recusada** | Configurações | "Validando…" → "Aceita" ou "A Twitch recusou essa credencial." |
| **Área inteira travada** | Aprendizado · Radar | Seções desenhadas, cada uma travada com o que falta; contadores reais no topo. |
| **Dado de terceiro vencido** | Lives | Thumbs e metadados com mais de 30 dias são apagados e buscados de novo (AD-9). |
| **Destravou agora** | Qualquer | O item troca para ligado ao vivo, com o marcador **Novo**. |

## Interaction Primitives

**Teclado primeiro na Revisão.** O dono assiste quase todos os cortes; é o caminho mais repetido do produto.

| Tecla | Ação |
|---|---|
| `J` / `K` | Próximo / corte anterior |
| `Espaço` | Play / pausa |
| `←` / `→` | Voltar / avançar 2 s |
| `I` / `O` | Marcar início / fim na posição atual |
| `1` / `2` | 👍 / 👎 |
| `R` | Renderizar o corte |
| `D` | Descartar (com desfazer) |
| `E` | Salvar como Exemplo Ouro |
| `Shift+.` / `Shift+,` | Velocidade + / − |
| `g` + letra | Ir para uma área (sequência: `g` e depois a letra, em até 1 s) |
| `[` | Fixar ou soltar a sidebar |
| `Ctrl+K` | Paleta de comandos |
| `Ctrl+V` (na vitrine) | Colar um link e abrir a Sala |
| `Esc` | Fechar modal, sair da edição, devolver o foco à lista |
| `?` | Lista de atalhos |

**Regra de foco:** com o foco num campo de texto (título, faixa, legenda), **todas** as teclas de letra única ficam desligadas. `Esc` sai do campo e religa os atalhos. A sequência `g` + letra não conflita com `R`/`E`, porque só vale logo depois do `g`.

**Mouse:**
- clique age; arrastar só nas alças da waveform e para soltar um arquivo na vitrine;
- ações principais nunca só no hover.

**Proibido:**
- rolagem infinita;
- modal sobre modal;
- confirmação para ação desfazível;
- botão que finge funcionar;
- número sem fonte;
- "marcar como postado" sem link.

## Accessibility Floor

O contraste visual fica no `DESIGN.md`.

- **Status nunca só por cor:** sempre ícone + palavra do vocabulário fixo.
- Tudo é operável por teclado; a ordem de `Tab` segue a leitura; o foco fica sempre visível.
- O progresso dos jobs e o "destravou" são anunciados por `aria-live` (educado).
- `prefers-reduced-motion` respeitado: o movimento-assinatura e as transições viram troca simples.
- Campos com rótulo claro; o player tem controles acessíveis.
- Alvo WCAG 2.2 AA.

## Responsive & Platform

| Largura | Comportamento |
|---|---|
| ≥ 2560 px (alvo) | Revisão em 3 colunas largas; vitrine com 5–6 cards por linha. |
| 1920–2559 px | 3 colunas com a ficha mais estreita; 4 cards por linha. |
| 1280–1919 px (notebook) | A sidebar não fica fixa aberta, mesmo com o alfinete; a ficha do corte vira gaveta à direita. |
| < 1280 px | Fora do escopo: "Use uma janela maior." |

- **Plataforma:** Windows 11 e Linux, nos navegadores Chromium e Firefox (C4).
- **Notificações** pela API do navegador:
  - opt-in;
  - funcionam com a aba **aberta em segundo plano** (minimizada ou atrás de outras janelas);
  - **com o navegador fechado não há aviso**: o resultado espera na faixa "Na sua mesa".

## Tempo real e concorrência

- **SSE** (`/api/eventos`) atualiza jobs, faixa, sidebar (contagens e estado do sistema) e capacidades.
- **Abrir ou ler nunca escreve estado.** Job com lock de outra sessão ou da CLI é mostrado e não é tocado.
- **Fila única:** cortes e renders, pedidos pelo painel ou pelo Claude/Gemini (MCP), entram na mesma fila serial e aparecem na Fila e no chip "Na fila".

## Dados de terceiros

- **Fontes dos dados:** listas de vídeos, thumbs e status de live vêm das **APIs oficiais** (YouTube Data API, Twitch Helix), com custo R$ 0 dentro da cota. Sem chave, Recentes usa o fallback parcial (ver State Patterns).
- **Em alta:** usa só a ordenação oficial das plataformas; nunca um ranking nosso entre canais de terceiros (YouTube III.E.2.a).
- **Cache:** no máximo 30 dias (AD-9).

## Inspiration & Anti-patterns

- **Da Twitch:**
  - grade de lives ao vivo com selo e espectadores;
  - abrir uma live numa página com o player grande e um painel ao lado (na Twitch é o chat; aqui é o **painel de corte**).
- **Do YouTube:**
  - prateleiras horizontais por streamer, com a opção "tudo por data";
  - thumbs grandes;
  - página do vídeo com o player em destaque.
- **Rejeitado: "caixa que aperta links + Find clips"** (palavras do dono). Colar link e arrastar arquivo continuam existindo, mas a porta de entrada é a vitrine.
- **Rejeitado: hero de landing page** ("Find the moment. Make the cut.").
- **Rejeitado: nota geral como ordem principal** (saturada em 10.0 no motor atual).
- **Rejeitado: "Em breve" genérico.** Todo travado diz o que falta e qual história destrava.
- **Rejeitado: dados de exemplo** em qualquer lugar (A5).
- **Rejeitado: editor de timeline** (A1). Só início, fim, títulos e legendas.

## Key Flows

### Flow 1 — A manhã depois da madrugada (Bomba, terça, 9h, café na mão)

1. Bomba abre o Picorte. A vitrine carrega em **Recentes**. A faixa **Na sua mesa** mostra "Revisar (2) · Links pendentes (2)" (dois cortes exportados ontem ainda sem link).
2. Clica em **Revisar (2)**. A Revisão abre em "CAÇANDO TESOURO! - GRAND THEFT AUTO 6 - Parte 2", Alanzoka, 15 cortes. O cabeçalho diz: "Este vídeo rodou sem visão e sem chat (upload comum). Comentários do público medidos."
3. Aperta `Espaço`. O primeiro corte (ouro, `descoberta_detalhe`) toca. Na ficha: riso medido, comentário do público medido, chat "não medido: vídeo sem chat".
4. O fim corta o riso: aperta `O` dois segundos depois. Dá `1` (👍), `J` para o próximo. Repete por 20 minutos, descartando 4 cortes com `D`.
5. Aperta `R` nos que ajustou. Os renders entram na fila única; o anel da GPU no pé da sidebar começa a encher ("Renderizando 1/6" ao passar o mouse). Os outros cortes aprovados já tinham sido renderizados sozinhos na madrugada (padrão "Renderizar sozinho"), então a Revisão foi escolha dele, não obrigação (C3).
6. Vai para **Publicação**. O Pacote do Dia tem 3 cortes respeitando a cadência; um ficou de fora: "cooldown do TikTok até 14h". Ele exporta, copia título e descrição do primeiro e posta no Shorts.
7. **Clímax:** cola o link no cartão. O corte vira **Publicado**, e o chip **Links pendentes** cai na hora. Ele sabe que esse corte vai ser medido.

**Falha:** o link colado não é de uma rede aceita → "Esse link não é do YouTube, TikTok, Instagram ou Facebook." O campo mantém o texto.

### Flow 2 — Cortar um VOD que acabou de sair (Bomba, quinta, 22h)

1. Em **Recentes**, a prateleira do Davy Jones mostra "GTA 6 É AGORA , O INICIO DA GAMEPLAY" (11h20), sem marcação do Picorte.
2. Clica. A **Sala do vídeo** abre; o portão responde: "DAVY JONES · liberado (tolerância pública)".
3. Escolhe 9:16, "Games · facecam no topo", motor **Ollama** (o Gemini aparece como "Indisponível agora: sem cota desde 21/11"), caça **Profunda** e "Renderizar sozinho".
4. O preview mostra o enquadramento sobre a thumb real do vídeo.
5. **Clímax:** aperta **Cortar este vídeo**. O card na vitrine ganha "na fila", e a faixa mostra "Na fila (1) · Baixando". Ele deixa a aba aberta em segundo plano; a notificação avisa quando os cortes ficam prontos.

**Falha:** o YouTube bloqueia o download ("robô").
- A notificação avisa e o chip **Falhas (1)** aparece.
- O chip leva à Fila filtrada: "O YouTube bloqueou o download. Troque de IP (reinicie o modem) e tente de novo." + **Retomar**.

### Flow 3 — Canal fora do cadastro (Bomba, sábado, à tarde)

1. Um amigo manda o link de uma live do BisteconeLive. Bomba aperta `Ctrl+V` na vitrine.
2. A Sala abre; o portão responde: "BisteconeLive não está cadastrado. Nada foi baixado." O painel de corte fica desabilitado.
3. **Cadastrar fonte** abre o formulário de permissão com o canal preenchido.
4. Ele escolhe status `liberada`, base "tolerância pública", cola o link de evidência, escreve o motivo e salva (C1).
5. **Clímax:** volta para a Sala; o portão diz "liberado (tolerância pública)" e o painel de corte acende. Nenhum download aconteceu antes da decisão dele.

**Falha:** evidência vazia → "Falta a evidência (link ou nota)." O formulário não salva sem ela.

### Flow 4 — A Twitch destrava sozinha (Bomba, domingo)

1. Em Configurações › Credenciais de app, Bomba cola o Client ID e o segredo do app grátis da Twitch e salva. A tela mostra "Validando…".
2. A sonda valida: "Aceita".
3. **Clímax:** sem recarregar, a aba **Ao vivo** perde o cadeado e ganha o marcador **Novo**. Dois streamers cadastrados aparecem ao vivo, com espectadores e "verificado agora". O player da live funciona; "Cortar ao vivo" continua travado ("Chega na história 5.2").

**Falha:** "A Twitch recusou essa credencial." O Ao vivo continua travado (`config`).

### Flow 5 — Chegou um claim (Bomba, segunda, 18h)

1. O YouTube Studio avisa um claim de bloqueio num Short do Coringa.
2. Bomba abre **Escudo › Registrar claim**: rede YouTube Shorts, cola o link do vídeo, tipo "claim de bloqueio", motivo "música do jogo".
3. Antes de confirmar, o formulário mostra: "Pausa a fonte CORINGA em todas as redes. 3 cortes saem do pacote e 1 job sai da fila."
4. Confirma. O disjuntor pausa a fonte.
5. **Clímax:** na hora, o Pacote do Dia mostra os 3 cortes fora ("fonte pausada por claim"), a Fila marca o job em espera, os cards do Coringa na vitrine ganham "fonte pausada", e Fontes › Pausas registra o claim ligado.

**Falha:** o link não é de um corte publicado pelo Picorte → "Não achei esse vídeo entre os publicados. Escolha a fonte à mão." O formulário passa a pedir a fonte.

## Open Questions

Confirmadas pelo dono em 2026-11-21:
- Sala como página;
- Recentes por streamer;
- avançar sozinho;
- descartar ≠ 👎;
- sidebar autorretrátil;
- destaque do topo.

Propostas da revisão de cobertura (decididas pelo dono em 2026-11-21):
- ~~Padrão "Renderizar sozinho"~~: **aprovado pelo dono em 2026-11-21 (opção A)**.
- ~~Fallback do Recentes pelo `yt-dlp`~~ e ~~saída "Não vou postar"~~: **aprovados pelo dono em 2026-11-21**.
- **Valores iniciais ajustáveis na implementação** (não bloqueiam): prazos de "desatualizado", desfazer por 8 s, setas de 2 s, 5–6 cards por linha, limiar de amostra pequena = 3 VODs.

Fora deste documento porque não existem no backend:
- cancelar um job em andamento;
- escolher um trecho do VOD antes de cortar.
