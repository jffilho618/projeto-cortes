import subprocess
import sys
import threading

import pytest

import projects
from picorte.services.eventos import Barramento, formatar_sse
from picorte.services.fila import FilaEstudio
from picorte.services.job_lock import ProjetoOcupado

PID = "abcdef123456"
SEGURAR = ("import sys, time\nfrom filelock import FileLock\n"
           "l = FileLock(sys.argv[1]); l.acquire(); print('ok', flush=True); time.sleep(60)")


def _projeto(raiz, status="new", pid=PID):
    path = raiz / pid
    path.mkdir(parents=True)
    projects.atomic_json(path / "project.json", {
        "id": pid, "source": "x.mp4", "options": {}, "status": status, "stage": "waiting",
        "created": 1.0, "updated": 1.0, "cache": {}, "renders": {}, "error": None})
    return path


def _eventos(q):
    itens = []
    while not q.empty():
        itens.append(q.get_nowait())
    return itens


def test_formatar_sse():
    assert formatar_sse("job", {"a": "ç"}) == 'event: job\ndata: {"a": "ç"}\n\n'


def test_abrir_e_listar_nao_escreve_project_json(tmp_path):
    path = _projeto(tmp_path, status="running")
    antes = (path / "project.json").read_bytes()
    fila = FilaEstudio(tmp_path)
    [item] = fila.listar()
    assert (path / "project.json").read_bytes() == antes
    assert item["status"] == "interrupted"
    assert item["status_gravado"] == "running"
    fila.fechar()


def test_job_vivo_em_outro_processo_continua_rodando(tmp_path):
    path = _projeto(tmp_path, status="running")
    p = subprocess.Popen([sys.executable, "-c", SEGURAR, str(path / ".job.lock")],
                         stdout=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == "ok"
        fila = FilaEstudio(tmp_path)
        assert fila.listar()[0]["status"] == "running"
        assert fila.ocupado(PID) is True
        fila.fechar()
    finally:
        p.kill()
        p.wait()


def test_enfileirar_roda_e_publica_eventos(tmp_path):
    _projeto(tmp_path)
    chamadas = []
    bus = Barramento()
    q = bus.assinar()
    fila = FilaEstudio(tmp_path, barramento=bus,
                       executar=lambda path, acao, preview, pick: chamadas.append((path.name, acao)) or 0)
    fila.enfileirar(PID, "prepare")
    fila._futuros[PID].result(timeout=5)
    assert chamadas == [(PID, "prepare")]
    fases = [d["fase"] for t, d in _eventos(q) if t == "job"]
    assert fases == ["na_fila", "inicio", "fim"]
    fila.fechar()


def test_falha_do_job_marca_failed(tmp_path):
    path = _projeto(tmp_path)
    fila = FilaEstudio(tmp_path, executar=lambda *a: 2)
    fila.enfileirar(PID, "render")
    fila._futuros[PID].result(timeout=5)
    estado = projects.read_project(path)
    assert estado["status"] == "failed"
    assert estado["error"]
    fila.fechar()


def test_enfileirar_duas_vezes_e_recusado(tmp_path):
    _projeto(tmp_path)
    solta = threading.Event()
    fila = FilaEstudio(tmp_path, executar=lambda *a: solta.wait(5) and 0)
    fila.enfileirar(PID, "prepare")
    with pytest.raises(ProjetoOcupado):
        fila.enfileirar(PID, "prepare")
    solta.set()
    fila._futuros[PID].result(timeout=5)
    fila.fechar()


def test_acao_e_selecao_invalidas(tmp_path):
    _projeto(tmp_path)
    fila = FilaEstudio(tmp_path, executar=lambda *a: 0)
    with pytest.raises(ValueError):
        fila.enfileirar(PID, "apagar")
    with pytest.raises(ValueError):
        fila.enfileirar(PID, "render", pick="1;rm")
    fila.fechar()


def test_acao_pedida_fica_no_projeto_e_sobrevive_a_falha(tmp_path):
    """Live do Paulinho (2026-11-23): criado com "all", o Editor parou no limite do Claude; ao trocar o motor, o
    painel reenfileirava "prepare" e nada era renderizado. A ação pedida precisa ficar salva no projeto."""
    from picorte.services.revisao import linha_da_fila

    path = _projeto(tmp_path)
    fila = FilaEstudio(tmp_path, executar=lambda *a: (_ for _ in ()).throw(RuntimeError("[Editor-Chefe] limite do Claude")))
    fila.enfileirar(PID, "all")
    fila._futuros[PID].result(timeout=5)
    estado = projects.read_project(path)
    assert estado["status"] == "failed" and estado["acao_pedida"] == "all"
    assert linha_da_fila(estado)["acao"] == "all"
    fila.fechar()


def test_projeto_antigo_sem_acao_pedida_retoma_com_prepare(tmp_path):
    from picorte.services.revisao import linha_da_fila

    assert linha_da_fila({"id": "x", "status": "failed"})["acao"] == "prepare"
