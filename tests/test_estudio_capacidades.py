import re

from estudio_fakes import QUANDO, _fixa, cache_falso
from picorte.capacidades import ServicoCapacidades, listar_capacidades
from picorte.capacidades.catalogo import catalogo
from picorte.capacidades.sondas import CacheSondas, ResultadoSonda
from picorte.services.eventos import Barramento


def _por_id(dados):
    return {c["id"]: c for c in dados["capacidades"]}


def test_catalogo_cobre_o_mapa_inteiro():
    ids = [c.id for c in catalogo()]
    assert len(ids) == len(set(ids)) == 82
    for prefixo, n in {"SIS": 14, "FIL": 7, "REV": 15, "FON": 9, "ESC": 9, "SAU": 5,
                       "PUB": 6, "MET": 6, "RAD": 5, "LIV": 6}.items():
        assert sum(1 for i in ids if i.startswith(prefixo + "-")) == n, prefixo


def test_cada_capacidade_tem_origem_e_fonte():
    for c in catalogo():
        assert c.origem.get("epico") and c.fonte_dado and c.titulo, c.id
        assert re.fullmatch(r"[A-Z]{3}-\d+", c.id)


def test_areas_inteiras_travadas_continuam_travadas(tmp_path):
    caps = _por_id(listar_capacidades(tmp_path, cache_falso()))
    for i in ["MET-1", "MET-3", "RAD-1", "RAD-2", "PUB-5", "PUB-6", "LIV-1", "LIV-3"]:
        assert caps[i]["status"] == "travado", i
        assert caps[i]["dados"] is None


def test_fila_ganhou_o_lock_e_ficou_ligada(tmp_path):
    assert _por_id(listar_capacidades(tmp_path, cache_falso()))["SIS-2"]["status"] == "ligado"


def test_ollama_fora_do_ar_trava_por_config(tmp_path):
    cache = cache_falso(ollama=_fixa(False, "Ollama não respondeu", host="http://localhost:11434"))
    sis6 = _por_id(listar_capacidades(tmp_path, cache))["SIS-6"]
    assert sis6["status"] == "travado" and sis6["tipo_motivo"] == "config"
    assert sis6["dados"] is None and sis6["verificado_em"] == QUANDO


def test_ollama_no_ar_mostra_modelos(tmp_path):
    sis6 = _por_id(listar_capacidades(tmp_path, cache_falso()))["SIS-6"]
    assert sis6["status"] == "ligado" and sis6["dados"]["modelos"] == ["qwen3.5:9b"]


def test_gemini_com_429_fica_parcial_temporario(tmp_path):
    cache = cache_falso(agy=_fixa(False, "cota", presente=True, ultima_falha=QUANDO))
    sis7 = _por_id(listar_capacidades(tmp_path, cache))["SIS-7"]
    assert (sis7["status"], sis7["tipo_motivo"]) == ("parcial", "temporario")


def test_ytdlp_ausente_trava_e_demucs_ausente_e_parcial(tmp_path):
    caps = _por_id(listar_capacidades(tmp_path, cache_falso(**{"yt-dlp": _fixa(False)})))
    assert caps["SIS-11"]["status"] == "travado"
    caps = _por_id(listar_capacidades(tmp_path, cache_falso(demucs=_fixa(False))))
    assert caps["SIS-11"]["status"] == "parcial" and "demucs" in caps["SIS-11"]["motivo"]


def test_resumo_conta_os_status(tmp_path):
    dados = listar_capacidades(tmp_path, cache_falso())
    assert sum(dados["resumo"].values()) == 82


def test_servico_publica_evento_quando_status_muda(tmp_path):
    estado = {"ok": True}
    cache = CacheSondas({**{k: (0.0, v) for k, v in {
        "gpu": _fixa(True, gpu_name="g", vram_mib=1), "agy": _fixa(True, presente=True, ultima_falha=None),
        "claude": _fixa(True), "yt-dlp": _fixa(True), "node": _fixa(True), "demucs": _fixa(True),
        "disco": _fixa(True, livre_gib=99.0)}.items()},
        "ollama": (0.0, lambda: ResultadoSonda(estado["ok"], "", {"modelos": ["m"]}, QUANDO))})
    bus = Barramento()
    q = bus.assinar()
    servico = ServicoCapacidades(tmp_path, cache=cache, barramento=bus)
    servico.atual()
    assert q.empty()
    estado["ok"] = False
    servico.atual()
    tipo, dados = q.get_nowait()
    assert tipo == "capacidades"
    assert {"id": "SIS-6", "de": "ligado", "para": "travado"} in dados["mudaram"]


def test_historia_6_4_ligou_o_banco_o_mcp_e_os_sinais(tmp_path):
    caps = _por_id(listar_capacidades(tmp_path, cache_falso()))
    for i in ["SIS-5", "SIS-12", "REV-2", "FON-4", "FON-5"]:
        assert caps[i]["status"] == "ligado", i
        assert caps[i]["ligou_em"] == "2026-11-22", i
    for i in ["ESC-1", "ESC-5"]:
        assert caps[i]["status"] == "parcial" and "B3" not in caps[i]["motivo"], i


def test_historia_6_5_ligou_a_sala_e_recentes_e_parcial(tmp_path):
    caps = _por_id(listar_capacidades(tmp_path, cache_falso()))
    assert caps["LIV-5"]["status"] == "ligado" and caps["LIV-5"]["ligou_em"] == "2026-11-22"
    assert (caps["LIV-4"]["status"], caps["LIV-4"]["tipo_motivo"]) == ("parcial", "config")
    for i in ["LIV-1", "LIV-2", "LIV-3", "LIV-6"]:
        assert caps[i]["status"] == "travado", i
