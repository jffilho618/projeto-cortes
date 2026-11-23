"""Code review do motor — fatia (a) descoberta (2026-11-23).

Cada teste aqui nasceu de um achado verificado no código e nos projetos reais; o nome diz o que quebrava.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import score_clips as sc
from picorte.engine.confidence import independent_signals, tag_technical_failures

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "picorte" / "engine"
DIVERGE_DE_PROPOSITO = {"dashboard.py"}  # W1: o dashboard da raiz diverge de propósito


def _pares_espelho() -> list[str]:
    return sorted(p.name for p in ROOT.glob("*.py")
                  if (ENGINE / p.name).is_file() and p.name not in DIVERGE_DE_PROPOSITO)


# ------------------------------------------------------------------ item 9: espelhos raiz × picorte/engine/

def test_todos_os_pares_espelho_sao_conhecidos():
    """Se um par some (ou nasce), a lista de espelhos do W1 precisa ser revista."""
    assert len(_pares_espelho()) >= 13


@pytest.mark.parametrize("nome", _pares_espelho())
def test_espelho_raiz_e_engine_identicos(nome):
    assert (ROOT / nome).read_bytes() == (ENGINE / nome).read_bytes(), (
        f"{nome} da raiz e de picorte/engine/ divergiram (W1): sincronize as duas cópias")


# ------------------------------------------------------------------ item 3: palavra-chave por palavra inteira

def test_cue_nao_casa_dentro_de_outra_palavra():
    banal = " vamos lá, isso aí, no jogo de novo, ano passado nadei "
    assert sc._cue_hits(banal, sc.EMOTION_CUES) == 0      # "vamos" não é "amo"
    assert sc._cue_hits(banal, sc.PAYOFF_WORDS) == 0      # "isso" não é "so"
    assert sc._cue_hits(banal, sc.NEGATION_WORDS) == 0    # "no"/"nadei" não são "no"/"nada"
    assert sc._cue_hits(" que terror, absoluta dúvida ", sc.CURIOSITY_CUES) == 0  # "terror" não é "erro"
    assert sc._cue_hits(" que terror, absoluta dúvida ", sc.STAKES_WORDS) == 0    # "luta", "vida"


def test_cue_continua_casando_palavra_e_expressao():
    assert sc._cue_hits(" eu amo esse jogo ", sc.EMOTION_CUES) == 1
    assert sc._cue_hits(" não, nem pensar ", sc.NEGATION_WORDS) == 2
    assert sc._cue_hits(" Não acredito! ", sc.HOOK_CUES) == 1          # expressão de 2 palavras com pontuação
    assert sc._cue_hits(" Here's why it works ", sc.HOOK_CUES) == 1    # apóstrofo
    assert sc._cue_hits(" bem-vindos ao canal ", sc.META_OPENERS) == 1  # hífen


def test_frase_banal_de_gameplay_nao_ganha_nota_de_texto():
    sent = {"text": "vamos lá, isso aí, no jogo de novo, ano passado nadei", "start": 0.0, "end": 4.0, "words": []}
    parts, _ = sc.score_sentence(sent)
    assert parts["emotion"] == 0.0


def test_deitico_visual_nao_casa_dentro_de_outra_frase():
    feat = sc.sentence_features({"text": "isso deve ser bom", "start": 0.0, "end": 2.0})
    assert feat["visual_deictic"] is False          # "deve ser" contém "ve se"
    feat = sc.sentence_features({"text": "olha isso aqui", "start": 0.0, "end": 2.0})
    assert feat["visual_deictic"] is True


# ------------------------------------------------------------------ item 4: regra do ouro sem contar o mesmo fato 2×

def test_pico_de_chat_sem_fala_nao_ganha_sinal_de_fala():
    cand = {"seed_kind": "chat_peak", "text": "", "track_origin": "coop_payoff_nontextual",
            "evidence": {"chat_measured": True, "chat": 7.0}}
    assert independent_signals(cand) == ["chat"]


def test_dica_vinda_do_comentario_nao_vira_sinal_de_fala():
    seeds = [{"start": 10.0, "end": 40.0, "text": "12:34 kkkk que burro", "track_origin": "coop_payoff_nontextual",
              "seed_kind": "comment_timestamp", "score_parts": {"comment_likes": 3}}]
    sentences = [{"start": 12.0, "end": 15.0, "text": "ok continuando aqui"}]
    (cand,) = sc.merge_comment_seeds([], seeds, sentences)
    assert cand.get("archetype_hint")                    # a dica continua chegando ao Editor-Chefe
    assert independent_signals(cand) == ["comentario"]


def test_dica_de_falha_tecnica_vinda_do_chat_nao_vira_sinal_de_fala():
    cand = {"start": 0.0, "end": 30.0, "text": "ok", "evidence": {}}
    (tagged,) = tag_technical_failures([cand], [(5.0, 10.0)], [{"t": 12.0, "text": "caiu a live"}], 0.0)
    assert "falha_tecnica" in tagged["tags"] and tagged.get("archetype_hint") == "chat_trolagem"
    assert "fala" not in independent_signals(tagged)


def test_fala_de_verdade_continua_contando():
    coop = {"text": "foi você que me matou, culpa sua", "track_origin": "coop_payoff_nontextual", "evidence": {}}
    assert "fala" in independent_signals(coop)
    vacilo = {"text": "ok", "archetype_hint": "nobada_vacilo", "archetype_hint_source": "fala", "evidence": {}}
    assert "fala" in independent_signals(vacilo)
    antigo = {"text": "ok", "archetype_hint": "nobada_vacilo", "evidence": {}}  # candidates.json de antes
    assert "fala" in independent_signals(antigo)


# ------------------------------------------------------------------ itens 2, 5 e 10a: discover de ponta a ponta

import json  # noqa: E402
import subprocess  # noqa: E402

from picorte.config import resolve_cli_binary  # noqa: E402
from picorte.engine import health  # noqa: E402

FFMPEG = resolve_cli_binary("ffmpeg") or "ffmpeg"


def _fala(duracao: float) -> list[dict]:
    words, t = [], 0.5
    frases = ("olha isso cara. que absurdo mano! ele caiu de novo. " * 40).split()
    for tok in frases:
        if t + 0.5 > duracao:
            break
        words.append({"word": tok, "start": round(t, 2), "end": round(t + 0.5, 2)})
        t += 0.6
    return words


def _projeto(tmp_path: Path, media: Path, duracao: float) -> Path:
    (tmp_path / "transcript.json").write_text(json.dumps({
        "video": str(media), "duration": duracao, "language": "pt", "words": _fala(duracao)}), encoding="utf-8")
    return tmp_path


def test_discover_descarta_candidato_mudo_e_registra_na_saude(tmp_path: Path):
    """P1 (3.6.5): trecho com áudio zerado não vira corte — ligação do filtro dentro do discover."""
    wav = tmp_path / "audio.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "aevalsrc='if(between(t,20,35),0,0.3*sin(2*PI*220*t))':s=16000:d=60", str(wav)], check=True)
    sc.discover(_projeto(tmp_path, wav, 60.0), min_len=8, max_len=30)

    from picorte.engine.confidence import silence_fraction
    cands = json.loads((tmp_path / "candidates.json").read_text(encoding="utf-8"))["candidates"]
    assert cands, "o trecho com som precisa continuar gerando candidatos"
    assert all(silence_fraction(float(c["start"]), float(c["end"]), [(20.0, 35.0)]) <= 0.2 for c in cands)
    assert (tmp_path / "digital_silence.json").is_file()
    h = health.load(tmp_path)["silencio_digital"]
    assert h["status"] == "ok" and "descartados" in h["detail"]


def test_piso_do_silencio_digital_acompanha_o_piso_do_audio():
    """O piso de -79,5 dB do silêncio digital depende do clamp de -80 dB da linha do tempo de áudio."""
    import evidence
    from picorte.engine import confidence

    assert confidence.DIGITAL_SILENCE_FLOOR_DB == evidence.SILENCE_DB + 0.5


def test_discover_com_audio_corrompido_registra_falha_e_nao_na(tmp_path: Path):
    """Sem linha do tempo de áudio o filtro P1 de silêncio digital não roda: isso é falha, não 'não se aplica'."""
    bad = tmp_path / "audio.wav"
    bad.write_bytes(b"isto nao e audio" * 64)
    sc.discover(_projeto(tmp_path, bad, 40.0), min_len=8, max_len=30)
    h = health.load(tmp_path)
    assert h["audio"]["status"] == "failed"
    assert h["silencio_digital"]["status"] == "failed"


def test_discover_com_visao_quebrada_registra_falha_com_motivo(tmp_path: Path, monkeypatch):
    """O laço da visão engolia o erro (except: pass) e a saúde dizia ok quando havia `sections`."""
    import picorte.engine.visual_games as vg

    mp4 = tmp_path / "source.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=40",
                    "-f", "lavfi", "-i", "sine=frequency=220:duration=40", "-shortest", "-c:v", "mpeg4",
                    "-c:a", "aac", str(mp4)], check=True)

    def quebrado(*a, **k):
        raise RuntimeError("decodificador de quadros quebrado")

    monkeypatch.setattr(vg, "sample_video_frames", quebrado)
    sc.discover(_projeto(tmp_path, mp4, 40.0), min_len=8, max_len=30)
    h = health.load(tmp_path)["vision"]
    assert h["status"] == "failed"
    assert "RuntimeError" in h["detail"] and "quebrado" in h["detail"]


# ------------------------------------------------------------------ item 6: portão P1 dos comentários

from picorte.risk_shield import policy_gate  # noqa: E402

NAO_PERMITIDOS = sorted(policy_gate.BLOCKED_PERMISSION_STATUSES | {"pendente", "", "Liberada?"})


@pytest.mark.parametrize("status", NAO_PERMITIDOS)
def test_minerador_so_aceita_status_permitido(status):
    import picorte.engine.comments_miner as cm

    def runner(*a, **k):
        raise AssertionError("o yt-dlp não pode ser chamado para fonte não permitida")

    with pytest.raises(PermissionError):
        cm.mine_youtube_comments("https://youtu.be/x", permission_status=status, runner=runner)


@pytest.mark.parametrize("status", NAO_PERMITIDOS)
def test_cache_de_comentarios_nao_passa_por_cima_do_p1(tmp_path: Path, status):
    """Fonte pausada/bloqueada depois da 1ª coleta: o cache não pode continuar alimentando a descoberta."""
    import picorte.engine.comments_miner as cm

    (tmp_path / "comment_seeds.json").write_text(json.dumps([{"start": 1.0, "end": 9.0}]), encoding="utf-8")
    seen = []
    out = cm.save_comment_seeds("https://youtu.be/x", tmp_path, permission_status=status,
                                on_status=lambda s, d="": seen.append((s, d)))
    assert out is None
    assert seen and seen[0][0] == "na" and "P1" in seen[0][1]


def test_status_permitido_continua_minerando(tmp_path: Path, monkeypatch):
    import picorte.engine.comments_miner as cm

    for status in sorted(policy_gate.ALLOWED_PERMISSION_STATUSES):
        monkeypatch.setattr(cm, "mine_youtube_comments", lambda url, **k: [{"start": 1.0, "end": 9.0}])
        (tmp_path / "comment_seeds.json").unlink(missing_ok=True)
        assert cm.save_comment_seeds("https://youtu.be/x", tmp_path, permission_status=status) is not None


# ------------------------------------------------------------------ item 11: heatmap com nota fraca (3.6.5 AC6)

def test_semente_de_heatmap_nao_sobe_na_fusao_sem_sinal_medido(tmp_path: Path, monkeypatch):
    from picorte.engine.chat_seismic import SEISMIC_VERSION

    wav = tmp_path / "audio.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=60", str(wav)], check=True)
    (tmp_path / "transcript.json").write_text(json.dumps({
        "video": str(wav), "duration": 60.0, "language": "pt", "words": _fala(20.0)}), encoding="utf-8")
    pico = {"start": 40.0, "end": 50.0, "center": 45.0, "value": 0.0}
    monkeypatch.setattr(sc, "_gabarito_heatmap_peaks", lambda workdir, meta: [pico])
    zero = {"vel_zscore": 0.0, "emote_burst": 0.0}
    chat_frio = {"version": SEISMIC_VERSION, "per_second": [dict(zero) for _ in range(60)], "delay_s": 30.0,
                 "peaks": []}
    monkeypatch.setattr(sc, "_load_optional_chat_seismic", lambda w, s, d: (chat_frio, None))

    sc.discover(tmp_path, min_len=8, max_len=30)
    cands = json.loads((tmp_path / "candidates.json").read_text(encoding="utf-8"))["candidates"]
    (seed,) = [c for c in cands if c.get("seed_kind") == "heatmap_peak"]
    assert seed["overall"] == sc.heatmap_seed_overall(0.0)


# ------------------------------------------------------------------ item 10b/10c: ligações do select

def _projeto_select(tmp_path: Path, monkeypatch, standalone: dict[int, float]):
    from picorte.ai import llm_router as lr_mod

    wav = tmp_path / "audio.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=120", str(wav)], check=True)
    (tmp_path / "transcript.json").write_text(json.dumps({
        "video": str(wav), "duration": 120.0, "language": "pt", "words": _fala(120.0)}), encoding="utf-8")
    base = {"seed_kind": "sentence", "score_parts": {}, "evidence": {}, "reason": "teste", "raw_score": 8.0}
    cands = [
        {**base, "start": 2.0, "end": 32.0, "duration": 30.0, "hook": "piada interna", "overall": 8.4,
         "text": "olha isso cara, que absurdo mano, piada interna do canal"},
        {**base, "start": 60.0, "end": 90.0, "duration": 30.0, "hook": "caiu a live", "overall": 8.2,
         "text": "ele caiu de novo, que absurdo", "tags": ["falha_tecnica"]},
    ]
    sc.save_candidates(tmp_path, cands, {"source_duration": 120.0, "content_profile": "mixed"})

    def fake_provider(self, provider, model, system_prompt, user_prompt):
        if "Full-VOD Scout" in system_prompt:
            return "[]"
        rows = json.loads(user_prompt.split("CANDIDATOS JSON:\n", 1)[-1])
        return json.dumps([{"index": r["index"], "adjustment": 0.0, "archetype": "rage_tilt", "tier": "forte",
                            "tone": "hype", "reason": "ok",
                            "standalone": standalone.get(int(float(r.get("start", 0)) // 60), 8.0)}
                           for r in rows])

    monkeypatch.setattr(lr_mod.LLMRouter, "_run_provider", fake_provider)


def test_select_manda_corte_sem_contexto_para_longo_e_preserva_tags(tmp_path: Path, monkeypatch):
    _projeto_select(tmp_path, monkeypatch, standalone={0: 3.0})
    segments, _ = sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    shorts = [s for s in segments if not s.get("formato")]  # a versão TikTok irmã (3.7.3) é do mesmo momento
    assert [round(s["start"]) for s in shorts] == [60]
    assert "falha_tecnica" in shorts[0].get("tags", [])
    longos = json.loads((tmp_path / "longo_compilacao.json").read_text(encoding="utf-8"))
    assert [round(s["start"]) for s in longos] == [2]


def test_select_estende_o_fim_ate_o_riso_acabar(tmp_path: Path, monkeypatch):
    import picorte.engine.prosody_events as pe

    _projeto_select(tmp_path, monkeypatch, standalone={})

    def estende(segments, video, **k):
        return [{**s, "end": float(s["end"]) + 1.0, "evidence": {**(s.get("evidence") or {}), "end_after_laugh_s": 1.0}}
                for s in segments]

    monkeypatch.setattr(pe, "extend_end_past_laugh", estende)
    segments, _ = sc.select(tmp_path, min_score=7.0, max_clips=5, ai_mode="claude")
    assert segments and all((s.get("evidence") or {}).get("end_after_laugh_s") == 1.0 for s in segments)
    assert health.load(tmp_path)["end_after_laugh"]["status"] == "ok"


# ------------------------------------------------------------------ item 7a: susto de verdade, não fala após pausa

import numpy as np  # noqa: E402

SR = 16000


def _voz(seg: float, amp: float) -> np.ndarray:
    t = np.arange(int(seg * SR)) / SR
    return (amp * np.sin(2 * np.pi * 200 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)


def _sala(seg: float, amp: float = 0.001) -> np.ndarray:
    return (amp * np.random.default_rng(0).standard_normal(int(seg * SR))).astype(np.float32)


def test_fala_depois_de_pausa_nao_e_susto():
    from picorte.engine.prosody_events import detect_jumpscare_spike

    audio = np.concatenate([_voz(3, 0.1), _sala(2.5), _voz(3, 0.1), _sala(2.5), _voz(3, 0.1)])
    assert detect_jumpscare_spike(audio, sample_rate=SR)["detected"] is False


def test_volta_do_noise_gate_nao_e_susto():
    from picorte.engine.prosody_events import detect_jumpscare_spike

    audio = np.concatenate([_voz(3, 0.1), np.zeros(int(2.5 * SR), np.float32), _voz(3, 0.1)])
    out = detect_jumpscare_spike(audio, sample_rate=SR)
    assert out["detected"] is False and out["jump_db"] < 60  # -120 dB do zero absoluto não vira salto de 97 dB


def test_grito_depois_de_silencio_tenso_e_susto():
    from picorte.engine.prosody_events import detect_jumpscare_spike

    audio = np.concatenate([_voz(3, 0.1), _sala(2.5), _voz(1.0, 0.7), _voz(3, 0.1)])
    out = detect_jumpscare_spike(audio, sample_rate=SR)
    assert out["detected"] is True
    assert 5.4 <= out["spike_time_s"] <= 5.9


def test_fala_continua_nao_e_susto():
    from picorte.engine.prosody_events import detect_jumpscare_spike

    assert detect_jumpscare_spike(_voz(9, 0.1), sample_rate=SR)["detected"] is False


# ------------------------------------------------------------------ item 8a: HUD só vale como sinal com OCR

def _quadros(n=6):
    return [np.full((240, 320, 3), (i * 40) % 255, dtype=np.uint8) for i in range(n)]  # topo muda: "movimento"


def _carros(frame):
    return [{"label": "car", "class_id": 2, "conf": 0.9, "bbox": [0, 0, 50, 50]} for _ in range(6)]


def test_hud_sem_ocr_e_so_bonus_pequeno():
    """Sem texto do jogo lido, movimento no topo + carros do COCO não podem chegar à nota de 'lance de jogo'."""
    from picorte.engine.hud_detector import detect_hud_events

    out = detect_hud_events(_quadros(), 0.0, 6.0, vision_preset="high",
                            ocr_runner=lambda f, i: [], yolo_runner=_carros)
    assert out["ocr_hits"] == 0
    assert out["score"] <= 2.0


def test_hud_le_palavras_do_jogo_em_portugues():
    from picorte.engine.hud_detector import detect_hud_events

    textos = {0: ["VOCÊ ELIMINOU FULANO"], 2: ["ELIMINADO"], 4: ["VITÓRIA ROYALE"]}
    out = detect_hud_events(_quadros(), 0.0, 6.0, vision_preset="low",
                            ocr_runner=lambda f, i: textos.get(i, []))
    assert out["ocr_hits"] == 3


def test_sinal_hud_do_ouro_exige_texto_lido_pelo_ocr():
    so_ruido = {"vision_measured": True, "hud": 5.9, "hud_ocr_hits": 0}
    assert "hud" not in independent_signals({"text": "", "evidence": so_ruido})
    com_texto = {"vision_measured": True, "hud": 5.9, "hud_ocr_hits": 2}
    assert "hud" in independent_signals({"text": "", "evidence": com_texto})


def test_editor_chefe_so_recebe_hud_com_texto_lido():
    from picorte.ai.llm_router import _measured_signals

    assert "hud" not in _measured_signals({"vision_measured": True, "visual_games": 3.5, "hud": 5.9,
                                           "hud_ocr_hits": 0})
    assert _measured_signals({"vision_measured": True, "visual_games": 3.5, "hud": 5.9, "hud_ocr_hits": 1})["hud"] == 5.9


def test_discover_leva_os_acertos_de_ocr_para_a_evidencia():
    cand = {"start": 0.0, "end": 10.0, "overall": 7.0, "raw_score": 7.0, "evidence": {}}
    (out,) = sc.apply_4d_and_snap([cand], visual_scores={(0.0, 10.0): {"visual_score": 3.0, "hud_score": 4.0,
                                                                         "hud_ocr_hits": 2}})
    assert out["evidence"]["hud_ocr_hits"] == 2


# ------------------------------------------------------------------ item 1: visão que degrada avisa

import sys  # noqa: E402


@pytest.fixture
def sem_bibliotecas_de_visao(monkeypatch):
    """Simula o PC de 2026-11-23: mediapipe, hsemotion e rapidocr ausentes (o YOLO existe)."""
    import picorte.engine.hud_detector as hd
    import picorte.engine.visual_games as vg

    for mod in ("mediapipe", "hsemotion", "hsemotion.facial_emotions", "hsemotion_onnx",
                "hsemotion_onnx.facial_emotions", "rapidocr_onnxruntime"):
        monkeypatch.setitem(sys.modules, mod, None)
    vg._default_landmark_runner_factory.cache_clear()
    vg._default_emotion_runner_factory.cache_clear()
    hd._default_ocr_runner_factory.cache_clear()
    yield
    vg._default_landmark_runner_factory.cache_clear()
    vg._default_emotion_runner_factory.cache_clear()
    hd._default_ocr_runner_factory.cache_clear()


def test_facecam_sem_mediapipe_diz_que_nao_mediu_rosto(sem_bibliotecas_de_visao):
    from picorte.engine.visual_games import analyze_facecam_reactions

    out = analyze_facecam_reactions(_quadros(), 0.0, 6.0, vision_preset="high")
    assert out["face_measured"] is False
    assert any("MediaPipe" in d for d in out["degraded"]) and any("HSEmotion" in d for d in out["degraded"])
    assert "degradado" in out["backend_used"]


def test_hud_sem_rapidocr_diz_que_nao_leu_texto(sem_bibliotecas_de_visao):
    from picorte.engine.hud_detector import detect_hud_events

    out = detect_hud_events(_quadros(), 0.0, 6.0, vision_preset="low")
    assert any("RapidOCR" in d for d in out["degraded"])
    assert "degradado" in out["backend_used"]


def test_runner_injetado_nao_conta_como_degradado():
    from picorte.engine.visual_games import analyze_facecam_reactions

    pts = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (2.0, 1.0), (1.0, 1.0)]
    out = analyze_facecam_reactions(_quadros(), 0.0, 6.0, vision_preset="low", landmark_runner=lambda f: pts)
    assert out["face_measured"] is True and out["degraded"] == []


def test_facecam_so_de_movimento_nao_vai_ao_editor_nem_ao_ouro():
    from picorte.ai.llm_router import _measured_signals

    ev = {"vision_measured": True, "facecam_measured": False, "visual_games": 9.0}
    assert "facecam" not in _measured_signals(ev)
    assert "visao" not in independent_signals({"text": "", "evidence": ev})
    ev_ok = {"vision_measured": True, "facecam_measured": True, "visual_games": 9.0}
    assert _measured_signals(ev_ok)["facecam"] == 9.0
    assert "visao" in independent_signals({"text": "", "evidence": ev_ok})


def test_discover_com_visao_degradada_registra_falha(tmp_path: Path, sem_bibliotecas_de_visao):
    mp4 = tmp_path / "source.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=40",
                    "-f", "lavfi", "-i", "sine=frequency=220:duration=40", "-shortest", "-c:v", "mpeg4",
                    "-c:a", "aac", str(mp4)], check=True)
    sc.discover(_projeto(tmp_path, mp4, 40.0), min_len=8, max_len=30, vision_preset="low")
    h = health.load(tmp_path)["vision"]
    assert h["status"] == "failed" and "MediaPipe" in h["detail"] and "RapidOCR" in h["detail"]
    cands = json.loads((tmp_path / "candidates.json").read_text(encoding="utf-8"))["candidates"]
    medidos = [c for c in cands if (c.get("evidence") or {}).get("vision_measured")]
    assert medidos and all(c["evidence"]["facecam_measured"] is False for c in medidos)


# ------------------------------------------------------------------ itens 12 e A1: emoção no rosto recortado

_BOCA_FECHADA = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (2.0, 0.0), (1.0, 0.0)]
_ROSTO = (40, 40, 100, 120)  # (x, y, w, h) da facecam nos quadros de teste
_N = 20                       # 10 s a 2 quadros/s
_PARADOS = [np.zeros((240, 320, 3), dtype=np.uint8) for _ in range(_N)]


def _serie(base: dict, pico: dict | None = None, onde=(10, 13)) -> list[dict]:
    """Rosto 'normal' do streamer o trecho todo e, se houver, uma reação de 2 s (4 quadros a 2 quadros/s)."""
    return [dict(pico) if (pico and onde[0] <= i <= onde[1]) else dict(base) for i in range(_N)]


def _facecam(serie: list[dict], *, landmarks=lambda f: _BOCA_FECHADA, rosto=_ROSTO, vistos=None) -> dict:
    from picorte.engine.visual_games import analyze_facecam_reactions

    it = iter(serie)

    def emo(crop):
        if vistos is not None:
            vistos.append(crop.shape)
        return next(it)

    return analyze_facecam_reactions(_PARADOS, 0.0, 10.0, vision_preset="high", landmark_runner=landmarks,
                                     emotion_runner=emo, face_locator=lambda f: rosto)


BRAVO = {"anger": 0.65, "neutral": 0.1, "fear": 0.05, "surprise": 0.04, "happiness": 0.05}  # viés medido (ae5f08)


def test_rosto_normal_bravo_nao_conta_como_reacao():
    """O modelo dá 'raiva' ao rosto concentrado de quem joga (25 de 29 quadros na ae5f08): não é reação."""
    assert _facecam(_serie(BRAVO))["emotion_peak"] <= 0.05


def test_reacao_sustentada_sobre_o_rosto_normal_e_reacao():
    out = _facecam(_serie(BRAVO, {"anger": 0.04, "happiness": 0.95}))  # risada de 0:40:05 da ae5f08
    assert out["emotion_peak"] >= 0.5


def test_pico_de_um_segundo_nao_e_reacao_sustentada():
    """Medido na ae5f08: o modelo oscila quadro a quadro; com 1 s bastando, 11 de 12 candidatos davam ≥ 0,5."""
    out = _facecam(_serie(BRAVO, {"anger": 0.08, "fear": 0.83, "neutral": 0.04}, onde=(10, 11)))
    assert out["emotion_peak"] <= 0.1


def test_emocao_que_nao_e_reacao_nao_conta():
    assert _facecam(_serie(BRAVO, {"anger": 0.05, "sadness": 0.9}))["emotion_peak"] <= 0.05


def test_rosto_neutro_nao_conta_como_empolgacao():
    assert _facecam(_serie(BRAVO, {"neutral": 0.95}))["emotion_peak"] <= 0.05


def test_emocao_mais_forte_nunca_da_nota_menor():
    notas = [_facecam(_serie(BRAVO, {"anger": 0.1, "happiness": v}))["score"] for v in (0.2, 0.39, 0.4, 0.7, 1.0)]
    assert notas == sorted(notas), notas


def test_emocao_e_medida_no_rosto_recortado_nao_no_quadro():
    vistos = []
    _facecam(_serie(BRAVO), vistos=vistos)
    assert vistos and all(h < 240 and w < 320 for h, w, *_ in vistos)


def test_rosto_pequeno_demais_nao_mede_emocao_e_diz_por_que():
    out = _facecam(_serie(BRAVO), rosto=(10, 10, 30, 40))  # proxy de 240p: rosto de ~30 px
    assert out["emotion_measured"] is False
    assert any("pequeno" in d for d in out["degraded"])


def test_sem_boca_medida_a_emocao_ganha_o_peso_dela():
    """Sem MediaPipe (MAR não medido), a boca não entra como zero: a emoção leva o peso dela (0,65 em vez de 0,35).
    Passar do limiar do sinal 'visão' (6,5) ainda exige movimento da cabeça junto — aqui os quadros estão parados."""
    from picorte.engine.visual_games import UnavailableBackend

    sem_mp = UnavailableBackend("MediaPipe", ImportError("x"), lambda: None)
    serie = _serie(BRAVO, {"anger": 0.02, "fear": 0.97, "surprise": 0.01}, onde=(8, 13))
    out = _facecam(serie, landmarks=sem_mp)
    assert out["face_measured"] is True and out["emotion_measured"] is True
    assert out["emotion_peak"] >= 0.8
    assert out["score"] >= 0.6 * 10 * out["emotion_peak"]  # antes: 0,35 × emoção (≈ 3,2)


def test_fabrica_hsemotion_onnx_devolve_as_8_emocoes():
    pytest.importorskip("hsemotion_onnx")
    if not (Path.home() / ".hsemotion" / "enet_b0_8_best_vgaf.onnx").is_file():
        pytest.skip("modelo do HSEmotion não baixado nesta máquina")
    import picorte.engine.visual_games as vg

    vg._default_emotion_runner_factory.cache_clear()
    run = vg._default_emotion_runner_factory()
    out = run(np.full((120, 100, 3), 128, dtype=np.uint8))
    assert set(out) == {"anger", "contempt", "disgust", "fear", "happiness", "neutral", "sadness", "surprise"}
    assert abs(sum(out.values()) - 1.0) < 1e-3


# ------------------------------------------------------------------ A1 (custo): OCR e rosto sem travar a descoberta

def test_ocr_espacado_nao_rele_a_tela_parada():
    """Medido na ae5f08: ~8 textos fixos por quadro no topo e 0,8–1 s de OCR por quadro."""
    from picorte.engine.hud_detector import detect_hud_events

    chamadas = []
    parado = [np.full((240, 320, 3), 90, dtype=np.uint8) for _ in range(12)]
    detect_hud_events(parado, 0.0, 12.0, vision_preset="low", ocr_runner=lambda f, i: chamadas.append(i) or [],
                      ocr_every_s=3.0)
    assert chamadas == [0]


def test_ocr_espacado_le_de_novo_quando_a_tela_muda():
    from picorte.engine.hud_detector import detect_hud_events

    chamadas = []
    mudando = [np.full((240, 320, 3), (i * 30) % 250, dtype=np.uint8) for i in range(12)]
    out = detect_hud_events(mudando, 0.0, 12.0, vision_preset="low",
                            ocr_runner=lambda f, i: chamadas.append(i) or (["ELIMINADO"] if i == 6 else []),
                            ocr_every_s=3.0)
    assert chamadas == [0, 3, 6, 9] and out["ocr_hits"] == 1


def test_localizador_de_rosto_rapido_devolve_caixa_na_escala_do_quadro(monkeypatch):
    import picorte.engine.reaction_layout as rl
    from picorte.engine.visual_games import locate_face_fast

    vistos = []

    def fake(frame):
        vistos.append(frame.shape[1])
        return (100, 50, 30, 40)

    monkeypatch.setattr(rl, "find_reactor_face", fake)
    assert locate_face_fast(np.zeros((720, 1280, 3), dtype=np.uint8)) == (200, 100, 60, 80)
    assert vistos == [640]


def test_motivos_da_visao_degradada_cabem_numa_linha():
    motivos = ["MediaPipe indisponível (ModuleNotFoundError: x)"] + [
        f"rosto pequeno demais para medir emoção ({px} px < 64 px)" for px in (49, 46, 57, 45, 40)]
    out = sc._merge_vision_reasons(motivos)
    assert out == ["MediaPipe indisponível (ModuleNotFoundError: x)",
                   "rosto pequeno demais para medir emoção em 5 candidatos (até 57 px < 64 px)"]


# ------------------------------------------------------------------ decisão (a) do dono: susto vira "pico sonoro"

def test_pico_sonoro_nao_da_bonus_automatico():
    """Ouvido pelo dono em 2026-11-23: de 3 picos, 1 susto real, 1 som do jogo (granada), 1 grito agradecendo doação."""
    from picorte.engine.prosody_events import attach_prosody_evidence

    def tom(seg, amp):  # sem a modulação de 4 Hz da `_voz`, que o detector de riso confunde com risada (W28)
        return (amp * np.sin(2 * np.pi * 200 * np.arange(int(seg * SR)) / SR)).astype(np.float32)

    grito = np.concatenate([tom(3, 0.1), _sala(2.5), tom(1.0, 0.7), tom(3, 0.1)])
    (out,) = attach_prosody_evidence([{"start": 0.0, "end": 9.5, "overall": 7.0, "text": "obrigado pelos 10 reais",
                                       "evidence": {}}], "a.wav", [], decoder=lambda p, s, e: grito)
    assert out["evidence"]["jumpscare_db"] >= 18.0   # continua medido
    assert out["overall"] == 7.0                       # sem o +0,8 automático
    assert "prosody_bonus" not in out["score_parts"]


def test_pico_sonoro_nao_conta_como_sinal_do_ouro():
    assert "susto" not in independent_signals({"text": "", "evidence": {"jumpscare_db": 30.0}})


def test_editor_recebe_pico_sonoro_com_instrucao_de_conferir_pela_fala():
    from picorte.ai.llm_router import COMPANION_SYSTEM_PROMPT, _measured_signals

    sinais = _measured_signals({"jumpscare_db": 27.4})
    assert sinais == {"pico_sonoro_db": 27.4}
    assert "pico_sonoro_db" in COMPANION_SYSTEM_PROMPT and "doação" in COMPANION_SYSTEM_PROMPT
