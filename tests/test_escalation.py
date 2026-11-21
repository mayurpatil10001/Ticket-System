"""Escalation sweep tests."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models.notification import Notification
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.models.user import User
from app.services.escalation import escalation_sweep


def _make_head(db, suffix=""):
    u = User(name=f"Head{suffix}", email=f"head{suffix}@ci.com", phone=f"88800{suffix[:5]}",
             role="head", is_active=True, created_at=datetime.now(UTC))
    db.add(u)
    db.flush()
    return u


def _make_overdue_ticket(db, member_id, status="Open"):
    now = datetime.now(UTC)
    t = Ticket(
        public_id=f"TKT-ESC{id(member_id)}", member_id=member_id, category="Payment",
        priority="High", status=status, subject="Overdue test", description="Overdue ticket description.",
        tat_minutes_snapshot=240,
        due_at=now - timedelta(hours=2),
        awaiting_member=False,
        tat_clock_started_at=now - timedelta(hours=6),
        created_at=now - timedelta(hours=6),
        updated_at=now - timedelta(hours=2),
        last_member_activity_at=now - timedelta(hours=6),
    )
    db.add(t)
    db.flush()
    return t


def test_breach_escalates(db):
    head = _make_head(db, "e1")
    m = User(name="Mem1", email="mem1@t.com", phone="777001e1", role="member", created_at=datetime.now(UTC))
    db.add(m)
    db.flush()

    t = _make_overdue_ticket(db, m.id)
    count = escalation_sweep(db)
    db.refresh(t)
    assert count >= 1
    assert t.status == "Escalated"


def test_sweep_twice_no_duplicates(db):
    head = _make_head(db, "e2")
    m = User(name="Mem2", email="mem2@t.com", phone="7770002e2", role="member", created_at=datetime.now(UTC))
    db.add(m)
    db.flush()

    t = _make_overdue_ticket(db, m.id)
    escalation_sweep(db)
    escalation_sweep(db)

    events = db.query(TicketEvent).filter(TicketEvent.ticket_id == t.id, TicketEvent.event_type == "escalated").all()
    assert len(events) == 1

    notifs = db.query(Notification).filter(Notification.ticket_id == t.id, Notification.kind == "escalated").all()
    assert len(notifs) <= 1


def test_awaiting_member_skipped(db):
    m = User(name="Mem3", email="mem3@t.com", phone="777003e3", role="member", created_at=datetime.now(UTC))
    db.add(m)
    db.flush()

    t = _make_overdue_ticket(db, m.id)
    t.awaiting_member = True
    db.flush()

    count = escalation_sweep(db)
    db.refresh(t)
    assert t.status == "Open"  # Not escalated
