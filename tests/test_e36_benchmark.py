"""Story 3.6.1 — Gabarito automático (comentários com horário + heatmap) e baseline de Precision@K.

Mede o motor ATUAL; nada na seleção muda. Custo zero: só dados já baixados, nenhuma chamada a LLM.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


# ---------------------------------------------------------------- Task 1: horário bruto na semente

def test_comment_seed_keeps_raw_timestamp():
    import picorte.engine.comments_miner as cm

    payload = {"duration": 3000, "comments": [{"text": "12:34 caiu do prédio kkkk", "like_count": 9}]}

    def fake_runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")

    seeds = cm.mine_youtube_comments("https://youtu.be/x", permission_status="liberada", runner=fake_runner)
    assert seeds[0]["timestamp_s"] == 754.0


# ---------------------------------------------------------------- Task 2: gabarito, acerto e acaso

def _seed(start, end, likes=0, text="lance", ts=None):
    s = {"start": start, "end": end, "text": text, "seed_kind": "comment_timestamp",
         "score_parts": {"comment_likes": likes}}
    if ts is not None:
        s["timestamp_s"] = ts
    return s


def test_comment_moments_use_raw_timestamp_when_present():
    from picorte.engine import benchmark as b

    m = b.comment_moments([_seed(88.0, 122.0, likes=44, text="caiu kkk", ts=95.0)])
    assert m == [{"fonte": "comentario", "a": 95.0, "b": 95.0, "t": 95.0, "likes": 44, "texto": "caiu kkk"}]


def test_comment_moments_infer_timestamp_from_window_of_old_seeds():
    from picorte.engine import benchmark as b

    # janela padrão do minerador: t − 12 s … t + 22 s
    assert b.comment_moments([_seed(88.0, 122.0)])[0]["t"] == 100.0
    assert b.comment_moments([_seed(0.0, 30.0)])[0]["t"] == 8.0


def test_heatmap_moments_are_peaks_of_most_replayed():
    from picorte.engine import benchmark as b

    heatmap = [{"start_time": 0, "end_time": 10, "value": 0.2},
               {"start_time": 10, "end_time": 20, "value": 0.9},
               {"start_time": 20, "end_time": 30, "value": 0.3}]
    assert b.heatmap_moments(heatmap) == [{"fonte": "heatmap", "a": 10.0, "b": 20.0, "t": 15.0, "valor": 0.9}]


def test_build_gabarito_without_comments_or_heatmap_is_sem_gabarito():
    from picorte.engine import benchmark as b

    g = b.build_gabarito([], [])
    assert g["status"] == "sem_gabarito"
    assert g["momentos"] == []


def test_build_gabarito_merges_sources_sorted_by_time():
    from picorte.engine import benchmark as b

    heatmap = [{"start_time": 10, "end_time": 20, "value": 0.9}]
    g = b.build_gabarito([_seed(400.0, 434.0, ts=412.0)], heatmap)
    assert g["status"] == "ok"
    assert [m["fonte"] for m in g["momentos"]] == ["heatmap", "comentario"]
    assert g["fontes"] == {"comentarios": 1, "heatmap": 1}


def test_clip_hits_with_tolerance():
    from picorte.engine import benchmark as b

    moments = [{"a": 100.0, "b": 100.0}]
    assert b.clip_hits(80.0, 120.0, moments)
    assert b.clip_hits(110.0, 140.0, moments, tol=10.0)        # borda: 110 − 10 = 100
    assert not b.clip_hits(111.0, 140.0, moments, tol=10.0)
    assert not b.clip_hits(0.0, 50.0, moments)


def test_chance_hit_is_exact_probability_of_random_clip():
    from picorte.engine import benchmark as b

    # clipe de 30 s em VOD de 1000 s: início uniforme em [0, 970]; acerta se início ∈ [460, 510]
    p = b.chance_hit(30.0, 1000.0, [{"a": 500.0, "b": 500.0}], tol=10.0)
    assert p == pytest.approx(50.0 / 970.0)


def test_chance_hit_counts_overlapping_moments_once():
    from picorte.engine import benchmark as b

    one = b.chance_hit(30.0, 1000.0, [{"a": 500.0, "b": 500.0}], tol=10.0)
    two = b.chance_hit(30.0, 1000.0, [{"a": 500.0, "b": 500.0}, {"a": 505.0, "b": 505.0}], tol=10.0)
    assert two == pytest.approx(55.0 / 970.0)
    assert two < 2 * one


def test_chance_hit_clip_longer_than_vod():
    from picorte.engine import benchmark as b

    assert b.chance_hit(100.0, 50.0, [{"a": 10.0, "b": 10.0}]) == 1.0
    assert b.chance_hit(100.0, 50.0, []) == 0.0


def test_chance_cover_combines_k_random_clips():
    from picorte.engine import benchmark as b

    p1 = 50.0 / 970.0
    p = b.chance_cover([30.0, 30.0], 1000.0, {"a": 500.0, "b": 500.0}, tol=10.0)
    assert p == pytest.approx(1 - (1 - p1) ** 2)


# ---------------------------------------------------------------- Task 3: avaliação de um VOD

def _segments(n=10, length=30.0, gap=100.0):
    """n clipes de `length` s, a cada `gap` s; rank 1 = o último (ordem do arquivo ≠ ordem do rank)."""
    return [{"start": i * gap, "end": i * gap + length, "rank": n - i, "seed_kind": "multitrack"}
            for i in range(n)]


def _gab(*times):
    from picorte.engine import benchmark as b

    return b.build_gabarito([_seed(0.0, 0.0, ts=t) for t in times], [])


def test_evaluate_vod_precision_uses_rank_order():
    from picorte.engine import benchmark as b

    segs = _segments()                       # rank 1..5 = clipes que começam em 900, 800, 700, 600, 500
    gab = _gab(915.0, 615.0, 15.0)           # 2 acertos no top-5; 15 s só acerta o rank 10
    r = b.evaluate_vod(segs, gab, duration=1000.0)
    assert r["status"] == "ok"
    k5 = r["k"]["5"]
    assert k5["k_efetivo"] == 5
    assert k5["acertos"] == 2
    assert k5["precisao"] == pytest.approx(0.4)
    assert r["k"]["10"]["acertos"] == 3
    assert k5["recall"] == pytest.approx(2 / 3)


def test_evaluate_vod_reports_exact_chance_and_lift():
    from picorte.engine import benchmark as b

    segs = _segments()
    gab = _gab(915.0, 615.0, 15.0)
    k5 = b.evaluate_vod(segs, gab, duration=1000.0)["k"]["5"]
    acaso = b.chance_hit(30.0, 1000.0, gab["momentos"])
    assert k5["precisao_acaso"] == pytest.approx(acaso)
    assert k5["lift"] == pytest.approx(0.4 / acaso)
    expected_recall = sum(b.chance_cover([30.0] * 5, 1000.0, m) for m in gab["momentos"]) / 3
    assert k5["recall_acaso"] == pytest.approx(expected_recall)


def test_evaluate_vod_with_fewer_clips_than_k():
    from picorte.engine import benchmark as b

    r = b.evaluate_vod(_segments(n=3), _gab(215.0), duration=1000.0)
    assert r["k"]["10"]["k_efetivo"] == 3
    assert r["k"]["10"]["precisao"] == pytest.approx(1 / 3)


def test_evaluate_vod_counts_clips_seeded_by_the_gabarito_itself():
    from picorte.engine import benchmark as b

    segs = _segments()
    segs[-1]["seed_kind"] = "comment_timestamp"   # rank 1 nasceu de um comentário → vazamento
    r = b.evaluate_vod(segs, _gab(915.0), duration=1000.0)
    assert r["k"]["5"]["semeados_pelo_gabarito"] == 1


def test_evaluate_vod_without_gabarito_has_no_metrics():
    from picorte.engine import benchmark as b

    r = b.evaluate_vod(_segments(), b.build_gabarito([], []), duration=1000.0)
    assert r == {"status": "sem_gabarito", "clipes": 10}


# ---------------------------------------------------------------- Task 4: projetos, dedup e arquivo

def _make_project(root: Path, pid: str, url: str, updated: float, *, seeds=None, heatmap=None,
                  heatmap_file=None, n=10):
    d = root / pid
    d.mkdir(parents=True)
    meta = {"title": f"VOD {pid}", "duration": 1000.0, "url": True}
    if heatmap is not None:
        meta["heatmap"] = heatmap
    (d / "project.json").write_text(json.dumps({
        "id": pid, "source": url, "updated": updated, "status": "complete",
        "options": {"ai_mode": "gemini"}, "source_meta": meta}), encoding="utf-8")
    (d / "segments.json").write_text(json.dumps(_segments(n=n)), encoding="utf-8")
    if seeds is not None:
        (d / "comment_seeds.json").write_text(json.dumps(seeds), encoding="utf-8")
    if heatmap_file is not None:
        (d / "heatmap.json").write_text(json.dumps(heatmap_file), encoding="utf-8")
    return d


def test_youtube_id_from_common_urls():
    from picorte.engine import benchmark as b

    assert b.youtube_id("https://www.youtube.com/watch?v=kVy8zSfuRc0&t=874s") == "kVy8zSfuRc0"
    assert b.youtube_id("https://youtu.be/kVy8zSfuRc0?t=3") == "kVy8zSfuRc0"
    assert b.youtube_id("C:/videos/meu.mp4") is None


def test_load_project_reads_heatmap_file_when_source_meta_has_none(tmp_path):
    from picorte.engine import benchmark as b

    hm = [{"start_time": 10, "end_time": 20, "value": 0.9}]
    d = _make_project(tmp_path, "p1", "https://youtu.be/AAAAAAAAAAA", 1.0, heatmap=[], heatmap_file=hm)
    proj = b.load_project(d)
    assert proj["video_id"] == "AAAAAAAAAAA"
    assert proj["heatmap"] == hm
    assert len(proj["segments"]) == 10


def test_load_project_without_segments_is_skipped(tmp_path):
    from picorte.engine import benchmark as b

    d = _make_project(tmp_path, "p1", "https://youtu.be/AAAAAAAAAAA", 1.0)
    (d / "segments.json").unlink()
    assert b.load_project(d) is None


def test_run_benchmark_writes_result_gabarito_and_health(tmp_path):
    from picorte.engine import benchmark as b
    from picorte.engine import health

    projects = tmp_path / "projects"
    _make_project(projects, "velho", "https://youtu.be/AAAAAAAAAAA", 1.0, seeds=[_seed(0, 0, ts=15.0)])
    novo = _make_project(projects, "novo", "https://www.youtube.com/watch?v=AAAAAAAAAAA", 2.0,
                         seeds=[_seed(0, 0, ts=915.0), _seed(0, 0, ts=615.0)])
    sem = _make_project(projects, "sem", "https://youtu.be/BBBBBBBBBBB", 3.0)
    out = tmp_path / "benchmarks"

    report = b.run_benchmark(projects, out, date="2026-11-21", label="baseline")

    saved = json.loads((out / "2026-11-21-baseline.json").read_text(encoding="utf-8"))
    assert saved == json.loads(json.dumps(report))
    assert [v["projeto"] for v in report["vods"]] == ["novo"]          # dedup: fica o mais recente
    assert report["duplicados_ignorados"] == [{"projeto": "velho", "video_id": "AAAAAAAAAAA", "usado": "novo"}]
    assert report["vods"][0]["resultado"]["k"]["5"]["acertos"] == 2
    assert [v["projeto"] for v in report["sem_gabarito"]] == ["sem"]
    assert report["media"]["vods_com_gabarito"] == 1
    assert report["media"]["k"]["5"]["precisao"] == pytest.approx(0.4)
    gab = json.loads((out / "gabaritos" / "AAAAAAAAAAA.json").read_text(encoding="utf-8"))
    assert [m["t"] for m in gab["momentos"]] == [615.0, 915.0]
    assert health.load(novo)["benchmark_gabarito"]["status"] == "ok"
    assert health.load(sem)["benchmark_gabarito"]["status"] == "na"


def test_run_benchmark_without_any_gabarito_has_no_average(tmp_path):
    from picorte.engine import benchmark as b

    projects = tmp_path / "projects"
    _make_project(projects, "sem", "https://youtu.be/BBBBBBBBBBB", 3.0)
    report = b.run_benchmark(projects, tmp_path / "out", date="2026-11-21")
    assert report["media"] == {"vods_com_gabarito": 0, "k": {}}
    assert (tmp_path / "out" / "2026-11-21.json").is_file()


# ---------------------------------------------------------------- Task 5: fetch-labels (rede só sob pedido)

YTDLP_PAYLOAD = {
    "duration": 1000,
    "heatmap": [{"start_time": 0, "end_time": 10, "value": 0.1},
                {"start_time": 10, "end_time": 20, "value": 1.0},
                {"start_time": 20, "end_time": 30, "value": 0.2}],
    "comments": [{"text": "15:15 que vacilo kkkk", "like_count": 30}],
}


def _fake_ytdlp(calls):
    def runner(cmd, **kwargs):
        calls.append(cmd)
        assert "--skip-download" in cmd                      # só metadados, nunca mídia
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(YTDLP_PAYLOAD), stderr="")
    return runner


def _allow_gate(url, meta):
    return {"allowed": True, "permission_status": "liberada"}


def test_fetch_labels_writes_seeds_and_heatmap_without_touching_selection(tmp_path):
    from picorte.engine import benchmark as b

    d = _make_project(tmp_path, "p1", "https://youtu.be/AAAAAAAAAAA", 1.0, heatmap=[])
    before = {n: (d / n).read_bytes() for n in ("project.json", "segments.json")}
    calls = []

    res = b.fetch_labels(d, runner=_fake_ytdlp(calls), gate=_allow_gate)

    assert res["status"] == "ok" and res["comentarios"] == 1 and res["heatmap_bins"] == 3
    assert len(calls) == 1                                    # uma chamada traz comentários + heatmap
    seeds = json.loads((d / "comment_seeds.json").read_text(encoding="utf-8"))
    assert seeds[0]["timestamp_s"] == 915.0
    assert len(json.loads((d / "heatmap.json").read_text(encoding="utf-8"))) == 3
    assert {n: (d / n).read_bytes() for n in before} == before
    gab = b.build_gabarito(*[b.load_project(d)[k] for k in ("seeds", "heatmap")])
    assert gab["fontes"] == {"comentarios": 1, "heatmap": 1}


def test_fetch_labels_respects_p1_gate(tmp_path):
    from picorte.engine import benchmark as b

    d = _make_project(tmp_path, "p1", "https://youtu.be/AAAAAAAAAAA", 1.0)
    calls = []

    def deny(url, meta):
        raise PermissionError("[P1:pre_ingest] Fonte desconhecida")

    res = b.fetch_labels(d, runner=_fake_ytdlp(calls), gate=deny)
    assert res["status"] == "bloqueado_p1"
    assert calls == []
    assert not (d / "comment_seeds.json").exists()


def test_fetch_labels_keeps_existing_comment_seeds(tmp_path):
    from picorte.engine import benchmark as b

    d = _make_project(tmp_path, "p1", "https://youtu.be/AAAAAAAAAAA", 1.0, seeds=[_seed(0, 0, ts=42.0)])
    b.fetch_labels(d, runner=_fake_ytdlp([]), gate=_allow_gate)
    assert json.loads((d / "comment_seeds.json").read_text(encoding="utf-8"))[0]["timestamp_s"] == 42.0


def test_fetch_labels_never_raises_when_ytdlp_fails(tmp_path):
    from picorte.engine import benchmark as b
    from picorte.engine import health

    d = _make_project(tmp_path, "p1", "https://youtu.be/AAAAAAAAAAA", 1.0)

    def boom(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    res = b.fetch_labels(d, runner=boom, gate=_allow_gate)
    assert res["status"] == "failed"
    assert health.load(d)["benchmark_labels"]["status"] == "failed"


def test_cli_run_writes_dated_file(tmp_path, capsys):
    from picorte.engine import benchmark as b

    projects = tmp_path / "projects"
    _make_project(projects, "p1", "https://youtu.be/AAAAAAAAAAA", 1.0, seeds=[_seed(0, 0, ts=915.0)])
    assert b.main(["run", "--projects", str(projects), "--out", str(tmp_path / "out"),
                   "--date", "2026-11-21", "--label", "baseline"]) == 0
    assert (tmp_path / "out" / "2026-11-21-baseline.json").is_file()
    assert "P@5=0.20" in capsys.readouterr().out


# ---------------------------------------------------------------- triagem e conjunto de prova

URL_A = "https://www.youtube.com/watch?v=AAAAAAAAAAA"
URL_B = "https://youtu.be/BBBBBBBBBBB"


def _fakes(*, comments=5, chat_per_min=40.0, channel="alanzoka", duration=3600.0, heat=False):
    """Probe/portão/comentários/chat falsos: nenhum acesso à rede."""
    calls = {"comments": 0, "chat": 0}

    def probe(url):
        hm = HEATMAP_BINS if heat else []
        return {"title": f"live {url[-3:]}", "channel": channel, "duration": duration, "heatmap": hm, "url": True}

    def gate(url, meta):
        if meta.get("channel") != "alanzoka":
            raise PermissionError("[P1:pre_ingest] Fonte desconhecida")
        return {"allowed": True, "permission_status": "liberada"}

    def fake_comments(url, workdir, **kw):
        calls["comments"] += 1
        out = Path(workdir) / "comment_seeds.json"
        out.write_text(json.dumps([_seed(0, 0, ts=100.0 * (i + 1)) for i in range(comments)]), encoding="utf-8")
        return out

    def fake_chat(url, workdir, **kw):
        calls["chat"] += 1
        n = int(chat_per_min * duration / 60.0)
        if not n:
            return None
        out = Path(workdir) / "chat.json"
        out.write_text(json.dumps([{"t": i * duration / n, "author": "a", "text": "kkk"} for i in range(n)]),
                       encoding="utf-8")
        return out

    return {"probe": probe, "gate": gate, "comments": fake_comments, "chat": fake_chat}, calls


HEATMAP_BINS = [{"start_time": 0, "end_time": 10, "value": 0.1}, {"start_time": 10, "end_time": 20, "value": 1.0},
                {"start_time": 20, "end_time": 30, "value": 0.1}]


def test_triar_vod_approves_live_with_comments_and_busy_chat(tmp_path):
    from picorte.engine import benchmark as b

    fakes, _ = _fakes()
    r = b.triar_vod(URL_A, tmp_path / "t", **fakes)
    assert r["aprovado"] is True and r["motivos"] == []
    assert r["comentarios"] == 5
    assert r["chat_msgs_min"] == pytest.approx(40.0, rel=0.01)
    assert r["video_id"] == "AAAAAAAAAAA"


def test_triar_vod_rejects_few_comments_and_quiet_chat(tmp_path):
    from picorte.engine import benchmark as b

    fakes, _ = _fakes(comments=1, chat_per_min=5.0)
    r = b.triar_vod(URL_A, tmp_path / "t", **fakes)
    assert r["aprovado"] is False
    assert any("comentários" in m for m in r["motivos"])
    assert any("chat" in m for m in r["motivos"])


def test_triar_vod_heatmap_peak_counts_toward_gabarito(tmp_path):
    from picorte.engine import benchmark as b

    fakes, _ = _fakes(comments=2, heat=True)
    assert b.triar_vod(URL_A, tmp_path / "t", **fakes)["aprovado"] is True


def test_triar_vod_blocked_by_p1_downloads_nothing(tmp_path):
    from picorte.engine import benchmark as b

    fakes, calls = _fakes(channel="desconhecido")
    r = b.triar_vod(URL_A, tmp_path / "t", **fakes)
    assert r["aprovado"] is False and "P1" in r["motivos"][0]
    assert calls == {"comments": 0, "chat": 0}


def test_preparar_conjunto_prepares_only_approved_lives_in_blind_mode(tmp_path):
    from picorte.engine import benchmark as b

    fakes, _ = _fakes()
    triados = {URL_A: True, URL_B: False}

    def triar(url, workdir, **kw):
        r = b.triar_vod(url, workdir, **fakes)
        if not triados[url]:
            r["aprovado"], r["motivos"] = False, ["chat parado"]
        return r

    created, ran = [], []

    def create(root, source, options):
        pid = f"{len(created):012x}"
        (Path(root) / pid).mkdir(parents=True)
        created.append((source, options))
        return {"id": pid}

    def run(path, action):
        ran.append((Path(path).name, action, sorted(p.name for p in Path(path).iterdir())))
        return {"status": "review"}

    out = tmp_path / "benchmarks"
    conj = b.preparar_conjunto([URL_A, URL_B, URL_A + "&t=5"], tmp_path / "projects", out,
                               triar=triar, create=create, run=run)

    assert len(created) == 1 and created[0][0] == URL_A
    assert created[0][1]["benchmark_blind"] is True and created[0][1]["ai_mode"] == "ollama"
    assert created[0][1]["llm"] == "qwen3.5:9b"   # mesmo Editor-Chefe em todo o conjunto (cota grátis do Gemini não aguenta)
    # comentários e chat da triagem vão para o projeto: o prepare não baixa de novo
    assert ran == [("000000000000", "prepare", ["chat.json", "comment_seeds.json"])]
    assert [v["video_id"] for v in conj["vods"]] == ["AAAAAAAAAAA"]
    assert [v["video_id"] for v in conj["descartados"]] == ["BBBBBBBBBBB"]
    assert json.loads((out / "conjunto.json").read_text(encoding="utf-8")) == conj


def test_preparar_conjunto_skips_lives_already_in_the_set(tmp_path):
    from picorte.engine import benchmark as b

    fakes, _ = _fakes()
    out = tmp_path / "benchmarks"
    out.mkdir()
    (out / "conjunto.json").write_text(json.dumps({"vods": [{"video_id": "AAAAAAAAAAA", "projeto": "x"}],
                                                   "descartados": []}), encoding="utf-8")
    calls = []
    conj = b.preparar_conjunto([URL_A], tmp_path / "projects", out,
                               triar=lambda u, w, **k: calls.append(u), create=None, run=None)
    assert calls == [] and len(conj["vods"]) == 1


def test_run_benchmark_can_be_restricted_to_the_test_set(tmp_path):
    from picorte.engine import benchmark as b

    projects = tmp_path / "projects"
    d = _make_project(projects, "cego", URL_A, 1.0, seeds=[_seed(0, 0, ts=915.0)])
    state = json.loads((d / "project.json").read_text(encoding="utf-8"))
    state["options"]["benchmark_blind"] = True
    (d / "project.json").write_text(json.dumps(state), encoding="utf-8")
    _make_project(projects, "outro", URL_B, 1.0, seeds=[_seed(0, 0, ts=915.0)])
    conj = tmp_path / "conjunto.json"
    conj.write_text(json.dumps({"vods": [{"video_id": "AAAAAAAAAAA", "projeto": "cego"}]}), encoding="utf-8")

    report = b.run_benchmark(projects, tmp_path / "out", date="2026-11-21", conjunto=conj)
    assert [v["projeto"] for v in report["vods"]] == ["cego"]
    assert report["vods"][0]["modo_cego"] is True


def test_sem_triagem_approves_any_youtube_live_without_network(tmp_path):
    from picorte.engine import benchmark as b

    r = b.sem_triagem("https://www.youtube.com/watch?v=x50ONQrBPRM", tmp_path / "t")
    assert r == {"url": "https://www.youtube.com/watch?v=x50ONQrBPRM", "video_id": "x50ONQrBPRM",
                 "aprovado": True, "motivos": [], "triagem": False}


def test_cli_preparar_conjunto_skips_triage_by_default(tmp_path, monkeypatch):
    from picorte.engine import benchmark as b

    used = []
    monkeypatch.setattr(b, "preparar_conjunto", lambda urls, *a, **k: used.append(k.get("triar")) or
                        {"vods": [], "descartados": []})
    lista = tmp_path / "lista.txt"
    lista.write_text(URL_A + "\n", encoding="utf-8")
    b.main(["preparar-conjunto", str(lista)])
    b.main(["preparar-conjunto", str(lista), "--com-triagem"])
    assert used == [b.sem_triagem, None]


def test_cli_preparar_conjunto_does_not_add_any_vod_by_itself(tmp_path, monkeypatch):
    from picorte.engine import benchmark as b

    seen = []
    monkeypatch.setattr(b, "preparar_conjunto", lambda urls, *a, **k: seen.extend(urls) or
                        {"vods": [], "descartados": []})
    lista = tmp_path / "lista.txt"
    lista.write_text(URL_A + "\n# comentário\n", encoding="utf-8")
    assert b.main(["preparar-conjunto", str(lista)]) == 0
    assert seen == [URL_A]


# ---------------------------------------------------------------- filtro do gabarito (comentário que não marca momento bom)

@pytest.mark.parametrize("texto,motivo", [
    ("QUAL NOME DA MUSICA?", "pergunta"),
    ("qual o nome da música que toca no : 44 ?", "pergunta"),
    ("alguém sabe o nome do carro", "pergunta"),
    ("caiu FPS sim", "tecnico"),
    ("realmente os sons estão saindo bem atrasados", "tecnico"),
    ("a live travou aqui", "tecnico"),
    ("começa aqui! de nada", "inicio"),
    ("4:06:11", "sem_texto"),
    ("", "sem_texto"),
])
def test_filter_removes_comments_that_do_not_mark_a_good_moment(texto, motivo):
    from picorte.engine import benchmark as b

    assert b.motivo_fora_do_gabarito(texto) == motivo


@pytest.mark.parametrize("texto", [
    "😂😂😂",
    "🔥🔥🔥",
    "KKKKKKKKKKKKKKKK",
    "o Jason é idêntico ao Arthur pqp",
    "ele caiu do prédio kkkk",
    "mago se empolgou um pouco demais kk",
    "que cena absurda!",
])
def test_filter_keeps_comments_about_what_happened(texto):
    from picorte.engine import benchmark as b

    assert b.motivo_fora_do_gabarito(texto) is None


def test_build_gabarito_keeps_removed_comments_with_reason():
    from picorte.engine import benchmark as b

    g = b.build_gabarito([_seed(0, 0, ts=100.0, text="kkkkk caiu"), _seed(0, 0, ts=200.0, text="caiu FPS sim")], [])
    assert [m["t"] for m in g["momentos"]] == [100.0]
    assert g["fontes"]["comentarios"] == 1
    assert g["removidos"] == [{"t": 200.0, "texto": "caiu FPS sim", "likes": 0, "motivo": "tecnico"}]


def test_build_gabarito_with_only_noise_is_sem_gabarito():
    from picorte.engine import benchmark as b

    g = b.build_gabarito([_seed(0, 0, ts=200.0, text="qual a música?")], [])
    assert g["status"] == "sem_gabarito" and len(g["removidos"]) == 1
