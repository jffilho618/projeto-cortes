import pytest

from picorte.risk_shield.policy_gate import PolicyViolationError
from picorte.services.sala import abrir_sala, validar_link

META = {"title": "GTA 6 É AGORA", "channel": "Davy Jones", "channel_url": "https://www.youtube.com/@Gameplayrj",
        "duration": 40815, "thumbnail": "https://i.ytimg.com/vi/x50ONQrBPRM/maxresdefault.jpg",
        "live_status": "was_live", "formats": [{"x": 1}]}


def test_validar_link():
    assert validar_link(" https://www.youtube.com/watch?v=x50ONQrBPRM ") == "https://www.youtube.com/watch?v=x50ONQrBPRM"
    assert validar_link("https://www.twitch.tv/videos/123456789")
    assert validar_link("https://kick.com/video/abc-123")
    for ruim in ["", "oi", "https://example.com/watch?v=x", "file:///C:/a.mp4"]:
        with pytest.raises(ValueError, match="não parece um link de vídeo"):
            validar_link(ruim)


def test_sala_liberada_com_metadados_e_projeto_existente():
    visto = {}

    def portao(db, *, source_input, meta, owner=None):
        visto.update(source_input=source_input, meta=meta)
        return {"allowed": True, "source_name": "DAVY JONES", "permission_basis": "tolerancia_publica"}

    r = abrir_sala("https://www.youtube.com/watch?v=x50ONQrBPRM", db=None, sondar=lambda u: dict(META), portao=portao,
                   projetos=[{"id": "p1", "source": "https://youtu.be/x50ONQrBPRM", "status": "review", "stage": "x"}])
    assert r["video"]["titulo"] == "GTA 6 É AGORA" and r["video"]["duracao_s"] == 40815
    assert r["video"]["id_youtube"] == "x50ONQrBPRM" and r["video"]["plataforma"] == "youtube"
    assert r["video"]["ao_vivo"] is False
    assert r["portao"] == {"liberado": True, "fonte": "DAVY JONES", "base": "tolerancia_publica"}
    assert r["projeto"] == {"id": "p1", "status": "review", "stage": "x"}
    assert "formats" not in visto["meta"]  # a mesma régua do preparo, sem a lista de formatos


def test_sala_barrada_diz_o_motivo_e_nada_e_baixado():
    def barra(db, **kw):
        raise PolicyViolationError("[P1:pre_ingest] Fonte desconhecida: 'X'. Nada foi baixado.", code="source_unknown")

    r = abrir_sala("https://www.youtube.com/watch?v=x50ONQrBPRM", db=None, sondar=lambda u: dict(META),
                   portao=barra, projetos=[])
    assert r["portao"] == {"liberado": False, "codigo": "source_unknown",
                           "motivo": "[P1:pre_ingest] Fonte desconhecida: 'X'. Nada foi baixado."}
    assert r["projeto"] is None


def test_metadados_indisponiveis_viram_erro_legivel():
    def falha(url):
        raise RuntimeError("yt-dlp: HTTP Error 404")

    with pytest.raises(ValueError, match="Não consegui ler este vídeo"):
        abrir_sala("https://www.youtube.com/watch?v=x50ONQrBPRM", db=None, sondar=falha, portao=None, projetos=[])
