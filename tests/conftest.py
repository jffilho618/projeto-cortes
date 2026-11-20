"""Garante que .venv/bin (Linux) ou .venv/Scripts (Windows) esteja no PATH e isola o banco nos testes."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'picorte_pytest.db'}")

import picorte.config  # noqa: F401, E402


import pytest  # noqa: E402


@pytest.fixture
def allow_p1_source_gate(monkeypatch):
    """Libera o Hard Gate Pre-Ingest (D1) em testes que cobrem OUTRO comportamento do pipeline.

    O portão em si é coberto por tests/test_epic4_source_gate.py (inclusive integrado ao run_project).
    """
    import picorte.risk_shield.source_resolver as sr

    def _allow(db, *, source_input, meta, owner=None, registry_path=None):
        return {"allowed": True, "stage": "pre_ingest", "source_id": None, "channel_handle": None,
                "permission_status": "gameplay_proprio", "permission_basis": "explicita", "owner": owner}

    monkeypatch.setattr(sr, "gate_project_source", _allow)
