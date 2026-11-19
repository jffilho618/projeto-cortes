from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np


def _resolve_ffmpeg() -> str:
    local = Path(".venv/bin/ffmpeg")
    if local.is_file():
        return str(local.resolve())
    return "ffmpeg"


def _add_subtle_inner_atmosphere(canvas: np.ndarray) -> np.ndarray:
    """Bring subtle dark-crimson smoke wisps and soft white energy arcs into safe-band flanks."""
    h, w = canvas.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Subtle dark-wine smoke clouds along left & right flanks of the 2560x423 / 1546x423 band
    smoke_mask = np.zeros((h, w), dtype=np.float32)
    clouds = [
        (430, 560, 260, 140, 0.38),
        (540, 860, 220, 120, 0.30),
        (2130, 570, 270, 145, 0.38),
        (2020, 875, 240, 130, 0.34),
        (1820, 535, 190, 95, 0.22),
        (820, 910, 210, 95, 0.22),
    ]
    for cx, cy, rx, ry, strength in clouds:
        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        smoke_mask += np.exp(-d * 1.45) * strength
    smoke_mask = np.clip(smoke_mask, 0.0, 0.58)[:, :, None]
    smoke_color = np.array([28.0, 6.0, 52.0], dtype=np.float32).reshape((1, 1, 3))
    out = canvas * (1.0 - smoke_mask) + smoke_color * smoke_mask
    return out


def build() -> None:
    bg_src = Path("canais/bomba-clips/banner/banner-background-limpo-2560x1440.png")
    mascot_src = Path("canais/bomba-clips/avatar/mascote-bomba-transparente.png")
    out_dir = Path("canais/bomba-clips/banner")
    out_dir.mkdir(parents=True, exist_ok=True)

    bg = cv2.imdecode(np.fromfile(str(bg_src), dtype=np.uint8), cv2.IMREAD_COLOR)
    bg_2560 = cv2.resize(bg, (2560, 1440), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    canvas = _add_subtle_inner_atmosphere(bg_2560)

    # Render crisp vector lockup (BOMBA CLIPS + 5 social sticker icons + @BOMBACLIPS)
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="2560" height="1440" viewBox="0 0 2560 1440">
  <defs>
    <linearGradient id="igGrad" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#feda75"/>
      <stop offset="25%" stop-color="#fa7e1e"/>
      <stop offset="55%" stop-color="#d62976"/>
      <stop offset="80%" stop-color="#962fbf"/>
      <stop offset="100%" stop-color="#4f5bd5"/>
    </linearGradient>
  </defs>

  <g transform="translate(1430, 700) rotate(-2.2)">
    <text x="8" y="11" text-anchor="middle" font-family="Ubuntu, sans-serif" font-weight="900" font-style="italic" letter-spacing="-3" font-size="146" fill="#0a0a0d" stroke="#0a0a0d" stroke-width="26" stroke-linejoin="round">BOMBA CLIPS</text>
    <text x="0" y="0" text-anchor="middle" font-family="Ubuntu, sans-serif" font-weight="900" font-style="italic" letter-spacing="-3" font-size="146" fill="#ffffff" stroke="#0a0a0d" stroke-width="22" stroke-linejoin="round" paint-order="stroke">BOMBA CLIPS</text>
  </g>

  <g transform="translate(965, 772)">
    <g transform="translate(0, 0)">
      <rect x="3" y="4" width="64" height="64" rx="16" fill="#0a0a0d"/>
      <rect x="0" y="0" width="64" height="64" rx="16" fill="url(#igGrad)" stroke="#0a0a0d" stroke-width="6"/>
      <rect x="15" y="15" width="34" height="34" rx="10" fill="none" stroke="#ffffff" stroke-width="4.5"/>
      <circle cx="32" cy="32" r="8.5" fill="none" stroke="#ffffff" stroke-width="4.5"/>
      <circle cx="42.5" cy="21.5" r="2.8" fill="#ffffff"/>
    </g>

    <g transform="translate(78, 0)">
      <rect x="3" y="4" width="64" height="64" rx="16" fill="#0a0a0d"/>
      <rect x="0" y="0" width="64" height="64" rx="16" fill="#111318" stroke="#0a0a0d" stroke-width="6"/>
      <path d="M37 15v23a8.5 8.5 0 1 1-6.5-8.2v5.8a3.5 3.5 0 1 0 2.5 3.4V15h5.2c1.2 4.5 4.4 7.7 8.8 8.7v5.5c-4-.4-7.5-2-10-4.7z" transform="translate(-2,1)" fill="#25f4ee"/>
      <path d="M37 15v23a8.5 8.5 0 1 1-6.5-8.2v5.8a3.5 3.5 0 1 0 2.5 3.4V15h5.2c1.2 4.5 4.4 7.7 8.8 8.7v5.5c-4-.4-7.5-2-10-4.7z" transform="translate(2,-1)" fill="#fe2c55"/>
      <path d="M37 15v23a8.5 8.5 0 1 1-6.5-8.2v5.8a3.5 3.5 0 1 0 2.5 3.4V15h5.2c1.2 4.5 4.4 7.7 8.8 8.7v5.5c-4-.4-7.5-2-10-4.7z" fill="#ffffff"/>
    </g>

    <g transform="translate(156, 0)">
      <rect x="3" y="4" width="64" height="64" rx="16" fill="#0a0a0d"/>
      <rect x="0" y="0" width="64" height="64" rx="16" fill="#1877f2" stroke="#0a0a0d" stroke-width="6"/>
      <path d="M36 53V34h6.4l1-7.4H36v-4.7c0-2.1.6-3.6 3.7-3.6h4V11.7c-.7-.1-3-.3-5.7-.3-5.6 0-9.5 3.4-9.5 9.8v5.4h-6.4V34h6.4v19z" fill="#ffffff"/>
    </g>

    <g transform="translate(234, 0)">
      <rect x="3" y="4" width="64" height="64" rx="16" fill="#0a0a0d"/>
      <rect x="0" y="0" width="64" height="64" rx="16" fill="#ff5a00" stroke="#0a0a0d" stroke-width="6"/>
      <rect x="14" y="21" width="24" height="22" rx="6" fill="#ffffff"/>
      <polygon points="40,26 51,20 51,44 40,38" fill="#ffffff"/>
      <circle cx="22" cy="17" r="5.5" fill="#ffffff"/>
      <circle cx="33" cy="17" r="4.5" fill="#ffffff"/>
    </g>

    <g transform="translate(312, 0)">
      <rect x="3" y="4" width="82" height="64" rx="16" fill="#0a0a0d"/>
      <rect x="0" y="0" width="82" height="64" rx="16" fill="#ff0000" stroke="#0a0a0d" stroke-width="6"/>
      <polygon points="33,19 33,45 55,32" fill="#ffffff"/>
    </g>

    <g transform="translate(418, 49)">
      <text x="4" y="5" font-family="Ubuntu Sans, sans-serif" font-weight="900" font-size="48" letter-spacing="1" fill="#0a0a0d" stroke="#0a0a0d" stroke-width="11" stroke-linejoin="round">@BOMBACLIPS</text>
      <text x="0" y="0" font-family="Ubuntu Sans, sans-serif" font-weight="900" font-size="48" letter-spacing="1" fill="#ffffff" stroke="#0a0a0d" stroke-width="10" stroke-linejoin="round" paint-order="stroke">@BOMBACLIPS</text>
    </g>
  </g>
</svg>"""
    svg_path = Path("/tmp/bomba_lockup.svg")
    overlay_png = Path("/tmp/bomba_lockup.png")
    svg_path.write_text(svg, encoding="utf-8")
    subprocess.run([_resolve_ffmpeg(), "-y", "-i", str(svg_path), "-vframes", "1", str(overlay_png)], check=True, capture_output=True)

    ov = cv2.imread(str(overlay_png), cv2.IMREAD_UNCHANGED).astype(np.float32)
    ov_a = ov[:, :, 3:4] / 255.0
    canvas = ov[:, :, :3] * ov_a + canvas * (1.0 - ov_a)

    # Pad mascot cleanly with 40px transparent margin BEFORE rotating so glasses stem never clips
    mascot = cv2.imdecode(np.fromfile(str(mascot_src), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    mh, mw = mascot.shape[:2]
    target_h = 370
    target_w = int(round(mw * target_h / mh))
    mascot_res = cv2.resize(mascot, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    pad = 40
    padded = cv2.copyMakeBorder(mascot_res, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    ph, pw = padded.shape[:2]
    M = cv2.getRotationMatrix2D((pw / 2.0, ph / 2.0), 4.0, 1.0)
    mascot_rot = cv2.warpAffine(padded, M, (pw, ph), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

    mx, my = 605 - pad, 535 - pad
    sh_alpha = cv2.GaussianBlur(mascot_rot[:, :, 3].astype(np.float32) / 255.0, (25, 25), 9.0) * 0.55
    sx, sy = mx + 10, my + 14
    roi_s = canvas[sy:sy + ph, sx:sx + pw]
    canvas[sy:sy + ph, sx:sx + pw] = roi_s * (1.0 - sh_alpha[:, :, None])

    m_a = mascot_rot[:, :, 3:4].astype(np.float32) / 255.0
    roi_m = canvas[my:my + ph, mx:mx + pw]
    canvas[my:my + ph, mx:mx + pw] = mascot_rot[:, :, :3].astype(np.float32) * m_a + roi_m * (1.0 - m_a)

    final = np.clip(canvas, 0, 255).astype(np.uint8)
    final_path = out_dir / "banner-youtube-2560x1440.png"
    ok, fbuf = cv2.imencode(".png", final)
    assert ok
    final_path.write_bytes(fbuf.tobytes())

    # Safe-zone inspection outputs
    sim = (final.astype(np.float32) * 0.42).astype(np.uint8)
    sim[508:931, :] = final[508:931, :]
    cv2.rectangle(sim, (0, 508), (2559, 931), (255, 220, 0), 3)
    cv2.rectangle(sim, (507, 508), (2053, 931), (0, 212, 255), 5)
    ok2, sbuf = cv2.imencode(".png", sim)
    assert ok2
    (out_dir / "banner-youtube-safezone-check.png").write_bytes(sbuf.tobytes())

    mob = final[508:931, 507:2053]
    ok3, mbuf = cv2.imencode(".png", mob)
    assert ok3
    (out_dir / "banner-youtube-mobile-preview.png").write_bytes(mbuf.tobytes())

    # Facebook cover 851x315 derived proportionally from the centered safe band
    fb_crop = final[490:1010, 550:2030]
    fb_cover = cv2.resize(fb_crop, (851, 315), interpolation=cv2.INTER_LANCZOS4)
    ok4, fbbuf = cv2.imencode(".png", fb_cover)
    assert ok4
    (out_dir / "capa-facebook-851x315.png").write_bytes(fbbuf.tobytes())
    print("DONE:", final_path, "FB:", (out_dir / "capa-facebook-851x315.png"))


if __name__ == "__main__":
    build()
