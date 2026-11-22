import json

import pytest

from picorte.services.vitrine import (CacheVitrine, id_do_video, indice_projetos, listar_canal,
                                      normalizar_entrada)

ENTRADA = {"id": "q4ekFpRjgKQ", "title": "EMBOSCADOS! - GRAND THEFT AUTO 6 - Parte 6", "duration": 8087,
           "timestamp": 1795276800, "view_count": 287000, "live_status": None}


def test_normaliza_uma_entrada_real_do_ytdlp():
    v = normalizar_entrada(ENTRADA)
    assert v == {"id": "q4ekFpRjgKQ", "url": "https://www.youtube.com/watch?v=q4ekFpRjgKQ",
                 "titulo": "EMBOSCADOS! - GRAND THEFT AUTO 6 - Parte 6", "duracao_s": 8087,
                 "publicado_em": "2026-11-21T16:00:00+00:00", "visualizacoes": 287000,
                 "thumb": "https://i.ytimg.com/vi/q4ekFpRjgKQ/hqdefault.jpg", "era_live": False}


def test_live_em_curso_ou_agendada_fica_de_fora_sem_api_oficial():
    assert normalizar_entrada({**ENTRADA, "live_status": "is_live"}) is None
    assert normalizar_entrada({**ENTRADA, "live_status": "is_upcoming"}) is None
    assert normalizar_entrada({"title": "sem id"}) is None


def test_campos_ausentes_ficam_none_nunca_zero():
    v = normalizar_entrada({"id": "abc12345678", "title": "x"})
    assert v["duracao_s"] is None and v["visualizacoes"] is None and v["publicado_em"] is None


def test_listar_canal_junta_abas_sem_duplicar_e_ordena():
    abas = {
        "https://www.youtube.com/@x/videos": {"entries": [ENTRADA, {**ENTRADA, "id": "velho000000", "timestamp": 1700000000}]},
        "https://www.youtube.com/@x/streams": {"entries": [{**ENTRADA, "live_status": "was_live"},
                                                          {**ENTRADA, "id": "novo0000000", "timestamp": 1795300000}]},
    }
    vids = listar_canal("https://www.youtube.com/@x", limite=3, rodar=lambda url, limite: abas.get(url))
    assert [v["id"] for v in vids] == ["novo0000000", "q4ekFpRjgKQ", "velho000000"]


def test_listar_canal_falha_quando_nenhuma_aba_responde():
    with pytest.raises(RuntimeError):
        listar_canal("https://www.youtube.com/@x", rodar=lambda url, limite: None)


def test_cache_respeita_prazo_e_usa_o_velho_quando_a_busca_falha(tmp_path):
    agora = [1_000_000.0]
    cache = CacheVitrine(tmp_path / "v.json", prazo_s=100, relogio=lambda: agora[0])
    chamadas = []
    buscar = lambda: chamadas.append(1) or [normalizar_entrada(ENTRADA)]  # noqa: E731
    assert cache.obter("alanzoka", buscar)["desatualizado"] is False
    cache.obter("alanzoka", buscar)
    assert len(chamadas) == 1  # dentro do prazo: não busca de novo
    agora[0] += 200

    def falha():
        raise RuntimeError("rede")

    r = cache.obter("alanzoka", falha)
    assert r["desatualizado"] is True and r["videos"][0]["id"] == "q4ekFpRjgKQ"


def test_cache_nunca_guarda_mais_de_30_dias(tmp_path):
    agora = [1_000_000.0]
    arq = tmp_path / "v.json"
    cache = CacheVitrine(arq, prazo_s=100, maximo_s=1000, relogio=lambda: agora[0])
    cache.obter("a", lambda: [normalizar_entrada(ENTRADA)])
    agora[0] += 2000
    cache.obter("b", lambda: [])
    assert "a" not in json.loads(arq.read_text(encoding="utf-8"))


def test_cache_sem_dado_e_busca_falhando_levanta(tmp_path):
    cache = CacheVitrine(tmp_path / "v.json")
    with pytest.raises(RuntimeError):
        cache.obter("x", lambda: (_ for _ in ()).throw(RuntimeError("rede")))


def test_id_do_video_e_indice_de_projetos():
    assert id_do_video("https://www.youtube.com/watch?v=q4ekFpRjgKQ&t=10") == "q4ekFpRjgKQ"
    assert id_do_video("https://youtu.be/q4ekFpRjgKQ") == "q4ekFpRjgKQ"
    assert id_do_video("https://www.youtube.com/live/q4ekFpRjgKQ") == "q4ekFpRjgKQ"
    assert id_do_video("C:/videos/meu.mp4") is None
    ind = indice_projetos([{"id": "p1", "source": "https://youtu.be/q4ekFpRjgKQ", "status": "review", "stage": "x"},
                           {"id": "p2", "source": "C:/a.mp4", "status": "complete"}])
    assert ind == {"q4ekFpRjgKQ": {"id": "p1", "status": "review", "stage": "x"}}


def test_canal_sem_abas_ou_inexistente_e_problema_de_cadastro_nao_de_rede():
    from picorte.services.vitrine import CanalSemVideos
    with pytest.raises(CanalSemVideos, match="Confira o canal no cadastro"):
        listar_canal("https://www.youtube.com/@x", rodar=lambda url, limite: {"_falha": "sem_aba"})
    with pytest.raises(RuntimeError) as exc:
        listar_canal("https://www.youtube.com/@x", rodar=lambda url, limite: {"_falha": "rede"})
    assert not isinstance(exc.value, CanalSemVideos)


def test_classificar_falha_do_ytdlp():
    from picorte.services.vitrine import classificar_falha
    assert classificar_falha("ERROR: [youtube:tab] @bistecone: This channel does not have a videos tab") == "sem_aba"
    assert classificar_falha("WARNING: ... HTTP Error 404: Not Found ... Giving up after 3 retries") == "sem_aba"
    assert classificar_falha("ERROR: Unable to download API page: <urlopen error timed out>") == "rede"
