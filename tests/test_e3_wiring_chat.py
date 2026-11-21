"""Etapa 1b (auditoria E3) — Sismógrafo do Chat ligado de verdade: baixa o chat do VOD do YouTube via yt-dlp."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import ingest


def _yt_line(ms: int, *runs) -> str:
    return json.dumps({"replayChatItemAction": {"videoOffsetTimeMsec": str(ms), "actions": [{"addChatItemAction": {
        "item": {"liveChatTextMessageRenderer": {"message": {"runs": list(runs)}}}}}]}})


def test_parse_youtube_live_chat_flattens_runs_and_emojis(tmp_path: Path):
    raw = tmp_path / "x.live_chat.json"
    raw.write_text("\n".join([
        _yt_line(12500, {"text": "KKKKK "}, {"emoji": {"emojiId": "😂", "shortcuts": [":face-with-tears-of-joy:"]}}),
        _yt_line(3000, {"text": "noob"}),
        json.dumps({"replayChatItemAction": {"videoOffsetTimeMsec": "4000", "actions": [
            {"addLiveChatTickerItemAction": {}}]}}),  # evento sem mensagem: ignorado
        "linha quebrada {",
    ]), encoding="utf-8")
    msgs = ingest.parse_youtube_live_chat(raw)
    assert msgs == [{"t": 3.0, "text": "noob"}, {"t": 12.5, "text": "KKKKK 😂"}]


def test_channel_emoji_without_unicode_uses_shortcut(tmp_path: Path):
    raw = tmp_path / "x.live_chat.json"
    raw.write_text(_yt_line(1000, {"emoji": {"emojiId": "UCabc/xyz", "shortcuts": [":_alanKEKW:"],
                                            "isCustomEmoji": True}}), encoding="utf-8")
    assert ingest.parse_youtube_live_chat(raw) == [{"t": 1.0, "text": ":_alanKEKW:"}]


def test_download_live_chat_writes_normalized_chat_json(tmp_path: Path):
    calls = []

    def fake_run(cmd, timeout=None, **kw):
        calls.append(cmd)
        out_tmpl = cmd[cmd.index("-o") + 1]
        Path(out_tmpl.replace("%(ext)s", "live_chat.json")).write_text(
            _yt_line(2000, {"text": "CLIP"}), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    out = ingest.download_live_chat("https://www.youtube.com/watch?v=abc", tmp_path, runner=fake_run)
    assert out == tmp_path / "chat.json"
    assert json.loads(out.read_text(encoding="utf-8")) == [{"t": 2.0, "text": "CLIP"}]
    assert "--skip-download" in calls[0] and "live_chat" in calls[0]
    assert not list(tmp_path.glob("*.live_chat.json"))  # bruto removido


def test_download_live_chat_ignores_non_youtube_sources(tmp_path: Path):
    def never(*a, **k):
        raise AssertionError("não deveria chamar o yt-dlp")

    assert ingest.download_live_chat("https://www.twitch.tv/videos/123", tmp_path, runner=never) is None


def test_download_live_chat_failure_is_not_fatal(tmp_path: Path):
    def boom(cmd, timeout=None, **kw):
        raise subprocess.TimeoutExpired(cmd, timeout)

    assert ingest.download_live_chat("https://youtu.be/abc", tmp_path, runner=boom) is None


def test_download_live_chat_reuses_existing_file(tmp_path: Path):
    (tmp_path / "chat.json").write_text(json.dumps([{"t": 1.0, "text": "oi"}]), encoding="utf-8")

    def never(*a, **k):
        raise AssertionError("cache deveria evitar novo download")

    assert ingest.download_live_chat("https://youtu.be/abc", tmp_path, runner=never) == tmp_path / "chat.json"


def test_timeout_keeps_partial_chat_already_downloaded(tmp_path: Path):
    """Live de 11h (VOD real x50ONQrBPRM): 45s de download = 38 min de chat. Estourar o tempo não joga fora o já baixado."""
    seen = []

    def slow(cmd, timeout=None, **kw):
        out_tmpl = cmd[cmd.index("-o") + 1]
        Path(out_tmpl.replace("%(ext)s", "live_chat.json.part")).write_text(
            "\n".join([_yt_line(1000, {"text": "bom dia Davy"}), _yt_line(2_280_000, {"text": "KKKKKK"})]),
            encoding="utf-8")
        raise subprocess.TimeoutExpired(cmd, timeout)

    out = ingest.download_live_chat("https://youtu.be/x", tmp_path, runner=slow,
                                    on_status=lambda s, d: seen.append((s, d)))
    assert json.loads(out.read_text(encoding="utf-8"))[-1] == {"t": 2280.0, "text": "KKKKKK"}
    assert seen[-1][0] == "ok" and "parcial" in seen[-1][1]
    assert not list(tmp_path.glob("chatsrc*"))


def test_chat_timeout_scales_with_vod_duration():
    assert ingest.chat_timeout_for(None) == ingest.CHAT_TIMEOUT
    assert ingest.chat_timeout_for(11.33 * 3600) > ingest.CHAT_TIMEOUT  # 11h: ~14 min só de chat
    assert ingest.chat_timeout_for(600) == ingest.CHAT_TIMEOUT


def test_engine_mirror_has_same_chat_functions():
    from picorte.engine import ingest as engine_ingest

    assert hasattr(engine_ingest, "download_live_chat") and hasattr(engine_ingest, "parse_youtube_live_chat")


def test_prepare_downloads_chat_for_url_sources_before_discover(tmp_path: Path, monkeypatch, allow_p1_source_gate):
    import projects

    order = []
    monkeypatch.setattr(projects.ingest, "download_live_chat",
                        lambda url, workdir, **k: order.append(("chat", url)))
    monkeypatch.setattr(projects.score_clips, "discover", lambda *a, **k: order.append(("discover",)) or (_ for _ in ()).throw(RuntimeError("stop")))
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
    assert ("chat", "https://www.youtube.com/watch?v=abc") in order
    assert order.index(("chat", "https://www.youtube.com/watch?v=abc")) < order.index(("discover",))
