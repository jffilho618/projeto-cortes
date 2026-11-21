# Digest — (c) melhorias gerais — rodada 1, assistente 1

Acesso de todas as fontes: 2026-11-21. "(snippet)" = afirmação veio do resumo da busca, não da página lida; confiança rebaixada.

## Achados

**Ferramentas open-source**
- AutoClip (artbyjazi): seleção só por LLM sobre a transcrição; o LLM devolve índices de palavras e o tempo é resolvido pelos timestamps do Whisper (sem tempo inventado); detecção de shots só para reframe; reframe MediaPipe por shot sem interpolar; diarização WhisperX opcional; −14 LUFS. README admite que a qualidade "acompanha o modelo" e não há teste de qualidade da escolha | https://github.com/artbyjazi/autoclip | artbyjazi/GitHub | 2026 | alta | técnica
- OpenShorts (mutonby, ~9,5k ★, 726 commits): faster-whisper com timestamps por palavra + PySceneDetect; Gemini recebe transcrição + fronteiras de cena e devolve 3–15 momentos de 15–60s com nota de viralidade; só texto vai ao LLM (pode trocar por servidor local OpenAI-compatível); layout por cena: TRACK (MediaPipe+YOLOv8), GENERAL (fundo borrado), SPLIT (2 falantes, legenda na emenda), SCREENCAST | https://github.com/mutonby/openshorts | GitHub | 2026-10 | alta | ferramenta/técnica
- Issues abertas do OpenShorts (nov/2026) são quase todas de infra (crash render #199, Remotion #142/#179/#180, fila travada #188, caminho Windows #163). Relevante para games: facecam minúscula em 9:16, sem layout gameplay+facecam (#168, 2026-11-17). Nenhuma issue da 1ª página reclama da qualidade da seleção | https://github.com/mutonby/openshorts/issues | GitHub | 2026-11 | alta | ferramenta
- Clippers locais "alternativa ao Opus" ativos em 2026: HotClip, OpenClipper, OpisClip, MXClip (Ollama), FunClip (FunASR/SenseVoice, corte por texto/falante) (snippet) | https://github.com/topics/ai-clipping | GitHub topics | 2026 | média | ferramenta
- Detectores de pico de chat Twitch usam densidade de mensagens/emotes por janela (chatplot, twitch-highlight-finder push 2024-05, twitch-highlights-logger); CTIC diz usar burst estatístico + fuzzy matching de reações parecidas, repo 404 (snippet) | https://github.com/packsun/chatplot | GitHub | indeterminado | baixa | técnica
- Heurística citada: início do corte ~30s antes do pico de chat (chat reage com atraso); outro ranqueia por distância do pico à mediana móvel (snippet) | https://devpost.com/software/clip-it | Devpost | indeterminado | baixa | técnica
- "Most Replayed" sem API oficial; só scrapers (Apify, npm `yt_most_replayed`, que o autor chama de rudimentar); listing diz que o heatmap só aparece com ~50 mil views (snippet) | https://apify.com/karamelo/youtube-most-replayed-scraper-heatmap-extractor | Apify | indeterminado | média | plataforma/técnica

**Acadêmico — o corte que se sustenta**
- HIVE: pipeline em etapas (ASR corrigido por OCR, diarização + agrupamento de rostos, segmentação de cenas, nota por regras de highlight do gênero, junção de cenas adjacentes, escolha de abertura/fechamento entre cenas candidatas, poda de cenas irrelevantes) | https://arxiv.org/html/2507.02790v2 | arXiv | 2025-10 | alta | técnica
- HIVE números: abertura/fechamento é o que mais pesa — fronteiras aleatórias derrubam Hook Rate 0,71→0,28 e Suspense 0,73→0,30; sem etapa de highlight VEI 4,01→2,74; fluxo só ASR VEI 0,54; humano ainda lidera (VEI 6,35, Hook 0,87) | https://arxiv.org/html/2507.02790v2 | arXiv | 2025-10 | alta | número
- RankCut (IUI '26): LLM ranqueia segmentos da transcrição sob duração-alvo e um seletor monta em ordem cronológica (snippet); Video Trimming (arXiv 2412.09513): junta segmentos de alta saliência com filtro de trechos desperdiçados (snippet) | https://www2.informatik.uni-hamburg.de/wtm/publications/2026/SLCWBW26/iui26_Shah-et-al.pdf | Univ. Hamburg | 2026 | média | técnica

**Práticas de canais de cortes**
- quso.ai, 108.138 Shorts maduros (≥14 dias): views medianas 0–10s=514, 11–20s=901 (pico), 21–30s=542, 31–45s=347, 46–60s=188, 61–90s=186, 90s+=51. É views, não retenção; não isola tema/criador | https://quso.ai/research/youtube-shorts-length | quso.ai (vendor) | 2026-06 | média | número
- Limite dos Shorts subiu para 3 min em 2024-10; sem dado confiável de retenção para Shorts de 3 min (snippet) | https://www.overseeros.com/blog/best-youtube-shorts-length | Overseeros | 2026 | média | plataforma
- TikTok Creator Rewards: só vídeos ≥60s, originais, pós-adesão, ≥1.000 views qualificadas no For You; RPM citado US$ 0,40–1,00/mil. Blogs, sem confirmação oficial (snippet) | https://www.soundstripe.com/blogs/how-much-does-tiktok-pay-per-view | Soundstripe | 2026 | média | plataforma/número
- Inferência do assistente (combina as duas acima): conflito de duração — Shorts curtos (11–20s) têm mais views, TikTok só monetiza ≥60s | — | — | — | média | prática
- PT-BR (vendor, opinião): clímax nos 3s iniciais, imagem inicial que prenda sem som, gancho → contexto breve → convite; cortar silêncio e leitura de chat; queda no início da curva = gancho fraco, no fim = corte longo; 25–40s a 60s (snippet) | https://streamhub.world/pt/streamer-blog/strategy/3352-creating-high-retention-highlights-editing-techniques-for-stream-recaps/ | StreamHub | indeterminado | baixa | prática
- Anúncio de serviço de clipping (anedota): melhores cortes têm reação forte, opinião forte ou são "compreensíveis sem o contexto da live" (snippet) | https://whop.com/clip-service-50 | Whop | indeterminado | baixa | prática
- Streams Charts: economia de redes de clipping pagas (N3on: US$ 1,4 mi em 5 semanas; pagamento por milhão de views ou bounty); reação emocional, confronto e polêmica são os cortes mais valiosos; plataformas podem remover cortes/contas sem aviso; sem CPM nem retenção | https://streamscharts.com/news/manufactured-virality-how-paid-clipping-networks-became-streamer-marketings-hidden-engine | Streams Charts | 2026-05 | alta | número/prática

**Plataformas**
- YouTube Studio mostra "Viewed vs. Swiped away" por Short (Analytics → Conteúdo → Shorts); guias divergem sobre o peso no ranking (snippet) | https://support.google.com/youtube/answer/12220281 | Google | indeterminado | média | plataforma
- Desde 2025-03-31 a view pública de Short conta a cada início/replay; monetização YPP segue em "engaged views" (snippet) | https://techcrunch.com/2025/03/26/youtube-is-changing-how-youtube-shorts-views-are-counted | TechCrunch | 2025-03 | alta | plataforma
- 2025-07-15: "repetitious content" virou "inauthentic content" (conteúdo em massa/repetitivo); "reused content" inalterada — avalia clipes/compilações por comentário, modificação ou valor original; vale mesmo com permissão do autor, independe de copyright, pode desmonetizar o canal inteiro (snippet) | https://support.google.com/youtube/answer/1311392 | Google/SEJ | 2025-07 | média | plataforma
- YouTube passa a favorecer Shorts originais e reduzir alcance de canais que repostam clipes de terceiros sem mudança significativa; Rene Ritchie: "minor technical edits" e "template-based bulk changes" não bastam; alcance reavaliado quando o canal muda; sem data de início nem sinal de que o canal foi afetado | https://www.searchenginejournal.com/youtube-original-shorts-reposted-clips-reach/591774/ | Search Engine Journal | 2026-10 | alta | plataforma

## Pistas
- Prompts do AutoClip (`highlight_v1.txt`) e do OpenShorts: índices de palavras × segundos.
- `active_speaker.py` do OpenShorts (falante ativo por áudio+vídeo?).
- Issue #168 do OpenShorts (facecam 9:16).
- Papers RankCut (IUI '26) e Video Trimming (2412.09513).
- Repo certo do CTIC (404) e twitch-highlight-detection (MINT).
- Inferência não verificada: "template-based bulk changes" provavelmente não contam como transformação → reforçar Score de Transformação (P2) com variação real por corte.
- Página oficial do TikTok Creator Rewards (regra dos 60s).

## Não achei
- Retenção (não views) por duração para Shorts/TikTok/Reels, inclusive 1–3 min.
- Retrospectivas com números de donos de canais de cortes, sobretudo BR (só vendor).
- Efeito medido de loop, jump cuts, legendas animadas ou nº de cortes por live na retenção.
- API oficial do Most Replayed.
- Técnica explícita em ferramenta open-source para o corte se sustentar sozinho (mais próximo: abertura/fechamento do HIVE).
- Reclamações de qualidade de seleção nas issues.
- Duração ideal para Reels/Facebook em 2026.
