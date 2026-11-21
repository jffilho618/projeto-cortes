# Auditoria E3 / E3.5 — "done no papel" × "ligado no pipeline" (2026-11-20)

Etapa 1 do plano de qualidade do motor (Épico 5 pausado). Método: para cada critério de aceite (AC) do `epics.md`, rastrear quem chama o módulo **fora dos testes** e conferir os artefatos dos projetos reais em `projects/` (`candidates.json`, `segments.json`, `project.json`).

## O que roda de verdade

- Modo Gemini (o usado pelo dono): 10 arquétipos + 3 tiers aparecem nos cortes reais com variedade (ex.: `2501be513575` → 7 arquétipos em 15 cortes). 5 pistas (`multitrack`), Full-VOD Scout (`llm_scout`), Editor-Chefe v2, `golden_examples.json`, dossiê `gta6.json`, MMR.
- Heatmap/capítulos do YouTube, `temporal_nms`, HUD sem `PERSON`, dêiticos visuais (3.5.1).
- Snap de bordas, selo de título, thumbnail com `rembg` opcional (3.2/3.4/3.5).
- Atenção: no modo `heuristic` (padrão do projeto e 1ª opção do painel) **nada do E3.5 roda**.

## Achados e situação

| # | História | Achado | Situação |
|---|---|---|---|
| A1 | 3.2 | **Visão de games (MAR, HUD, facecam) nunca rodou em VOD longo.** O proxy visual pedia `worst[height<=360]/worst`, formato combinado que o YouTube atual não oferece → "Requested format is not available" → descoberta só com áudio+texto (`evidence_available.visual=false` em todos os projetos reais). | ✅ Corrigido (seletor `worstvideo…`), validado com download real de 20s (601 frames 426×240 lidos pelo OpenCV) |
| A2 | 3.1 | **Sismógrafo do Chat nunca rodou em projeto real**: ninguém baixava o chat (`chat_seismic.json` = 0 projetos). | ✅ **Validado com dado real** no replay de live do YouTube `x50ONQrBPRM` (Gameplayrj, 11h20, indicado pelo dono): 45s de download = 8.074 mensagens / 38 min de live, Sismógrafo achou 2 picos. Limite de tempo proporcional à duração (`chat_timeout_for`, 22 min p/ 11h20); se estourar, **aproveita o chat parcial** (testado real: 5.775 mensagens em 30s, saúde "parcial"); leitura linha a linha (bruto de 11h ≈ 300 MB; `chat.json` final ≈ 300 KB por 25 min). Histórico: antes não validado (VODs do dono são uploads comuns sem chat; nos replays testados o `yt-dlp` não expôs `live_chat` sem o solver JS remoto `ejs:github`). Explicação do dono: as fontes vêm da aba **"Vídeos"** dos canais (trechos de live recortados e reenviados pelos próprios streamers, porque as lives inteiras são gigantes) — uploads comuns nunca têm chat. Os 2 replays testados da aba "Ao vivo" (`was_live`) também vieram sem chat, mesmo com o solver JS. O chat da **Twitch** entra junto com o monitor de lives ao vivo do **Épico 5** (decisão do dono em 2026-11-20: até agora só fontes do YouTube). Opção pendente para o YouTube: instalar `yt-dlp[default]` (`yt-dlp-ejs` 0.8.0, solver JS oficial empacotado, sem download remoto a cada execução) + `--js-runtimes node`. |
| A3 | 3.5.4 | `prosody_events` (riso 3–6 Hz, susto >18 dB, ritmo de fala) sem nenhum chamador. | ✅ Ligado na descoberta (top 40 candidatos, bônus modesto) |
| A4 | 3.5.3 | **Editor-Chefe via só texto**: nenhum sinal não verbal chegava ao LLM; e `visual_games` herdava a nota geral quando a visão não media (falsa medição). | ✅ Campo `sinais` (riso, susto, fala, chat, facecam, HUD) **só com o que foi medido** (`vision_measured`/`chat_measured`) |
| A5 | 3.5.4 | `comments_miner` sem chamador. | ✅ Ligado (só YouTube, respeita P1). Validação real: 39 momentos marcados pelo público em ~9s no VOD `yWvnOWILFk0`; o comentário chega ao LLM como `comentario_publico` e o texto do candidato é a fala real do trecho |
| A6 | 3.5.4 | `multimodal_keyframes` (LLM vê 3 frames) sem chamador. | ✅ Ligado como **opção desligada por padrão** (`keyframes`, painel e `--keyframes`): Claude Sonnet, só candidatos com dêitico/arquétipo visual/nota limítrofe, **uma chamada por VOD**, descrição chega ao Editor-Chefe como `visao`; falha não derruba a seleção (vai para a saúde). Medição real (proxy do VOD `chge7GrCNc0`, 3 candidatos/9 frames): **~US$ 0,26 de limite por VOD**, descrições conferidas frame a frame. — Histórico: testado com `claude -p` (assinatura, sem API key): **lê imagens** via `--allowedTools Read --add-dir`. Custo reportado (limite da assinatura) por candidato: Opus ~US$ 0,45 · **Sonnet ~US$ 0,27, descrição fiel** · Haiku ~US$ 0,04 mas **alucinou** ("cai de bunda no chão" em frames só com texto) → descartado. Gemini sem cota em 2026-11-20: testar o mesmo fluxo quando a cota voltar. |
| A7 | 3.5.4 | `activity_segmenter` sem chamador. | ⏸ Para o brainstorming |
| A8 | 3.3 | Troca dinâmica de layout e Sniper Crop (`reframe_games`) sem chamador; layout games é estático. | ⏸ Frente de formato (após brainstorming) |
| A9 | 3.4 | Cold Open Reverso e Seamless Loop só planejados, nunca renderizados (`find_seamless_loop_end` sem chamador). | ⏸ Frente de formato |
| A10 | 3.4 | Compilação cross-streamer: `cross_streamer.py` não existe; `build_cross_streamer_sync_plan` sem chamador. | ⏸ Depende do Épico 5 |
| A11 | 3.5 | Par Short Isca ↔ Corte Longo quase nunca se forma (projeto tem 1 formato só) e `pair_short_and_long_clips` liga Short a **qualquer** longo mesmo sem sobreposição (`best_overlap > 0.0 or longs`). | ⏸ Frente de formato (bug a corrigir) |
| A12 | 3.5.5 | Arcos de 2 atos e compilação por arquétipo só geram `.json` (e só em `hunt_mode=deep`); ninguém renderiza. | ⏸ Frente de formato |

## Cobertura de arquétipos

Os 16 arquétipos do brainstorming foram agrupados em 10 canônicos. **Não existe arquétipo para nobada/vacilo** (erro bobo, se perder, cair do mapa, chat "noob"/"skill issue"/"KKKK", autodepreciação). O mais próximo, `clutch_fail`, procura lance épico (killfeed, `POG`/`CLUTCH`). Entrada para a etapa 2 (pesquisa + `bmad-brainstorming`).

## Também entraram na etapa 1b

- **Decisão B do dono — Editor-Chefe nunca falha em silêncio:** 1 nova tentativa por lote; se ainda falhar (cota, timeout, resposta vazia, lote parcial, filtro ou companion do modo Dupla), a seleção **para** com `EditorChiefUnavailable` e mensagem explicando o que ficou salvo e como seguir (trocar o Motor de IA ou escolher "sem IA" de propósito). Antes caía para o modo determinístico e o projeto terminava "concluído".
- **Registro de saúde do motor (dados para o painel do E6, W9):** `<projeto>/engine_health.json` com `ok`/`na`/`failed` + motivo para proxy visual, visão, prosódia, chat, comentários, heatmap, Full-VOD Scout, Editor-Chefe, keyframes e thumbnail (`picorte/engine/health.py`).
- **yt-dlp:** instalado só o `yt-dlp-ejs` 0.8.0; `ytdlp_base_cmd()` adiciona `--js-runtimes node` quando o node existe (sem node, sem flag — AD-11). Medido: 0 avisos e 47 formatos (antes 1 aviso e 44), +~1s por chamada.

## Verificação

Suíte completa: **592 testes passando** ao fim da etapa 1b (arquivos espelho raiz ↔ `picorte/engine/` sincronizados). Novos testes: `tests/test_e3_wiring_chat.py`, `test_e3_wiring_visual_proxy.py`, `test_e3_wiring_prosody.py`, `test_e3_wiring_comments.py`, `test_e3_wiring_ytdlp_runtime.py`, `test_e3_editor_chief_failure.py`, `test_e3_engine_health.py`, `test_e3_wiring_keyframes.py`.
