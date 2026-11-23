"""Code review do motor — fatia (d) P1 (2026-11-23): nenhuma entrada baixa fonte sem passar pelo portão."""
from __future__ import annotations

import sys

import pytest


def test_download_pela_linha_de_comando_passa_pelo_portao_p1(monkeypatch, tmp_path):
    import download_and_transcribe as dt
    import ingest
    from picorte.risk_shield import source_resolver
    from picorte.risk_shield.policy_gate import PolicyViolationError

    def nao_baixa(*a, **k):
        raise AssertionError("baixou antes do portão P1")

    def portao(db, *, source_input, meta, owner=None, registry_path=None):
        raise PolicyViolationError("[P1:pre_ingest] Fonte desconhecida", code="source_unknown")

    monkeypatch.setattr(dt, "resolve_source", nao_baixa)
    monkeypatch.setattr(ingest, "probe_source", lambda url: {"channel": "canal estranho"})
    monkeypatch.setattr(source_resolver, "gate_project_source", portao)
    monkeypatch.setattr(sys, "argv", ["download_and_transcribe.py", "https://www.youtube.com/watch?v=x",
                                      "--workdir", str(tmp_path)])
    with pytest.raises(PolicyViolationError):
        dt.main()
