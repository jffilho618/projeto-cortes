"""Contrato canônico de Publicação Assistida e Multi-Streamer (PublishPayload — base do Épico 6).

Gera metadados nativos em PT-BR para YouTube Shorts, TikTok, Instagram Reels e Facebook Reels,
resolve a identidade/créditos do streamer (P1 + P2), e exporta o Pacote do Dia com agenda segura
(3 clipes/dia: 12h, 18h, 21h). 100% multiplataforma (Windows + Linux — AD-11).
"""
from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import re
import shutil
from typing import Any
import unicodedata

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "assets" / "streamers" / "registry.json"

PLATFORM_UPLOAD_URLS: dict[str, str] = {
    "youtube_shorts": "https://studio.youtube.com/",
    "tiktok": "https://www.tiktok.com/tiktokstudio/upload",
    "instagram_reels": "https://business.facebook.com/latest/reels_composer",
    "facebook_reels": "https://business.facebook.com/latest/reels_composer",
}

GAME_DISPLAY_MAP: dict[str, tuple[str, list[str]]] = {
    "gta6": ("GTA 6", ["#gta6", "#gtavi"]),
    "gta5": ("GTA 5", ["#gta5", "#gtav"]),
    "gtarp": ("GTA RP", ["#gtarp", "#gta"]),
    "valorant": ("Valorant", ["#valorant"]),
    "cs2": ("CS2", ["#cs2", "#counterstrike"]),
    "lol": ("League of Legends", ["#lol", "#leagueoflegends"]),
    "minecraft": ("Minecraft", ["#minecraft"]),
    "fortnite": ("Fortnite", ["#fortnite"]),
    "eldenring": ("Elden Ring", ["#eldenring"]),
    "residentevil": ("Resident Evil", ["#residentevil"]),
    "reddead2": ("Red Dead 2", ["#rdr2", "#reddead2"]),
}


def _norm_text(text: str | None) -> str:
    raw = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()


def _slugify(text: str | None, fallback: str = "streamer") -> str:
    norm = _norm_text(text)
    slug = re.sub(r"\s+", "-", norm).strip("-")
    return slug or fallback


def load_streamer_registry(registry_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    return {
        "channel_brand": {
            "name": "Bomba Clips",
            "handle": "@bombaclips4",
            "contact_email": "jffilho618@gmail.com",
        },
        "streamers": [],
    }


def resolve_streamer(
    *,
    channel_name: str | None = None,
    title: str | None = None,
    source_url: str | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve o autor do corte contra o cadastro de streamers (ou cria perfil limpo dinâmico)."""
    reg = registry or load_streamer_registry()
    streamers = list(reg.get("streamers") or [])

    # 1) Match exato ou por substring no nome do canal / título / URL
    haystacks = [_norm_text(channel_name), _norm_text(title), _norm_text(source_url)]
    for candidate in streamers:
        aliases = [
            _norm_text(candidate.get("display_name")),
            _norm_text(candidate.get("slug")),
            *(_norm_text(a) for a in (candidate.get("aliases") or [])),
        ]
        aliases = [a for a in aliases if a]
        for h in haystacks:
            if not h:
                continue
            for alias in aliases:
                if h == alias or re.search(rf"(?:^|\s){re.escape(alias)}(?:\s|$)", h):
                    return {
                        "slug": candidate.get("slug") or _slugify(candidate.get("display_name")),
                        "display_name": str(candidate.get("display_name") or "").upper(),
                        "accent_hex": str(candidate.get("accent_hex") or "#E11D2E"),
                        "twitch": str(candidate.get("twitch") or ""),
                        "youtube": str(candidate.get("youtube") or ""),
                        "handle": str(candidate.get("handle") or f"@{_slugify(candidate.get('display_name'))}"),
                        "registered": True,
                    }

    raw_name = str(channel_name or "").strip()
    if raw_name:
        clean_handle = "@" + re.sub(r"[^a-zA-Z0-9_.]", "", raw_name.replace(" ", "")).lower()
        return {
            "slug": _slugify(raw_name),
            "display_name": raw_name.upper()[:24],
            "accent_hex": "#E11D2E",
            "twitch": "",
            "youtube": "",
            "handle": clean_handle if len(clean_handle) > 1 else "",
            "registered": False,
        }

    return {
        "slug": "games",
        "display_name": "",
        "accent_hex": "#E11D2E",
        "twitch": "",
        "youtube": "",
        "handle": "",
        "registered": False,
    }


def _resolve_game_info(source_meta: dict[str, Any] | None, title: str = "") -> tuple[str, list[str]]:
    sm = source_meta or {}
    raw_game = _norm_text(sm.get("detected_game") or sm.get("game") or "")
    combined = f"{raw_game} {_norm_text(sm.get('title'))} {_norm_text(title)}"

    for key, (label, tags) in GAME_DISPLAY_MAP.items():
        if key in raw_game.replace(" ", "") or key in combined.replace(" ", ""):
            return label, list(tags)
    if "grand theft auto 6" in combined or "gta vi" in combined or "gta 6" in combined:
        return "GTA 6", ["#gta6", "#gtavi"]
    if "grand theft auto" in combined:
        return "GTA", ["#gta"]
    if raw_game:
        tag = "#" + re.sub(r"\s+", "", raw_game)
        return raw_game.title(), [tag]
    return "Games", ["#games"]


def _clean_title(text: str, max_len: int = 90) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    cleaned = re.sub(r"\s+#shorts\b", "", cleaned, flags=re.IGNORECASE).strip()
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[: max_len - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return (cut or cleaned[: max_len - 1]) + "…"


def _dedupe_hashtags(tags: list[str], limit: int = 5) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in tags:
        clean = str(t or "").strip().lower()
        if not clean:
            continue
        if not clean.startswith("#"):
            clean = "#" + re.sub(r"[^a-z0-9]", "", clean)
        if len(clean) <= 1 or clean in seen:
            continue
        seen.add(clean)
        out.append(clean)
        if len(out) >= limit:
            break
    return out


def build_publish_kit(
    seg: dict[str, Any],
    *,
    source_meta: dict[str, Any] | None = None,
    mp4_path: str | Path = "",
    thumb_path: str | Path = "",
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Constrói o PublishPayload canônico para as 4 redes (usado hoje na UI assistida e no Épico 6 via OAuth)."""
    reg = registry or load_streamer_registry()
    brand = reg.get("channel_brand") or {}
    brand_name = str(brand.get("name") or "Bomba Clips")
    contact_email = str(brand.get("contact_email") or "jffilho618@gmail.com")

    sm = source_meta or {}
    hook_fallback = str(seg.get("hook") or "Corte de games").replace("-", " ").strip().capitalize()
    base_title = str(seg.get("proposed_title") or seg.get("title") or hook_fallback).strip()
    yt_title = _clean_title(base_title, max_len=90)
    pinned_comment = str(seg.get("pinned_comment_debate") or "").strip()

    streamer = resolve_streamer(
        channel_name=sm.get("channel") or sm.get("uploader"),
        title=f"{sm.get('title') or ''} {base_title}",
        source_url=sm.get("source_url") or sm.get("url"),
        registry=reg,
    )
    game_label, game_tags = _resolve_game_info(sm, base_title)

    streamer_name_title = streamer["display_name"].title() if streamer["display_name"] else ""
    streamer_tag = f"#{streamer['slug'].replace('-', '')}" if streamer["slug"] and streamer["slug"] != "games" else ""

    yt_tags = _dedupe_hashtags(["#shorts", *game_tags, streamer_tag, "#games"], limit=5)
    tt_tags = _dedupe_hashtags([*game_tags, streamer_tag, "#games", "#clips"], limit=5)
    ig_tags = _dedupe_hashtags([*game_tags, streamer_tag, "#reels", "#games"], limit=5)
    fb_tags = _dedupe_hashtags([*game_tags, streamer_tag, "#games", "#reels"], limit=5)

    # Bloco de créditos oficiais (P1)
    credit_lines: list[str] = []
    if streamer_name_title:
        credit_lines.append(f"🎬 Créditos — {streamer_name_title}:")
        if streamer["twitch"]:
            credit_lines.append(f"• Twitch: {streamer['twitch']}")
        if streamer["youtube"]:
            credit_lines.append(f"• YouTube: {streamer['youtube']}")
        if not streamer["twitch"] and not streamer["youtube"] and streamer["handle"]:
            credit_lines.append(f"• Canal oficial: {streamer['handle']}")
    credits_block = "\n".join(credit_lines)

    yt_desc_parts = [
        yt_title,
        f"Se curtiu o corte, deixa o like e se inscreve no {brand_name} pra mais momentos de {game_label}!",
    ]
    if credits_block:
        yt_desc_parts.append(credits_block)
    yt_desc_parts.append(
        f"⚠️ Canal de cortes feito por fãs, sem vínculo oficial com o criador. "
        f"Para remoção imediata ou contato: {contact_email}"
    )
    yt_desc_parts.append(" ".join(yt_tags))
    yt_description = "\n\n".join(yt_desc_parts)

    short_credit = f"Créditos: {streamer['handle'] or streamer_name_title}" if (streamer["handle"] or streamer_name_title) else ""

    tt_lines = [yt_title]
    if short_credit:
        tt_lines.append(short_credit)
    tt_lines.append(" ".join(tt_tags))
    tt_description = "\n".join(tt_lines)

    ig_lines = [yt_title]
    if pinned_comment:
        ig_lines.append(f"👇 {pinned_comment}")
    if short_credit:
        ig_lines.append(short_credit)
    ig_lines.append(" ".join(ig_tags))
    ig_description = "\n\n".join(ig_lines)

    fb_lines = [yt_title]
    if pinned_comment:
        fb_lines.append(pinned_comment)
    if short_credit:
        fb_lines.append(short_credit)
    fb_lines.append(" ".join(fb_tags))
    fb_description = "\n\n".join(fb_lines)

    mp4_str = str(mp4_path) if mp4_path else ""
    thumb_str = str(thumb_path) if thumb_path else ""

    def _entry(platform: str, desc: str, tags: list[str]) -> dict[str, Any]:
        from picorte.risk_shield.copy_guard import audit_and_sanitize_copy

        credit_val = streamer["handle"] or streamer_name_title
        audit = audit_and_sanitize_copy(
            platform=platform,
            title=yt_title,
            description=desc,
            hashtags=tags,
            context_banner_2s=str(seg.get("context_banner_2s") or ""),
            pinned_comment=pinned_comment,
            source_credit=credit_val,
        )
        return {
            "platform": platform,
            "title": audit["sanitized_title"],
            "description": audit["sanitized_description"],
            "hashtags": audit["sanitized_hashtags"],
            "pinned_comment": audit["pinned_comment"],
            "upload_url": PLATFORM_UPLOAD_URLS[platform],
            "video_path": mp4_str,
            "thumb_path": thumb_str,
            "source_credit": credit_val,
            "copy_audit": {
                "status": audit["status"],
                "fixes": audit["fixes"],
                "ad_friendly_warnings": audit["ad_friendly_warnings"],
            },
        }

    return {
        "schema_version": 1,
        "brand_name": brand_name,
        "contact_email": contact_email,
        "streamer": streamer,
        "game": game_label,
        "archetype": seg.get("archetype") or "",
        "tier": seg.get("tier") or "",
        "platforms": {
            "youtube_shorts": _entry("youtube_shorts", yt_description, yt_tags),
            "tiktok": _entry("tiktok", tt_description, tt_tags),
            "instagram_reels": _entry("instagram_reels", ig_description, ig_tags),
            "facebook_reels": _entry("facebook_reels", fb_description, fb_tags),
        },
    }


def _format_copy_txt(kit: dict[str, Any], slot_label: str) -> str:
    p = kit["platforms"]
    yt = p["youtube_shorts"]
    tt = p["tiktok"]
    ig = p["instagram_reels"]
    fb = p["facebook_reels"]
    lines = [
        f"=== {kit['brand_name'].upper()} · AGENDA SUGERIDA: {slot_label} ===",
        f"Streamer: {kit['streamer'].get('display_name') or 'Games'} | Jogo: {kit['game']}",
        "",
        "---------------- YOUTUBE SHORTS ----------------",
        f"TÍTULO:\n{yt['title']}",
        "",
        f"DESCRIÇÃO:\n{yt['description']}",
        "",
        f"1º COMENTÁRIO FIXADO:\n{yt['pinned_comment'] or '(sem pergunta gerada)'}",
        "",
        "------------------- TIKTOK ---------------------",
        tt["description"],
        "",
        "--------------- INSTAGRAM REELS ----------------",
        ig["description"],
        "",
        "--------------- FACEBOOK REELS -----------------",
        fb["description"],
        "",
    ]
    return "\n".join(lines)


def export_daily_bundle(
    project_dir: Path | str,
    *,
    clip_stems: list[str] | None = None,
    out_root: Path | str | None = None,
    per_day: int = 3,
    slots: tuple[str, ...] = ("12h", "18h", "21h"),
    registry: dict[str, Any] | None = None,
    db: Any = None,
    cadence_state_path: Path | str | None = None,
) -> dict[str, Any]:
    """Exporta um Pacote do Dia organizado nos horários seguros (3/dia) com 1 mp4 + 1 thumb + 1 _COPIAR.txt por clipe.

    Portão P1 Pre-Export: revalida a permissão da fonte agora, exporta só cortes auditados (sem `hard_block`),
    marca `human_review` com prefixo REVISAR_ e avisa redes em Cool-Down/teto de cadência no _COPIAR.txt.
    """
    from picorte.risk_shield.cadence_guard import check_cadence
    from picorte.risk_shield.pipeline import EXPORTABLE_STATUSES
    from picorte.risk_shield.policy_gate import PolicyViolationError, assert_can_export

    if db is None:
        from picorte.db.connection import get_default_db

        db = get_default_db()
    pdir = Path(project_dir).resolve()
    clips_dir = pdir / "clips"
    if not clips_dir.is_dir():
        raise FileNotFoundError(f"Pasta de clipes não encontrada em {pdir}")

    proj_state = {}
    proj_json = pdir / "project.json"
    if proj_json.is_file():
        proj_state = json.loads(proj_json.read_text(encoding="utf-8"))
    source_meta = proj_state.get("source_meta") or {}

    source_id = (proj_state.get("source_gate") or {}).get("source_id")
    if not source_id:
        raise PolicyViolationError(
            "[P1:pre_export] Projeto sem fonte vinculada (portão Pre-Ingest não registrado). Nada foi exportado.",
            code="source_unlinked",
        )
    assert_can_export(db, source_id=source_id)

    cadence_blocked: dict[str, str] = {}
    for plat in ("youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"):
        cad = check_cadence(db, platform=plat, state_path=cadence_state_path)
        if cad.get("status") == "block":
            cadence_blocked[plat] = str(cad.get("reason") or "limite de cadência")

    all_mp4s = sorted(clips_dir.glob("*.mp4"))
    if clip_stems:
        wanted = set(clip_stems)
        all_mp4s = [m for m in all_mp4s if m.stem in wanted]
    if not all_mp4s:
        raise ValueError("Nenhum clipe exportado encontrado para montar o Pacote do Dia.")

    base_root = Path(out_root).resolve() if out_root else (PROJECT_ROOT / "prontos_para_postar")
    day_stamp = date.today().isoformat()
    bundle_dir = base_root / f"{day_stamp}_{pdir.name[:8]}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    per_day = max(1, int(per_day))
    slot_list = list(slots) if slots else ["12h", "18h", "21h"]
    exported_files: list[dict[str, Any]] = []
    skipped_blocked: list[str] = []

    export_idx = 0
    for mp4 in all_mp4s:
        stem = mp4.stem
        meta_file = clips_dir / f"{stem}.meta.json"
        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.is_file() else {"hook": stem}
        risk_st = str(meta.get("risk_status") or (meta.get("risk_verdict") or {}).get("overall_status") or "").lower()
        if risk_st not in EXPORTABLE_STATUSES:  # sem veredito, erro de auditoria ou bloqueado: não sai
            skipped_blocked.append(stem)
            continue
        needs_review = risk_st == "human_review"
        idx = export_idx
        export_idx += 1
        thumb_src = clips_dir / f"{stem}_thumb.png"
        if not thumb_src.is_file():
            fallback_png = clips_dir / f"{stem}.png"
            thumb_src = fallback_png if fallback_png.is_file() else thumb_src

        kit = meta.get("publish_kit")
        if not isinstance(kit, dict) or "platforms" not in kit:
            kit = build_publish_kit(
                meta,
                source_meta=source_meta,
                mp4_path=mp4,
                thumb_path=thumb_src if thumb_src.is_file() else "",
                registry=registry,
            )

        day_num = (idx // per_day) + 1
        slot = slot_list[(idx % per_day) % len(slot_list)]
        streamer_slug = kit["streamer"].get("slug") or "games"
        short_slug = _slugify(meta.get("proposed_title") or stem, fallback=stem)[:36]
        prefix = f"{idx + 1:02d}_D{day_num}_{slot}_{streamer_slug}_{short_slug}"
        if needs_review:
            prefix = f"REVISAR_{prefix}"

        dst_mp4 = bundle_dir / f"{prefix}.mp4"
        shutil.copy2(mp4, dst_mp4)

        dst_thumb = None
        if thumb_src.is_file():
            dst_thumb = bundle_dir / f"{prefix}_thumb.png"
            shutil.copy2(thumb_src, dst_thumb)

        dst_txt = bundle_dir / f"{prefix}_COPIAR.txt"
        warn_lines = [
            f"⛔ NÃO POSTAR em {plat.replace('_', ' ').upper()} agora: {why}" for plat, why in cadence_blocked.items()
        ]
        if needs_review:
            warn_lines.insert(0, "🟠 REVISAR antes de postar: o escudo P1 pediu olho humano neste corte.")
        header = ("\n".join(warn_lines) + "\n\n") if warn_lines else ""
        dst_txt.write_text(header + _format_copy_txt(kit, f"Dia {day_num} · {slot}"), encoding="utf-8")

        exported_files.append({
            "stem": stem,
            "slot": f"D{day_num} {slot}",
            "mp4": str(dst_mp4),
            "thumb": str(dst_thumb) if dst_thumb else None,
            "copy_txt": str(dst_txt),
            "risk_status": risk_st,
            "needs_review": needs_review,
        })

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_id": pdir.name,
        "count": len(exported_files),
        "per_day": per_day,
        "skipped_blocked": skipped_blocked,
        "cadence_blocked": cadence_blocked,
        "files": exported_files,
    }
    (bundle_dir / "AGENDA.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "bundle_dir": str(bundle_dir),
        "count": len(exported_files),
        "skipped_blocked": skipped_blocked,
        "cadence_blocked": cadence_blocked,
        "files": exported_files,
    }
