"""Probe sources and download only the media a long job needs.

Local files are never copied. Long URL sources download audio for discovery
(or a low-resolution video when there is no audio) and later download only the
selected video sections. Everything uses yt-dlp/ffprobe locally.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from picorte.config import ytdlp_base_cmd

LONG_SECONDS = 2 * 60 * 60
LONG_BYTES = 8 * 1024**3
AUDIO_EXTS = {".m4a", ".mp3", ".opus", ".ogg", ".wav", ".aac", ".flac", ".webm"}
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi"}
MIN_FREE_BYTES = 500 * 1024**2
SECTION_TIMEOUT = 180
FULL_TIMEOUT = 60 * 60


class SectionDownloadTimeout(RuntimeError):
    """A ranged section download produced no usable file before timing out."""


def is_url(source):
    return urlparse(str(source)).scheme in {"http", "https"}


def _kill_tree(proc):
    """Stop a downloader and any ffmpeg child it started."""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, text=True, check=False)
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass


def _run(cmd, timeout=None, **kwargs):
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("check", True)
    if timeout is None:
        return subprocess.run(cmd, **kwargs)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(
            cmd, timeout, output=stdout, stderr=stderr)
    if kwargs.get("check", True) and proc.returncode:
        raise subprocess.CalledProcessError(
            proc.returncode, cmd, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def _format_size(fmt, duration):
    if not isinstance(fmt, dict):
        return 0
    for key in ("filesize", "filesize_approx"):
        try:
            value = int(fmt.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    try:
        rate = float(fmt.get("tbr") or 0)
    except (TypeError, ValueError):
        rate = 0.0
    if rate > 0 and duration:
        return int(rate * 1000 / 8 * float(duration))
    return 0


def _default_bitrate(height):
    if not height:
        return 4_000_000
    if height >= 1080:
        return 8_000_000
    if height >= 720:
        return 5_000_000
    if height >= 480:
        return 2_500_000
    return 1_500_000


def _normalize_chapters(raw_chapters):
    out = []
    for item in raw_chapters or []:
        if not isinstance(item, dict):
            continue
        try:
            start = float(item.get("start_time"))
            end = float(item.get("end_time"))
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        out.append({
            "title": str(item.get("title") or "").strip(),
            "start_time": round(start, 2),
            "end_time": round(end, 2),
        })
    return out


def _normalize_heatmap(raw_heatmap):
    out = []
    for item in raw_heatmap or []:
        if not isinstance(item, dict):
            continue
        try:
            start = float(item.get("start_time"))
            end = float(item.get("end_time"))
            value = float(item.get("value"))
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        out.append({
            "start_time": round(start, 2),
            "end_time": round(end, 2),
            "value": round(max(0.0, min(1.0, value)), 4),
        })
    return out


def _safe_detect_game_slug(title, chapters=None):
    try:
        from picorte.ai.game_dossiers.loader import detect_game_slug
        return detect_game_slug(title, chapters=chapters)
    except Exception:
        return None


def extract_heatmap_peaks(heatmap, *, min_value=0.65, min_gap_sec=30.0):
    """Retorna máximos locais do heatmap Most Replayed espaçados por min_gap_sec."""
    bins = _normalize_heatmap(heatmap)
    if not bins:
        return []
    candidates = []
    n = len(bins)
    for idx, item in enumerate(bins):
        val = item["value"]
        if val < float(min_value):
            continue
        left_val = bins[idx - 1]["value"] if idx > 0 else -1.0
        right_val = bins[idx + 1]["value"] if idx + 1 < n else -1.0
        if val >= left_val and val >= right_val:
            center = round((item["start_time"] + item["end_time"]) / 2.0, 2)
            candidates.append({
                "start": item["start_time"],
                "end": item["end_time"],
                "center": center,
                "value": val,
            })
    candidates.sort(key=lambda item: (-item["value"], item["start"]))
    kept = []
    for cand in candidates:
        if all(abs(cand["center"] - prev["center"]) >= float(min_gap_sec) for prev in kept):
            kept.append(cand)
    return kept


def _probe_local(path, run=None):
    run = run or _run
    path = Path(path).expanduser().resolve()
    result = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size:stream=codec_type,width,height",
        "-of", "json", str(path)])
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"ffprobe returned invalid JSON for {path}") from exc
    streams = data.get("streams") or []
    video = next(
        (item for item in streams if item.get("codec_type") == "video"), {})
    size = int((data.get("format") or {}).get("size") or path.stat().st_size)
    duration = (data.get("format") or {}).get("duration")
    return {
        "source": str(path),
        "url": False,
        "title": path.name,
        "channel": None,
        "duration": float(duration) if duration is not None else None,
        "size": size,
        "estimated_size": size,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "has_audio": any(item.get("codec_type") == "audio" for item in streams),
        "has_video": bool(video),
        "chapters": [],
        "heatmap": [],
        "detected_game": _safe_detect_game_slug(path.stem),
    }


def _probe_url(url, run=None):
    run = run or _run
    fallback = {
        "source": url, "url": True, "title": url, "channel": None, "duration": None,
        "size": None, "estimated_size": None, "width": 0, "height": 0,
        "has_audio": None, "has_video": None, "formats": [],
        "chapters": [], "heatmap": [], "detected_game": None,
    }
    try:
        result = run([
            *ytdlp_base_cmd(), "--dump-single-json",
            "--skip-download", "--no-playlist", url])
        data = json.loads(result.stdout or "{}")
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return fallback

    duration = data.get("duration")
    try:
        duration = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration = None
    formats = [item for item in (data.get("formats") or [])
               if isinstance(item, dict)]
    videos = [item for item in formats
              if item.get("vcodec") not in (None, "none")]
    audios = [item for item in formats
              if item.get("acodec") not in (None, "none")]
    video = max(
        videos,
        key=lambda item: (int(item.get("height") or 0),
                          float(item.get("tbr") or 0)),
        default=None)
    audio = max(
        audios,
        key=lambda item: float(item.get("tbr") or 0),
        default=None)
    estimated = 0
    if video is not None:
        estimated += _format_size(video, duration)
        if not estimated and duration:
            estimated = int(_default_bitrate(
                int(video.get("height") or 0)) * duration / 8)
        if audio is not None:
            estimated += _format_size(audio, duration)
    elif audio is not None:
        estimated = _format_size(audio, duration)
    elif duration:
        estimated = int(_default_bitrate(0) * duration / 8)

    title = str(data.get("title") or url)
    channel = data.get("channel") or data.get("uploader") or None
    channel = str(channel).strip() if channel else None
    channel_url = data.get("channel_url") or data.get("uploader_url") or None
    chapters = _normalize_chapters(data.get("chapters"))
    heatmap = _normalize_heatmap(data.get("heatmap"))

    return {
        "source": url,
        "url": True,
        "title": title,
        "channel": channel,
        "channel_url": channel_url,
        "duration": duration,
        "size": None,
        "estimated_size": estimated or None,
        "width": int((video or {}).get("width") or 0),
        "height": int((video or {}).get("height") or 0),
        "has_audio": any(
            item.get("acodec") not in (None, "none") for item in formats),
        "has_video": bool(videos),
        "formats": formats,
        "chapters": chapters,
        "heatmap": heatmap,
        "detected_game": _safe_detect_game_slug(title, chapters=chapters),
    }


def probe_source(source, runner=None):
    """Return local or yt-dlp metadata; URL failures become an unknown source."""
    source = str(source)
    run = runner or _run
    if is_url(source):
        return _probe_url(source, run)
    path = Path(source).expanduser()
    if not path.is_file():
        raise ValueError(f"Video file does not exist or URL is invalid: {source}")
    return _probe_local(path, run)


def is_long_source(meta, seconds=LONG_SECONDS, size_bytes=LONG_BYTES):
    """Duration, estimated full download, or unknown duration selects long."""
    duration = (meta or {}).get("duration")
    if duration is None:
        return True
    try:
        if float(duration) >= float(seconds):
            return True
    except (TypeError, ValueError):
        return True
    size = (meta or {}).get("estimated_size")
    try:
        return size is not None and float(size) >= float(size_bytes)
    except (TypeError, ValueError):
        return True


def _find_media(workdir, prefix):
    workdir = Path(workdir)
    for path in sorted(workdir.glob(prefix + ".*")):
        if path.suffix.lower() in AUDIO_EXTS | VIDEO_EXTS and path.is_file():
            return path.resolve()
    return None


def _remove_old(workdir, prefix):
    for path in Path(workdir).glob(prefix + ".*"):
        if path.suffix.lower() in AUDIO_EXTS | VIDEO_EXTS:
            try:
                path.unlink()
            except OSError:
                pass


def download_visual_discovery(url, workdir, runner=None):
    """Download the lowest-resolution video for speechless visual discovery."""
    run = runner or _run
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    _remove_old(workdir, "discovery")
    try:
        run([
            *ytdlp_base_cmd(),
            # YouTube atual entrega vídeo e áudio separados: "worst" (combinado) costuma não existir.
            # A visão de games só precisa da faixa de vídeo em baixa resolução.
            "-f", "worstvideo[height>=240][height<=360]/worstvideo[height<=480]/worst[height<=360]/worst",
            "--no-playlist",
            "-o", str(workdir / "discovery.%(ext)s"), url])
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            "Download failed: no video file produced.") from exc
    video = _find_media(workdir, "discovery")
    if video is None:
        raise RuntimeError("Download failed: no video file produced.")
    return video


def download_discovery(url, workdir, meta=None, runner=None):
    """Download best audio, or a low-resolution video for silent URLs."""
    run = runner or _run
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    meta = meta or probe_source(url, runner=run)
    _remove_old(workdir, "audio")
    _remove_old(workdir, "discovery")

    if meta.get("has_audio") is not False:
        try:
            run([
                *ytdlp_base_cmd(), "-f", "bestaudio/best",
                "--no-playlist", "-o", str(workdir / "audio.%(ext)s"), url])
        except (OSError, subprocess.SubprocessError):
            pass
        audio = _find_media(workdir, "audio")
        if audio is not None:
            return audio, "audio"

    return download_visual_discovery(url, workdir, runner=run), "video"


def _download(url, out_path, fmt, runner=None, timeout=None, extra=()):
    """Run one yt-dlp download, converting a timeout into a clear error."""
    run = runner or _run
    cmd = [*ytdlp_base_cmd(), "-f", fmt,
           "--merge-output-format", "mp4", "--no-playlist",
           "--force-overwrites", *extra, "-o", str(out_path), url]
    try:
        if runner is None:
            run(cmd, timeout=timeout)
        else:
            run(cmd)
    except subprocess.TimeoutExpired as exc:
        raise SectionDownloadTimeout(
            f"Downloader stalled for {timeout} seconds.") from exc
    if not out_path.is_file() or out_path.stat().st_size <= 0:
        raise RuntimeError(f"Download produced no file: {out_path.name}")
    return out_path


def download_section(url, start, end, out_path, quality=1080, runner=None,
                     timeout=SECTION_TIMEOUT):
    """Download one accurate video section with a bounded wait."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for stale in (out_path, out_path.with_suffix(out_path.suffix + ".part")):
        try:
            stale.unlink()
        except OSError:
            pass
    if quality:
        fmt = (f"bestvideo[height<={int(quality)}]+bestaudio/"
               f"best[height<={int(quality)}]")
    else:
        fmt = "worst"
    try:
        return _download(
            url, out_path, fmt, runner=runner, timeout=timeout,
            extra=("--download-sections",
                   f"*{float(start):.3f}-{float(end):.3f}",
                   "--force-keyframes-at-cuts"))
    except SectionDownloadTimeout as exc:
        for stale in (out_path, out_path.with_suffix(out_path.suffix + ".part")):
            try:
                stale.unlink()
            except OSError:
                pass
        raise SectionDownloadTimeout(
            f"Section download stalled for {float(start):.0f}-"
            f"{float(end):.0f}s. The source may not support ranged "
            "downloads.") from exc


def download_full(url, out_path, quality=1080, runner=None,
                  timeout=FULL_TIMEOUT):
    """Download a complete source for sources where ranged cuts stall."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for stale in (out_path, out_path.with_suffix(out_path.suffix + ".part")):
        try:
            stale.unlink()
        except OSError:
            pass
    if quality:
        q = int(quality)
        fmt = (f"bestvideo[height<={q}][protocol=https][vcodec^=avc1]+"
               f"bestaudio[protocol=https][ext=m4a]/"
               f"bestvideo[height<={q}][protocol=https]+"
               f"bestaudio[protocol=https]/best[height<={q}]")
    else:
        fmt = "worst"
    return _download(url, out_path, fmt, runner=runner, timeout=timeout)


def check_disk(path, required_bytes):
    """Warn below 1.5x the estimate; stop only under 500 MB free."""
    free = shutil.disk_usage(str(path)).free
    if free < MIN_FREE_BYTES:
        raise ValueError(
            f"Not enough free disk space: {free / 1024**2:.0f} MB free.")
    if required_bytes and free < 1.5 * float(required_bytes):
        print(f"Disk warning: {free / 1024**3:.1f} GB free, "
              f"estimated job size {float(required_bytes) / 1024**3:.1f} GB.",
              flush=True)


CHAT_TIMEOUT = 20 * 60
# Medido em 2026-11-20 (VOD real de 11h20 do Gameplayrj): 45s de download = 38 min de chat (~50x tempo real).
CHAT_SPEED_FACTOR = 40.0


def chat_timeout_for(duration_s):
    """Limite do download de chat proporcional à duração do VOD (margem sobre ~50x o tempo real)."""
    try:
        dur = float(duration_s or 0.0)
    except (TypeError, ValueError):
        dur = 0.0
    return max(CHAT_TIMEOUT, int(dur / CHAT_SPEED_FACTOR) + 5 * 60)
_YOUTUBE_HOSTS = ("youtube.com", "youtu.be")


def _chat_runs_text(runs):
    parts = []
    for run in runs or []:
        if "text" in run:
            parts.append(str(run["text"]))
            continue
        emoji = run.get("emoji") or {}
        eid = str(emoji.get("emojiId") or "")
        # Emoji Unicode vem no emojiId; emoji de canal (custom) só tem o atalho legível (ex.: ":_alanKEKW:").
        if eid and not emoji.get("isCustomEmoji") and "/" not in eid and len(eid) <= 8:
            parts.append(eid)
        elif emoji.get("shortcuts"):
            parts.append(str(emoji["shortcuts"][0]))
    return "".join(parts).strip()


def parse_youtube_live_chat(path):
    """Converte o .live_chat.json (NDJSON aninhado do yt-dlp) em [{'t': s, 'text': str}] ordenado."""
    messages = []
    # Linha a linha: o bruto de uma live de 11h passa de 300 MB (nunca carregar inteiro na memória).
    with open(path, encoding="utf-8", errors="replace") as fh:
        rows = (line for line in fh if line.strip())
        for line in rows:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            messages.extend(_live_chat_row_messages(row))
    messages.sort(key=lambda m: m["t"])
    return messages


def _live_chat_row_messages(row):
    out = []
    replay = row.get("replayChatItemAction") or {}
    try:
        t = float(replay.get("videoOffsetTimeMsec")) / 1000.0
    except (TypeError, ValueError):
        return out
    for action in replay.get("actions") or []:
        item = (action.get("addChatItemAction") or {}).get("item") or {}
        renderer = item.get("liveChatTextMessageRenderer") or item.get("liveChatPaidMessageRenderer")
        if not renderer:
            continue
        text = _chat_runs_text((renderer.get("message") or {}).get("runs"))
        if text:
            out.append({"t": round(t, 3), "text": text})
    return out


def download_live_chat(url, workdir, runner=None, timeout=CHAT_TIMEOUT, on_status=None):
    """Baixa o chat do replay de live do YouTube (só metadados, nenhum vídeo) para <workdir>/chat.json.

    Opcional e nunca fatal: fonte que não é YouTube, VOD sem chat ou falha do yt-dlp retornam None.
    Deve ser chamado só DEPOIS do portão P1 Pre-Ingest.
    """
    report = on_status or (lambda status, detail="": None)
    workdir = Path(workdir)
    out = workdir / "chat.json"
    if out.is_file():
        report("ok", "chat em cache")
        return out
    host = (urlparse(str(url)).netloc or "").lower()
    if not any(h in host for h in _YOUTUBE_HOSTS):
        report("na", "fonte não é YouTube")
        return None
    run = runner or _run
    template = workdir / "chatsrc.%(ext)s"
    cmd = [*ytdlp_base_cmd(), "--skip-download", "--write-subs", "--sub-langs", "live_chat",
           "--no-playlist", "-o", str(template), str(url)]
    partial = False
    raw = workdir / "chatsrc.live_chat.json"
    try:
        run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        # Estourou o tempo: aproveita o que já foi baixado (o yt-dlp grava o chat aos poucos em .part).
        part = workdir / "chatsrc.live_chat.json.part"
        if part.is_file():
            part.replace(raw)
            partial = True
        else:
            report("failed", f"tempo esgotado ({int(timeout)}s) sem nenhum chat baixado")
            return None
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"Chat da live indisponível ({type(exc).__name__}); seguindo sem Sismógrafo.", flush=True)
        report("failed", f"{type(exc).__name__}: {exc}")
        return None
    if not raw.is_file():
        report("na", "vídeo sem chat salvo (upload comum ou replay sem chat)")
        return None
    try:
        messages = parse_youtube_live_chat(raw)
    finally:
        for leftover in workdir.glob("chatsrc*"):
            leftover.unlink(missing_ok=True)
    if not messages:
        report("na", "chat vazio")
        return None
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(messages, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out)
    if partial:
        report("ok", f"parcial: {len(messages)} mensagens até {messages[-1]['t'] / 60:.0f} min (tempo esgotado)")
    else:
        report("ok", f"{len(messages)} mensagens")
    return out
