"""Etapa 1b (auditoria E3) — Comentários com timestamp do YouTube ligados à descoberta (gabarito humano grátis).

Validação real (2026-11-20, VOD yWvnOWILFk0): 39 momentos marcados pelo público em ~9s, só metadados.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


SEED = {"start": 88.0, "end": 122.0, "duration": 34.0, "hook": "ele caiu do prédio kkkk", "text": "ele caiu do prédio kkkk",
        "overall": 7.6, "raw_score": 7.6, "seed_kind": "comment_timestamp", "track_origin": "coop_payoff_nontextual",
        "score_parts": {"comment_likes": 44}, "evidence": {}, "reason": "Timestamp de comentário (44 likes)"}


def test_save_comment_seeds_writes_file_for_allowed_youtube_source(tmp_path: Path, monkeypatch):
    import picorte.engine.comments_miner as cm

    monkeypatch.setattr(cm, "mine_youtube_comments", lambda url, **k: [dict(SEED)])
    out = cm.save_comment_seeds("https://www.youtube.com/watch?v=x", tmp_path, permission_status="liberada")
    assert out == tmp_path / "comment_seeds.json"
    assert json.loads(out.read_text(encoding="utf-8"))[0]["seed_kind"] == "comment_timestamp"


def test_save_comment_seeds_skips_non_youtube_and_never_raises(tmp_path: Path, monkeypatch):
    import picorte.engine.comments_miner as cm

    def boom(url, **k):
        raise RuntimeError("yt-dlp quebrou")

    monkeypatch.setattr(cm, "mine_youtube_comments", boom)
    assert cm.save_comment_seeds("https://www.twitch.tv/videos/1", tmp_path, permission_status="liberada") is None
    assert cm.save_comment_seeds("https://youtu.be/x", tmp_path, permission_status="liberada") is None


def test_save_comment_seeds_respects_p1_gate(tmp_path: Path):
    import picorte.engine.comments_miner as cm

    assert cm.save_comment_seeds("https://youtu.be/x", tmp_path, permission_status="desconhecida") is None


def test_merge_comment_seeds_uses_transcript_text_and_keeps_public_hint():
    import score_clips

    sentences = [{"start": 90.0, "end": 95.0, "text": "não acredito que eu pulei"},
                 {"start": 96.0, "end": 100.0, "text": "caí de novo mano"},
                 {"start": 300.0, "end": 305.0, "text": "outra coisa"}]
    merged = score_clips.merge_comment_seeds([], [dict(SEED)], sentences)
    assert merged[0]["text"] == "não acredito que eu pulei caí de novo mano"
    assert merged[0]["comment_hint"] == "ele caiu do prédio kkkk"
    assert merged[0]["comment_likes"] == 44


def test_editor_chief_sees_public_comment_hint():
    from picorte.ai.llm_router import LLMRouter

    prompts = []

    def fake(provider, model, system_prompt, user_prompt):
        prompts.append(user_prompt)
        rows = json.loads(user_prompt[user_prompt.index("["):])
        return json.dumps([{"index": r["index"], "adjustment": 0.0, "reason": "ok"} for r in rows])

    cand = {"start": 88.0, "end": 122.0, "overall": 7.6, "text": "caí de novo", "evidence": {},
            "comment_hint": "ele caiu do prédio kkkk", "comment_likes": 44}
    LLMRouter(provider_runner=fake).rerank_candidates([cand], ai_mode="gemini")
    rows = json.loads(prompts[0][prompts[0].index("["):])
    assert rows[0]["comentario_publico"] == "ele caiu do prédio kkkk (44 likes)"


def test_discover_includes_comment_seeds(tmp_path: Path):
    import subprocess

    import score_clips
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
    cands, stats = score_clips.discover(tmp_path, min_len=8, max_len=40)
    assert any(c.get("seed_kind") == "comment_timestamp" and c.get("comment_hint") for c in cands)
    assert stats["comment_seeds"] == 1


def test_prepare_mines_comments_after_gate_for_url(tmp_path: Path, monkeypatch, allow_p1_source_gate):
    import picorte.engine.comments_miner as cm
    import projects

    calls = []
    monkeypatch.setattr(cm, "save_comment_seeds", lambda url, workdir, **k: calls.append((url, k)))
    monkeypatch.setattr(projects.ingest, "download_live_chat", lambda *a, **k: None)
    monkeypatch.setattr(projects.score_clips, "discover", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stop")))
    monkeypatch.setattr(projects.ingest, "probe_source", lambda s, runner=None: {
        "source": s, "url": True, "title": "t", "channel": "alanzoka", "duration": 120.0, "estimated_size": 1})
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    monkeypatch.setattr(projects.dt, "resolve_source", lambda *a, **k: video)
    monkeypatch.setattr(projects.dt, "transcribe", lambda *a, **k: {"words": [], "duration": 120.0}, raising=False)
    state = projects.create_project(tmp_path / "p", "https://www.youtube.com/watch?v=abc", {"min_len": 15})
    path = projects.project_path(tmp_path / "p", state["id"])
    (path / "transcript.json").write_text(json.dumps({"words": [], "duration": 120.0}), encoding="utf-8")
    with pytest.raises(Exception):
        projects.run_project(path, action="prepare")
    assert calls and calls[0][0] == "https://www.youtube.com/watch?v=abc"
    assert calls[0][1]["permission_status"] == "gameplay_proprio"  # vem do portão P1 (fixture)
