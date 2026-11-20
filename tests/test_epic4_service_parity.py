"""P12 (code review Épico 4) — AD-10: painel web e MCP acessam o RiskShield só pelo StudioService (mesma regra)."""
from __future__ import annotations

from pathlib import Path

import pytest

from picorte.db.connection import Database

ROOT = Path(__file__).resolve().parents[1]


def _service(tmp_path: Path):
    from picorte.services.studio_service import StudioService

    db = Database(f"sqlite:///{(tmp_path / 'p12.db').as_posix()}")
    db.init_schema()
    return StudioService(db)


@pytest.mark.parametrize("rel", ["dashboard.py", "picorte/mcp/server.py"])
def test_entrypoints_do_not_import_risk_shield_directly(rel):
    assert "picorte.risk_shield" not in (ROOT / rel).read_text(encoding="utf-8")


def test_service_cooldown_roundtrip(tmp_path: Path):
    svc = _service(tmp_path)
    state = tmp_path / "cad.json"
    svc.risk_set_cooldown("tiktok", hours=2, reason="teste", state_path=state)
    assert "tiktok" in svc.risk_cooldown_status(state_path=state)
    svc.risk_clear_cooldown("tiktok", state_path=state)
    assert svc.risk_cooldown_status(state_path=state) == {}


def test_service_rejects_unknown_platform(tmp_path: Path):
    with pytest.raises(ValueError):
        _service(tmp_path).risk_set_cooldown("orkut", state_path=tmp_path / "cad.json")


def test_service_pause_source_and_audit(tmp_path: Path):
    svc = _service(tmp_path)
    src = svc.create_source(name="S", platform="twitch", channel_handle="@s", permission_status="liberada")
    res = svc.risk_pause_source(src["id"], claim_type="manual_emergency", reason="teste")
    assert res["source_status"] == "pausada_emergencia"
    verdict = svc.risk_audit_clip(source_id=src["id"], title="corte")
    assert verdict["overall_status"] == "hard_block"


def test_service_game_policy(tmp_path: Path):
    pol = _service(tmp_path).risk_game_policy("gta6")
    assert pol["policy"]["publisher"] == "Rockstar Games"
