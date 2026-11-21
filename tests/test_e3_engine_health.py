"""Etapa 1b — Registro de saúde do motor (dados para o painel "Saúde do motor" do E6, W9).

Cada parte que antes falhava em silêncio grava ok / na (não se aplica) / failed + motivo em engine_health.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest


def test_record_and_load_merge_parts(tmp_path: Path):
    from picorte.engine import health

    health.record(tmp_path, "visual_proxy", "failed", "Requested format is not available")
    health.record(tmp_path, "comments", "ok", "39 momentos")
    data = health.load(tmp_path)
    assert data["visual_proxy"]["status"] == "failed"
    assert "Requested format" in data["visual_proxy"]["detail"]
    assert data["comments"]["status"] == "ok" and data["comments"]["at"]
    assert health.failures(tmp_path) == ["visual_proxy"]


def test_record_rejects_unknown_status(tmp_path: Path):
    from picorte.engine import health

    with pytest.raises(ValueError):
        health.record(tmp_path, "x", "talvez")


def test_chat_download_reports_na_failed_and_ok(tmp_path: Path):
    import ingest

    seen = []
    ingest.download_live_chat("https://www.twitch.tv/videos/1", tmp_path, on_status=lambda s, d: seen.append(s))

    def boom(cmd, timeout=None, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)

    ingest.download_live_chat("https://youtu.be/x", tmp_path, runner=boom, on_status=lambda s, d: seen.append(s))

    def no_chat(cmd, timeout=None, **kw):
        return subprocess.CompletedProcess(cmd, 0, "", "")

    ingest.download_live_chat("https://youtu.be/x", tmp_path, runner=no_chat, on_status=lambda s, d: seen.append(s))
    assert seen == ["na", "failed", "na"]


def test_comment_seeds_report_status(tmp_path: Path, monkeypatch):
    import picorte.engine.comments_miner as cm

    seen = []
    cm.save_comment_seeds("https://www.twitch.tv/videos/1", tmp_path, permission_status="liberada",
                          on_status=lambda s, d: seen.append(s))
    monkeypatch.setattr(cm, "mine_youtube_comments", lambda url, **k: (_ for _ in ()).throw(RuntimeError("x")))
    cm.save_comment_seeds("https://youtu.be/x", tmp_path, permission_status="liberada",
                          on_status=lambda s, d: seen.append(s))
    monkeypatch.setattr(cm, "mine_youtube_comments", lambda url, **k: [{"start": 1.0, "end": 9.0}])
    cm.save_comment_seeds("https://youtu.be/x", tmp_path, permission_status="liberada",
                          on_status=lambda s, d: seen.append((s, d)))
    assert seen[0] == "na" and seen[1] == "failed" and seen[2] == ("ok", "1 momentos marcados pelo público")


def test_discover_records_signal_health(tmp_path: Path):
    import score_clips
    from picorte.config import resolve_cli_binary
    from picorte.engine import health

    wav = tmp_path / "audio.wav"
    subprocess.run([resolve_cli_binary("ffmpeg") or "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=40", str(wav)], check=True)
    words, t = [], 0.5
    for tok in ("olha isso cara. que absurdo mano! ele caiu de novo. " * 8).split():
        words.append({"word": tok, "start": round(t, 2), "end": round(t + 0.5, 2)})
        t += 0.6
    (tmp_path / "transcript.json").write_text(json.dumps({
        "video": str(wav), "duration": 40.0, "language": "pt", "words": words}), encoding="utf-8")
    score_clips.discover(tmp_path, min_len=8, max_len=30)
    h = health.load(tmp_path)
    assert h["prosody"]["status"] == "ok"
    assert h["chat"]["status"] == "na"
    assert h["heatmap"]["status"] == "na"
    assert h["comment_seeds"]["status"] == "na"
    assert h["vision"]["status"] == "na"  # fonte só de áudio: visão não se aplica


def test_select_records_editor_failure_before_stopping(tmp_path: Path, monkeypatch):
    import score_clips
    from picorte.ai import llm_router
    from picorte.engine import health

    cands = [{"start": 10.0, "end": 40.0, "duration": 30.0, "overall": 8.5, "raw_score": 8.5, "text": "olha",
              "hook": "olha", "evidence": {}, "score_parts": {}}]
    (tmp_path / "candidates.json").write_text(json.dumps({"version": 1, "mode": "heuristic", "candidates": cands}),
                                              encoding="utf-8")
    (tmp_path / "transcript.json").write_text(json.dumps({"words": [], "duration": 60.0}), encoding="utf-8")
    monkeypatch.setattr(llm_router.LLMRouter, "rerank_candidates",
                        lambda *a, **k: (_ for _ in ()).throw(llm_router.EditorChiefUnavailable("gemini", "cota")))
    with pytest.raises(llm_router.EditorChiefUnavailable):
        score_clips.select(tmp_path, min_score=0.0, ai_mode="gemini")
    assert health.load(tmp_path)["editor"]["status"] == "failed"


def test_select_records_editor_ok(tmp_path: Path, monkeypatch):
    import score_clips
    from picorte.ai import llm_router
    from picorte.engine import health

    cands = [{"start": 10.0, "end": 40.0, "duration": 30.0, "overall": 8.5, "raw_score": 8.5, "text": "olha",
              "hook": "olha", "evidence": {}, "score_parts": {}}]
    (tmp_path / "candidates.json").write_text(json.dumps({"version": 1, "mode": "heuristic", "candidates": cands}),
                                              encoding="utf-8")
    (tmp_path / "transcript.json").write_text(json.dumps({"words": [], "duration": 60.0}), encoding="utf-8")
    monkeypatch.setattr(llm_router.LLMRouter, "rerank_candidates",
                        lambda self, c, **k: {"candidates": [dict(x, archetype="clutch_fail") for x in c],
                                              "llm_mode_used": "claude"})
    score_clips.select(tmp_path, min_score=0.0, ai_mode="claude")
    assert health.load(tmp_path)["editor"]["status"] == "ok"
