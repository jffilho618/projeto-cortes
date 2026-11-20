"""P9 (code review Épico 4) — react_guard: modo escuro, frame em tons de cinza e precisão da persistência."""
from __future__ import annotations

import cv2
import numpy as np


def _dark_youtube_frame() -> np.ndarray:
    fr = np.full((360, 640, 3), (15, 15, 15), dtype=np.uint8)  # fundo #0f0f0f do YouTube escuro
    fr[0:32, :] = (36, 33, 32)  # barra de abas/endereço escura
    cv2.rectangle(fr, (20, 44), (480, 315), (60, 90, 70), -1)  # player com o vídeo do terceiro
    cv2.rectangle(fr, (20, 305), (360, 311), (10, 10, 235), -1)  # barra vermelha de progresso
    return fr


def test_dark_mode_youtube_is_detected():
    from picorte.risk_shield.react_guard import detect_dangerous_react

    res = detect_dangerous_react([_dark_youtube_frame() for _ in range(4)], fps_sampled=1.0)
    assert res["is_dangerous_react"] is True


def test_dark_night_game_scene_is_not_react():
    from picorte.risk_shield.react_guard import detect_dangerous_react

    night = np.full((360, 640, 3), (18, 16, 14), dtype=np.uint8)
    cv2.circle(night, (320, 200), 40, (40, 160, 200), -1)  # luz/poste no jogo
    res = detect_dangerous_react([night.copy() for _ in range(6)], fps_sampled=1.0,
                                 transcript_text="que noite escura nesse mapa")
    assert res["is_dangerous_react"] is False


def test_grayscale_frames_do_not_crash():
    from picorte.risk_shield.react_guard import detect_dangerous_react

    gray = np.full((360, 640), 120, dtype=np.uint8)
    res = detect_dangerous_react([gray, gray], fps_sampled=1.0)
    assert res["status"] == "pass"


def test_persistence_threshold_is_exact_at_high_fps():
    from picorte.risk_shield.react_guard import detect_dangerous_react

    frames = [_dark_youtube_frame() for _ in range(25)]  # 25 frames a 10 fps = exatamente 2,5s
    res = detect_dangerous_react(frames, fps_sampled=10.0, min_persist_seconds=2.5)
    assert res["is_dangerous_react"] is True
