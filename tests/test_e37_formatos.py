"""3.7.3 — par Short↔Longo com sobreposição real, versão TikTok 60–75 s e família no pHash."""
from __future__ import annotations

from pathlib import Path

import pytest


def _sents(n=200, dur=4.0, gap=0.5, t0=0.0):
    out, t = [], t0
    for i in range(n):
        out.append({"start": round(t, 2), "end": round(t + dur, 2), "text": f"frase {i}"})
        t += dur + gap
    return out


SENTS = _sents()  # 200 frases de 4 s com 0,5 s de pausa → ~900 s de fala


# ---------------------------------------------------------------- par Short↔Longo

def test_short_sem_sobreposicao_nao_liga_a_longo_nenhum():
    from picorte.engine.retention_engine import pair_short_and_long_clips

    clips = [{"id": "s1", "start": 10.0, "end": 40.0}, {"id": "L1", "start": 500.0, "end": 740.0}]
    out = pair_short_and_long_clips(clips)
    assert "parent_long_clip_id" not in out[0]


def test_short_pouco_dentro_do_longo_nao_liga():
    from picorte.engine.retention_engine import pair_short_and_long_clips

    clips = [{"id": "s1", "start": 230.0, "end": 260.0}, {"id": "L1", "start": 0.0, "end": 240.0}]
    assert "parent_long_clip_id" not in pair_short_and_long_clips(clips)[0]


def test_short_dentro_do_longo_liga():
    from picorte.engine.retention_engine import pair_short_and_long_clips

    clips = [{"id": "s1", "start": 100.0, "end": 130.0}, {"id": "L1", "start": 0.0, "end": 240.0}]
    assert pair_short_and_long_clips(clips)[0]["parent_long_clip_id"] == "L1"


# ---------------------------------------------------------------- versão TikTok

def test_versao_tiktok_tem_60_a_75_s_contem_o_short_e_termina_em_frase():
    from picorte.engine.formats import moment_id_for, tiktok_version

    short = {"start": 450.0, "end": 480.0, "overall": 8.5, "tier": "forte", "proposed_title": "X"}
    short["moment_id"] = moment_id_for(short)
    tk = tiktok_version(short, SENTS, source_duration=900.0)
    assert 60.0 <= tk["end"] - tk["start"] <= 75.0
    assert tk["start"] <= 450.0 and tk["end"] >= 480.0
    starts = {s["start"] for s in SENTS}
    ends = {s["end"] for s in SENTS}
    assert tk["start"] in starts or tk["start"] == 450.0
    assert tk["end"] in ends or tk["end"] == 480.0
    assert tk["formato"] == "tiktok_60"
    assert tk["aspect"] == "9:16"
    assert tk["moment_id"] == short["moment_id"]


def test_fonte_curta_demais_nao_gera_versao_tiktok():
    from picorte.engine.formats import tiktok_version

    sents = _sents(n=8)  # ~36 s de vídeo
    assert tiktok_version({"start": 5.0, "end": 30.0}, sents, source_duration=36.0) is None


def test_short_ja_longo_nao_ganha_versao_tiktok():
    from picorte.engine.formats import tiktok_version

    assert tiktok_version({"start": 100.0, "end": 170.0}, SENTS, source_duration=900.0) is None


# ---------------------------------------------------------------- proposta de Longo

def test_longo_de_3_a_5_min_em_volta_do_pico_do_heatmap():
    from picorte.engine.formats import long_proposal

    short = {"start": 400.0, "end": 430.0, "tier": "ouro"}
    lg = long_proposal(short, SENTS, heatmap_peaks=[{"center": 480.0}], source_duration=900.0)
    assert 180.0 <= lg["end"] - lg["start"] <= 300.0
    assert lg["start"] <= 400.0 and lg["end"] >= 430.0
    assert lg["start"] <= 480.0 <= lg["end"]
    assert lg["miolo"] == "heatmap"
    assert lg["aspect"] == "16:9"
    assert lg["formato"] == "longo_16x9"


def test_longo_so_para_ouro_ou_forte():
    from picorte.engine.formats import long_proposal

    assert long_proposal({"start": 400.0, "end": 430.0, "tier": "experimental"}, SENTS,
                         heatmap_peaks=[], source_duration=900.0) is None


def test_pouca_fala_nao_gera_longo():
    from picorte.engine.formats import long_proposal

    sparse = _sents(n=30, dur=1.0, gap=29.0)  # 1 s de fala a cada 30 s
    assert long_proposal({"start": 400.0, "end": 430.0, "tier": "ouro"}, sparse,
                         heatmap_peaks=[], source_duration=900.0) is None


def test_irmaos_saem_no_fim_sem_rank_e_com_o_mesmo_momento():
    from picorte.engine.formats import add_format_siblings

    segs = [{"start": 400.0, "end": 430.0, "rank": 1, "tier": "ouro", "overall": 9.0},
            {"start": 600.0, "end": 625.0, "rank": 2, "tier": "experimental", "overall": 7.0}]
    out = add_format_siblings(segs, SENTS, heatmap_peaks=[], source_duration=900.0)
    shorts = [s for s in out if s.get("formato", "short") == "short"]
    extras = [s for s in out if s.get("formato") in ("tiktok_60", "longo_16x9")]
    assert len(shorts) == 2
    assert {s["formato"] for s in extras} == {"tiktok_60", "longo_16x9"}
    assert sum(1 for s in extras if s["formato"] == "longo_16x9") == 1  # só o ouro
    assert all("rank" not in s for s in extras)
    assert {s["moment_id"] for s in extras} <= {s["moment_id"] for s in shorts}


# ---------------------------------------------------------------- projects: ligação e render

def test_parent_short_id_ligado_pelo_momento():
    from projects import link_format_family

    segs = [{"id": "001", "start": 1.0, "end": 30.0, "moment_id": "m1"},
            {"id": "002", "start": 0.0, "end": 65.0, "moment_id": "m1", "formato": "tiktok_60"}]
    out = link_format_family(segs)
    assert out[1]["parent_short_id"] == "001"


def test_longo_renderiza_em_16x9_e_layout_simples():
    from projects import render_params_for

    opts = {"aspect": "9:16", "layout": "games", "max_len": 58}
    assert render_params_for({"formato": "longo_16x9", "aspect": "16:9"}, opts) == ("16:9", "single", None)
    assert render_params_for({"formato": "tiktok_60"}, opts) == ("9:16", "games", 75)
    assert render_params_for({}, opts) == ("9:16", "games", 58)


def test_formatos_extras_e_opcao_bool_que_so_entra_na_chave_quando_desligada():
    import projects

    assert projects.validate_options({})["formatos_extras"] is True
    with pytest.raises(ValueError):
        projects.validate_options({"formatos_extras": "sim"})
    k_on = projects.score_keys("t", {}, projects.validate_options({}))[1]
    k_off = projects.score_keys("t", {}, projects.validate_options({"formatos_extras": False}))[1]
    assert k_on != k_off


# ---------------------------------------------------------------- família no pHash

def _scene(seed: int, n: int = 15):
    import cv2
    import numpy as np

    rng = np.random.default_rng(seed)
    frames = []
    for _ in range(n):
        fr = np.full((360, 640, 3), (60, 90, 70), dtype=np.uint8)
        for _ in range(6):
            x, y = int(rng.integers(0, 600)), int(rng.integers(0, 320))
            cv2.rectangle(fr, (x, y), (x + 40, y + 40), tuple(int(c) for c in rng.integers(0, 255, 3)), -1)
        frames.append(fr)
    return frames


def test_versao_da_mesma_familia_nao_e_duplicata_mas_a_de_fora_e(tmp_path: Path):
    from picorte.db.connection import Database
    from picorte.db.repositories import PicorteRepositories
    from picorte.risk_shield.ypp_guard import compute_video_phash, evaluate_ypp_and_dedup

    db = Database(f"sqlite:///{(tmp_path / 'f.db').as_posix()}")
    db.init_schema()
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(name="S", platform="twitch", channel_handle="@s", permission_status="liberada")
    vid = repos.videos.create_video(source_id=src["id"], source_url="u", game_slug="")
    short = repos.clips.create_clip(video_id=vid["id"], start_sec=0.0, end_sec=30.0)
    frames = _scene(9)
    db.execute("UPDATE clips SET phash_signature = ? WHERE id = ?", (compute_video_phash(frames), short["id"]))
    kw = dict(frames=frames, has_facecam_split=True, has_dynamic_captions=True, has_context_banner=True,
              has_native_metadata=True)
    assert evaluate_ypp_and_dedup(db, family_clip_ids=[short["id"]], **kw)["is_duplicate"] is False
    assert evaluate_ypp_and_dedup(db, **kw)["is_duplicate"] is True
