---
title: 'technical research: motor de seleção de cortes de lives/VODs de games'
type: 'technical'
topic: 'motor de seleção de cortes de lives/VODs de games (Picorte)'
decision: 'O que entra no motor de seleção E3/E3.5 (arquétipos novos, fusão de sinais, melhorias) — insumo da etapa 2b/2c'
source: 'run'
status: complete
preset: 'standard'
validation: 'normal'
created: '2026-11-21'
updated: '2026-11-21'
claims_verified: 5
claims_unverified: 3
---

# Pesquisa técnica: motor de seleção de cortes de lives/VODs de games

**Decisão que esta pesquisa serve:** o que entra no motor de seleção do Picorte (E3/E3.5) — arquétipos novos, como combinar sinais e melhorias gerais — como insumo do brainstorming (2b) e da validação (2c).

## Resumo executivo

1. **O que viraliza são reações de pessoas, não lances de jogo.** Os clipes mais vistos da Twitch giram em torno de reação, constrangimento, susto, perda dramática e hostilidade; até a perda de um mundo de Minecraft vale pela reação [1]. O modelo acadêmico treinado em ~2 milhões de clipes da Twitch já separa "falha", "constrangedor" e "vergonhoso" como contextos próprios [2]. **O arquétipo nobada/vacilo tem respaldo** e faz par com "constrangimento", que também nos falta.
2. **Sinal bom importa mais que muitos sinais.** Em LoL, o vídeo sozinho deu F1 72,2, o chat sozinho 43,2 e os dois juntos só 74,7 [4]; no KuaiHL, tirar o visual custa 4,7% e tirar o texto 2,0% [3]. E o heatmap "mais repetidos" é ruidoso: nem humanos acertam melhor que o acaso [9]. Isso confirma a sua intuição (mais partes funcionando ajuda) **com um limite**: cada sinal precisa estar medido de verdade e calibrado — de novo o papel do registro de saúde.
3. **Três consertos baratos aparecem com força:** (a) o chat reage **~20–27 s depois** do momento — o pico tem de ser puxado para trás [5]; (b) a **escolha de início e fim** é o que mais pesa na qualidade de um corte gerado (gancho cai de 0,71 para 0,28 com bordas aleatórias) [16]; (c) o LLM que reordena uma lista é **sensível à ordem** dos candidatos [7].
4. **Dá para medir sem anotar à mão:** os clipes que os espectadores da Twitch criam (API oficial com o segundo exato no VOD [11]) e o desempenho dos nossos cortes publicados viram "gabarito automático", como fazem os papers [5][3][10].

**Maior ressalva:** quase não há evidência pública sobre lives brasileiras nem sobre vários tipos (doação lida, falha técnica, fala fora de contexto, autodepreciação, "skill issue"). Esses ficam como hipótese para o brainstorming, não como fato.

## (a) Arquétipos que faltam

**Achados.** O Kotaku analisou os clipes mais vistos da história da Twitch e achou negatividade em quase todos: ameaça real ao streamer, constrangimento público com silêncio da plateia, susto real, perda dramática com contexto de anos, hostilidade contra a streamer, e uma exceção wholesome [1]. Conclusão do texto: o topo é sobre pessoas e reações, não sobre o jogo [1]. O paper EPJ (MINT, ~2 mi de clipes) cobre vitória, engraçado, constrangedor e vergonhoso, com exemplos de "failing", "outplay" e momentos fora do jogo, e usa emotes do chat como componente crítico (confiança média: só o resumo dos autores foi lido) [2]. Ferramentas comerciais de clipping para games separam "momentos de habilidade" de "momentos emocionais" (risada incontrolável, rage quit, grito) [12]. A Twitch, em 2017, achou dois temas de clipe pelos emotes: hype (PogChamp) e emoção/compaixão (BibleThump) — hipótese sem validação [8]. KEKW é usado para rir de erro e clutch falho (fonte fraca) [25].

**Tabela — arquétipos com respaldo e sinais**

| Arquétipo | Temos hoje? | Sinais com evidência | Fontes |
|---|---|---|---|
| Fail/nobada/vacilo | **Não** (`clutch_fail` busca lance épico) | riso no chat (KEKW/LUL), riso no áudio, morte/tela de derrota (inferência) | [2][25][13] |
| Constrangedor/vergonhoso (silêncio, mico) | **Não** | categorias próprias no EPJ; sinal específico não documentado | [2][1] |
| Rage/surto/rage quit | verificar no 2b | grito, variação de voz | [12] |
| Susto real | sim (susto >18 dB) | reação genuína | [1][15] |
| Emocional/wholesome | verificar no 2b | cluster de emotes de compaixão | [8][1] |
| Perda dramática com contexto | verificar no 2b | vale pela reação + contexto, não pelo gameplay | [1] |
| Hostilidade/treta | verificar no 2b | negatividade domina o topo | [1] |
| Vitória/outplay (hype) | sim | pico de Pog, eventos de jogo, grito | [2][8][12] |
| Fora do jogo/conversa/fala intrigante | parcial (texto) | gancho na transcrição | [2][15] |

**Sem evidência encontrada (hipóteses para o 2b):** doação lida em voz alta, falha técnica ao vivo, fala fora de contexto, autodepreciação, sorte absurda/bug, "skill issue"/"F" como sinal, silêncio súbito como sinal de constrangimento.

**Detalhe técnico útil:** emotes mudam rápido (8 mi de emotes distintos, 400 mil usados numa semana) — uma lista fixa envelhece; dá para aprender o sentido dos emotes pelo contexto [14]. O PogChamp original foi removido da Twitch em 2021; variantes vivem em extensões de terceiros (fonte fraca) [25].

## (b) Como combinar os sinais e medir

**Como os outros fazem.** Os trabalhos acadêmicos **aprendem** os pesos em vez de fixá-los: Fu et al. juntam vídeo e chat numa rede pequena [4]; o KuaiHL (Kuaishou) usa atenção sobre imagem, fala, comentários e identidade do streamer, corrige o desalinhamento de tempo entre eles e treina com **ranking por pares** (+2% de acerto na ordem) [3]. A abordagem dominante trata highlight como "este trecho é melhor que aquele do mesmo vídeo" [3][4]. Com LLM como juiz, o HiVid dá nota em janelas e depois reordena por comparações para corrigir a escala entre janelas [6] (fonte única); e rerankers por LLM mudam o resultado conforme a ordem dos candidatos no prompt [7] (não verificado).

**Quais sinais predizem.**
- **Chat:** contagem de mensagens funciona para os poucos melhores momentos; para achar mais, ajudam **mensagens curtas/emotes** e **todo mundo falando a mesma coisa** (janela de 25 s) [5]. Enganam: bots de propaganda e conversa paralela [5]. Atraso do pico: **~20 s, deslocamento aprendido de 23–27 s** em Dota 2 e LoL [5] (não verificado: única fonte; busca de confirmação não achou segunda).
- **Vídeo/imagem:** foi a modalidade mais forte nos dois estudos com números [3][4].
- **Riso:** detector aberto existe; riso sozinho não é highlight pronto, mas "trecho seguido de riso" é um bom rótulo de engraçado [13].
- **Heatmap "mais repetidos":** ruidoso — modelos acertam pouco acima do acaso e humanos não superam o acaso; só aparece com dezenas de milhares de views [9]. Útil como rótulo agregado em massa [10], fraco como sinal isolado.

**Medir sem anotar à mão.** Opções com evidência: (1) **clipes da Twitch** — a API oficial devolve o segundo de início no VOD, views e duração [11] (não achamos paper validando-os como rótulo; é hipótese razoável); (2) **"mais repetidos"** agregados, como no Mr.HiSum (31.892 vídeos) [10]; (3) **comportamento de quem assiste** — o KuaiHL usa a fração de quem assistiu além de um limite [3], o que no nosso caso é a retenção dos cortes publicados. Métricas práticas: **Precision@K** comparada com o acaso (K/N) [9][5].

## (c) Melhorias em geral

**Ferramentas open-source.** As duas mais ativas escolhem trechos só com LLM lendo a transcrição; a imagem serve apenas ao enquadramento [17][18]. Truque útil do AutoClip: o LLM devolve **índices de palavras**, e o tempo vem dos timestamps do Whisper, então o LLM nunca inventa horário [17]. O OpenShorts escolhe layout por cena (rosto, fundo borrado, dois falantes, tela) e tem issue aberta pedindo layout gameplay + facecam em 9:16, que ninguém resolveu [18]. Nenhuma das duas mede se as escolhas são boas [17][18].

**Corte que se sustenta sozinho.** O HIVE monta cortes em etapas (quem fala, cenas, nota por cena, juntar vizinhas, escolher abertura e fechamento, podar irrelevantes) e mostra que **abertura e fechamento são o fator que mais pesa** [16]; mesmo assim, editores humanos ainda ganham com folga (gancho 0,87 contra 0,71) [16].

**Duração e plataformas.** Num levantamento de 108 mil Shorts, 11–20 s teve mais views medianas (901) e acima de 45 s caiu muito — mas é dado de vendor, de views e não de retenção [19] (não verificado). O TikTok só paga vídeos ≥60 s (blogs, sem página oficial confirmada) [20]. **O sinal mais importante:** desde outubro de 2026 o YouTube reduz o alcance de canais que repostam clipes de terceiros sem mudança significativa, e "edições técnicas mínimas" ou "mudanças em massa por template" não contam [21][22]; a política de conteúdo reaproveitado vale mesmo com permissão do autor e pode desmonetizar o canal [23]. As redes de clipping pagas valorizam reação emocional, confronto e polêmica [24].

## Insights que só a combinação mostra

1. **Arquétipo + sinal + transformação andam juntos.** O que viraliza é reação humana [1][2]; o que o YouTube exige é transformação real [21][23]. Um corte de nobada com contexto curto, gancho próprio e comentário/edição original atende os dois — já um corte cru, por melhor que seja o momento, perde alcance.
2. **O gargalo não é ter mais sinais, é calibrar os que temos.** Fusão ganha pouco sobre o melhor sinal [4][3], o heatmap é ruidoso [9] e o chat tem atraso de ~20 s [5]. Isso reforça a saúde do motor e a medição (Precision@K com gabarito automático) antes de inventar sinais novos.
3. **Bordas valem mais que a nota.** O HIVE mostra que abertura/fechamento pesa mais que a etapa de highlight [16], e o atraso do chat desloca a borda [5]: o snap de bordas do Picorte é tão importante quanto a escolha.

## Recomendações (para o brainstorming 2b e a validação 2c)

| # | Recomendação | Base / confiança |
|---|---|---|
| R1 | Criar os arquétipos **nobada/vacilo** e **constrangimento/mico**; avaliar no 2b rage, wholesome, perda dramática e treta | [1][2] — média-alta |
| R2 | Deslocar o pico do chat ~20–25 s para trás e usar 3 traços de chat (volume, mensagens curtas/emotes, mesma coisa repetida); filtrar bots | [5] — média (fonte única) |
| R3 | Embaralhar a ordem dos candidatos ao Editor-Chefe (ou comparar em pares) | [7][6] — média-baixa |
| R4 | Montar o **gabarito automático** com clipes da Twitch (API oficial) e, depois, retenção dos cortes publicados; medir com Precision@K contra o acaso | [11][3][9] — média (hipótese aplicada) |
| R5 | Só depois de R4, trocar pesos "a olho" por pesos aprendidos com ranking por pares (liga com o Cérebro que Aprende, Épico 7) | [3][4] — média |
| R6 | LLM devolver índices de palavras, não segundos | [17] — alta (técnica documentada) |
| R7 | Tratar abertura/fechamento como etapa própria (frente de formato: Cold Open, contexto mínimo) | [16] — alta |
| R8 | Reforçar o Score de Transformação (P2): variação real por corte, não só template | [21][22][23] — alta |
| R9 | Heatmap como bônus fraco, não sinal forte; manter registro de saúde quando ausente | [9] — alta |
| R10 | Duração: revisar no 2b o alvo de Shorts (curtos) × TikTok (≥60 s para pagar) | [19][20] — baixa-média |

## Medição própria: atraso do chat (2026-11-21)

Dado nosso, não da web. VOD `x50ONQrBPRM` (replay de live no YouTube, Gameplayrj, PT-BR), primeiros 52 min: 10.815 mensagens (206/min, 553 de riso) contra o volume do áudio a cada 1 s (silêncio digital limitado a −50 dB). Script: `chat_delay.py` (scratchpad da sessão; não versionado).

| Leitura | Resultado |
|---|---|
| Correlação cruzada áudio → chat (todas as mensagens) | melhor atraso **25–28 s** |
| Correlação cruzada áudio → chat (só riso: kkk, haha, 😂) | melhor atraso **35–38 s** |
| Média do chat em volta dos 25 maiores saltos de volume | chat começa a subir em **+20 s**, pico em **+25 a +35 s** |
| 20 maiores picos de chat → maior salto de áudio antes | mediana **30 s** (quartis 18–52 s, muito espalhado) |

**Leitura:** confirma a literatura [5] e fica um pouco acima (~30 s contra 20–27 s), coerente com a latência maior do YouTube e com o riso digitado vindo depois. As correlações são fracas (≈0,06): volume sozinho é um sinal pobre, e o atraso individual varia muito — por isso o deslocamento deve ser uma janela, não um número exato. Limitação: um VOD, um streamer, 52 min.

**Situação no código hoje:** o Sismógrafo não compensa atraso nenhum — a janela de um pico de chat é `[pico − 6 s, pico + 8 s]` (`picorte/engine/chat_seismic.py:148`) e `score_chat_window` credita ao candidato o chat **dentro** do próprio trecho. Ou seja, o corte semeado por pico de chat começa ~25 s **depois** do momento que causou o pico. Entra na etapa 3 como correção (R2 passa a ter base própria).

## Perguntas em aberto

- Clipes da Twitch criados por espectadores são bom rótulo? Responder: comparar, em 2–3 VODs com clipes, Precision@K do seletor atual (nenhum paper encontrado).
- ~~Atraso do chat no YouTube/BR~~ → medido: ~25–35 s (ver "Medição própria"). Falta repetir em mais VODs/streamers.
- Sinais de doação lida, falha técnica, fala fora de contexto, autodepreciação, "skill issue": sem evidência pública; levar como hipótese ao 2b.
- Retenção (não views) por duração em Shorts/TikTok/Reels: não encontrada.
- Relatos de editores de cortes brasileiros: só blogs de ferramentas; um Deepen poderia focar Reddit/fóruns/vídeos BR.
- Texto completo do paper EPJ/MINT e seu dataset (bloqueados nesta busca).

## Apêndice de fontes

| n | Sustenta | Publicador | Pub | Acesso | Confiança |
|---|---|---|---|---|---|
| [1] | Top clipes da Twitch = reações, negatividade | [Kotaku](https://kotaku.com/twitchs-most-watched-clips-have-almost-nothing-to-do-wi-1842038158) | 2020-03 | 2026-11-21 | alta |
| [2] | MINT/EPJ: failing, awkward, embarrassing; emotes críticos | [BMC On Physical Sciences](https://blogs.biomedcentral.com/on-physicalsciences/2021/09/02/epic-moments-live-streaming/) | 2021-09 | 2026-11-21 | média |
| [3] | KuaiHL: fusão por atenção, ranking por pares, ablação | [arXiv 2407.12002](https://arxiv.org/html/2407.12002v1) | 2024-06 | 2026-11-21 | alta |
| [4] | Fu et al.: vídeo 72,2 × chat 43,2 × ambos 74,7 | [ACL/EMNLP via ar5iv](https://ar5iv.labs.arxiv.org/html/1707.08559) | 2017-07 | 2026-11-21 | alta |
| [5] | Lightor: atraso 20–27 s, 3 traços de chat, bots | [arXiv 1910.12201](https://ar5iv.labs.arxiv.org/html/1910.12201) | 2019-10 | 2026-11-21 | média (unverified) |
| [6] | HiVid: LLM-juiz em janelas + reordenação | [arXiv 2602.14214](https://arxiv.org/html/2602.14214v1) | 2026-02 | 2026-11-21 | média |
| [7] | Rerank listwise sensível à ordem | [alphaXiv 2604.03642](https://www.alphaxiv.org/abs/2604.03642) | 2026-04 | 2026-11-21 | média (unverified) |
| [8] | Temas de clipe por emotes | [Twitch Blog](https://blog.twitch.com/en/2017/10/05/using-chat-emotes-as-signals-for-content-themes-13c31d4a0f74/) | 2017-10 | 2026-11-21 | média |
| [9] | Most Replayed ruidoso (YTMR500) | [arXiv 2309.06102](https://ar5iv.labs.arxiv.org/html/2309.06102) | 2023-09 | 2026-11-21 | alta |
| [10] | Mr.HiSum: Most Replayed como rótulo em massa | [GitHub MR.HiSum](https://github.com/MRHiSum/MR.HiSum) | 2023 | 2026-11-21 | alta |
| [11] | API Get Clips: vod_offset, views | [Twitch Developers](https://dev.twitch.tv/docs/api/reference/clips#get-clips) | 2026-11 | 2026-11-21 | alta |
| [12] | Powder: habilidade × emoção, grito, riso, chat | [TechCrunch](https://techcrunch.com/2023/11/20/powder-an-ai-clipping-tool-for-gaming-can-detect-when-a-creator-yells-during-a-stream) | 2023-11 | 2026-11-21 | média |
| [13] | Riso: detector aberto; FunnyNet-W | [arXiv 2401.04210](https://arxiv.org/html/2401.04210v1) / [laughter-detection](https://www.github.com/jrgillick/laughter-detection) | 2024-01 | 2026-11-21 | média |
| [14] | Emotes mudam rápido; aprender sentido | [arXiv 2108.08411](https://arxiv.org/abs/2108.08411) | 2021-08 | 2026-11-21 | alta |
| [15] | Testes Lição/Emoção Pura/Gancho | [StreamHub](https://streamhub.world/pt/streamer-blog/streaming/4109-content-repurposing-turning-long-form-streams-into-engaging-video-clips/) | 2026-09 | 2026-11-21 | média |
| [16] | HIVE: abertura/fechamento pesa mais | [arXiv 2507.02790](https://arxiv.org/html/2507.02790v2) | 2025-10 | 2026-11-21 | alta |
| [17] | AutoClip: índices de palavras | [GitHub artbyjazi/autoclip](https://github.com/artbyjazi/autoclip) | 2026 | 2026-11-21 | alta |
| [18] | OpenShorts: layout por cena, issue facecam | [GitHub mutonby/openshorts](https://github.com/mutonby/openshorts) | 2026-10 | 2026-11-21 | alta |
| [19] | Shorts 11–20 s com mais views | [quso.ai](https://quso.ai/research/youtube-shorts-length) | 2026-06 | 2026-11-21 | média (unverified) |
| [20] | TikTok paga ≥60 s | [Soundstripe](https://www.soundstripe.com/blogs/how-much-does-tiktok-pay-per-view) | 2026 | 2026-11-21 | média |
| [21] | YouTube reduz alcance de repostados | [Search Engine Journal](https://www.searchenginejournal.com/youtube-original-shorts-reposted-clips-reach/591774/) | 2026-10 | 2026-11-21 | alta |
| [22] | Confirmação independente de [21] | [Dexerto](https://www.dexerto.com/youtube/youtube-cracks-down-on-clipping-channels-in-shorts-update-prioritizing-original-content-3415700/) / [Social Media Today](https://socialmediatoday.com/news/youtube-updates-shorts-algorithm-to-put-more-focus-on-original-content/831976) | 2026-10 | 2026-11-21 | alta |
| [23] | Reused content vale mesmo com permissão | [YouTube Help](https://support.google.com/youtube/answer/1311392) | 2025-07 | 2026-11-21 | média |
| [24] | Redes de clipping pagas valorizam reação/confronto | [Streams Charts](https://streamscharts.com/news/manufactured-virality-how-paid-clipping-networks-became-streamer-marketings-hidden-engine) | 2026-05 | 2026-11-21 | alta |
| [25] | KEKW para erro; PogChamp removido | [Eklipse](https://blog.eklipse.gg/tips-trivia/twitch-trivia/kekw-meaning-twitch-emote-origin.html) | s/d | 2026-11-21 | baixa |

## Mapa de validade

Plataformas e regras (YouTube, TikTok) envelhecem mais rápido: rechecar [20][21][23] até **2027-02**; ferramentas open-source [17][18] e LLM-juiz [6][7] até **2027-02**; papers clássicos [4][5][9] e taxonomia [1][2] valem como padrão até ~2028.
