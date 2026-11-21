"""Reason enforcement tests at Pydantic, service, and DB levels."""
from __future__ import annotations

import pytest

from app.core.exceptions import ReasonRequired
from app.schemas.ticket import PriorityChangeRequest, ReopenRequest


class TestPydanticValidation:
    def test_reopen_no_reason_fails(self):
        with pytest.raises(Exception):
            ReopenRequest(reason="")

    def test_reopen_short_reason_fails(self):
        with pytest.raises(Exception):
            ReopenRequest(reason="    ")

    def test_reopen_valid_reason(self):
        r = ReopenRequest(reason="Still not paid after resolution.")
        assert len(r.reason) >= 5

    def test_priority_no_reason_fails(self):
        with pytest.raises(Exception):
            PriorityChangeRequest(priority="High", reason="ok")  # 2 chars

    def test_priority_valid(self):
        r = PriorityChangeRequest(priority="High", reason="Urgent due to SLA breach now.")
        assert r.reason


class TestServiceLayer:
    def test_change_priority_no_reason_raises(self, db):
        from app.models.user import User
        from app.models.ticket import Ticket
        from app.services.ticket_service import change_priority

        agent = User(name="A", email="a@t.com", phone="1111111111", role="agent", created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        db.add(agent)
        db.flush()

        ticket = Ticket(
            public_id="TKT-R001", member_id=agent.id, category="Payment",
            priority="Medium", status="Open", subject="Test", description="Test description here.",
            tat_minutes_snapshot=240,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db.add(ticket)
        db.flush()

        with pytest.raises(ReasonRequired):
            change_priority(db, ticket=ticket, new_priority="High", reason="ab", actor=agent)
