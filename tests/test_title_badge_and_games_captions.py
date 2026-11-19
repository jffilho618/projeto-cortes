from __future__ import annotations

from pathlib import Path
import re

import cv2
import numpy as np

import render_clips


def test_create_torn_paper_badge_creates_rgba_png_with_jagged_transparent_edges(tmp_path: Path):
    from picorte.engine.title_badge import create_torn_paper_badge

    out = tmp_path / "_title_badge.png"
    res = create_torn_paper_badge(out, width=960, height=210)

    assert res == out
    assert out.exists()
    img = cv2.imread(str(out), cv2.IMREAD_UNCHANGED)
    assert img is not None
    assert img.shape == (210, 960, 4)

    alpha = img[:, :, 3]
    # Corners must stay transparent outside the torn paper strip
    assert alpha[0, 0] == 0
    assert alpha[0, -1] == 0
    assert alpha[-1, 0] == 0
    assert alpha[-1, -1] == 0
    # Center body must be solid opaque
    assert alpha[105, 480] == 255

    # Top and bottom edges must be organic/jagged, not a rigid rectangle
    mid_col_top = int(np.argmax(alpha[:, 480] > 200))
    quarter_col_top = int(np.argmax(alpha[:, 240] > 200))
    three_quarter_col_top = int(np.argmax(alpha[:, 720] > 200))
    assert len({mid_col_top, quarter_col_top, three_quarter_col_top}) >= 2 or mid_col_top > 4


def test_build_ass_games_layout_uses_lower_fixed_anchor_and_seam_title_badge(tmp_path: Path):
    ass_path = tmp_path / "games.ass"
    words = [
        {"word": "não,", "start": 40.0, "end": 40.2},
        {"word": "amigo,", "start": 40.2, "end": 40.5},
        {"word": "por", "start": 40.5, "end": 40.8},
        {"word": "favor!", "start": 40.8, "end": 41.2},
    ]

    render_clips.build_ass(
        words,
        clip_start=0.0,
        clip_end=50.0,
        path=ass_path,
        tw=1080,
        th=1920,
        font_size=74,
        margin_v=450,
        context_banner_2s="Colocou gasolina comum e deu ruim!",
        games_layout=True,
        facecam_h=640,
    )

    content = ass_path.read_text(encoding="utf-8")

    # Symmetrical narrower margins so words stay on fewer lines and centered
    cap_style = next(line for line in content.splitlines() if line.startswith("Style: Cap,"))
    fields = cap_style.split(",")
    margin_l = int(fields[19])
    margin_r = int(fields[20])
    assert margin_l == margin_r
    assert margin_l <= 80

    # Dialogue captions anchored low and fixed with \an8\pos(540, y) where y > 1520
    cap_dialogues = [l for l in content.splitlines() if l.startswith("Dialogue: 0,")]
    assert cap_dialogues
    m = re.search(r"\\an8\\pos\(540,(\d+)\)", cap_dialogues[0])
    assert m is not None, f"Missing fixed lower \\an8\\pos anchor in {cap_dialogues[0]}"
    assert int(m.group(1)) >= 1520

    # ContextBanner centered on the facecam/gameplay seam without ASS grey box (torn-paper PNG is the bg)
    banner_style = next(line for line in content.splitlines() if line.startswith("Style: ContextBanner,"))
    b_fields = banner_style.split(",")
    assert int(b_fields[2]) >= 72  # proportional bold display size matching reference
    assert b_fields[15] == "1"  # BorderStyle=1 (outline/shadow over torn-paper PNG, no box=3)

    banner_dialogues = [l for l in content.splitlines() if "ContextBanner," in l and l.startswith("Dialogue:")]
    assert len(banner_dialogues) == 1
    assert "\\an5\\pos(540,640)" in banner_dialogues[0]
    # Highlights at least one word in bright yellow (&H0000D4FF&)
    assert "&H0000D4FF&" in banner_dialogues[0]
    # Balanced 2-line split when wrapping multi-word titles
    assert "\\N" in banner_dialogues[0]
