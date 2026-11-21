"""Etapa 1b (auditoria E3) — Prosódia (riso 3–6 Hz, susto, ritmo de fala) ligada à descoberta e sinais
não verbais medidos chegando ao Editor-Chefe (antes ele via só o texto)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

SR = 16000


def _laugh(sec=6.0):
    t = np.arange(int(SR * sec)) / SR
    return (0.4 * (0.5 + 0.5 * np.sin(2 * math.pi * 4.5 * t)) * np.sin(2 * math.pi * 300 * t)).astype(np.float32)


def _scare(sec=6.0):
    a = np.full(int(SR * sec), 0.002, dtype=np.float32)
    a[int(SR * 3.0):int(SR * 3.4)] = 0.8 * np.sin(2 * math.pi * 900 * np.arange(int(SR * 0.4)) / SR)
    return a


def _flat(sec=6.0):
    return (0.1 * np.sin(2 * math.pi * 200 * np.arange(int(SR * sec)) / SR)).astype(np.float32)


def _cands():
    return [
        {"start": 10.0, "end": 16.0, "overall": 7.0, "text": "kkkkk", "evidence": {}},
        {"start": 50.0, "end": 56.0, "overall": 7.0, "text": "nossa", "evidence": {}},
        {"start": 90.0, "end": 96.0, "overall": 7.0, "text": "ok", "evidence": {}},
    ]


def _decoder(audio_path, start, end):
    return {10.0: _laugh(), 50.0: _scare(), 90.0: _flat()}[float(start)]


def test_prosody_evidence_marks_laugh_scare_and_bonus():
    from picorte.engine.prosody_events import attach_prosody_evidence

    out = attach_prosody_evidence(_cands(), "a.wav", [], decoder=_decoder)
    laugh, scare, flat = out
    assert laugh["evidence"]["laugh"] >= 0.35
    assert scare["evidence"]["jumpscare_db"] >= 18.0
    assert flat["evidence"]["laugh"] < 0.35 and flat["evidence"]["jumpscare_db"] == 0.0
    assert laugh["overall"] > 7.0 and scare["overall"] > 7.0 and flat["overall"] == 7.0
    assert laugh["score_parts"]["prosody_bonus"] > 0


def test_prosody_marks_fast_panic_speech_from_sentences():
    from picorte.engine.prosody_events import attach_prosody_evidence

    sentences = [{"start": float(i * 10), "end": float(i * 10 + 4), "text": "uma frase normal aqui"} for i in range(12)]
    sentences.append({"start": 91.0, "end": 93.0, "text": "corre corre corre vai vai vai sai sai agora rapido"})
    out = attach_prosody_evidence(_cands(), "a.wav", sentences, decoder=_decoder)
    assert out[2]["evidence"]["speech_rate"] == "fast_panic"


def test_prosody_respects_limit_and_survives_decoder_failure():
    from picorte.engine.prosody_events import attach_prosody_evidence

    def broken(*a):
        raise RuntimeError("ffmpeg falhou")

    out = attach_prosody_evidence(_cands(), "a.wav", [], decoder=broken)
    assert all("laugh" not in c["evidence"] for c in out)
    out2 = attach_prosody_evidence(_cands(), "a.wav", [], decoder=_decoder, limit=1)
    assert sum("laugh" in c["evidence"] for c in out2) == 1


def test_4d_fusion_flags_only_really_measured_vision():
    import score_clips

    cands = [{"start": 0.0, "end": 10.0, "overall": 6.0, "evidence": {}, "text": "a"},
             {"start": 30.0, "end": 40.0, "overall": 6.0, "evidence": {}, "text": "b"}]
    out = score_clips.apply_4d_and_snap(cands, words=[], silences=None, duration_s=60.0, chat_seismic=None,
                                        visual_scores={(0.0, 10.0): {"visual_score": 8.0, "hud_score": 2.0}})
    by = {c["text"]: c for c in out}
    assert by["a"]["evidence"]["vision_measured"] is True
    assert not by["b"]["evidence"].get("vision_measured")


def test_editor_chief_receives_only_measured_nonverbal_signals():
    from picorte.ai.llm_router import LLMRouter

    prompts = []

    def fake(provider, model, system_prompt, user_prompt):
        prompts.append(user_prompt)
        rows = json.loads(user_prompt[user_prompt.index("["):])
        return json.dumps([{"index": r["index"], "adjustment": 0.0, "reason": "ok"} for r in rows])

    cands = [
        {"start": 1.0, "end": 9.0, "overall": 8.0, "text": "kkkk caiu",
         "evidence": {"laugh": 0.62, "jumpscare_db": 0.0, "speech_rate": "fast_panic", "chat": 7.5,
                      "chat_measured": True, "visual_games": 8.1, "hud": 3.0, "vision_measured": True}},
        {"start": 20.0, "end": 29.0, "overall": 7.0, "text": "sem medição",
         "evidence": {"visual_games": 7.0, "hud": 0.0, "chat": 0.0}},
    ]
    LLMRouter(provider_runner=fake).rerank_candidates(cands, ai_mode="gemini")
    payload = prompts[0]
    rows = json.loads(payload[payload.index("["):])
    assert rows[0]["sinais"] == {"riso": 0.62, "fala": "fast_panic", "chat": 7.5, "facecam": 8.1, "hud": 3.0}
    assert "sinais" not in rows[1]


def test_discover_attaches_prosody_on_real_audio(tmp_path: Path):
    import subprocess

    import score_clips
    from picorte.config import resolve_cli_binary

    wav = tmp_path / "audio.wav"
    subprocess.run([resolve_cli_binary("ffmpeg") or "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "aevalsrc='0.4*(0.5+0.5*sin(2*PI*4.5*t))*sin(2*PI*300*t)':s=16000:d=40", str(wav)], check=True)
    words, t = [], 0.5
    for tok in ("olha isso aqui cara. que absurdo ele caiu do prédio! inteiro kkkk mano. " * 6).split():
        words.append({"word": tok, "start": round(t, 2), "end": round(t + 0.5, 2)})
        t += 0.6
    (tmp_path / "transcript.json").write_text(json.dumps({
        "video": str(wav), "duration": 40.0, "language": "pt", "words": words}), encoding="utf-8")
    cands, _ = score_clips.discover(tmp_path, min_len=8, max_len=30)
    assert any("laugh" in (c.get("evidence") or {}) for c in cands)
