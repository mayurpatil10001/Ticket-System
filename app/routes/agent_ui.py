"""Agent UI routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.exceptions import Forbidden
from app.core.security import get_current_user
from app.db import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.services import escalation
from app.services.message_service import add_message
from app.services.saved_reply_service import list_saved_replies
from app.services.settings_service import load_settings
from app.services.ticket_service import (
    assign_ticket,
    change_priority,
    get_ticket_or_404,
    request_info,
    resolve_ticket,
    apply_profile_change,
)

router = APIRouter(prefix="/agent", tags=["agent-ui"])


def _require_agent(request: Request, db: Session) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise Forbidden("Please log in.")
    user = db.get(User, user_id)
    if not user or user.role not in ("agent", "head"):
        raise Forbidden("Agent access required.")
    return user


@router.get("/queue", response_class=HTMLResponse)
async def agent_queue(request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_agent(request, db)
    escalation.escalation_sweep(db)

    # Filters from query params
    p = request.query_params
    status_f = p.get("status")
    category_f = p.get("category")
    priority_f = p.get("priority")
    overdue_f = p.get("overdue") == "1"
    assignee_f = p.get("assignee", "all")
    q_text = p.get("q", "").strip()
    sort_f = p.get("sort", "due")
    selected_id = p.get("ticket")

    from app.core.clock import clock
    now = clock.now()

    query = db.query(Ticket)
    if status_f:
        query = query.filter(Ticket.status == status_f)
    if category_f:
        query = query.filter(Ticket.category == category_f)
    if priority_f:
        query = query.filter(Ticket.priority == priority_f)
    if overdue_f:
        query = query.filter(Ticket.due_at <= now, Ticket.status.notin_(["Closed", "Resolved"]))
    if assignee_f == "me":
        query = query.filter(Ticket.assignee_id == user.id)
    elif assignee_f == "unassigned":
        query = query.filter(Ticket.assignee_id.is_(None))
    if q_text:
        query = query.filter(
            Ticket.subject.ilike(f"%{q_text}%") | Ticket.public_id.ilike(f"%{q_text}%")
        )

    if sort_f == "due":
        query = query.order_by(Ticket.due_at.asc().nullslast())
    elif sort_f == "created":
        query = query.order_by(Ticket.created_at.desc())
    else:
        query = query.order_by(Ticket.updated_at.desc())

    tickets = query.limit(100).all()

    # Selected ticket for detail pane
    selected_ticket = None
    messages = []
    events = []
    saved_replies = []
    if selected_id:
        try:
            selected_ticket = get_ticket_or_404(db, selected_id, user)
            messages = selected_ticket.messages
            events = sorted(selected_ticket.events, key=lambda e: e.created_at)
            saved_replies = list_saved_replies(db)
        except Exception:
            pass

    agents = db.query(User).filter(User.role.in_(["agent", "head"]), User.is_active.is_(True)).all()

    from app.routes.tickets_api import _ticket_tat_block, _ticket_permissions
    tat = _ticket_tat_block(selected_ticket, db) if selected_ticket else None
    perms = _ticket_permissions(selected_ticket, user, db) if selected_ticket else None

    return render(request, "agent/queue.html", {
        "user": user,
        "tickets": tickets,
        "selected_ticket": selected_ticket,
        "messages": messages,
        "events": events,
        "saved_replies": saved_replies,
        "agents": agents,
        "tat": tat,
        "perms": perms,
        "filters": {
            "status": status_f, "category": category_f, "priority": priority_f,
            "overdue": overdue_f, "assignee": assignee_f, "q": q_text, "sort": sort_f,
        },
        "now": now,
    })


@router.post("/tickets/{public_id}/assign", response_class=HTMLResponse)
async def agent_assign(public_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_agent(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    form = await request.form()
    assignee_id = int(str(form.get("assignee_id", user.id)))
    assignee = db.get(User, assignee_id)
    if assignee:
        assign_ticket(db, ticket=ticket, assignee=assignee, actor=user)
    return RedirectResponse(url=f"/agent/queue?ticket={public_id}", status_code=303)


@router.post("/tickets/{public_id}/reply", response_class=HTMLResponse)
async def agent_reply(public_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_agent(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    form = await request.form()
    body = str(form.get("body", "")).strip()
    is_note = form.get("is_internal_note") == "1"
    action = str(form.get("action", "reply"))

    if body:
        add_message(db, ticket=ticket, author=user, body=body, is_internal_note=is_note)

    if action == "reply_resolve" and body:
        try:
            resolve_ticket(db, ticket=ticket, message=body, actor=user)
        except Exception:
            pass
    elif action == "request_info":
        if body:
            request_info(db, ticket=ticket, message=body, actor=user)

    return RedirectResponse(url=f"/agent/queue?ticket={public_id}", status_code=303)


@router.post("/tickets/{public_id}/resolve", response_class=HTMLResponse)
async def agent_resolve(public_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_agent(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    form = await request.form()
    message = str(form.get("message", "This ticket has been resolved.")).strip()
    resolve_ticket(db, ticket=ticket, message=message or "This ticket has been resolved.", actor=user)
    return RedirectResponse(url=f"/agent/queue?ticket={public_id}", status_code=303)


@router.post("/tickets/{public_id}/priority", response_class=HTMLResponse)
async def agent_priority(public_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_agent(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    form = await request.form()
    priority = str(form.get("priority", ""))
    reason = str(form.get("reason", "")).strip()
    change_priority(db, ticket=ticket, new_priority=priority, reason=reason, actor=user)
    return RedirectResponse(url=f"/agent/queue?ticket={public_id}", status_code=303)


@router.post("/tickets/{public_id}/apply-profile-change", response_class=HTMLResponse)
async def agent_apply_profile(public_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_agent(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    apply_profile_change(db, ticket=ticket, actor=user)
    return RedirectResponse(url=f"/agent/queue?ticket={public_id}", status_code=303)
