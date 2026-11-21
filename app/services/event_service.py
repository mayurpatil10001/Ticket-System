"""Event logging service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.clock import clock
from app.models.ticket_event import TicketEvent


def log_event(
    db: Session,
    *,
    ticket_id: int,
    actor_id: int | None,
    event_type: str,
    from_value: str | None = None,
    to_value: str | None = None,
    reason: str | None = None,
    created_at=None,
) -> TicketEvent:
    """Write a TicketEvent row and add it to the session (not yet flushed)."""
    event = TicketEvent(
        ticket_id=ticket_id,
        actor_id=actor_id,
        event_type=event_type,
        from_value=from_value,
        to_value=to_value,
        reason=reason,
        created_at=created_at if created_at is not None else clock.now(),
    )
    db.add(event)
    return event
