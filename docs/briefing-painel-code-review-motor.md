# Briefing para a sessão do painel — impacto do code review do motor (2026-11-23)

**Para:** a sessão que cuida do painel "Estúdio do Criador" (Épico 6).
**Base de código:** branch `review/motor-fatia-a` (8 commits à frente do `main`, sem push). Trabalhe a partir dele ou depois do merge.
**Detalhe de cada mudança:** `_bmad-output/implementation-artifacts/deferred-work.md` (seções "code review do motor", W42–W63).

## 1. Já mudado no painel pelo review (confira e aceite ou ajuste)

| Arquivo | Mudança |
|---|---|
| `picorte/services/sinais.py` | facecam só de movimento (`evidence.facecam_measured == False`) não aparece como medida |
| `picorte/services/revisao.py` | "Energia do áudio" segue a parte `audio` da saúde (antes olhava `prosody`) |

Testes: `tests/test_cr_painel.py`.

## 2. Saúde do motor (`engine_health.json`) — partes novas e significados novos

| Parte | O que mudou | Impacto no painel |
|---|---|---|
| `audio` | **nova**: ok / na (sem mídia) / failed (áudio não medido) | rótulo legível na matriz e na revisão |
| `vision` | agora `failed` quando degradado ("MediaPipe indisponível", "rosto pequeno demais para medir emoção em N candidatos") ou quando a análise falha (com motivo) | **vai aparecer em vermelho** nos projetos com vídeo até a W49 (MAR); explicar ao operador que é degradação conhecida |
| `silencio_digital` | `failed` (não mais `na`) quando havia mídia mas o áudio não foi medido | — |
| `full_vod_scout` | `failed` quando o batedor cai (cota, timeout, JSON inválido) e "k de n blocos falharam" no Map-Reduce | antes aparecia como "nenhum achado" |
| `editor` | detalhe pode trazer "2ª passada falhou: …"; nova falha "lote parcial: k de n candidatos avaliados" (para a seleção — Decisão B) | mostrar o motivo na tela de falha |
| `llm_rerank` | **nova** (rota antiga `--llm`) | rótulo |
| `modo_deep` | **nova** (falha dos arcos/compilações do modo deep) | rótulo |
| `freeze`, `cold_open` | **novas** no render: ok / failed (ffmpeg) / na (desligado com motivo) | rótulo |

A matriz monta as colunas sozinha (`saude.matriz_motor`), mas aparecem com o nome cru: dar rótulos em português.

## 3. Evidência e sinais dos cortes (`segments.json`)

- Campos novos em `evidence`: `facecam_measured`, `hud_ocr_hits`, `archetype_hint_source` (`fala` / `comentario` / `chat`).
- `jumpscare_db` continua gravado, mas **não é mais "susto"**: vai ao Editor como `pico_sonoro_db` e **saiu dos sinais do ouro** (`sinais_independentes` não traz mais `susto`). Onde o painel diz "susto", trocar por "pico sonoro".
- O sinal "hud" só conta com texto lido pelo OCR; a "facecam" agora mede emoção no rosto recortado (hsemotion-onnx).
- **Menos cortes `ouro`**: a regra dos 2 sinais deixou de contar o mesmo fato duas vezes (nos projetos atuais: 8 → 5 de 38).

## 4. Selo Verde e P1

- Camada 2 (revisão humana) ganhou suicidio, se matar, nazismo, suicide, kill myself, nazi (saíram da Camada 3 por colidirem com jogos). **Mais cortes com `human_review`** na fila — a tela de revisão precisa deixar isso claro.
- Camada 3 (aborta): estupro, pedofilia, rape, pedophile, pedophilia, child porn.
- Comentários com horário: o P1 agora usa a lista de **permitidos** do `policy_gate` e é checado antes do cache.

## 5. Motor de IA

- **Sem fallback automático para API paga** (Anthropic/Gemini): sem o CLI de assinatura o Editor para com a mensagem da regra 6. Se o painel oferece/menciona API key ou modo pago, ajustar o texto.
- O modelo do Ollama (`llm`) não vai mais como `--model` para Claude/Gemini.

## 6. Render e formato

- Trechos de compostos saem com `sem_banner` (sem selo "PARTE 0"); o `.srt` agora acompanha freeze e Cold Open.
- Teaser do Cold Open que pegava o freeze passa a terminar no clímax (`cold_open.ajuste`).

## 7. Pendências do painel que o review encontrou

- **W36:** o `studio_service` precisa passar os ids da família (Short, TikTok e Longo do mesmo `moment_id`) ao `audit_clip_risk`, senão o 2º formato vira duplicata no pHash.
- **W32:** a saúde não é zerada entre execuções; avaliar mostrar só as partes da última execução.
- Dois pacotes de OpenCV instalados juntos (W52) — não desinstalar sem o dono.

## 8. Fontes

`assets/streamers/registry.json` ganhou RodrigoF ("El Gato") e Paulinho o Loko; entram como `liberada` (tolerância pública) no próximo `prepare`.
