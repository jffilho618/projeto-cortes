import subprocess
import sys
from pathlib import Path

import pytest

from picorte.services.job_lock import ProjetoOcupado, job_ativo, segurar_job

SEGURAR = ("import sys, time\nfrom filelock import FileLock\n"
           "l = FileLock(sys.argv[1]); l.acquire(); print('ok', flush=True); time.sleep(60)")


def _outro_processo_segura(arquivo):
    p = subprocess.Popen([sys.executable, "-c", SEGURAR, str(arquivo)],
                         stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "ok"
    return p


def test_sem_lock_nao_ha_job(tmp_path):
    assert job_ativo(tmp_path) is False


def test_job_ativo_nao_cria_arquivo(tmp_path):
    job_ativo(tmp_path)
    assert not (tmp_path / ".job.lock").exists()


def test_lock_de_outro_processo_conta_como_job_ativo(tmp_path):
    p = _outro_processo_segura(tmp_path / ".job.lock")
    try:
        assert job_ativo(tmp_path) is True
        with pytest.raises(ProjetoOcupado):
            with segurar_job(tmp_path, espera=0.2):
                pass
    finally:
        p.kill()
        p.wait()
    assert job_ativo(tmp_path) is False


def test_segurar_job_libera_ao_sair(tmp_path):
    with segurar_job(tmp_path):
        pass
    assert job_ativo(tmp_path) is False


def test_run_project_segura_o_lock_durante_o_job(tmp_path, monkeypatch):
    import projects
    visto = {}

    def falso(path, action="all", preview=False, pick=None, resume=True, progress=None):
        visto["ativo"] = job_ativo(tmp_path)
        return {"ok": True}

    monkeypatch.setattr(projects, "_run_project", falso)
    assert projects.run_project(tmp_path, action="prepare") == {"ok": True}
    assert visto["ativo"] is True
    assert job_ativo(tmp_path) is False


def test_espelho_do_motor_continua_identico():
    raiz = Path(__file__).resolve().parents[1]
    assert (raiz / "projects.py").read_bytes() == (raiz / "picorte/engine/projects.py").read_bytes()
