"""Member UI routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.csrf import verify_csrf_token
from app.core.exceptions import Forbidden
from app.core.security import get_current_user
from app.db import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.services import escalation
from app.services.message_service import add_message
from app.services.settings_service import load_settings
from app.services.ticket_service import (
    confirm_ticket,
    create_ticket,
    get_ticket_or_404,
    reopen_ticket,
)

router = APIRouter(prefix="/member", tags=["member-ui"])


def _require_member(request: Request, db: Session) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise Forbidden("Please log in.")
    user = db.get(User, user_id)
    if not user or user.role != "member":
        raise Forbidden("Member access required.")
    return user


@router.get("/tickets", response_class=HTMLResponse)
async def member_tickets(request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_member(request, db)
    escalation.escalation_sweep(db)

    tab = request.query_params.get("tab", "active")
    q = db.query(Ticket).filter(Ticket.member_id == user.id)
    if tab == "active":
        q = q.filter(Ticket.status.notin_(["Resolved", "Closed"]))
    elif tab == "resolved":
        q = q.filter(Ticket.status.in_(["Resolved", "Closed"]))

    tickets = q.order_by(Ticket.updated_at.desc()).all()
    settings = load_settings(db)
    return render(request, "member/tickets.html", {
        "tickets": tickets,
        "tab": tab,
        "user": user,
        "settings": settings,
    })


@router.get("/raise", response_class=HTMLResponse)
async def member_raise_step1(request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_member(request, db)
    return render(request, "member/raise_step1.html", {"user": user})


@router.get("/raise/{category}", response_class=HTMLResponse)
async def member_raise_step2(category: str, request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_member(request, db)
    valid = ["Payment", "Profile change", "Survey issue", "Eligibility", "Other"]
    if category not in valid:
        return RedirectResponse(url="/member/raise", status_code=302)
    settings = load_settings(db)
    from app.services.settings_service import get_priority_for_category
    priority = get_priority_for_category(db, category)
    tat_minutes = settings.tat_minutes[priority]
    return render(request, "member/raise_step2.html", {
        "user": user,
        "category": category,
        "tat_minutes": tat_minutes,
    })


@router.post("/raise/{category}", response_class=HTMLResponse)
async def member_raise_submit(
    category: str,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.main import render

    user = _require_member(request, db)
    form = await request.form()

    if not verify_csrf_token(request, str(form.get("csrf_token", ""))):
        return render(request, "member/raise_step2.html", {
            "user": user, "category": category, "error": "Security token expired. Please try again.", "tat_minutes": 240
        })

    desc = str(form.get("description", "")).strip()
    survey_ref = str(form.get("survey_ref", "")).strip() or None
    req_field = str(form.get("requested_field", "")).strip() or None
    req_value = str(form.get("requested_value", "")).strip() or None

    errors = {}
    if len(desc) < 10:
        errors["description"] = "Please describe your issue in at least 10 characters."
    if len(desc) > 2000:
        errors["description"] = "Description must be under 2000 characters."
    if category == "Profile change" and not req_field:
        errors["requested_field"] = "Please select which field you want to change."
    if category == "Profile change" and not req_value:
        errors["requested_value"] = "Please enter the new value."

    if errors:
        settings = load_settings(db)
        from app.services.settings_service import get_priority_for_category
        priority = get_priority_for_category(db, category)
        return render(request, "member/raise_step2.html", {
            "user": user,
            "category": category,
            "errors": errors,
            "form": form,
            "tat_minutes": settings.tat_minutes[priority],
        })

    try:
        ticket = create_ticket(
            db,
            member=user,
            category=category,
            description=desc,
            survey_ref=survey_ref,
            requested_field=req_field,
            requested_value=req_value,
        )
    except ValueError as e:
        return render(request, "member/raise_step2.html", {
            "user": user, "category": category, "error": str(e), "tat_minutes": 240
        })

    return render(request, "member/raise_success.html", {"user": user, "ticket": ticket})


@router.get("/tickets/{public_id}", response_class=HTMLResponse)
async def member_ticket_detail(public_id: str, request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_member(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    messages = [m for m in ticket.messages if not m.is_internal_note]
    settings = load_settings(db)
    from app.routes.tickets_api import _ticket_tat_block, _ticket_permissions
    tat = _ticket_tat_block(ticket, db)
    perms = _ticket_permissions(ticket, user, db)
    return render(request, "member/ticket_detail.html", {
        "user": user,
        "ticket": ticket,
        "messages": messages,
        "tat": tat,
        "perms": perms,
        "settings": settings,
    })


@router.post("/tickets/{public_id}/reply", response_class=HTMLResponse)
async def member_reply(public_id: str, request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_member(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    form = await request.form()

    body = str(form.get("body", "")).strip()
    errors = {}
    if not body:
        errors["body"] = "Reply cannot be empty."
    if len(body) > 2000:
        errors["body"] = "Reply must be under 2000 characters."

    if errors:
        messages = [m for m in ticket.messages if not m.is_internal_note]
        from app.routes.tickets_api import _ticket_tat_block, _ticket_permissions
        return render(request, "member/ticket_detail.html", {
            "user": user, "ticket": ticket, "messages": messages,
            "tat": _ticket_tat_block(ticket, db),
            "perms": _ticket_permissions(ticket, user, db),
            "errors": errors, "reply_body": body,
            "settings": load_settings(db),
        })

    try:
        add_message(db, ticket=ticket, author=user, body=body)
    except Exception as e:
        messages = [m for m in ticket.messages if not m.is_internal_note]
        from app.routes.tickets_api import _ticket_tat_block, _ticket_permissions
        return render(request, "member/ticket_detail.html", {
            "user": user, "ticket": ticket, "messages": messages,
            "tat": _ticket_tat_block(ticket, db),
            "perms": _ticket_permissions(ticket, user, db),
            "error": str(e), "settings": load_settings(db),
        })

    return RedirectResponse(url=f"/member/tickets/{public_id}", status_code=303)


@router.post("/tickets/{public_id}/confirm", response_class=HTMLResponse)
async def member_confirm(public_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_member(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    confirm_ticket(db, ticket=ticket, actor=user)
    return RedirectResponse(url=f"/member/tickets/{public_id}", status_code=303)


@router.post("/tickets/{public_id}/reopen", response_class=HTMLResponse)
async def member_reopen(public_id: str, request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_member(request, db)
    ticket = get_ticket_or_404(db, public_id, user)
    form = await request.form()
    reason = str(form.get("reason", "")).strip()

    try:
        reopen_ticket(db, ticket=ticket, reason=reason, actor=user)
    except Exception as e:
        messages = [m for m in ticket.messages if not m.is_internal_note]
        from app.routes.tickets_api import _ticket_tat_block, _ticket_permissions
        return render(request, "member/ticket_detail.html", {
            "user": user, "ticket": ticket, "messages": messages,
            "tat": _ticket_tat_block(ticket, db),
            "perms": _ticket_permissions(ticket, user, db),
            "reopen_error": str(e), "settings": load_settings(db),
        })

    return RedirectResponse(url=f"/member/tickets/{public_id}", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
async def member_profile(request: Request, db: Session = Depends(get_db)):
    from app.main import render

    user = _require_member(request, db)
    return render(request, "member/profile.html", {"user": user})
