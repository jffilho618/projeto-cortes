"""Gabarito automático e Precision@K do motor de seleção (Épico 3.6 — Story 3.6.1).

Mede o motor; não muda nada nele. O gabarito é fraco e automático, sem anotação manual:
- comentários com horário do YouTube (`comment_seeds.json`, gerado por `comments_miner`);
- picos do heatmap "mais repetidos" (`source_meta.heatmap`, ou `heatmap.json` vindo do `fetch-labels`).

Definições (ver docs/superpowers/plans/2026-11-21-3-6-1-gabarito-baseline-precision-k.md):
- momento = intervalo [a, b]; clipe [s, e] acerta se algum momento cruza [s − tol, e + tol];
- Precision@K = acertos no top-K (por `rank`) / k_efetivo;
- acaso da precisão = probabilidade exata de um clipe do mesmo tamanho, posto ao acaso no VOD, acertar;
- Recall@K = fração dos momentos cobertos pelo top-K; acaso = 1 − Π(1 − p_i) (o K/N da literatura).

Custo zero: `run` só lê arquivos locais. Rede só no `fetch-labels` (metadados, sob pedido, portão P1).
"""
from __future__ import annotations

from datetime import date as _date
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

from picorte.engine import health as _health
from picorte.engine import ingest as _ingest

DEFAULT_TOL = 10.0
DEFAULT_KS = (5, 10)
# Janela padrão do minerador (comments_miner.mine_youtube_comments): t − 12 s … t + 22 s.
_SEED_BEFORE = 12.0
_SEED_AFTER = 22.0
GABARITO_SEED_KINDS = {"comment_timestamp", "heatmap_peak"}


# ------------------------------------------------------------------------------------ gabarito

def _seed_time(seed: dict[str, Any]) -> float:
    if seed.get("timestamp_s") is not None:
        return float(seed["timestamp_s"])
    start = float(seed.get("start") or 0.0)
    end = float(seed.get("end") or 0.0)
    if start > 0:
        return start + _SEED_BEFORE
    return max(0.0, end - _SEED_AFTER)


def comment_moments(seeds: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = []
    for seed in seeds or []:
        if not isinstance(seed, dict):
            continue
        t = round(_seed_time(seed), 2)
        likes = int((seed.get("score_parts") or {}).get("comment_likes") or seed.get("comment_likes") or 0)
        out.append({"fonte": "comentario", "a": t, "b": t, "t": t, "likes": likes,
                    "texto": str(seed.get("text") or "")[:180]})
    return out


def heatmap_moments(heatmap: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [{"fonte": "heatmap", "a": float(p["start"]), "b": float(p["end"]), "t": float(p["center"]),
             "valor": float(p["value"])}
            for p in _ingest.extract_heatmap_peaks(list(heatmap or []))]


# Filtro do gabarito: comentário com horário que NÃO marca um momento bom (pergunta, reclamação técnica,
# marca de início, horário solto). Fica guardado em "removidos" com o motivo, para conferência.
_TS_ANY = re.compile(r"\b(?:\d{1,2}:)?\d{1,2}:\d{2}\b")
_PERGUNTA_INICIO = re.compile(r"^(qual|quais|quem|quando|onde|como|por ?que|alguem sabe|que musica|nome da musica)\b")
_TECNICO = re.compile(r"\b(fps|lag|lagou|lagando|travou|travando|delay|buffer\w*|sem (som|audio)|mutou|mutad\w*)\b"
                      r"|\b(som|sons|audio)\b.*\batrasad|\bcaiu a (live|transmissao)\b")
_INICIO = re.compile(r"\bcomeca (aqui|em|a gameplay|o jogo)\b|\binicio (da live|da gameplay|do jogo)\b")


def _fold(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _has_content(text: str) -> bool:
    """Tem letra ou emoji (😂🔥 contam como reação do público)."""
    return any(ch.isalpha() or ord(ch) >= 0x2600 for ch in text)


def motivo_fora_do_gabarito(texto: str) -> str | None:
    """Motivo para um comentário com horário NÃO contar como momento bom; None se ele conta."""
    raw = _TS_ANY.sub(" ", str(texto or "")).strip()
    if not _has_content(raw):
        return "sem_texto"
    low = _fold(raw).strip(" -–—:;,.!")
    if low.endswith("?") or _PERGUNTA_INICIO.search(low):
        return "pergunta"
    if _TECNICO.search(low):
        return "tecnico"
    if _INICIO.search(low):
        return "inicio"
    return None


def build_gabarito(seeds, heatmap) -> dict[str, Any]:
    comments, removidos = [], []
    for m in comment_moments(seeds):
        motivo = motivo_fora_do_gabarito(m["texto"])
        if motivo:
            removidos.append({"t": m["t"], "texto": m["texto"], "likes": m["likes"], "motivo": motivo})
        else:
            comments.append(m)
    peaks = heatmap_moments(heatmap)
    momentos = sorted(comments + peaks, key=lambda m: (m["t"], m["fonte"]))
    return {
        "status": "ok" if momentos else "sem_gabarito",
        "momentos": momentos,
        "fontes": {"comentarios": len(comments), "heatmap": len(peaks)},
        "removidos": removidos,
    }


# ------------------------------------------------------------------------------------ acerto e acaso

def clip_hits(start: float, end: float, moments, tol: float = DEFAULT_TOL) -> bool:
    lo, hi = float(start) - tol, float(end) + tol
    return any(float(m["a"]) <= hi and float(m["b"]) >= lo for m in moments or [])


def _start_interval(length: float, span: float, moment: dict[str, Any], tol: float) -> tuple[float, float] | None:
    """Inícios s ∈ [0, span] em que um clipe de `length` acerta o momento."""
    lo = max(0.0, float(moment["a"]) - length - tol)
    hi = min(span, float(moment["b"]) + tol)
    return (lo, hi) if hi >= lo else None


def chance_hit(length: float, duration: float, moments, tol: float = DEFAULT_TOL) -> float:
    """Probabilidade exata de um clipe de `length` com início uniforme no VOD acertar algum momento."""
    moments = list(moments or [])
    if not moments:
        return 0.0
    span = float(duration) - float(length)
    if span <= 0:
        return 1.0
    intervals = sorted(iv for iv in (_start_interval(length, span, m, tol) for m in moments) if iv)
    covered, cur_lo, cur_hi = 0.0, None, None
    for lo, hi in intervals:
        if cur_hi is None or lo > cur_hi:
            if cur_hi is not None:
                covered += cur_hi - cur_lo
            cur_lo, cur_hi = lo, hi
        else:
            cur_hi = max(cur_hi, hi)
    if cur_hi is not None:
        covered += cur_hi - cur_lo
    return min(1.0, covered / span)


def chance_cover(lengths, duration: float, moment: dict[str, Any], tol: float = DEFAULT_TOL) -> float:
    """Probabilidade de ao menos um de K clipes aleatórios (tamanhos `lengths`) cobrir o momento."""
    miss = 1.0
    for length in lengths:
        miss *= 1.0 - chance_hit(length, duration, [moment], tol)
    return 1.0 - miss


# ------------------------------------------------------------------------------------ avaliação

def _ranked(segments) -> list[dict[str, Any]]:
    segs = [s for s in segments or [] if isinstance(s, dict)]
    return sorted(segs, key=lambda s: (int(s.get("rank") or 10**6), -float(s.get("overall") or 0.0),
                                       float(s.get("start") or 0.0)))


def evaluate_vod(segments, gabarito: dict[str, Any], duration: float, ks=DEFAULT_KS,
                 tol: float = DEFAULT_TOL) -> dict[str, Any]:
    ranked = _ranked(segments)
    if gabarito.get("status") != "ok":
        return {"status": "sem_gabarito", "clipes": len(ranked)}
    moments = gabarito["momentos"]
    duration = float(duration)
    result: dict[str, Any] = {"status": "ok", "clipes": len(ranked), "momentos": len(moments), "k": {}}
    for k in ks:
        top = ranked[:int(k)]
        n = len(top)
        lengths = [max(0.0, float(s["end"]) - float(s["start"])) for s in top]
        acertos = sum(1 for s in top if clip_hits(s["start"], s["end"], moments, tol))
        cobertos = sum(1 for m in moments if any(clip_hits(s["start"], s["end"], [m], tol) for s in top))
        precisao = acertos / n if n else 0.0
        acaso = (sum(chance_hit(L, duration, moments, tol) for L in lengths) / n) if n else 0.0
        recall = cobertos / len(moments)
        recall_acaso = sum(chance_cover(lengths, duration, m, tol) for m in moments) / len(moments)
        result["k"][str(k)] = {
            "k_efetivo": n,
            "acertos": acertos,
            "precisao": precisao,
            "precisao_acaso": acaso,
            "lift": precisao / acaso if acaso > 0 else None,
            "recall": recall,
            "recall_acaso": recall_acaso,
            "semeados_pelo_gabarito": sum(1 for s in top if s.get("seed_kind") in GABARITO_SEED_KINDS),
        }
    return result


# ------------------------------------------------------------------------------------ projetos

_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_id(url: Any) -> str | None:
    parsed = urlparse(str(url or ""))
    host = (parsed.netloc or "").lower()
    vid = None
    if host.endswith("youtu.be"):
        vid = parsed.path.strip("/").split("/")[0]
    elif "youtube.com" in host:
        vid = (parse_qs(parsed.query).get("v") or [None])[0]
        if not vid and parsed.path.startswith(("/live/", "/shorts/")):
            vid = parsed.path.split("/")[2]
    return vid if vid and _YT_ID.match(vid) else None


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_project(workdir: Any) -> dict[str, Any] | None:
    """Lê o que o benchmark precisa de um projeto já processado; None se não houver seleção."""
    d = Path(workdir)
    segments = _read_json(d / "segments.json", None)
    if not isinstance(segments, list):
        return None
    state = _read_json(d / "project.json", {}) or {}
    meta = state.get("source_meta") or {}
    selection = _read_json(d / "selection.json", {}) or {}
    heatmap = meta.get("heatmap") or _read_json(d / "heatmap.json", []) or []
    seeds = _read_json(d / "comment_seeds.json", []) or []
    duration = meta.get("duration") or selection.get("source_duration") or 0.0
    return {
        "workdir": d,
        "projeto": state.get("id") or d.name,
        "source": state.get("source"),
        "video_id": youtube_id(state.get("source")),
        "titulo": meta.get("title") or "",
        "duracao": float(duration or 0.0),
        "updated": float(state.get("updated") or 0.0),
        "modo_ia": selection.get("mode") or (state.get("options") or {}).get("ai_mode"),
        "modo_cego": bool((state.get("options") or {}).get("benchmark_blind")),
        "segments": segments,
        "candidates": list((_read_json(d / "candidates.json", {}) or {}).get("candidates") or []),
        "seeds": seeds if isinstance(seeds, list) else [],
        "heatmap": heatmap if isinstance(heatmap, list) else [],
    }


def _rounded(obj: Any) -> Any:
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _rounded(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rounded(v) for v in obj]
    return obj


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


PRE_EDITOR_KS = (10, 20)


def evaluate_pre_editor(candidates, gabarito: dict[str, Any], duration: float, ks=PRE_EDITOR_KS,
                        tol: float = DEFAULT_TOL) -> dict[str, Any] | None:
    """Mede a lista de candidatos da descoberta (ordem pela nota do motor), ANTES do Editor-Chefe — sem sorteio de LLM.

    `cobertura` = fração dos momentos do público que têm ao menos um candidato em cima (o teto do que o juiz pode achar).
    """
    cands = [c for c in candidates or [] if isinstance(c, dict) and "start" in c and "end" in c]
    if not cands or gabarito.get("status") != "ok":
        return None
    out = evaluate_vod(cands, gabarito, duration, ks=ks, tol=tol)
    moments = gabarito["momentos"]
    out["candidatos"] = len(cands)
    out["cobertura"] = sum(1 for m in moments if any(clip_hits(c["start"], c["end"], [m], tol) for c in cands)) \
        / len(moments)
    return out


def _average(vods: list[dict[str, Any]], ks, key: str = "resultado") -> dict[str, Any]:
    vods = [v for v in vods if v.get(key)]
    media: dict[str, Any] = {"vods_com_gabarito": len(vods), "k": {}}
    if not vods:
        return media
    for k in ks:
        rows = [v[key]["k"][str(k)] for v in vods]
        prec = sum(r["precisao"] for r in rows) / len(rows)
        acaso = sum(r["precisao_acaso"] for r in rows) / len(rows)
        media["k"][str(k)] = {
            "precisao": prec,
            "precisao_acaso": acaso,
            "lift": prec / acaso if acaso > 0 else None,
            "recall": sum(r["recall"] for r in rows) / len(rows),
            "recall_acaso": sum(r["recall_acaso"] for r in rows) / len(rows),
            "vods_acima_do_acaso": sum(1 for r in rows if r["precisao"] > r["precisao_acaso"]),
        }
    return media


def run_benchmark(projects_dir: Any, out_dir: Any, *, date: str | None = None, label: str | None = None,
                  ks=DEFAULT_KS, tol: float = DEFAULT_TOL, conjunto: Any = None) -> dict[str, Any]:
    """Mede todos os projetos com seleção; grava <out>/<data>[-<label>].json e <out>/gabaritos/<vod>.json."""
    projects_dir, out_dir = Path(projects_dir), Path(out_dir)
    date = date or _date.today().isoformat()
    loaded = [p for p in (load_project(d) for d in sorted(projects_dir.iterdir()) if d.is_dir()) if p]
    if conjunto is not None:  # só o conjunto de prova (projetos em modo cego)
        wanted = {v.get("projeto") for v in (_read_json(Path(conjunto), {}) or {}).get("vods") or []}
        loaded = [p for p in loaded if p["projeto"] in wanted]

    latest: dict[str, dict[str, Any]] = {}
    for proj in loaded:
        key = proj["video_id"] or proj["projeto"]
        if key not in latest or proj["updated"] > latest[key]["updated"]:
            latest[key] = proj
    chosen = sorted(latest.values(), key=lambda p: p["projeto"])
    duplicados = [{"projeto": p["projeto"], "video_id": p["video_id"],
                   "usado": latest[p["video_id"] or p["projeto"]]["projeto"]}
                  for p in loaded if latest[p["video_id"] or p["projeto"]] is not p]

    vods, sem = [], []
    for proj in chosen:
        gab = build_gabarito(proj["seeds"], proj["heatmap"])
        base = {"projeto": proj["projeto"], "video_id": proj["video_id"], "titulo": proj["titulo"],
                "duracao_s": proj["duracao"], "modo_ia": proj["modo_ia"], "modo_cego": proj["modo_cego"],
                "fontes": gab["fontes"]}
        if gab["status"] != "ok":
            sem.append({**base, "motivo": "sem comentários com horário nem heatmap"})
            _health.record(proj["workdir"], "benchmark_gabarito", "na",
                           "sem gabarito (sem comentários com horário nem heatmap)")
            continue
        resultado = evaluate_vod(proj["segments"], gab, proj["duracao"], ks=ks, tol=tol)
        pre = evaluate_pre_editor(proj["candidates"], gab, proj["duracao"], tol=tol)
        vods.append({**base, "resultado": resultado, "pre_editor": pre})
        _write_json(out_dir / "gabaritos" / f"{proj['video_id'] or proj['projeto']}.json", _rounded({
            "video_id": proj["video_id"], "projeto": proj["projeto"], "titulo": proj["titulo"],
            "duracao_s": proj["duracao"], "medido_em": date, **gab}))
        _health.record(proj["workdir"], "benchmark_gabarito", "ok",
                       f"{gab['fontes']['comentarios']} comentários + {gab['fontes']['heatmap']} picos do heatmap")

    report = _rounded({
        "data": date,
        "label": label,
        "conjunto": str(conjunto) if conjunto is not None else None,
        "tol_s": tol,
        "ks": list(ks),
        "custo": "zero (só arquivos locais; nenhuma chamada a LLM)",
        "media": _average(vods, ks),
        "media_pre_editor": _average(vods, PRE_EDITOR_KS, key="pre_editor"),
        "vods": vods,
        "sem_gabarito": sem,
        "duplicados_ignorados": duplicados,
    })
    _write_json(out_dir / (f"{date}-{label}.json" if label else f"{date}.json"), report)
    return report


# ------------------------------------------------------------------------------------ fetch-labels

def _default_gate(url: str, meta: dict[str, Any]) -> dict[str, Any]:
    from picorte.db.connection import get_default_db
    from picorte.risk_shield.source_resolver import gate_project_source

    return gate_project_source(get_default_db(), source_input=url, meta=meta)


def fetch_labels(workdir: Any, *, runner=None, gate=None) -> dict[str, Any]:
    """Completa o gabarito de um projeto já processado: comentários com horário + heatmap (só metadados).

    Rede sob pedido explícito; passa pelo portão P1 real; nunca toca project/candidates/segments/selection.
    Grava `comment_seeds.json` (se ainda não existe, igual ao prepare pós-1b) e `heatmap.json`.
    """
    import subprocess
    from picorte.engine import comments_miner as _cm

    d = Path(workdir)
    state = _read_json(d / "project.json", {}) or {}
    url = str(state.get("source") or "")
    meta = state.get("source_meta") or {}
    if not youtube_id(url):
        _health.record(d, "benchmark_labels", "na", "fonte não é YouTube")
        return {"status": "na", "detalhe": "fonte não é YouTube"}
    try:
        verdict = (gate or _default_gate)(url, meta)
    except Exception as exc:  # fail-closed: qualquer recusa ou erro do portão bloqueia
        _health.record(d, "benchmark_labels", "na", f"bloqueado pelo P1: {exc}")
        return {"status": "bloqueado_p1", "detalhe": str(exc)[:300]}

    captured: dict[str, str] = {}
    base_run = runner or (lambda cmd, **kw: subprocess.run(cmd, timeout=_cm.COMMENTS_TIMEOUT, **kw))

    def _capture(cmd, **kwargs):
        res = base_run(cmd, **kwargs)
        captured["stdout"] = res.stdout or ""
        return res

    try:
        seeds = _cm.mine_youtube_comments(url, permission_status=verdict.get("permission_status") or "liberada",
                                          runner=_capture, max_comments=300)
        heatmap = _ingest._normalize_heatmap(json.loads(captured.get("stdout") or "{}").get("heatmap"))
    except Exception as exc:
        _health.record(d, "benchmark_labels", "failed", f"{type(exc).__name__}: {exc}")
        return {"status": "failed", "detalhe": f"{type(exc).__name__}: {exc}"[:300]}

    if not (d / "comment_seeds.json").is_file():
        _write_json(d / "comment_seeds.json", seeds)
    if heatmap:
        _write_json(d / "heatmap.json", heatmap)
    detail = f"{len(seeds)} comentários com horário, {len(heatmap)} faixas de heatmap"
    _health.record(d, "benchmark_labels", "ok" if (seeds or heatmap) else "na", detail)
    return {"status": "ok", "comentarios": len(seeds), "heatmap_bins": len(heatmap)}


# ------------------------------------------------------------------------------------ conjunto de prova

MIN_GABARITO_MOMENTS = 3        # comentários com horário + picos do heatmap
MIN_CHAT_PER_MIN = 20.0         # abaixo disso o Sismógrafo 2.0 (3.6.2) desliga
# As opções de sempre do dono (9:16, games, até 58 s) + modo cego. Editor-Chefe fixo no Qwen local para o
# antes/depois ser comparável: a cota grátis do Gemini acabou em 2026-11-21 com lives longas (429, ~4 dias).
BENCH_OPTIONS = {"aspect": "9:16", "layout": "games", "max_len": 58, "ai_mode": "ollama", "llm": "qwen3.5:9b",
                 "benchmark_blind": True}


def _default_probe(url: str) -> dict[str, Any]:
    meta = _ingest.probe_source(url)
    meta.pop("formats", None)
    return meta


def _default_comments(url, workdir, **kw):
    from picorte.engine import comments_miner as _cm
    return _cm.save_comment_seeds(url, workdir, **kw)


def _default_chat(url, workdir, **kw):
    return _ingest.download_live_chat(url, workdir, **kw)


def triar_vod(url: str, workdir: Any, *, probe=None, gate=None, comments=None, chat=None) -> dict[str, Any]:
    """Confere uma live ANTES de baixar mídia: portão P1, gabarito (comentários + heatmap) e chat movimentado.

    Só metadados; comentários e chat ficam em `workdir` para o prepare reaproveitar (não baixa duas vezes).
    """
    d = Path(workdir)
    d.mkdir(parents=True, exist_ok=True)
    meta = (probe or _default_probe)(url)
    duration = float(meta.get("duration") or 0.0)
    out: dict[str, Any] = {"url": url, "video_id": youtube_id(url), "titulo": meta.get("title") or "",
                           "canal": meta.get("channel"), "duracao_s": duration, "comentarios": 0,
                           "picos_heatmap": 0, "chat_msgs_min": 0.0, "aprovado": False, "motivos": []}
    try:
        verdict = (gate or _default_gate)(url, meta)
    except Exception as exc:
        out["motivos"].append(f"bloqueado pelo P1: {str(exc)[:200]}")
        return out

    status = verdict.get("permission_status") or "liberada"
    (comments or _default_comments)(url, d, permission_status=status)
    seeds = _read_json(d / "comment_seeds.json", []) or []
    out["comentarios"] = len(seeds)
    out["picos_heatmap"] = len(_ingest.extract_heatmap_peaks(meta.get("heatmap")))
    if out["comentarios"] + out["picos_heatmap"] < MIN_GABARITO_MOMENTS:
        out["motivos"].append(f"poucos comentários com horário ({out['comentarios']}) e picos de heatmap "
                              f"({out['picos_heatmap']}); precisa de {MIN_GABARITO_MOMENTS} momentos")

    (chat or _default_chat)(url, d, timeout=_ingest.chat_timeout_for(duration))
    msgs = _read_json(d / "chat.json", []) or []
    minutes = (duration or (float(msgs[-1].get("t") or 0.0) if msgs else 0.0)) / 60.0
    out["chat_msgs_min"] = round(len(msgs) / minutes, 1) if minutes > 0 else 0.0
    if not msgs:
        out["motivos"].append("sem chat salvo (não é gravação de live, ou o chat não ficou salvo)")
    elif out["chat_msgs_min"] < MIN_CHAT_PER_MIN:
        out["motivos"].append(f"chat parado ({out['chat_msgs_min']} msg/min; precisa de {MIN_CHAT_PER_MIN:g})")
    out["aprovado"] = not out["motivos"]
    return out


def sem_triagem(url: str, workdir: Any = None) -> dict[str, Any]:
    """Padrão do dono: as lives da lista já foram escolhidas por ele; nada é conferido antes do prepare."""
    return {"url": url, "video_id": youtube_id(url), "aprovado": True, "motivos": [], "triagem": False}


def preparar_conjunto(urls, projects_dir: Any, out_dir: Any, *, triar=None, create=None, run=None,
                      options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Triagem + prepare (modo cego) das lives aprovadas; grava/atualiza <out>/conjunto.json."""
    import shutil

    projects_dir, out_dir = Path(projects_dir), Path(out_dir)
    conj_path = out_dir / "conjunto.json"
    conj = _read_json(conj_path, {}) or {}
    conj.setdefault("criterios", {"min_momentos_gabarito": MIN_GABARITO_MOMENTS,
                                  "min_chat_msgs_min": MIN_CHAT_PER_MIN})
    conj.setdefault("vods", [])
    conj.setdefault("descartados", [])
    seen = {v.get("video_id") for v in conj["vods"]}
    opts = {**BENCH_OPTIONS, **(options or {})}

    def _save():
        _write_json(conj_path, conj)

    for url in urls:
        vid = youtube_id(url)
        if not vid or vid in seen:
            continue
        seen.add(vid)
        triagem_dir = out_dir / "triagem" / vid
        try:
            tri = (triar or triar_vod)(url, triagem_dir)
        except Exception as exc:
            tri = {"url": url, "video_id": vid, "aprovado": False, "motivos": [f"triagem falhou: {exc}"[:300]]}
        conj["descartados"] = [x for x in conj["descartados"] if x.get("video_id") != vid]
        if not tri.get("aprovado"):
            conj["descartados"].append(tri)
            _save()
            continue
        if create is None or run is None:
            from picorte.engine import projects as _projects
            create = create or _projects.create_project
            run = run or _projects.run_project
        state = create(projects_dir, url, dict(opts))
        path = projects_dir / state["id"]
        for name in ("comment_seeds.json", "chat.json"):
            if (triagem_dir / name).is_file():
                shutil.copy2(triagem_dir / name, path / name)
        entry = {**tri, "projeto": state["id"]}
        try:
            entry["status"] = (run(path, action="prepare") or {}).get("status")
        except (Exception, SystemExit) as exc:
            entry["status"], entry["erro"] = "failed", str(exc)[:300]
        conj["vods"].append(entry)
        _save()
    _save()
    return conj


def _read_urls(path: str) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


# ------------------------------------------------------------------------------------ CLI

def _print_report(report: dict[str, Any]) -> None:
    for v in report["vods"]:
        line = [f"{v['projeto']} {v['video_id'] or '-'} ({v['fontes']['comentarios']} com., "
                f"{v['fontes']['heatmap']} heat.)"]
        for k, r in v["resultado"]["k"].items():
            line.append(f"P@{k}={r['precisao']:.2f} (acaso {r['precisao_acaso']:.2f}, k_ef {r['k_efetivo']})")
        print(" | ".join(line))
    for v in report["sem_gabarito"]:
        print(f"{v['projeto']} {v['video_id'] or '-'}: sem gabarito")
    print(json.dumps(report["media"], ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m picorte.engine.benchmark",
                                 description="Gabarito automático e Precision@K do motor (Story 3.6.1).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="mede os projetos (custo zero, só arquivos locais)")
    run.add_argument("--projects", default="projects")
    run.add_argument("--out", default="benchmarks")
    run.add_argument("--label", default=None)
    run.add_argument("--date", default=None)
    run.add_argument("--tol", type=float, default=DEFAULT_TOL)
    run.add_argument("--conjunto", default=None, help="mede só o conjunto de prova (ex.: benchmarks/conjunto.json)")
    tri = sub.add_parser("triar", help="só confere as lives de uma lista (P1, comentários, chat); não baixa mídia")
    tri.add_argument("lista")
    tri.add_argument("--out", default="benchmarks")
    prep = sub.add_parser("preparar-conjunto", help="triagem + prepare em modo cego das lives aprovadas")
    prep.add_argument("lista")
    prep.add_argument("--projects", default="projects")
    prep.add_argument("--out", default="benchmarks")
    prep.add_argument("--com-triagem", action="store_true",
                      help="confere P1, comentários e chat antes de baixar (padrão: sem triagem)")
    fetch = sub.add_parser("fetch-labels", help="baixa só metadados (comentários + heatmap) de projetos")
    fetch.add_argument("project_ids", nargs="+")
    fetch.add_argument("--projects", default="projects")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        _print_report(run_benchmark(args.projects, args.out, date=args.date, label=args.label, tol=args.tol,
                                    conjunto=args.conjunto))
        return 0
    if args.cmd == "triar":
        for url in _read_urls(args.lista):
            vid = youtube_id(url) or "sem_id"
            r = triar_vod(url, Path(args.out) / "triagem" / vid)
            status = "OK  " if r["aprovado"] else "NÃO "
            info = f"{r['comentarios']} com., {r['picos_heatmap']} heat., {r['chat_msgs_min']} msg/min"
            extra = "" if r["aprovado"] else " | " + "; ".join(r["motivos"])
            print(f"{status}{vid} {r['titulo'][:60]} | {info}{extra}", flush=True)
        return 0
    if args.cmd == "preparar-conjunto":
        conj = preparar_conjunto(_read_urls(args.lista), args.projects, args.out,
                                 triar=None if args.com_triagem else sem_triagem)
        resumo = {"vods": [(v["video_id"], v.get("projeto"), v.get("status")) for v in conj["vods"]],
                  "descartados": [(v.get("video_id"), v.get("motivos")) for v in conj["descartados"]]}
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
        return 0
    for pid in args.project_ids:
        print(pid, json.dumps(fetch_labels(Path(args.projects) / pid), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
