"""Code review do motor — fatia (b) seleção e IA (2026-11-23).

Cada teste nasceu de um achado verificado no código; o nome diz o que quebrava.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import score_clips as sc
from picorte.ai.llm_router import EditorChiefUnavailable, LLMRouter, attach_neighbor_context
from picorte.config import resolve_cli_binary
from picorte.engine import health

FFMPEG = resolve_cli_binary("ffmpeg") or "ffmpeg"


def _cands(n=3):
    return [{"start": float(i * 30), "end": float(i * 30 + 20), "overall": 7.0, "text": f"corte {i}"}
            for i in range(n)]


def _rows(user_prompt: str) -> list[dict]:
    return json.loads(user_prompt[user_prompt.index("["):])


def _completo(provider, model, system_prompt, user_prompt):
    return json.dumps([{"index": r["index"], "adjustment": 0.5, "reason": "ok", "archetype": "clutch_fail",
                        "tier": "forte"} for r in _rows(user_prompt)])


# ------------------------------------------------------------------ item 1: lote parcial (Decisão B)

def test_lote_parcial_e_tentado_de_novo_e_depois_para():
    chamadas = []

    def parcial(provider, model, system_prompt, user_prompt):
        chamadas.append(1)
        return json.dumps([{"index": _rows(user_prompt)[0]["index"], "adjustment": 0.5}])

    with pytest.raises(EditorChiefUnavailable) as exc:
        LLMRouter(provider_runner=parcial).rerank_candidates(_cands(3), ai_mode="gemini")
    assert len(chamadas) == 2
    assert "parcial" in str(exc.value) and "1 de 3" in str(exc.value)


def test_lote_parcial_que_volta_completo_na_nova_tentativa_segue():
    estado = {"n": 0}

    def depois_completo(provider, model, system_prompt, user_prompt):
        estado["n"] += 1
        rows = _rows(user_prompt)
        rows = rows[:1] if estado["n"] == 1 else rows
        return json.dumps([{"index": r["index"], "adjustment": 0.5, "reason": "ok"} for r in rows])

    out = LLMRouter(provider_runner=depois_completo).rerank_candidates(_cands(3), ai_mode="gemini")
    assert len(out["candidates"]) == 3 and all(c.get("llm_mode_used") == "gemini" for c in out["candidates"])


# ------------------------------------------------------------------ item 4: 2ª passada que falha fica registrada

def test_falha_da_segunda_passada_fica_registrada():
    estado = {"n": 0}

    def cai_na_segunda(provider, model, system_prompt, user_prompt):
        estado["n"] += 1
        if estado["n"] > 1:
            raise RuntimeError("cota esgotada")
        return _completo(provider, model, system_prompt, user_prompt)

    out = LLMRouter(provider_runner=cai_na_segunda).rerank_candidates(_cands(3), ai_mode="gemini")
    assert out["segunda_passada"].startswith("falhou") and "cota esgotada" in out["segunda_passada"]


def test_segunda_passada_que_roda_diz_ok():
    out = LLMRouter(provider_runner=_completo).rerank_candidates(_cands(3), ai_mode="gemini")
    assert out["segunda_passada"] == "ok"


# ------------------------------------------------------------------ item 5: contexto guarda a frase mais próxima

def _frases_antes():
    return [{"start": float(i * 4), "end": float(i * 4 + 3.5), "text": f"frase numero {i} " + "bla " * 25}
            for i in range(5)]


def test_contexto_antes_do_corte_guarda_a_frase_mais_proxima():
    (rec,) = attach_neighbor_context([{"start": 20.0, "end": 40.0, "overall": 7.0}], _frases_antes())
    assert "[-1] frase numero 4" in rec["pre_context"]


def test_editor_recebe_a_frase_colada_no_comeco_do_corte():
    vistos = []

    def espia(provider, model, system_prompt, user_prompt):
        vistos.extend(_rows(user_prompt))
        return _completo(provider, model, system_prompt, user_prompt)

    LLMRouter(provider_runner=espia).rerank_candidates(
        [{"start": 20.0, "end": 40.0, "overall": 7.0, "text": "o corte"}], ai_mode="gemini", sentences=_frases_antes())
    assert vistos and "[-1] frase numero 4" in vistos[0]["pre_context"]


# ------------------------------------------------------------------ item 7: marcas da rodada anterior

def test_reavaliacao_limpa_marcas_da_rodada_anterior():
    cands = _cands(3)
    for c in cands:  # como ficam no candidates.json depois de uma seleção
        c.update(ordem_ajustes=[2.0, -1.0], confianca_baixa=True, last_pass_adjustment=0.5, llm_adjustment=0.5,
                 overall=7.5)
    out = LLMRouter(provider_runner=_completo).rerank_candidates(cands, ai_mode="gemini")
    assert not any(c.get("confianca_baixa") for c in out["candidates"])
    assert all(c.get("ordem_ajustes") == [0.5, 0.5] for c in out["candidates"])  # a 2ª passada rodou de novo
    assert all(c["overall"] == 7.5 for c in out["candidates"])                    # ajuste não acumula


# ------------------------------------------------------------------ item 8: borda estendida atualiza o texto

def test_borda_estendida_atualiza_texto_e_contexto():
    sents = [{"start": 0.0, "end": 4.0, "text": "o setup começa aqui"},
             {"start": 4.0, "end": 10.0, "text": "o corte"},
             {"start": 10.0, "end": 14.0, "text": "a reação depois"}]

    def estende(provider, model, system_prompt, user_prompt):
        return json.dumps([{"index": r["index"], "adjustment": 0.0, "extend_sentences_before": 1,
                            "extend_sentences_after": 1} for r in _rows(user_prompt)])

    out = LLMRouter(provider_runner=estende).rerank_candidates(
        [{"start": 4.0, "end": 10.0, "overall": 7.0, "text": "o corte"}], ai_mode="gemini", sentences=sents)
    (c,) = out["candidates"]
    assert (c["start"], c["end"]) == (0.0, 14.0)
    assert c["text"] == "o setup começa aqui o corte a reação depois"
    assert "o setup" not in c.get("pre_context", "") and "a reação" not in c.get("post_context", "")


# ------------------------------------------------------------------ item 10: Dupla e modelo por provedor

def test_dupla_respeita_keep_overflow():
    def mesmo_arquetipo(provider, model, system_prompt, user_prompt):
        return json.dumps([{"index": r["index"], "adjustment": 0.2, "archetype": "clutch_fail", "tier": "forte",
                            "reason": "ok"} for r in _rows(user_prompt)])

    out = LLMRouter(provider_runner=mesmo_arquetipo).rerank_candidates(
        _cands(6), ai_mode="dupla", filter_provider="ollama", companion_provider="gemini",
        max_per_archetype=3, keep_overflow=True)
    assert len(out["candidates"]) == 6


def test_modelo_do_ollama_nao_vai_para_claude_ou_gemini():
    vistos = []

    def espia(provider, model, system_prompt, user_prompt):
        vistos.append((provider, model))
        return _completo(provider, model, system_prompt, user_prompt)

    LLMRouter(provider_runner=espia).rerank_candidates(_cands(3), ai_mode="gemini", model="qwen2.5:7b")
    LLMRouter(provider_runner=espia).rerank_candidates(_cands(3), ai_mode="dupla", filter_provider="ollama",
                                                       companion_provider="claude", model="qwen2.5:7b")
    assert vistos and all(m is None for p, m in vistos if p != "ollama")
    assert ("ollama", "qwen2.5:7b") in vistos


# ------------------------------------------------------------------ D1 (a): sem fallback pago automático (regra 6)

@pytest.mark.parametrize("provedor", ["claude", "gemini"])
def test_sem_cli_nao_cai_na_api_paga(monkeypatch, provedor):
    import picorte.ai.llm_router as lr

    monkeypatch.setattr(lr, "resolve_cli_binary", lambda name: None)
    for k in ("ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(k, "chave-de-teste")

    def proibido(*a, **k):
        raise AssertionError("a API paga não pode ser chamada sem decisão explícita (regra 6)")

    monkeypatch.setattr(lr.urllib.request, "urlopen", proibido)
    with pytest.raises(RuntimeError, match="regra 6"):
        LLMRouter()._run_provider(provedor, None, "sistema", "dados")


# ------------------------------------------------------------------ item 2: Scout não esconde falha

def _frases(n=20):
    return [{"start": i * 5.0, "end": i * 5.0 + 4.0, "text": f"frase {i} do streamer"} for i in range(n)]


def test_scout_com_provedor_fora_do_ar_levanta_erro():
    from picorte.ai.llm_scout import scout_full_vod

    def cota(*a):
        raise RuntimeError("429 cota do gemini")

    with pytest.raises(Exception, match="cota"):
        scout_full_vod(_frases(), router=LLMRouter(provider_runner=cota), ai_mode="gemini")


def test_scout_com_resposta_sem_json_levanta_erro():
    from picorte.ai.llm_scout import ScoutUnavailable, scout_full_vod

    with pytest.raises(ScoutUnavailable):
        scout_full_vod(_frases(), router=LLMRouter(provider_runner=lambda *a: "desculpe, não consegui"),
                       ai_mode="gemini")


def test_scout_que_nao_acha_nada_devolve_vazio_sem_erro():
    from picorte.ai.llm_scout import scout_full_vod

    assert scout_full_vod(_frases(), router=LLMRouter(provider_runner=lambda *a: "[]"), ai_mode="gemini") == []


def test_scout_conta_os_blocos_que_falharam():
    from picorte.ai.llm_scout import LONG_VOD_MAPREDUCE_SECONDS, scout_full_vod

    longo = [{"start": i * 30.0, "end": i * 30.0 + 25.0, "text": f"frase {i} do streamer"}
             for i in range(int(LONG_VOD_MAPREDUCE_SECONDS / 30) + 60)]
    estado = {"bloco": 0}

    def um_bloco_cai(provider, model, system_prompt, user_prompt):
        if "BLOCO DA TRANSCRIÇÃO" in user_prompt:
            estado["bloco"] += 1
            if estado["bloco"] == 1:
                raise RuntimeError("timeout no bloco")
            return json.dumps([{"start_sid": "S0001", "end_sid": "S0002", "summary": "lance"}])
        return "[]"

    relatorio: dict = {}
    scout_full_vod(longo, router=LLMRouter(provider_runner=um_bloco_cai), ai_mode="gemini", max_workers=1,
                   report=relatorio)
    assert relatorio["blocos_falhos"] == 1 and relatorio["blocos"] >= 2
    assert "timeout no bloco" in relatorio["motivo"]


# ------------------------------------------------------------------ item 6: busca livre lê a live inteira

def test_busca_livre_le_a_transcricao_inteira():
    from picorte.ai.llm_scout import MAX_DIRECT_CHARS, query_vod_clips

    longo = [{"start": i * 6.0, "end": i * 6.0 + 5.0, "text": f"frase {i} " + "fala comprida " * 6}
             for i in range(int(MAX_DIRECT_CHARS / 60) + 200)]
    ultimo = f"S{len(longo):04d}"
    prompts = []

    def responde_no_fim(provider, model, system_prompt, user_prompt):
        prompts.append(user_prompt)
        if f"[{ultimo}]" in user_prompt:
            return json.dumps([{"start_sid": ultimo, "end_sid": ultimo, "why": "achei no fim"}])
        return "[]"

    out = query_vod_clips(longo, query="o momento do fim", router=LLMRouter(provider_runner=responde_no_fim),
                          ai_mode="gemini")
    assert any(f"[{ultimo}]" in p for p in prompts), "o fim da live nunca foi lido"
    assert out and out[0]["start"] == longo[-1]["start"]


# ------------------------------------------------------------------ item 3: dica vacilo/mico só é "fala" com fala

def test_dica_de_mico_vinda_do_chat_e_do_comentario_nao_vira_fala():
    from picorte.engine.confidence import independent_signals
    from picorte.engine.multitrack import build_multitrack_pool

    cand = {"start": 10.0, "end": 40.0, "overall": 7.0, "text": "ok seguindo aqui", "seed_kind": "comment_timestamp",
            "comment_hint": "que vergonha", "archetype_hint": "mico_constrangimento",
            "archetype_hint_source": "comentario", "evidence": {"chat_reaction": "cringe", "chat_measured": True}}
    pool = build_multitrack_pool([cand], sentences=[{"start": 10.0, "end": 40.0, "text": "ok seguindo aqui"}])
    (rec,) = [c for c in pool if c["start"] == 10.0]
    assert rec.get("archetype_hint") == "mico_constrangimento"
    assert rec.get("archetype_hint_source") != "fala"
    assert "fala" not in independent_signals(rec)


def test_dica_de_vacilo_dita_pelo_streamer_e_fala():
    from picorte.engine.multitrack import build_multitrack_pool

    cand = {"start": 10.0, "end": 40.0, "overall": 7.0, "text": "que burro, como eu sou burro", "evidence": {}}
    pool = build_multitrack_pool([cand], sentences=[{"start": 10.0, "end": 40.0, "text": cand["text"]}])
    (rec,) = [c for c in pool if c["start"] == 10.0]
    assert rec.get("archetype_hint_source") == "fala"


# ------------------------------------------------------------------ item 11: léxico das pistas por palavra inteira

def test_lexico_das_pistas_nao_casa_dentro_de_outra_palavra():
    from picorte.engine.multitrack import ARCHETYPE_LEXICON_PTBR, _lexicon_hits

    coop = ARCHETYPE_LEXICON_PTBR["coop_karma_payoff"]
    assert _lexicon_hits("a gravação ficou boa e a clipagem também", coop) == 0
    assert _lexicon_hits("grava isso, clipa aí", coop) == 2
    assert _lexicon_hits("Foi você, culpa sua!", coop) == 2


# ------------------------------------------------------------------ item 10: limite único de Short

def test_limite_de_short_e_um_so():
    from picorte.engine import composites, formats

    assert composites.SHORT_MAX_S == formats.SHORT_MAX_S


# ------------------------------------------------------------------ itens 9, 10 e testes de ligação do select

def _fala(duracao: float) -> list[dict]:
    words, t = [], 0.5
    for tok in ("olha isso cara. que absurdo mano! ele caiu de novo. " * 80).split():
        if t + 0.5 > duracao:
            break
        words.append({"word": tok, "start": round(t, 2), "end": round(t + 0.5, 2)})
        t += 0.6
    return words


def _projeto_select(tmp_path: Path, monkeypatch, *, duracao=120.0, cegos=False):
    from picorte.ai import llm_router as lr_mod

    wav = tmp_path / "audio.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:duration={duracao:g}", str(wav)], check=True)
    (tmp_path / "transcript.json").write_text(json.dumps({
        "video": str(wav), "duration": duracao, "language": "pt", "words": _fala(duracao)}), encoding="utf-8")
    if cegos:
        (tmp_path / "project.json").write_text(json.dumps({"options": {"benchmark_blind": True}}), encoding="utf-8")
    base = {"seed_kind": "sentence", "score_parts": {}, "evidence": {}, "reason": "teste", "raw_score": 8.0}
    cands = [{**base, "start": 30.0, "end": 60.0, "duration": 30.0, "hook": "corte", "overall": 8.4,
              "text": "olha isso cara, que absurdo mano, ele caiu de novo"}]
    sc.save_candidates(tmp_path, cands, {"source_duration": duracao, "content_profile": "mixed"})

    def fake_provider(self, provider, model, system_prompt, user_prompt):
        if "Full-VOD Scout" in system_prompt or "BLOCO DA TRANSCRIÇÃO" in user_prompt:
            return "[]"
        rows = json.loads(user_prompt.split("CANDIDATOS JSON:\n", 1)[-1])
        return json.dumps([{"index": r["index"], "adjustment": 0.0, "archetype": "rage_tilt", "tier": "forte",
                            "tone": "hype", "reason": "ok"} for r in rows])

    monkeypatch.setattr(lr_mod.LLMRouter, "_run_provider", fake_provider)


def test_select_gera_versao_tiktok_e_respeita_formatos_extras(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch)
    segs, _ = sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    assert any(s.get("formato") == "tiktok_60" for s in segs)
    assert health.load(tmp_path)["formatos_extras"]["status"] == "ok"
    assert health.load(tmp_path)["seamless_loop"]["status"] in ("ok", "na")
    segs, _ = sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude", formatos_extras=False)
    assert not any(s.get("formato") not in ("short", "vertical_longo") for s in segs)  # só o corte principal


def test_select_em_modo_cego_nao_gera_formatos_extras(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch, cegos=True)
    assert sc._benchmark_blind(tmp_path)
    segs, _ = sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    assert not any(s.get("formato") not in ("short", "vertical_longo") for s in segs)  # só o corte principal


def test_select_registra_falha_da_segunda_passada_na_saude(tmp_path: Path, monkeypatch):
    from picorte.ai import llm_router as lr_mod

    _projeto_select(tmp_path, monkeypatch)
    sc.save_candidates(tmp_path, [{"seed_kind": "sentence", "score_parts": {}, "evidence": {}, "reason": "t",
                                   "raw_score": 8.0, "start": float(s), "end": float(s + 25), "duration": 25.0,
                                   "hook": "c", "overall": 8.4, "text": "olha isso cara, que absurdo"}
                                  for s in (5, 40, 75)], {"source_duration": 120.0, "content_profile": "mixed"})
    estado = {"n": 0}
    original = lr_mod.LLMRouter._run_provider

    def cai_depois(self, provider, model, system_prompt, user_prompt):
        if "CANDIDATOS JSON" in user_prompt:
            estado["n"] += 1
            if estado["n"] > 1:
                raise RuntimeError("cota esgotada")
        return original(self, provider, model, system_prompt, user_prompt)

    monkeypatch.setattr(lr_mod.LLMRouter, "_run_provider", cai_depois)
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    detalhe = health.load(tmp_path)["editor"]["detail"]
    assert "2ª passada falhou" in detalhe and "cota esgotada" in detalhe


def test_select_registra_scout_que_caiu_como_falha(tmp_path: Path, monkeypatch):
    from picorte.ai import llm_router as lr_mod

    _projeto_select(tmp_path, monkeypatch)
    original = lr_mod.LLMRouter._run_provider

    def scout_cai(self, provider, model, system_prompt, user_prompt):
        if "Full-VOD Scout" in system_prompt:
            raise RuntimeError("429 cota")
        return original(self, provider, model, system_prompt, user_prompt)

    monkeypatch.setattr(lr_mod.LLMRouter, "_run_provider", scout_cai)
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    h = health.load(tmp_path)["full_vod_scout"]
    assert h["status"] == "failed" and "429 cota" in h["detail"]


def test_rota_antiga_llm_registra_ollama_fora_do_ar(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch)

    def fora(*a, **k):
        raise ConnectionError("ollama desligado")

    monkeypatch.setattr(sc, "_ollama_chat", fora)
    sc.select(tmp_path, min_score=7.0, max_clips=5, llm="qwen2.5:7b", ai_mode="heuristic")
    h = health.load(tmp_path)["llm_rerank"]
    assert h["status"] == "failed" and "ollama desligado" in h["detail"]


def test_modo_deep_registra_falha_dos_arcos(tmp_path: Path, monkeypatch):
    import picorte.engine.two_act_arc as ta

    _projeto_select(tmp_path, monkeypatch)

    def quebra(*a, **k):
        raise ValueError("arco quebrado")

    monkeypatch.setattr(ta, "detect_two_act_arcs", quebra)
    # formatos_extras=False: o _add_composites também usa o detector, mas lá a falha já é barulhenta (sobe)
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude", hunt_mode="deep", formatos_extras=False)
    h = health.load(tmp_path)["modo_deep"]
    assert h["status"] == "failed" and "arco quebrado" in h["detail"]


def test_run_da_linha_de_comando_repassa_max_len(tmp_path: Path, monkeypatch):
    vistos = {}
    monkeypatch.setattr(sc, "discover", lambda *a, **k: ([], {}))
    monkeypatch.setattr(sc, "select", lambda *a, **k: (vistos.update(k) or ([], "heuristic")))
    monkeypatch.setattr(sc, "_no_clips_message", lambda *a, **k: None)
    (tmp_path / "transcript.json").write_text(json.dumps({"words": [], "duration": 10.0}), encoding="utf-8")
    try:
        sc.run(tmp_path, max_len=45, min_score=7.0)
    except SystemExit:
        pass
    assert vistos.get("max_len") == 45


def test_discover_leva_acertos_de_ocr_do_hud_ate_a_evidencia(tmp_path: Path, monkeypatch):
    import picorte.engine.hud_detector as hd

    mp4 = tmp_path / "source.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=40",
                    "-f", "lavfi", "-i", "sine=frequency=220:duration=40", "-shortest", "-c:v", "mpeg4",
                    "-c:a", "aac", str(mp4)], check=True)
    monkeypatch.setattr(hd, "detect_hud_events", lambda *a, **k: {"score": 7.6, "ocr_hits": 2, "events": [],
                                                                  "degraded": []})
    (tmp_path / "transcript.json").write_text(json.dumps({
        "video": str(mp4), "duration": 40.0, "language": "pt", "words": _fala(40.0)}), encoding="utf-8")
    sc.discover(tmp_path, min_len=8, max_len=30, vision_preset="low")
    cands = json.loads((tmp_path / "candidates.json").read_text(encoding="utf-8"))["candidates"]
    medidos = [c for c in cands if (c.get("evidence") or {}).get("vision_measured")]
    assert medidos and all(c["evidence"]["hud_ocr_hits"] == 2 for c in medidos)


# ------------------------------------------------------------------ W53 na prática: consolidação do Scout cabe no limite

def test_consolidacao_do_scout_cabe_na_linha_de_comando_do_windows():
    """Live real de 4h49 (2026-11-23): 181 eventos num prompt só → WinError 206 (linha de comando > ~32 mil)."""
    from picorte.ai.llm_router import MAX_CLI_PROMPT_CHARS
    from picorte.ai.llm_scout import LONG_VOD_MAPREDUCE_SECONDS, scout_full_vod

    longo = [{"start": i * 20.0, "end": i * 20.0 + 18.0, "text": f"frase {i} do streamer"}
             for i in range(int(LONG_VOD_MAPREDUCE_SECONDS * 3 / 20))]
    tamanhos, consolidacoes = [], []

    def provedor(provider, model, system_prompt, user_prompt):
        tamanhos.append(len(system_prompt) + len(user_prompt))
        if "BLOCO DA TRANSCRIÇÃO" in user_prompt:
            sids = [ln.split("]")[0].lstrip("[") for ln in user_prompt.splitlines() if ln.startswith("[S")]
            return json.dumps([{"start_sid": s, "end_sid": s, "summary": "lance comprido " * 12} for s in sids[:6]])
        consolidacoes.append(user_prompt)
        sid = next(ln.split("..")[0].lstrip("[") for ln in user_prompt.splitlines() if ln.startswith("[S"))
        return json.dumps([{"start_sid": sid, "end_sid": sid, "archetype": "rage_tilt", "why": "x"}])

    out = scout_full_vod(longo, router=LLMRouter(provider_runner=provedor), ai_mode="gemini", max_workers=1,
                         max_findings=20)
    assert max(tamanhos) <= MAX_CLI_PROMPT_CHARS + 2000
    assert len(consolidacoes) >= 2 and out


# ------------------------------------------------------------------ qual modelo respondeu (fim do achismo)

def test_modelo_do_claude_sai_da_resposta_json(monkeypatch):
    import picorte.ai.llm_router as lr

    saida = json.dumps({"result": "[]", "modelUsage": {"claude-opus-5-5": {}, "claude-haiku-5-5": {}}})
    monkeypatch.setattr(lr, "resolve_cli_binary", lambda n: "claude.exe" if n == "claude" else None)
    monkeypatch.setattr(lr.subprocess, "run", lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, saida, ""))
    r = LLMRouter()
    r._run_provider("claude", None, "s", "u")
    assert r.models_seen["claude"] == {"claude-opus-5-5", "claude-haiku-5-5"}


def test_modelo_do_agy_sai_do_registro_dele(monkeypatch):
    """Medido em 2026-11-23: a resposta JSON do agy não traz o modelo; o registro (--log-file) traz."""
    import picorte.ai.llm_router as lr

    def fake_run(cmd, **k):
        log = cmd[cmd.index("--log-file") + 1]
        Path(log).write_text('I1123 model_config_manager.go:375] Propagating selected model override to backend: '
                             'label="Gemini 4 Neon (High)"\n', encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"status": "SUCCESS", "response": "[]"}), "")

    monkeypatch.setattr(lr, "resolve_cli_binary", lambda n: "C:/x/agy.exe" if n == "agy" else None)
    monkeypatch.setattr(lr.subprocess, "run", fake_run)
    r = LLMRouter()
    r._run_provider("gemini", None, "s", "u")
    assert r.models_seen["gemini"] == {"Gemini 4 Neon (High)"}


def test_saude_do_editor_diz_qual_modelo_respondeu(tmp_path: Path, monkeypatch):
    from picorte.ai import llm_router as lr_mod

    _projeto_select(tmp_path, monkeypatch)
    original = lr_mod.LLMRouter._run_provider

    def com_modelo(self, provider, model, system_prompt, user_prompt):
        self.models_seen.setdefault(provider, set()).add("modelo-x")
        return original(self, provider, model, system_prompt, user_prompt)

    monkeypatch.setattr(lr_mod.LLMRouter, "_run_provider", com_modelo)
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    assert "modelo-x" in health.load(tmp_path)["editor"]["detail"]


def test_saude_diz_quando_o_cli_nao_informa_o_modelo(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch)  # o provedor falso não registra modelo
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    assert "modelo não informado pelo CLI" in health.load(tmp_path)["editor"]["detail"]


# ------------------------------------------------------------------ duração padrão e formato em todo corte (aprovado)

def test_duracao_maxima_padrao_e_de_short():
    """Live real do Paulinho: com o padrão de 300 s saíram 'Shorts' de 1 a 5 min."""
    import projects

    assert projects.DEFAULT_OPTIONS["max_len"] == 58
    assert projects.validate_options({})["max_len"] == 58


def test_todo_corte_principal_diz_o_formato():
    from picorte.engine.formats import SHORT_MAX_S

    segs = [{"start": 0.0, "end": 42.0}, {"start": 100.0, "end": 100.0 + SHORT_MAX_S + 1},
            {"start": 300.0, "end": 360.0, "formato": "tiktok_60"}]
    sc._label_formats(segs)
    assert [s["formato"] for s in segs] == ["short", "vertical_longo", "tiktok_60"]


def test_select_grava_o_formato_no_segments_json(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch)
    segs, _ = sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    gravados = json.loads((tmp_path / "segments.json").read_text(encoding="utf-8"))
    assert gravados and all(s.get("formato") for s in gravados)


# ------------------------------------------------------------------ envelope do agy com bloco de código (live real)

def test_resposta_do_agy_com_bloco_de_codigo_e_lida():
    """Live real (2026-11-23): 3 de 41 blocos do batedor 'sem JSON' — o modelo pôs ```json``` dentro do
    envelope {"response": ...} do agy e o leitor tirava a cerca antes de abrir o envelope."""
    from picorte.ai.llm_router import _extract_json_array

    interno = '```json\n[\n  {"start_sid": "S1010", "end_sid": "S1012", "summary": "é assim que o cego vê a balada"}\n]\n```'
    raw = json.dumps({"conversation_id": "x", "status": "SUCCESS", "response": interno})
    out = _extract_json_array(raw)
    assert out == [{"start_sid": "S1010", "end_sid": "S1012", "summary": "é assim que o cego vê a balada"}]


def test_resposta_do_claude_com_bloco_de_codigo_e_lida():
    from picorte.ai.llm_router import _extract_json_array

    raw = json.dumps({"result": '```json\n[{"index": 0, "adjustment": 1.0}]\n```', "modelUsage": {}})
    assert _extract_json_array(raw) == [{"index": 0, "adjustment": 1.0}]


# ------------------------------------------------------------------ redes escolhidas pelo dono (padrão: YouTube Shorts + TikTok)

def test_redes_padrao_sao_youtube_shorts_e_tiktok():
    import projects

    assert projects.validate_options({})["redes"] == ["youtube_shorts", "tiktok"]
    with pytest.raises(ValueError):
        projects.validate_options({"redes": ["orkut"]})
    with pytest.raises(ValueError):
        projects.validate_options({"redes": []})


def test_trocar_as_redes_refaz_a_selecao():
    import projects

    a = projects.validate_options({})
    b = projects.validate_options({"redes": ["youtube_shorts", "tiktok", "youtube_longo"]})
    assert projects.score_keys("t", {"words": []}, a)[1] != projects.score_keys("t", {"words": []}, b)[1]


def test_irmaos_so_das_redes_ligadas():
    from picorte.engine.formats import add_format_siblings

    sents = [{"start": float(i * 3), "end": float(i * 3 + 2.5), "text": f"frase {i}"} for i in range(200)]
    seg = {"start": 300.0, "end": 340.0, "tier": "ouro", "overall": 9.0}
    so_tiktok = add_format_siblings([seg], sents, heatmap_peaks=[], source_duration=600.0, tiktok=True, longo=False)
    assert {s.get("formato") for s in so_tiktok if s.get("formato")} == {"tiktok_60"}
    nada = add_format_siblings([seg], sents, heatmap_peaks=[], source_duration=600.0, tiktok=False, longo=False)
    assert not [s for s in nada if s.get("formato")]


def test_select_respeita_as_redes(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch)
    segs, _ = sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude", redes=["youtube_shorts", "tiktok"])
    fmts = {s.get("formato") for s in segs}
    assert "tiktok_60" in fmts and "longo_16x9" not in fmts
    segs, _ = sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude", redes=["youtube_shorts"])
    assert not {s.get("formato") for s in segs} & {"tiktok_60", "longo_16x9"}


# ------------------------------------------------------------------ live real: timeout de 180 s e batedor refeito

@pytest.mark.parametrize("provedor,cli", [("claude", "claude"), ("gemini", "agy")])
def test_chamada_ao_cli_tem_tempo_para_modelo_lento(monkeypatch, provedor, cli):
    """Live real (2026-11-23): o Gemini 4 Neon (High) levou > 180 s num lote e o Editor parou 2x por timeout."""
    import picorte.ai.llm_router as lr

    vistos = {}

    def fake_run(cmd, **k):
        vistos["timeout"] = k.get("timeout")
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"result": "[]", "response": "[]"}), "")

    monkeypatch.setattr(lr, "resolve_cli_binary", lambda n: f"C:/x/{cli}.exe" if n == cli else None)
    monkeypatch.setattr(lr.subprocess, "run", fake_run)
    LLMRouter()._run_provider(provedor, None, "s", "u")
    assert vistos["timeout"] >= 600


def _contar_scout(monkeypatch, falha_bloco=False):
    from picorte.ai import llm_router as lr_mod

    chamadas = {"scout": 0}
    original = lr_mod.LLMRouter._run_provider

    def conta(self, provider, model, system_prompt, user_prompt):
        if "Full-VOD Scout" in system_prompt or "BLOCO DA TRANSCRIÇÃO" in user_prompt:
            chamadas["scout"] += 1
            if falha_bloco:
                raise RuntimeError("timeout no batedor")
        return original(self, provider, model, system_prompt, user_prompt)

    monkeypatch.setattr(lr_mod.LLMRouter, "_run_provider", conta)
    return chamadas


def test_batedor_nao_e_refeito_quando_a_selecao_roda_de_novo(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch)
    chamadas = _contar_scout(monkeypatch)
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="gemini")
    primeira = chamadas["scout"]
    assert primeira >= 1
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")  # retomada com outro motor
    assert chamadas["scout"] == primeira, "o batedor foi refeito"
    assert "cache" in health.load(tmp_path)["full_vod_scout"]["detail"]


def test_batedor_que_falhou_nao_vai_para_o_cache(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch)
    chamadas = _contar_scout(monkeypatch, falha_bloco=True)
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="gemini")
    assert not (tmp_path / "scout_cache.json").exists()


# ------------------------------------------------------------------ progresso visível durante a seleção (live real)

def test_batedor_avisa_cada_bloco_e_a_consolidacao():
    from picorte.ai.llm_scout import LONG_VOD_MAPREDUCE_SECONDS, scout_full_vod

    longo = [{"start": i * 30.0, "end": i * 30.0 + 25.0, "text": f"frase {i}"}
             for i in range(int(LONG_VOD_MAPREDUCE_SECONDS / 30) + 60)]

    def prov(provider, model, system_prompt, user_prompt):
        if "BLOCO DA TRANSCRIÇÃO" in user_prompt:
            return json.dumps([{"start_sid": "S0001", "end_sid": "S0001", "summary": "x"}])
        return "[]"

    avisos = []
    scout_full_vod(longo, router=LLMRouter(provider_runner=prov), ai_mode="gemini", max_workers=1,
                   on_progress=avisos.append)
    assert any("Batedor: bloco 1/" in a for a in avisos)
    assert any("Batedor: consolidando" in a for a in avisos)


def test_editor_avisa_cada_lote():
    avisos = []
    LLMRouter(provider_runner=_completo).rerank_candidates(_cands(3), ai_mode="gemini", on_progress=avisos.append)
    assert any("Editor-Chefe" in a and "lote 1/1" in a for a in avisos)


def test_select_repassa_o_progresso(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch)
    avisos = []
    sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude", on_progress=avisos.append)
    assert any("Editor-Chefe" in a for a in avisos)
