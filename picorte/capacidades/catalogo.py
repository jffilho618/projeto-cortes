"""Catálogo estático das capacidades (mapa medido em 2026-11-21, brainstorm-intent.md).

O status daqui é o ponto de partida; `regras.py` sobrescreve as capacidades que dependem de sonda.
Ao ligar uma função, atualize a linha aqui (status, falta) e preencha `ligou_em`.
"""
from __future__ import annotations

from picorte.capacidades.modelo import Capacidade

MAPA_VERIFICADO_EM = "2026-11-21"


def _c(id_, area, titulo, status, tipo, falta, fonte, epico, historia, cap=None,
       escopo="global", depende=(), ligou_em=None) -> Capacidade:
    itens = tuple(p.strip() for p in falta.split(";") if p.strip()) if falta else ()
    return Capacidade(
        id=id_, area=area, titulo=titulo, status=status, tipo_motivo=tipo,
        motivo=falta or "", falta=itens, fonte_dado=fonte,
        origem={"epico": epico, "historia": historia, "cap": cap}, escopo=escopo,
        depende_de=tuple(depende), verificado_em=MAPA_VERIFICADO_EM, ligou_em=ligou_em)


L, P, T = "ligado", "parcial", "travado"


def catalogo() -> list[Capacidade]:
    return [
        # 1. Sistema
        _c("SIS-1", "sistema", "GPU detectada e preset de visão", L, None, "", "config.detect_gpu_profile", "1", "1.1"),
        _c("SIS-2", "sistema", "Fila serial de jobs (1 por vez)", L, None, "", "picorte.services.fila", "6", "6.3", ligou_em="2026-11-21"),
        _c("SIS-3", "sistema", "Lock de estágio de VRAM", L, None, "", "vram_runner.py", "2", "2.2"),
        _c("SIS-4", "sistema", "Modo Madrugada", P, "codigo", "agendador e controle na tela; só existe is_in_night_window", "vram_runner.py", "2", "2.2"),
        _c("SIS-5", "sistema", "Banco", L, None, "", "picorte.db (B1–B4, B6 da história 6.4)", "2", "2.1", ligou_em="2026-11-22"),
        _c("SIS-6", "sistema", "Motor de IA: Ollama", L, None, "", "Ollama /api/tags", "2", "2.3"),
        _c("SIS-7", "sistema", "Motor de IA: Gemini (agy)", L, None, "", "engine_health.json + erro do projeto", "2", "2.3"),
        _c("SIS-8", "sistema", "Motor de IA: Claude CLI", L, None, "", "claude no PATH", "2", "2.3"),
        _c("SIS-9", "sistema", "Modo Dupla", P, "dado", "nenhum uso real registrado", "llm_router", "2", "2.3", depende=("SIS-6", "SIS-8")),
        _c("SIS-10", "sistema", "Modo determinístico", L, "escolha", "aviso: nada do E3.5 roda nesse modo", "options.ai_mode", "3", "auditoria E3"),
        _c("SIS-11", "sistema", "yt-dlp, node e demucs", L, None, "", "sondas de binário", "1", "W4/W9"),
        _c("SIS-12", "sistema", "Servidor MCP", L, None, "", "picorte/mcp/server.py (fila única, B5)", "2", "2.4", ligou_em="2026-11-22"),
        _c("SIS-13", "sistema", "Custos e teto mensal", T, "codigo", "registro de gastos (B12)", "—", "6", "regra 6"),
        _c("SIS-14", "sistema", "Espaço livre em disco", L, None, "", "shutil.disk_usage", "6", "6.3"),
        # 2. Fila e projetos
        _c("FIL-1", "fila", "Criar projeto (URL ou arquivo; lote de 1–100)", L, None, "", "POST /api/projetos, /api/lote", "1", "E1"),
        _c("FIL-2", "fila", "Portão P1 antes de baixar", L, None, "", "project.json.source_gate", "4", "4.1", escopo="projeto"),
        _c("FIL-3", "fila", "Estágio, progresso e log", L, None, "", "GET /api/fila (estágio em PT-BR, título real) + job.log", "6", "6.6", escopo="projeto", ligou_em="2026-11-22"),
        _c("FIL-4", "fila", "VOD longo em blocos de 30 min e por seções", L, None, "", "*.partNNN.json, sections/", "1", "1.2", escopo="projeto"),
        _c("FIL-5", "fila", "Falha do Editor-Chefe com próximo passo", L, None, "", "GET /api/fila (falha.acao)", "6", "6.6", escopo="projeto", ligou_em="2026-11-22"),
        _c("FIL-6", "fila", "Separar conjunto de prova da produção", L, None, "", "options.benchmark_blind (Fila › Conjunto de prova)", "6", "6.6", ligou_em="2026-11-22"),
        _c("FIL-7", "fila", "Caça profunda e busca por pergunta", P, "codigo", "controles na tela; hoje só CLI/MCP", "hunt_mode, picorte_buscar_por_pergunta", "3.5", "3.5.5", escopo="projeto"),
        # 3. Revisão
        _c("REV-1", "revisao", "Arquétipo, tier, título, faixa 2s, 1º comentário, motivo", L, None, "", "segments.json, selection.json, .meta.json", "3.5", "3.5.3", escopo="corte"),
        _c("REV-2", "revisao", "Sinais medidos por corte", L, None, "", "clips.score_* (NULL = não medido)", "3", "3.2/3.5.4", escopo="corte", ligou_em="2026-11-22"),
        _c("REV-3", "revisao", "Ajustar início/fim; editar transcrição e legenda", L, None, "", "/candidates, /transcript", "1", "E1", escopo="corte"),
        _c("REV-4", "revisao", "Preview 480p e render final", L, None, "", "run (preview/render)", "1", "E1", escopo="corte"),
        _c("REV-5", "revisao", "Thumbnail automática", L, None, "", "*_thumb.png", "3.5", "3.5", escopo="corte"),
        _c("REV-6", "revisao", "Faixa de contexto 2s no vídeo", L, None, "", "render_clips.py", "3", "3.4", escopo="corte"),
        _c("REV-7", "revisao", "Keyframes (o LLM vê 3 frames)", L, "escolha", "desligado por padrão; Claude Sonnet, ~US$ 0,26 de limite por VOD (medido em 20/11, auditoria E3)", "options.keyframes", "3.5", "3.5.4", escopo="projeto"),
        _c("REV-8", "revisao", "👍/👎 por corte", L, None, "", "revisao_cortes (B10)", "6", "6.6", escopo="corte", ligou_em="2026-11-22"),
        _c("REV-9", "revisao", "Salvar como Exemplo Ouro", L, None, "", "picorte/ai/golden_examples.json", "6", "6.6", escopo="corte", ligou_em="2026-11-22"),
        _c("REV-10", "revisao", "Cold Open e Seamless Loop", T, "codigo", "render", "retention_engine", "3.7", "3.7.1", escopo="corte"),
        _c("REV-11", "revisao", "Layout dinâmico e Sniper Crop", T, "codigo", "ligar ao render", "reframe_games", "3.7", "3.7.2", escopo="corte"),
        _c("REV-12", "revisao", "Par Short ↔ Longo", T, "codigo", "corrigir o bug A11; parent_long_clip_id NULL", "clips", "3.7", "3.7.3", escopo="corte"),
        _c("REV-13", "revisao", "Arcos de 2 atos e compilação por arquétipo", P, "codigo", "render; hoje só JSON no modo deep", "two_act_arc, archetype_compiler", "3.7", "3.7.4", escopo="projeto"),
        _c("REV-14", "revisao", "Compilação cross-streamer", T, "codigo", "Épico 5", "—", "5", "A10"),
        _c("REV-15", "revisao", "nobada/mico, standalone, bordas por frase, ouro com 2 sinais", T, "codigo", "histórias 3.6.3–3.6.5", "—", "3.6", "3.6.3"),
        # 4. Fontes e permissões (P1)
        _c("FON-1", "fontes", "Lista de fontes com status e base da permissão", L, None, "", "sources + registry.json", "4", "4.1"),
        _c("FON-2", "fontes", "Cadastrar fonte e mudar permissão", L, None, "", "StudioService.create_source", "2", "2.4"),
        _c("FON-3", "fontes", "Tentativas barradas", L, None, "", "GET /api/fontes/barradas (erros [P1:pre_ingest] dos projetos)", "6", "6.7", ligou_em="2026-11-22"),
        _c("FON-4", "fontes", "Elo fonte → vídeos → cortes", L, None, "", "videos.source_id", "2", "2.1", ligou_em="2026-11-22"),
        _c("FON-5", "fontes", "Políticas por publisher/jogo", L, None, "", "publisher_policies (sincronizada no boot)", "4", "4.1", ligou_em="2026-11-22"),
        _c("FON-6", "fontes", "Campanhas CPM", P, "codigo", "cadastro e lista ligados; o radar de campanhas chega na história 5.1", "campaigns", "4", "4.1/5.1"),
        _c("FON-7", "fontes", "Pausar fonte (disjuntor manual)", L, None, "", "/api/risco/pausar-fonte, MCP", "4", "4.1"),
        _c("FON-8", "fontes", "Dossiês de jogo", L, None, "", "picorte/ai/game_dossiers/", "3.5", "3.5.5"),
        _c("FON-9", "fontes", "Perfis e piadas internas", T, "codigo", "história 5.4", "—", "5", "5.4"),
        # 5. Escudo (P1)
        _c("ESC-1", "escudo", "Veredito por corte e por rede", P, "dado", "nenhum corte renderizado depois do Escudo ainda; renderize de novo para ter veredito", "clips.risk_status + .meta.json.risk_verdict", "4", "4.5", escopo="corte"),
        _c("ESC-2", "escudo", "Selo Verde 15s (bleep e ***)", L, None, "", "render", "4", "4.4", escopo="corte"),
        _c("ESC-3", "escudo", "Remoção de música com Demucs", L, None, "", "clean_music_in_render", "4", "4.3", escopo="corte", depende=("SIS-11",)),
        _c("ESC-4", "escudo", "React Guard", L, None, "", "orquestrador", "4", "4.4", escopo="corte"),
        _c("ESC-5", "escudo", "YPP, originalidade TikTok e pHash", P, "dado", "aparece quando houver corte renderizado com veredito", "clips.ypp_transform_score, phash_signature", "4", "4.2", escopo="corte"),
        _c("ESC-6", "escudo", "Limpeza de texto por rede", L, None, "", "publish_kit", "4", "4.2", escopo="corte"),
        _c("ESC-7", "escudo", "Cadência e cooldown de 48h", L, None, "", "work/cadence_state.json", "4", "4.2"),
        _c("ESC-8", "escudo", "Registrar claim manual → pausa", L, None, "", "POST /api/escudo/claim → claims_events", "6", "6.7", ligou_em="2026-11-22"),
        _c("ESC-9", "escudo", "Monitor automático de claims", T, "codigo", "história 6.2", "—", "6", "6.2", "CAP-16"),
        # 6. Saúde e benchmark
        _c("SAU-1", "saude", "Saúde por projeto e por parte", L, None, "", "engine_health.json", "1", "1b/W9", escopo="projeto"),
        _c("SAU-2", "saude", "Confiança do projeto", T, "codigo", "história 3.6.5", "—", "3.6", "3.6.5", escopo="projeto"),
        _c("SAU-3", "saude", "Precision@K com lift contra o acaso", L, None, "amostra pequena (n=1)", "benchmarks/*.json", "3.6", "3.6.1"),
        _c("SAU-4", "saude", "Gabaritos acumulados para a 3.6.6", L, None, "", "benchmarks/gabaritos/", "3.6", "3.6.1"),
        _c("SAU-5", "saude", "Canário semanal e yt-dlp diário", T, "codigo", "W9", "—", "6", "W9"),
        # 7. Publicação
        _c("PUB-1", "publicacao", "Pacote do Dia", L, None, "", "GET /api/publicacao/pacote + export_daily_bundle", "6", "6.8", ligou_em="2026-11-22"),
        _c("PUB-2", "publicacao", "Kit por rede, copiar em 1 clique", L, None, "", ".meta.json.publish_kit", "4", "4.2/6.1", escopo="corte"),
        _c("PUB-3", "publicacao", "Registrar a URL publicada (pendência C2)", L, None, "", "POST /api/publicacao/links → publications", "6", "6.8", escopo="corte", ligou_em="2026-11-22"),
        _c("PUB-4", "publicacao", "YouTube Longo e Related Video", T, "codigo", "B11 + 3.7.3", "—", "6", "3.7.3", "CAP-15", depende=("REV-12",)),
        _c("PUB-5", "publicacao", "Contas OAuth das 5 redes", T, "codigo", "6.1 cofre de tokens; app aprovado por rede (T1)", "social_accounts", "6", "6.1", "CAP-15"),
        _c("PUB-6", "publicacao", "Publicação automática", T, "codigo", "6.1 + auditorias", "—", "6", "6.1", "CAP-15", depende=("PUB-5",)),
        # 8. Métricas e aprendizado
        _c("MET-1", "metricas", "Snapshots 1h/24h/7d", T, "codigo", "história 7.1", "metric_snapshots", "7", "7.1", "CAP-18", depende=("PUB-3",)),
        _c("MET-2", "metricas", "Recompensa anti-clickbait", T, "codigo", "história 7.1", "—", "7", "7.1", "CAP-18", depende=("MET-1",)),
        _c("MET-3", "metricas", "Bandit com esquecimento", T, "codigo", "história 7.2", "—", "7", "7.2", "CAP-18", depende=("MET-1",)),
        _c("MET-4", "metricas", "Reciclagem A/B do gancho", T, "codigo", "história 7.2", "—", "7", "7.2", "CAP-18", depende=("MET-3",)),
        _c("MET-5", "metricas", "Dataset rotulado e treino local", T, "codigo", "história 7.3", "—", "7", "7.3", "CAP-18", depende=("REV-8",)),
        _c("MET-6", "metricas", "Pesos calibrados pelo gabarito (≥ 20 VODs)", T, "codigo", "história 3.6.6", "—", "3.6", "3.6.6", depende=("SAU-4",)),
        # 9. Radar
        _c("RAD-1", "radar", "Tendências e calendário", T, "codigo", "história 5.1", "—", "5", "5.1"),
        _c("RAD-2", "radar", "Monitor de lives ao vivo, com chat da Twitch", T, "codigo", "história 5.2", "—", "5", "5.2"),
        _c("RAD-3", "radar", "Caçador de clipes de terceiros", T, "codigo", "história 5.3", "—", "5", "5.3"),
        _c("RAD-4", "radar", "Detector de treta e consenso entre streamers", T, "codigo", "história 5.3", "—", "5", "5.3"),
        _c("RAD-5", "radar", "Limpeza de dados de terceiros em 30 dias", T, "codigo", "história 5.1", "—", "5", "5.1"),
        # 10. Lives
        _c("LIV-1", "lives", "Ao vivo: streamers cadastrados transmitindo agora", T, "config", "credencial de app da Twitch (grátis e revogável); consulta oficial de está ao vivo", "sources + API oficial", "6", "6.5"),
        _c("LIV-2", "lives", "Abrir a live com player ao vivo e opções de corte", T, "codigo", "player embutido oficial + captura da live (5.2)", "—", "5", "5.2", depende=("LIV-1",)),
        _c("LIV-3", "lives", "Em alta", T, "codigo", "radar com a ordenação oficial das APIs (5.1)", "—", "5", "5.1"),
        _c("LIV-4", "lives", "Recentes: vídeos recentes dos streamers cadastrados", P, "config", "sem a chave da YouTube Data API a lista vem do yt-dlp, sem estatísticas oficiais; a chave entra em Configurações quando o cofre de segredos existir (história 6.1)", "registry.json + yt-dlp (cache 6 h, máx. 30 dias)", "6", "6.5"),
        _c("LIV-5", "lives", "Cortar um VOD na Sala do vídeo", L, None, "", "GET /api/sala + POST /api/lote", "6", "6.5", ligou_em="2026-11-22"),
        _c("LIV-6", "lives", "Selo AO VIVO, espectadores, duração", T, "codigo", "só com dado da API oficial e verificado_em", "API oficial", "5", "5.2", depende=("LIV-1",)),
    ]
