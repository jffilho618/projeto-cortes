"""Etapa 1b (auditoria E3) — proxy visual de VOD longo: o YouTube atual não tem formato combinado 'worst'.

Sem isso a visão de games (MAR, HUD/killfeed, facecam) nunca rodou na descoberta de VODs longos em produção
("Requested format is not available" → "Visual proxy skipped").
"""
from __future__ import annotations

from pathlib import Path
import subprocess

import ingest


def _capture(tmp_path: Path):
    seen = []

    def fake_run(cmd, timeout=None, **kw):
        seen.append(cmd)
        (tmp_path / "discovery.mp4").write_bytes(b"v")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    return seen, fake_run


def test_visual_proxy_accepts_video_only_streams(tmp_path: Path):
    seen, fake_run = _capture(tmp_path)
    ingest.download_visual_discovery("https://www.youtube.com/watch?v=x", tmp_path, runner=fake_run)
    fmt = seen[0][seen[0].index("-f") + 1]
    first_choice = fmt.split("/")[0]
    assert first_choice.startswith("worstvideo")  # faixa só de vídeo vem primeiro (visão não precisa de áudio)
    assert "height<=360" in first_choice or "height<=480" in first_choice
    assert fmt.split("/")[-1] == "worst"  # último recurso continua existindo


def test_engine_mirror_uses_same_visual_proxy_selector(tmp_path: Path):
    from picorte.engine import ingest as engine_ingest

    seen, fake_run = _capture(tmp_path)
    engine_ingest.download_visual_discovery("https://www.youtube.com/watch?v=x", tmp_path, runner=fake_run)
    assert seen[0][seen[0].index("-f") + 1].startswith("worstvideo")
