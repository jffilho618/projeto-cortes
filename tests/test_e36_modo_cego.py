"""Story 3.6.1 — Modo cego: no conjunto de prova o motor não vê o gabarito (comentários com horário e heatmap).

Sem isso o motor "lê as respostas antes da prova": os comentários viram sementes e dica ao Editor-Chefe, e o
heatmap vira semente/bônus — a Precision@K sairia inflada. Fora do conjunto de prova nada muda.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

SEED = {"start": 88.0, "end": 122.0, "duration": 34.0, "timestamp_s": 100.0, "hook": "caiu kkkk",
        "text": "ele caiu do prédio kkkk", "overall": 7.6, "raw_score": 7.6, "seed_kind": "comment_timestamp",
        "track_origin": "coop_payoff_nontextual", "score_parts": {"comment_likes": 44}, "evidence": {},
        "reason": "Timestamp de comentário (44 likes)"}
HEATMAP = [{"start_time": 40.0, "end_time": 45.0, "value": 0.2},
           {"start_time": 45.0, "end_time": 50.0, "value": 1.0},
           {"start_time": 50.0, "end_time": 55.0, "value": 0.3}]


def _vod(tmp_path: Path, *, blind: bool):
    from picorte.config import resolve_cli_binary

    wav = tmp_path / "audio.wav"
    subprocess.run([resolve_cli_binary("ffmpeg") or "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=160", str(wav)], check=True)
    words, t = [], 0.5
    for tok in ("olha isso cara. que absurdo mano! ele caiu de novo. " * 30).split():
        words.append({"word": tok, "start": round(t, 2), "end": round(t + 0.5, 2)})
        t += 0.6
    (tmp_path / "transcript.json").write_text(json.dumps({
        "video": str(wav), "duration": 160.0, "language": "pt", "words": words}), encoding="utf-8")
    (tmp_path / "comment_seeds.json").write_text(json.dumps([dict(SEED)]), encoding="utf-8")
    (tmp_path / "project.json").write_text(json.dumps({
        "id": "p", "options": {"benchmark_blind": blind},
        "source_meta": {"duration": 160.0, "heatmap": HEATMAP}}), encoding="utf-8")


def test_discover_blind_hides_comments_and_heatmap_from_the_motor(tmp_path: Path):
    import score_clips
    from picorte.engine import health

    _vod(tmp_path, blind=True)
    cands, stats = score_clips.discover(tmp_path, min_len=8, max_len=40)

    assert not any(c.get("seed_kind") in ("comment_timestamp", "heatmap_peak") for c in cands)
    assert not any(c.get("comment_hint") for c in cands)
    assert stats["comment_seeds"] == 0
    assert stats["modo_cego"] is True
    h = health.load(tmp_path)
    assert h["comment_seeds"]["status"] == "na" and "modo cego" in h["comment_seeds"]["detail"]
    assert h["heatmap"]["status"] == "na" and "modo cego" in h["heatmap"]["detail"]


def test_discover_outside_test_set_still_uses_comments_and_heatmap(tmp_path: Path):
    import score_clips
    from picorte.engine import health

    _vod(tmp_path, blind=False)
    cands, stats = score_clips.discover(tmp_path, min_len=8, max_len=40)

    assert any(c.get("seed_kind") == "comment_timestamp" for c in cands)
    assert stats["comment_seeds"] == 1
    assert stats["modo_cego"] is False
    assert health.load(tmp_path)["heatmap"]["status"] == "ok"


def test_select_heatmap_peaks_are_hidden_in_blind_projects(tmp_path: Path):
    import score_clips

    meta = {"heatmap": HEATMAP}
    (tmp_path / "project.json").write_text(json.dumps({"options": {"benchmark_blind": True}}), encoding="utf-8")
    assert score_clips._gabarito_heatmap_peaks(tmp_path, meta) == []
    (tmp_path / "project.json").write_text(json.dumps({"options": {}}), encoding="utf-8")
    assert [p["center"] for p in score_clips._gabarito_heatmap_peaks(tmp_path, meta)] == [47.5]


def test_engine_mirror_has_the_same_blind_switch():
    from picorte.engine import score_clips as engine_sc

    assert hasattr(engine_sc, "_gabarito_heatmap_peaks")
    assert hasattr(engine_sc, "_benchmark_blind")


# ---------------------------------------------------------------- opção de projeto e cache

def test_benchmark_blind_option_must_be_boolean():
    import projects

    assert projects.validate_options({"benchmark_blind": True})["benchmark_blind"] is True
    assert projects.validate_options({})["benchmark_blind"] is False
    with pytest.raises(ValueError):
        projects.validate_options({"benchmark_blind": "sim"})


def test_blind_changes_discovery_cache_but_old_projects_keep_their_keys():
    import projects

    base = projects.validate_options({})
    old_style = {k: v for k, v in base.items() if k != "benchmark_blind"}   # project.json de antes da 3.6.1
    key_old = projects.score_keys("t", {"x": 1}, old_style)
    key_off = projects.score_keys("t", {"x": 1}, base)
    key_on = projects.score_keys("t", {"x": 1}, {**base, "benchmark_blind": True})
    assert key_old == key_off               # nenhum projeto antigo é reprocessado
    assert key_on[0] != key_off[0]          # ligar o modo cego refaz a descoberta
