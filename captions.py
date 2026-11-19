"""Validate editable transcripts and export clip-relative SubRip captions."""
import copy
import math
from pathlib import Path

from score_clips import sentenceize


def update_transcript(data, words):
    if not isinstance(words, list) or not words:
        raise ValueError("Provide at least one timed word.")
    duration = float(data["duration"])
    clean = []
    previous = 0.0
    for item in words:
        text = str(item.get("word", "")).strip()
        start, end = float(item["start"]), float(item["end"])
        if (not text or len(text) > 500 or "\n" in text or "\r" in text
                or not math.isfinite(start) or not math.isfinite(end)
                or start < previous - 0.001 or end <= start or end > duration + 0.001):
            raise ValueError("Words must have text and ordered, non-overlapping times within the video.")
        entry = {"word": text, "start": start, "end": end}
        for flag in ("hidden", "emphasis"):
            if flag in item:
                if not isinstance(item[flag], bool):
                    raise ValueError("Word flags must be true or false.")
                if item[flag]:
                    entry[flag] = True
        clean.append(entry)
        previous = end
    result = copy.deepcopy(data)
    result["words"] = clean
    result["segments"] = [{k: s[k] for k in ("start", "end", "text")}
                          for s in sentenceize(clean)]
    return result


def srt_time(seconds):
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


def write_srt(words, start, end, path, group_size=8, silence_gap=0.70):
    if isinstance(group_size, bool) or not isinstance(group_size, int) or not 1 <= group_size <= 100:
        raise ValueError("Caption group size must be an integer from 1 to 100.")
    selected = [w for w in words
                if not w.get("hidden") and w["end"] > start and w["start"] < end]
    groups = []
    cur = []
    for w in selected:
        if cur and (
            len(cur) >= group_size
            or (float(w["start"]) - float(cur[-1]["end"])) >= silence_gap
        ):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)

    blocks = []
    for group in groups:
        a = max(start, float(group[0]["start"])) - start
        raw_end = min(end, float(group[-1]["end"])) - start
        b = max(a + 0.12, raw_end)
        text = " ".join(w["word"].strip() for w in group)
        blocks.append(f"{len(blocks) + 1}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n")
    Path(path).write_text("\n".join(blocks), encoding="utf-8")
    return Path(path)
