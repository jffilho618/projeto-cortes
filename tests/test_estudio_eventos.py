import threading
import time

from fastapi.testclient import TestClient

from estudio_fakes import cache_falso
from picorte.api import create_app
from picorte.capacidades import ServicoCapacidades


def test_fluxo_comeca_com_ola_e_entrega_eventos_do_barramento(tmp_path):
    raiz = tmp_path / "projects"
    app = create_app(raiz, hosts=("testserver",), token="t", dist=tmp_path / "d",
                     capacidades=ServicoCapacidades(raiz, cache=cache_falso()))
    bus = app.state.barramento

    def publicar_depois():
        time.sleep(0.5)
        bus.publicar("job", {"projeto": "abcdef123456", "fase": "inicio"})

    threading.Thread(target=publicar_depois, daemon=True).start()
    with TestClient(app).stream("GET", "/api/eventos?max_eventos=2") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        corpo = "".join(r.iter_text())
    assert corpo.startswith("retry: 3000\n\nevent: ola\n")
    assert 'event: job\ndata: {"projeto": "abcdef123456", "fase": "inicio"}' in corpo
