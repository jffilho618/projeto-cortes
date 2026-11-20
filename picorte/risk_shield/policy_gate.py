"""Story 4.1 — Portão de Status da Fonte e Políticas por Publisher/Jogo (Hard Gate P1, zero bypass)."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
import unicodedata

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICIES_PATH = PROJECT_ROOT / "assets" / "policies" / "publishers.json"

ALLOWED_PERMISSION_STATUSES = {"liberada", "contrato", "campanha_ativa", "gameplay_proprio"}
BLOCKED_PERMISSION_STATUSES = {"desconhecida", "lista_negra", "pausada_por_claim", "pausada_emergencia", "expirada"}

LEAK_TERMS = (
    "leak",
    "leaked",
    "vazado",
    "vazamento",
    "datamine",
    "datamined",
    "build vazada",
    "rom vazada",
    "emulador switch",
)
SPOILER_ENDING_TERMS = (
    "final secreto",
    "final do jogo",
    "ending",
    "ultimo chefe",
    "chefe final",
    "final boss",
    "morte do protagonista",
    "morte da protagonista",
    "morte do jason",
    "morte da lucia",
    "cutscene final",
    "cena pos creditos",
    "cena pos-creditos",
)
CHEAT_TERMS = ("aimbot", "wallhack", "wall hack", "cheat", "cheats", "hack de", "trapaca", "trapaça", "exploit")
GAMBLING_TERMS = (
    "cassino", "casino", "case opening", "abrindo caixa", "caixa de skin", "caixas de skin",
    "roleta de skin", "aposta de skin", "skin gratis", "cupom", "codigo promocional", "bet",
)
CUTSCENE_TERMS = ("cutscene", "cut scene", "cinematica", "cinematic", "cena completa", "filme do jogo")
MUSIC_RULES = {"no_licensed_radio_music", "no_raw_ost_music", "no_licensed_emote_music"}
# Regras que têm avaliador neste módulo; qualquer outra regra declarada vai para revisão humana.
EVALUATED_RULES = MUSIC_RULES | {
    "no_leaks_or_datamine", "no_emulation_or_rom", "no_story_ending_spoiler", "strict_copyright_review",
    "no_cheats_or_exploits", "no_gambling_skins_promo", "no_embargoed_cutscenes", "no_raw_long_cutscene",
}


def _hits(terms: tuple[str, ...], text: str) -> list[str]:
    """Casa termos como palavras inteiras no texto normalizado ("ending" nunca casa "trending")."""
    return [t for t in terms if re.search(rf"(?:^|\W){re.escape(_norm(t))}(?:\W|$)", text)]


class PolicyViolationError(PermissionError):
    """Erro intransponível disparado pelos portões P1 quando uma fonte ou política bloqueia a operação."""

    def __init__(self, message: str, *, code: str = "p1_blocked", details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _norm(text: str | None) -> str:
    raw = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", raw.lower()).strip()


def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def load_publisher_policies(policies_path: Path | str | None = None) -> list[dict[str, Any]]:
    path = Path(policies_path) if policies_path else DEFAULT_POLICIES_PATH
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("policies") or [])
    if isinstance(data, list):
        return list(data)
    return []


def sync_publisher_policies(db: Database, policies_path: Path | str | None = None) -> int:
    """Sincroniza o catálogo declarativo assets/policies/publishers.json para a tabela publisher_policies."""
    policies = load_publisher_policies(policies_path)
    repos = PicorteRepositories(db)
    count = 0
    for pol in policies:
        slug = str(pol.get("game_slug") or "").strip().lower()
        if not slug:
            continue
        repos.policies.upsert_policy(
            publisher=str(pol.get("publisher") or "Unknown"),
            game_slug=slug,
            release_date=pol.get("release_date"),
            spoiler_window_days=int(14 if pol.get("spoiler_window_days") is None else pol["spoiler_window_days"]),
            forbidden_content_rules=list(pol.get("forbidden_content_rules") or []),
            has_licensed_radio_music=bool(pol.get("has_licensed_radio_music")),
            violence_check_strict=bool(pol.get("violence_check_strict")),
        )
        count += 1
    return count


def sync_registry_sources(
    db: Database,
    *,
    registry_path: Path | str | None = None,
    default_status: str = "desconhecida",
) -> list[dict[str, Any]]:
    """Garante que streamers do registry.json tenham espelho em `sources` (nunca promove permissão sozinho)."""
    from picorte.engine.publish_kit import load_streamer_registry

    reg = load_streamer_registry(registry_path)
    repos = PicorteRepositories(db)
    existing = repos.sources.list_sources()
    existing_handles = {str(s.get("channel_handle") or "").strip().lower() for s in existing}
    created: list[dict[str, Any]] = []
    for st in reg.get("streamers") or []:
        handle = str(st.get("handle") or f"@{st.get('slug')}").strip().lower()
        if handle in existing_handles:
            continue
        row = repos.sources.create_source(
            name=str(st.get("display_name") or st.get("slug") or handle),
            platform="youtube",
            channel_handle=handle,
            permission_status=default_status,
            credit_template=f"Créditos: {handle}",
        )
        existing_handles.add(handle)
        created.append(row)
    return created


def _find_source(
    db: Database, *, source_id: str | None = None, channel_handle: str | None = None
) -> dict[str, Any] | None:
    repos = PicorteRepositories(db)
    if source_id:
        found = repos.sources.get_source(source_id)
        if found:
            return found
    if channel_handle:
        clean = str(channel_handle).strip().lower()
        clean_no_at = clean.lstrip("@")
        for row in repos.sources.list_sources():
            h = str(row.get("channel_handle") or "").strip().lower()
            n = str(row.get("name") or "").strip().lower()
            if clean in {h, n} or clean_no_at in {h.lstrip("@"), n}:
                return row
    return None


def _check_active_campaign(db: Database, source_id: str, now: datetime) -> dict[str, Any]:
    rows = db.fetch_all(
        "SELECT * FROM campaigns WHERE source_id = ? AND is_active = 1 ORDER BY created_at DESC",
        (source_id,),
    )
    if not rows:
        return {"valid": False, "reason": "Nenhuma campanha ativa encontrada para esta fonte."}
    has_future = False
    for row in rows:
        start = _parse_iso_dt(row.get("starts_at"))
        exp = _parse_iso_dt(row.get("expires_at"))
        if exp is not None and exp <= now:
            continue
        if start is not None and start > now:
            has_future = True
            continue
        return {"valid": True, "campaign": row}
    if has_future:
        return {"valid": False, "reason": "Campanha paga ainda não começou."}
    # Todas as campanhas expiraram -> TTL automático: desativa e marca a fonte como `expirada`.
    db.execute("UPDATE campaigns SET is_active = 0 WHERE source_id = ?", (source_id,))
    PicorteRepositories(db).sources.update_permission(source_id, "expirada")
    return {"valid": False, "reason": "Campanha paga expirada (TTL vencido)."}


def _assert_source_allowed(
    db: Database,
    *,
    stage: str,
    source_id: str | None = None,
    channel_handle: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now_dt = now or datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    source = _find_source(db, source_id=source_id, channel_handle=channel_handle)
    if source is None:
        raise PolicyViolationError(
            f"[P1:{stage}] Fonte não cadastrada/desconhecida ({channel_handle or source_id or 'vazia'}). "
            "Cadastre e autorize a fonte antes de baixar ou exportar.",
            code="source_unknown",
            details={"stage": stage, "source_id": source_id, "channel_handle": channel_handle},
        )

    status = str(source.get("permission_status") or "desconhecida").strip().lower()
    if status not in ALLOWED_PERMISSION_STATUSES:
        raise PolicyViolationError(
            f"[P1:{stage}] Fonte '{source.get('name')}' bloqueada pelo portão P1 (status='{status}').",
            code=f"source_{status}",
            details={"stage": stage, "source_id": source["id"], "permission_status": status},
        )

    campaign = None
    if status == "campanha_ativa":
        camp_chk = _check_active_campaign(db, source["id"], now_dt)
        if not camp_chk["valid"]:
            raise PolicyViolationError(
                f"[P1:{stage}] Fonte '{source.get('name')}' bloqueada: {camp_chk['reason']}",
                code="campaign_expired",
                details={"stage": stage, "source_id": source["id"], "reason": camp_chk["reason"]},
            )
        campaign = camp_chk["campaign"]

    return {
        "allowed": True,
        "stage": stage,
        "source": source,
        "permission_status": status,
        "campaign": campaign,
    }


def assert_can_ingest(
    db: Database,
    *,
    source_id: str | None = None,
    channel_handle: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Hard Gate P1 Pre-Ingest: impede qualquer download de fonte desconhecida, banida, pausada ou expirada."""
    return _assert_source_allowed(
        db, stage="pre_ingest", source_id=source_id, channel_handle=channel_handle, now=now
    )


def assert_can_export(
    db: Database,
    *,
    source_id: str | None = None,
    channel_handle: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Hard Gate P1 Pre-Export/Pre-Publish: revalida status da fonte e TTL de campanha antes de sair."""
    return _assert_source_allowed(
        db, stage="pre_export", source_id=source_id, channel_handle=channel_handle, now=now
    )


def evaluate_candidate_policy(
    db: Database,
    *,
    game_slug: str | None,
    title: str = "",
    transcript_text: str = "",
    today: date | None = None,
    policies_path: Path | str | None = None,
) -> dict[str, Any]:
    """Avalia um candidato contra as regras da publisher (spoilers, leaks, embargos, rádio licenciada, rigor)."""
    slug = str(game_slug or "").strip().lower()
    repos = PicorteRepositories(db)
    policy = repos.policies.get_by_game(slug) if slug else None
    catalog = {str(p.get("game_slug") or "").lower(): p for p in load_publisher_policies(policies_path)}
    cat_entry = catalog.get(slug, {})

    if policy is None and slug in catalog:
        sync_publisher_policies(db, policies_path)
        policy = repos.policies.get_by_game(slug)

    combined = _norm(f"{title} {transcript_text}")
    reasons: list[str] = []
    status = "pass"

    rules = list((policy or {}).get("forbidden_content_rules") or cat_entry.get("forbidden_content_rules") or [])
    requires_music_check = bool((policy or {}).get("has_licensed_radio_music")) or bool(MUSIC_RULES & set(rules))
    violence_strict = bool((policy or {}).get("violence_check_strict"))
    default_review_mode = str(cat_entry.get("default_review_mode") or "standard")

    # 1) Vazamentos / datamine / emulação proibida
    if "no_leaks_or_datamine" in rules or "no_emulation_or_rom" in rules:
        hit_leaks = _hits(LEAK_TERMS, combined)
        if hit_leaks:
            status = "hard_block"
            reasons.append(f"Violação de política ({slug}): vazamento/leak/emulação detectado ({', '.join(hit_leaks)}).")

    # 2) Janela de spoiler pós-lançamento
    if "no_story_ending_spoiler" in rules:
        # Sem data de lançamento conhecida (ex.: catálogo genérico de jogos de história) = sempre checar.
        in_spoiler_window = True
        release = (policy or {}).get("release_date") or cat_entry.get("release_date")
        if release:
            try:
                rel_date = date.fromisoformat(str(release)[:10])
                ref_today = today or date.today()
                raw_window = (policy or {}).get("spoiler_window_days", cat_entry.get("spoiler_window_days"))
                window_days = 14 if raw_window is None else int(raw_window)
                in_spoiler_window = (ref_today - rel_date).days <= window_days
            except ValueError:
                in_spoiler_window = True
        if in_spoiler_window:
            hit_spoilers = _hits(SPOILER_ENDING_TERMS, combined)
            if hit_spoilers:
                status = "hard_block"
                reasons.append(
                    f"Spoiler bloqueado na janela pós-lançamento de {slug} ({', '.join(hit_spoilers)})."
                )

    # 3) Regras que pedem olho humano (trapaça, apostas de skin, cutscenes) e regras sem avaliador
    review_checks = (
        ("no_cheats_or_exploits", CHEAT_TERMS, "promoção de trapaça/exploit"),
        ("no_gambling_skins_promo", GAMBLING_TERMS, "promoção de aposta/cassino de skins"),
        ("no_embargoed_cutscenes", CUTSCENE_TERMS, "possível cutscene sob embargo"),
        ("no_raw_long_cutscene", CUTSCENE_TERMS, "possível cutscene longa crua"),
    )
    for rule, terms, label in review_checks:
        if rule in rules:
            found = _hits(terms, combined)
            if found:
                reasons.append(f"Política {slug}: {label} ({', '.join(found)}).")
                if status == "pass":
                    status = "human_review"
    unknown_rules = [r for r in rules if r not in EVALUATED_RULES]
    if unknown_rules:
        reasons.append(f"Regras declaradas sem avaliador automático: {', '.join(unknown_rules)}.")
        if status == "pass":
            status = "human_review"

    # 4) Publishers de rigor extremo (ex.: Nintendo)
    if status == "pass" and ("strict_copyright_review" in rules or default_review_mode == "human_review"):
        status = "human_review"
        reasons.append(
            f"Publisher de rigor extremo ({(policy or {}).get('publisher') or slug}): revisão humana obrigatória."
        )

    return {
        "gate": "publisher_policy",
        "game_slug": slug,
        "publisher": (policy or {}).get("publisher") or "",
        "status": status,
        "reasons": reasons,
        "requires_music_check": requires_music_check,
        "violence_check_strict": violence_strict,
        "rules_checked": rules,
    }
