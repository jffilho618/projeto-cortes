"""
Stage 3 of the viral-clip pipeline.

Renders scored segments to clips in a chosen aspect ratio:
  - 16:9 (default) -> landscape, full frame kept
  - 9:16           -> vertical, dynamic speaker-tracking crop (YuNet + snap-on-cut)
  - 1:1            -> square
Captions are word-by-word CapCut style, burnt in via the ffmpeg ASS engine,
with selectable style presets. Optional --tighten removes filler words and
long silences (captions are re-timed automatically). Every clip gets a PNG
poster and a .meta.json with a ready-to-post title, description and hashtags.

No external/paid APIs. ffmpeg + OpenCV only. Usage:
    python render_clips.py [workdir] [--aspect 16:9|9:16|1:1]
                           [--out DIR] [--style NAME]
                           [--tighten] [--loudnorm] [--preview]
Output directory (default ./clips) can also be set with $CHOPIFY_OUT.
"""
import sys
import os
import re
import json
import argparse
import subprocess
import math
from pathlib import Path

import branding
import tighten  # local module: filler/silence removal

# aspect -> (target_w, target_h, caption_font_size, caption_margin_v)
# AD-7: 9:16 usa margin_v = 450px (Área Segura Unificada para Shorts/TikTok/Reels/FB)
ASPECTS = {
    "16:9": (1920, 1080, 72, 95),
    "9:16": (1080, 1920, 96, 450),
    "1:1":  (1080, 1080, 82, 120),
}
DEFAULT_ASPECT = "16:9"

# --preview drafts: small, fast, no poster/meta. Caption font/margins scale down
# proportionally from the full-size ASPECTS values (height is the anchor).
PREVIEW = {
    "16:9": (854, 480),
    "9:16": (480, 854),
    "1:1":  (480, 480),
}

# Caption presets. Colors are #RRGGBB here; build_ass accepts both hex and the
# ASS strings returned by branding.load_brand. Font size and margin are measured
# at 1080px output height, so None means "use this aspect's base value".
CAPTION_STYLES = {
    "default": {
        "font": "Arial Black", "weight": -1, "color": "#FFFFFF",
        "highlight": "#FFFF00", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": False, "words_per_cue": 3,
        "position": "bottom", "outline": 5, "shadow": 2, "background": "none",
        "background_color": "#000000", "background_opacity": 70,
        "animation": "none", "highlight_mode": "word", "emoji": False,
        "emphasis": False,
    },
    "clean": {
        "font": "Arial", "weight": 0, "color": "#FFFFFF",
        "highlight": "#FFB000", "emphasis_color": "#FFD400",
        "outline_color": "#101010", "uppercase": False, "words_per_cue": 3,
        "position": "bottom", "outline": 2, "shadow": 1, "background": "none",
        "animation": "none", "highlight_mode": "word",
    },
    "minimal": {
        "font": "Arial", "weight": 0, "color": "#FFFFFF",
        "highlight": "#D4EF83", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": False, "words_per_cue": 5,
        "position": "bottom", "outline": 8, "shadow": 0, "background": "box",
        "background_color": "#111111", "background_opacity": 65,
        "animation": "none", "highlight_mode": "word",
    },
    "bold": {
        "font": "Impact", "weight": -1, "color": "#FFFFFF",
        "highlight": "#FF7A00", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": True, "words_per_cue": 2,
        "position": "bottom", "outline": 8, "shadow": 2, "background": "none",
        "animation": "pop", "highlight_mode": "word",
    },
    "boxed": {
        "font": "Arial Black", "weight": -1, "color": "#FFFFFF",
        "highlight": "#FFFF00", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": True, "words_per_cue": 3,
        "position": "bottom", "outline": 10, "shadow": 0, "background": "box",
        "background_color": "#000000", "background_opacity": 80,
        "animation": "none", "highlight_mode": "word",
    },
    "karaoke": {
        "font": "Arial Black", "weight": -1, "color": "#FFFFFF",
        "highlight": "#FFFF00", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": False, "words_per_cue": 4,
        "position": "bottom", "outline": 5, "shadow": 2, "background": "none",
        "animation": "none", "highlight_mode": "karaoke",
    },
    "pop": {
        "font": "Impact", "weight": -1, "color": "#FFFFFF",
        "highlight": "#FF7A00", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": True, "words_per_cue": 2,
        "position": "bottom", "outline": 6, "shadow": 2, "background": "none",
        "animation": "pop", "highlight_mode": "word",
    },
    "neon": {
        "font": "Arial", "weight": 0, "color": "#FFFFFF",
        "highlight": "#00FFFF", "emphasis_color": "#00FFFF",
        "outline_color": "#00FFFF", "uppercase": True, "words_per_cue": 3,
        "position": "bottom", "outline": 3, "shadow": 0, "background": "none",
        "animation": "fade", "highlight_mode": "word",
    },
    "typewriter": {
        "font": "Courier New", "weight": 0, "color": "#FFFFFF",
        "highlight": "#00FF7F", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": False, "words_per_cue": 4,
        "position": "bottom", "outline": 3, "shadow": 1, "background": "none",
        "animation": "typewriter", "highlight_mode": "word",
    },
    "retro": {
        "font": "Georgia", "weight": 0, "color": "#FFF6D5",
        "highlight": "#FFB000", "emphasis_color": "#FFD400",
        "outline_color": "#2B1A0A", "uppercase": False, "words_per_cue": 3,
        "position": "bottom", "outline": 2, "shadow": 6, "background": "none",
        "animation": "none", "highlight_mode": "word",
    },
    "hormozi": {
        "font": "Arial Black", "weight": -1, "color": "#FFFFFF",
        "highlight": "#FF0000", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": False, "words_per_cue": 2,
        "position": "bottom", "outline": 5, "shadow": 2, "background": "none",
        "animation": "pop", "highlight_mode": "word",
    },
    "mrbeast": {
        "font": "Arial Black", "weight": -1, "color": "#FFFFFF",
        "highlight": "#00FF00", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": False, "words_per_cue": 2,
        "position": "bottom", "outline": 5, "shadow": 2, "background": "none",
        "animation": "pop", "highlight_mode": "word",
    },
    "podcast": {
        "font": "Arial", "weight": 0, "color": "#FFFFFF",
        "highlight": "#FFFF00", "emphasis_color": "#FFD400",
        "outline_color": "#000000", "uppercase": False, "words_per_cue": 4,
        "position": "bottom", "outline": 3, "shadow": 1, "background": "none",
        "animation": "none", "highlight_mode": "karaoke",
    },
}
DEFAULT_STYLE = "default"
ALIGNMENTS = {"bottom": 2, "center": 5, "top": 8}

# Automatic emphasis is deliberately small and deterministic. Two words per cue
# at most, so a line never turns into a wall of colour.
POWER_WORDS = frozenset("""
secret mistake mistakes never always free proven guarantee guaranteed fastest
best worst huge massive insane crazy shocking truth nobody everyone stop start
why how million billion thousand hundred percent money cash rich broke
""".split())

EMOJI_RULES = [
    (("money", "cash", "dollar", "profit", "revenue", "rich", "paid", "pay",
      "salary", "price", "cost", "income", "sale"), "💰"),
    (("grow", "growth", "scale", "audience", "follower", "subscriber", "view"), "📈"),
    (("idea", "secret", "tip", "hack", "strategy", "plan", "trick"), "💡"),
    (("time", "hour", "minute", "day", "week", "month", "year", "deadline"), "⏰"),
    (("love", "heart", "passion"), "❤️"),
    (("fire", "amazing", "incredible", "insane", "crazy"), "🔥"),
    (("win", "success", "best", "great", "awesome", "winner"), "🏆"),
    (("mistake", "wrong", "fail", "failure", "problem", "risk", "warning"), "⚠️"),
    (("think", "brain", "learn", "knowledge", "understand"), "🧠"),
    (("work", "job", "business", "client", "customer"), "💼"),
    (("video", "camera", "record", "content", "youtube", "tiktok", "podcast"), "🎬"),
]


def default_out():
    """Output dir: --out wins, then $CHOPIFY_OUT, then ./clips (no more hardcoded C:\\clips)."""
    return Path(os.environ.get("CHOPIFY_OUT") or "clips")


def get_style(name):
    if name not in CAPTION_STYLES:
        raise SystemExit(f"Unknown caption style '{name}'. "
                         f"Choose from: {', '.join(CAPTION_STYLES)}")
    return CAPTION_STYLES[name]


def resolve_caption(style_name=DEFAULT_STYLE, brand=None, caption=None):
    """Merge preset -> brand -> project override into one concrete style."""
    style = {"weight": -1, **branding.CAPTION_DEFAULTS, **get_style(style_name)}
    if brand:
        for key in branding.CAPTION_FIELDS:
            value = brand.get(key)
            if value is not None:
                style[key] = value
    if caption:
        style.update(branding.validate_caption(caption))
    return style


def ass_style_color(value):
    """Accept #RRGGBB and the ASS strings load_brand already produces."""
    if isinstance(value, str) and re.fullmatch(r"&H[0-9a-fA-F]{6,8}&", value):
        return value
    return branding.ass_color(value)


def ass_box_color(value, opacity):
    color = ass_style_color(value)[2:-1]
    bgr = color[2:] if len(color) == 8 else color
    alpha = round((100 - opacity) * 255 / 100)
    return f"&H{alpha:02X}{bgr}&"


def _plain_word(word):
    return re.sub(r"^[^\w$€£¥]+|[^\w%$€£¥]+$", "", str(word).strip())


def is_emphasized(word):
    plain = _plain_word(word)
    if not plain:
        return False
    if re.search(r"\d", plain) or re.search(r"[$€£¥]", plain):
        return True
    if plain.isupper() and len(plain) > 2 and any(c.isalpha() for c in plain):
        return True
    return plain.lower().strip(".,!?;:'\"") in POWER_WORDS


def _emoji_for(word):
    token = re.sub(r"[^a-z0-9']", "", str(word).lower())
    if not token:
        return None
    for stems, emoji in EMOJI_RULES:
        if any(token.startswith(stem) for stem in stems):
            return emoji
    return None


def _cue_highlight(group, enabled):
    """Indexes to emphasise, at most two per cue. Forced flags always count."""
    marked = [i for i, word in enumerate(group) if word.get("emphasis") is True]
    if enabled:
        marked += [i for i, word in enumerate(group)
                   if i not in marked and is_emphasized(word["word"])]
    return set(marked[:2])


def _cue_emoji(group):
    for index, word in enumerate(group):
        emoji = _emoji_for(word["word"])
        if emoji:
            return index, emoji
    return None, None


def _motion_tag(animation):
    if animation == "pop":
        return r"\fscx135\fscy135\t(0,120,\fscx100\fscy100)"
    if animation == "bounce":
        return (r"\fscx88\fscy118\t(0,90,\fscx112\fscy88)"
                r"\t(90,210,\fscx100\fscy100)")
    if animation == "fade":
        return r"\fad(150,0)"
    return ""

WORDS_PER_LINE = 3
DET_FPS = 5
DET_W = 640
EMA_ALPHA = 0.20
JUMP_FRAC = 0.22
MARGIN_FRAC = 0.18
YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
             "face_detection_yunet/face_detection_yunet_2023mar.onnx")


def sanitize(text, maxlen=70):
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:maxlen].strip("-") or "clip"


def ffprobe_dims(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split("x")[:2]
    return int(w), int(h)


def crop_for(W, H, tw, th):
    """Largest centred crop of the WxH source matching the target aspect."""
    tar = tw / float(th)
    src = W / float(H)
    if abs(src - tar) < 1e-3:
        cw, ch = W, H
    elif src > tar:                      # source wider -> crop width
        ch = H
        cw = int(round(H * tar))
    else:                                # source taller -> crop height
        cw = W
        ch = int(round(W / tar))
    cw -= cw % 2
    ch -= ch % 2
    x0 = max(0, (W - cw) // 2)
    y0 = max(0, (H - ch) // 2)
    return cw, ch, x0, y0


def _make_detector(workdir):
    import cv2
    candidates = [
        Path(workdir).parent / "yunet.onnx",
        Path(__file__).resolve().parent / "picorte" / "models" / "yunet.onnx",
        Path(__file__).resolve().parent.parent / "models" / "yunet.onnx",
        Path(__file__).resolve().parent / "yunet.onnx",
    ]
    model = next((p for p in candidates if p.exists()), candidates[0])
    if not model.exists():
        try:
            import urllib.request
            urllib.request.urlretrieve(YUNET_URL, str(model))
        except Exception as e:
            print("  YuNet download failed -> fallback:", e, flush=True)
    if model.exists() and hasattr(cv2, "FaceDetectorYN"):
        try:
            return "yunet", cv2.FaceDetectorYN.create(str(model), "", (DET_W, 360), 0.6, 0.3, 5000)
        except Exception as e:
            print("  YuNet init failed -> fallback:", e, flush=True)
    if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data"):
        return "haar", cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return "none", None


def detect_track(source, start, dur, W, workdir):
    """Low-res detection pass -> [(t_rel, center_x_source_px or None)]."""
    import cv2
    det_path = Path(workdir) / "_det.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(source),
         "-t", f"{dur:.3f}", "-vf", f"fps={DET_FPS},scale={DET_W}:-2",
         "-an", str(det_path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    kind, det = _make_detector(workdir)
    cap = cv2.VideoCapture(str(det_path))
    dw = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or DET_W
    dh = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360
    sx = W / float(dw)
    if kind == "yunet":
        det.setInputSize((int(dw), int(dh)))
    track = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = i / float(DET_FPS)
        cx = None
        if kind == "yunet" and det is not None:
            _, faces = det.detect(frame)
            if faces is not None and len(faces):
                best = max(faces, key=lambda f: f[2] * f[3] * float(f[14]))
                cx = (best[0] + best[2] / 2.0) * sx
        elif kind == "haar" and det is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = det.detectMultiScale(gray, 1.1, 5, minSize=(36, 36))
            if len(faces):
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                cx = (x + w / 2.0) * sx
        track.append((t, cx))
        i += 1
    cap.release()
    try:
        det_path.unlink()
    except OSError:
        pass
    return track


def smooth_track(track, W, crop_w):
    half = crop_w / 2.0
    max_off = half - crop_w * MARGIN_FRAC
    jump = W * JUMP_FRAC
    known = [c for _, c in track if c is not None]
    base = sorted(known)[len(known) // 2] if known else W / 2.0
    filled = []
    last = base
    for t, c in track:
        if c is None:
            c = last
        last = c
        filled.append((t, c))
    if not filled:
        return [(0.0, min(max(base, half), W - half))]
    out = []
    c = filled[0][1]
    prev_face = filled[0][1]
    for t, face in filled:
        if abs(face - prev_face) > jump:
            c = face
        else:
            c += EMA_ALPHA * (face - c)
        if face - c > max_off:
            c = face - max_off
        elif c - face > max_off:
            c = face + max_off
        prev_face = face
        out.append((t, min(max(c, half), W - half)))
    return out


def build_sendcmd(track, crop_w, path):
    lines = []
    last = None
    for t, cx in track:
        x = int(round(cx - crop_w / 2.0))
        if last is None or abs(x - last) >= 2:
            lines.append(f"{t:.2f} crop x {x};")
            last = x
    if not lines:
        lines = ["0.0 crop x 0;"]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def ass_time(t):
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def ass_escape(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


_PT_EXCLUSIVE_WORDS = {
    "à", "ao", "aos", "até", "com", "como", "das", "dos", "é", "ela", "ele",
    "então", "essa", "esse", "está", "estão", "estou", "eu", "faz", "fez",
    "foi", "fui", "gente", "aqui", "ali", "agora", "isso", "isto", "já", "lá",
    "mais", "mano", "mas", "meu", "minha", "muito", "na", "não", "nas", "né",
    "nos", "nossa", "olha", "os", "ou", "para", "pelo", "pela", "por", "pra",
    "que", "quem", "sem", "ser", "será", "sim", "só", "tá", "tem", "ter",
    "tô", "tudo", "um", "uma", "vai", "vamos", "você", "vocês", "cara",
    "caramba", "opa", "nunca", "sempre", "porque", "quando", "onde", "nada",
}

_EN_STOPWORDS = {
    "a", "about", "after", "all", "am", "an", "and", "any", "anybody's", "are",
    "around", "as", "at", "be", "because", "been", "being", "believe", "brat",
    "bro", "brother", "but", "by", "can", "can't", "come", "could", "did",
    "didn't", "do", "does", "doesn't", "don't", "down", "every", "everyone",
    "for", "from", "funny", "get", "go", "going", "good", "got", "had", "has",
    "have", "he", "he's", "her", "here", "hey", "him", "his", "how", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "just", "keeping", "know", "last", "let", "let's", "like", "look",
    "man", "me", "mean", "more", "my", "need", "never", "not", "nothing", "now",
    "of", "off", "on", "one", "only", "or", "other", "our", "out", "over",
    "people", "point", "really", "right", "said", "say", "see", "she", "she's",
    "shit", "should", "so", "some", "something", "stop", "sure", "take", "tell",
    "than", "that", "that's", "the", "their", "them", "then", "there", "these",
    "they", "they're", "thing", "think", "this", "those", "time", "to", "too",
    "up", "us", "very", "want", "was", "wasn't", "way", "we", "we're", "well",
    "were", "what", "what's", "when", "where", "which", "who", "why", "will",
    "with", "won't", "would", "yeah", "yes", "you", "you're", "you've",
    "your", "arguing", "ice", "again",
}

_PT_ACCENT_RE = re.compile(r"[áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]")


def _is_pure_english_npc_sentence(sent_words: list[dict]) -> bool:
    text = " ".join(str(w.get("word", "")).strip() for w in sent_words)
    if _PT_ACCENT_RE.search(text):
        return False
    tokens = [re.sub(r"[^a-zA-Z0-9'áéíóúâêôãõç]", "", w.get("word", "").lower()) for w in sent_words]
    tokens = [t for t in tokens if t]
    if not tokens:
        return False
    pt_hits = sum(1 for t in tokens if t in _PT_EXCLUSIVE_WORDS)
    if pt_hits > 0:
        return False
    en_hits = sum(1 for t in tokens if t in _EN_STOPWORDS)
    if len(tokens) == 1:
        return tokens[0] in {"i", "i'm", "he's", "she's", "it's", "they're", "we're", "you're", "the", "yeah"}
    return en_hits >= 2 and (en_hits / len(tokens)) >= 0.45


def filter_streamer_language_words(words: list[dict], dominant_language: str | None = "pt") -> list[dict]:
    """Remove falas isoladas em inglês (NPCs/cutscenes) quando o idioma principal do streamer é PT-BR."""
    if not words or (dominant_language or "").lower() not in {"pt", "pt-br", "portuguese"}:
        return list(words or [])

    # Divide por pausa >= 0.65s ou fim de sentença para preservar gírias em inglês dentro de frases PT
    sentences: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur and (float(w["start"]) - float(cur[-1]["end"])) >= 0.65:
            sentences.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?…][\"')\]]?$", str(w.get("word", "")).strip()):
            sentences.append(cur)
            cur = []
    if cur:
        sentences.append(cur)

    flags = [_is_pure_english_npc_sentence(s) for s in sentences]
    kept: list[dict] = []
    for idx, sent in enumerate(sentences):
        if flags[idx]:
            continue
        # Remove resíduo isolado de 1 token inglês ("I", "Oh,", etc.) se os blocos vizinhos eram NPC em inglês
        if len(sent) <= 2 and (
            (idx > 0 and flags[idx - 1]) or (idx + 1 < len(sentences) and flags[idx + 1])
        ):
            txt = " ".join(re.sub(r"[^a-zA-Z']", "", w.get("word", "").lower()) for w in sent).strip()
            if txt in {"i", "oh", "ah", "uh", "well", "and", "but", "so"}:
                continue
        kept.extend(sent)
    return kept


_BANNER_STOPWORDS = {
    "a", "o", "as", "os", "e", "em", "de", "do", "da", "dos", "das",
    "no", "na", "nos", "nas", "um", "uma", "por", "para", "com", "que",
    "se", "é", "eh", "foi", "vai", "ao", "ou", "quando", "como", "ele", "ela",
}


def _format_games_banner_ass(text: str, max_chars_per_line: int = 24) -> str:
    clean = " ".join(str(text).replace("\n", " ").split())
    if not clean:
        return ""
    raw_words = clean.split(" ")
    if len(raw_words) > 9:
        raw_words = raw_words[:9]

    best_idx = None
    best_score = -1.0
    for idx, tok in enumerate(raw_words):
        stripped = re.sub(r"[^\wáàâãéêíóôõúüç]", "", tok.lower())
        if not stripped or stripped in _BANNER_STOPWORDS:
            continue
        score = len(stripped) + (2.0 if any(ch.isdigit() for ch in stripped) else 0.0)
        if 0 < idx < len(raw_words) - 1:
            score += 0.5
        if score > best_score:
            best_score = score
            best_idx = idx
    highlight_indices: set[int] = set()
    if best_idx is not None:
        highlight_indices.add(best_idx)
        if best_idx + 1 < len(raw_words):
            nxt = re.sub(r"[^\wáàâãéêíóôõúüç]", "", raw_words[best_idx + 1].lower())
            if nxt and nxt not in _BANNER_STOPWORDS and len(nxt) >= 4:
                highlight_indices.add(best_idx + 1)

    styled_tokens = []
    for idx, tok in enumerate(raw_words):
        word_up = ass_escape(tok.upper())
        word_color = "&H0000D4FF&" if idx in highlight_indices else "&H00FFFFFF&"
        styled_tokens.append("{\\c" + word_color + "}" + word_up)

    total_chars = sum(len(w) for w in raw_words) + max(0, len(raw_words) - 1)
    if len(raw_words) <= 1 or total_chars <= 15:
        return " ".join(styled_tokens)

    # Balanced 2-line split near midpoint so neither line has a tiny orphan
    best_split = 1
    best_diff = 10**9
    for split_at in range(1, len(raw_words)):
        left_len = len(" ".join(raw_words[:split_at]))
        right_len = len(" ".join(raw_words[split_at:]))
        overflow_pen = 0
        if left_len > max_chars_per_line:
            overflow_pen += (left_len - max_chars_per_line) * 4
        if right_len > max_chars_per_line:
            overflow_pen += (right_len - max_chars_per_line) * 4
        diff = abs(left_len - right_len) + overflow_pen
        if diff < best_diff:
            best_diff = diff
            best_split = split_at
    return " ".join(styled_tokens[:best_split]) + "\\N" + " ".join(styled_tokens[best_split:])


def build_ass(words, clip_start, clip_end, path, tw, th, font_size, margin_v,
              style_name=DEFAULT_STYLE, brand=None, caption=None,
              context_banner_2s=None, games_layout=False, facecam_h=None,
              banner_start=0.0, banner_end=3.4):
    st = resolve_caption(style_name, brand, caption)
    color = ass_style_color(st["color"])
    highlight = ass_style_color(st["highlight"])
    emphasis = ass_style_color(st["emphasis_color"])
    outline_color = ass_style_color(st["outline_color"])
    if st["font_size"] is not None:
        font_size = max(12, round(st["font_size"] * th / 1080))
    if st["margin"] is not None:
        margin_v = max(0, round(st["margin"] * th / 1080))
    outline_px = max(0, round(st["outline"] * th / 1080))
    shadow_px = max(0, round(st["shadow"] * th / 1080))
    alignment = ALIGNMENTS[st["position"]]
    if st["background"] == "box":
        border_style = 3
        outline_colour = ass_box_color(st["background_color"], st["background_opacity"])
        back_colour = outline_colour
    else:
        border_style = 1
        outline_colour = outline_color
        back_colour = "&H64000000"
    sub = [w for w in words
           if not w.get("hidden") and w["end"] > clip_start and w["start"] < clip_end]
    if games_layout:
        margin_l = max(20, round(60 * tw / 1080))
        margin_r = margin_l
        cap_font_size = max(12, round(font_size * 0.78))
        cap_margin_v = max(30, round(th * 0.16))
        cap_y = round(th * 0.80)  # 1536px em 1080x1920 — acima da zona de legendas nativas do jogo!
        banner_clean_len = len(" ".join(str(context_banner_2s or "").split()))
        if banner_clean_len <= 30:
            banner_ratio, banner_scalex = 0.044, 92
        elif banner_clean_len <= 38:
            banner_ratio, banner_scalex = 0.041, 90
        else:
            banner_ratio, banner_scalex = 0.033, 84
        banner_font = max(20, round(th * banner_ratio))
        banner_font_name = "Impact" if sys.platform == "win32" else "Ubuntu Sans"
        banner_outline = max(2, round(banner_font * 0.115))
        banner_shadow = max(1, round(banner_font * 0.065))
        banner_margin_lr = max(20, round(tw * 0.085))
        banner_style_line = (
            f"Style: ContextBanner,{banner_font_name},{banner_font},&H00FFFFFF,&H00FFFFFF,"
            f"&H00000000,&HC0000000,-1,0,0,0,{banner_scalex},100,-0.5,0,1,{banner_outline},"
            f"{banner_shadow},5,{banner_margin_lr},{banner_margin_lr},20,1\n\n"
        )
    else:
        margin_l = 80
        margin_r = max(160, round(160 * tw / 1080)) if th > tw else 80
        cap_font_size = font_size
        cap_margin_v = margin_v
        cap_y = None
        banner_style_line = (
            f"Style: ContextBanner,{st['font']},{max(22, round(font_size * 0.65))},"
            f"&H00FFFFFF,&H00FFFFFF,&HC8000000,&HC8000000,-1,0,0,0,100,100,0,0,3,12,"
            f"0,8,80,80,{max(40, round(th * 0.14))},1\n\n"
        )
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {tw}\nPlayResY: {th}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap,{st['font']},{cap_font_size},{color},{color},{outline_colour},"
        f"{back_colour},{st['weight']},0,0,0,100,100,0,0,{border_style},"
        f"{outline_px},{shadow_px},{alignment},{margin_l},{margin_r},{cap_margin_v},1\n"
        + banner_style_line
        + "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )
    group_size = int(st["words_per_cue"] or WORDS_PER_LINE)
    groups = []
    cur_group = []
    for w in sub:
        if cur_group and (
            len(cur_group) >= group_size
            or (float(w["start"]) - float(cur_group[-1]["end"])) >= 0.70
        ):
            groups.append(cur_group)
            cur_group = []
        cur_group.append(w)
    if cur_group:
        groups.append(cur_group)

    animation = st["animation"]
    events = []
    next_group_starts = {
        id(groups[idx][-1]): float(groups[idx + 1][0]["start"])
        for idx in range(len(groups) - 1)
    }
    for group in groups:
        emphasised = _cue_highlight(group, bool(st["emphasis"]))
        emoji_index, emoji = _cue_emoji(group) if st["emoji"] else (None, None)
        for i, word in enumerate(group):
            w_start = max(float(word["start"]), clip_start)
            # Evita timestamps esticados pelo Whisper (> 1.8s numa palavra única)
            w_end = min(float(word["end"]), w_start + 1.8)
            s0 = w_start - clip_start
            if i + 1 < len(group):
                next_s = float(group[i + 1]["start"])
                if next_s - w_end <= 0.35:
                    raw_en = min(clip_end, next_s) - clip_start
                else:
                    raw_en = min(clip_end, w_end + 0.15) - clip_start
            else:
                cap_next = next_group_starts.get(id(word), float(clip_end))
                raw_en = min(clip_end, cap_next, w_end + 0.15) - clip_start
            en = max(s0 + 0.08, raw_en)
            parts = []
            for j, item in enumerate(group):
                if animation == "typewriter" and j > i:
                    continue
                token = ass_escape(item["word"].strip())
                if st["uppercase"]:
                    token = token.upper()
                if j == emoji_index:
                    token += f" {{\\fnSegoe UI Emoji}}{emoji}{{\\fn{st['font']}}}"
                if j == i and st["highlight_mode"] != "none":
                    word_color = highlight
                elif st["highlight_mode"] == "karaoke" and j < i:
                    word_color = highlight
                elif st["highlight_mode"] != "none" and j in emphasised:
                    word_color = emphasis
                else:
                    word_color = color
                motion = _motion_tag(animation) if j == i else ""
                parts.append("{" + f"\\c{word_color}" + motion + "}" + token)
            pos_tag = f"{{\\an8\\pos({tw // 2},{cap_y})}}" if cap_y is not None else ""
            events.append(
                f"Dialogue: 0,{ass_time(s0)},{ass_time(en)},Cap,,0,0,0,,{pos_tag}{' '.join(parts)}")
    if context_banner_2s:
        banner_raw = str(context_banner_2s).replace("\n", " ").strip()
        if banner_raw:
            if games_layout:
                seam_y = int(facecam_h) if facecam_h else ((round(th / 3.0)) // 2) * 2
                banner_styled = _format_games_banner_ass(banner_raw, max_chars_per_line=26)
                b_start = max(0.0, float(banner_start))
                b_end = max(b_start + 0.6, float(banner_end))
                events.append(
                    f"Dialogue: 1,{ass_time(b_start)},{ass_time(b_end)},ContextBanner,,0,0,0,,{{\\fad(140,140)\\q2\\an5\\pos({tw // 2},{seam_y})}}{banner_styled}"
                )
            else:
                banner_txt = ass_escape(banner_raw)
                safe_x = tw // 2
                safe_y = max(40, round(th * 0.156))  # ~300px em 1080x1920 (y=240..360 AD-7)
                events.append(
                    f"Dialogue: 1,0:00:00.00,0:00:02.00,ContextBanner,,0,0,0,,{{\\an8\\pos({safe_x},{safe_y})}}{banner_txt}"
                )
    Path(path).write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def write_meta(seg, out_path, source_meta=None):
    """Deterministic ready-to-post metadata + PublishPayload PT-BR saved as <clip>.meta.json."""
    from picorte.engine.publish_kit import build_publish_kit

    thumb_candidate = Path(out_path).with_name(Path(out_path).stem + "_thumb.png")
    kit = build_publish_kit(
        seg,
        source_meta=source_meta,
        mp4_path=out_path,
        thumb_path=seg.get("thumbnail_1280x720") or (str(thumb_candidate) if thumb_candidate.is_file() else ""),
    )
    yt = kit["platforms"]["youtube_shorts"]
    meta = {
        "title": yt["title"],
        "description": yt["description"],
        "hashtags": yt["hashtags"],
        "score": seg.get("overall"),
        "start": seg.get("start"),
        "end": seg.get("end"),
        "publish_kit": kit,
    }
    for extra in (
        "proposed_title",
        "context_banner_2s",
        "pinned_comment_debate",
        "parent_long_clip_id",
        "cold_open",
        "thumbnail_1280x720",
        "llm_mode_used",
        "archetype",
        "tier",
    ):
        if seg.get(extra) is not None:
            meta[extra] = seg[extra]
    Path(out_path).with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return Path(out_path).with_suffix(".meta.json")


CAPTION_OPTION_MAP = {
    "words_per_cue": "words_per_cue",
    "uppercase": "uppercase",
    "caption_position": "position",
    "caption_animation": "animation",
    "caption_background": "background",
    "caption_outline": "outline",
    "caption_shadow": "shadow",
    "emoji": "emoji",
    "emphasis": "emphasis",
    "caption_font": "font",
    "caption_color": "color",
    "caption_highlight": "highlight",
    "caption_emphasis_color": "emphasis_color",
}


def add_caption_arguments(ap):
    """Add the shared caption flags to chopify.py and render_clips.py."""
    ap.add_argument("--caption-json", dest="caption_json", metavar="PATH",
                    help="load a full caption style JSON object")
    ap.add_argument("--words-per-cue", dest="words_per_cue", type=int, metavar="N",
                    help="words shown together in each caption cue (1-8)")
    ap.add_argument("--uppercase", action=argparse.BooleanOptionalAction, default=None,
                    help="force captions to uppercase (or --no-uppercase)")
    ap.add_argument("--caption-position", dest="caption_position",
                    choices=["bottom", "center", "top"], default=None)
    ap.add_argument("--caption-animation", dest="caption_animation",
                    choices=["none", "pop", "bounce", "fade", "typewriter"],
                    default=None, help="motion for the active word")
    ap.add_argument("--caption-background", dest="caption_background",
                    choices=["none", "box"], default=None,
                    help="draw a background box behind each cue")
    ap.add_argument("--caption-outline", dest="caption_outline", type=int,
                    metavar="N", help="outline width at 1080px height (0-12)")
    ap.add_argument("--caption-shadow", dest="caption_shadow", type=int,
                    metavar="N", help="shadow depth at 1080px height (0-12)")
    ap.add_argument("--emoji", action=argparse.BooleanOptionalAction, default=None,
                    help="add one relevant emoji per cue (or --no-emoji)")
    ap.add_argument("--emphasis", action=argparse.BooleanOptionalAction, default=None,
                    help="emphasise numbers, money and power words (or --no-emphasis)")
    ap.add_argument("--caption-font", dest="caption_font", metavar="FAMILY")
    ap.add_argument("--caption-color", dest="caption_color", metavar="#RRGGBB")
    ap.add_argument("--caption-highlight", dest="caption_highlight", metavar="#RRGGBB")
    ap.add_argument("--caption-emphasis-color", dest="caption_emphasis_color",
                    metavar="#RRGGBB")


def caption_from_args(args):
    """Build and validate a caption override from shared CLI flags."""
    supplied = getattr(args, "caption_json", None) is not None
    caption = {}
    path = getattr(args, "caption_json", None)
    if path:
        try:
            raw = Path(path).read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise ValueError(f"Could not read caption JSON: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Caption JSON is invalid: {exc}") from exc
        caption.update(branding.validate_caption(data))
    for dest, key in CAPTION_OPTION_MAP.items():
        value = getattr(args, dest, None)
        if value is not None:
            caption[key] = value
            supplied = True
    return branding.validate_caption(caption) if supplied else None


def _detect_overlay_border(frame, axis: str, search_start: int, search_end: int, span_a: int, span_b: int, *, prefer_inner: str) -> int | None:
    """Detecta borda retangular da webcam (transição contínua de cor/luminância) ao longo de uma faixa."""
    import numpy as np

    lo = max(0, min(search_start, search_end))
    hi = max(search_start, search_end)
    if hi - lo < 6:
        return None
    sa, sb = max(0, min(span_a, span_b)), max(span_a, span_b)
    if sb - sa < 16:
        return None

    patch = frame[sa:sb, lo:hi] if axis == "x" else frame[lo:hi, sa:sb]
    if patch.size == 0:
        return None
    f32 = patch.astype(np.float32)
    if axis == "x":
        # Diferença média entre colunas adjacentes ao longo de toda a altura da webcam
        diffs = np.mean(np.abs(f32[:, 1:, :] - f32[:, :-1, :]), axis=(0, 2))
    else:
        diffs = np.mean(np.abs(f32[1:, :, :] - f32[:-1, :, :]), axis=(1, 2))
    if diffs.size == 0:
        return None
    med = float(np.median(diffs))
    best_idx = int(np.argmax(diffs))
    peak = float(diffs[best_idx])
    if peak >= max(10.0, med * 2.2):
        # Retorna posição absoluta + margem de segurança para dentro da webcam
        pos = lo + best_idx
        return pos + 3 if prefer_inner == "right" else pos - 3
    return None


def expand_facecam_box(detected, frame_w: int, frame_h: int, frame=None) -> tuple[int, int, int, int]:
    """Expande a caixa facial do YuNet para enquadrar a webcam inteira sem vazar pixels do jogo."""
    if frame is not None and hasattr(frame, "shape"):
        frame_h, frame_w = int(frame.shape[0]), int(frame.shape[1])
    fx, fy, fw, fh = [int(v) for v in detected]
    pad_x = max(48, int(round(fw * 1.25)))
    pad_top = max(24, int(round(fh * 0.50)))
    pad_bot = max(32, int(round(fh * 0.65)))

    x1 = max(0, fx - pad_x)
    y1 = max(0, fy - pad_top)
    x2 = min(frame_w, fx + fw + pad_x)
    y2 = min(frame_h, fy + fh + pad_bot)

    if frame is not None:
        # Detecta bordas reais da webcam ao redor do rosto para cortar exatamente dentro da moldura
        span_y1 = max(0, fy - int(fh * 0.3))
        span_y2 = min(frame_h, fy + fh + int(fh * 0.3))
        span_x1 = max(0, fx - int(fw * 0.6))
        span_x2 = min(frame_w, fx + fw + int(fw * 0.6))

        left_edge = _detect_overlay_border(frame, "x", max(0, fx - int(fw * 2.0)), max(2, fx - 4), span_y1, span_y2, prefer_inner="right")
        if left_edge is not None and left_edge > x1 and (fx + fw - left_edge) >= int(fw * 1.3):
            x1 = max(0, min(fx - 8, left_edge))
        right_edge = _detect_overlay_border(frame, "x", min(frame_w - 2, fx + fw + 4), min(frame_w, fx + fw + int(fw * 2.0)), span_y1, span_y2, prefer_inner="left")
        if right_edge is not None and right_edge < x2 and (right_edge - fx) >= int(fw * 1.3):
            x2 = min(frame_w, max(fx + fw + 8, right_edge))
        bot_edge = _detect_overlay_border(frame, "y", min(frame_h - 2, fy + fh + 4), min(frame_h, fy + fh + int(fh * 1.4)), span_x1, span_x2, prefer_inner="left")
        if bot_edge is not None and bot_edge < y2:
            y2 = min(frame_h, max(fy + fh + 8, bot_edge))
        top_edge = _detect_overlay_border(frame, "y", max(0, fy - int(fh * 1.2)), max(2, fy - 4), span_x1, span_x2, prefer_inner="right")
        if top_edge is not None and top_edge > y1:
            y1 = max(0, min(fy - 8, top_edge))

    if x2 <= x1 + max(64, fw):
        x1 = max(0, fx - pad_x)
        x2 = min(frame_w, fx + fw + pad_x)
    if y2 <= y1 + max(64, fh):
        y1 = max(0, fy - pad_top)
        y2 = min(frame_h, fy + fh + pad_bot)

    w = max(64, x2 - x1)
    h = max(64, y2 - y1)
    if frame is None:
        min_w = int(round(h * 1.30))
        if w < min_w and min_w <= frame_w:
            extra = min_w - w
            left_shift = min(x1, extra // 2)
            x1 -= left_shift
            x2 = min(frame_w, x2 + (extra - left_shift))
            if (x2 - x1) < min_w and x1 > 0:
                x1 = max(0, x2 - min_w)
            w = max(64, x2 - x1)

    return int(x1), int(y1), int(w), int(h)


GREEN_SEAL_MUTE_GAIN = 0.016  # -36 dB
GREEN_SEAL_FADE_S = 0.015


def _apply_green_seal(seg, cap_words, start, dur):
    """Selo Verde 15s no render: censura legenda, registra bleeps (sempre recalculados) e barra a Camada 3."""
    from picorte.risk_shield.green_seal_15s import plan_green_seal_audio_and_captions
    from picorte.risk_shield.policy_gate import PolicyViolationError

    gs_plan = plan_green_seal_audio_and_captions(
        cap_words, clip_start=start, clip_end=start + dur, cold_open_plan=seg.get("cold_open"))
    seg["_green_seal_bleeps"] = list(gs_plan["bleep_intervals"])
    seg["_green_seal_status"] = gs_plan["status"]
    if gs_plan["status"] == "hard_block":
        raise PolicyViolationError(
            "[P1:selo_verde] Conteúdo de Camada 3 no corte "
            f"({', '.join(gs_plan['hard_block_hits'])}). Render abortado.",
            code="green_seal_hard_block",
            details={"hits": gs_plan["hard_block_hits"]},
        )
    return gs_plan["censored_words"]


def _green_seal_audio_filter(bleeps, dur):
    """Filtro ffmpeg de soft-mute (-36 dB) com rampa de 15 ms nas bordas (sem estalo/corte seco).

    `asetnsamples=64` faz o `volume` (eval=frame) reavaliar a cada ~1,3 ms, o que permite a rampa.
    """
    terms = []
    f = GREEN_SEAL_FADE_S
    for iv in bleeps:
        bs = max(0.0, float(iv["start"]))
        be = min(float(dur), float(iv["end"]))
        if be <= bs + 0.02:
            continue
        terms.append(
            f"if(between(t,{bs:.3f},{be:.3f}),"
            f"max({GREEN_SEAL_MUTE_GAIN},max(1-(t-{bs:.3f})/{f},1-({be:.3f}-t)/{f})),1)"
        )
    if not terms:
        return ""
    expr = "*".join(f"min(1,{t})" for t in terms)
    return f"asetnsamples=n=64:p=0,volume='{expr}':eval=frame"


def render(seg, words, source, W, H, workdir, aspect, out_dir=None, style=DEFAULT_STYLE,
           do_tighten=False, loudnorm=False, preview=False, brand=None,
           layout="single", centers=(0.25, 0.75), caption=None,
           source_offset=0.0, vision_preset="auto", dominant_language=None):
    from captions import write_srt
    out_dir = (Path(out_dir) if out_dir else default_out()).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    source = Path(source).resolve()
    resolved = resolve_caption(style, brand, caption)
    if layout not in {"single", "split", "games"} or (layout in {"split", "games"} and aspect != "9:16"):
        raise ValueError("Split/Games layout requires vertical 9:16 output.")
    if len(centers) != 2 or any(not math.isfinite(v) or not 0 <= v <= 1 for v in centers):
        raise ValueError("Speaker centers must be between 0 and 1.")
    full_w, full_h, font_size, margin_v = ASPECTS[aspect]
    if preview:
        # fast 480p-class draft: smaller frame, smaller captions, no poster/meta
        tw, th = PREVIEW[aspect]
        scale = th / float(full_h)
        font_size = max(12, round(font_size * scale))
        margin_v = max(10, round(margin_v * scale))
    else:
        tw, th = full_w, full_h
    start = float(seg["start"])
    end = float(seg["end"])
    dur = end - start
    offset = float(source_offset)
    if not math.isfinite(offset) or offset < 0:
        raise ValueError("Source offset must be a finite nonnegative number.")
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or dur <= 0:
        raise ValueError("Invalid clip start/end times.")
    if start < offset - 1e-9:
        raise ValueError("Clip start precedes its source section.")
    local_start = max(0.0, start - offset)
    cw, ch, x0, y0 = crop_for(W, H, tw, th)

    cap_words = words
    if dominant_language is None and workdir:
        t_json = Path(workdir) / "transcript.json"
        if t_json.is_file():
            try:
                dominant_language = json.loads(t_json.read_text(encoding="utf-8")).get("language")
            except (OSError, ValueError):
                pass
    if dominant_language:
        cap_words = filter_streamer_language_words(cap_words, dominant_language=dominant_language)
    render_src = source
    if do_tighten:
        keeps = tighten.plan_cuts(cap_words, start, end)
        render_src = out_dir / "_tight_source.mp4"
        tighten.apply_cuts(source, keeps, start, render_src,
                           source_offset=offset)
        cap_words, dur = tighten.remap_words(cap_words, start, keeps)
        print(f"  tightened: {len(keeps)} keep-ranges, "
              f"{(end - start) - dur:.1f}s removed", flush=True)
        start = 0.0
        local_start = 0.0
    games_layout = layout == "games"
    games_facecam_h = ((round(th / 3.0)) // 2) * 2 if games_layout else None
    banner_text = seg.get("context_banner_2s")
    if games_layout and not banner_text:
        banner_text = seg.get("proposed_title") or (
            str(seg["hook"]).replace("-", " ").strip() if seg.get("hook") else None
        )

    badge_path = None
    badge_seam_top = 0
    badge_end_sec = 3.5
    ass_banner_start = 0.0
    ass_banner_end = 3.5
    if games_layout and banner_text and str(banner_text).strip():
        from picorte.engine.title_badge import create_torn_paper_badge

        badge_w = min(tw - 20, max(160, round(tw * 0.86)))
        badge_h = max(64, round(th * 0.132))
        badge_path = out_dir / "_title_badge.png"
        create_torn_paper_badge(badge_path, width=badge_w, height=badge_h)
        badge_seam_top = max(0, int(games_facecam_h) - badge_h // 2)

    # Selo Verde 15s (P1): '***' na legenda + bleeps; Camada 3 aborta o render (nunca falha em silêncio).
    cap_words = _apply_green_seal(seg, cap_words, start, dur)

    build_ass(cap_words, start, start + dur, out_dir / "_caption.ass",
              tw, th, font_size, margin_v, style, brand, caption,
              context_banner_2s=banner_text, games_layout=games_layout,
              facecam_h=games_facecam_h,
              banner_start=ass_banner_start, banner_end=ass_banner_end)

    needs_track = cw < W * 0.95          # real horizontal crop -> track the speaker
    if layout == "split":
        # Keep every YUV420 panel even-sized. Older libass/ffmpeg builds can
        # crash on odd-height intermediate frames (854px drafts / 2 = 427).
        panel_h = (th // 4) * 2
        pcw, pch, _, py = crop_for(W, H, tw, panel_h)
        positions = [max(0, min(W - pcw, round(W * c - pcw / 2))) for c in centers]
        vf = (f"[0:v]split=2[a][b];[a]crop={pcw}:{pch}:{positions[0]}:{py},"
              f"scale={tw}:{panel_h}[top];[b]crop={pcw}:{pch}:{positions[1]}:{py},"
              f"scale={tw}:{panel_h}[bottom];[top][bottom]vstack=inputs=2,"
              f"pad={tw}:{th}:0:0,subtitles=_caption.ass")
        mode = "podcast split-screen"
    elif layout == "games":
        import cv2
        from picorte.engine.reaction_layout import (
            build_reaction_layout,
            find_reactor_face,
        )

        cap = cv2.VideoCapture(str(render_src))
        face_boxes = []
        try:
            n_samples = 6
            for idx in range(n_samples):
                ts_ms = (local_start + (dur * (idx + 0.5) / n_samples)) * 1000.0
                cap.set(cv2.CAP_PROP_POS_MSEC, ts_ms)
                ok, frame = cap.read()
                if ok and frame is not None:
                    detected = find_reactor_face(frame)
                    if detected is not None:
                        face_boxes.append(expand_facecam_box(detected, W, H, frame=frame))
        finally:
            cap.release()

        face_box = None
        if face_boxes:
            # Mediana por coordenada elimina falsos positivos isolados (ex.: boneco/fundo da prateleira)
            def _med(vals):
                s = sorted(vals)
                return int(s[len(s) // 2])
            face_box = (
                _med([b[0] for b in face_boxes]),
                _med([b[1] for b in face_boxes]),
                _med([b[2] for b in face_boxes]),
                _med([b[3] for b in face_boxes]),
            )
            seg["_detected_facecam_box"] = list(face_box)

        # Unanimidade: parte de baixo sempre preenchida 100% e centralizada (sem modo wide-menu com blur)
        facecam_h = games_facecam_h
        rl = build_reaction_layout(
            source_w=W,
            source_h=H,
            out_w=tw,
            out_h=th,
            facecam_box=face_box,
            facecam_h=facecam_h,
            focus_x_norm=0.5,
            focus_y_norm=0.5,
        )
        mode = "games facecam+gameplay"

        if badge_path is not None:
            vf = (
                rl["filter_chain"]
                + f",setsar=1[games_bg];[games_bg][1:v]overlay=(W-w)/2:{badge_seam_top}"
                + f":enable='between(t,0,{badge_end_sec:.3f})',subtitles=_caption.ass"
            )
        else:
            vf = rl["filter_chain"] + ",setsar=1,subtitles=_caption.ass"
    elif needs_track:
        track = smooth_track(detect_track(render_src, local_start, dur, W, workdir), W, cw)
        build_sendcmd(track, cw, out_dir / "_crop.cmd")
        init_x = max(0, min(int(round(track[0][1] - cw / 2.0)), W - cw))
        vf = (f"sendcmd=f=_crop.cmd,crop={cw}:{ch}:{init_x}:{y0},"
              f"scale={tw}:{th},subtitles=_caption.ass")
        mode = "speaker-tracked"
    else:
        vf = f"crop={cw}:{ch}:{x0}:{y0},scale={tw}:{th},subtitles=_caption.ass"
        mode = "full-frame"

    suffix = ".preview" if preview else ""
    prefix = sanitize(str(seg["id"])) + "-" if seg.get("id") else ""
    out = out_dir / (prefix + sanitize(seg.get("hook", "clip")) + suffix + ".mp4")
    cmd = ["ffmpeg", "-y", "-ss", f"{local_start:.3f}", "-i", str(render_src),
           "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
    next_input_idx = 1
    if badge_path is not None:
        pos = cmd.index("-t")
        cmd[pos:pos] = ["-i", badge_path.name]
        next_input_idx += 1
    if brand and brand.get("logo"):
        width = max(20, round(brand["logo_width"] * tw / 1920))
        if layout == "single":
            vf = "[0:v]" + vf
        graph = (vf + f"[captioned];[{next_input_idx}:v]scale={width}:-1[logo];"
                 "[captioned][logo]overlay=W-w-24:24:eof_action=repeat[v]")
        pos = cmd.index("-t")
        cmd[pos:pos] = ["-i", brand["logo"]]
        cmd[cmd.index("-c:v"):cmd.index("-c:v")] = ["-filter_complex", graph, "-map", "[v]", "-map", "0:a?"]
    elif layout in {"split", "games"}:
        cmd[cmd.index("-c:v"):cmd.index("-c:v")] = ["-filter_complex", vf + "[v]", "-map", "[v]", "-map", "0:a?"]
    else:
        cmd[cmd.index("-c:v"):cmd.index("-c:v")] = ["-vf", vf]
    af_parts = []
    gs_filter = _green_seal_audio_filter(seg.get("_green_seal_bleeps") or [], dur)
    if gs_filter:
        af_parts.append(gs_filter)
    if loudnorm:
        af_parts.append("loudnorm=I=-14:TP=-1.5:LRA=11")
    if af_parts:
        cmd[cmd.index("-c:v"):cmd.index("-c:v")] = ["-af", ",".join(af_parts)]
    print(">", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(out_dir))
    write_srt(cap_words, start, start + dur, out.with_suffix(".srt"),
              group_size=resolved["words_per_cue"])

    for tmpf in (out_dir / "_caption.ass", out_dir / "_crop.cmd", out_dir / "_title_badge.png"):
        try:
            tmpf.unlink()
        except OSError:
            pass

    if do_tighten:
        try:
            render_src.unlink()
        except OSError:
            pass

    if preview:
        # drafts skip the poster and metadata - they exist to be eyeballed fast
        print(f"SAVED {out}  ({aspect} {tw}x{th} preview, {mode})", flush=True)
        return out

    # poster: a representative still saved next to the clip (<clip>.png)
    poster = out.with_suffix(".png")
    subprocess.run(["ffmpeg", "-y", "-ss", f"{dur * 0.4:.2f}", "-i", str(out),
                    "-frames:v", "1", "-q:v", "2", str(poster)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    meta_path = write_meta(seg, out)

    print(f"SAVED {out}  ({aspect} {tw}x{th}, {mode})  "
          f"+ poster {poster.name} + {meta_path.name}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir", nargs="?", default="work")
    ap.add_argument("--aspect", default=DEFAULT_ASPECT, choices=list(ASPECTS),
                    help="output aspect ratio (default 16:9)")
    ap.add_argument("--out", default=None,
                    help="output directory (default ./clips, or $CHOPIFY_OUT)")
    ap.add_argument("--style", default=DEFAULT_STYLE,
                    help="caption preset: " + ", ".join(CAPTION_STYLES))
    ap.add_argument("--tighten", action="store_true",
                    help="remove filler words (um, uh...) and long silences")
    ap.add_argument("--loudnorm", action="store_true",
                    help="normalize audio to -14 LUFS (platform standard)")
    ap.add_argument("--preview", action="store_true",
                    help="render fast 480p drafts (no poster/meta) to review "
                         "clip selection before the full render")
    ap.add_argument("--brand", help="path to reusable JSON brand preset")
    ap.add_argument("--layout", choices=["single", "split", "games"], default="single")
    ap.add_argument("--centers", type=float, nargs=2, default=[0.25, 0.75])
    add_caption_arguments(ap)
    args = ap.parse_args()
    from branding import load_brand
    brand = load_brand(args.brand) if args.brand else None
    try:
        caption = caption_from_args(args)
    except ValueError as exc:
        raise SystemExit(f"Caption: {exc}")

    workdir = Path(args.workdir).resolve()
    out_dir = (Path(args.out) if args.out else default_out()).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    transcript = json.loads((workdir / "transcript.json").read_text(encoding="utf-8-sig"))
    segments = json.loads((workdir / "segments.json").read_text(encoding="utf-8-sig"))
    words = transcript["words"]

    source = Path(transcript["video"])
    if not source.exists():
        cands = sorted(workdir.glob("source.*"))
        source = cands[0] if cands else source
    source = source.resolve()

    W, H = ffprobe_dims(source)
    print(f"Source {source} {W}x{H}; {len(segments)} clips -> {args.aspect} "
          f"(style={args.style}, tighten={args.tighten}) -> {out_dir}", flush=True)

    saved = []
    failed = 0
    for i, seg in enumerate(segments, 1):
        print(f"--- Clip {i}/{len(segments)}: "
              f"{seg.get('hook', '')[:60]!r} (overall {seg.get('overall')}) ---",
              flush=True)
        try:
            saved.append(str(render({**seg, "id": f"{i:03}"}, words, source, W, H, workdir, args.aspect,
                                    out_dir=out_dir, style=args.style,
                                    do_tighten=args.tighten, loudnorm=args.loudnorm,
                                    preview=args.preview, brand=brand,
                                    layout=args.layout, centers=args.centers,
                                    caption=caption)))
        except subprocess.CalledProcessError as e:
            print(f"ERROR rendering clip {i}: {e}", flush=True)
            failed += 1

    print("RENDERED", len(saved), "clips:", flush=True)
    for s in saved:
        print("  ", s, flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
