"""Message service."""
from __future__ import annotations

import nh3
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.exceptions import Forbidden
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.user import User
from app.services import event_service

MAX_BODY = 2000


def add_message(
    db: Session,
    *,
    ticket: Ticket,
    author: User,
    body: str,
    is_internal_note: bool = False,
    _skip_commit: bool = False,
) -> TicketMessage:
    """
    Add a message or internal note to a ticket.
    Members cannot post internal notes.
    Members cannot post to Closed tickets.
    Agents cannot post to Closed tickets.
    """
    body = nh3.clean(body.strip(), tags=set())
    if not body:
        raise ValueError("Message body cannot be empty.")
    if len(body) > MAX_BODY:
        raise ValueError(f"Message must be at most {MAX_BODY} characters.")

    if author.role == "member":
        if is_internal_note:
            raise Forbidden("Members cannot post internal notes.")
        if ticket.status == "Closed":
            raise Forbidden("This ticket is closed. Please raise a new ticket.")
        # Implicit resume if clock is paused
        if ticket.awaiting_member:
            from app.services.ticket_service import resume_clock
            resume_clock(db, ticket=ticket, actor=author)

    if author.role in ("agent", "head"):
        if ticket.status == "Closed":
            raise Forbidden("Cannot reply to a closed ticket.")
        # First reply: record it and move to In Progress if still Open
        if ticket.status == "Open" and not is_internal_note:
            from app.services.state_machine import apply_transition
            apply_transition(ticket, "In Progress", author.role)
            if not ticket.first_response_at:
                ticket.first_response_at = clock.now()

    now = clock.now()
    msg = TicketMessage(
        ticket_id=ticket.id,
        author_id=author.id,
        body=body,
        is_internal_note=is_internal_note,
        created_at=now,
    )
    db.add(msg)

    # Update last activity
    if author.role == "member":
        ticket.last_member_activity_at = now
    ticket.updated_at = now

    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=author.id,
        event_type="note_added" if is_internal_note else "message_sent",
    )

    if not _skip_commit:
        db.commit()
        db.refresh(msg)
    return msg
