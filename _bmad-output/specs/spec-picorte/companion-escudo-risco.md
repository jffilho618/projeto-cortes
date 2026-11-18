# Companion 2 — Escudo Anti-Strike, Direitos Autorais e Monetização (P1)

> Parte integrante do contrato `SPEC-picorte` (`CAP-10`, `CAP-11`, `CAP-12`, `CAP-13`, `CAP-16`). Define os portões automáticos obrigatórios do pilar **P1 (Canal protegido antes de alcance)**.

---

## 1. Máquina de Estados da Fonte (`CAP-10`)

Toda fonte cadastrada na tabela `sources` do PostgreSQL possui um estado de permissão obrigatório:

| Status da Fonte | Pode baixar / processar? | Pode publicar? | Regra de Transição |
|---|---|---|---|
| **`desconhecida`** *(padrão inicial)* | **NÃO (Bloqueado)** | **NÃO (Bloqueado)** | Se aparecer em alta no Radar, gera alerta ao operador informando a audiência atual e o que falta para liberá-la. |
| **`gameplay_proprio`** | **SIM** | **SIM** | Nasce autorizado quando a origem é gravação local do próprio operador. |
| **`liberada`** | **SIM** | **SIM** | Streamer/canal com política pública ou autorização explícita para canais de cortes (exige link/evidência da permissão no cadastro). |
| **`contrato`** | **SIM** | **SIM** | Parceria direta com o criador; respeita eventual data de vigência. |
| **`campanha_ativa`** | **SIM (enquanto vigente)** | **SIM (enquanto vigente)** | Vinculada a um registro em `campaigns` com `expires_at`. Quando `now() > expires_at`, o status cai automaticamente para `expirada` e trava novos envios. |
| **`pausada_por_claim`** | **NÃO** | **NÃO** | Acionado automaticamente pelo Disjuntor Global (`CAP-16`) ao primeiro claim de bloqueio ou strike em qualquer rede. Só sai deste estado por ação manual explícita do operador após análise. |
| **`lista_negra`** | **NÃO (Permanente)** | **NÃO (Permanente)** | Criador ou detentor que proíbe cortes ou aplica strikes. Bloqueio definitivo. |

---

## 2. Registro de Políticas por Publisher / Jogo (`CAP-10`)

A tabela `publisher_policies` armazena as restrições específicas de cada jogo/publisher:

| Campo | Descrição e Aplicação no Portão |
|---|---|
| `publisher` / `game_slug` | Ex.: `Rockstar Games` / `gta-6`, `Nintendo`, `Riot Games`. |
| `spoiler_window_days` | Dias após o lançamento (`release_date`) em que cenas de final, chefes finais ou reviravoltas da história principal são bloqueadas ou exigem tag de spoiler. |
| `forbidden_content_rules` | Lista de padrões bloqueados (ex.: para GTA 6: compilações puras de cutscenes sem gameplay/comentário, final da campanha, material de vazamento/leak pré-lançamento). |
| `has_licensed_radio_music` | Booleano (`true` em jogos como GTA, Fortnite com emotes licenciados, FIFA). Quando `true`, ativa obrigatoriamente o scanner acústico e a Cirurgia Seletiva de Música com `Demucs` (`CAP-11`). |
| `violence_check_strict` | Quando `true`, força limiar rigoroso no detector visual dos primeiros 15 segundos (`CAP-12`). |

---

## 3. Cirurgia Seletiva de Música com `Demucs` (`CAP-11`)

1. **Detecção de Música de Fundo:**
   - Analisa a faixa de áudio do corte em janelas de 2s verificando harmônicos musicais contínuos sob a voz (ou jogos marcados com `has_licensed_radio_music = true`).
2. **Separação Neural Local (Sem Truques de Pitch/Speed — A2):**
   - Nos intervalos `[t_ini, t_fim]` onde música é detectada (com crossfade suave de 150 ms nas bordas), o worker executa o modelo `htdemucs` na GPU (em estágio isolado da VRAM), extrai o stem `vocals` (voz limpa do streamer) e substitui apenas aquele trecho do áudio, zerando a música licenciada sem perder a reação falada.
   - Se um trecho musical não tiver fala relevante do streamer e for essencialmente música protegida, o candidato é descartado.

---

## 4. Filtro "Selo Verde 15s" e Detector de "React Perigoso" (`CAP-12`)

### 4.1. Selo Verde nos Primeiros 15 Segundos (Proteção de Monetização / Ad-Friendly)
- **Camada de Áudio e Legenda:**
  - Inspeciona os timestamps das palavras transcritas entre `0.0s` e `15.0s` (incluindo o Cold Open).
  - Palavras presentes no dicionário de profanidade severa / desmonetização recebem um **micro-bleep ou atenuação de `-40 dB` durante exatos `150–250 ms`** sobre a palavra e são grafadas com `***` no arquivo `.ass` de legenda queimada.
- **Camada de Visão Computacional:**
  - Avalia os frames de `0.0s` a `15.0s` contra padrões de sangue excessivo/gore explícito em close-up. Se detectar violação na abertura, o motor tenta escolher outro Cold Open limpo; se persistir nos primeiros 15s, aplica desfoque localizado ou reprova o candidato.

### 4.2. Detector Visual de "React Perigoso" (`react_guard.py`)
- Streamers frequentemente saem do jogo e abrem vídeos de terceiros no YouTube, TikTok, Instagram ou TV ao vivo. Cortar um "react de vídeo protegido" gera strike direto do dono do vídeo original.
- O detector visual verifica na área principal da tela:
  1. Presença de barras de endereço de navegador, players de vídeo (barra de progresso vermelha do YouTube, logo do TikTok/Reels/Twitch de outro canal) ou ausência prolongada da interface/textura do jogo;
  2. Termos na transcrição como *"deixa eu ver esse vídeo"*, *"abre aí o canal do..."*.
- Qualquer trecho classificado como *React de Terceiro* é bloqueado automaticamente (ou exige revisão manual explícita com alerta vermelho).

---

## 5. Score de Transformação YPP e Deduplicação Perceptual (`CAP-13`)

Antes de um corte receber status `pronto_para_fila`, ele precisa passar por dois testes matemáticos:

1. **Score Mínimo de Transformação YPP (P2 — Mínimo `70/100`):**
   - `+25 pts`: Reenquadramento dinâmico / composição Facecam + Jogo ativa (não é frame 16:9 cru);
   - `+25 pts`: Legenda dinâmica `.ass` sincronizada palavra a palavra e posicionada na área segura;
   - `+20 pts`: Cold Open Reverso (1,5s) e/ou Faixa de Contexto Instantâneo (2s) aplicados;
   - `+15 pts`: Título específico próprio + 1º Comentário de Debate + Crédito à fonte gerados;
   - `+15 pts`: Compilação Cross-Streamer ou edição multi-segmento.
2. **Deduplicação Perceptual (`pHash` + Texto):**
   - Calcula uma assinatura composta por `8 hashes perceptuais (pHash)` amostrados ao longo do corte + `similaridade de cosseno / Jaccard` sobre a transcrição normalizada.
   - Se colidir (`similaridade > 0.85`) com qualquer corte já existente no PostgreSQL (evitando postar o mesmo lance vindo da live ao vivo, depois da VOD e depois de um Twitch Clip), o duplicado é descartado.

---

## 6. Disjuntor Global de Claims e Strikes (`CAP-16`)

1. O serviço `claim_breaker.py` consulta periodicamente o status dos vídeos publicados nas APIs conectadas (e recebe registro manual caso o operador reporte uma notificação por e-mail/painel).
2. Ao detectar **qualquer** bloqueio de Content ID, restrição de direitos autorais ou strike:
   - Executa em uma única transação no PostgreSQL:
     - `UPDATE sources SET permission_status = 'pausada_por_claim' WHERE id = :source_id`;
     - `UPDATE publications SET status = 'pausada_emergencia' WHERE clip_id IN (...) AND status IN ('agendada', 'fila')`;
   - Emite alerta prioritário no topo do painel "Estúdio do Criador" (cor de perigo do `DESIGN.md` + ícone + texto explicativo) e via MCP.
