import json

from picorte.services.saude import benchmark, matriz_motor


def test_matriz_projeto_por_parte_com_resumo(tmp_path):
    raiz = tmp_path / "projects"
    a = raiz / "aaaaaaaaaaaa"
    a.mkdir(parents=True)
    (a / "engine_health.json").write_text(json.dumps({
        "chat": {"status": "ok", "detail": ""}, "vision": {"status": "na", "detail": "fonte só de áudio"},
        "editor": {"status": "failed", "detail": "agy 429"}}), encoding="utf-8")
    b = raiz / "bbbbbbbbbbbb"
    b.mkdir()
    projetos = [{"id": "aaaaaaaaaaaa", "source_meta": {"title": "VOD A"}}, {"id": "bbbbbbbbbbbb", "source": "x"}]
    m = matriz_motor(raiz, projetos)
    assert m["partes"] == ["chat", "editor", "vision"]
    pa, pb = m["projetos"]
    assert pa["titulo"] == "VOD A" and pa["celulas"]["editor"] == {"status": "failed", "detalhe": "agy 429"}
    assert pa["resumo"] == "1 parte falhou (editor) · 1 não se aplica · 1 ok"
    assert pb["celulas"] == {} and pb["resumo"] == "saúde não registrada (projeto anterior ao registro)"


def test_benchmark_por_versao_com_acaso_e_n(tmp_path):
    pasta = tmp_path / "benchmarks"
    (pasta / "gabaritos").mkdir(parents=True)
    for i in range(4):
        (pasta / "gabaritos" / f"v{i}.json").write_text("{}", encoding="utf-8")
    (pasta / "conjunto.json").write_text("{}", encoding="utf-8")
    (pasta / "2026-11-21-baseline.json").write_text(json.dumps({"data": "2026-11-21", "label": "baseline", "media": {
        "vods_com_gabarito": 4, "k": {"5": {"precisao": 0.25, "precisao_acaso": 0.12, "lift": 2.08}}}}), encoding="utf-8")
    (pasta / "2026-11-22-3.6.2.json").write_text(json.dumps({"data": "2026-11-22", "label": "3.6.2", "media": {
        "vods_com_gabarito": 2, "k": {"5": {"precisao": 0.3, "precisao_acaso": 0.1, "lift": 3.0}}}}), encoding="utf-8")
    (pasta / "quebrado.json").write_text("{", encoding="utf-8")
    r = benchmark(pasta)
    assert [v["label"] for v in r["versoes"]] == ["3.6.2", "baseline"]
    assert r["versoes"][0] == {"label": "3.6.2", "data": "2026-11-22", "n": 2, "amostra_pequena": True,
                               "ks": {"5": {"precisao": 0.3, "acaso": 0.1, "lift": 3.0}}, "arquivo": "2026-11-22-3.6.2.json"}
    assert r["versoes"][1]["amostra_pequena"] is False
    assert (r["gabaritos"], r["meta"]) == (4, 20)


def test_benchmark_sem_pasta(tmp_path):
    assert benchmark(tmp_path / "nada") == {"versoes": [], "gabaritos": 0, "meta": 20}
