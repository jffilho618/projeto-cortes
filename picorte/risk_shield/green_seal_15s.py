"""Story 4.4 — Filtro 'Selo Verde 15s' (Áudio bleep/soft-mute + Legenda *** + Cold Open + Visão anti-gore/nudez + Thumbnail)."""
from __future__ import annotations

import math
from pathlib import Path
import re
from typing import Any
import unicodedata
import wave

import cv2
import numpy as np

# Camada 3: violação grave em QUALQUER segundo do clipe -> HARD_BLOCK
# W55 (code review 2026-11-23, decisão do dono, julgada pelo cortes-pilares): só termos SEM colisão com jogo;
# "suicidio", "se matar" e "nazismo" desceram para a Camada 2 (Suicide Squad, Wolfenstein dublado, Call of Duty).
TIER_3_HARD_BLOCK_TERMS: tuple[str, ...] = (
    "estupro",
    "pedofilia",
    "rape",
    "pedophile",
    "pedophilia",
    "child porn",
)

# Camada 2: termos sensíveis para anunciantes (drogas pesadas, automutilação, terror) nos primeiros 15s
# -> não dá para "bipar" o assunto: vai para revisão humana (mudar o início ou descartar o corte).
TIER_2_REVIEW_TERMS: tuple[str, ...] = (
    "cocaina",
    "heroina",
    "crack",
    "overdose",
    "automutilacao",
    "se cortar",
    "terrorista",
    "atentado",
    "massacre",
    # W55: colidem com títulos e personagens de jogos -> revisão humana, nunca aborto automático
    "suicidio",
    "se matar",
    "nazismo",
    "suicide",
    "kill myself",
    "nazi",
)

# Camada 1: palavrões severos que custam monetização nos primeiros 15s (e no Cold Open) -> bleep + ***
TIER_1_SEVERE_EXACT: set[str] = {
    "porra",
    "poha",
    "caralho",
    "krl",
    "crl",
    "puta",
    "putaria",
    "foda",
    "fodase",
    "foder",
    "fuder",
    "fudido",
    "fodido",
    "buceta",
    "xoxota",
    "cuzao",
    "arrombado",
    "arrombada",
    "desgraca",
    "vagabunda",
    "piranha",
    "fuck",
    "fucking",
    "motherfucker",
    "shit",
    "bitch",
    "asshole",
}

# Allowlist explícita contra falsos positivos de substring (ex.: "computador" contém "puta")
ALLOWLIST_WORDS: set[str] = {
    "computador",
    "computadores",
    "disputa",
    "disputar",
    "reputacao",
    "amputacao",
    "deputado",
    "deputada",
    "imputar",
    "escrupulo",
    "caramelo",
    "caramba",
    "foca",
}


def _norm_token(word: str) -> str:
    raw = unicodedata.normalize("NFKD", str(word or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def _is_tier1_profanity(word: str) -> bool:
    tok = _norm_token(word)
    if not tok or tok in ALLOWLIST_WORDS:
        return False
    if tok in TIER_1_SEVERE_EXACT:
        return True
    # Match composto exato com hífen removido (ex.: "foda-se" -> "fodase")
    for stem in ("caralh", "arrombad", "motherfuck"):
        if tok.startswith(stem):
            return True
    return False


def _segundos(x: float) -> str:
    return f"{x:.0f}"  # segundo inteiro desde o início do corte: o que o operador procura no player


def _lista_segundos(secs: list[float]) -> str:
    itens = [f"{_segundos(x)} s" for x in secs]
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


def _norm_palavra(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", base)


def _segundo_do_termo(term: str, words: list[dict[str, Any]], c_start: float, c_end: float) -> float | None:
    """Onde o termo (1 ou mais palavras) começa, em segundos desde o início do corte; None se não achar."""
    toks = [t for t in (_norm_palavra(x) for x in term.split()) if t]
    no_corte = [w for w in words if float(w.get("end", 0)) > c_start and float(w.get("start", 0)) < c_end]
    norms = [_norm_palavra(w.get("word") or "") for w in no_corte]
    for i in range(len(norms) - len(toks) + 1):
        if toks and norms[i:i + len(toks)] == toks:
            return max(0.0, float(no_corte[i].get("start", 0.0)) - c_start)
    return None


def _motivo_termo(prefixo: str, term: str, words: list[dict[str, Any]], c_start: float, c_end: float) -> str:
    onde = _segundo_do_termo(term, words, c_start, c_end)
    return f'{prefixo} "{term}" aos {_segundos(onde)} s do corte' if onde is not None else f'{prefixo} "{term}" no corte'


def plan_green_seal_audio_and_captions(
    words: list[dict[str, Any]],
    *,
    clip_start: float,
    clip_end: float,
    cold_open_plan: dict[str, Any] | None = None,
    window_s: float = 15.0,
    pad_s: float = 0.04,
) -> dict[str, Any]:
    """Planeja censura cirúrgica (0–15s + teaser Cold Open) e retorna cópia das palavras com '***' para .ass."""
    c_start = float(clip_start)
    c_end = float(clip_end)
    full_text = " ".join(str(w.get("word") or "") for w in words if float(w.get("end", 0)) > c_start and float(w.get("start", 0)) < c_end)
    norm_full = unicodedata.normalize("NFKD", full_text).encode("ascii", "ignore").decode("ascii").lower()
    hard_block_hits = [t for t in TIER_3_HARD_BLOCK_TERMS if re.search(rf"(?:^|\W){re.escape(t)}(?:\W|$)", norm_full)]
    early_text = " ".join(
        str(w.get("word") or "") for w in words
        if float(w.get("end", 0)) > c_start and float(w.get("start", 0)) < min(c_end, c_start + window_s)
    )
    norm_early = unicodedata.normalize("NFKD", early_text).encode("ascii", "ignore").decode("ascii").lower()
    tier2_hits = [t for t in TIER_2_REVIEW_TERMS if re.search(rf"(?:^|\W){re.escape(t)}(?:\W|$)", norm_early)]

    co_enabled = bool(cold_open_plan and cold_open_plan.get("enabled"))
    co_s = float(cold_open_plan.get("teaser_start", 0.0)) if co_enabled else -1.0
    co_e = float(cold_open_plan.get("teaser_end", 0.0)) if co_enabled else -1.0

    censored_words: list[dict[str, Any]] = []
    bleep_intervals: list[dict[str, Any]] = []
    cold_open_hits: list[dict[str, Any]] = []
    cold_open_bleeps: list[dict[str, Any]] = []
    cold_open_words: list[dict[str, Any]] = []
    first_8s_hits = 0

    for item in words:
        w_copy = dict(item)
        ws = float(item.get("start", 0.0))
        we = float(item.get("end", ws + 0.2))
        if we <= c_start or ws >= c_end:
            censored_words.append(w_copy)
            continue

        rel_s = max(0.0, ws - c_start)
        rel_e = max(rel_s + 0.08, min(c_end, we) - c_start)
        is_profane = _is_tier1_profanity(str(item.get("word") or ""))

        if is_profane and rel_s < window_s:
            w_copy["word"] = "***"
            w_copy["censored_green_seal"] = True
            bleep_intervals.append({
                "start": round(max(0.0, rel_s - pad_s), 3),
                "end": round(min(c_end - c_start, rel_e + pad_s), 3),
                "original_word": str(item.get("word") or ""),
            })
            if rel_s < 8.0:
                first_8s_hits += 1

        if co_enabled and we > co_s and ws < co_e:
            # Teaser do Cold Open toca no 0:00 do vídeo final: censura na linha do tempo do teaser.
            t_word = dict(item)
            if is_profane:
                cold_open_hits.append({
                    "start": round(ws, 3),
                    "end": round(we, 3),
                    "word": str(item.get("word") or ""),
                })
                t_word["word"] = "***"
                t_word["censored_green_seal"] = True
                cold_open_bleeps.append({
                    "start": round(max(0.0, ws - co_s - pad_s), 3),
                    "end": round(min(co_e - co_s, we - co_s + pad_s), 3),
                    "original_word": str(item.get("word") or ""),
                })
            cold_open_words.append(t_word)

        censored_words.append(w_copy)

    density_shift = first_8s_hits >= 4
    if hard_block_hits:
        status = "hard_block"
    elif density_shift or tier2_hits:
        status = "human_review"
    elif bleep_intervals or cold_open_hits:
        status = "auto_fixed"
    else:
        status = "pass"

    # O que achou e onde (pedido do dono, 2026-11-23): a Revisão mostra este texto em vez de "motivo não registrado".
    reasons = [_motivo_termo("termo grave", t, words, c_start, c_end) for t in hard_block_hits]
    reasons += [_motivo_termo("termo que pede revisão humana", t, words, c_start, min(c_end, c_start + window_s))
                for t in tier2_hits]
    if density_shift:
        reasons.append(f"{first_8s_hits} palavrões nos primeiros 8 s do corte")

    return {
        "gate": "green_seal_15s_audio",
        "status": status,
        "reasons": reasons,
        "censored_words": censored_words,
        "bleep_intervals": bleep_intervals,
        "cold_open_hits": cold_open_hits,
        "cold_open_bleeps": cold_open_bleeps,
        "cold_open_censored_words": cold_open_words,
        "tier2_hits": tier2_hits,
        "hard_block_hits": hard_block_hits,
        "density_shift_recommended": density_shift,
    }


def apply_audio_bleeps(
    audio_in: Path | str,
    audio_out: Path | str,
    intervals: list[dict[str, float]],
    *,
    mode: str = "soft_mute",
    fade_ms: float = 15.0,
) -> Path:
    """Aplica soft-mute (-36 dB) ou bleep suave (1000 Hz -20 dBFS) com rampa de fade 15ms sem estalos."""
    src, dst = Path(audio_in), Path(audio_out)
    with wave.open(str(src), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if nch > 1:
        arr = arr.reshape(-1, nch)
    else:
        arr = arr[:, None]

    n_samples = arr.shape[0]
    fade_n = max(8, int(round(sr * (fade_ms / 1000.0))))
    out_arr = arr.copy()

    for iv in intervals:
        s_i = max(0, min(n_samples, int(round(float(iv["start"]) * sr))))
        e_i = max(s_i, min(n_samples, int(round(float(iv["end"]) * sr))))
        seg_len = e_i - s_i
        if seg_len < 16:
            continue

        gain = np.full(seg_len, 0.016, dtype=np.float32)  # -36 dB
        fn = min(fade_n, seg_len // 3)
        if fn > 1:
            gain[:fn] = np.linspace(1.0, 0.016, fn, dtype=np.float32)
            gain[-fn:] = np.linspace(0.016, 1.0, fn, dtype=np.float32)

        out_arr[s_i:e_i, :] *= gain[:, None]
        if mode == "bleep":
            t = np.arange(seg_len, dtype=np.float32) / float(sr)
            env = np.ones(seg_len, dtype=np.float32)
            if fn > 1:
                env[:fn] = np.linspace(0.0, 1.0, fn, dtype=np.float32)
                env[-fn:] = np.linspace(1.0, 0.0, fn, dtype=np.float32)
            tone = (0.10 * np.sin(2.0 * math.pi * 1000.0 * t) * env).astype(np.float32)
            out_arr[s_i:e_i, :] += tone[:, None]

    # Limiter -1.5 dBTP
    peak = float(np.max(np.abs(out_arr))) if out_arr.size else 0.0
    if peak > 0.841:
        out_arr *= 0.841 / peak

    pcm = np.clip(out_arr * 32767.0, -32768.0, 32767.0).astype(np.int16)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as wf:
        wf.setnchannels(nch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return dst


def score_frame_visual_safety(
    frame: np.ndarray, *, exclude_box: tuple[int, int, int, int] | None = None
) -> dict[str, Any]:
    """Avalia segurança visual de 1 frame (gore/sangue concentrado ou exposição excessiva de pele/nudez)."""
    if frame is None or getattr(frame, "size", 0) == 0:
        return {"safe": True, "flags": [], "gore_ratio": 0.0, "skin_ratio": 0.0, "penalty": 0.0}

    work = frame if frame.ndim == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    h, w = work.shape[:2]
    valid_full = np.ones((h, w), dtype=np.uint8)
    if exclude_box:
        ex, ey, ew, eh = [int(v) for v in exclude_box]
        valid_full[max(0, ey) : min(h, ey + eh), max(0, ex) : min(w, ex + ew)] = 0

    small = cv2.resize(work, (240, 135), interpolation=cv2.INTER_AREA)
    # Proporções medidas só sobre a área NÃO excluída (a facecam não dilui o denominador).
    valid = cv2.resize(valid_full, (240, 135), interpolation=cv2.INTER_NEAREST).astype(bool)
    n_valid = int(valid.sum())
    if n_valid == 0:
        return {"safe": True, "flags": [], "gore_ratio": 0.0, "skin_ratio": 0.0, "penalty": 0.0}
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)

    # 1) Sangue saturado concentrado (H perto de 0/180, S > 155, V entre 55 e 230)
    red1 = (hsv[:, :, 0] <= 8) & (hsv[:, :, 1] >= 155) & (hsv[:, :, 2] >= 55) & (hsv[:, :, 2] <= 230)
    red2 = (hsv[:, :, 0] >= 172) & (hsv[:, :, 1] >= 155) & (hsv[:, :, 2] >= 55) & (hsv[:, :, 2] <= 230)
    gore_ratio = float(np.count_nonzero((red1 | red2) & valid)) / n_valid

    # 2) Exposição excessiva de pele em área de gameplay (YCrCb padrão de pele)
    skin_mask = (
        (ycrcb[:, :, 0] > 65)
        & (ycrcb[:, :, 1] >= 133) & (ycrcb[:, :, 1] <= 173)
        & (ycrcb[:, :, 2] >= 77) & (ycrcb[:, :, 2] <= 127)
    )
    skin_ratio = float(np.count_nonzero(skin_mask & valid)) / n_valid

    flags: list[str] = []
    penalty = 0.0
    if gore_ratio >= 0.22:
        flags.append("gore")
        penalty += 500.0
    if skin_ratio >= 0.48:
        flags.append("nudity_exposure")
        penalty += 450.0

    return {
        "safe": len(flags) == 0,
        "flags": flags,
        "gore_ratio": round(gore_ratio, 4),
        "skin_ratio": round(skin_ratio, 4),
        "penalty": penalty,
    }


def audit_visual_green_seal_15s(
    frames: list[np.ndarray],
    *,
    fps_sampled: float = 1.0,
    exclude_box: tuple[int, int, int, int] | None = None,
) -> dict[str, Any]:
    """Audita visualmente os primeiros 15s do clipe contra gore e nudez excessiva."""
    limit_n = max(1, int(round(15.0 * max(0.1, fps_sampled))))
    flagged: list[dict[str, Any]] = []
    for idx, fr in enumerate(frames[:limit_n]):
        res = score_frame_visual_safety(fr, exclude_box=exclude_box)
        if not res["safe"]:
            flagged.append({"sec": round(idx / max(0.1, fps_sampled), 2), **res})

    if not flagged:
        return {"gate": "green_seal_15s_visual", "status": "pass", "flagged_frames": [], "shift_start_recommended": False,
                "reasons": []}

    early_only = all(f["sec"] <= 4.0 for f in flagged)
    nomes = {"gore": "sangue (gore)", "nudity_exposure": "exposição de pele"}
    reasons = []
    for flag, nome in nomes.items():
        secs = [float(f["sec"]) for f in flagged if flag in (f.get("flags") or [])]
        if secs:
            reasons.append(f"{nome} na tela aos {_lista_segundos(secs)} do corte")
    return {
        "gate": "green_seal_15s_visual",
        "status": "human_review",
        "reasons": reasons,
        "flagged_frames": flagged,
        "shift_start_recommended": early_only,
    }
