"""Story 3.6.2 — Sismógrafo 2.0: atraso compensado, anti-ruído e tipo de reação.

Medição própria (2026-11-21, x50ONQrBPRM): o chat sobe ~20 s e tem pico em +25–35 s depois do lance.
Hoje o pico vira janela [pico−6, pico+8] e o corte nasce ~25 s depois da causa.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from picorte.engine import chat_seismic as cs


def _msgs(pairs):
    return [{"t": float(t), "text": txt} for t, txt in pairs]


# ---------------------------------------------------------------- Task 1: anti-ruído

@pytest.mark.parametrize("text", ["!sorteio", "!pix", "https://bit.ly/xyz", "olha www.loja.com.br", "  "])
def test_noise_messages_are_detected(text):
    assert cs.is_noise(text)


@pytest.mark.parametrize("text", ["KKKKKKK", "F", "que isso mano", "CLIPA"])
def test_real_reactions_are_not_noise(text):
    assert not cs.is_noise(text)


def test_same_author_flooding_a_long_text_is_dropped():
    spam = "SIGAM O CANAL DO MEU AMIGO QUE ELE FAZ LIVE TODO DIA"
    msgs = [{"t": t, "text": spam, "author": "bot1"} for t in (10.0, 12.0, 15.0)]
    msgs += [{"t": 11.0 + i, "text": "KKKK", "author": f"u{i}"} for i in range(4)]
    kept, dropped = cs.drop_spam(msgs)
    assert dropped == 3
    assert [m["text"] for m in kept] == ["KKKK"] * 4


def test_crowd_chant_and_long_laughs_without_author_are_kept():
    # chat real (2026-11-21): sem autor não dá para separar bot de multidão — o coro é concordância
    chant = "SE ZELDA PERDER PRA ISSO VAI SER A MAIOR INJUSTIÇA"
    msgs = _msgs([(10 + i, chant) for i in range(5)] + [(20 + i, "kkkkkkkkkkkkkkkkkkkkkk") for i in range(5)]
                 + [(30 + i, ":face-green-smiling::face-green-smiling::face-green-smiling:") for i in range(5)])
    kept, dropped = cs.drop_spam(msgs)
    assert dropped == 0 and len(kept) == 15


def test_analyze_ignores_noise_when_counting():
    msgs = _msgs([(5, "!sorteio")] * 50 + [(6, "oi")])
    out = cs.analyze_chat_seismic(msgs, duration_s=60)
    assert out["noise_dropped"] == 50
    assert sum(r["msg_count"] for r in out["per_second"]) == 1


# ---------------------------------------------------------------- Task 2: tipo de reação e concordância

def test_reaction_laugh():
    r = cs.classify_reaction(["kkkkk", "KKKKKKK", "hahaha", "😂😂", "mano"])
    assert r["tipo"] == "riso"


def test_clip_request_wins_with_two_mentions():
    r = cs.classify_reaction(["kkkk"] * 10 + ["CLIPA", "corta essa"])
    assert r["tipo"] == "pedido_corte"


@pytest.mark.parametrize("texts,tipo", [
    (["SOCORRO", "que susto", "😱"], "susto"),
    (["que vergonha", "cringe demais", "😬"], "cringe"),
    (["F", "F", "rip"], "luto"),
    (["INSANO", "que isso", "🔥🔥"], "hype"),
    (["❤️", "que lindo", "fofo"], "amor"),
])
def test_reaction_types(texts, tipo):
    assert cs.classify_reaction(texts)["tipo"] == tipo


def test_reaction_none_when_nothing_matches():
    assert cs.classify_reaction(["boa noite", "de onde vc é"])["tipo"] is None


def _burst(center, n, text, spread=4.0):
    return [(center + spread * i / max(1, n - 1), text) for i in range(n)]


def test_short_agreeing_peak_outweighs_long_varied_peak_with_same_volume():
    base = [(float(s), "oi") for s in range(0, 600, 3)]
    short = _burst(150, 40, "KKKK")
    long_ = [(450 + 4 * i / 39, f"nossa que jogada incrível essa daí número {i}") for i in range(40)]
    out = cs.analyze_chat_seismic(_msgs(base + short + long_), duration_s=600)
    peaks = out["peaks"]
    assert len(peaks) >= 2
    assert abs(peaks[0]["peak_second"] - 150) <= 6        # o curto e concordante vem primeiro
    assert peaks[0]["short_frac"] > peaks[1]["short_frac"]
    assert peaks[0]["reaction_type"] == "riso"


# ---------------------------------------------------------------- Task 3: calibração do atraso

def _series_with_delay(delay, n=3000, seed=7):
    rng = np.random.default_rng(seed)
    audio = np.zeros(n)
    events = rng.choice(np.arange(60, n - 120), size=40, replace=False)
    audio[events] = rng.uniform(5, 15, size=40)
    chat = rng.poisson(3.0, size=n).astype(float)
    for e in events:
        chat[e + delay: e + delay + 3] += 25
    return chat, audio


def test_calibration_finds_the_chat_delay():
    chat, audio = _series_with_delay(27)
    cal = cs.calibrate_delay(chat, audio)
    assert abs(cal["delay_s"] - 27) <= 2
    assert cal["confiavel"] is True
    assert cal["strength"] >= 2.0


def test_calibration_falls_back_to_30s_on_noise():
    rng = np.random.default_rng(1)
    cal = cs.calibrate_delay(rng.poisson(3.0, 3000).astype(float), rng.random(3000))
    assert cal["delay_s"] == 30 and cal["confiavel"] is False


def test_calibration_never_leaves_15_to_45s():
    chat, audio = _series_with_delay(70)
    assert 15 <= cs.calibrate_delay(chat, audio)["delay_s"] <= 45


def test_audio_jump_ignores_return_from_digital_silence():
    rms = np.array([-30.0, -30.0, -80.0, -80.0, -28.0, -12.0, -30.0])
    base = np.full(7, -30.0)
    jump = cs.audio_jump_series(rms, base)
    assert jump[4] == 0.0                     # volta do silêncio digital não é "lance"
    assert int(jump.argmax()) == 5


# ---------------------------------------------------------------- Task 4: âncora da causa e janela deslocada

def test_cause_anchor_is_strongest_audio_jump_before_the_peak():
    jump = np.zeros(400)
    jump[172] = 9.0
    jump[195] = 20.0                          # depois de t−15: não pode ser a causa
    jump[140] = 30.0                          # antes de t−45: também não
    cause, strength = cs.anchor_cause(200, jump, delay_s=30)
    assert cause == 172 and strength == 9.0


def test_cause_without_audio_is_peak_minus_delay():
    assert cs.anchor_cause(200, None, delay_s=28) == (172, 0.0)


def test_peak_window_starts_at_the_cause():
    base = [(float(s), "oi") for s in range(0, 400, 3)]
    burst = _burst(200, 40, "KKKK", spread=3.0)
    jump = np.zeros(400)
    jump[172] = 9.0
    out = cs.analyze_chat_seismic(_msgs(base + burst), duration_s=400, audio_jump=jump, delay_s=30)
    pk = out["peaks"][0]
    assert pk["cause_second"] == 172
    assert pk["start"] == pytest.approx(164.0) and pk["end"] == pytest.approx(186.0)
    assert out["version"] == 2 and out["delay_s"] == 30


def test_chat_window_credits_reaction_that_comes_after_the_clip():
    base = [(float(s), "oi") for s in range(0, 400, 3)]
    out = cs.analyze_chat_seismic(_msgs(base + _burst(200, 40, "KKKK", spread=3.0)), duration_s=400,
                                  audio_jump=np.zeros(400), delay_s=30)
    causa = cs.score_chat_window(out, 165, 195)     # o lance: o chat chega ~30 s depois
    depois = cs.score_chat_window(out, 196, 215)    # a reação em si
    assert causa > depois
    assert causa >= 6.0


def test_old_v1_seismic_keeps_old_window_behavior():
    v1 = {"duration_s": 10, "per_second": [{"t": i, "msg_count": 0, "vel_zscore": 0.0, "emote_burst": 0.0}
                                            for i in range(10)], "peaks": []}
    v1["per_second"][5]["vel_zscore"] = 5.5
    assert cs.score_chat_window(v1, 4, 6) > 0


# ---------------------------------------------------------------- Task 5: carga, chat pequeno, cache v2, saúde

def _write_chat(workdir: Path, n_msgs: int, duration: float, text="kkkk"):
    msgs = [{"t": round(duration * i / max(1, n_msgs), 3), "text": text} for i in range(n_msgs)]
    (workdir / "chat.json").write_text(json.dumps(msgs), encoding="utf-8")


def test_loader_turns_seismograph_off_when_chat_is_too_small(tmp_path):
    import score_clips

    _write_chat(tmp_path, 300, 3600.0)                    # 5 msg/min
    seismic, motivo = score_clips._load_optional_chat_seismic(tmp_path, None, 3600.0)
    assert seismic is None
    assert "chat pequeno demais" in motivo


def test_loader_rate_uses_only_the_span_covered_by_a_partial_chat(tmp_path):
    import score_clips

    _write_chat(tmp_path, 1800, 600.0)                    # 180 msg/min nos 10 min baixados, VOD de 11 h
    seismic, motivo = score_clips._load_optional_chat_seismic(tmp_path, None, 40000.0)
    assert seismic is not None and motivo is None


def test_loader_rebuilds_old_v1_cache(tmp_path):
    import score_clips

    _write_chat(tmp_path, 6000, 600.0)
    (tmp_path / "chat_seismic.json").write_text(json.dumps({"duration_s": 1, "per_second": [], "peaks": []}),
                                                encoding="utf-8")
    seismic, _ = score_clips._load_optional_chat_seismic(tmp_path, None, 600.0)
    assert seismic["version"] == 2


def test_loader_calibrates_with_audio_features(tmp_path):
    import score_clips

    _write_chat(tmp_path, 6000, 600.0)
    np.savez(tmp_path / "audio_features.npz", rms=np.full(600, -30.0, dtype=np.float32),
             baseline=np.full(600, -30.0, dtype=np.float32))
    seismic, _ = score_clips._load_optional_chat_seismic(tmp_path, None, 600.0)
    assert seismic["delay"]["fonte"] == "calibrado"


def test_engine_mirror_has_the_new_loader():
    import score_clips
    from picorte.engine import score_clips as engine_sc

    assert Path(score_clips.__file__).read_text(encoding="utf-8") == \
        Path(engine_sc.__file__).read_text(encoding="utf-8")


# ---------------------------------------------------------------- Task 6: tipo de reação até o Editor-Chefe

def test_apply_4d_passes_the_reaction_type_of_the_peak_caused_inside_the_clip():
    import score_clips

    base = [(float(s), "oi") for s in range(0, 400, 3)]
    jump = np.zeros(400)
    jump[172] = 9.0
    seismic = cs.analyze_chat_seismic(_msgs(base + _burst(200, 40, "KKKK", spread=3.0)), duration_s=400,
                                      audio_jump=jump, delay_s=30)
    out = score_clips.apply_4d_and_snap([{"start": 165.0, "end": 190.0, "overall": 7.0, "evidence": {}}],
                                        chat_seismic=seismic, duration_s=400.0)
    assert out[0]["evidence"]["chat_reaction"] == "riso"


def test_editor_chief_receives_measured_reaction_and_clip_request():
    from picorte.ai.llm_router import _measured_signals

    sig = _measured_signals({"chat_measured": True, "chat": 7.2, "chat_reaction": "pedido_corte"})
    assert sig["reacao_chat"] == "pedido_corte" and sig["pedido_corte"] is True
    assert "reacao_chat" not in _measured_signals({"chat_reaction": "riso"})      # sem medição, não vai


# ---------------------------------------------------------------- Task 8: chat real (x50ONQrBPRM, medição de 2026-11-21)

def _real_project(video_id: str):
    import os

    root = Path(os.environ.get("PICORTE_PROJECTS_DIR", "projects"))
    for pj in sorted(root.glob("*/project.json")) if root.is_dir() else []:
        try:
            if video_id in str(json.loads(pj.read_text(encoding="utf-8")).get("source") or ""):
                return pj.parent
        except (OSError, ValueError):
            continue
    return None


def test_real_chat_of_x50_calibrates_inside_15_45s():
    import score_clips

    proj = _real_project("x50ONQrBPRM")
    if proj is None or not (proj / "chat.json").is_file() or not (proj / "audio_features.npz").is_file():
        pytest.skip("chat real do x50ONQrBPRM não está nesta máquina")
    msgs = cs.parse_chat_log(proj / "chat.json")
    jump = score_clips._audio_jump_for(proj)
    out = cs.analyze_chat_seismic(msgs, duration_s=float(len(jump)), audio_jump=jump)
    cal = out["delay"]
    assert 15 <= cal["delay_s"] <= 45
    assert cal["fonte"] == "calibrado" and cal["strength"] is not None
    assert out["peaks"] and all("reaction_type" in p and "cause_second" in p for p in out["peaks"])


# ---------------------------------------------------------------- Task 7: autor no parser do chat do YouTube

def test_youtube_chat_parser_keeps_author():
    import ingest

    row = {"replayChatItemAction": {"videoOffsetTimeMsec": "12500", "actions": [{"addChatItemAction": {"item": {
        "liveChatTextMessageRenderer": {"message": {"runs": [{"text": "KKKK"}]},
                                        "authorExternalChannelId": "UCabc", "authorName": {"simpleText": "fulano"}}}}}]}}
    assert ingest._live_chat_row_messages(row) == [{"t": 12.5, "text": "KKKK", "author": "UCabc"}]
