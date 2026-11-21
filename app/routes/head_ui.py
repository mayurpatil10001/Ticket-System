"""Head UI routes."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.exceptions import Forbidden
from app.db import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.services import escalation
from app.services.saved_reply_service import (
    create_saved_reply,
    delete_saved_reply,
    list_saved_replies,
    update_saved_reply,
)
from app.services.settings_service import (
    DEFAULTS,
    invalidate_cache,
    load_settings,
    save_setting,
)

router = APIRouter(prefix="/head", tags=["head-ui"])


def _require_head(request: Request, db: Session) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise Forbidden("Please log in.")
    user = db.get(User, user_id)
    if not user or user.role != "head":
        raise Forbidden("Head access required.")
    return user


@router.get("/dashboard", response_class=HTMLResponse)
async def head_dashboard(request: Request, db: Session = Depends(get_db)):
    from app.main import render
    from app.core.clock import clock
    from sqlalchemy import func

    user = _require_head(request, db)
    escalation.escalation_sweep(db)
    escalation.auto_resolve_awaiting(db)
    escalation.auto_close_resolved(db)

    now = clock.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    open_count = db.query(Ticket).filter(Ticket.status == "Open").count()
    overdue_count = db.query(Ticket).filter(
        Ticket.status.in_(["Open", "In Progress", "Reopened", "Escalated"]),
        Ticket.due_at <= now,
    ).count()
    escalated_count = db.query(Ticket).filter(Ticket.status == "Escalated").count()
    resolved_today = db.query(Ticket).filter(
        Ticket.status.in_(["Resolved", "Closed"]),
        Ticket.resolved_at >= today_start,
    ).count()

    resolved_all = db.query(Ticket).filter(Ticket.resolved_at.isnot(None)).all()
    if resolved_all:
        total_mins = sum(
            int((t.resolved_at - t.created_at).total_seconds() // 60)
            for t in resolved_all if t.resolved_at and t.created_at
        )
        avg_resolution = total_mins // len(resolved_all)
    else:
        avg_resolution = 0

    category_rows = (
        db.query(Ticket.category, func.count(Ticket.id))
        .filter(Ticket.status.notin_(["Closed"]))
        .group_by(Ticket.category)
        .all()
    )
    by_category = [{"category": c, "count": n} for c, n in category_rows]

    agents = db.query(User).filter(User.role == "agent", User.is_active.is_(True)).all()
    agent_load = []
    for agent in agents:
        open_a = db.query(Ticket).filter(
            Ticket.assignee_id == agent.id,
            Ticket.status.in_(["Open", "In Progress", "Reopened", "Escalated"]),
        ).count()
        overdue_a = db.query(Ticket).filter(
            Ticket.assignee_id == agent.id,
            Ticket.due_at <= now,
            Ticket.status.in_(["Open", "In Progress", "Reopened"]),
        ).count()
        responded = db.query(Ticket).filter(
            Ticket.assignee_id == agent.id,
            Ticket.first_response_at.isnot(None),
        ).all()
        avg_fr = None
        if responded:
            avg_fr = sum(
                int((t.first_response_at - t.created_at).total_seconds() // 60)
                for t in responded if t.first_response_at and t.created_at
            ) // len(responded)
        agent_load.append({"agent": agent, "open": open_a, "overdue": overdue_a, "avg_fr": avg_fr})

    escalated = (
        db.query(Ticket)
        .filter(Ticket.status == "Escalated")
        .order_by(Ticket.due_at.asc())
        .all()
    )

    return render(request, "head/dashboard.html", {
        "user": user,
        "open_count": open_count,
        "overdue_count": overdue_count,
        "escalated_count": escalated_count,
        "resolved_today": resolved_today,
        "avg_resolution": avg_resolution,
        "by_category": by_category,
        "agent_load": agent_load,
        "escalated_tickets": escalated,
        "now": now,
    })


@router.get("/settings", response_class=HTMLResponse)
async def head_settings(request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_head(request, db)
    settings = load_settings(db)
    saved_replies = list_saved_replies(db)
    agents = db.query(User).filter(User.role.in_(["agent", "head"]), User.is_active.is_(True)).all()
    return render(request, "head/settings.html", {
        "user": user,
        "settings": settings,
        "saved_replies": saved_replies,
        "agents": agents,
    })


@router.post("/settings/{key}", response_class=HTMLResponse)
async def head_save_setting(key: str, request: Request, db: Session = Depends(get_db)):
    user = _require_head(request, db)
    form = await request.form()

    allowed_keys = set(DEFAULTS.keys())
    if key not in allowed_keys:
        return RedirectResponse(url="/head/settings", status_code=303)

    # Parse the form value as JSON or plain scalar
    raw = str(form.get("value", ""))
    try:
        value = json.loads(raw)
    except Exception:
        # Try as int, float, then string
        try:
            value = int(raw)
        except ValueError:
            value = raw

    save_setting(db, key, value, actor_id=user.id)
    return RedirectResponse(url="/head/settings?saved=" + key, status_code=303)


@router.post("/saved-replies/create", response_class=HTMLResponse)
async def head_create_reply(request: Request, db: Session = Depends(get_db)):
    user = _require_head(request, db)
    form = await request.form()
    title = str(form.get("title", "")).strip()
    body_text = str(form.get("body", "")).strip()
    category = str(form.get("category", "")).strip() or None
    if title and body_text:
        create_saved_reply(db, title=title, body=body_text, category=category, actor=user)
    return RedirectResponse(url="/head/settings", status_code=303)


@router.post("/saved-replies/{reply_id}/delete", response_class=HTMLResponse)
async def head_delete_reply(reply_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_head(request, db)
    delete_saved_reply(db, reply_id=reply_id)
    return RedirectResponse(url="/head/settings", status_code=303)


@router.get("/queue", response_class=HTMLResponse)
async def head_queue(request: Request, db: Session = Depends(get_db)):
    """Head can also view the agent queue."""
    from app.main import render

    user = _require_head(request, db)
    escalation.escalation_sweep(db)
    tickets = db.query(Ticket).filter(
        Ticket.status.notin_(["Closed"])
    ).order_by(Ticket.due_at.asc().nullslast()).limit(100).all()
    agents = db.query(User).filter(User.role.in_(["agent", "head"]), User.is_active.is_(True)).all()

    return render(request, "agent/queue.html", {
        "user": user,
        "tickets": tickets,
        "selected_ticket": None,
        "messages": [],
        "events": [],
        "saved_replies": [],
        "agents": agents,
        "tat": None,
        "perms": None,
        "filters": {"status": None, "category": None, "priority": None, "overdue": False, "assignee": "all", "q": "", "sort": "due"},
        "now": __import__("app.core.clock", fromlist=["clock"]).clock.now(),
    })
