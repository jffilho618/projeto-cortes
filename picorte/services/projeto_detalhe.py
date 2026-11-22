"""Detalhe de um projeto para o painel (movido do dashboard.py; só leitura)."""
from pathlib import Path

import projects


def detalhe_projeto(root, project_id):
    """Build the JSON payload for one project, including selection.json."""
    path = projects.project_path(root, project_id)
    state = projects.read_project(path)
    data = {"project": state, "busy": False, "candidates": [],
            "transcript": None, "selection": {}, "files": [], "log": ""}
    for filename, key in [("segments.json", "candidates"),
                          ("transcript.json", "transcript"),
                          ("selection.json", "selection")]:
        if (path / filename).exists():
            data[key] = projects.read_json(path / filename)
    for directory in ("previews", "clips"):
        for file in sorted((path / directory).glob("*")):
            if file.suffix in {".mp4", ".srt", ".png", ".json"}:
                data["files"].append({"name": file.name, "kind": directory,
                                      "url": f"/media/{project_id}/{directory}/{file.name}"})
    publish_kits = {}
    risk_verdicts = {}
    clips_dir = path / "clips"
    if clips_dir.is_dir():
        try:
            from picorte.engine.publish_kit import build_publish_kit
            sm_proj = state.get("source_meta") or {}
            for mp4 in sorted(clips_dir.glob("*.mp4")):
                stem = mp4.stem
                meta_file = clips_dir / f"{stem}.meta.json"
                meta = projects.read_json(meta_file) if meta_file.is_file() else {"hook": stem}
                risk_verdicts[stem] = meta.get("risk_verdict") or (
                    {"overall_status": meta["risk_status"]} if meta.get("risk_status") else None)
                kit = meta.get("publish_kit")
                if not isinstance(kit, dict) or "platforms" not in kit:
                    thumb_f = clips_dir / f"{stem}_thumb.png"
                    kit = build_publish_kit(
                        meta,
                        source_meta=sm_proj,
                        mp4_path=mp4,
                        thumb_path=thumb_f if thumb_f.is_file() else "",
                    )
                publish_kits[stem] = kit
        except Exception:
            pass
    data["publish_kits"] = publish_kits
    data["risk_verdicts"] = risk_verdicts
    try:
        from picorte.services.studio_service import StudioService
        data["publications"] = StudioService().list_project_publications(project_id)
    except Exception:
        data["publications"] = {}
    try:
        from picorte.services.studio_service import StudioService
        data["cooldowns"] = StudioService().risk_cooldown_status()
    except Exception:
        data["cooldowns"] = {}
    if (path / "job.log").exists():
        with (path / "job.log").open("rb") as log:
            log.seek(max(0, (path / "job.log").stat().st_size - 12000))
            data["log"] = log.read().decode("utf-8", errors="replace")
    transcript = data.get("transcript") or {}
    source_meta = state.get("source_meta") or {}
    render_from_sections = bool(
        source_meta.get("render_from_sections")
        or transcript.get("render_from_sections"))
    video = transcript.get("video") or state.get("video")
    data.update({
        "source_meta": source_meta,
        "progress": state.get("progress") or {},
        "render_errors": state.get("render_errors") or [],
        "playable_source": bool(
            not render_from_sections and video
            and Path(video).is_file()),
    })
    return data
