import json

import pytest

from picorte.db.connection import Database
from picorte.services.decisoes import (MOTIVOS_RUIM, gravar_descarte, gravar_rotulo, ler_decisoes,
                                       salvar_exemplo_ouro)


@pytest.fixture
def db(tmp_path):
    banco = Database(f"sqlite:///{tmp_path / 'd.db'}")
    banco.init_schema()
    return banco


def test_rotulo_e_opcional_e_tem_motivo_de_um_clique(db):
    assert ler_decisoes(db, "p1") == {}
    gravar_rotulo(db, "p1", "003", -1, "borda errada")
    gravar_rotulo(db, "p1", "001", 1)
    d = ler_decisoes(db, "p1")
    assert d["003"] == {"rotulo": -1, "motivo": "borda errada", "descartado": False, "exemplo_ouro": False}
    assert d["001"]["rotulo"] == 1 and d["001"]["motivo"] == ""
    gravar_rotulo(db, "p1", "003", 0)  # tirar o rótulo
    assert ler_decisoes(db, "p1")["003"]["rotulo"] is None
    assert "borda errada" in MOTIVOS_RUIM


def test_rotulo_invalido_e_recusado(db):
    with pytest.raises(ValueError):
        gravar_rotulo(db, "p1", "001", 5)
    with pytest.raises(ValueError):
        gravar_rotulo(db, "p1", "001", -1, "qualquer coisa")
    with pytest.raises(ValueError):
        gravar_rotulo(db, "p1", "../x", 1)


def test_descartar_e_separado_do_rotulo_e_tem_desfazer(db):
    gravar_rotulo(db, "p1", "002", -1, "momento fraco")
    gravar_descarte(db, "p1", "002", True)
    assert ler_decisoes(db, "p1")["002"] == {"rotulo": -1, "motivo": "momento fraco", "descartado": True, "exemplo_ouro": False}
    gravar_descarte(db, "p1", "002", False)
    assert ler_decisoes(db, "p1")["002"]["descartado"] is False
    assert ler_decisoes(db, "p2") == {}


def test_exemplo_ouro_vai_para_a_biblioteca_sem_duplicar(db, tmp_path):
    pasta = tmp_path / "p1"
    pasta.mkdir()
    (pasta / "segments.json").write_text(json.dumps([
        {"start": 10, "end": 40, "proposed_title": "Callback do trailer", "archetype": "callback_oculto", "tier": "ouro",
         "why_extraordinary": "testa detalhe do trailer", "context_banner_2s": "No trailer era diferente"}]), encoding="utf-8")
    biblioteca = tmp_path / "golden_examples.json"
    biblioteca.write_text(json.dumps({"version": 1, "examples": [{"id": "ja-existia", "tier": "ouro"}]}), encoding="utf-8")
    estado = {"id": "p1", "source": "https://youtu.be/q4ekFpRjgKQ", "source_meta": {"detected_game": "gta6"}}
    for _ in range(2):
        salvar_exemplo_ouro(db, "p1", pasta, estado, "001", arquivo=biblioteca)
    dados = json.loads(biblioteca.read_text(encoding="utf-8"))
    assert [e["id"] for e in dados["examples"]] == ["ja-existia", "p1-001"]
    novo = dados["examples"][1]
    assert novo == {"id": "p1-001", "archetype": "callback_oculto", "tier": "ouro", "game": "gta6",
                    "source_url": "https://youtu.be/q4ekFpRjgKQ", "summary": "Callback do trailer",
                    "why_gold": "testa detalhe do trailer", "ideal_context_banner": "No trailer era diferente",
                    "ideal_duration_bucket": "short"}
    assert ler_decisoes(db, "p1")["001"]["exemplo_ouro"] is True


def test_exemplo_ouro_de_corte_que_nao_existe(db, tmp_path):
    pasta = tmp_path / "p1"
    pasta.mkdir()
    (pasta / "segments.json").write_text("[]", encoding="utf-8")
    with pytest.raises(KeyError):
        salvar_exemplo_ouro(db, "p1", pasta, {"id": "p1"}, "009", arquivo=tmp_path / "g.json")
