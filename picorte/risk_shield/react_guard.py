"""Story 4.4 — Detector Visual de 'React Perigoso' (P1: bloqueia navegador/player de terceiros preservando UI de jogo)."""
from __future__ import annotations

import math
import re
from typing import Any
import unicodedata

import cv2
import numpy as np

REACT_TRANSCRIPT_TRIGGERS: tuple[str, ...] = (
    "vamos ver esse video",
    "olha esse video",
    "olha esse clipe do",
    "toca o trailer",
    "assistir o trailer",
    "assistindo o trailer",
    "manda o link no chat",
    "react de",
    "reagindo a",
    "abre no youtube",
)


def _norm(text: str | None) -> str:
    raw = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", raw.lower()).strip()


def _score_single_frame_browser_react(
    frame: np.ndarray, *, exclude_box: tuple[int, int, int, int] | None = None
) -> dict[str, Any]:
    """Avalia sinais de navegador/player de terceiros nas bordas externas do 16:9 (ignora celular/menu in-game)."""
    if frame is None or getattr(frame, "size", 0) == 0:
        return {"score": 0.0, "signals": []}

    work = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) if frame.ndim == 2 else frame.copy()
    h, w = work.shape[:2]
    if exclude_box:
        ex, ey, ew, eh = [int(v) for v in exclude_box]
        work[max(0, ey) : min(h, ey + eh), max(0, ex) : min(w, ex + ew)] = 0

    small = cv2.resize(work, (320, 180), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    signals: list[str] = []
    score = 0.0

    # Sinal 1: Barra de abas/endereço uniforme clara no topo externo (y < 12%) atravessando > 75% da largura
    top_strip = gray[:20, :]
    top_bright_flat = float(np.mean((top_strip > 200) & (hsv[:20, :, 1] < 30)))
    if top_bright_flat > 0.72:
        score += 0.45
        signals.append("top_browser_chrome")

    # Sinal 2: Fundo web branco/cinza-claro ocupando bordas direita/inferior (> 28% da tela fora do player)
    web_bg_frac = float(np.mean((gray > 220) & (hsv[:, :, 1] < 25)))
    if web_bg_frac > 0.24:
        score += 0.35
        signals.append("bright_web_feed_bg")

    # Sinais 1b/2b (modo escuro, padrão em lives de games): barra de abas escura e lisa + fundo web quase preto.
    # Sozinhos nunca passam do limiar (noite em jogo também é escura e lisa): só somam com a barra vermelha.
    top_sat = hsv[:20, :, 1]
    chrome_px = (top_strip >= 20) & (top_strip <= 60) & (top_sat < 30)
    top_dark_flat = float(np.mean(chrome_px))
    chrome_flat = bool(chrome_px.any()) and float(top_strip[chrome_px].std()) < 6.0
    if top_dark_flat > 0.72 and chrome_flat:
        score += 0.25
        signals.append("top_browser_chrome_dark")
    web_dark_frac = float(np.mean((gray < 24) & (hsv[:, :, 1] < 25)))
    if web_dark_frac > 0.24:
        score += 0.2
        signals.append("dark_web_feed_bg")

    # Sinal 3: Barra vermelha horizontal de progresso do player YouTube (faixa fina vermelha saturada em y 75..92%)
    bot_player_band = hsv[135:170, 5:280]
    red_px = ((bot_player_band[:, :, 0] <= 8) | (bot_player_band[:, :, 0] >= 172)) & (bot_player_band[:, :, 1] >= 170) & (bot_player_band[:, :, 2] >= 140)
    # Verifica se existe uma linha horizontal com > 35% de vermelho contínuo
    row_red_max = float(np.max(np.mean(red_px, axis=1))) if red_px.size else 0.0
    if row_red_max > 0.32:
        score += 0.45
        signals.append("youtube_red_progress_bar")

    return {"score": min(1.0, score), "signals": signals}


def detect_dangerous_react(
    frames: list[np.ndarray],
    *,
    fps_sampled: float = 1.0,
    transcript_text: str = "",
    exclude_box: tuple[int, int, int, int] | None = None,
    min_persist_seconds: float = 2.5,
) -> dict[str, Any]:
    """Detecta react de vídeo/navegador de terceiros exigindo persistência >= 2.5s (evita falso positivo em UI do jogo)."""
    norm_txt = _norm(transcript_text)
    tx_hits = [t for t in REACT_TRANSCRIPT_TRIGGERS if t in norm_txt]
    threshold = 0.55 if tx_hits else 0.72

    fps = max(0.1, float(fps_sampled))
    # Conta frames (inteiros) em vez de somar 1/fps: sem erro de arredondamento no limiar de persistência.
    needed_frames = max(1, math.ceil(float(min_persist_seconds) * fps - 1e-9))
    max_run = 0
    cur_run = 0
    matched_signals: set[str] = set()

    for fr in frames:
        res = _score_single_frame_browser_react(fr, exclude_box=exclude_box)
        if res["score"] >= threshold:
            cur_run += 1
            max_run = max(max_run, cur_run)
            matched_signals.update(res["signals"])
        else:
            cur_run = 0

    max_persist = max_run / fps
    is_dangerous = max_run >= needed_frames
    return {
        "gate": "react_guard",
        "status": "hard_block" if is_dangerous else "pass",
        "is_dangerous_react": is_dangerous,
        "max_persist_seconds": round(max_persist, 2),
        "signals": sorted(matched_signals),
        "transcript_triggers": tx_hits,
    }
