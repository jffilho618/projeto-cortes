"""Engenharia de Retenção + Par Short Isca / Vídeo Longo (Stories 3.4 & 3.5)."""
from __future__ import annotations

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
