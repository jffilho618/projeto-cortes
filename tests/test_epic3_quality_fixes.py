from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_ptbr_scoring_recognizes_portuguese_hooks_and_emotion():
    import score_clips

    pt_seg = {
        "start": 0.0,
        "end": 35.0,
        "text": (
            "Cara, olha isso! Eu não acredito que colocaram sistema de peso, "
            "sono e musculatura absurdamente detalhado no jogo. "
            "O segredo é como funciona a diferença na prática, incrível!"
        ),
        "words": [{"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, w in enumerate(["a"] * 40)],
    }
    scores, text_score = score_clips.score_sentence(pt_seg)
    assert scores["hook"] > 0.0
    assert scores["emotion"] > 0.0
    assert scores["payoff"] > 0.0
    assert text_score >= 5.5


def test_select_candidates_preserves_ai_copy_fields_and_full_reason():
    import score_clips

    long_reason = "Momento histórico e de altíssimo engajamento: " + ("detalhe muito importante " * 10)
    cand = {
        "start": 100.0,
        "end": 145.0,
        "hook": "sistema absurdo",
        "overall": 8.8,
        "raw_score": 6.2,
        "score_parts": {"hook": 0.5},
        "reason": long_reason,
        "proposed_title": "SISTEMAS INSANOS DO GTA 6!",
        "context_banner_2s": "Peso, sono e musculatura no GTA 6",
        "thumbnail_words": "NÍVEL SAN ANDREAS!",
        "pinned_comment_debate": "Você vai deixar o personagem maromba?",
        "llm_mode_used": "gemini",
        "evidence": {"audio": 7.5},
    }
    segs, _ = score_clips.select_candidates([cand], min_score=8.0, dedupe=False)
    assert len(segs) == 1
    seg = segs[0]
    assert seg["proposed_title"] == "SISTEMAS INSANOS DO GTA 6!"
    assert seg["context_banner_2s"] == "Peso, sono e musculatura no GTA 6"
    assert seg["thumbnail_words"] == "NÍVEL SAN ANDREAS!"
    assert seg["pinned_comment_debate"] == "Você vai deixar o personagem maromba?"
    assert seg["llm_mode_used"] == "gemini"
    assert len(seg["reason"]) > 200


def test_llm_router_allows_strong_boost_and_covers_full_timeline():
    from picorte.ai.llm_router import LLMRouter

    # 80 candidatos ao longo de 3000s; os últimos têm notas 5.5 mas são ouro no final do vídeo
    cands = [
        {"start": float(i * 35), "end": float(i * 35 + 30), "overall": 6.5 if i < 55 else 5.5, "text": f"trecho {i}"}
        for i in range(80)
    ]

    seen_starts = []
    alvo = {}

    def fake_runner(provider, model, system_prompt, user_prompt):
        rows = json.loads(user_prompt)
        seen_starts.extend(r["start"] for r in rows)
        # Eleva um candidato do FIM do vídeo com +3.0 (5.5 -> 8.5), sempre o mesmo (pelo texto) nas 2 passadas.
        # Code review 2026-11-23: o lote volta inteiro (os outros com ajuste 0) — lote parcial agora para (Decisão B).
        alvo.setdefault("text", max(rows, key=lambda r: r["start"])["text"])
        out = []
        for r in rows:
            if r["text"] == alvo["text"]:
                out.append({
                    "index": r["index"],
                    "adjustment": 3.0,
                    "reason": "Corte de ouro no final do vídeo",
                    "proposed_title": "DESCOBERTA NO FINAL!",
                    "context_banner_2s": "Olha o que ele achou em casa",
                    "thumbnail_words": "COBRA EM CASA!",
                    "pinned_comment_debate": "Vocês esperavam por isso?",
                })
            else:
                out.append({"index": r["index"], "adjustment": 0.0, "reason": "neutro"})
        return json.dumps(out)

    res = LLMRouter(provider_runner=fake_runner).rerank_candidates(cands, ai_mode="gemini")
    # Deve incluir trechos do fim do vídeo (> 2500s) mesmo com mais de 50 candidatos
    assert max(seen_starts) >= 2500.0
    boosted = [c for c in res["candidates"] if c.get("proposed_title") == "DESCOBERTA NO FINAL!"]
    assert boosted and boosted[0]["overall"] >= 8.0


def test_expand_facecam_box_avoids_tight_face_crop():
    import render_clips

    # Face 183x224 perto de (1607, 7) em 1920x1080 (como no vídeo real do BRKsEDU)
    x, y, w, h = render_clips.expand_facecam_box((1607, 7, 183, 224), frame_w=1920, frame_h=1080)
    assert w >= 183 * 2.0
    assert h >= 224 * 1.4
    assert w / h >= 1.15
    assert x >= 0 and y >= 0 and x + w <= 1920 and y + h <= 1080


def test_studio_app_uses_shorts_max_len_for_9_16():
    app_js = Path("assets/studio/app.js").read_text(encoding="utf-8")
    assert "58" in app_js


def test_corner_facecam_scoring_beats_large_game_character():
    from picorte.engine.reaction_layout import _score_corner_facecam

    # Webcam no canto superior direito (como no vídeo do BRKsEDU) vs personagem grande no centro-esquerda
    edu_cam = _score_corner_facecam((1653.5, 54.9, 98.3, 137.6), 1920, 1080, 0.929)
    jason_npc = _score_corner_facecam((455.1, 144.6, 211.1, 311.1), 1920, 1080, 0.924)
    assert edu_cam > jason_npc

