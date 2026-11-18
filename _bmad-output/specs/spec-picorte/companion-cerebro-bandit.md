# Companion 4 — O Cérebro que Aprende: Bandit Contextual com Esquecimento, Campanhas Pagas, Reciclagem A/B e Active Learning

> Parte integrante do contrato `SPEC-picorte` (`CAP-17`, `CAP-18`). Define a matemática de decisão dos pilares **P3 (Os dados de agora decidem)** e **P4 (A inteligência de seleção é nossa)**.

---

## 1. Coleta de Snapshots e Fórmula de Recompensa Anti-Clickbait (`CAP-18`)

Para cada corte publicado em qualquer uma das 5 redes, o coletor (`metrics_collector.py`) grava 3 snapshots na tabela `metrics_snapshots`: **`1h`**, **`24h`** e **`7d`** após a publicação.

### 1.1. Métricas Coletadas
- `views`: total de visualizações até o momento do snapshot;
- `likes`, `comments`, `shares`: engajamento absoluto;
- `avg_view_percentage` ($R_{\text{media}}$): retenção percentual média do corte (quando fornecida pela API da rede, ex.: YouTube Analytics / TikTok);
- `stayed_to_watch_pct` ($R_{3\text{s}}$): percentual de espectadores que **não** deslizaram nos primeiros 3 segundos (*viewed vs swiped away*).

### 1.2. Fórmula da Recompensa ($Y$) — Views sem Premiar Clickbait
Para cumprir a decisão do dono (*"perseguir visualizações sem premiar clickbait"*), a recompensa bruta de uma publicação na janela $w \in \{24\text{h}, 7\text{d}\}$ é normalizada pela mediana recente (últimos 14 dias) daquela mesma rede e formato no nosso canal, e multiplicada por um fator de qualidade de retenção $Q_{\text{ret}}$ e pelo multiplicador financeiro de campanha $M_{\text{camp}}$:

$$Y = \left( \frac{\text{views}}{\max(\text{mediana\_views}_{14\text{d}}, 100)} \right) \times Q_{\text{ret}} \times M_{\text{camp}}$$

Onde:
- **Penalidade Anti-Clickbait ($Q_{\text{ret}}$):**
  - Se a retenção média $R_{\text{media}}$ estiver disponível: $Q_{\text{ret}} = \text{clamp}\left(\frac{R_{\text{media}}}{0.65},\ 0.2,\ 1.5\right)$. Assim, um corte com clickbait onde as pessoas entram e saem logo ($R_{\text{media}} = 20\%$) sofre penalidade severa ($Q_{\text{ret}} \approx 0.30$), enquanto um corte que segura o público até o fim ($R_{\text{media}} \ge 85\%$) ganha bônus ($Q_{\text{ret}} \approx 1.30$).
  - Se a rede não informar retenção no snapshot inicial, usa a razão `(likes + 3 * comments + 5 * shares) / views` comparada à mediana do canal como proxy de satisfação.
- **Multiplicador de Campanha Paga ($M_{\text{camp}}$):**
  - `1.0` para cortes normais (monetização orgânica / YPP);
  - `1.0 + (cpm_reais / cpm_base_canal)` quando o corte pertence a uma **Campanha Paga de Clipping ativa** (`campaigns`), fazendo o Bandit priorizar automaticamente fontes que pagam dinheiro direto por 1.000 views enquanto a campanha durar.

---

## 2. Bandit Contextual / Hierárquico com Esquecimento do Passado (`CAP-18`)

### 2.1. Separação do Efeito das Variáveis (Generalização Rápida)
Em vez de tratar cada combinação inteira como um braço isolado (o que impediria o sistema de perceber que *"GTA 6 está dando view independente do streamer"*), o modelo usa um **Linear/Generalized Contextual Thompson Sampling com pesos aditivos por fator**:

$$\hat{Y}(x) = \theta_0 + \theta_{\text{jogo}(x)} + \theta_{\text{streamer}(x)} + \theta_{\text{tipo\_momento}(x)} + \theta_{\text{formato}(x)} + \theta_{\text{duracao}(x)} + \theta_{\text{rede}(x)} + \theta_{\text{horario}(x)} + \beta \cdot S_{\text{radar}}(x)$$

Onde cada parâmetro $\theta_k \sim \mathcal{N}(\mu_k, \sigma_k^2)$ mantém sua média $\mu_k$ e incerteza $\sigma_k^2$ na tabela `bandit_state`:
- Se 4 cortes de `jogo = GTA_6` com o Streamer A explodem de views, $\mu_{\text{jogo}=\text{GTA\_6}}$ sobe imediatamente. Quando aparece um VOD de `GTA_6` do Streamer B (ainda não testado em GTA 6), ele já herda o $\mu_{\text{jogo}=\text{GTA\_6}}$ alto!

### 2.2. Esquecimento do Passado (Reação Rápida à Mudança de Interesse — P3)
A cada ciclo diário de atualização (ou a cada novo lote de snapshots), todas as precisões acumuladas sofrem **decaimento exponencial pelo fator de esquecimento $\gamma \in [0.85, 0.92]$ por dia**:
- A variância efetiva dos pesos antigos aumenta ($\sigma_k^2 \leftarrow \sigma_k^2 / \gamma$) e as observações com mais de 14–21 dias perdem peso exponencialmente.
- **Efeito prático:** se um jogo ou streamer que foi campeão no mês passado esfriar esta semana, em 3 a 5 dias de resultados fracos o peso dele cai e o sistema migra a cota de publicação para o novo pico apontado pelo Radar ($S_{\text{radar}}$) e pelos testes recentes.
- **Orçamento de Exploração (~20%):** pelo menos 1 em cada 5 vagas da fila diária é reservada para candidatos de alta incerteza ($\sigma_k$ alto) ou picos recém-detectados no Radar da Twitch/YouTube.

---

## 3. Reciclagem A/B de Gancho — "Segunda Vida" (`CAP-18`)

O serviço `ab_recycler.py` analisa os snapshots de `24h` e detecta o padrão **"Ouro Escondido Atrás de um Gancho Fraco"**:
- **Condição de disparo:**
  - Retenção do corpo do vídeo (após os primeiros 5 segundos) no quartil superior do canal ($R_{\text{pos5s}} \ge 70\%$ ou taxa de likes/comentários por espectador retido muito alta); **MAS**
  - Taxa de abandono nos primeiros 3 segundos ruim ($R_{3\text{s}} < 55\%$ ou views abaixo da mediana).
- **Ação automática:**
  - O sistema cria um job de **Segunda Vida (`ab_variant = 2`)** para aquele mesmo corte:
    1. Escolhe um **novo Cold Open de 1,5s** (o segundo maior pico visual/sonoro do corte);
    2. Gera uma **nova Faixa de Contexto de 2s** e um **novo Título** com ângulo diferente via LLM;
    3. Agenda a versão reciclada para outra rede (ex.: se flopou no Shorts, testa no TikTok/Reels) ou para republicação após janela mínima de 14 dias.

---

## 4. Autocaptura de Dataset Rotulado e Treino na RTX 4060 Ti (`CAP-18`)

Para cumprir o **P4 (A inteligência de seleção é nossa)** e aproveitar a especialidade do dono em Visão Computacional e Machine Learning:

1. **Coleta Passiva Automática (`active_learning.py`):**
   - Sempre que um corte completa o ciclo de `24h`/`7d` nos extremos da distribuição:
     - **Classe Positiva (`y = 1`):** recompensa $Y \ge 2.5\times$ a mediana recente do canal;
     - **Classe Negativa (`y = 0`):** recompensa $Y \le 0.35\times$ a mediana recente do canal;
   - O sistema exporta automaticamente para `dataset_rotulado/<clip_id>/`:
     - `features.npz`: séries temporais de 1 Hz de áudio (`evidence.py`), 2 fps de visão (`visual_games.py`: MAR da facecam, movimento, eventos de HUD), curva do Sismógrafo do Chat e embeddings do texto;
     - `keyframes/`: 5 frames representativos do corte + o frame do Cold Open + a Thumbnail gerada;
     - `label.json`: métricas reais de `1h`, `24h`, `7d` (`views`, $R_{3\text{s}}$, $R_{\text{media}}$, recompensa $Y$).
2. **Treinamento Local (`train_local_scorer.py`):**
   - Quando `dataset_rotulado/` acumula $\ge 200$ exemplos (e depois a cada novo lote no **Modo Madrugada da RTX 4060 Ti**), treina um modelo local leve (Gradient Boosting / MLP / cabeça temporal sobre os vetores multimodais) que substitui os pesos fixos iniciais ($w_{\text{chat}}, w_{\text{audio}}, w_{\text{visao}}, w_{\text{texto}}$) do `score_clips.py` pelos pesos aprendidos diretamente no gosto real do público dos nossos canais.
