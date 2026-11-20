"""P11 (code review Épico 4) — Selo P1 no painel: nunca verde sem veredito, selo vermelho, Raio-X e Cool-Down por rede."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEAL_JS = ROOT / "assets" / "studio" / "risk_seal.js"
NODE = shutil.which("node")


def _node(expr: str):
    script = f"const m = require({json.dumps(str(SEAL_JS))}); console.log(JSON.stringify({expr}));"
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js não encontrado")


def test_without_verdict_seal_is_never_green():
    seal = _node('m.riskSeal(null, "tiktok", null)')
    assert seal["cls"] == "risk-none"
    assert "🟢" not in seal["label"]


@pytest.mark.parametrize("status,cls,emoji", [
    ("pass", "risk-pass", "🟢"),
    ("auto_fixed", "risk-fixed", "🟡"),
    ("human_review", "risk-warn", "🟠"),
    ("hard_block", "risk-block", "🔴"),
    ("audit_error", "risk-block", "🔴"),
])
def test_platform_status_maps_to_seal(status, cls, emoji):
    verdict = {"overall_status": "pass", "per_platform": {"tiktok": status}}
    seal = _node(f'm.riskSeal({json.dumps(verdict)}, "tiktok", null)')
    assert seal["cls"] == cls
    assert seal["label"].startswith(emoji)


def test_cooldown_overrides_green_seal():
    verdict = {"overall_status": "pass", "per_platform": {"tiktok": "pass"}}
    seal = _node(f'm.riskSeal({json.dumps(verdict)}, "tiktok", {{"remaining_hours": 12, "reason": "x"}})')
    assert seal["label"].startswith("⏸")


def test_blocked_verdict_wins_over_cooldown():
    verdict = {"overall_status": "hard_block", "per_platform": {"tiktok": "hard_block"}}
    seal = _node(f'm.riskSeal({json.dumps(verdict)}, "tiktok", {{"remaining_hours": 12}})')
    assert seal["cls"] == "risk-block"


def test_xray_lists_each_gate_with_reason_escaped():
    verdict = {"overall_status": "hard_block", "gates": {
        "source_permission": {"status": "hard_block", "reason": "Fonte <pausada>"},
        "green_seal_15s": {"status": "pass"},
    }}
    html = _node(f'm.riskXray({json.dumps(verdict)})')
    assert "source_permission" in html or "Fonte" in html
    assert "&lt;pausada&gt;" in html
    assert "<pausada>" not in html


def test_studio_serves_risk_seal_script_and_index_loads_it():
    import dashboard

    index = (dashboard.STATIC / "index.html").read_text(encoding="utf-8")
    assert '/risk_seal.js' in index
    assert index.index("/risk_seal.js") < index.index("/app.js")


def test_project_detail_exposes_risk_verdict_per_clip(tmp_path: Path):
    import dashboard

    root = tmp_path / "projects"
    pdir = root / "abc123456789"
    (pdir / "clips").mkdir(parents=True)
    (pdir / "project.json").write_text(json.dumps({
        "id": "abc123456789", "created": "2026-11-20T00:00:00Z", "source": "x.mp4", "status": "complete",
        "stage": "complete", "options": {}, "source_meta": {}}), encoding="utf-8")
    (pdir / "clips" / "001-a.mp4").write_bytes(b"mp4")
    (pdir / "clips" / "001-a.meta.json").write_text(json.dumps({
        "risk_status": "human_review", "risk_verdict": {"overall_status": "human_review"}}), encoding="utf-8")
    detail = dashboard.project_detail(root, "abc123456789")
    assert detail["risk_verdicts"]["001-a"]["overall_status"] == "human_review"
