"""Shared, resumable local project pipeline for CLI and dashboard."""
import hashlib
import json
import math
import re
import time
import uuid
from pathlib import Path

import download_and_transcribe as dt
import render_clips
import score_clips
import evidence
import visual
import ingest
import sections
import branding
from captions import update_transcript

DEFAULT_OPTIONS = {"aspect": "16:9", "style": "default", "tighten": False,
                   "loudnorm": False, "whisper_model": "auto", "device": "auto",
                   "vision_preset": "auto",
                   "min_len": 15, "max_len": 300, "max_clips": None,
                   "min_score": 8.0, "preferred_len": None,
                   "llm": None, "ai_mode": "heuristic",
                   "ai_filter": "ollama", "ai_companion": "claude",
                   "search": None, "semantic": None, "query": None,
                   "hunt_mode": "fast",
                   "embed_model": "nomic-embed-text", "brand": None,
                   "layout": "single", "centers": [0.25, 0.75], "caption": None,
                   "source_owner": None, "keyframes": False,
                   "benchmark_blind": False, "formatos_extras": True}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def atomic_json(path, data):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_identity(path):
    path = Path(path).resolve()
    stat = path.stat()
    return [str(path), stat.st_size, stat.st_mtime_ns]


def validate_options(options):
    unknown = set(options) - set(DEFAULT_OPTIONS)
    if unknown:
        raise ValueError(f"Unknown settings: {', '.join(sorted(unknown))}")
    result = {**DEFAULT_OPTIONS, **options}
    if result["aspect"] not in render_clips.ASPECTS or result["style"] not in render_clips.CAPTION_STYLES:
        raise ValueError("Unknown aspect ratio or caption style.")
    if result["layout"] not in {"single", "split", "games"}:
        raise ValueError("Layout must be single, split or games.")
    if result["layout"] in {"split", "games"} and result["aspect"] != "9:16":
        raise ValueError("Split/Games split-screen requires aspect 9:16.")
    for key in ("min_len", "max_len"):
        if isinstance(result[key], bool) or not isinstance(result[key], int) or not 1 <= result[key] <= 3600:
            raise ValueError(f"{key} must be an integer from 1 to 3600.")
    if result["min_len"] > result["max_len"]:
        raise ValueError("Minimum clip length cannot exceed maximum clip length.")
    if result["max_clips"] is not None and (
            isinstance(result["max_clips"], bool) or not isinstance(result["max_clips"], int)
            or not 1 <= result["max_clips"] <= 3600):
        raise ValueError("max_clips must be an integer from 1 to 3600 or null.")
    if result["min_score"] is not None and (not isinstance(result["min_score"], (int, float))
            or not math.isfinite(result["min_score"]) or not 0 <= result["min_score"] <= 10):
        raise ValueError("Minimum score must be between 0 and 10.")
    if result["preferred_len"] is not None:
        try:
            preferred = score_clips.parse_duration(result["preferred_len"])
        except ValueError as exc:
            raise ValueError(f"preferred_len is invalid. {exc}") from exc
        preferred = float(max(result["min_len"], min(result["max_len"], preferred)))
        result["preferred_len"] = int(preferred) if preferred.is_integer() else preferred
    if result["device"] not in {"cpu", "cuda", "auto"}:
        raise ValueError("Device must be cpu, cuda or auto.")
    if result["vision_preset"] not in {"auto", "low", "high"}:
        raise ValueError("vision_preset must be auto, low or high.")
    if result["whisper_model"] == "auto" or result["device"] == "auto":
        from picorte.config import resolve_vision_preset
        vp = resolve_vision_preset(result["vision_preset"])
        if result["whisper_model"] == "auto":
            if result["vision_preset"] == "auto":
                result["whisper_model"] = vp["gpu_profile"]["whisper_model"]
            else:
                result["whisper_model"] = vp["models"]["whisper_model"]
        if result["device"] == "auto":
            result["device"] = vp["gpu_profile"]["device"]
    if result["ai_mode"] not in {"heuristic", "ollama", "claude", "gemini", "dupla"}:
        raise ValueError("ai_mode must be heuristic, ollama, claude, gemini or dupla.")
    for k in ("ai_filter", "ai_companion"):
        if result[k] not in {"ollama", "claude", "gemini"}:
            raise ValueError(f"{k} must be ollama, claude or gemini.")
    if result["hunt_mode"] is None:
        result["hunt_mode"] = "fast"
    if result["hunt_mode"] not in {"fast", "deep"}:
        raise ValueError("hunt_mode must be fast or deep.")
    if result["search"] and result["semantic"]:
        raise ValueError("Choose keyword search or semantic search, not both.")
    centers = result["centers"]
    if not isinstance(centers, (list, tuple)) or len(centers) != 2 or any(
            not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in centers):
        raise ValueError("Provide two speaker centers between 0 and 1.")
    for key in ("whisper_model", "embed_model", "llm", "search", "semantic", "query", "brand"):
        if result[key] is not None and (not isinstance(result[key], str) or len(result[key]) > 2000):
            raise ValueError(f"{key} must be text.")
    for key in ("tighten", "loudnorm"):
        if not isinstance(result[key], bool):
            raise ValueError(f"{key} must be true or false.")
    if result["caption"] is not None:
        result["caption"] = branding.validate_caption(result["caption"])
    if result["source_owner"] is not None and (
            not isinstance(result["source_owner"], str) or len(result["source_owner"]) > 64):
        raise ValueError("source_owner must be 'proprio' or a registered streamer slug.")
    if not isinstance(result["keyframes"], bool):
        raise ValueError("keyframes must be true or false.")
    if not isinstance(result["benchmark_blind"], bool):
        raise ValueError("benchmark_blind must be true or false.")
    if not isinstance(result["formatos_extras"], bool):
        raise ValueError("formatos_extras must be true or false.")
    return result


def score_options(options):
    keys = ("llm", "ai_mode", "ai_filter", "ai_companion", "vision_preset", "search",
            "semantic", "query", "hunt_mode", "embed_model", "min_score", "max_clips", "min_len",
            "max_len", "preferred_len")
    return {key: options.get(key, DEFAULT_OPTIONS.get(key)) for key in keys}


def score_keys(transcript_key, data, options):
    """Return (discovery_key, selection_key) for split stage caching."""
    discovery_options = {key: options[key] for key in (
        "search", "semantic", "embed_model", "min_len", "max_len",
        "preferred_len")}
    if options.get("benchmark_blind"):  # modo cego (3.6.1): só entra na chave quando ligado
        discovery_options["benchmark_blind"] = True
    discovery_key = digest([transcript_key, data, discovery_options,
                            evidence.EVIDENCE_VERSION,
                            visual.FEATURE_VERSION])
    selection_options = {
        key: options.get(key, DEFAULT_OPTIONS.get(key))
        for key in ("min_score", "max_clips", "llm", "ai_mode", "ai_filter", "ai_companion", "vision_preset", "query", "hunt_mode",
                    "keyframes")
    }
    if options.get("formatos_extras") is False:  # 3.7.3: só entra na chave quando desligado (cache atual vale)
        selection_options["formatos_extras"] = False
    selection_key = digest([discovery_key, selection_options])
    return discovery_key, selection_key


def project_path(root, project_id):
    if not re.fullmatch(r"[a-f0-9]{12}", project_id):
        raise ValueError("Invalid project ID.")
    return Path(root) / project_id


def create_project(root, source, options):
    project_id = uuid.uuid4().hex[:12]
    return init_project(project_path(root, project_id), source, options, project_id)


def init_project(path, source, options, project_id=None):
    if not isinstance(source, str) or not source.strip() or len(source) > 8000:
        raise ValueError("Provide a video path or URL.")
    options = validate_options(options)
    source = source.strip()
    if Path(source).expanduser().is_file():
        source = str(Path(source).expanduser().resolve())
    project_id = project_id or uuid.uuid4().hex[:12]
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    state = {"id": project_id, "source": source.strip(), "options": options,
             "status": "new", "stage": "waiting", "created": time.time(),
             "updated": time.time(), "cache": {}, "renders": {}, "error": None}
    save_project(path, state)
    return state


def read_project(path):
    return read_json(Path(path) / "project.json")


def save_project(path, state):
    state["updated"] = time.time()
    atomic_json(Path(path) / "project.json", state)


def edit_transcript(path, words):
    path = Path(path)
    data = update_transcript(read_json(path / "transcript.json"), words)
    atomic_json(path / "transcript.json", data)
    state = read_project(path)
    # Preserve candidate time ranges for manual editing; changed words invalidate renders.
    state["status"] = "review"
    save_project(path, state)
    return data


TIKTOK_MAX_LEN = 75


def link_format_family(segments):
    """3.7.3: versão TikTok e Longo apontam para o Short do mesmo momento (`parent_short_id`)."""
    short_by_moment = {s.get("moment_id"): s.get("id") for s in segments
                       if s.get("moment_id") and s.get("formato", "short") == "short"}
    out = []
    for seg in segments:
        rec = dict(seg)
        if rec.get("formato") in ("tiktok_60", "longo_16x9") and short_by_moment.get(rec.get("moment_id")):
            rec["parent_short_id"] = short_by_moment[rec["moment_id"]]
        out.append(rec)
    return out


def render_params_for(seg, options):
    """(aspect, layout, max_len do Cold Open) de cada segmento: o Longo sai 16:9, layout simples e sem Cold Open."""
    if seg.get("formato") == "longo_16x9" or seg.get("aspect") == "16:9" and options["aspect"] != "16:9":
        return "16:9", "single", None
    if seg.get("formato") in ("arco_2_atos", "compilacao"):  # 3.7.4: compostos não ganham Cold Open
        return options["aspect"], options["layout"], None
    max_len = TIKTOK_MAX_LEN if seg.get("formato") == "tiktok_60" else options.get("max_len")
    return options["aspect"], options["layout"], max_len


def _chat_peaks(path):
    """Picos do Sismógrafo do chat (3.6.2) gravados no projeto; vazio sem chat (3.7.1: clímax do Cold Open)."""
    try:
        data = json.loads((Path(path) / "chat_seismic.json").read_text(encoding="utf-8"))
        return list(data.get("peaks") or []) if isinstance(data, dict) else []
    except (OSError, ValueError):
        return []


def validate_segments(segments, duration):
    if not isinstance(segments, list):
        raise ValueError("Candidates must be a list.")
    if not segments:
        return []
    result = []
    for item in segments:
        if not isinstance(item, dict):
            raise ValueError("Each clip must be an object.")
        start, end = float(item["start"]), float(item["end"])
        score = float(item.get("overall", 0))
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= duration:
            raise ValueError("Clip times must be inside the source video.")
        if not math.isfinite(score) or not 0 <= score <= 10:
            raise ValueError("Clip score must be between 0 and 10.")
        record = dict(item)
        record.update(start=start, end=end,
                      hook=str(item.get("hook", "clip"))[:200], overall=score)
        result.append(record)
    return result


def run_project(path, action="all", preview=False, pick=None, resume=True, progress=None):
    """Prepare candidates or render saved candidates; checkpoint every successful clip.

    Holds the per-project job lock (B9) so the Studio can tell a live job from an interrupted one.
    """
    from picorte.services.job_lock import segurar_job
    with segurar_job(Path(path).resolve()):
        return _run_project(path, action=action, preview=preview, pick=pick,
                            resume=resume, progress=progress)


def _run_project(path, action="all", preview=False, pick=None, resume=True, progress=None):
    """Body of run_project, called with the job lock held."""
    path = Path(path).resolve()
    state = read_project(path)
    options = validate_options(state["options"])
    if action not in {"all", "prepare", "render"}:
        raise ValueError("Unknown project action.")
    def stage(name):
        state.update(status="running", stage=name, error=None,
                     progress={"stage": name, "done": 0, "total": 0,
                               "detail": ""})
        save_project(path, state)
        print(f"[{state['id']}] {name}", flush=True)
        if progress:
            progress(name)

    def transcribe_progress(done, total):
        state["progress"] = {"stage": "transcribe", "done": int(done),
                             "total": int(total),
                             "detail": f"chunk {done}/{total}"}
        save_project(path, state)

    try:
        if action in {"all", "prepare"}:
            from picorte.engine import health as _health
            _health.marcar_execucao(path, action)  # W32: o painel mostra só a saúde desta execução
            stage("source")
            source_input = state["source"]
            local = Path(source_input).expanduser()
            is_url = ingest.is_url(source_input)
            if not is_url and not local.is_file():
                raise ValueError(
                    f"Video file does not exist or URL is invalid: {source_input}")
            if not is_url and local.suffix.lower() not in ingest.VIDEO_EXTS:
                raise ValueError(
                    "Use a video file: MP4, MKV, WebM, MOV, M4V or AVI.")
            identity = file_identity(local) if local.is_file() else source_input
            source_key = digest(identity)
            cached_meta = (resume
                           and state["cache"].get("source_meta") == source_key
                           and isinstance(state.get("source_meta"), dict))
            if cached_meta:
                meta = state["source_meta"]
            else:
                meta = ingest.probe_source(source_input)
                meta.pop("formats", None)
                meta = {**meta, "long": ingest.is_long_source(meta)}
                state["source_meta"] = meta
                state["cache"]["source_meta"] = source_key
                save_project(path, state)
            long = bool(meta.get("long", ingest.is_long_source(meta)))

            # Hard Gate P1 Pre-Ingest (D1): nenhuma fonte desconhecida/pausada é baixada.
            from picorte.db.connection import get_default_db
            from picorte.risk_shield.source_resolver import gate_project_source
            state["source_gate"] = gate_project_source(
                get_default_db(), source_input=source_input, meta=meta,
                owner=options.get("source_owner"))
            save_project(path, state)

            source = Path(state.get("video", "__missing__"))
            media_kind = str(meta.get("media_kind") or "")
            render_from_sections = bool(meta.get("render_from_sections", False))
            if (not resume or state["cache"].get("source") != source_key
                    or not source.is_file()):
                if is_url and long:
                    ingest.check_disk(path, None)
                    source, media_kind = ingest.download_discovery(
                        source_input, path, meta)
                    render_from_sections = True
                elif is_url:
                    ingest.check_disk(path, meta.get("estimated_size"))
                    source = dt.resolve_source(source_input, path)
                    media_kind = "video"
                    render_from_sections = False
                else:
                    source = dt.resolve_source(source_input, path)
                    media_kind = "video"
                    render_from_sections = False
                if not media_kind:
                    media_kind = ("audio"
                                  if source.suffix.lower() in ingest.AUDIO_EXTS
                                  else "video")
                state["video"] = str(source)
                state["cache"]["source"] = source_key
                state["cache"]["source_media"] = digest(file_identity(source))
                meta = {**meta, "long": long, "media_kind": media_kind,
                        "render_from_sections": render_from_sections}
                if is_url:
                    meta["discovery"] = str(source)
                state["source_meta"] = meta
                save_project(path, state)
            else:
                if not media_kind:
                    media_kind = ("audio"
                                  if source.suffix.lower() in ingest.AUDIO_EXTS
                                  else "video")
                render_from_sections = bool(
                    render_from_sections and is_url and long)
                meta = {**meta, "long": long, "media_kind": media_kind,
                        "render_from_sections": render_from_sections}
                if is_url:
                    meta["discovery"] = str(source)
                state["source_meta"] = meta

            stage("transcribe")
            transcript_key = digest([
                dt.TRANSCRIPT_VERSION, file_identity(source),
                options["whisper_model"], options["device"], bool(long),
                media_kind, bool(render_from_sections), source_input])
            transcript_path = path / "transcript.json"
            if (not resume or state["cache"].get("transcript") != transcript_key
                    or not transcript_path.exists()):
                duration = meta.get("duration")
                if duration is None:
                    try:
                        duration = ingest.probe_source(
                            str(source)).get("duration")
                    except (OSError, ValueError):
                        duration = None
                media_only = (is_url and long and media_kind == "video"
                              and meta.get("has_audio") is False)
                if media_only and not duration:
                    raise ValueError(
                        "Cannot determine the duration of the silent source.")
                source_identity = file_identity(source)
                if media_only:
                    dt.write_media_transcript(
                        source, path, duration, source=source_input,
                        media_kind=media_kind,
                        render_from_sections=render_from_sections,
                        identity=source_identity)
                else:
                    from picorte.config import resolve_vision_preset
                    vp_trans = resolve_vision_preset(options.get("vision_preset", "auto"))
                    compute_type = (
                        "int8"
                        if options["device"] == "cpu"
                        else vp_trans["models"]["compute_type"]
                    )
                    dt.transcribe(
                        source, path, options["whisper_model"],
                        options["device"],
                        compute_type,
                        duration=duration if long else None,
                        chunked=bool(long), source=source_input,
                        media_kind=media_kind,
                        render_from_sections=render_from_sections,
                        identity=source_identity,
                        progress=transcribe_progress)
                    if (is_url and long and media_kind == "audio"
                            and not read_json(transcript_path).get("words")):
                        visual = ingest.download_visual_discovery(
                            source_input, path)
                        data = read_json(transcript_path)
                        data.update(video=str(visual), media_kind="video")
                        atomic_json(transcript_path, data)
                        source = visual
                        media_kind = "video"
                        source_identity = file_identity(source)
                        state["video"] = str(source)
                        state["source_meta"] = {
                            **state.get("source_meta", {}),
                            "media_kind": "video",
                            "discovery": str(visual)}
                        state["cache"]["source_media"] = digest(source_identity)
                        transcript_key = digest([
                            dt.TRANSCRIPT_VERSION, source_identity,
                            options["whisper_model"], options["device"],
                            bool(long), media_kind,
                            bool(render_from_sections), source_input])
                        print("No speech; switching discovery to the "
                              "low-resolution visual video.", flush=True)
                state["cache"]["transcript"] = transcript_key
                state["source_identity"] = source_identity
                state["progress"] = {"stage": "transcribe", "done": 1,
                                     "total": 1, "detail": "complete"}
                save_project(path, state)
            stage("discover")
            data = read_json(transcript_path)
            discovery_key, selection_key = score_keys(transcript_key, data, options)
            candidates_path = path / "candidates.json"
            selection_path = path / "selection.json"
            segments_path = path / "segments.json"
            if options["search"] or options["semantic"]:
                combined_key = digest([discovery_key, selection_key])
                if (not resume or state["cache"].get("score") != combined_key
                        or not segments_path.exists()):
                    score_clips.run(path, **score_options(options))
                    state["cache"]["score"] = combined_key
                    save_project(path, state)
            else:
                if (not resume or state["cache"].get("discovery") != discovery_key
                        or not candidates_path.exists()):
                    visual_proxy = None
                    if (is_url and long and media_kind == "audio"
                            and options.get("layout") == "games"
                            and meta.get("has_video")):
                        from picorte.engine import health as _health
                        visual_proxy = ingest._find_media(path, "discovery")
                        if visual_proxy is None:
                            try:
                                visual_proxy = ingest.download_visual_discovery(source_input, path)
                                _health.record(path, "visual_proxy", "ok", Path(visual_proxy).name)
                            except Exception as vis_exc:
                                print(f"Visual proxy skipped ({vis_exc})", flush=True)
                                _health.record(path, "visual_proxy", "failed", str(vis_exc))
                    if is_url:
                        # Sismógrafo do Chat (3.1): chat do replay da live (YouTube), opcional e não fatal.
                        from picorte.engine import health as _health
                        ingest.download_live_chat(
                            source_input, path, timeout=ingest.chat_timeout_for(meta.get("duration")),
                            on_status=_health.recorder(path, "chat_download"))
                        # Comentários com timestamp (3.5.4): só YouTube, respeita o status P1 da fonte.
                        from picorte.engine import comments_miner as _comments
                        _comments.save_comment_seeds(
                            source_input, path,
                            permission_status=(state.get("source_gate") or {}).get("permission_status")
                            or "desconhecida",
                            on_status=_health.recorder(path, "comments_download"))
                    score_clips.discover(
                        path, min_len=options["min_len"], max_len=options["max_len"],
                        preferred_len=options["preferred_len"],
                        vision_preset=options.get("vision_preset", "auto"),
                        visual_source=visual_proxy)
                    state["cache"]["discovery"] = discovery_key
                    save_project(path, state)

                stage("select")
                if (not resume or state["cache"].get("selection") != selection_key
                        or not segments_path.exists() or not selection_path.exists()):
                    score_clips.select(
                        path,
                        min_score=options["min_score"] if options["min_score"] is not None else 8.0,
                        max_clips=options["max_clips"],
                        preferred_len=options["preferred_len"],
                        llm=options["llm"],
                        ai_mode=options.get("ai_mode", "heuristic"),
                        ai_filter=options.get("ai_filter", "ollama"),
                        ai_companion=options.get("ai_companion", "claude"),
                        query=options.get("query"),
                        hunt_mode=options.get("hunt_mode", "fast"),
                        keyframes=bool(options.get("keyframes", False)),
                        max_len=options["max_len"],  # 3.6.4: limite do fim estendido até o riso acabar
                        formatos_extras=options.get("formatos_extras", True))  # 3.7.3
                    state["cache"]["selection"] = selection_key
                    save_project(path, state)

            state["selection"] = read_json(selection_path)
        if action == "prepare":
            state.update(status="review", stage="ready for review")
        else:
            stage("render preview" if preview else "render")
            data = read_json(path / "transcript.json")
            source = Path(data["video"]).resolve()
            section_source = str(data.get("source") or state["source"])
            if state.get("source_identity") and state["source_identity"] != file_identity(source):
                raise ValueError("Source video changed since transcription. Find clips again before rendering.")
            segments = validate_segments(read_json(path / "segments.json"), data["duration"])
            if not segments:
                stats = state.get("selection") or {}
                low = stats.get("score_min")
                high = stats.get("score_max")
                score = stats.get("min_score", options["min_score"] or 8.0)
                range_text = (f"Candidate scores {low:.1f}-{high:.1f}. "
                              if low is not None else "No candidates were found. ")
                raise ValueError(f"{range_text}No clips reached {score:.1f}. "
                                 f"Lower the minimum score or run this project with "
                                 f"--action prepare to review the range.")
            # Assign stable IDs before subset selection so names do not shift.
            segments = [{**s, "id": f"{i:03}"} for i, s in enumerate(segments, 1)]
            try:
                from picorte.engine.retention_engine import pair_short_and_long_clips
                segments = pair_short_and_long_clips(link_format_family(segments))
            except Exception:
                pass
            todos_segmentos = segments  # W36: a família do pHash vale para o VOD inteiro, não só o pick
            segments = score_clips.pick_segments(segments, pick)
            out = path / ("previews" if preview else "clips")
            out.mkdir(exist_ok=True)
            brand = branding.load_brand(options["brand"]) if options["brand"] else None
            logo_identity = file_identity(brand["logo"]) if brand and brand["logo"] else None
            render_from_sections = bool(
                (state.get("source_meta") or {}).get("render_from_sections")
                or data.get("render_from_sections"))
            cached_full = (sections.find_full_source(path)
                           if render_from_sections else None)
            if cached_full is not None:
                print(f"Using cached full source: {cached_full.name}", flush=True)
                render_from_sections = False
                source = cached_full
            section_plan = {}
            if render_from_sections:
                groups = sections.plan_sections(
                    segments, data.get("duration") or 0)
                for group_index, group in enumerate(groups, 1):
                    for clip_index in group["clips"]:
                        section_plan[clip_index] = (group_index, group)
                W, H = None, None
            else:
                W, H = render_clips.ffprobe_dims(source)
            loaded_sections = {}
            failed_sections = {}
            render_errors = []
            state["render_errors"] = render_errors
            outputs = []
            for i, segment in enumerate(segments, 1):
                stage(f"{'preview' if preview else 'render'} {i}/{len(segments)}")
                render_source = source
                source_offset = 0.0
                section_key = None
                group_index = None
                if render_from_sections:
                    group_index, group = section_plan[i - 1]
                    source_offset = float(group["start"])
                    section_key = digest([
                        section_source, group["start"], group["end"],
                        sections.SECTION_VERSION])
                key = digest([segment, data["words"], file_identity(source),
                              options, brand, logo_identity, preview,
                              source_offset, section_key])
                cached = state["renders"].get(key)
                expected_suffixes = [".mp4", ".srt"] if preview else [".mp4", ".srt", ".png", ".meta.json"]
                if resume and cached and all(Path(cached).with_suffix(ext).is_file() for ext in expected_suffixes):
                    outputs.append(cached)
                    continue
                if render_from_sections:
                    if group_index in failed_sections:
                        render_errors.append(
                            {"clip": segment["id"],
                             "error": failed_sections[group_index]})
                        continue
                    loaded = loaded_sections.get(group_index)
                    if loaded is None:
                        try:
                            render_source = sections.ensure_section(
                                section_source, path, group_index,
                                group["start"], group["end"])
                            W, H = render_clips.ffprobe_dims(render_source)
                            loaded_sections[group_index] = (
                                render_source, W, H)
                        except ingest.SectionDownloadTimeout as exc:
                            print(f"Section download stalled: {exc}", flush=True)
                            print("Downloading the full source once and "
                                  "rendering from it instead.", flush=True)
                            source = sections.ensure_full_source(
                                section_source, path)
                            render_from_sections = False
                            source_offset = 0.0
                            section_key = None
                            W, H = render_clips.ffprobe_dims(source)
                            render_source = source
                            key = digest([
                                segment, data["words"],
                                file_identity(source), options, brand,
                                logo_identity, preview, source_offset,
                                section_key])
                        except (Exception, SystemExit) as exc:
                            failed_sections[group_index] = str(exc)
                            render_errors.append(
                                {"clip": segment["id"], "error": str(exc)})
                            save_project(path, state)
                            continue
                    else:
                        render_source, W, H = loaded
                try:
                    enriched_seg = {**segment, "id": segment["id"] + "-" + key[:8]}
                    # 3.7.3: cada formato no seu aspecto (o Longo sai 16:9, layout simples, sem Cold Open)
                    seg_aspect, seg_layout, co_max_len = render_params_for(segment, options)
                    try:
                        # 3.7.1: Cold Open só com clímax MEDIDO (pico de chat ou punchline), respeitando max_len
                        from picorte.engine.retention_engine import cold_open_for_segment
                        if co_max_len is None:
                            plan = {"enabled": False, "motivo": f"formato {segment.get('formato')} sem Cold Open"}
                        else:
                            plan = cold_open_for_segment(
                                segment, data["words"], _chat_peaks(path), max_len=co_max_len)
                        if plan.get("novo_inicio") is not None:
                            enriched_seg["start"] = plan["novo_inicio"]
                        enriched_seg["cold_open"] = plan
                    except Exception as exc:
                        enriched_seg["cold_open"] = {"enabled": False,
                                                     "motivo": f"erro no plano: {type(exc).__name__}: {exc}"}
                    try:
                        # 3.7.5: freeze + seta no momento-chave medido, no tempo que sobra depois do Cold Open
                        from picorte.engine.edit_effects import freeze_for_segment
                        co = enriched_seg.get("cold_open") or {}
                        used = (float(co.get("teaser_duration") or 0.0) - 0.25) if co.get("enabled") else 0.0
                        enriched_seg["freeze"] = (
                            {"enabled": False, "motivo": f"formato {segment.get('formato')} sem freeze"}
                            if co_max_len is None else
                            freeze_for_segment(enriched_seg, data["words"], _chat_peaks(path),
                                               max_len=co_max_len, used_s=max(0.0, used)))
                    except Exception as exc:
                        enriched_seg["freeze"] = {"enabled": False,
                                                  "motivo": f"erro no plano: {type(exc).__name__}: {exc}"}
                    render_kwargs = dict(
                        style=options["style"], do_tighten=options["tighten"], loudnorm=options["loudnorm"],
                        preview=preview, brand=brand, layout=seg_layout, centers=options["centers"],
                        caption=options["caption"], source_offset=source_offset,
                        vision_preset=options.get("vision_preset", "auto"),
                        dominant_language=data.get("language"))
                    if segment.get("formato") in ("arco_2_atos", "compilacao"):
                        # 3.7.4: cada trecho pelo render normal (P1 por trecho) e emenda com ponte
                        from picorte.engine.composites import render_composite
                        comp = render_composite(
                            enriched_seg, out_dir=out, render_fn=render_clips.render,
                            render_args=(data["words"], render_source, W, H, path, seg_aspect),
                            render_kwargs=render_kwargs, meta_fn=render_clips.write_meta)
                        if comp["output"] is None:
                            raise ValueError(f"composto {segment.get('formato')} não renderizado: {comp['motivo']}")
                        output = comp["output"]
                    else:
                        output = render_clips.render(enriched_seg, data["words"], render_source, W, H, path,
                                                     seg_aspect, out_dir=out, **render_kwargs)
                    try:
                        import shutil as _shutil
                        from picorte.engine.publish_kit import resolve_streamer
                        from picorte.engine.thumbnail_factory import generate_thumbnail

                        thumb_out = Path(output).with_name(Path(output).stem + "_thumb.png")
                        clip_dur = max(0.5, float(segment["end"]) - float(segment["start"]))
                        clip_local_start = max(0.0, float(segment["start"]) - source_offset)
                        clip_local_end = clip_local_start + clip_dur
                        thumb_ts = clip_local_start + clip_dur * 0.4
                        thumb_src = render_source if (W and H and W >= H) else Path(output)
                        sm_proj = state.get("source_meta") or {}
                        streamer_info = resolve_streamer(
                            channel_name=sm_proj.get("channel") or sm_proj.get("uploader"),
                            title=f"{sm_proj.get('title') or ''} {enriched_seg.get('proposed_title') or ''}",
                            source_url=state.get("source"),
                        )
                        thumb_res = generate_thumbnail(
                            thumb_src,
                            thumb_out,
                            title_text=(
                                enriched_seg.get("thumbnail_words")
                                or enriched_seg.get("proposed_title")
                                or enriched_seg.get("hook")
                                or "DESTAQUE"
                            ),
                            timestamp_s=thumb_ts if thumb_src == render_source else clip_dur * 0.4,
                            clip_start_s=clip_local_start if thumb_src == render_source else 0.0,
                            clip_end_s=clip_local_end if thumb_src == render_source else clip_dur,
                            aspect=seg_aspect,
                            vision_preset=options.get("vision_preset", "auto"),
                            facecam_box=enriched_seg.get("_detected_facecam_box"),
                            streamer_name=streamer_info.get("display_name") or None,
                            streamer_accent_hex=streamer_info.get("accent_hex") or "#E11D2E",
                        )
                        if not preview:
                            enriched_seg["thumbnail_1280x720"] = thumb_res["path"]
                            # Substitui o poster cru (<clip>.png com legenda) pela capa oficial única
                            poster_png = Path(output).with_suffix(".png")
                            if Path(thumb_res["path"]).is_file() and Path(thumb_res["path"]).suffix.lower() == ".png":
                                try:
                                    _shutil.copy2(thumb_res["path"], poster_png)
                                except OSError:
                                    pass
                            render_clips.write_meta(enriched_seg, Path(output), source_meta=sm_proj)
                    except Exception as thumb_exc:
                        print(f"Thumbnail warning: {thumb_exc}", flush=True)
                        from picorte.engine import health as _health
                        _health.record(path, "thumbnail", "failed",
                                       f"{Path(output).stem}: {type(thumb_exc).__name__}: {thumb_exc}")
                    if not preview:
                        # Thumbnail pode falhar (inclusive pelo Selo Verde): o .meta.json com crédito à fonte
                        # é gravado mesmo assim, e todo corte final recebe o veredito P1 (RiskShield).
                        if not enriched_seg.get("thumbnail_1280x720"):
                            render_clips.write_meta(enriched_seg, Path(output),
                                                    source_meta=state.get("source_meta") or {})
                        from picorte.db.connection import get_default_db
                        from picorte.risk_shield.pipeline import (attach_risk_verdict, clean_music_in_render,
                                                                  family_clip_ids)
                        music_result = clean_music_in_render(output, cache_dir=path / "stems_cache")
                        attach_risk_verdict(
                            get_default_db(),
                            meta_path=Path(output).with_suffix(".meta.json"),
                            source_id=(state.get("source_gate") or {}).get("source_id"),
                            seg=enriched_seg,
                            words=data["words"],
                            mp4_path=output,
                            options={**options, "aspect": seg_aspect, "layout": seg_layout},
                            game_slug=str((state.get("source_meta") or {}).get("detected_game") or ""),
                            music_result=music_result,
                            clip_id=f"studio-{state['id']}:{segment['id']}",
                            family_clip_ids=family_clip_ids(state['id'], segment, todos_segmentos),
                        )
                except (Exception, SystemExit) as exc:
                    if not render_from_sections:
                        raise
                    render_errors.append(
                        {"clip": segment["id"], "error": str(exc)})
                    save_project(path, state)
                    continue
                state["renders"][key] = str(output)
                outputs.append(str(output))
                save_project(path, state)
            state["last_outputs"] = outputs
            if render_errors:
                message = f"{len(render_errors)} clip(s) failed to render."
                if not outputs:
                    raise ValueError(message + " Sections stay cached for retry.")
                state.update(status="failed", stage="render incomplete",
                             error=message + " Successful clips were kept.")
                save_project(path, state)
                return state
            if render_from_sections and not preview:
                sections.cleanup_sections(path)
            state.update(status="review" if preview else "complete", stage="preview ready" if preview else "complete")
        save_project(path, state)
        try:
            from picorte.services.reconciliacao import sincronizar_pasta
            from picorte.services.studio_service import StudioService
            sincronizar_pasta(StudioService(), path, state)
        except Exception as db_exc:  # o banco não derruba o job, mas a falha fica visível na Saúde
            from picorte.engine import health as _health
            _health.record(path, "banco", "failed", f"{type(db_exc).__name__}: {db_exc}")
        return state
    except (Exception, SystemExit) as exc:
        state.update(status="failed", error=str(exc), stage=state.get("stage", "failed"))
        save_project(path, state)
        raise


def run_batch(sources, root, options, runner=None, **kwargs):
    if not isinstance(sources, list) or not sources or any(not isinstance(s, str) for s in sources):
        raise ValueError("Batch input must be a non-empty JSON list of video paths or URLs.")
    results = []
    for source in sources:
        state = create_project(root, source, options)
        path = project_path(root, state["id"])
        try:
            result = (runner or run_project)(path, **kwargs)
            results.append({"id": state["id"], "source": source, "status": result["status"]})
        except (Exception, SystemExit) as exc:
            results.append({"id": state["id"], "source": source, "status": "failed", "error": str(exc)})
    return results
