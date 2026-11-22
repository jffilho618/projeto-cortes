"""Story 4.1 — Disjuntor Global de Emergência por Fonte (P1: pausa imediata ao 1º claim/strike).

Tudo acontece numa única transação: fonte travada, evento auditável, publicações pendentes pausadas e
vídeos ainda na fila bloqueados. Se qualquer passo falhar, nada muda (sem estado parcial).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from picorte.db.connection import Database
from picorte.db.repositories import PicorteRepositories

MANUAL_CLAIM_TYPES = {"manual", "manual_emergency"}


def pause_source_globally(
    db: Database,
    *,
    source_id: str,
    claim_type: str = "copyright_claim",
    details: str = "",
    reason: str = "",
    publication_id: str | None = None,
) -> dict[str, Any]:
    """Trava a fonte, registra em `claims_events`, pausa publicações pendentes e bloqueia vídeos na fila."""
    source = PicorteRepositories(db).sources.get_source(source_id)
    if source is None:
        raise ValueError(f"Fonte não encontrada: {source_id}")

    manual = str(claim_type) in MANUAL_CLAIM_TYPES
    source_status = "pausada_emergencia" if manual else "pausada_por_claim"
    publication_status = "pausado_emergencia" if manual else "pausado_claim"
    now = datetime.now(timezone.utc).isoformat()
    claim_event_id = str(uuid.uuid4())
    event_details = " | ".join(x for x in (str(reason).strip(), str(details).strip()) if x)

    with db.transaction() as tx:
        tx.execute(
            "UPDATE sources SET permission_status = ?, updated_at = ? WHERE id = ?",
            (source_status, now, source_id),
        )
        tx.execute(
            """INSERT INTO claims_events
               (id, publication_id, source_id, claim_type, details, triggered_global_pause, detected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (claim_event_id, publication_id, source_id, str(claim_type), event_details, 1, now),
        )
        pending = tx.fetch_all(
            """SELECT p.id FROM publications p
               JOIN clips c ON c.id = p.clip_id
               JOIN videos v ON v.id = c.video_id
               WHERE v.source_id = ? AND p.status IN ('fila', 'agendado', 'exportado')""",
            (source_id,),
        )
        for row in pending:
            tx.execute("UPDATE publications SET status = ? WHERE id = ?", (publication_status, row["id"]))
        blocked_videos = tx.execute(
            "UPDATE videos SET status = 'bloqueado_p1', updated_at = ? WHERE source_id = ? AND status = 'queued'",
            (now, source_id),
        )

    return {
        "source_id": source_id,
        "source_name": source.get("name"),
        "source_status": source_status,
        "claim_event_id": claim_event_id,
        "claim_type": claim_type,
        "reason": str(reason).strip(),
        "paused_publications": len(pending),
        "blocked_videos": blocked_videos,
        "detected_at": now,
    }
