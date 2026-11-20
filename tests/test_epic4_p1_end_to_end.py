"""P13 (code review Épico 4) — Suíte adversarial P1 ponta a ponta no pipeline REAL (sem liberar o portão por fixture).

Fluxo: vídeo local real → dono declarado → Pre-Ingest → render FFmpeg → música detectada → veredito no .meta.json
→ Pacote do Dia → disjuntor (pausa da fonte) → export barrado e nova ingestão barrada.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from picorte.config import resolve_cli_binary


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    import picorte.db.connection as conn

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'p1_e2e.db').as_posix()}")
    monkeypatch.setattr(conn, "_DEFAULT_DB", None)
    monkeypatch.setattr("picorte.risk_shield.cadence_guard.DEFAULT_CADENCE_STATE_PATH", tmp_path / "cad.json")
    return conn.get_default_db()


def _make_video(path: Path) -> Path:
    # Vídeo com movimento + acorde musical contínuo (simula rádio licenciada tocando no gameplay)
    subprocess.run([
        resolve_cli_binary("ffmpeg") or "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=15:duration=22",
        "-f", "lavfi", "-i",
        "aevalsrc='0.2*sin(2*PI*110*t)+0.2*sin(2*PI*440*t)+0.15*sin(2*PI*554.37*t)':s=44100:d=22",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ], check=True)
    # Chat com pico sísmico em 8–14s para a descoberta achar o lance (igual ao e2e do Épico 3)
    msgs = [{"t": s + 0.1, "text": "boa jogada"} for s in range(22)]
    msgs += [{"t": s + k * 0.04, "text": "KKKKKK CLUTCH MENTIRA LUL"} for s in range(8, 15) for k in range(20)]
    path.with_name(f"{path.stem}_chat.json").write_text(json.dumps(msgs), encoding="utf-8")
    return path


def _prepare_project(tmp_path: Path, video: Path, owner: str | None):
    import projects

    root = tmp_path / "projects"
    opts = {"aspect": "9:16", "layout": "games", "vision_preset": "low", "ai_mode": "heuristic",
            "min_len": 12, "max_len": 22, "min_score": 0.0}
    if owner:
        opts["source_owner"] = owner
    state = projects.create_project(root, str(video), opts)
    pdir = projects.project_path(root, state["id"])
    words, t = [], 1.0
    for token in "olha esse clutch absurdo no final da partida cara inacreditavel o que ele fez agora".split():
        words.append({"word": token, "start": round(t, 2), "end": round(t + 0.9, 2)})
        t += 1.25
    identity = projects.file_identity(video)
    key = projects.digest([projects.dt.TRANSCRIPT_VERSION, identity, state["options"]["whisper_model"],
                           state["options"]["device"], False, "video", False, str(video.resolve())])
    (pdir / "transcript.json").write_text(json.dumps({
        "video": str(video.resolve()), "duration": 22.0, "language": "pt", "words": words,
        "source": str(video.resolve()), "media_kind": "video", "render_from_sections": False, "identity": identity,
    }), encoding="utf-8")
    state["cache"]["transcript"] = key
    state["source_identity"] = identity
    state["video"] = str(video.resolve())
    projects.save_project(pdir, state)
    return pdir


def test_local_file_without_owner_never_reaches_transcription(tmp_path, isolated_db):
    import projects
    from picorte.risk_shield.policy_gate import PolicyViolationError

    pdir = _prepare_project(tmp_path, _make_video(tmp_path / "v.mp4"), owner=None)
    with pytest.raises(PolicyViolationError):
        projects.run_project(pdir, action="prepare", resume=True)
    assert not (pdir / "candidates.json").exists()


def test_full_p1_chain_on_real_pipeline(tmp_path, isolated_db):
    import projects
    from picorte.engine.publish_kit import export_daily_bundle
    from picorte.risk_shield.policy_gate import PolicyViolationError
    from picorte.services.studio_service import StudioService

    video = _make_video(tmp_path / "live.mp4")
    pdir = _prepare_project(tmp_path, video, owner="alanzoka")

    # 1) Pre-Ingest: dono declarado = streamer cadastrado, liberado por tolerância pública
    prep = projects.run_project(pdir, action="prepare", resume=True)
    gate = prep["source_gate"]
    assert gate["channel_handle"] == "@alanzoka"
    assert gate["permission_basis"] == "tolerancia_publica"

    # 2) Render real: todo corte sai com veredito, ligado à fonte real (não "sem vínculo")
    done = projects.run_project(pdir, action="render", resume=True, pick="1")
    mp4 = Path(done["last_outputs"][0])
    meta = json.loads(mp4.with_suffix(".meta.json").read_text(encoding="utf-8"))
    verdict = meta["risk_verdict"]
    assert verdict["gates"]["source_permission"]["status"] == "pass"
    assert verdict["gates"]["source_permission"]["permission_basis"] == "tolerancia_publica"
    # 3) Música contínua foi detectada e tratada (cirurgia aplicada ou revisão explícita, nunca ignorada)
    music = verdict["gates"]["music_surgeon"]
    assert music["status"] in {"auto_fixed", "human_review"}
    assert meta["risk_status"] in {"auto_fixed", "human_review", "hard_block"}

    # 4) Pacote do Dia respeita o veredito (bloqueado não sai; revisão sai marcada)
    bundle = export_daily_bundle(pdir, out_root=tmp_path / "out", db=isolated_db)
    if meta["risk_status"] == "hard_block":
        assert mp4.stem in bundle["skipped_blocked"]
    else:
        exported = {f["stem"]: f for f in bundle["files"]}
        assert exported[mp4.stem]["needs_review"] is (meta["risk_status"] == "human_review")

    # 5) Disjuntor: 1º claim pausa a fonte → nada mais sai nem entra
    StudioService().risk_pause_source(gate["source_id"], claim_type="copyright_claim", reason="claim no YouTube")
    with pytest.raises(PolicyViolationError):
        export_daily_bundle(pdir, out_root=tmp_path / "out2", db=isolated_db)
    with pytest.raises(PolicyViolationError):
        projects.run_project(pdir, action="prepare", resume=True)
