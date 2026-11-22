"""Edição dirigida pelo conteúdo (Épico 3.7 — Story 3.7.5).

Freeze de 0,8 s com círculo e seta (balançando) no momento-chave MEDIDO do corte, na cor do estilo do arquétipo.
A variação vem do conteúdo (arquétipo, momento-chave, layout do instante), nunca de sorteio (A2; P2).
Camada em FFmpeg/OpenCV — o caminho de reserva do AC3; o HyperFrames só entra após a prova de conceito aprovada.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

FREEZE_S = 0.8
NO_FREEZE_FORMATS = ("longo_16x9", "arco_2_atos", "compilacao")
# BGR por estilo da faixa (resolve_archetype_retention_policy): hype amarelo, tenso vermelho, curioso ciano.
ARROW_BGR = {"hype": (0, 212, 255), "tenso": (60, 60, 255), "curioso": (255, 220, 0),
             "ironico": (255, 255, 255), "editorial": (255, 255, 255)}


def freeze_for_segment(seg: dict[str, Any], words: list[dict[str, Any]] | None,
                       chat_peaks: list[dict[str, Any]] | None, *, max_len: float | None,
                       used_s: float = 0.0, d: float = FREEZE_S) -> dict[str, Any]:
    """Plano do freeze: momento-chave medido (pico de chat ou punchline, 3.7.1), só verticais, cabe no max_len."""
    from picorte.engine.retention_engine import pick_climax

    if seg.get("formato") in NO_FREEZE_FORMATS:
        return {"enabled": False, "motivo": f"formato {seg.get('formato')} sem freeze"}
    s, e = float(seg.get("start") or 0.0), float(seg.get("end") or 0.0)
    climax = pick_climax(seg, words, chat_peaks)
    if climax is None:
        return {"enabled": False, "motivo": "sem momento-chave medido"}
    t = climax["t"] - s
    if t < 1.0 or t > (e - s) - 0.5:
        return {"enabled": False, "motivo": "momento-chave colado na borda do corte"}
    if max_len and (e - s) + float(d) + float(used_s) > float(max_len):
        return {"enabled": False, "motivo": "max_len: o freeze não cabe"}
    return {"enabled": True, "t": round(t, 3), "d": float(d), "fonte": climax["fonte"]}


def arrow_color_for(archetype: str | None, tone: str | None = None) -> tuple[int, int, int]:
    from picorte.engine.retention_engine import resolve_archetype_retention_policy

    style = resolve_archetype_retention_policy(archetype, tone=tone).get("banner_style", "hype")
    return ARROW_BGR.get(style, ARROW_BGR["hype"])


def target_point(timeline: list[dict[str, Any]] | None, t: float, w: int, h: int) -> tuple[int, int]:
    """Centro da área do JOGO no layout daquele instante (é para onde a seta aponta)."""
    from picorte.engine.reframe_games import LAYOUT_RATIO_MAP

    layout = next((s["layout"] for s in timeline or [] if float(s["start"]) <= t < float(s["end"])), None)
    if layout in ("historia_70_30", "reacao_split_50_50"):
        face_h = LAYOUT_RATIO_MAP[layout] * h / 1920.0
        return int(w // 2), int(round((face_h + h) / 2.0))
    return int(w // 2), int(h // 2)


def make_arrow_overlay(path: Any, size: tuple[int, int], target: tuple[int, int],
                       color: tuple[int, int, int]) -> Path:
    """PNG transparente do tamanho do vídeo com círculo no alvo e seta vindo de cima à esquerda."""
    import cv2
    import numpy as np

    w, h = int(size[0]), int(size[1])
    img = np.zeros((h, w, 4), np.uint8)
    cx, cy = int(target[0]), int(target[1])
    r = max(20, int(w * 0.12))
    thick = max(3, int(w * 0.012))
    tail = (max(0, cx - int(2.2 * r)), max(0, cy - int(2.2 * r)))
    tip = (cx - int(0.75 * r), cy - int(0.75 * r))
    for col, extra in (((0, 0, 0, 255), thick // 2 + 2), ((*color, 255), 0)):
        cv2.circle(img, (cx, cy), r, col, thick + extra, lineType=cv2.LINE_AA)
        cv2.arrowedLine(img, tail, tip, col, thick + extra, line_type=cv2.LINE_AA, tipLength=0.3)
    out = Path(path)
    cv2.imwrite(str(out), img)
    return out


def freeze_ffmpeg_cmd(in_path: Any, overlay_png: Any, out_path: Any, *, t: float, d: float) -> list[str]:
    """Congela o quadro em t por d s (vídeo e áudio pausam) com a seta balançando por cima durante o freeze."""
    graph = (
        "[0:v]split=2[v0][v1];"
        f"[v0]trim=end={t:.3f},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={d:.3f}[vf];"
        f"[vf][1:v]overlay=x=0:y='8*sin(2*PI*2.5*t)':enable='between(t,{t:.3f},{t + d:.3f})':shortest=1[va];"
        f"[v1]trim=start={t:.3f},setpts=PTS-STARTPTS[vb];"
        "[0:a]asplit=2[a0][a1];"
        f"[a0]atrim=end={t:.3f},asetpts=PTS-STARTPTS,apad=pad_dur={d:.3f}[aa];"
        f"[a1]atrim=start={t:.3f},asetpts=PTS-STARTPTS[ab];"
        "[va][aa][vb][ab]concat=n=2:v=1:a=1[v][a]"
    )
    return ["ffmpeg", "-y", "-i", str(in_path), "-loop", "1", "-i", str(overlay_png), "-filter_complex", graph,
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out_path)]


def apply_freeze(seg: dict[str, Any], mp4: Any, *, size: tuple[int, int], runner: Any = None) -> bool:
    """Aplica o freeze planejado no mp4 renderizado (troca em lugar). Falha → arquivo intacto, com motivo."""
    plan = seg.get("freeze")
    if not isinstance(plan, dict) or not plan.get("enabled"):
        return False
    run = runner or subprocess.run
    src = Path(mp4)
    png = src.with_name(src.stem + ".seta.png")
    tmp = src.with_name(src.stem + ".freeze" + src.suffix)
    try:
        target = target_point(seg.get("layout_timeline"), float(plan["t"]), int(size[0]), int(size[1]))
        make_arrow_overlay(png, size, target, arrow_color_for(seg.get("archetype"), seg.get("tone")))
        run(freeze_ffmpeg_cmd(src, png, tmp, t=float(plan["t"]), d=float(plan["d"])), check=True, capture_output=True)
        if not tmp.is_file():
            raise RuntimeError("ffmpeg não gerou o arquivo do freeze")
        tmp.replace(src)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        plan["rendered"] = False
        plan["motivo"] = f"falha ao aplicar o freeze: {type(exc).__name__}"
        return False
    finally:
        png.unlink(missing_ok=True)
    plan["rendered"] = True
    plan["alvo"] = list(target)
    seg.setdefault("transformacoes", []).append(
        {"nome": "freeze_seta", "t": plan["t"], "d": plan["d"], "fonte": plan.get("fonte")})
    return True


def cold_open_start_after_freeze(clip_start: float, cold_open: dict[str, Any] | None,
                                 freeze: dict[str, Any] | None) -> float:
    """O freeze insere d s no vídeo: um teaser que vem depois dele fica d s mais adiante no mp4."""
    if not (cold_open and cold_open.get("enabled") and freeze and freeze.get("enabled")):
        return float(clip_start)
    if float(cold_open["teaser_start"]) - float(clip_start) >= float(freeze["t"]):
        return float(clip_start) - float(freeze["d"])
    return float(clip_start)
