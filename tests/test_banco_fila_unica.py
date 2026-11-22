import pytest
from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades
from picorte.services.estudio_conexao import (EstudioDesligado, apagar_conexao, enfileirar_no_estudio,
                                              gravar_conexao, ler_conexao)
from picorte.services.fila import FilaEstudio


def test_conexao_grava_le_e_apaga(tmp_path):
    arq = tmp_path / ".picorte" / "estudio.json"
    gravar_conexao(8770, "segredo", arquivo=arq)
    assert ler_conexao(arquivo=arq)["porta"] == 8770
    apagar_conexao(arquivo=arq)
    assert ler_conexao(arquivo=arq) is None


def test_sem_estudio_aberto_avisa_e_nao_cria_nada(tmp_path):
    with pytest.raises(EstudioDesligado, match="python estudio.py"):
        enfileirar_no_estudio(["https://www.youtube.com/watch?v=x"], arquivo=tmp_path / "nada.json")


def test_mcp_usa_a_mesma_rota_do_painel(tmp_path):
    raiz = tmp_path / "projects"
    chamadas = []
    fila = FilaEstudio(raiz, executar=lambda p, a, pr, pk: chamadas.append((p.name, a)) or 0)
    app = create_app(raiz, token="tok", dist=tmp_path / "d", fila=fila,
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()))
    arq = tmp_path / "estudio.json"
    gravar_conexao(8770, "tok", arquivo=arq)
    with TestClient(app) as cliente:
        r = enfileirar_no_estudio(["https://www.youtube.com/watch?v=x"], arquivo=arq, post=cliente.post)
        pid = r["projetos"][0]["id"]
        fila._futuros[pid].result(timeout=5)
    assert chamadas == [(pid, "prepare")]
    assert (raiz / pid / "project.json").is_file()


def test_erro_do_estudio_vira_mensagem_legivel(tmp_path):
    arq = tmp_path / "estudio.json"
    gravar_conexao(8770, "tok", arquivo=arq)

    class Resposta:
        status_code = 400
        content = b'{"erro":"Envie de 1 a 100 fontes."}'

        def json(self):
            return {"erro": "Envie de 1 a 100 fontes."}

    with pytest.raises(ValueError, match="Envie de 1 a 100 fontes."):
        enfileirar_no_estudio([], arquivo=arq, post=lambda *a, **k: Resposta())


def test_arquivo_velho_de_estudio_fechado_a_forca_vira_aviso(tmp_path):
    import socket
    with socket.socket() as s:  # porta livre agora e sem ninguém escutando depois
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    arq = tmp_path / "estudio.json"
    gravar_conexao(porta, "tok", arquivo=arq)
    with pytest.raises(EstudioDesligado, match="python estudio.py"):
        enfileirar_no_estudio(["https://www.youtube.com/watch?v=x"], arquivo=arq)
