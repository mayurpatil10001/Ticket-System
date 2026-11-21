"""
Escalation service.

escalation_sweep() is called:
  1. By APScheduler every 60 seconds.
  2. Lazily at the start of queue, dashboard, and notification requests.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.services import event_service, notification_service
from app.services.settings_service import load_settings
from app.services.tat import working_minutes_between

logger = logging.getLogger(__name__)


def escalation_sweep(db: Session) -> int:
    """
    Find all breached tickets and escalate them.
    Idempotent: a ticket that is already Escalated is never re-escalated.
    Returns the count of newly escalated tickets.
    """
    now = clock.now()
    settings = load_settings(db)
    cal = settings.work_calendar

    # Cheap indexed query
    candidates = (
        db.query(Ticket)
        .filter(
            Ticket.status.in_(["Open", "In Progress", "Reopened"]),
            Ticket.awaiting_member.is_(False),
            Ticket.due_at <= now,
        )
        .all()
    )

    escalated_count = 0
    for ticket in candidates:
        # Row-level idempotency check: re-read with an update marker
        rows_updated = db.execute(
            text(
                "UPDATE tickets SET status='Escalated', updated_at=:now "
                "WHERE id=:id AND status IN ('Open','In Progress','Reopened') "
                "AND awaiting_member=0 AND due_at <= :now"
            ),
            {"id": ticket.id, "now": now.isoformat()},
        ).rowcount

        if rows_updated == 0:
            continue  # Already escalated by another sweep — skip

        db.expire(ticket)
        db.refresh(ticket)

        # Build reason string
        if ticket.tat_clock_started_at:
            elapsed = working_minutes_between(ticket.tat_clock_started_at, now, cal)
            reason = (
                f"TAT breached: target {ticket.tat_minutes_snapshot} working min, "
                f"elapsed ~{elapsed} working min."
            )
        else:
            reason = "TAT breached."

        event_service.log_event(
            db,
            ticket_id=ticket.id,
            actor_id=None,
            event_type="escalated",
            from_value=ticket.status if ticket.status != "Escalated" else "Escalated",
            to_value="Escalated",
            reason=reason,
        )

        # Notify all Heads — but only once (check existing unread notification)
        already_notified = (
            db.query(Notification)
            .filter(
                Notification.ticket_id == ticket.id,
                Notification.kind == "escalated",
                Notification.read_at.is_(None),
            )
            .first()
        )
        if not already_notified:
            notification_service.notify_all_heads(
                db,
                ticket_id=ticket.id,
                kind="escalated",
                body=f"{ticket.public_id} escalated — TAT breached.",
            )

        db.commit()
        escalated_count += 1
        logger.info("Escalated ticket %s", ticket.public_id)

    return escalated_count


def auto_resolve_awaiting(db: Session) -> int:
    """
    Auto-resolve tickets where member has not replied within the configured window.
    """
    settings = load_settings(db)
    days = settings.awaiting_member_auto_resolve_days
    now = clock.now()
    cutoff = now - __import__("datetime").timedelta(days=days)

    candidates = (
        db.query(Ticket)
        .filter(
            Ticket.awaiting_member.is_(True),
            Ticket.paused_at <= cutoff,
        )
        .all()
    )

    count = 0
    for ticket in candidates:
        old_status = ticket.status
        ticket.status = "Resolved"
        ticket.awaiting_member = False
        ticket.paused_at = None
        ticket.resolved_at = now
        ticket.updated_at = now

        event_service.log_event(
            db,
            ticket_id=ticket.id,
            actor_id=None,
            event_type="auto_resolved",
            from_value=old_status,
            to_value="Resolved",
            reason=f"No reply from member for {days} days after info request.",
        )
        notification_service.create_notification(
            db,
            user_id=ticket.member_id,
            ticket_id=ticket.id,
            kind="auto_resolved",
            body=(
                f"Your ticket {ticket.public_id} was auto-resolved after {days} days "
                f"with no reply. You may reopen it within {settings.reopen_window_days} days."
            ),
        )
        db.commit()
        count += 1

    return count


def auto_close_resolved(db: Session) -> int:
    """Auto-close tickets that have been Resolved for auto_close_days with no action."""
    settings = load_settings(db)
    days = settings.auto_close_days
    now = clock.now()
    cutoff = now - __import__("datetime").timedelta(days=days)

    candidates = (
        db.query(Ticket)
        .filter(
            Ticket.status == "Resolved",
            Ticket.resolved_at <= cutoff,
        )
        .all()
    )

    count = 0
    for ticket in candidates:
        ticket.status = "Closed"
        ticket.closed_at = now
        ticket.updated_at = now

        event_service.log_event(
            db,
            ticket_id=ticket.id,
            actor_id=None,
            event_type="auto_closed",
            from_value="Resolved",
            to_value="Closed",
            reason=f"Auto-closed after {days} days with no member action.",
        )
        db.commit()
        count += 1

    return count
