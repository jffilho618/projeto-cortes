"""Vídeos compostos de vários trechos (Épico 3.7 — Story 3.7.4).

- Arco de 2 atos: promessa → desfecho distante ("5 minutos depois..."). O detector (`two_act_arc`) é só léxico,
  então o arco só vale se o desfecho cair dentro de um Short já selecionado (prova de que o momento é bom).
- Compilação por arquétipo: ≥ 4 Shorts do mesmo arquétipo (ex.: "TOP VACILOS DA LIVE").
- Render: cada trecho passa pelo render normal (layout, legenda, Selo Verde = P1 por trecho); trecho barrado sai;
  os pedaços são emendados com cartão de ponte no arco.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Callable

ARC_MAX_TOTAL_S = 180.0
ARC_MAX_PER_VOD = 2
MIN_PIECES = {"arco_2_atos": 2, "compilacao": 4}
CARD_S = 1.5
_PIECE_DROP = ("trechos", "rank", "cold_open", "transformacoes", "layout_timeline", "bridge_text")


from picorte.engine.formats import SHORT_MAX_S  # noqa: E402 — limite único de Short (era 60 aqui e 59 lá)


def _is_short(seg: dict[str, Any]) -> bool:
    """Short de verdade: formato short e ≤ SHORT_MAX_S (corte longo estoura os 240 s da compilação)."""
    dur = float(seg.get("end") or 0.0) - float(seg.get("start") or 0.0)
    return seg.get("formato", "short") == "short" and 0 < dur <= SHORT_MAX_S


def _with_neighbors(sentences: list[dict[str, Any]], start: float, end: float) -> tuple[float, float]:
    """Amplia o ato com a frase anterior e a seguinte (contexto mínimo)."""
    idx = [i for i, s in enumerate(sentences) if float(s["start"]) <= start + 0.01 and float(s["end"]) >= end - 0.01]
    if not idx:
        return start, end
    i = idx[0]
    lo = float(sentences[i - 1]["start"]) if i > 0 else start
    hi = float(sentences[i + 1]["end"]) if i + 1 < len(sentences) else end
    return lo, hi


def arc_composites(sentences: list[dict[str, Any]] | None, shorts: list[dict[str, Any]] | None, *,
                   max_arcs: int = ARC_MAX_PER_VOD) -> list[dict[str, Any]]:
    from picorte.engine.two_act_arc import detect_two_act_arcs

    sents = sorted(sentences or [], key=lambda s: float(s["start"]))
    picked = [s for s in shorts or [] if _is_short(s)]
    out: list[dict[str, Any]] = []
    for arc in detect_two_act_arcs(sents):
        a2s, a2e = float(arc["act2_start"]), float(arc["act2_end"])
        host = next((s for s in picked if float(s["start"]) <= a2s and a2e <= float(s["end"]) + 1.0), None)
        if host is None:
            continue
        p1 = _with_neighbors(sents, float(arc["act1_start"]), float(arc["act1_end"]))
        p2 = _with_neighbors(sents, a2s, a2e)
        total = (p1[1] - p1[0]) + (p2[1] - p2[0])
        if p2[0] <= p1[1] or total > ARC_MAX_TOTAL_S:
            continue
        out.append({
            "formato": "arco_2_atos",
            "start": round(p1[0], 2), "end": round(p2[1], 2), "duration": round(total + CARD_S, 2),
            "trechos": [{"start": round(p1[0], 2), "end": round(p1[1], 2)},
                        {"start": round(p2[0], 2), "end": round(p2[1], 2)}],
            "bridge_text": arc["bridge_text"],
            "archetype": arc.get("archetype") or "deadpan_karma",
            "hook": f"{arc['act1_text'][:30]} … {arc['act2_text'][:30]}",
            "overall": host.get("overall"),
            "moment_id": f"arco-{int(p1[0])}-{int(p2[1])}",
            "reason": f"Arco de 2 atos ({arc['bridge_text']}) com desfecho dentro de um corte selecionado",
        })
        if len(out) >= int(max_arcs):
            break
    return out


def compilation_composites(segments: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    from picorte.engine.archetype_compiler import compile_by_archetype

    out = []
    for comp in compile_by_archetype([s for s in segments or [] if _is_short(s)]):
        clips = comp["clips"]
        out.append({
            "formato": "compilacao",
            "start": round(float(clips[0]["start"]), 2), "end": round(float(clips[-1]["end"]), 2),
            "duration": comp["total_duration"],
            "trechos": [{"start": round(float(c["start"]), 2), "end": round(float(c["end"]), 2)} for c in clips],
            "archetype": comp["archetype"],
            "proposed_title": comp["title"], "hook": comp["title"],
            "overall": comp["avg_score"],
            "moment_id": f"comp-{comp['archetype']}",
            "reason": f"Compilação de {comp['clip_count']} cortes {comp['archetype']}",
        })
    return out


def _slug(text: Any) -> str:
    return re.sub(r"[^\w\-]+", "-", str(text or "clip")).strip("-")[:60] or "clip"


def make_bridge_card(text: str, out: Any, *, size: tuple[int, int] = (1080, 1920), dur: float = CARD_S) -> Path:
    """Cartão preto com o texto da ponte ("5 minutos depois...") e áudio mudo (ASS: sem depender de fonte)."""
    out = Path(out)
    w, h = int(size[0]), int(size[1])
    ass = out.with_suffix(".ass")
    clean = str(text or "").replace("\n", " ").replace("{", "(").replace("}", ")")
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Ponte,Arial,{max(24, round(h * 0.045))},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,"
        "100,100,0,0,1,3,0,5,40,40,0,1\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        f"Dialogue: 0,0:00:00.00,0:00:{dur:05.2f},Ponte,,0,0,0,,{clean}\n",
        encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d={dur}:r=30",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{dur}",
                    "-vf", f"subtitles={ass.name}", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", out.name],
                   check=True, capture_output=True, cwd=str(out.parent))
    ass.unlink(missing_ok=True)
    return out


def concat_parts(parts: list[Any], out: Any) -> Path:
    """Emenda os pedaços (mesmo tamanho) com fps 30 e áudio 48 kHz estéreo (filtro concat)."""
    cmd = ["ffmpeg", "-y"]
    for p in parts:
        cmd += ["-i", str(p)]
    chains = "".join(
        f"[{i}:v]fps=30,setsar=1,format=yuv420p[v{i}];[{i}:a]aresample=48000,"
        f"aformat=channel_layouts=stereo[a{i}];" for i in range(len(parts)))
    joined = "".join(f"[v{i}][a{i}]" for i in range(len(parts)))
    cmd += ["-filter_complex", chains + f"{joined}concat=n={len(parts)}:v=1:a=1[v][a]",
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return Path(out)


def _probe_size(path: Any) -> tuple[int, int]:
    res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", str(path)], check=True, capture_output=True, text=True)
    w, h = res.stdout.strip().split("x")[:2]
    return int(w), int(h)


def _cleanup(path: Path) -> None:
    for p in (path, path.with_suffix(".meta.json"), path.with_suffix(".srt"), path.with_suffix(".png"),
              path.with_name(path.stem + "_thumb.png")):
        Path(p).unlink(missing_ok=True)


def render_composite(comp: dict[str, Any], *, out_dir: Any, render_fn: Callable[..., Any],
                     render_args: tuple = (), render_kwargs: dict[str, Any] | None = None,
                     size: tuple[int, int] | None = None, concat_fn: Callable[..., Any] | None = None,
                     card_fn: Callable[..., Any] | None = None, meta_fn: Callable[..., Any] | None = None
                     ) -> dict[str, Any]:
    """Renderiza cada trecho pelo render normal e emenda. Devolve {output | None, motivo, barrados}."""
    from picorte.risk_shield.policy_gate import PolicyViolationError

    out_dir = Path(out_dir)
    concat = concat_fn or concat_parts
    card = card_fn or make_bridge_card
    cid = str(comp.get("id") or "comp")
    base = {k: v for k, v in comp.items() if k not in _PIECE_DROP}
    pieces: list[Path] = []
    blocked = 0
    for i, t in enumerate(comp.get("trechos") or []):
        sub = {**base, "start": t["start"], "end": t["end"], "duration": round(t["end"] - t["start"], 2),
               "id": f"{cid}-p{i}", "hook": f"parte-{i}", "cold_open": {"enabled": False, "motivo": "trecho"}}
        try:
            pieces.append(Path(render_fn(sub, *render_args, out_dir=out_dir, **(render_kwargs or {}))))
        except PolicyViolationError:
            blocked += 1
    need = MIN_PIECES.get(str(comp.get("formato")), 2)
    if len(pieces) < need:
        for p in pieces:
            _cleanup(p)
        return {"output": None, "barrados": blocked,
                "motivo": f"só {len(pieces)} trechos aprovados pelo P1 (mínimo {need})"}
    parts: list[Path] = list(pieces)
    bridge = None
    if comp.get("formato") == "arco_2_atos" and comp.get("bridge_text") and len(pieces) >= 2:
        bridge = out_dir / f"{cid}-ponte.mp4"
        card(comp["bridge_text"], bridge, size=size or _probe_size(pieces[0]))
        parts = [pieces[0], bridge, *pieces[1:]]
    final = out_dir / f"{_slug(cid)}-{_slug(comp.get('hook'))}.mp4"
    concat(parts, final)
    for p in pieces:
        _cleanup(p)
    if bridge is not None:
        bridge.unlink(missing_ok=True)
    comp.setdefault("transformacoes", []).append(
        {"nome": str(comp.get("formato")), "trechos": len(pieces), "barrados": blocked})
    if meta_fn is not None:
        meta_fn(comp, final)
    return {"output": final, "barrados": blocked, "motivo": None}
