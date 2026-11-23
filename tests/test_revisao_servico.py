import json

import pytest

from picorte.services.revisao import estagio_pt, linha_da_fila, montar_revisao


def _projeto(tmp_path, *, health=None, chat=False):
    pasta = tmp_path / "aaaaaaaaaaaa"
    (pasta / "clips").mkdir(parents=True)
    (pasta / "previews").mkdir()
    estado = {"id": "aaaaaaaaaaaa", "source": "https://www.youtube.com/watch?v=q4ekFpRjgKQ", "status": "review",
              "options": {"ai_mode": "ollama", "benchmark_blind": False},
              "source_meta": {"title": "EMBOSCADOS! - GTA 6", "channel": "alanzoka", "detected_game": "gta6", "duration": 8087},
              "source_gate": {"source_name": "ALANZOKA"}}
    segs = [
        {"start": 10, "end": 40, "overall": 9.0, "tier": "forte", "archetype": "caos_coop", "proposed_title": "Forte medido",
         "evidence": {"audio": 7.0, "chat": 6.0, "chat_measured": True}, "score_parts": {"text_score": 6.5}, "reason": "arco forte"},
        {"start": 100, "end": 130, "overall": 10.0, "tier": "ouro", "archetype": "callback_oculto", "proposed_title": "Ouro do Scout",
         "evidence": {}, "score_parts": {"llm_scout": 1}, "track_origin": "full_vod_scout", "why_extraordinary": "callback raro",
         "context_banner_2s": "No trailer era diferente", "pinned_comment_debate": "Genial ou exagero?"},
        {"start": 200, "end": 230, "overall": 8.0, "tier": "forte", "archetype": "rage_tilt", "hook": "Forte sem sinal",
         "evidence": {"audio": 3.0}},
    ]
    (pasta / "segments.json").write_text(json.dumps(segs), encoding="utf-8")
    (pasta / "clips" / "002-bbbb-ouro.mp4").write_bytes(b"x")
    (pasta / "clips" / "002-bbbb-ouro.meta.json").write_text(json.dumps({"risk_verdict": {
        "overall_status": "human_review", "per_platform": {"youtube_shorts": "pass", "tiktok": "human_review"}}}), encoding="utf-8")
    (pasta / "previews" / "001-aaaa-forte.preview.mp4").write_bytes(b"x")
    if health:
        (pasta / "engine_health.json").write_text(json.dumps(health), encoding="utf-8")
    if chat:
        (pasta / "chat.json").write_text("[]", encoding="utf-8")
    return pasta, estado


def test_estagio_em_portugues():
    assert estagio_pt("running", "transcribe") == "Transcrevendo"
    assert estagio_pt("running", "source") == "Baixando"
    assert estagio_pt("running", "select") == "Escolhendo cortes"
    assert estagio_pt("running", "render") == "Renderizando"
    assert estagio_pt("review", "ready for review") == "Pronto para revisar"
    assert estagio_pt("queued", "waiting") == "Na fila"
    assert estagio_pt("failed", "discover") == "Falhou"
    assert estagio_pt("interrupted", "render") == "Interrompido"


def test_linha_da_fila_com_titulo_real_e_progresso_do_render():
    linha = linha_da_fila({"id": "p1", "status": "running", "stage": "render", "created": 1795276800,
                           "progress": {"stage": "render 4/17", "done": 0, "total": 0},
                           "options": {"ai_mode": "gemini", "benchmark_blind": True},
                           "source": "https://youtu.be/x", "source_meta": {"title": "GTA 6 AO VIVO", "detected_game": "gta6"},
                           "source_gate": {"source_name": "DAVY JONES"}})
    assert linha["titulo"] == "GTA 6 AO VIVO" and linha["streamer"] == "DAVY JONES" and linha["jogo"] == "gta6"
    assert linha["estagio"] == "Renderizando" and linha["progresso"] == {"feito": 4, "total": 17}
    assert linha["motor"] == "gemini" and linha["prova"] is True and linha["falha"] is None


def test_falha_traz_a_acao_certa():
    p1 = linha_da_fila({"id": "e", "status": "failed", "error": "[P1:pre_ingest] Fonte desconhecida: 'X'. Nada foi baixado."})
    motor = linha_da_fila({"id": "f", "status": "failed", "error": "lote 1/2 falhou 2x: CalledProcessError: agy.exe"})
    parado = linha_da_fila({"id": "g", "status": "interrupted"})
    assert p1["falha"]["acao"] == "cadastrar_fonte"
    assert motor["falha"]["acao"] == "trocar_motor"
    assert parado["falha"] == {"motivo": "O job parou antes de terminar.", "acao": "retomar"}
    assert linha_da_fila({"id": "s", "source": "C:/videos/meu.mp4"})["titulo"] == "meu.mp4"


def test_revisao_ordena_por_tier_e_sinais_que_concordam(tmp_path):
    pasta, estado = _projeto(tmp_path)
    r = montar_revisao(pasta, estado, {})
    assert [c["titulo"] for c in r["cortes"]] == ["Ouro do Scout", "Forte medido", "Forte sem sinal"]
    assert r["projeto"]["titulo"] == "EMBOSCADOS! - GTA 6" and r["projeto"]["n_cortes"] == 3
    assert r["projeto"]["streamer"] == "ALANZOKA" and r["projeto"]["jogo"] == "gta6"


def test_sinais_medido_ou_nao_medido_com_motivo_nunca_zero(tmp_path):
    pasta, estado = _projeto(tmp_path, health={"vision": {"status": "na", "detail": "sem GPU livre"}})
    cortes = {c["seg"]: c for c in montar_revisao(pasta, estado, {})["cortes"]}
    forte = {s["chave"]: s for s in cortes["001"]["sinais"]}
    assert forte["chat"] == {"chave": "chat", "nome": "Chat", "estado": "medido", "valor": 6.0, "motivo": ""}
    assert forte["visual"]["estado"] == "nao_medido" and forte["visual"]["valor"] is None
    assert forte["visual"]["motivo"] == "sem GPU livre"
    scout = {s["chave"]: s for s in cortes["002"]["sinais"]}
    assert scout["chat"]["motivo"] == "vídeo sem chat"
    assert scout["texto"]["motivo"] == "escolhido pelo Scout, sem nota de texto"


def test_sinal_que_falhou_aparece_como_falhou(tmp_path):
    pasta, estado = _projeto(tmp_path, chat=True, health={"chat": {"status": "failed", "detail": "chat.json corrompido"}})
    scout = {s["chave"]: s for s in {c["seg"]: c for c in montar_revisao(pasta, estado, {})["cortes"]}["002"]["sinais"]}
    assert scout["chat"]["estado"] == "falhou" and scout["chat"]["motivo"] == "chat.json corrompido"


def test_p1_por_rede_e_sem_veredito(tmp_path):
    pasta, estado = _projeto(tmp_path)
    cortes = {c["seg"]: c for c in montar_revisao(pasta, estado, {})["cortes"]}
    assert cortes["002"]["p1"] == {
        "sem_veredito": False, "geral": "human_review", "por_rede": {"youtube_shorts": "pass", "tiktok": "human_review"},
        "motivos": [], "motivos_por_rede": {"youtube_shorts": [], "tiktok": [
            {"portao": "Esta rede", "texto": "revisão humana pedida pelo P1 (motivo não registrado)"}]}}
    assert cortes["001"]["p1"] == {"sem_veredito": True, "geral": None, "por_rede": {}, "motivos": [],
                                   "motivos_por_rede": {}}


def test_renders_casam_pelo_prefixo_e_decisoes_entram(tmp_path):
    pasta, estado = _projeto(tmp_path)
    decisoes = {"002": {"rotulo": 1, "motivo": "", "descartado": False, "exemplo_ouro": True}}
    cortes = {c["seg"]: c for c in montar_revisao(pasta, estado, decisoes)["cortes"]}
    assert cortes["002"]["render"] == {"clip": "/media/aaaaaaaaaaaa/clips/002-bbbb-ouro.mp4", "preview": None}
    assert cortes["001"]["render"] == {"clip": None, "preview": "/media/aaaaaaaaaaaa/previews/001-aaaa-forte.preview.mp4"}
    assert cortes["002"]["decisao"]["exemplo_ouro"] is True
    assert cortes["003"]["decisao"] == {"rotulo": None, "motivo": "", "descartado": False, "exemplo_ouro": False}
    assert cortes["002"]["faixa_2s"] == "No trailer era diferente" and cortes["002"]["motivo"] == "callback raro"


def test_projeto_sem_segmentos_tem_lista_vazia(tmp_path):
    pasta = tmp_path / "bbbbbbbbbbbb"
    pasta.mkdir()
    r = montar_revisao(pasta, {"id": "bbbbbbbbbbbb", "source": "x"}, {})
    assert r["cortes"] == [] and r["projeto"]["n_cortes"] == 0


@pytest.mark.parametrize("status", ["new", "complete"])
def test_estagios_simples(status):
    assert estagio_pt(status, None) in {"Criado", "Pronto"}
