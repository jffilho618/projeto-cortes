import json

from picorte.services.sinais import miniatura_do_corte, sinais_medidos, veredito_do_corte


def test_sinais_medidos_de_um_candidato_real():
    seg = {"evidence": {"audio": 7.84, "visual": None, "chat": 2.58, "chat_measured": True,
                        "visual_games": 8.26, "hud": 0.0}, "score_parts": {"text_score": 6.1}}
    assert sinais_medidos(seg) == {"score_chat": 2.58, "score_audio": 7.84, "score_visual": None, "score_text": 6.1}


def test_chat_sem_marca_de_medido_nao_conta():
    seg = {"evidence": {"chat": 3.0, "audio": 5.0}}
    assert sinais_medidos(seg)["score_chat"] is None


def test_visual_games_so_vale_com_visao_medida():
    assert sinais_medidos({"evidence": {"visual": None, "visual_games": 8.0}})["score_visual"] is None
    assert sinais_medidos({"evidence": {"visual": None, "visual_games": 8.0, "vision_measured": True}})["score_visual"] == 8.0


def test_corte_do_scout_sem_evidencia_fica_todo_nao_medido():
    seg = {"evidence": {}, "score_parts": {"llm_scout": 1}, "overall": 10.0}
    assert set(sinais_medidos(seg).values()) == {None}


def test_tipos_estranhos_viram_nao_medido():
    seg = {"evidence": {"audio": "7", "chat": True, "chat_measured": True}, "score_parts": None}
    assert set(sinais_medidos(seg).values()) == {None}


def test_veredito_lido_do_meta(tmp_path):
    mp4 = tmp_path / "001-ab-x.mp4"
    (tmp_path / "001-ab-x.meta.json").write_text(json.dumps({
        "risk_status": "human_review", "thumbnail_1280x720": str(tmp_path / "t.png"),
        "risk_verdict": {"overall_status": "human_review", "ypp_score": 82, "phash_signature": "ab12"}}), encoding="utf-8")
    assert veredito_do_corte(mp4) == {"risk_status": "human_review", "ypp_transform_score": 82, "phash_signature": "ab12"}
    assert miniatura_do_corte(mp4) == str(tmp_path / "t.png")


def test_sem_meta_ou_sem_veredito_devolve_none(tmp_path):
    assert veredito_do_corte(tmp_path / "nao-existe.mp4") is None
    (tmp_path / "002-x.meta.json").write_text(json.dumps({"title": "x"}), encoding="utf-8")
    assert veredito_do_corte(tmp_path / "002-x.mp4") is None
    assert miniatura_do_corte(tmp_path / "002-x.mp4") == ""


def test_compact_do_pipeline_guarda_o_phash():
    from picorte.risk_shield.pipeline import _compact
    v = _compact({"overall_status": "pass", "ypp_score": 80, "phash_signature": "ff00", "gates": {}})
    assert v["phash_signature"] == "ff00"
