"""
Ticket service — create, assign, priority change, request-info/resume,
resolve, confirm, reopen.
"""
from __future__ import annotations

import re
from datetime import UTC, timedelta
from typing import Optional

import nh3
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.exceptions import (
    Forbidden,
    IllegalTransition,
    NotFound,
    ReasonRequired,
    ReopenWindowClosed,
)
from app.models.ticket import Ticket
from app.models.ticket_counter import TicketCounter
from app.models.user import User
from app.services import event_service, notification_service
from app.services.settings_service import get_priority_for_category, load_settings
from app.services.state_machine import apply_transition
from app.services.tat import (
    clock_start_for_ticket,
    compute_due_at,
    is_queued_for_next_shift,
    working_minutes_between,
)

_UPI_RE = re.compile(r"^[\w.\-]{2,256}@[a-zA-Z]{2,64}$")
MAX_DESCRIPTION = 2000
MIN_DESCRIPTION = 10

CATEGORY_SUBJECTS = {
    "Payment": "Payment not received",
    "Profile change": "Profile change request",
    "Survey issue": "Survey issue",
    "Eligibility": "Eligibility query",
    "Other": "Support query",
}


def _sanitize(text_input: str) -> str:
    return nh3.clean(text_input, tags=set())


def _next_public_id(db: Session) -> str:
    """Thread-safe sequential ID using atomic UPDATE on SQLite."""
    # Atomic increment: UPDATE ticket_counter SET last_number = last_number + 1 WHERE id = 1
    result = db.execute(
        text("UPDATE ticket_counter SET last_number = last_number + 1 WHERE id = 1")
    )
    if result.rowcount == 0:
        db.execute(text("INSERT OR IGNORE INTO ticket_counter (id, last_number) VALUES (1, 1)"))
        db.flush()
        result = db.execute(text("UPDATE ticket_counter SET last_number = last_number + 1 WHERE id = 1 AND last_number = 1"))
    row = db.execute(text("SELECT last_number FROM ticket_counter WHERE id = 1")).fetchone()
    n = row[0]
    db.flush()
    return f"TKT-{n:04d}"


def create_ticket(
    db: Session,
    *,
    member: User,
    category: str,
    description: str,
    survey_ref: Optional[str] = None,
    requested_field: Optional[str] = None,
    requested_value: Optional[str] = None,
) -> Ticket:
    if category not in ("Payment", "Profile change", "Survey issue", "Eligibility", "Other"):
        from app.core.exceptions import Forbidden
        raise ValueError(f"Invalid category: {category!r}")

    description = _sanitize(description.strip())
    if len(description) < MIN_DESCRIPTION:
        raise ValueError(f"Description must be at least {MIN_DESCRIPTION} characters.")
    if len(description) > MAX_DESCRIPTION:
        raise ValueError(f"Description must be at most {MAX_DESCRIPTION} characters.")

    if survey_ref:
        survey_ref = _sanitize(survey_ref.strip())[:300]
    if requested_field:
        requested_field = _sanitize(requested_field.strip())[:50]
    if requested_value:
        requested_value = _sanitize(requested_value.strip())[:300]

    # Validate UPI if that's the field being changed
    if requested_field == "UPI ID" and requested_value:
        if not _UPI_RE.match(requested_value):
            raise ValueError("Invalid UPI ID format. Expected format: name@bank")

    settings = load_settings(db)
    priority = get_priority_for_category(db, category)
    tat_minutes = settings.tat_minutes[priority]
    cal = settings.work_calendar
    mode = settings.tat_mode.get(priority, "working_hours")

    now = clock.now()
    queued = is_queued_for_next_shift(now, cal)
    clock_start = clock_start_for_ticket(now, cal)
    due_at = compute_due_at(clock_start, tat_minutes, 0, cal, mode)

    subject = CATEGORY_SUBJECTS.get(category, "Support query")
    if category == "Profile change" and requested_field:
        subject = f"Profile change: {requested_field}"

    public_id = _next_public_id(db)

    ticket = Ticket(
        public_id=public_id,
        member_id=member.id,
        category=category,
        priority=priority,
        status="Open",
        subject=subject,
        description=description,
        survey_ref=survey_ref,
        requested_field=requested_field,
        requested_value=requested_value,
        tat_minutes_snapshot=tat_minutes,
        due_at=due_at,
        tat_clock_started_at=clock_start,
        awaiting_member=False,
        paused_seconds_working=0,
        queued_for_next_shift=queued,
        reopen_count=0,
        last_member_activity_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(ticket)
    db.flush()

    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=member.id,
        event_type="created",
        to_value="Open",
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def assign_ticket(db: Session, *, ticket: Ticket, assignee: User, actor: User) -> Ticket:
    # Agents can self-assign; heads can assign anyone
    if actor.role == "agent" and assignee.id != actor.id:
        raise Forbidden("Agents can only assign tickets to themselves.")
    if actor.role == "member":
        raise Forbidden("Members cannot assign tickets.")

    old_assignee_id = ticket.assignee_id
    ticket.assignee_id = assignee.id
    ticket.updated_at = clock.now()

    if ticket.status == "Open":
        apply_transition(ticket, "In Progress", actor.role)

    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type="assigned",
        from_value=str(old_assignee_id) if old_assignee_id else None,
        to_value=str(assignee.id),
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def change_priority(
    db: Session,
    *,
    ticket: Ticket,
    new_priority: str,
    reason: str,
    actor: User,
) -> Ticket:
    if actor.role == "member":
        raise Forbidden("Members cannot change ticket priority.")
    if ticket.status == "Closed":
        raise IllegalTransition(ticket.status, ticket.status, [])

    reason = reason.strip()
    if len(reason) < 5:
        raise ReasonRequired("reason")

    settings = load_settings(db)
    old_priority = ticket.priority
    ticket.priority = new_priority
    ticket.tat_minutes_snapshot = settings.tat_minutes[new_priority]

    # Recompute due_at from the original clock start
    if ticket.tat_clock_started_at:
        mode = settings.tat_mode.get(new_priority, "working_hours")
        ticket.due_at = compute_due_at(
            ticket.tat_clock_started_at,
            ticket.tat_minutes_snapshot,
            ticket.paused_seconds_working,
            settings.work_calendar,
            mode,
        )

    ticket.updated_at = clock.now()
    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type="priority_changed",
        from_value=old_priority,
        to_value=new_priority,
        reason=reason,
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def request_info(
    db: Session,
    *,
    ticket: Ticket,
    message: str,
    actor: User,
) -> Ticket:
    """Pause the TAT clock, waiting for member response."""
    if actor.role == "member":
        raise Forbidden("Members cannot request info.")
    if ticket.awaiting_member:
        return ticket  # already paused — idempotent

    now = clock.now()
    ticket.awaiting_member = True
    ticket.paused_at = now
    ticket.updated_at = now

    # Add the message
    from app.services.message_service import add_message
    add_message(db, ticket=ticket, author=actor, body=message, is_internal_note=False, _skip_commit=True)

    event_service.log_event(db, ticket_id=ticket.id, actor_id=actor.id, event_type="paused")
    db.commit()
    db.refresh(ticket)
    return ticket


def resume_clock(db: Session, *, ticket: Ticket, actor: User) -> Ticket:
    """Resume TAT clock after member replies. Called by message_service."""
    if not ticket.awaiting_member or ticket.paused_at is None:
        return ticket

    settings = load_settings(db)
    now = clock.now()
    cal = settings.work_calendar

    paused_working = working_minutes_between(ticket.paused_at, now, cal)
    ticket.paused_seconds_working += paused_working * 60
    ticket.awaiting_member = False
    ticket.paused_at = None

    # Recompute due_at
    if ticket.tat_clock_started_at:
        mode = settings.tat_mode.get(ticket.priority, "working_hours")
        ticket.due_at = compute_due_at(
            ticket.tat_clock_started_at,
            ticket.tat_minutes_snapshot,
            ticket.paused_seconds_working,
            cal,
            mode,
        )
    ticket.updated_at = now

    event_service.log_event(db, ticket_id=ticket.id, actor_id=actor.id, event_type="resumed")
    # Notify assigned agent
    if ticket.assignee_id:
        notification_service.create_notification(
            db,
            user_id=ticket.assignee_id,
            ticket_id=ticket.id,
            kind="member_replied",
            body=f"Member replied to {ticket.public_id}. Clock resumed.",
        )
    return ticket


def resolve_ticket(
    db: Session,
    *,
    ticket: Ticket,
    message: str,
    actor: User,
) -> Ticket:
    if actor.role == "member":
        raise Forbidden("Members cannot resolve tickets.")

    message = message.strip()
    if not message:
        raise ValueError("A closing message is required when resolving a ticket.")

    now = clock.now()
    old_status = ticket.status
    apply_transition(ticket, "Resolved", actor.role)
    ticket.resolved_at = now
    ticket.awaiting_member = False
    ticket.paused_at = None
    ticket.updated_at = now

    from app.services.message_service import add_message
    add_message(db, ticket=ticket, author=actor, body=message, is_internal_note=False, _skip_commit=True)

    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type="status_changed",
        from_value=old_status,
        to_value="Resolved",
    )
    # Notify member
    notification_service.create_notification(
        db,
        user_id=ticket.member_id,
        ticket_id=ticket.id,
        kind="resolved",
        body=f"Your ticket {ticket.public_id} has been resolved. Please confirm or reopen.",
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def confirm_ticket(db: Session, *, ticket: Ticket, actor: User) -> Ticket:
    """Member confirms resolution → Closed."""
    if actor.role != "member":
        raise Forbidden("Only the member can confirm resolution.")
    if actor.id != ticket.member_id:
        raise Forbidden("You can only confirm your own tickets.")

    now = clock.now()
    apply_transition(ticket, "Closed", actor.role)
    ticket.closed_at = now
    ticket.updated_at = now

    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type="status_changed",
        from_value="Resolved",
        to_value="Closed",
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def reopen_ticket(
    db: Session,
    *,
    ticket: Ticket,
    reason: str,
    actor: User,
) -> Ticket:
    """Member reopens a Resolved ticket. Enforces window and limit."""
    if actor.role != "member":
        raise Forbidden("Only the member can reopen tickets.")
    if actor.id != ticket.member_id:
        raise Forbidden("You can only reopen your own tickets.")

    reason = reason.strip()
    if len(reason) < 5:
        raise ReasonRequired("reason")

    settings = load_settings(db)
    now = clock.now()

    # Check window
    if ticket.resolved_at:
        resolved_at = ticket.resolved_at
        if resolved_at.tzinfo is None:
            from datetime import timezone
            resolved_at = resolved_at.replace(tzinfo=timezone.utc)
        window_end = resolved_at + timedelta(days=settings.reopen_window_days)
        if now > window_end:
            raise ReopenWindowClosed(
                f"The reopen window closed on {window_end.isoformat()}. Please raise a new ticket."
            )

    # Check max reopens
    if ticket.reopen_count >= settings.max_reopens:
        raise ReopenWindowClosed(
            f"This ticket has been reopened {ticket.reopen_count} time(s). "
            f"Maximum is {settings.max_reopens}. Please raise a new ticket."
        )

    old_status = ticket.status
    apply_transition(ticket, "Reopened", actor.role, reason)
    ticket.reopen_count += 1
    ticket.resolved_at = None
    ticket.awaiting_member = False
    ticket.paused_at = None
    ticket.paused_seconds_working = 0
    ticket.last_member_activity_at = now
    ticket.updated_at = now

    # Fresh TAT from reopen time
    cal = settings.work_calendar
    mode = settings.tat_mode.get(ticket.priority, "working_hours")
    clock_start = clock_start_for_ticket(now, cal)
    ticket.tat_clock_started_at = clock_start
    ticket.due_at = compute_due_at(clock_start, ticket.tat_minutes_snapshot, 0, cal, mode)

    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type="reopened",
        from_value=old_status,
        to_value="Reopened",
        reason=reason,
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def apply_profile_change(db: Session, *, ticket: Ticket, actor: User) -> Ticket:
    if actor.role == "member":
        raise Forbidden("Members cannot apply profile changes.")

    event_service.log_event(
        db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type="profile_applied",
        to_value=ticket.requested_field,
    )
    ticket.updated_at = clock.now()
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_or_404(db: Session, public_id: str, actor: User) -> Ticket:
    """Return ticket if actor is authorized to see it, else 404."""
    ticket = db.query(Ticket).filter(Ticket.public_id == public_id).first()
    if not ticket:
        raise NotFound("Ticket")
    if actor.role == "member" and ticket.member_id != actor.id:
        # Do not leak existence — return 404
        raise NotFound("Ticket")
    return ticket
