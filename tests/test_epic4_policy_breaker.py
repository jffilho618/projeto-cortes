"""Testes TDD Story 4.1 — Portão de Fontes, Políticas de Publisher e Disjuntor Global (Onda 4A)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories


def _make_db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{(tmp_path / 'e4_policy.db').as_posix()}")
    db.init_schema()
    return db


def test_publisher_policies_catalog_loads_and_syncs_to_db(tmp_path: Path):
    from picorte.risk_shield.policy_gate import load_publisher_policies, sync_publisher_policies

    db = _make_db(tmp_path)
    policies = load_publisher_policies()
    slugs = {p["game_slug"] for p in policies}
    assert {"gta6", "nintendo_general", "valorant", "cs2", "minecraft", "fortnite"}.issubset(slugs)

    synced = sync_publisher_policies(db)
    assert synced >= 6
    repos = PicorteRepositories(db)
    gta = repos.policies.get_by_game("gta6")
    assert gta is not None
    assert gta["publisher"] == "Rockstar Games"
    assert gta["has_licensed_radio_music"] is True
    assert gta["violence_check_strict"] is True


def test_policy_gate_blocks_unknown_blacklist_paused_and_expired_campaign(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError, assert_can_export, assert_can_ingest

    db = _make_db(tmp_path)
    repos = PicorteRepositories(db)

    src_unknown = repos.sources.create_source(
        name="Canal Novo", platform="youtube", channel_handle="@canalnovo", permission_status="desconhecida"
    )
    src_black = repos.sources.create_source(
        name="Canal Banido", platform="youtube", channel_handle="@banido", permission_status="lista_negra"
    )
    src_paused = repos.sources.create_source(
        name="Canal Claim", platform="youtube", channel_handle="@claim", permission_status="pausada_por_claim"
    )
    src_ok = repos.sources.create_source(
        name="Alanzoka", platform="youtube", channel_handle="@alanzoka", permission_status="liberada"
    )
    src_own = repos.sources.create_source(
        name="Bomba Gameplay", platform="local", channel_handle="@bombaclips4", permission_status="gameplay_proprio"
    )
    src_camp_exp = repos.sources.create_source(
        name="Campanha Velha", platform="twitch", channel_handle="@campvelha", permission_status="campanha_ativa"
    )
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    repos.campaigns.create_campaign(source_id=src_camp_exp["id"], game_slug="gta6", cpm_brl=12.0, expires_at=yesterday)

    src_camp_ok = repos.sources.create_source(
        name="Campanha Nova", platform="twitch", channel_handle="@campnova", permission_status="campanha_ativa"
    )
    next_week = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    repos.campaigns.create_campaign(source_id=src_camp_ok["id"], game_slug="gta6", cpm_brl=15.0, expires_at=next_week)

    # Fonte desconhecida, lista negra, pausada e campanha vencida DEVEM bloquear 100%
    for blocked in (src_unknown, src_black, src_paused, src_camp_exp):
        with pytest.raises(PolicyViolationError):
            assert_can_ingest(db, source_id=blocked["id"])
        with pytest.raises(PolicyViolationError):
            assert_can_export(db, source_id=blocked["id"])

    # Fonte None (não cadastrada) também bloqueia
    with pytest.raises(PolicyViolationError):
        assert_can_ingest(db, source_id=None, channel_handle="@naoexiste")

    # Liberada, gameplay_proprio e campanha ativa válida passam
    for allowed in (src_ok, src_own, src_camp_ok):
        res_in = assert_can_ingest(db, source_id=allowed["id"])
        res_ex = assert_can_export(db, source_id=allowed["id"])
        assert res_in["allowed"] is True
        assert res_ex["allowed"] is True


def test_policy_gate_checks_publisher_spoilers_leaks_and_nintendo_strict(tmp_path: Path):
    from picorte.risk_shield.policy_gate import evaluate_candidate_policy, sync_publisher_policies

    db = _make_db(tmp_path)
    sync_publisher_policies(db)

    # Vazamento/spoiler de GTA 6 dentro da janela de spoiler é bloqueado
    v_leak = evaluate_candidate_policy(
        db,
        game_slug="gta6",
        title="FINAL SECRETO VAZADO DO GTA 6 — MORTE DO PROTAGONISTA!",
        transcript_text="Olha esse leak do final do GTA 6 que vazou ontem",
        today=date(2026, 11, 20),
    )
    assert v_leak["status"] == "hard_block"
    assert any("spoiler" in r.lower() or "leak" in r.lower() or "vazamento" in r.lower() for r in v_leak["reasons"])

    # Clipe normal de gameplay do GTA 6 passa (sinalizando rádio licenciada)
    v_ok = evaluate_candidate_policy(
        db,
        game_slug="gta6",
        title="Alanzoka testa física dos carros no GTA 6",
        transcript_text="Olha a lama grudando no pneu, sensacional",
        today=date(2026, 11, 20),
    )
    assert v_ok["status"] == "pass"
    assert v_ok["requires_music_check"] is True

    # Nintendo (rigor extremo) exige revisão humana / bloqueio por padrão
    v_nint = evaluate_candidate_policy(
        db,
        game_slug="nintendo_general",
        title="Speedrun de Zelda sem tomar dano",
        transcript_text="Bora pro castelo de Hyrule",
        today=date(2026, 11, 20),
    )
    assert v_nint["status"] in {"human_review", "hard_block"}


def test_source_breaker_pauses_source_globally_and_cancels_queued_publications(tmp_path: Path):
    from picorte.risk_shield.policy_gate import PolicyViolationError, assert_can_export
    from picorte.risk_shield.source_breaker import pause_source_globally

    db = _make_db(tmp_path)
    repos = PicorteRepositories(db)
    src = repos.sources.create_source(
        name="Streamer Teste", platform="youtube", channel_handle="@streamerteste", permission_status="liberada"
    )
    vid = repos.videos.create_video(source_id=src["id"], source_url="https://yt/1", game_slug="gta6")
    clip = repos.clips.create_clip(video_id=vid["id"], start_sec=10.0, end_sec=40.0)
    pub_yt = repos.publications.create_publication(clip_id=clip["id"], platform="youtube_shorts", status="fila")
    pub_tt = repos.publications.create_publication(clip_id=clip["id"], platform="tiktok", status="agendado")
    pub_done = repos.publications.create_publication(clip_id=clip["id"], platform="instagram_reels", status="publicado")

    result = pause_source_globally(
        db,
        source_id=src["id"],
        claim_type="copyright_strike",
        details="Claim manual detectado no YouTube",
        publication_id=pub_done["id"],
    )

    assert result["source_status"] == "pausada_por_claim"
    assert result["paused_publications"] == 2
    assert result["claim_event_id"]

    # Publicações pendentes (fila/agendado) foram pausadas; já publicada mantém histórico
    rows = {r["id"]: r["status"] for r in db.fetch_all("SELECT id, status FROM publications")}
    assert rows[pub_yt["id"]] == "pausado_claim"
    assert rows[pub_tt["id"]] == "pausado_claim"
    assert rows[pub_done["id"]] == "publicado"

    # E o policy_gate agora barra imediatamente qualquer novo export dessa fonte
    with pytest.raises(PolicyViolationError):
        assert_can_export(db, source_id=src["id"])
