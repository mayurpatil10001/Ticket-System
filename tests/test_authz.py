"""Authorization matrix tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def seeded_client(app_client, db):
    """Client with seeded users in the test DB."""
    from datetime import UTC, datetime
    from app.models.user import User

    now = datetime.now(UTC)
    head = User(name="TestHead", email="thead@ci.com", phone="5550001", role="head", is_active=True, created_at=now)
    agent = User(name="TestAgent", email="tagent@ci.com", phone="5550002", role="agent", is_active=True, created_at=now)
    member = User(name="TestMember", email="tmember@ci.com", phone="5550003", role="member", is_active=True, created_at=now)
    member2 = User(name="OtherMember", email="tmember2@ci.com", phone="5550004", role="member", is_active=True, created_at=now)
    db.add_all([head, agent, member, member2])
    db.flush()
    db.commit()
    return app_client, {"head": head, "agent": agent, "member": member, "member2": member2}


def login(client, user_id):
    client.post("/api/auth/login", json={"user_id": user_id})


def test_member_cannot_see_other_member_ticket(seeded_client, db):
    client, users = seeded_client
    from datetime import UTC, datetime
    from app.models.ticket import Ticket

    # Create ticket as member2
    t = Ticket(
        public_id="TKT-AZ01", member_id=users["member2"].id, category="Payment",
        priority="High", status="Open", subject="Test", description="Description here.",
        tat_minutes_snapshot=240,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        last_member_activity_at=datetime.now(UTC),
    )
    db.add(t)
    db.commit()

    # Login as member (not member2)
    login(client, users["member"].id)
    r = client.get("/api/tickets/TKT-AZ01")
    assert r.status_code == 404  # Must not leak existence


def test_agent_can_see_all_tickets(seeded_client, db):
    client, users = seeded_client
    from datetime import UTC, datetime
    from app.models.ticket import Ticket

    t = Ticket(
        public_id="TKT-AZ02", member_id=users["member"].id, category="Eligibility",
        priority="Medium", status="Open", subject="Test", description="Test description here.",
        tat_minutes_snapshot=1440,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        last_member_activity_at=datetime.now(UTC),
    )
    db.add(t)
    db.commit()

    login(client, users["agent"].id)
    r = client.get("/api/tickets/TKT-AZ02")
    assert r.status_code == 200


def test_member_cannot_resolve(seeded_client, db):
    client, users = seeded_client
    from datetime import UTC, datetime
    from app.models.ticket import Ticket

    t = Ticket(
        public_id="TKT-AZ03", member_id=users["member"].id, category="Other",
        priority="Low", status="In Progress", subject="Test", description="Test description.",
        tat_minutes_snapshot=2880,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        last_member_activity_at=datetime.now(UTC),
    )
    db.add(t)
    db.commit()

    login(client, users["member"].id)
    r = client.post("/api/tickets/TKT-AZ03/resolve", json={"message": "Resolved by member"})
    assert r.status_code in (403, 422, 409)


def test_unauthenticated_blocked(seeded_client):
    client, _ = seeded_client
    client.cookies.clear()
    r = client.get("/api/tickets")
    assert r.status_code == 403


def test_settings_requires_head(seeded_client):
    client, users = seeded_client
    login(client, users["agent"].id)
    r = client.get("/api/settings")
    assert r.status_code == 403


def test_member_cannot_create_internal_ticket(seeded_client, db):
    client, users = seeded_client
    from datetime import UTC, datetime
    from app.models.ticket import Ticket

    t = Ticket(
        public_id="TKT-AZ04", member_id=users["member"].id, category="Payment",
        priority="High", status="Open", subject="Int test", description="Test description here.",
        tat_minutes_snapshot=240,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        last_member_activity_at=datetime.now(UTC),
    )
    db.add(t)
    db.commit()

    login(client, users["member"].id)
    r = client.post("/api/tickets/TKT-AZ04/internal-tickets", json={"team": "Finance", "title": "Test", "note": "Test note"})
    assert r.status_code in (403, 404)
