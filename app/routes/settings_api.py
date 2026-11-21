"""Settings and saved replies API (head only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_head
from app.db import get_db
from app.models.user import User
from app.schemas.auth import SavedReplyCreateRequest, SavedReplyUpdateRequest
from app.services import saved_reply_service
from app.services.settings_service import (
    DEFAULTS,
    invalidate_cache,
    load_settings,
    save_setting,
)

router = APIRouter(tags=["settings"])


@router.get("/settings")
async def api_get_settings(
    db: Session = Depends(get_db),
    actor: User = Depends(require_head),
):
    settings = load_settings(db)
    return {
        "tat_minutes": settings.tat_minutes,
        "tat_mode": settings.tat_mode,
        "working_hours": settings.working_hours,
        "reopen_window_days": settings.reopen_window_days,
        "max_reopens": settings.max_reopens,
        "awaiting_member_auto_resolve_days": settings.awaiting_member_auto_resolve_days,
        "auto_close_days": settings.auto_close_days,
        "escalation_recipients": settings.escalation_recipients,
        "category_priority": settings.category_priority,
    }


@router.put("/settings")
async def api_put_settings(
    body: dict,
    db: Session = Depends(get_db),
    actor: User = Depends(require_head),
):
    allowed_keys = set(DEFAULTS.keys())
    for key, value in body.items():
        if key in allowed_keys:
            save_setting(db, key, value, actor_id=actor.id)
    return {"ok": True}


@router.post("/settings/recalculate-open-tickets")
async def api_recalculate(
    db: Session = Depends(get_db),
    actor: User = Depends(require_head),
):
    """Recompute due_at for all open (non-terminal) tickets using current settings."""
    from app.models.ticket import Ticket
    from app.services.settings_service import load_settings
    from app.services.tat import compute_due_at

    invalidate_cache()
    settings = load_settings(db)
    cal = settings.work_calendar

    open_statuses = ["Open", "In Progress", "Reopened", "Escalated"]
    tickets = db.query(Ticket).filter(Ticket.status.in_(open_statuses)).all()
    count = 0
    for t in tickets:
        if t.tat_clock_started_at:
            mode = settings.tat_mode.get(t.priority, "working_hours")
            t.due_at = compute_due_at(
                t.tat_clock_started_at,
                t.tat_minutes_snapshot,
                t.paused_seconds_working,
                cal,
                mode,
            )
            count += 1
    db.commit()
    return {"recalculated": count}


# Saved replies
@router.get("/saved-replies")
async def api_list_saved_replies(
    category: str | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    # Agents and heads can read; members cannot
    if actor.role == "member":
        from app.core.exceptions import Forbidden
        raise Forbidden("Members cannot access saved replies.")
    replies = saved_reply_service.list_saved_replies(db, category=category)
    return [{"id": r.id, "title": r.title, "body": r.body, "category": r.category} for r in replies]


@router.post("/saved-replies", status_code=201)
async def api_create_saved_reply(
    body: SavedReplyCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_head),
):
    sr = saved_reply_service.create_saved_reply(
        db, title=body.title, body=body.body, category=body.category, actor=actor
    )
    return {"id": sr.id, "title": sr.title}


@router.put("/saved-replies/{reply_id}")
async def api_update_saved_reply(
    reply_id: int,
    body: SavedReplyUpdateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_head),
):
    sr = saved_reply_service.update_saved_reply(
        db, reply_id=reply_id, title=body.title, body=body.body, category=body.category
    )
    return {"id": sr.id, "title": sr.title}


@router.delete("/saved-replies/{reply_id}", status_code=204)
async def api_delete_saved_reply(
    reply_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_head),
):
    saved_reply_service.delete_saved_reply(db, reply_id=reply_id)
