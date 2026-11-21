"""Tickets REST API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.security import get_current_user
from app.db import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreateRequest
from app.services import escalation
from app.services.settings_service import load_settings
from app.services.ticket_service import create_ticket, get_ticket_or_404
from app.services.tat import working_minutes_between

router = APIRouter(tags=["tickets"])


def _ticket_tat_block(ticket: Ticket, db: Session) -> dict:
    settings = load_settings(db)
    now = clock.now()
    cal = settings.work_calendar

    if ticket.status in ("Closed", "Resolved") or ticket.due_at is None:
        return {"state": "met", "due_at": None, "remaining_minutes": 0, "label": "Resolved"}

    if ticket.awaiting_member:
        return {
            "state": "paused",
            "due_at": ticket.due_at.isoformat() if ticket.due_at else None,
            "remaining_minutes": None,
            "label": "CLOCK PAUSED / waiting for member",
        }

    if ticket.queued_for_next_shift and ticket.tat_clock_started_at and ticket.tat_clock_started_at > now:
        from app.services.tat import next_working_start
        nws = next_working_start(now, cal)
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo  # type: ignore
        IST = ZoneInfo("Asia/Kolkata")
        nws_ist_dt = nws.astimezone(IST)
        _h = str(nws_ist_dt.hour % 12 or 12)
        _ampm = "AM" if nws_ist_dt.hour < 12 else "PM"
        nws_ist = f"{_h}:{nws_ist_dt.strftime('%M')} {_ampm} {nws_ist_dt.strftime('%a')}"
        return {
            "state": "queued",
            "due_at": ticket.due_at.isoformat() if ticket.due_at else None,
            "remaining_minutes": None,
            "label": f"QUEUED / next shift {nws_ist}",
        }

    due_at = ticket.due_at
    if due_at and now > due_at:
        overdue_secs = int((now - due_at).total_seconds())
        h, m = divmod(overdue_secs // 60, 60)
        label = f"OVERDUE {h}h {m:02d}m" if h else f"OVERDUE {m}m"
        return {
            "state": "overdue",
            "due_at": due_at.isoformat(),
            "remaining_minutes": 0,
            "label": label,
        }

    remaining_secs = int((due_at - now).total_seconds())
    remaining_min = remaining_secs // 60
    h, m = divmod(remaining_min, 60)
    if remaining_secs < 1800:
        label = f"< 30m left"
    elif h:
        label = f"{h}h {m:02d}m left"
    else:
        label = f"{m}m left"

    return {
        "state": "running",
        "due_at": due_at.isoformat(),
        "remaining_minutes": remaining_min,
        "label": label,
    }


def _ticket_permissions(ticket: Ticket, actor: User, db: Session) -> dict:
    settings = load_settings(db)
    now = clock.now()

    can_reopen = False
    reopens_left = 0
    reopen_until = None
    can_confirm = False

    if actor.role == "member" and actor.id == ticket.member_id:
        if ticket.status == "Resolved":
            can_confirm = True
            reopens_left = max(0, settings.max_reopens - ticket.reopen_count)
            if ticket.resolved_at:
                ru = ticket.resolved_at + __import__("datetime").timedelta(days=settings.reopen_window_days)
                if now <= ru and reopens_left > 0:
                    can_reopen = True
                reopen_until = ru.isoformat()

    return {
        "can_reopen": can_reopen,
        "reopens_left": reopens_left,
        "reopen_until": reopen_until,
        "can_confirm": can_confirm,
    }


def _serialize_ticket(ticket: Ticket, actor: User, db: Session) -> dict:
    return {
        "id": ticket.id,
        "public_id": ticket.public_id,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "subject": ticket.subject,
        "description": ticket.description,
        "survey_ref": ticket.survey_ref,
        "requested_field": ticket.requested_field,
        "requested_value": ticket.requested_value,
        "assignee_id": ticket.assignee_id,
        "member_id": ticket.member_id,
        "queued_for_next_shift": ticket.queued_for_next_shift,
        "awaiting_member": ticket.awaiting_member,
        "reopen_count": ticket.reopen_count,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "tat": _ticket_tat_block(ticket, db),
        "permissions": _ticket_permissions(ticket, actor, db),
    }


@router.post("/tickets", status_code=201)
async def api_create_ticket(
    body: TicketCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    from app.core.exceptions import Forbidden
    if actor.role != "member":
        raise Forbidden("Only members can create tickets.")

    ticket = create_ticket(
        db,
        member=actor,
        category=body.category,
        description=body.description,
        survey_ref=body.survey_ref,
        requested_field=body.requested_field,
        requested_value=body.requested_value,
    )
    settings = load_settings(db)
    return {
        "public_id": ticket.public_id,
        "status": ticket.status,
        "priority": ticket.priority,
        "due_at": ticket.due_at.isoformat() if ticket.due_at else None,
        "queued_for_next_shift": ticket.queued_for_next_shift,
        "expected_reply_by": ticket.due_at.isoformat() if ticket.due_at else None,
    }


@router.get("/tickets")
async def api_list_tickets(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    status: str | None = Query(None),
    category: str | None = Query(None),
    priority: str | None = Query(None),
    overdue: bool = Query(False),
    assignee: str | None = Query(None),
    q: str | None = Query(None),
    sort: str = Query("due"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    # Lazy escalation sweep
    escalation.escalation_sweep(db)

    query = db.query(Ticket)

    if actor.role == "member":
        query = query.filter(Ticket.member_id == actor.id)

    if status:
        query = query.filter(Ticket.status == status)
    if category:
        query = query.filter(Ticket.category == category)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if overdue:
        now = clock.now()
        query = query.filter(Ticket.due_at <= now, Ticket.status.notin_(["Closed", "Resolved"]))
    if assignee == "me":
        query = query.filter(Ticket.assignee_id == actor.id)
    elif assignee == "unassigned":
        query = query.filter(Ticket.assignee_id.is_(None))
    elif assignee and assignee.isdigit():
        query = query.filter(Ticket.assignee_id == int(assignee))
    if q:
        query = query.filter(
            Ticket.subject.ilike(f"%{q}%") | Ticket.public_id.ilike(f"%{q}%")
        )

    if sort == "due":
        query = query.order_by(Ticket.due_at.asc().nullslast())
    elif sort == "created":
        query = query.order_by(Ticket.created_at.desc())
    else:
        query = query.order_by(Ticket.updated_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [_serialize_ticket(t, actor, db) for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/tickets/{public_id}")
async def api_get_ticket(
    public_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    messages = ticket.messages or []
    visible_messages = [
        m for m in messages
        if not m.is_internal_note or actor.role in ("agent", "head")
    ]

    return {
        **_serialize_ticket(ticket, actor, db),
        "messages": [
            {
                "id": m.id,
                "author_id": m.author_id,
                "author_name": m.author.name if m.author else "System",
                "author_role": m.author.role if m.author else "system",
                "body": m.body,
                "is_internal_note": m.is_internal_note,
                "created_at": m.created_at.isoformat(),
            }
            for m in visible_messages
        ],
    }


@router.get("/tickets/{public_id}/events")
async def api_get_events(
    public_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    from app.core.exceptions import Forbidden as _Forbidden
    if actor.role == "member":
        raise _Forbidden("Members cannot view the event log.")
    ticket = get_ticket_or_404(db, public_id, actor)
    events = ticket.events
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "actor": e.actor.name if e.actor else "System",
            "from_value": e.from_value,
            "to_value": e.to_value,
            "reason": e.reason,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
