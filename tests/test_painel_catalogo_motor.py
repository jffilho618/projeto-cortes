"""Catálogo de capacidades alinhado ao motor (3.6.2–3.6.5 e 3.7.1–3.7.5 prontos; 3.6.6 não) — pedido de 2026-11-23.

Destravar só o que existe, com o dado real na tela; o que não existe continua travado com motivo (A5).
"""
from __future__ import annotations

import json
from pathlib import Path

from estudio_fakes import cache_falso
from picorte.capacidades import listar_capacidades


def _caps(tmp_path):
    return {c["id"]: c for c in listar_capacidades(tmp_path, cache_falso())["capacidades"]}


def test_o_que_o_motor_ja_faz_esta_ligado(tmp_path):
    caps = _caps(tmp_path)
    for i in ["REV-10", "REV-11", "REV-12", "REV-13", "REV-15", "REV-16", "SAU-2", "ESC-1", "ESC-5"]:
        assert caps[i]["status"] == "ligado", i
        assert caps[i]["ligou_em"] == "2026-11-23", i
    assert "Facecam + jogo" in caps["REV-11"]["motivo"]  # só roda no layout games, quando acha a facecam
    assert "clímax" in caps["REV-10"]["motivo"]  # Cold Open sai em poucos cortes (W33): dito na tela
    assert "A11" not in caps["REV-12"]["motivo"] and "TikTok" in caps["REV-12"]["titulo"]


def test_o_que_nao_existe_continua_travado_ou_parcial_com_motivo(tmp_path):
    caps = _caps(tmp_path)
    assert caps["PUB-4"]["status"] == "parcial" and "6.1" in caps["PUB-4"]["motivo"]
    assert caps["FIL-7"]["status"] == "parcial" and "pergunta" in caps["FIL-7"]["motivo"]
    assert "só CLI" not in caps["FIL-7"]["motivo"]  # a Sala já tem caça rápida e profunda
    assert caps["MET-6"]["status"] == "travado"  # 3.6.6 em backlog
    assert caps["REV-14"]["status"] == "travado"  # cross-streamer é do Épico 5


def test_revisao_traz_standalone_e_confianca_reais(tmp_path: Path):
    from picorte.services.revisao import montar_revisao

    (tmp_path / "segments.json").write_text(json.dumps([{"id": "001", "standalone": 7.5}, {"id": "002"}]), encoding="utf-8")
    (tmp_path / "engine_health.json").write_text(json.dumps({"confianca_projeto": {"status": "ok", "detail": json.dumps({
        "sinais_ok": ["prosody", "editor"], "sinais_falhos": ["vision"], "sinais_ausentes": ["chat"], "nota": 0.43})}}),
        encoding="utf-8")
    rev = montar_revisao(tmp_path, {"id": "p"}, {})
    por_seg = {c["seg"]: c for c in rev["cortes"]}
    assert por_seg["001"]["standalone"] == 7.5 and por_seg["002"]["standalone"] is None
    assert rev["projeto"]["confianca"] == {"nota": 0.43, "sinais_ok": ["prosody", "editor"], "sinais_falhos": ["vision"],
                                           "sinais_ausentes": ["chat"]}


def test_confianca_ausente_ou_ilegivel_vira_none(tmp_path: Path):
    from picorte.services.saude import confianca_do_projeto

    assert confianca_do_projeto({}) is None
    assert confianca_do_projeto({"confianca_projeto": {"status": "ok", "detail": "não é json"}}) is None
    m = confianca_do_projeto({"confianca_projeto": {"status": "ok", "detail": '{"nota": 0.8, "sinais_ok": ["chat"]}'}})
    assert m == {"nota": 0.8, "sinais_ok": ["chat"], "sinais_falhos": [], "sinais_ausentes": []}


def test_matriz_da_saude_traz_a_confianca_de_cada_projeto(tmp_path: Path):
    from picorte.services.saude import matriz_motor

    (tmp_path / "p1").mkdir()
    (tmp_path / "p1" / "engine_health.json").write_text(json.dumps({"confianca_projeto": {
        "status": "ok", "detail": '{"nota": 0.43, "sinais_ok": ["editor"]}'}}), encoding="utf-8")
    linha = matriz_motor(tmp_path, [{"id": "p1"}])["projetos"][0]
    assert linha["confianca"]["nota"] == 0.43


def test_corte_traz_formato_momento_duracao_e_trechos(tmp_path: Path):
    """Live do Paulinho: Short, TikTok e Longo do mesmo momento pareciam duplicados; compilação aparecia com 13.640 s."""
    from picorte.services.revisao import montar_revisao

    (tmp_path / "segments.json").write_text(json.dumps([
        {"id": "001", "formato": "short", "moment_id": "m1", "start": 10, "end": 52},
        {"id": "002", "formato": "tiktok_60", "moment_id": "m1", "start": 0, "end": 62},
        {"id": "003", "formato": "compilacao", "start": 479.54, "end": 14119.73, "duration": 218.51,
         "trechos": [{"start": 480, "end": 526}, {"start": 1985, "end": 2020}]},
        {"id": "004", "start": 0, "end": 30},  # projeto de antes do campo formato
    ]), encoding="utf-8")
    c = {x["seg"]: x for x in montar_revisao(tmp_path, {"id": "p"}, {})["cortes"]}
    assert (c["001"]["formato"], c["001"]["moment_id"], c["001"]["duracao"]) == ("short", "m1", 42)
    assert c["002"]["formato"] == "tiktok_60" and c["002"]["moment_id"] == "m1"
    assert c["003"]["duracao"] == 218.51 and c["003"]["trechos"] == [{"start": 480, "end": 526}, {"start": 1985, "end": 2020}]
    assert c["004"]["formato"] is None and c["004"]["trechos"] == [] and c["004"]["duracao"] == 30


def test_ruido_do_winerror_10054_e_silenciado_e_o_resto_nao():
    """Navegador cancelando pedaços de mídia gera ConnectionResetError no Proactor do Windows: ruído sem efeito."""
    from picorte.api.app import filtro_de_reset

    repassados = []

    class Laco:
        def default_exception_handler(self, contexto):
            repassados.append(contexto)

    reset = {"message": "Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)",
             "exception": ConnectionResetError(10054, "Foi forçado o cancelamento de uma conexão existente")}
    outro = {"message": "Task exception was never retrieved", "exception": ValueError("de verdade")}
    filtro_de_reset("win32")(Laco(), reset)
    filtro_de_reset("win32")(Laco(), outro)
    filtro_de_reset("linux")(Laco(), reset)
    assert repassados == [outro, reset]
