"""Etapa 1b — yt-dlp resolve o desafio JS do YouTube com o node quando ele existir (AD-11: sem node, sem flag).

Medição real (2026-11-20): sem node → 1 aviso e 44 formatos; com node + yt-dlp-ejs → 0 avisos e 47 formatos (+~1s).
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def test_base_cmd_adds_node_runtime_only_when_available(monkeypatch):
    import picorte.config as cfg

    monkeypatch.setattr(cfg.shutil, "which", lambda name: "C:/node/node.exe" if name == "node" else None)
    assert cfg.ytdlp_base_cmd()[-2:] == ["--js-runtimes", "node"]
    monkeypatch.setattr(cfg.shutil, "which", lambda name: None)
    assert "--js-runtimes" not in cfg.ytdlp_base_cmd()


def test_every_ytdlp_call_site_uses_the_shared_base(monkeypatch, tmp_path: Path):
    import picorte.config as cfg
    import ingest
    from picorte.engine import comments_miner

    monkeypatch.setattr(cfg.shutil, "which", lambda name: "node" if name == "node" else None)
    seen = []

    def fake(cmd, timeout=None, **kw):
        seen.append(list(cmd))
        (tmp_path / "discovery.mp4").write_bytes(b"v")
        return subprocess.CompletedProcess(cmd, 0, "{}", "")

    ingest.download_visual_discovery("https://youtu.be/x", tmp_path, runner=fake)
    (tmp_path / "c").mkdir()
    ingest.download_live_chat("https://youtu.be/x", tmp_path / "c", runner=fake)
    comments_miner.mine_youtube_comments("https://youtu.be/x", permission_status="liberada", runner=fake)
    assert seen and all("--js-runtimes" in c for c in seen), seen


def test_no_raw_ytdlp_command_left_in_production_code():
    root = Path(__file__).resolve().parents[1]
    files = ["ingest.py", "download_and_transcribe.py", "picorte/engine/ingest.py",
             "picorte/engine/download_and_transcribe.py", "picorte/engine/comments_miner.py"]
    offenders = [f for f in files if '"-m", "yt_dlp"' in (root / f).read_text(encoding="utf-8")]
    assert offenders == []
