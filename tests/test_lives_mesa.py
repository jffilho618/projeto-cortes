from picorte.services.mesa import na_sua_mesa


def test_mesa_a_partir_dos_projetos_reais():
    projetos = [
        {"id": "a", "status": "review"}, {"id": "b", "status": "review"},
        {"id": "c", "status": "running", "stage": "render 4/17"}, {"id": "d", "status": "queued"},
        {"id": "e", "status": "failed", "error": "[P1:pre_ingest] Fonte desconhecida: 'BisteconeLive' não está entre os streamers cadastrados. Nada foi baixado."},
        {"id": "f", "status": "failed", "error": "lote 1/2 falhou 2x: CalledProcessError: Command '['agy.exe'"},
        {"id": "g", "status": "interrupted"}, {"id": "h", "status": "complete"},
    ]
    m = na_sua_mesa(projetos)
    assert m["revisar"] == 2
    assert m["na_fila"] == {"n": 2, "estagio": "render 4/17"}
    assert m["pede_voce"] == [{"projeto": "e", "motivo": projetos[4]["error"]}]
    falhas = {f["projeto"]: f for f in m["falhas"]}
    assert set(falhas) == {"f", "g"}
    assert falhas["f"]["proximo_passo"] == "Trocar o motor de IA e retomar"
    assert falhas["g"]["proximo_passo"] == "Retomar"


def test_links_pendentes_vem_do_banco_e_sem_banco_fica_nao_medido():
    assert na_sua_mesa([], links_pendentes=3)["links_pendentes"] == 3
    m = na_sua_mesa([])
    assert m["links_pendentes"] is None and "banco" in m["links_pendentes_motivo"]
    assert m["revisar"] == 0 and m["pede_voce"] == [] and m["na_fila"] == {"n": 0, "estagio": None}
