from __future__ import annotations

import json
import subprocess
import threading
import urllib.request
from pathlib import Path

import cv2
import pytest

from picorte.config import resolve_cli_binary

pytestmark = pytest.mark.usefixtures("allow_p1_source_gate")


def _ffmpeg_bin() -> str:
    return resolve_cli_binary("ffmpeg") or "ffmpeg"


def _ffprobe_dims(path: Path) -> tuple[int, int]:
    ffprobe = resolve_cli_binary("ffprobe") or "ffprobe"
    res = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    w, h = res.stdout.strip().split("x")
    return int(w), int(h)


def test_e3_practical_end_to_end_real_video_ffmpeg_chat_cv_thumbnail_dashboard_db(tmp_path):
    """Teste prático real do Épico 3: vídeo .mp4 real + chat.json + 4D + CV + 9:16 + Thumbnail + DB + Dashboard HTTP."""
    import dashboard
    import projects
    from picorte.mcp.server import PicorteMCPServer

    # 1. Cria um vídeo real 1280x720 (22s) com movimento visual + áudio real via FFmpeg
    video_path = tmp_path / "live_game_sample.mp4"
    ffmpeg = _ffmpeg_bin()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=15:duration=22",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=22",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(video_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert video_path.is_file()

    # 2. Cria log real de chat ao lado do vídeo (<stem>_chat.json) com pico sismico entre t=8..14s
    chat_msgs = []
    for sec in range(22):
        chat_msgs.append({"t": float(sec) + 0.1, "text": "boa jogada"})
    for sec in range(8, 15):
        for k in range(20):
            chat_msgs.append({"t": float(sec) + k * 0.04, "text": "KKKKKK CLUTCH MENTIRA LUL"})
    (tmp_path / "live_game_sample_chat.json").write_text(
        json.dumps(chat_msgs), encoding="utf-8"
    )

    # 3. Cria o projeto via Studio HTTP / projects e pré-popula transcript.json válido para testar discover + 4D + render real
    root = tmp_path / "studio_projects"
    state = projects.create_project(
        root,
        str(video_path),
        {
            "aspect": "9:16",
            "vision_preset": "low",
            "ai_mode": "heuristic",
            "min_len": 12,
            "max_len": 22,
            "min_score": 0.0,
        },
    )
    pdir = projects.project_path(root, state["id"])

    # Transcript real compatível com faster-whisper cache para focar o teste no pipeline E3 + render FFmpeg
    words = []
    speech = "olha esse clutch absurdo no final da partida cara inacreditavel o que ele fez agora no campeonato"
    t = 1.0
    for token in speech.split():
        words.append({"word": token, "start": round(t, 2), "end": round(t + 0.9, 2)})
        t += 1.25
    identity = projects.file_identity(video_path)
    t_key = projects.digest([
        projects.dt.TRANSCRIPT_VERSION,
        identity,
        state["options"]["whisper_model"],
        state["options"]["device"],
        False,
        "video",
        False,
        str(video_path.resolve()),
    ])
    (pdir / "transcript.json").write_text(
        json.dumps(
            {
                "video": str(video_path.resolve()),
                "duration": 22.0,
                "language": "pt",
                "words": words,
                "source": str(video_path.resolve()),
                "media_kind": "video",
                "render_from_sections": False,
                "identity": identity,
            }
        ),
        encoding="utf-8",
    )
    state["cache"]["transcript"] = t_key
    state["source_identity"] = identity
    state["video"] = str(video_path.resolve())
    projects.save_project(pdir, state)

    # Garante context_banner_2s para validar que vai pro .ass e .meta.json no render real
    # Primeiro roda prepare (discover + select + 4D + chat + CV low)
    prep_state = projects.run_project(pdir, action="prepare", resume=True)
    assert prep_state["status"] == "review"

    candidates = json.loads((pdir / "candidates.json").read_text(encoding="utf-8"))["candidates"]
    assert candidates, "discover deve gerar candidatos"
    # Confirma que Sismógrafo do Chat + Visão Games rodaram de verdade na descoberta
    assert "chat" in candidates[0]["evidence"]
    assert "visual_games" in candidates[0]["evidence"]
    assert candidates[0]["evidence"]["chat"] >= 6.0

    selection_meta = json.loads((pdir / "selection.json").read_text(encoding="utf-8"))
    assert selection_meta.get("source_duration") == pytest.approx(22.0)

    # Enriquece o segmento escolhido com context_banner_2s e pinned_comment_debate antes do render real
    segs = json.loads((pdir / "segments.json").read_text(encoding="utf-8"))
    assert segs
    segs[0]["context_banner_2s"] = "CLUTCH IMPOSSIVEL NO FINAL!"
    segs[0]["pinned_comment_debate"] = "Voce teria arriscado essa play?"
    (pdir / "segments.json").write_text(json.dumps(segs), encoding="utf-8")

    # 4. Roda render real FFmpeg (9:16, ass queimado, thumbnail 1280x720, cold_open, DB sync)
    done_state = projects.run_project(pdir, action="render", resume=True, pick="1")
    assert done_state["status"] == "complete"
    outputs = done_state["last_outputs"]
    assert len(outputs) == 1
    mp4_out = Path(outputs[0])
    assert mp4_out.is_file() and mp4_out.stat().st_size > 10_000

    # Verifica dimensões 9:16 reais via ffprobe (1080x1920)
    rw, rh = _ffprobe_dims(mp4_out)
    assert (rw, rh) == (1080, 1920)

    # Verifica thumbnail automática 9:16 (1080x1920 para Shorts/Reels) + .meta.json enriquecido + .ass com ContextBanner
    thumb_out = mp4_out.with_name(mp4_out.stem + "_thumb.png")
    assert thumb_out.is_file() and thumb_out.stat().st_size <= 2 * 1024 * 1024
    thumb_img = cv2.imread(str(thumb_out))
    assert thumb_img.shape == (1920, 1080, 3)

    meta = json.loads(mp4_out.with_suffix(".meta.json").read_text(encoding="utf-8"))
    assert meta["context_banner_2s"] == "CLUTCH IMPOSSIVEL NO FINAL!"
    assert meta["pinned_comment_debate"] == "Voce teria arriscado essa play?"
    assert meta["cold_open"]["teaser_duration"] >= 1.2
    assert Path(meta["thumbnail_1280x720"]).is_file()
    # P2 (Épico 4): todo corte final sai com veredito P1. Aqui o portão de ingestão foi liberado por fixture
    # sem fonte vinculada, então o escudo precisa barrar a exportação (fonte sem vínculo = hard_block).
    assert meta["risk_status"] == "hard_block"
    assert meta["risk_verdict"]["gates"]["source_permission"]["code"] == "source_unlinked"

    # Verifica DB + MCP + Dashboard HTTP
    mcp = PicorteMCPServer()
    fila = mcp.call_tool("picorte_status_fila", {})
    assert fila["total_clips"] >= 1
    assert fila["total_videos"] >= 1

    server = dashboard.make_server(root, 0)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/db/status") as r_db:
            db_json = json.loads(r_db.read().decode("utf-8"))
        assert db_json["total_clips"] >= 1

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/projects/{state['id']}") as r_proj:
            proj_json = json.loads(r_proj.read().decode("utf-8"))
        assert len(proj_json["files"]) >= 1
        assert len(proj_json["candidates"]) >= 1
    finally:
        server.shutdown()
        server.app.close()
        server.server_close()
