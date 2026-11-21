# Digest — (a) arquétipos — rodada 1, assistente 1

Método: 12 chamadas (7 buscas, 5 leituras, 2 falharam). Lidas de fato: Kotaku, blog BMC/EPJ, Twitch Engineering blog, StreamHub, TechCrunch; abstract arXiv Dolin et al. Paper EPJ completo bloqueado (Springer login / espelho 403) → só resumo dos autores e snippet. Acesso: 2026-11-21.

## Achados
- Song, Park & Cha, "Finding epic moments in live content through deep learning on collective decisions" (EPJ Data Science v10, 2021): modelo MINT treinado com ~2 milhões de clipes recomendados por usuários da Twitch + chats; separa "epic moments" (diversão) de "highlights" (informativos) | https://blogs.biomedcentral.com/on-physicalsciences/2021/09/02/epic-moments-live-streaming/ (DOI 10.1140/epjds/s13688-021-00295-6 não abriu) | BMC blog dos autores | 2021-09 | média | taxonomia/dado
- Contextos cobertos: vitória, engraçado, constrangedor ("awkward"), vergonhoso ("embarrassing"); exemplos de "failing", "outplay", "non-game" | mesma | BMC | 2021-09 | média | taxonomia
- O modelo combina reações do chat (emojis/emotes = "critical components"), estrutura dos frames, contagem de views e info do streamer; estudo com usuários achou sugestões comparáveis às de especialistas | mesma | BMC | 2021-09 | média | sinal
- Kotaku, clipes mais vistos da história da Twitch: padrão de negatividade — ameaça à segurança (tiro na janela do Dr Disrespect, swatting do Bugha), constrangimento/silêncio público (Ninja dançando floss diante de plateia muda), susto real (JurassicJunkieLive e a filha), perda dramática (Philza perdendo mundo hardcore de 5 anos), hostilidade contra a streamer (LivStix), exceção wholesome (Jesse D vendo o público crescer) | https://kotaku.com/twitchs-most-watched-clips-have-almost-nothing-to-do-wi-1842038158 | Kotaku | 2020-03 | alta | taxonomia/dado
- Kotaku: o topo gira em torno de pessoas e reações, não do jogo; até a perda do Philza vale pela reação e contexto (5 anos), não pelo gameplay | mesma | Kotaku | 2020-03 | alta | prática
- Twitch Data (2017): clipes agrupados por emotes no chat (TF-IDF, k=250, 30 dias) → dois temas: PogChamp (hype/awe) e BibleThump (emoção/compaixão); WutFace e Kappa no gráfico sem tema; autores tratam como hipótese sem validação | https://blog.twitch.com/en/2017/10/05/using-chat-emotes-as-signals-for-content-themes-13c31d4a0f74/ | Twitch Blog (Ariel Sagalovsky) | 2017-10 | média | sinal/taxonomia
- PogChamp original removido pela Twitch em 2021-01; variantes de Pog sobrevivem em plataformas de emotes de terceiros → detector só com emotes nativos perde o sinal (snippet) | Eklipse/Wikipedia | s/d | baixa-média | sinal
- KEKW usado de forma sarcástica para skillshot errado, clutch falho e momentos engraçados (snippet) | https://blog.eklipse.gg/tips-trivia/twitch-trivia/kekw-meaning-twitch-emote-origin.html | Eklipse | s/d | baixa | sinal
- Eklipse diz detectar picos de "KEKW", "LUL" ou risadas e tratar velocidade do chat + picos de emotes específicos como melhores indicadores; marketing sem algoritmo (snippet) | https://blog.eklipse.gg/?p=42257 | Eklipse | s/d | baixa | sinal
- Powder: 40+ modelos por jogo — eventos (vitórias, assistências, abates) em Fortnite/Valorant/Rocket League/CS2, detecção de risada, análise de áudio, detector de grito por variação de voz (a sair), "Community Hype" para picos de chat, busca por palavra na transcrição | https://techcrunch.com/2023/11/20/powder-an-ai-clipping-tool-for-gaming-can-detect-when-a-creator-yells-during-a-stream | TechCrunch | 2023-11 | média | sinal
- CEO da Powder: highlights = "skill-based moments" + "deeply emotional moments" (risada incontrolável, rage quits) e momentos sem nada óbvio na tela | mesma | TechCrunch | 2023-11 | média | taxonomia
- FunnyNet (ACCV 2022): rótulo "engraçado" = n segundos seguidos de risada; treinado, detecta engraçado mesmo sem risada no áudio; treinado em sitcoms/stand-up, não lives (snippet) | https://openaccess.thecvf.com/content/ACCV2022/papers/Liu_FunnyNet_Audiovisual_Learning_of_Funny_Moments_in_Videos_ACCV_2022_paper.pdf | CVF | 2022 | média | sinal
- Detecção de risada por picos de energia: F-score 81% áudio limpo, 71% ruidoso; código aberto jrgillick/laughter-detection (snippet) | https://www.github.com/jrgillick/laughter-detection | vários | s/d | baixa-média | sinal
- StreamHub (PT-BR): três testes — Lição, Emoção Pura (susto, comemoração, indignação, entendível sem conhecer o streamer), Gancho ("por que ele está dizendo isso?"); sem sinais | https://streamhub.world/pt/streamer-blog/streaming/4109-content-repurposing-turning-long-form-streams-into-engaging-video-clips/ | StreamHub | 2026-09 | média | prática/taxonomia
- Cut.Pro (PT-BR, autopromoção): canal de cortes cresce com reação, conversa, jogo com virada, "treta boa", história que se desenrola; não com compilação aleatória; no Kick viraliza aposta/cassino (restrito por TikTok/IG) (snippet) | https://cut.pro/pt-BR/blog/campeonato-de-cortes-para-streamer-2026 | Cut.Pro | 2026 | baixa | prática
- CatchLive (CHI 2022) e AntPivot (arXiv 2022) detectam picos sem taxonomia de tipos; AntPivot afirma não haver dataset público grande de highlights de lives (snippets) | https://kixlab.github.io/website-files/2022/chi2022-CatchLive-paper.pdf ; https://arxiv.org/abs/2206.04888v1 | KIXLAB/arXiv | 2022 | média | taxonomia (ausência)
- LIGHTOR (MSR, ICDE 2020): chat com timestamp estima onde está o highlight, refina com interação dos espectadores; Fu et al. (EMNLP 2017) previram highlights de LoL por reações do chat (snippets) | https://www.microsoft.com/en-us/research/uploads/prod/2020/02/icde20lightor.pdf ; https://aclanthology.org/D17-1102/ | MSR/ACL | 2020/2017 | média | sinal
- Dolin et al.: sentimento de neologismos e emotes da Twitch; corpus 8,06 mi emotes, >400 mil usados na semana; dicionário fixo envelhece → aprender o sentido (k-NN sobre embeddings) | https://arxiv.org/abs/2108.08411 | arXiv | 2021-08 | alta | sinal

## Tabela de arquétipos
| arquétipo | sinais típicos | fonte(s) |
|---|---|---|
| Vitória/outplay/skill (hype) | pico de Pog; eventos de jogo (abate, vitória, killfeed); grito | EPJ/BMC 2021; Twitch 2017; Powder 2023 |
| Fail/erro bobo ("nobada") | riso no chat (KEKW, LUL); "failing", "failed clutch" | BMC 2021; Eklipse (baixa) |
| Engraçado | pico KEKW/LUL; risada no áudio | BMC 2021; Eklipse; Powder; FunnyNet 2022 |
| Constrangedor/vergonhoso (incl. silêncio constrangedor) | categorias awkward/embarrassing; exemplo Ninja; sinal não documentado | BMC 2021; Kotaku 2020 |
| Rage quit/surto | grito, variação de voz | Powder 2023 |
| Susto/jumpscare | reação genuína; top clip; WutFace sem tema (hipótese) | StreamHub 2026; Kotaku 2020; Twitch 2017 |
| Emocional/wholesome | cluster BibleThump; top 1 Jesse D | Twitch 2017; Kotaku 2020 |
| Perda dramática com contexto | valor da reação + contexto; tela de morte/game over (inferência não verificada) | Kotaku 2020 |
| Ameaça/hostilidade real, treta | negatividade domina o topo; "treta boa" | Kotaku 2020; Cut.Pro (baixa) |
| Fora do jogo, conversa, fala intrigante | gancho falado na transcrição | BMC 2021; StreamHub 2026; Powder |
| Lição/dica | perguntas no chat (sugestão não verificada) | StreamHub 2026 |
| Aposta/cassino (Kick) | — (restrito TikTok/IG) | Cut.Pro (baixa) |

## Pistas
- Repo do MINT + dataset ~2 mi clipes (Song/Park/Cha 2021), PDF via PMC/ResearchGate.
- Tese de Ringer (York, 2022): https://etheses.whiterose.ac.uk/32406/1/PhD_Thesis__Revised_.pdf — streams "personality-driven" × "game-driven", chat.
- FunnyNet-W (arXiv 2401.04210); jrgillick/laughter-detection como detector local.
- Dolin et al. para aprender sentido de emotes 7TV/BTTV/FFZ.
- Ranking mensal Streams Charts / Twitch Strike para amostra atual de top clipes (incl. BR).
- LIGHTOR: atraso momento→pico de chat para calibrar janela.

## Não achei
- Taxonomia publicada e validada específica de clipes virais de games (só EPJ-resumo e Kotaku qualitativo).
- Evidência primária sobre: doação lida, falha técnica ao vivo, fala fora de contexto, autodepreciação, sorte absurda, bug/glitch, "skill issue"/"F" como sinais → crença não verificada.
- Silêncio súbito como indicador de constrangimento.
- Relatos PT-BR de editores sobre nobadas/alanzoka/Gaules/GTA RP (só blogs de ferramentas); r/LivestreamFail não coberto.
- Limiares de pico de chat publicados por ferramentas.
- Texto completo do EPJ.
