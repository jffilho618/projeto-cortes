"""Painel acompanhando o code review do motor (briefing de 2026-11-23, seções 2, 4 e W32)."""
from __future__ import annotations

import json
from pathlib import Path

from picorte.services.revisao import _sinais, alertas_da_saude, linha_da_fila, montar_revisao

ANTIGA = "2026-11-20T10:00:00+00:00"
NOVA = "2026-11-23T07:27:26+00:00"
MARCA = {"inicio": "2026-11-23T07:00:00+00:00", "acao": "prepare"}


def test_visao_degradada_traz_o_aviso_da_w49(tmp_path: Path):
    saude = {"vision": {"status": "failed", "detail": "12 candidatos medidos, mas degradado: MediaPipe indisponível"}}
    medido = {"evidence": {"vision_measured": True, "facecam_measured": False, "visual_games": 3.5}}
    (visao,) = [s for s in _sinais(medido, saude, tmp_path) if s["chave"] == "visual"]
    assert visao["estado"] == "falhou" and "W49" in visao["motivo"] and "MediaPipe" in visao["motivo"]


def test_corte_que_a_visao_nao_analisou_diz_isso(tmp_path: Path):
    """A visão só analisa os primeiros candidatos: corte fora deles não 'falhou' nem 'a visão não rodou'."""
    for saude in ({"vision": {"status": "ok", "detail": "12 candidatos medidos"}},
                  {"vision": {"status": "failed", "detail": "12 candidatos medidos, mas degradado: MediaPipe"}}):
        (visao,) = [s for s in _sinais({"evidence": {}}, saude, tmp_path) if s["chave"] == "visual"]
        assert (visao["estado"], visao["motivo"]) == ("nao_medido", "a visão não analisou este corte")
    (sem,) = [s for s in _sinais({"evidence": {}}, {}, tmp_path) if s["chave"] == "visual"]
    assert sem["motivo"] == "a visão não rodou"  # sem a parte vision na saúde, segue igual


def test_alertas_so_do_editor_e_do_batedor_na_ultima_execucao(tmp_path: Path):
    (tmp_path / "engine_health.json").write_text(json.dumps({
        "_execucao": MARCA,
        "editor": {"status": "failed", "detail": "lote parcial: 18 de 23 candidatos avaliados", "at": NOVA},
        "full_vod_scout": {"status": "failed", "detail": "velho", "at": ANTIGA},
        "vision": {"status": "failed", "detail": "degradado", "at": NOVA},
    }), encoding="utf-8")
    assert alertas_da_saude(tmp_path) == [{"parte": "Editor-Chefe", "detalhe": "lote parcial: 18 de 23 candidatos avaliados"}]
    linha = linha_da_fila({"id": "p", "status": "review"}, alertas_da_saude(tmp_path))
    assert linha["alertas"][0]["parte"] == "Editor-Chefe" and linha["falha"] is None


def test_revisao_usa_so_a_ultima_execucao_rotula_e_conta_quem_precisa_de_voce(tmp_path: Path):
    (tmp_path / "clips").mkdir()
    (tmp_path / "segments.json").write_text(json.dumps([{"id": "001", "tier": "ouro"}, {"id": "002", "tier": "forte"}]),
                                            encoding="utf-8")
    (tmp_path / "clips" / "001-x.meta.json").write_text(json.dumps({"risk_verdict": {"overall_status": "human_review"}}),
                                                       encoding="utf-8")
    (tmp_path / "engine_health.json").write_text(json.dumps({
        "_execucao": MARCA,
        "heatmap": {"status": "failed", "detail": "velho", "at": ANTIGA},
        "editor": {"status": "failed", "detail": "2ª passada falhou: timeout", "at": NOVA},
        "vision": {"status": "failed", "detail": "degradado: MediaPipe indisponível", "at": NOVA},
    }), encoding="utf-8")
    rev = montar_revisao(tmp_path, {"id": "p"}, {})
    assert rev["projeto"]["resumo_saude"][0] == "Editor-Chefe: 2ª passada falhou: timeout"
    assert "W49" in rev["projeto"]["resumo_saude"][1] and len(rev["projeto"]["resumo_saude"]) == 2
    assert rev["projeto"]["pedem_voce"] == 1


def test_sem_cli_de_ia_o_painel_avisa_que_nao_ha_api_paga():
    """Seção 5: sem o CLI da assinatura o Editor para (regra 6); nada de fallback para API paga."""
    from picorte.capacidades.sondas import sonda_agy, sonda_cli_ia

    claude = sonda_cli_ia("claude", resolver=lambda _n: None)
    assert claude.ok is False and "regra 6" in claude.detalhe and "API paga" in claude.detalhe
    assert sonda_cli_ia("claude", resolver=lambda _n: "C:/bin/claude.exe").ok is True
    gemini = sonda_agy(".", resolver=lambda _n: None)
    assert "regra 6" in gemini.detalhe


def test_keyframes_usam_a_assinatura_e_nao_a_api_paga(tmp_path):
    from estudio_fakes import cache_falso
    from picorte.capacidades import listar_capacidades

    rev7 = next(c for c in listar_capacidades(tmp_path, cache_falso())["capacidades"] if c["id"] == "REV-7")
    assert "claude -p" in rev7["motivo"] and "assinatura" in rev7["motivo"] and "US$ 0,26" in rev7["motivo"]


def test_familia_do_corte_pelo_moment_id():
    """W36: Short, versão TikTok e Longo do mesmo momento são família, não duplicata no pHash."""
    from picorte.risk_shield.pipeline import family_clip_ids

    segs = [{"id": "001", "moment_id": "m10-50"}, {"id": "002", "moment_id": "m60-90"},
            {"id": "003", "moment_id": "m10-50", "formato": "tiktok_60"}, {"id": "004", "moment_id": "m10-50", "formato": "longo_16x9"},
            {"id": "005"}]
    assert family_clip_ids("abc", segs[0], segs) == ["studio-abc:003", "studio-abc:004"]
    assert family_clip_ids("abc", segs[2], segs) == ["studio-abc:001", "studio-abc:004"]
    assert family_clip_ids("abc", segs[4], segs) == []


def test_veredito_repassa_a_familia_ao_escudo(tmp_path: Path, monkeypatch):
    import picorte.risk_shield.pipeline as pl

    visto = {}

    def auditar(_db, **kw):
        visto.update(kw)
        return {"overall_status": "pass"}

    monkeypatch.setattr(pl, "audit_clip_risk", auditar)
    monkeypatch.setattr(pl, "sample_clip_frames", lambda _p: [])
    pl.attach_risk_verdict(None, meta_path=tmp_path / "x.meta.json", source_id="s", seg={"start": 0, "end": 30},
                           words=[], mp4_path=None, options={}, clip_id="studio-abc:001",
                           family_clip_ids=["studio-abc:003"])
    assert visto["family_clip_ids"] == ["studio-abc:003"] and visto["clip_id"] == "studio-abc:001"


def test_render_passa_a_familia_calculada_sobre_todos_os_segmentos():
    raiz = Path(__file__).resolve().parents[1]
    fonte = (raiz / "projects.py").read_text(encoding="utf-8")
    assert "todos_segmentos = segments" in fonte
    assert "family_clip_ids=family_clip_ids(state['id'], segment, todos_segmentos)" in fonte


SPOILER = "Spoiler bloqueado na janela pós-lançamento de gta6 (final do jogo)."
NAO_REGISTRADO = "barrado pelo P1 (motivo não registrado)"
REDES4 = ("youtube_shorts", "tiktok", "instagram_reels", "facebook_reels")


def test_motivo_do_p1_vem_do_proprio_veredito():
    """Corte hard_block diz por quê, com o texto gravado no risk_verdict; igual em todas as redes, uma lista só."""
    from picorte.services.revisao import motivos_do_veredito

    v = {"overall_status": "hard_block", "per_platform": {r: "hard_block" for r in REDES4},
         "gates": {"source_permission": {"status": "pass"},
                   "publisher_policy": {"status": "hard_block", "reasons": [SPOILER]}}}
    m = motivos_do_veredito(v)
    assert m["motivos"] == [{"portao": "Política do publisher", "texto": SPOILER}] and m["motivos_por_rede"] == {}


def test_sem_motivo_gravado_diz_que_nao_foi_registrado():
    from picorte.services.revisao import motivos_do_veredito

    v = {"overall_status": "hard_block", "per_platform": {r: "hard_block" for r in REDES4},
         "gates": {"react_guard": {"status": "hard_block"}}}
    assert motivos_do_veredito(v)["motivos"] == [{"portao": "React perigoso", "texto": NAO_REGISTRADO}]
    erro = {"overall_status": "audit_error", "error": "TypeError: x"}
    assert motivos_do_veredito(erro)["motivos"] == [{"portao": "Auditoria", "texto": "TypeError: x"}]


def test_motivo_por_rede_quando_as_redes_diferem():
    """Rede pior que os portões gerais: a causa é dela e não foi gravada (o _compact só guarda o status)."""
    from picorte.services.revisao import motivos_do_veredito

    v = {"overall_status": "hard_block",
         "per_platform": {"youtube_shorts": "human_review", "tiktok": "hard_block",
                          "instagram_reels": "human_review", "facebook_reels": "pass"},
         "gates": {"green_seal_15s": {"status": "human_review", "reason": "palavrão nos 15 s"}}}
    m = motivos_do_veredito(v)
    assert m["motivos"] == []
    selo = {"portao": "Selo Verde 15s", "texto": "palavrão nos 15 s"}
    assert m["motivos_por_rede"]["youtube_shorts"] == [selo]
    assert m["motivos_por_rede"]["tiktok"] == [selo, {"portao": "Esta rede", "texto": NAO_REGISTRADO}]
    assert m["motivos_por_rede"]["facebook_reels"] == []


def test_ficha_da_revisao_traz_os_motivos(tmp_path: Path):
    (tmp_path / "clips").mkdir()
    (tmp_path / "segments.json").write_text(json.dumps([{"id": "001", "tier": "ouro"}]), encoding="utf-8")
    (tmp_path / "clips" / "001-x.meta.json").write_text(json.dumps({"risk_verdict": {
        "overall_status": "hard_block", "per_platform": {r: "hard_block" for r in REDES4},
        "gates": {"publisher_policy": {"status": "hard_block", "reasons": [SPOILER]}}}}), encoding="utf-8")
    p1 = montar_revisao(tmp_path, {"id": "p"}, {})["cortes"][0]["p1"]
    assert p1["motivos"][0]["texto"] == SPOILER and p1["geral"] == "hard_block"
