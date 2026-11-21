"""Reopen rules: window, max reopens, TAT reset."""
from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta

from app.core.exceptions import ReopenWindowClosed
from app.models.user import User
from app.models.ticket import Ticket
from app.services.ticket_service import reopen_ticket


def _make_member(db, suffix=""):
    u = User(name=f"M{suffix}", email=f"m{suffix}@t.com", phone=f"99900{suffix[:5]}",
             role="member", created_at=datetime.now(UTC))
    db.add(u)
    db.flush()
    return u


def _make_resolved_ticket(db, member, resolved_days_ago=1, reopen_count=0):
    now = datetime.now(UTC)
    t = Ticket(
        public_id=f"TKT-RE{id(member)}", member_id=member.id, category="Payment",
        priority="High", status="Resolved", subject="Test", description="Test reopen description.",
        tat_minutes_snapshot=240,
        resolved_at=now - timedelta(days=resolved_days_ago),
        reopen_count=reopen_count,
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=1),
        last_member_activity_at=now - timedelta(days=1),
    )
    db.add(t)
    db.flush()
    return t


def test_reopen_within_window(db):
    m = _make_member(db, "rw1")
    t = _make_resolved_ticket(db, m, resolved_days_ago=2)
    t2 = reopen_ticket(db, ticket=t, reason="Payment still not received in my account.", actor=m)
    assert t2.status == "Reopened"
    assert t2.reopen_count == 1


def test_reopen_window_expired(db):
    m = _make_member(db, "rw2")
    t = _make_resolved_ticket(db, m, resolved_days_ago=10)
    with pytest.raises(ReopenWindowClosed):
        reopen_ticket(db, ticket=t, reason="Window expired but trying anyway here.", actor=m)


def test_reopen_max_reached(db):
    m = _make_member(db, "rw3")
    t = _make_resolved_ticket(db, m, resolved_days_ago=1, reopen_count=2)
    with pytest.raises(ReopenWindowClosed):
        reopen_ticket(db, ticket=t, reason="Trying to reopen beyond max limit.", actor=m)


def test_reopen_last_allowed(db):
    m = _make_member(db, "rw4")
    t = _make_resolved_ticket(db, m, resolved_days_ago=1, reopen_count=1)
    t2 = reopen_ticket(db, ticket=t, reason="One reopen remaining, using it now.", actor=m)
    assert t2.reopen_count == 2


def test_reopen_resets_tat(db):
    m = _make_member(db, "rw5")
    t = _make_resolved_ticket(db, m, resolved_days_ago=1)
    old_due = t.due_at
    reopen_ticket(db, ticket=t, reason="TAT should reset after this reopen now.", actor=m)
    # due_at should be freshly computed (None originally, now set)
    assert t.due_at is not None
