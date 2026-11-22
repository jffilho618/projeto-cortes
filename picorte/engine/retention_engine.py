"""Engenharia de Retenção + Par Short Isca / Vídeo Longo (Stories 3.4 & 3.5)."""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from picorte.engine.audio_align import find_audio_offset


ARCHETYPE_RETENTION_POLICIES: dict[str, dict[str, Any]] = {
    "callback_oculto": {
        "use_cold_open": False,
        "banner_style": "curioso",
        "font_name": "Archivo",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HD0182433",
        "comparative_badge": True,
    },
    "descoberta_detalhe": {
        "use_cold_open": False,
        "banner_style": "curioso",
        "font_name": "Archivo",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HD0182433",
        "comparative_badge": True,
    },
    "serio_realtalk": {
        "use_cold_open": False,
        "banner_style": "editorial",
        "font_name": "Archivo",
        "primary_colour": "&H00F2F2F2",
        "back_colour": "&HE0121214",
        "comparative_badge": False,
    },
    "polemica_hottake": {
        "use_cold_open": False,
        "banner_style": "editorial",
        "font_name": "Archivo",
        "primary_colour": "&H00F5F5F5",
        "back_colour": "&HE01A1414",
        "comparative_badge": False,
    },
    "susto_tensao": {
        "use_cold_open": False,
        "banner_style": "tenso",
        "font_name": "Antonio",
        "primary_colour": "&H00E5E5FF",
        "back_colour": "&HE00D0D14",
        "comparative_badge": False,
    },
    "deadpan_karma": {
        "use_cold_open": False,
        "banner_style": "ironico",
        "font_name": "Archivo",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HD01A1A1A",
        "comparative_badge": False,
    },
    "caos_coop": {
        "use_cold_open": True,
        "banner_style": "hype",
        "font_name": "Arial Black",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HC8000000",
        "comparative_badge": False,
    },
    "rage_tilt": {
        "use_cold_open": True,
        "banner_style": "hype",
        "font_name": "Arial Black",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HC8000024",
        "comparative_badge": False,
    },
    "clutch_fail": {
        "use_cold_open": True,
        "banner_style": "hype",
        "font_name": "Arial Black",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HC8000000",
        "comparative_badge": False,
    },
    "chat_trolagem": {
        "use_cold_open": True,
        "banner_style": "hype",
        "font_name": "Archivo",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HC8141422",
        "comparative_badge": False,
    },
    # 3.6.3: o vacilo rende teaser (o erro em si); o mico precisa do setup inteiro, então sem Cold Open.
    "nobada_vacilo": {
        "use_cold_open": True,
        "banner_style": "hype",
        "font_name": "Arial Black",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HC8000000",
        "comparative_badge": False,
    },
    "mico_constrangimento": {
        "use_cold_open": False,
        "banner_style": "ironico",
        "font_name": "Archivo",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HD01A1A1A",
        "comparative_badge": False,
    },
}


def resolve_archetype_retention_policy(
    archetype: str | None,
    *,
    tone: str | None = None,
) -> dict[str, Any]:
    """Resolve política de Cold Open e estilo visual da Faixa de Contexto pelo arquétipo."""
    key = str(archetype or "").strip().lower()
    if key in ARCHETYPE_RETENTION_POLICIES:
        return dict(ARCHETYPE_RETENTION_POLICIES[key])
    t = str(tone or "").strip().lower()
    if t == "editorial":
        return dict(ARCHETYPE_RETENTION_POLICIES["serio_realtalk"])
    if t == "tenso":
        return dict(ARCHETYPE_RETENTION_POLICIES["susto_tensao"])
    if t == "curioso":
        return dict(ARCHETYPE_RETENTION_POLICIES["callback_oculto"])
    if t == "ironico":
        return dict(ARCHETYPE_RETENTION_POLICIES["deadpan_karma"])
    return {
        "use_cold_open": True,
        "banner_style": "hype",
        "font_name": "Arial Black",
        "primary_colour": "&H00FFFFFF",
        "back_colour": "&HC8000000",
        "comparative_badge": False,
    }


def build_cold_open_plan(
    clip_start: float,
    clip_end: float,
    *,
    peak_t: float | None = None,
    teaser_dur: float = 1.5,
    archetype: str | None = None,
    tone: str | None = None,
) -> dict[str, Any]:
    """Planeja Cold Open Reverso de 1.2s a 1.8s puxando o pico dramático para o segundo 0:00.

    Respeita a política do arquétipo: desliga spoiler em susto_tensao / serio_realtalk / callback_oculto.
    """
    s = float(clip_start)
    e = float(clip_end)
    policy = resolve_archetype_retention_policy(archetype, tone=tone)
    if not policy["use_cold_open"]:
        return {
            "enabled": False,
            "archetype": archetype,
            "clip_start": round(s, 3),
            "clip_end": round(e, 3),
            "teaser_start": round(s, 3),
            "teaser_end": round(s, 3),
            "teaser_duration": 0.0,
        }

    dur = max(0.5, e - s)
    td = max(1.2, min(1.8, float(teaser_dur), dur * 0.45))

    center = float(peak_t) if peak_t is not None else (s + dur * 0.65)
    t_start = max(s, min(e - td, center - td / 2.0))
    t_end = min(e, t_start + td)
    return {
        "enabled": True,
        "archetype": archetype,
        "clip_start": round(s, 3),
        "clip_end": round(e, 3),
        "teaser_start": round(t_start, 3),
        "teaser_end": round(t_end, 3),
        "teaser_duration": round(t_end - t_start, 3),
    }


def _fmt_ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_context_banner_ass(
    text: str,
    *,
    width: int = 1080,
    height: int = 1920,
    duration_s: float = 2.0,
    y_pos: int = 300,
    archetype: str | None = None,
    tone: str | None = None,
) -> str:
    """Gera bloco ASS para Faixa de Contexto de 2s na área segura superior (y=240..360, AD-7)."""
    policy = resolve_archetype_retention_policy(archetype, tone=tone)
    safe_y = max(240, min(360, int(y_pos)))
    safe_x = int(width // 2)
    clean_text = str(text or "").replace("\n", " ").strip()
    start_ts = _fmt_ass_time(0.0)
    end_ts = _fmt_ass_time(max(1.0, float(duration_s)))
    font_name = policy["font_name"]
    primary = policy["primary_colour"]
    back = policy["back_colour"]
    font_size = 42 if policy["banner_style"] == "editorial" else 46
    outline_px = 8 if policy["banner_style"] == "editorial" else 12
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {int(width)}\n"
        f"PlayResY: {int(height)}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: ContextBanner,{font_name},{font_size},{primary},{primary},{back},{back},-1,0,0,0,100,100,0,0,3,{outline_px},0,8,80,80,240,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    dialogue = (
        f"Dialogue: 1,{start_ts},{end_ts},ContextBanner,,0,0,0,,"
        f"{{\\an8\\pos({safe_x},{safe_y})}}{clean_text}\n"
    )
    return header + dialogue


def find_seamless_loop_end(
    words: list[dict[str, Any]],
    start: float,
    end: float,
    *,
    tail_pad_s: float = 0.25,
) -> float:
    """Encontra ponto final pós-palavra para corte limpo em loop de volta ao frame 0:00."""
    s = float(start)
    e = float(end)
    inside = [w for w in (words or []) if s <= float(w.get("start", 0.0)) <= e]
    if not inside:
        return round(e, 3)
    last_end = max(float(w.get("end", e)) for w in inside)
    return round(min(e, max(s + 1.0, last_end + float(tail_pad_s))), 3)


def build_cross_streamer_sync_plan(
    audio_tracks: list[np.ndarray],
    *,
    sample_rate: int = 16000,
) -> dict[str, Any]:
    """Sincroniza POVs de múltiplos streamers via audio_align para compilação Cross-Streamer."""
    if not audio_tracks:
        return {"offsets_s": []}
    ref = audio_tracks[0]
    offsets = [0.0]
    for track in audio_tracks[1:]:
        offsets.append(find_audio_offset(ref, track, sample_rate=sample_rate))
    return {"offsets_s": offsets}


def pair_short_and_long_clips(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Liga cada Short Isca (<60s) ao Vídeo Longo (180s-300s) correspondente via parent_long_clip_id (AD-7)."""
    out = [dict(c) for c in clips]
    longs = [
        c
        for c in out
        if 175.0 <= float(c.get("duration") or (float(c["end"]) - float(c["start"]))) <= 360.0
        and c.get("aspect", "16:9") == "16:9"
    ]
    for clip in out:
        dur = float(clip.get("duration") or (float(clip["end"]) - float(clip["start"])))
        if dur < 60.0 and not clip.get("parent_long_clip_id"):
            cs, ce = float(clip["start"]), float(clip["end"])
            # Prioriza vídeo longo que contenha ou sobreponha o intervalo do Short
            best = None
            best_overlap = -1.0
            for lng in longs:
                ls, le = float(lng["start"]), float(lng["end"])
                overlap = max(0.0, min(ce, le) - max(cs, ls))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best = lng
            if best is not None and (best_overlap > 0.0 or longs):
                clip["parent_long_clip_id"] = best.get("id")
    return out


# ------------------------------------------------------------------ 3.7.1: Cold Open de verdade + Seamless Loop

COLD_OPEN_XFADE_S = 0.25
CLIMAX_MIN_LEAD_S = 3.0
_TOKEN_NORM_RE = re.compile(r"[^\wÀ-ÿ]+")


PUNCHLINE_MIN_MATCH = 0.6  # fração das palavras do hook_quote achadas na janela (o Editor parafraseia)


def _norm_token(word: Any) -> str:
    import unicodedata

    plain = unicodedata.normalize("NFKD", str(word or "").lower()).encode("ascii", "ignore").decode("ascii")
    return _TOKEN_NORM_RE.sub("", plain)


def _find_punchline_end(quote: list[str], clip_words: list[dict[str, Any]]) -> float | None:
    """Fim da janela de palavras que mais se parece com o hook_quote (≥ 60% das palavras, sem acento)."""
    from collections import Counter

    n = len(quote)
    toks = [_norm_token(w.get("word")) for w in clip_words]
    want = Counter(quote)
    best, best_end = 0.0, None
    for i in range(max(0, len(toks) - n + 1)):
        got = Counter(toks[i:i + n])
        score = sum((want & got).values()) / n
        if score > best:
            best, best_end = score, float(clip_words[min(len(clip_words), i + n) - 1].get("end") or 0.0)
    return best_end if best >= PUNCHLINE_MIN_MATCH else None


def pick_climax(seg: dict[str, Any], words: list[dict[str, Any]] | None,
                chat_peaks: list[dict[str, Any]] | None, *, min_lead: float = CLIMAX_MIN_LEAD_S
                ) -> dict[str, Any] | None:
    """Clímax MEDIDO do corte: o pico de chat mais forte (pela causa) ou o fim da punchline (`hook_quote`).

    Pico cedo demais (antes de start+min_lead) não serve: o teaser repetiria a abertura. Sem sinal → None.
    """
    s, e = float(seg.get("start") or 0.0), float(seg.get("end") or 0.0)
    inside = [p for p in chat_peaks or []
              if p.get("cause_second") is not None and s + min_lead <= float(p["cause_second"]) <= e - 0.5]
    if inside:
        best = max(inside, key=lambda p: float(p.get("vel_zscore") or 0.0))
        return {"t": float(best["cause_second"]), "fonte": "chat"}
    quote = [t for t in (_norm_token(x) for x in str(seg.get("hook_quote") or "").split()) if t]
    if quote:
        clip_words = [w for w in words or [] if s <= float(w.get("start") or 0.0) <= e]
        end_t = _find_punchline_end(quote, clip_words)
        if end_t is not None and end_t - 0.5 >= s + min_lead:
            return {"t": end_t - 0.5, "fonte": "punchline"}
    return None


def cold_open_for_segment(seg: dict[str, Any], words: list[dict[str, Any]] | None,
                          chat_peaks: list[dict[str, Any]] | None, *, max_len: float | None = None,
                          xfade: float = COLD_OPEN_XFADE_S) -> dict[str, Any]:
    """Plano do Cold Open para um segmento: medido ou desligado (com motivo); respeita arquétipo e max_len."""
    s, e = float(seg.get("start") or 0.0), float(seg.get("end") or 0.0)
    off = {"enabled": False, "clip_start": round(s, 3), "clip_end": round(e, 3)}
    climax = pick_climax(seg, words, chat_peaks)
    if climax is None:
        return {**off, "motivo": "sem clímax medido (pico de chat ou punchline) dentro do corte"}
    plan = build_cold_open_plan(s, e, peak_t=climax["t"], archetype=seg.get("archetype"), tone=seg.get("tone"))
    if not plan["enabled"]:
        return {**off, "motivo": f"arquétipo {seg.get('archetype')} sem Cold Open (evita spoiler)"}
    plan["climax_t"] = round(climax["t"], 3)
    plan["climax_fonte"] = climax["fonte"]
    if max_len:
        excess = (e - s) + float(plan["teaser_duration"]) - float(xfade) - float(max_len)
        if excess > 0:
            novo = s + excess
            if novo > float(plan["teaser_start"]) - CLIMAX_MIN_LEAD_S:
                return {**off, "motivo": "max_len: não cabe o teaser sem cortar o setup do clímax"}
            plan["novo_inicio"] = round(novo, 3)
            plan["clip_start"] = round(novo, 3)
    return plan


def _teaser_bleep_filter(bleeps: list[dict[str, Any]] | None) -> str:
    terms = [f"between(t,{float(b['start']):.3f},{float(b['end']):.3f})" for b in bleeps or []
             if float(b.get("end") or 0.0) > float(b.get("start") or 0.0)]
    if not terms:
        return ""
    return f",volume='if({'+'.join(terms)},0.016,1)':eval=frame"  # −36 dB, como o Selo Verde


def cold_open_ffmpeg_cmd(in_path: Any, out_path: Any, rel_start: float, dur: float,
                         bleeps: list[dict[str, Any]] | None = None, *, xfade: float = COLD_OPEN_XFADE_S
                         ) -> list[str]:
    """Teaser (trecho [rel_start, rel_start+dur] do próprio corte) colado no 0:00 com xfade/acrossfade."""
    a, b, x = float(rel_start), float(rel_start) + float(dur), float(xfade)
    graph = (
        "[0:v]split=2[v0][v1];[0:a]asplit=2[a0][a1];"
        f"[v0]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[tv];"
        f"[a0]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS{_teaser_bleep_filter(bleeps)}[ta];"
        "[v1]setpts=PTS-STARTPTS[mv];[a1]asetpts=PTS-STARTPTS[ma];"
        f"[tv][mv]xfade=transition=fade:duration={x:.3f}:offset={float(dur) - x:.3f}[v];"
        f"[ta][ma]acrossfade=d={x:.3f}[a]"
    )
    return ["ffmpeg", "-y", "-i", str(in_path), "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out_path)]


def prepend_cold_open(mp4: Any, plan: dict[str, Any] | None, clip_start: float,
                      bleeps: list[dict[str, Any]] | None = None, *, runner: Any = None) -> bool:
    """Cola o teaser no começo do mp4 já renderizado (troca o arquivo em lugar). Falha → arquivo intacto."""
    import subprocess
    from pathlib import Path

    if not plan or not plan.get("enabled"):
        return False
    run = runner or subprocess.run
    src = Path(mp4)
    tmp = src.with_name(src.stem + ".coldopen" + src.suffix)
    rel = float(plan["teaser_start"]) - float(clip_start)
    try:
        run(cold_open_ffmpeg_cmd(src, tmp, rel, float(plan["teaser_duration"]), bleeps),
            check=True, capture_output=True)
    except Exception:
        tmp.unlink(missing_ok=True)
        return False
    if not tmp.is_file():
        return False
    tmp.replace(src)
    return True


def seamless_loop_end(sentences: list[dict[str, Any]] | None, start: float, end: float, *,
                      rms: Any = None, back: float = 1.5, fwd: float = 1.5, only_forward: bool = False,
                      max_len: float | None = None) -> float:
    """Fim do corte num FIM DE FRASE em [end−back, end+fwd] cujo volume mais se parece com o do começo.

    Assim o último segundo emenda com o 0:00 no replay. `only_forward` (riso estendido no fim) só avança.
    Recuo padrão de 1,5 s (o AC dizia 3 s): recuar mais cortaria a reação que o Editor-Chefe incluiu (3.6.4).
    Sem fim de frase no intervalo, mantém o fim. Limitação: a emenda é medida pelo volume, não pela imagem.
    """
    s, e = float(start), float(end)
    lo = e if only_forward else e - float(back)
    hi = e + float(fwd)
    if max_len:
        hi = min(hi, s + float(max_len))
    cands = sorted({round(float(x.get("end") or 0.0), 3) for x in sentences or []
                    if lo <= float(x.get("end") or 0.0) <= hi and float(x.get("end") or 0.0) > s + 1.0})
    if not cands:
        return e
    levels = np.asarray(rms, dtype=np.float64).ravel() if rms is not None else None
    if levels is None or levels.size == 0:
        return min(cands, key=lambda c: abs(c - e))

    def level(t: float) -> float:
        return float(levels[max(0, min(levels.size - 1, int(t)))])

    ref = level(s)
    return min(cands, key=lambda c: (round(abs(level(c) - ref), 1), abs(c - e)))
