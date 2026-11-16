# Visão do produto — projeto-cortes

**Data:** 2026-11-16 · **Consumidores:** PRD (E5), specs de domínio (E7–E9), arquitetura (E10). Os pilares (`pilares.md`) limitam esta visão; ela não os substitui.

## Nas palavras do dono

> "A ferramenta é como uma rede neural aprendendo, sempre perseguindo visualizações. Ela percebe sozinha o que está dando certo, em qualquer variável: um estilo de corte, um streamer, um jogo, um formato (curto ou longo), uma rede, um assunto. Exemplos: 'cortes de GTA 6 estão dando bom, independente do streamer'; 'agora o que dá view é o novo jogo do El Gato'; 'mudou, agora são cortes do Coringa jogando'; 'semana que vem tem mundial de Free Fire, então nessa data o assunto é Free Fire'."

## Leitura técnica (confirmada, com correções)

1. **Olho para fora — onde está a atenção agora.** Radar de tendências e calendário de eventos (lançamentos, campeonatos, atualizações). Correto: perceber o que está em alta **agora** não exige guardar o histórico de canais de terceiros. Mesmo assim:
   - **Usar o "em alta" que a própria fonte entrega**, sem calcular métricas a partir de dados de terceiros. Por exemplo: a lista de jogos mais assistidos da Twitch; os vídeos em alta na categoria Games pela YouTube Data API (`videos.list` com `chart=mostPopular`). Montar um ranking próprio comparando canais alheios esbarra nas regras III.E.2.a e III.E.4.h da API do YouTube.
   - Os dados de terceiros que forem guardados respeitam o limite de 30 dias (III.E.4.d).
   - **Ainda não verificado:** os termos da Twitch (o acordo de desenvolvedor não pôde ser lido nesta sessão), do Google Trends (API de acesso restrito) e das fontes de calendário (bases de lançamentos de jogos, de campeonatos de e-sports). Fica para a E7. O calendário também pode ser editorial: o operador cadastra eventos.
2. **Olho para dentro — o que funciona para nós.** Aprendizado com os resultados dos **nossos** cortes, por streamer, jogo, formato, duração, rede, assunto e horário. Correto. Duas correções para a E9:
   - **"Independente do streamer" exige um modelo que separe as variáveis.** Ele precisa aprender o efeito do jogo, o do streamer e o do formato separadamente, para generalizar "GTA 6 rende" para um streamer que ainda não testamos. Um bandit que trata cada combinação inteira como um braço só aprende combinações. Caminho provável: bandit contextual ou modelo hierárquico.
   - **"Mudou, agora é o Coringa" exige esquecer.** O gosto do público muda. O modelo precisa dar menos peso ao passado (janela deslizante ou desconto no Thompson sampling). O Thompson sampling simples da proposta original converge e demora a reagir à mudança.
3. **Testar, medir, apostar, abandonar.** Correto: é o ciclo de exploração e exploração do bandit. Limites reais para a E9:
   - O orçamento de teste disputa espaço com a cota de uploads (~6/dia por projeto GCP sem aumento de cota) e com o A2 (volume sem critério). Testar um assunto novo usa poucos cortes, não uma enxurrada.
   - A métrica perseguida é "visualizações", mas a E9 deve decidir se é a contagem bruta ou views ponderadas por retenção e receita por rede. Isso evita premiar clickbait que derruba a retenção, e o P2 continua valendo de qualquer forma.
4. **Freio (P1).** Correto, com um ajuste. Se algo está em alta mas a fonte não está liberada, o sistema **avisa e não publica**. Ele também **não baixa nem processa** essa fonte até o status mudar, porque baixar já pode ser o risco (decisão do yt-dlp, E8). O aviso deve dizer o que está em alta, a fonte e o que falta para liberá-la (por exemplo, pedir autorização ao streamer ou entrar numa campanha).

## Aderência aos pilares (modo Julgar, 2026-11-16)

| Pilar | Efeito | Motivo |
|---|---|---|
| P1 Canal protegido | reforça | "Se a fonte não está liberada, avisa e não publica" é o portão de status do P1. |
| P2 Obra própria e nativa | neutro | A visão fala do que cortar, não de como o corte sai. O risco é a recompensa "só views" premiar clickbait; o P2 continua valendo (ver item 3). |
| P3 Dados decidem | reforça | É o núcleo da visão: medição própria + sinais externos decidindo o que, onde e quando. |
| P4 Inteligência nossa | reforça | O aprendizado por variável fica nos nossos dados e no nosso modelo. |
| P5 Autônomo | reforça | "Percebe sozinha" é o caminho padrão; o aviso ao operador só aparece quando o P1 exige. |
| A2 Fábrica de spam | neutro | Fica neutro se o orçamento de teste respeitar o limite de volume (item 3). |
| A4 Contornar APIs | neutro | Fica neutro se o olho para fora usar só fontes oficiais. |

**Veredito: segue.** A visão cabe nos pilares. Um ponto para uma futura revisão do P3: ele não diz explicitamente que "o que funcionou ontem pode não funcionar hoje" (esquecimento). Hoje isso está implícito em "decide o que e quando". Se aparecer tensão no PRD, vale rodar o modo Revisar.
