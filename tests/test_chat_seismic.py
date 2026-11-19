from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


def test_parse_chat_log_twitch_and_youtube_formats(tmp_path):
    from picorte.engine.chat_seismic import parse_chat_log

    twitch_path = tmp_path / "twitch.json"
    twitch_path.write_text(
        json.dumps(
            {
                "comments": [
                    {"content_offset_seconds": 12.4, "message": {"body": "salve chat"}},
                    {"content_offset_seconds": 65.0, "message": {"body": "KKKKKKKK MENTIRA"}},
                ]
            }
        ),
        encoding="utf-8",
    )
    msgs_tw = parse_chat_log(twitch_path)
    assert len(msgs_tw) == 2
    assert msgs_tw[0]["t"] == pytest.approx(12.4)
    assert msgs_tw[1]["text"] == "KKKKKKKK MENTIRA"

    yt_path = tmp_path / "youtube_ndjson.jsonl"
    yt_path.write_text(
        "\n".join(
            [
                json.dumps({"videoOffsetTimeMsec": 5500, "text": "opa"}),
                json.dumps({"offset_seconds": 61.2, "body": "LUL CLIP ISSO ???"}),
            ]
        ),
        encoding="utf-8",
    )
    msgs_yt = parse_chat_log(yt_path)
    assert len(msgs_yt) == 2
    assert msgs_yt[0]["t"] == pytest.approx(5.5)
    assert msgs_yt[1]["t"] == pytest.approx(61.2)


def test_analyze_chat_seismic_detects_peaks_and_emote_bursts():
    from picorte.engine.chat_seismic import analyze_chat_seismic, score_chat_window

    messages = []
    # Baseline: ~1 msg/sec across 0..180s
    for sec in range(180):
        messages.append({"t": float(sec) + 0.1, "text": "normal comment"})
        if sec % 3 == 0:
            messages.append({"t": float(sec) + 0.5, "text": "ok"})

    # Massive spike between 90s and 98s (30 msgs/sec + emotes)
    for sec in range(90, 99):
        for k in range(25):
            messages.append(
                {
                    "t": float(sec) + k * 0.03,
                    "text": "KKKKKK LUL CLIP ISSO MENTIRA ???" if k % 2 == 0 else "OMEGALUL",
                }
            )

    result = analyze_chat_seismic(messages, duration_s=180.0)
    assert result["peaks"], "Deve detectar ao menos um pico sismico no chat"
    peak = result["peaks"][0]
    assert peak["vel_zscore"] >= 3.5
    assert peak["emote_burst"] > 0.0
    assert peak["start"] <= 92.0 and peak["end"] >= 96.0

    # Window around peak scores significantly higher than quiet baseline
    hot_score = score_chat_window(result, 88.0, 102.0)
    quiet_score = score_chat_window(result, 10.0, 30.0)
    assert hot_score >= 7.0
    assert quiet_score < hot_score


def test_analyze_chat_seismic_2h_log_runs_under_two_seconds():
    from picorte.engine.chat_seismic import analyze_chat_seismic

    messages = [
        {"t": (i * 1.44) % 7200.0, "text": "kkkkk lul" if i % 15 == 0 else "chat msg"}
        for i in range(5000)
    ]
    t0 = time.perf_counter()
    result = analyze_chat_seismic(messages, duration_s=7200.0)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0
    assert len(result["per_second"]) == 7200
