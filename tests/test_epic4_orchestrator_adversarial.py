"""Testes TDD Story 4.5 — Orquestrador RiskShield (RiskVerdict por Rede), MCP P1 e Endpoints UI/Cool-Down."""
from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _make_db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{(tmp_path / 'e4_orch.db').as_posix()}")
    db.init_schema()
    return db


def test_risk_orchestrator_returns_per_platform_verdict_and_persists_to_db(tmp_path: Path):
    from picorte.risk_shield.orchestrator import audit_clip_risk
    from picorte.risk_shield.policy_gate import sync_publisher_policies

    db = _make_db(tmp_path)
    sync_publisher_policies(db)
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(
        name="ALANZOKA", platform="youtube", channel_handle="@alanzoka", permission_status="liberada"
    )
    vid = repos.videos.create_video(source_id=src["id"], source_url="https://yt/gta6", game_slug="gta6")
    clip = repos.clips.create_clip(video_id=vid["id"], start_sec=10.0, end_sec=50.0)

    frames = []
    for i in range(6):
        fr = np.full((360, 202, 3), (50 + i * 8, 95, 60), dtype=np.uint8)
        cv2.circle(fr, (40 + i * 20, 150), 32, (200, 180, 60), -1)
        frames.append(fr)

    words = [
        {"word": "Olha", "start": 10.5, "end": 10.8},
        {"word": "porra", "start": 11.0, "end": 11.4},
        {"word": "que", "start": 11.5, "end": 11.7},
        {"word": "detalhe", "start": 11.8, "end": 12.2},
    ]

    verdict = audit_clip_risk(
        db,
        source_id=src["id"],
        clip_id=clip["id"],
        game_slug="gta6",
        title="Alanzoka testa física do GTA 6",
        description="Créditos: https://youtube.com/@alanzoka #shorts #gta6",
        hashtags=["#shorts", "#gta6", "#alanzoka"],
        source_credit="@alanzoka",
        words=words,
        clip_start=10.0,
        clip_end=50.0,
        frames=frames,
        has_facecam_split=True,
        has_dynamic_captions=True,
        has_context_banner=True,
        has_native_metadata=True,
        has_cold_open=True,
        # GTA 6 tem rádio licenciada: a checagem de música precisa ter rodado (aqui, sem música detectada).
        music_result={"status": "pass", "surgery_applied": False, "music_intervals": []},
        cadence_state_path=tmp_path / "cadence.json",
    )

    assert verdict["overall_status"] in {"pass", "auto_fixed"}
    assert "youtube_shorts" in verdict["per_platform"]
    assert "tiktok" in verdict["per_platform"]
    assert verdict["ypp_score"] >= 70
    assert verdict["phash_signature"]
    assert "green_seal_15s" in verdict["gates"]
    assert len(verdict["auto_fixes_applied"]) >= 1  # censurou "porra" nos 15s + limpou copy TikTok

    # Confirma persistência em `clips`
    updated = db.fetch_one("SELECT risk_status, ypp_transform_score, phash_signature FROM clips WHERE id = ?", (clip["id"],))
    assert updated is not None
    assert updated["risk_status"] in {"pass", "auto_fixed"}
    assert updated["ypp_transform_score"] >= 70
    assert updated["phash_signature"] == verdict["phash_signature"]


def test_mcp_and_dashboard_expose_risk_audit_cooldown_and_pause_source(tmp_path: Path, monkeypatch):
    import dashboard
    from picorte.mcp.server import PicorteMCPServer
    from picorte.risk_shield.policy_gate import sync_publisher_policies

    db = _make_db(tmp_path)
    sync_publisher_policies(db)
    monkeypatch.setattr("picorte.db.connection.get_default_db", lambda: db)
    monkeypatch.setattr("picorte.services.studio_service.get_default_db", lambda: db)
    cd_file = tmp_path / "cadence_state.json"
    monkeypatch.setattr("picorte.risk_shield.cadence_guard.DEFAULT_CADENCE_STATE_PATH", cd_file)

    repos = PicorteRepositories(db)
    src = repos.sources.create_source(
        name="ALANZOKA", platform="youtube", channel_handle="@alanzoka", permission_status="liberada"
    )

    # 1) MCP tools do Épico 4
    mcp = PicorteMCPServer(db=db)
    tool_names = {t["name"] for t in mcp.list_tools()}
    assert {"picorte_auditar_risco", "picorte_politicas_jogo", "picorte_pausar_fonte"}.issubset(tool_names)

    pol = mcp.call_tool("picorte_politicas_jogo", {"game_slug": "gta6"})
    assert pol["policy"]["publisher"] == "Rockstar Games"

    paused = mcp.call_tool(
        "picorte_pausar_fonte",
        {"source_id": src["id"], "claim_type": "manual_test", "details": "Teste disjuntor MCP"},
    )
    assert paused["source_status"] == "pausada_por_claim"

    # 2) Dashboard endpoints de Cool-Down 48h
    root = tmp_path / "projects"
    root.mkdir()
    server = dashboard.make_server(root, 0)
    port = server.server_port
    token = server.app.token
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://127.0.0.1:{port}"
        req = urllib.request.Request(
            f"{base}/api/risk/cooldown",
            data=json.dumps({"platform": "tiktok", "hours": 48, "reason": "Recuperacao spam"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Chopify-Token": token},
            method="POST",
        )
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read().decode("utf-8"))
        assert res["ok"] is True
        assert res["cooldown"]["cooldown_active"] is True

        with urllib.request.urlopen(f"{base}/api/risk/cooldown") as r:
            st = json.loads(r.read().decode("utf-8"))
        assert "tiktok" in st["cooldowns"]
    finally:
        server.shutdown()
        server.server_close()
