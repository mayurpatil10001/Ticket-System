"""Ticket action routes: assign, priority, resolve, confirm, reopen, request-info, etc."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.ticket import (
    AssignRequest,
    InternalTicketRequest,
    PriorityChangeRequest,
    ReopenRequest,
    RequestInfoRequest,
    ResolveRequest,
)
from app.services.internal_ticket_service import (
    complete_internal_ticket,
    create_internal_ticket,
)
from app.services.ticket_service import (
    apply_profile_change,
    assign_ticket,
    change_priority,
    confirm_ticket,
    get_ticket_or_404,
    request_info,
    reopen_ticket,
    resolve_ticket,
)

router = APIRouter(tags=["ticket-actions"])


@router.post("/tickets/{public_id}/assign")
async def api_assign(
    public_id: str,
    body: AssignRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    assignee = db.get(User, body.assignee_id)
    if not assignee:
        from app.core.exceptions import NotFound
        raise NotFound("User")
    ticket = assign_ticket(db, ticket=ticket, assignee=assignee, actor=actor)
    return {"public_id": ticket.public_id, "status": ticket.status, "assignee_id": ticket.assignee_id}


@router.post("/tickets/{public_id}/priority")
async def api_change_priority(
    public_id: str,
    body: PriorityChangeRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    ticket = change_priority(db, ticket=ticket, new_priority=body.priority, reason=body.reason, actor=actor)
    return {"public_id": ticket.public_id, "priority": ticket.priority, "due_at": ticket.due_at.isoformat() if ticket.due_at else None}


@router.post("/tickets/{public_id}/request-info")
async def api_request_info(
    public_id: str,
    body: RequestInfoRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    ticket = request_info(db, ticket=ticket, message=body.message, actor=actor)
    return {"public_id": ticket.public_id, "awaiting_member": ticket.awaiting_member}


@router.post("/tickets/{public_id}/resolve")
async def api_resolve(
    public_id: str,
    body: ResolveRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    ticket = resolve_ticket(db, ticket=ticket, message=body.message, actor=actor)
    return {"public_id": ticket.public_id, "status": ticket.status}


@router.post("/tickets/{public_id}/confirm")
async def api_confirm(
    public_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    ticket = confirm_ticket(db, ticket=ticket, actor=actor)
    return {"public_id": ticket.public_id, "status": ticket.status}


@router.post("/tickets/{public_id}/reopen")
async def api_reopen(
    public_id: str,
    body: ReopenRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    ticket = reopen_ticket(db, ticket=ticket, reason=body.reason, actor=actor)
    return {"public_id": ticket.public_id, "status": ticket.status, "reopen_count": ticket.reopen_count}


@router.post("/tickets/{public_id}/apply-profile-change")
async def api_apply_profile(
    public_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    ticket = apply_profile_change(db, ticket=ticket, actor=actor)
    return {"public_id": ticket.public_id, "event": "profile_applied"}


@router.post("/tickets/{public_id}/internal-tickets", status_code=201)
async def api_create_internal(
    public_id: str,
    body: InternalTicketRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    it = create_internal_ticket(db, ticket=ticket, team=body.team, title=body.title, note=body.note, actor=actor)
    return {"id": it.id, "team": it.team, "status": it.status}


@router.post("/internal-tickets/{it_id}/complete")
async def api_complete_internal(
    it_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    it = complete_internal_ticket(db, it_id=it_id, actor=actor)
    return {"id": it.id, "status": it.status}
