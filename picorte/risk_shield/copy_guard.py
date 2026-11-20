"""Story 4.2 — Copy Hygiene Guard por Rede (P1/P2: evita bloqueio 'Conteúdo não original' no TikTok e ícone amarelo)."""
from __future__ import annotations

import re
from typing import Any
import unicodedata

# Termos sensíveis que frequentemente disparam ícone amarelo / limitação de anúncios em títulos e faixas
YELLOW_ICON_TERMS: dict[str, str] = {
    "suicidio": "desistir",
    "se matar": "ir de base",
    "matar": "eliminar / abater",
    "mata": "elimina / derruba",
    "morto": "abatido",
    "sangue": "dano / caos",
    "gore": "cena pesada",
    "nudez": "cena ousada",
    "pelado": "sem roupa",
    "pelada": "sem roupa",
    "droga": "item proibido",
    "cocaina": "item proibido",
    "tiroteio": "trocação",
    "massacre": "caos total",
    "terrorista": "inimigo",
}

CROSS_PLATFORM_FORBIDDEN: dict[str, list[str]] = {
    "tiktok": ["#shorts", "#reels", "youtube.com", "youtu.be", "twitch.tv", "instagram.com", "canal de cortes"],
    "instagram_reels": ["#shorts", "#fyp", "#tiktok", "youtube.com", "youtu.be", "twitch.tv", "tiktok.com", "canal de cortes"],
    "facebook_reels": ["#shorts", "#fyp", "#tiktok", "youtube.com", "youtu.be", "twitch.tv", "tiktok.com"],
    "youtube_shorts": ["#fyp", "#tiktok", "#reels", "tiktok.com"],
    "youtube_long": ["#fyp", "#tiktok", "#reels", "#shorts", "tiktok.com"],
}


# Links de redes concorrentes com ou sem "https://" (ex.: "youtube.com/@canal", "youtu.be/xyz").
_PLATFORM_LINK_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be|twitch\.tv|instagram\.com|tiktok\.com|kick\.com)"
    r"(?:/[^\s,;!?]*)?",
    re.IGNORECASE,
)
_ANY_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_HASHTAG_RE = re.compile(r"#\w+")
NATIVE_ONLY_PLATFORMS = {"tiktok", "instagram_reels", "facebook_reels"}
TITLE_LIMITS = {"youtube_shorts": 95, "youtube_long": 100}


def _scrub_inline(text: str, plat: str, forbidden: list[str]) -> str:
    """Remove hashtags e links proibidos para a rede dentro de um texto de linha única (título/comentário)."""
    out = str(text or "")
    for token in forbidden:
        if token.startswith("#"):
            out = re.sub(rf"(?i){re.escape(token)}(?!\w)", "", out)
        elif "." in token:
            out = re.sub(rf"(?i)(?:https?://)?[^\s]*{re.escape(token)}[^\s,;!?]*", "", out)
    if plat in NATIVE_ONLY_PLATFORMS:
        out = _PLATFORM_LINK_RE.sub("", out)
        out = _ANY_URL_RE.sub("", out)
    out = re.sub(r"\s+([,.;!?])", r"\1", out)
    return re.sub(r"[ \t]{2,}", " ", out).strip(" ,;")


def _norm(text: str | None) -> str:
    raw = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", raw.lower()).strip()


def _detect_yellow_icon_warnings(text: str) -> list[dict[str, str]]:
    normed = f" {_norm(text)} "
    warnings: list[dict[str, str]] = []
    seen: set[str] = set()
    for term, suggestion in YELLOW_ICON_TERMS.items():
        clean_term = term.strip()
        if clean_term in seen:
            continue
        if re.search(rf"(?:^|\W){re.escape(clean_term)}(?:\W|$)", normed):
            seen.add(clean_term)
            warnings.append({"term": clean_term, "suggestion": suggestion.strip()})
    return warnings


def audit_and_sanitize_copy(
    *,
    platform: str,
    title: str = "",
    description: str = "",
    hashtags: list[str] | None = None,
    context_banner_2s: str = "",
    pinned_comment: str = "",
    source_credit: str = "",
    max_hashtags: int = 5,
) -> dict[str, Any]:
    """Audita e higieniza copy especificamente para a rede destino (P1 + P2)."""
    plat = str(platform or "youtube_shorts").strip().lower()
    forbidden = CROSS_PLATFORM_FORBIDDEN.get(plat, [])
    fixes: list[str] = []

    raw_desc = str(description or "")
    sanitized_desc = raw_desc

    # 1) Em TikTok / Reels / Facebook: remove URLs externas e frases de 'canal de cortes' que disparam filtro 'não original'
    if plat in {"tiktok", "instagram_reels", "facebook_reels"}:
        lines = sanitized_desc.splitlines()
        kept_lines: list[str] = []
        for line in lines:
            low_line = _norm(line)
            if _ANY_URL_RE.search(line) or _PLATFORM_LINK_RE.search(line):
                fixes.append("removed_external_url_line")
                continue
            if "canal de cortes" in low_line:
                cleaned_line = re.sub(r"canal de cortes[^.!\n]*[.!]?", "", line, flags=re.IGNORECASE).strip()
                fixes.append("removed_clip_channel_phrase")
                if cleaned_line:
                    kept_lines.append(cleaned_line)
                continue
            kept_lines.append(line)
        sanitized_desc = "\n".join(kept_lines)

    # 2) Remove menções/hashtags proibidas de plataformas concorrentes na descrição
    for token in forbidden:
        if token.startswith("#"):
            new_desc = re.sub(rf"(?i){re.escape(token)}\b", "", sanitized_desc)
            if new_desc != sanitized_desc:
                fixes.append(f"removed_cross_tag:{token}")
                sanitized_desc = new_desc
        elif "." in token:
            new_desc = re.sub(rf"(?i)(?:https?://)?[^\s]*{re.escape(token)}[^\s]*", "", sanitized_desc)
            if new_desc != sanitized_desc:
                fixes.append(f"removed_cross_url:{token}")
                sanitized_desc = new_desc

    # 3) Extrai, limpa e limita hashtags (<= max_hashtags)
    raw_tags = list(hashtags or [])
    if not raw_tags:
        raw_tags = _HASHTAG_RE.findall(sanitized_desc)
    forbidden_tags = {t.lower() for t in forbidden if t.startswith("#")}
    clean_tags: list[str] = []
    seen_tags: set[str] = set()
    for tag in raw_tags:
        t = str(tag or "").strip().lower()
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + re.sub(r"[^\w]", "", t)
        if t in forbidden_tags:
            fixes.append(f"dropped_hashtag:{t}")
            continue
        if t not in seen_tags and len(t) > 1:
            seen_tags.add(t)
            clean_tags.append(t)
    if len(clean_tags) > max_hashtags:
        fixes.append(f"trimmed_hashtags:{len(clean_tags)}->{max_hashtags}")
        clean_tags = clean_tags[:max_hashtags]

    # Remove hashtags antigas soltas no corpo e reanexa a linha limpa no final
    body_no_tags = _HASHTAG_RE.sub("", sanitized_desc)
    body_no_tags = re.sub(r"[ \t]{2,}", " ", body_no_tags)
    body_no_tags = re.sub(r"\n{3,}", "\n\n", body_no_tags).strip()

    # Garante crédito nativo (@handle) sem citar concorrente quando source_credit foi informado
    credit = str(source_credit or "").strip()
    if credit and credit.lower() not in body_no_tags.lower():
        if plat in {"tiktok", "instagram_reels", "facebook_reels"}:
            body_no_tags = f"{body_no_tags}\nCréditos: {credit}".strip()
            fixes.append("ensured_native_credit")

    if clean_tags:
        sanitized_desc = f"{body_no_tags}\n{' '.join(clean_tags)}".strip()
    else:
        sanitized_desc = body_no_tags

    # 4) Título e 1º comentário também são higienizados para a rede; título respeita o limite da rede
    raw_title = re.sub(r"\s+", " ", str(title or "")).strip()
    sanitized_title = _scrub_inline(raw_title, plat, forbidden)
    if sanitized_title != raw_title:
        fixes.append("sanitized_title")
    limit = TITLE_LIMITS.get(plat)
    if limit and len(sanitized_title) > limit:
        sanitized_title = sanitized_title[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
        fixes.append(f"trimmed_title_{limit}")
    raw_pinned = str(pinned_comment or "").strip()
    sanitized_pinned = _scrub_inline(raw_pinned, plat, forbidden)
    if sanitized_pinned != raw_pinned:
        fixes.append("sanitized_pinned_comment")

    # 5) Alerta de palavras de ícone amarelo (título + faixa 2s + 1º comentário)
    ad_warnings = _detect_yellow_icon_warnings(f"{sanitized_title} {context_banner_2s} {sanitized_pinned}")

    # Deduplica lista de fixes mantendo ordem; alerta de ícone amarelo nunca é mascarado por auto-correção
    unique_fixes = list(dict.fromkeys(fixes))
    status = "human_review" if ad_warnings else ("auto_fixed" if unique_fixes else "pass")

    return {
        "gate": "copy_hygiene",
        "platform": plat,
        "status": status,
        "auto_fixed": bool(unique_fixes),
        "fixes": unique_fixes,
        "sanitized_title": sanitized_title,
        "sanitized_description": sanitized_desc,
        "sanitized_hashtags": clean_tags,
        "pinned_comment": sanitized_pinned,
        "ad_friendly_warnings": ad_warnings,
    }
