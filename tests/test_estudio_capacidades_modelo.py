import pytest

from picorte.capacidades.modelo import Capacidade
from picorte.capacidades.sondas import CacheSondas, ResultadoSonda


def _cap(**kw):
    base = dict(id="X-1", area="sistema", titulo="Teste", status="ligado", tipo_motivo=None,
                motivo="", falta=(), fonte_dado="teste", origem={"epico": "6", "historia": "6.3"},
                escopo="global")
    return Capacidade(**{**base, **kw})


def test_travado_nunca_sai_com_dados():
    cap = _cap(status="travado", tipo_motivo="codigo", motivo="falta código",
               dados={"total": 42})
    assert cap.para_json()["dados"] is None


def test_ligado_mantem_dados_e_listas_viram_listas():
    j = _cap(dados={"vram_mib": 8188}, falta=("a",), depende_de=("SIS-1",)).para_json()
    assert j["dados"] == {"vram_mib": 8188}
    assert j["falta"] == ["a"] and j["depende_de"] == ["SIS-1"]
    assert set(j) == {"id", "area", "titulo", "status", "tipo_motivo", "motivo", "falta",
                      "fonte_dado", "origem", "escopo", "depende_de", "verificado_em",
                      "ligou_em", "dados"}


@pytest.mark.parametrize("campo,valor", [("status", "quase"), ("tipo_motivo", "preguica"),
                                          ("escopo", "universo")])
def test_valores_fora_do_contrato_sao_recusados(campo, valor):
    with pytest.raises(ValueError):
        _cap(**{campo: valor, **({"tipo_motivo": "codigo"} if campo == "status" else {})})


def test_travado_e_parcial_exigem_tipo_motivo():
    with pytest.raises(ValueError):
        _cap(status="travado", tipo_motivo=None)
    with pytest.raises(ValueError):
        _cap(status="parcial", tipo_motivo=None)


def test_cache_respeita_ttl():
    agora = [100.0]
    chamadas = []

    def sonda():
        chamadas.append(1)
        return ResultadoSonda(True, "ok")

    cache = CacheSondas({"s": (30.0, sonda)}, relogio=lambda: agora[0])
    cache.obter("s")
    agora[0] = 120.0
    cache.obter("s")
    assert len(chamadas) == 1
    agora[0] = 131.0
    cache.obter("s")
    assert len(chamadas) == 2


def test_sonda_que_explode_vira_resultado_falho():
    def quebra():
        raise RuntimeError("bum")

    r = CacheSondas({"s": (1.0, quebra)}).obter("s")
    assert r.ok is False and "bum" in r.detalhe
