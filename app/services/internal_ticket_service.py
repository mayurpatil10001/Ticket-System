"""InternalTicket service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.exceptions import Forbidden, NotFound
from app.models.internal_ticket import InternalTicket
from app.models.ticket import Ticket
from app.models.user import User
from app.services import event_service


def create_internal_ticket(
    db: Session,
    *,
    ticket: Ticket,
    team: str,
    title: str,
    note: str,
    actor: User,
) -> InternalTicket:
    if actor.role == "member":
        raise Forbidden("Members cannot create internal tickets.")

    it = InternalTicket(
        parent_ticket_id=ticket.id,
        team=team,
        title=title.strip(),
        note=note.strip(),
        status="Open",
        created_by=actor.id,
        created_at=clock.now(),
    )
    db.add(it)
    db.flush()

    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type="internal_ticket_created",
        to_value=team,
    )
    db.commit()
    db.refresh(it)
    return it


def complete_internal_ticket(db: Session, *, it_id: int, actor: User) -> InternalTicket:
    it = db.query(InternalTicket).filter(InternalTicket.id == it_id).first()
    if not it:
        raise NotFound("InternalTicket")
    if actor.role == "member":
        raise Forbidden("Members cannot complete internal tickets.")

    now = clock.now()
    it.status = "Done"
    it.done_by = actor.id
    it.done_at = now

    event_service.log_event(
        db,
        ticket_id=it.parent_ticket_id,
        actor_id=actor.id,
        event_type="internal_ticket_done",
        to_value=it.team,
    )
    db.commit()
    db.refresh(it)
    return it
