"""P5 (code review Épico 4) — copy_guard: alertas não somem, URL sem https, acentos em hashtag, título e comentário."""
from __future__ import annotations


def _audit(**kw):
    from picorte.risk_shield.copy_guard import audit_and_sanitize_copy

    return audit_and_sanitize_copy(**kw)


def test_auto_fix_does_not_hide_yellow_icon_warning():
    res = _audit(platform="tiktok", title="Ele mata todo mundo", description="veja #shorts")
    assert res["auto_fixed"] is True
    assert res["ad_friendly_warnings"]
    assert res["status"] == "human_review"


def test_mata_followed_by_punctuation_is_detected():
    res = _audit(platform="youtube_shorts", title="Ele mata!")
    assert any(w["term"] == "mata" for w in res["ad_friendly_warnings"])


def test_bare_domain_links_are_removed_on_tiktok():
    res = _audit(platform="tiktok", description="Live completa em youtube.com/@alanzoka\nMuito bom")
    assert "youtube.com" not in res["sanitized_description"]
    assert "Muito bom" in res["sanitized_description"]


def test_accented_hashtags_are_kept_whole():
    res = _audit(platform="youtube_shorts", description="corte bom #ação #gta6")
    assert res["sanitized_hashtags"] == ["#ação", "#gta6"]
    assert "ção" not in res["sanitized_description"].replace("#ação", "")


def test_title_is_sanitized_per_platform():
    res = _audit(platform="tiktok", title="Melhor momento #shorts twitch.tv/alanzoka")
    assert "#shorts" not in res["sanitized_title"]
    assert "twitch.tv" not in res["sanitized_title"]
    assert res["auto_fixed"] is True


def test_pinned_comment_is_sanitized_and_checked():
    res = _audit(platform="instagram_reels", pinned_comment="Assiste completo em youtu.be/xyz, ele mata demais")
    assert "youtu.be" not in res["pinned_comment"]
    assert any(w["term"] == "mata" for w in res["ad_friendly_warnings"])


def test_youtube_long_title_is_capped_at_100_chars():
    res = _audit(platform="youtube_long", title="palavra " * 30)
    assert len(res["sanitized_title"]) <= 100
