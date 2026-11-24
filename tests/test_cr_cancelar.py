"""Cancelar um job pelo painel (pedido do dono, 2026-11-23): o motor para entre as etapas."""
from __future__ import annotations

from pathlib import Path

import pytest


def test_pedido_de_cancelamento_para_na_proxima_etapa(tmp_path: Path):
    import projects

    projects.pedir_cancelamento(tmp_path)
    with pytest.raises(projects.JobCancelado):
        projects._check_cancel(tmp_path)
    assert not (tmp_path / projects.CANCEL_FLAG).exists()  # o pedido é consumido
    projects._check_cancel(tmp_path)  # sem pedido, segue


def test_pedido_antigo_nao_cancela_a_proxima_execucao(tmp_path: Path):
    import projects

    projects.pedir_cancelamento(tmp_path)
    projects._limpar_cancelamento(tmp_path)
    projects._check_cancel(tmp_path)


def test_job_cancelado_termina_como_cancelado_e_nao_como_falha(tmp_path: Path, monkeypatch):
    import projects

    estado = projects.create_project(tmp_path, "https://www.youtube.com/watch?v=x", {})
    pasta = projects.project_path(tmp_path, estado["id"])

    def probe_que_cancela(src):
        projects.pedir_cancelamento(pasta)  # o operador cancela durante a 1ª etapa
        return {"duration": 60.0, "channel": "x"}

    monkeypatch.setattr(projects.ingest, "probe_source", probe_que_cancela)
    monkeypatch.setattr("picorte.risk_shield.source_resolver.gate_project_source",
                        lambda *a, **k: {"allowed": True, "permission_status": "liberada"})
    final = projects.run_project(pasta, action="prepare")
    assert final["status"] == "cancelled"
    assert projects.read_project(pasta)["status"] == "cancelled"
