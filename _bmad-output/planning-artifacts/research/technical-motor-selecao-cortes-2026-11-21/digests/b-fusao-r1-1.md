# Digest — (b) fusão de sinais e medição — rodada 1, assistente 1

Acesso: 2026-11-21. PDFs ACL/NeurIPS não abriram como texto; números das versões HTML (ar5iv/arXiv).

## Achados

**1. Como combinam**
- Fu et al. (EMNLP 2017): fusão intermediária — features de vídeo (CNN-LSTM) + chat (LSTM por caractere) → MLP 2 camadas; pesos aprendidos | https://ar5iv.labs.arxiv.org/html/1707.08559 | ACL/EMNLP | 2017-07 | alta | método
- KuaiHL (Kuaishou): Perceiver com queries latentes sobre visual + ASR + comentários + ID do streamer; decoder causal dá nota por trecho; módulo com perda contrastiva DTW corrige defasagem entre modalidades | https://arxiv.org/html/2407.12002v1 | arXiv | 2024-06 | alta | método
- KuaiHL: perda por item (logloss) + perda de ranking por pares → +2,00% Kendall τ (0,5961 vs 0,5761) no KLive | idem | arXiv | 2024-06 | alta | número
- KuaiHL ablação: sem visual τ −4,72% (0,5489); sem texto (ASR+comentários) −2,01%; sem ID do streamer −0,51% | idem | arXiv | 2024-06 | alta | número
- Fu et al.: vídeo sozinho bate chat sozinho em LoL; fusão ganha pouco. F1 NALCS: chat 43,2 / vídeo 72,2 / ambos 74,7; LMS: 39,7 / 69,2 / 70,0 | https://ar5iv.labs.arxiv.org/html/1707.08559 | ACL/EMNLP | 2017-07 | alta | número
- HiVid (2026): LLM-juiz em 2 etapas — nota 0–100 por trecho em janelas de 10 quadros com resumo do vídeo carregado entre janelas; depois merge sort guiado pelo LLM comparando listas para corrigir diferença de escala entre janelas; suavização gaussiana σ=5 | https://arxiv.org/html/2602.14214v1 | arXiv | 2026-02 | alta | método
- HiVid com GPT-4o no Mr.HiSum: PLCC 0,66, SRCC 0,67, mAP50 0,86; até +11,5% PLCC sobre melhor baseline; ~US$ 1,35 por vídeo de 201 s | idem | arXiv | 2026-02 | média (fonte única) | número
- Rerankers listwise com LLM mudam conforme a ordem dos candidatos no prompt; embaralhar dados de fine-tuning não resolve; propõem calibração IPS e aumento de dados ciente de posição | https://www.alphaxiv.org/abs/2604.03642 | alphaXiv/arXiv | 2026-04 | média (só resumo) | método
- Em resumo de vídeo, qualidade varia com a posição do vídeo no prompt mesmo com conteúdo igual | https://arxiv.org/html/2606.04596 | arXiv | 2026-06 | baixa (snippet) | método
- Abordagem dominante: highlight como ranking por pares de trechos do mesmo vídeo | https://openaccess.thecvf.com/content_cvpr_2016/papers/Yao_Highlight_Detection_With_CVPR_2016_paper.pdf | CVPR | 2016-06 | média (snippet) | método

**2. Sinais que predizem / enganam**
- Pico do chat ~20 s depois do momento; deslocamento aprendido estável 23–27 s (Dota 2 e LoL) | https://ar5iv.labs.arxiv.org/html/1910.12201 | arXiv (Lightor, SFU/Microsoft) | 2019-10 | alta | número
- Fu et al.: melhor resultado com chat dos 7 s seguintes ao trecho (setup diferente do Lightor) | https://ar5iv.labs.arxiv.org/html/1707.08559 | ACL/EMNLP | 2017-07 | média | número
- Lightor: 3 features de chat em janela de 25 s — nº de mensagens, tamanho médio (mensagens curtas/emotes indicam highlight), semelhança entre mensagens (todos falando da mesma coisa) | Lightor | 2019-10 | alta | sinal
- Contagem sozinha funciona para k≤3 e piora em k=10; as 3 juntas melhores acima de k=5 | Lightor | 2019-10 | alta | sinal
- Enganam (Lightor): bots de propaganda com rajadas de mensagens; conversa paralela fora do assunto → derrubam precisão em k maior | Lightor | 2019-10 | alta | sinal
- Precision@10 do chat sozinho: 0,82 com 1 vídeo de treino, 50 de teste; sistema completo Dota 2: P@5 0,906 no início do trecho, 0,719 no fim (abstract: 70–90%) | Lightor | 2019-10 | alta | número
- Riso sozinho não é highlight pronto; detector aberto jrgillick/laughter-detection (Switchboard, avaliado no AudioSet); FunnyNet-W: engraçado = trecho seguido de riso; fusão áudio+visual+texto ajuda | https://www.github.com/jrgillick/laughter-detection ; https://arxiv.org/html/2401.04210v1 | GitHub/arXiv | 2024-01 | média (snippets) | sinal
- Avaliações de detecção de riso tendem a superestimar eficácia em cenários difíceis | https://theses.gla.ac.uk/84936/2/2024RenniePhD.pdf | Univ. Glasgow | 2024 | baixa (snippet) | medição
- "Most Replayed" é ruidoso: YTMR500 (500 vlogs), modelos P@15/30/50 ≈ 21–22% / 37–38% / 56–57% vs aleatório 15/30/50%; humanos não significativamente melhores que o acaso; fala e volume podem explicar parte dos picos | https://ar5iv.labs.arxiv.org/html/2309.06102 | arXiv (TU Delft) | 2023-09 | alta | número
- Heatmap "mais repetidos" só aparece com volume alto de views (dezenas de milhares) | YTMR500 ; https://www.macrumors.com/2022/05/19/youtube-rolls-out-most-replayed-feature/ | arXiv/MacRumors | 2023-09/2022-05 | média | sinal

**3. Rótulos fracos e datasets**
- Lightor dataset: 60 VODs Dota 2 rotulados por jogadores + 173 LoL rotulados por casamento com compilações de canal de highlights; github.com/sfu-db/Lightor_Exp | Lightor | 2019-10 | alta | dataset
- Fu et al.: 321 partidas LoL (NALCS/LMS), rótulos da comunidade (canal Onivia) alinhados por template matching; liberação não confirmada | ACL | 2017-07 | média | dataset
- Mr.HiSum: 31.892 vídeos YouTube-8M; rótulo = Most Replayed normalizado 0–1, agregado de >50 mil usuários/vídeo; CC BY 4.0 + ToS do YouTube | https://github.com/MRHiSum/MR.HiSum | GitHub/NeurIPS D&B | 2023 | alta | dataset
- KuaiHL: rótulo puramente comportamental — fração de impressões com tempo assistido acima de um limite (Long View Through Rate); 17.897 lives (19.334 h) | KuaiHL | 2024-06 | alta | medição
- Clipes da Twitch como rótulo fraco via API Get Clips: `vod_offset`, `view_count`, `duration`, `created_at`, `is_featured`; `vod_offset` nulo enquanto o VOD não existe (minutos); ~1.000 resultados por consulta, fatiar com `started_at`/`ended_at` | https://dev.twitch.tv/docs/api/reference/clips#get-clips | Twitch Developers | 2026-11 | alta | medição
- Duração do vídeo como supervisão implícita: trechos de vídeos curtos de usuários tendem a ser highlights | https://arxiv.org/pdf/1903.00859v1.pdf | arXiv (Xiong et al.) | 2019-03 | média (snippet) | método
- Ranking latente por pares de vídeos editados vs bruto (análogo: cortes publicados vs VOD) | https://projet.liris.cnrs.fr/imagine/pub/proceedings/ECCV-2014/papers/8689/86890787.pdf | ECCV | 2014 | média (snippet) | método
- KuaiHL afirma não existir dataset público grande de highlight de live | KuaiHL | 2024-06 | média | dataset
- COHETS (Hugging Face): Twitch, 65 vídeos, ~152 h com chat; card incompleto, diz dataset vazio | https://huggingface.co/datasets/samjaylin/COHETS | HF | ? | baixa | dataset

**4. Métricas**
- Lightor: Precision@K separada em início e fim do trecho | Lightor | 2019-10 | alta | medição
- YTMR500 prefere P@K a Kendall τ (peso à ordem do topo); sempre comparar com aleatório (K/N) | YTMR500 | 2023-09 | alta | medição
- KuaiHL: Kendall τ com limiares Δ e mAP (PHD); HiVid: PLCC, SRCC, mAP50, mAP15; nenhum NDCG | KuaiHL/HiVid | 2024-06/2026-02 | alta | medição
- Fu et al.: P/R/F1 por quadro | ACL | 2017-07 | alta | medição

## Recomendações do assistente (inferências)
- Atraso do chat: deslocar pico 20–27 s para trás (fonte única, 2 jogos; aprendível) — média.
- Trocar pesos a olho por pesos aprendidos com ranking por pares (Fu, KuaiHL) — média; não há base nossa ainda.
- LLM reordenando: ordem dos candidatos é viés → embaralhar e rodar várias vezes ou comparar por pares — média.

## Pistas
- github.com/sfu-db/Lightor_Exp para calibrar atraso e features de chat.
- Tese de Leeds/York (etheses.whiterose.ac.uk/32406), dataset "TwitchChat".
- AntPivot; PHD dataset (81 mil vídeos).
- Hipótese não validada: clipes da Twitch mais vistos do mesmo VOD vs seletor, com Precision@K — rótulo grátis via API oficial.
- FunnyNet-W (2401.04210); debias listwise IPS (2604.03642); Twitch "Recaps" (Tubefilter 2026-09).

## Não achei
- Paper validando clipes da Twitch criados por espectadores como rótulo, com números.
- Evidência de que emotes específicos predizem melhor que contagem bruta.
- Chat de sorteio como falso positivo (só bots e conversa paralela).
- LLM-juiz para highlights de live de games com números (post Eluvio 403).
- Desempenho de cortes publicados como rótulo (fora KuaiHL interno).
- Fusão precoce vs tardia no mesmo dataset de games.
- Correlação Most Replayed × highlights de games, ou viés de pico no início.
- NDCG em highlight de live.
