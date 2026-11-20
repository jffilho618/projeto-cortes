# Deferred Work — Picorte

## Deferred from: code review of epics.md (2026-11-20)

- **W1 · Duplicação de arquivos espelho entre raiz e `picorte/engine/`** (`render_clips.py`, `projects.py`, `ingest.py`, `score_clips.py`, `chopify.py`) — pré-existente desde o Épico 1 (`AD-1`); mantidos sincronizados por SHA-256 até refatoração de empacotamento.
- **W2 · Escopo de cadência/Cool-Down por `social_account_id` (múltiplos canais por rede) e migração para tabela de banco** — `social_accounts` entra em uso real com OAuth no Épico 6; no Épico 4 o estado fica em arquivo runtime (`work/cadence_state.json`) protegido por `FileLock` + escrita atômica e evolui para `social_account_id` no Épico 6.

## Descobertos ao aplicar a Onda 1 do code review do Épico 4 (2026-11-20)

- **W3 · Cold Open Reverso não é renderizado no vídeo** — `build_cold_open_plan` (Épico 3, `3.4`) só gera o plano; nenhuma etapa do render monta o teaser no 0:00. O Selo Verde já entrega `cold_open_bleeps` + `cold_open_censored_words` na linha do tempo do teaser, prontos para quando o render existir. Enquanto isso, o veredito P1 usa `has_cold_open=False`.
- **W4 · ✅ Resolvido em 2026-11-20** — `clean_music_in_render` roda em todo corte final e o `demucs 4.1.0` foi instalado no Python global do PC de mesa (torch `2.6.0+cu124` intacto, RTX 4060 Ti). Validação real com voz sintetizada + acorde: música −33 a −44 dB, correlação com a voz 0,43 → 0,90, ~8s por 11s de áudio. Notas: áudio sai mono quando há cirurgia; trecho só de música (sem voz) cai em `human_review` ("quase mudo"), o que é intencional. No notebook Linux, instalar com `python -m pip install demucs` (opcional, como YOLO/HSEmotion).
- **W5 · Projetos preparados antes do D1 não têm `source_gate`** — o Pacote do Dia barra a exportação deles (`source_unlinked`). Basta rodar o `prepare` de novo para o portão registrar a fonte.
- **W6 · Falso positivo do detector de sangue em cenas dominadas por vermelho-escuro saturado** — a thumbnail falha fechada (sem thumb automática) nesses casos. Aceito por P1 > P3; revisitar com modelo próprio no Épico 7.
