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
    assert m["partes"] == ["chat", "vision", "editor"]  # ordem do pipeline
    pa, pb = m["projetos"]
    assert pa["titulo"] == "VOD A" and pa["celulas"]["editor"] == {
        "status": "failed", "detalhe": "agy 429", "em": None, "conhecida": None}
    assert pa["resumo"] == "1 parte falhou (Editor-Chefe) · 1 não se aplica · 1 ok"
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


def test_matriz_mostra_so_a_ultima_execucao_com_rotulos(tmp_path):
    """W32 + seção 2 do briefing: partes de execução anterior saem da matriz; colunas com rótulo em português."""
    import json
    from picorte.services.saude import matriz_motor

    pasta = tmp_path / "p1"
    pasta.mkdir()
    (pasta / "engine_health.json").write_text(json.dumps({
        "_execucao": {"inicio": "2026-11-23T07:00:00+00:00", "acao": "prepare"},
        "heatmap": {"status": "failed", "detail": "velho", "at": "2026-11-20T10:00:00+00:00"},
        "audio": {"status": "ok", "detail": "36448 s medidos", "at": "2026-11-23T07:22:59+00:00"},
        "vision": {"status": "failed", "detail": "12 candidatos medidos, mas degradado: MediaPipe indisponível",
                   "at": "2026-11-23T07:27:26+00:00"},
    }), encoding="utf-8")
    m = matriz_motor(tmp_path, [{"id": "p1"}])
    assert m["partes"] == ["audio", "vision"]  # ordem do pipeline: o áudio vem antes da visão
    assert m["rotulos"]["audio"] == "Energia do áudio" and m["rotulos"]["vision"] == "Visão (facecam e HUD)"
    linha = m["projetos"][0]
    assert "heatmap" not in linha["celulas"] and linha["anteriores"] == 1
    assert "W49" in linha["celulas"]["vision"]["conhecida"]
    assert "Visão (facecam e HUD)" in linha["resumo"]
