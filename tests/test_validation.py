"""Input validation tests."""
from __future__ import annotations

import pytest


def test_empty_description_rejected():
    from app.schemas.ticket import TicketCreateRequest
    with pytest.raises(Exception):
        TicketCreateRequest(category="Payment", description="")


def test_whitespace_only_rejected():
    from app.schemas.ticket import TicketCreateRequest
    with pytest.raises(Exception):
        TicketCreateRequest(category="Payment", description="   ")


def test_oversized_description_rejected():
    from app.schemas.ticket import TicketCreateRequest
    with pytest.raises(Exception):
        TicketCreateRequest(category="Payment", description="A" * 2001)


def test_invalid_category_rejected():
    from app.schemas.ticket import TicketCreateRequest
    with pytest.raises(Exception):
        TicketCreateRequest(category="Hacking", description="Valid description here.")


def test_invalid_upi_rejected():
    from app.schemas.ticket import TicketCreateRequest
    with pytest.raises(Exception):
        TicketCreateRequest(
            category="Profile change",
            description="Please update my UPI.",
            requested_field="UPI ID",
            requested_value="not-a-valid-upi",
        )


def test_valid_upi_accepted():
    from app.schemas.ticket import TicketCreateRequest
    r = TicketCreateRequest(
        category="Profile change",
        description="Please update my UPI.",
        requested_field="UPI ID",
        requested_value="priya.nair@okaxis",
    )
    assert r.requested_value == "priya.nair@okaxis"


def test_underage_dob_rejected():
    from app.schemas.ticket import TicketCreateRequest
    with pytest.raises(Exception):
        TicketCreateRequest(
            category="Profile change",
            description="Please update my DOB.",
            requested_field="Date of birth",
            requested_value="2015-01-01",
        )


def test_html_stripped_in_service(db):
    """HTML tags should be stripped before storage."""
    from datetime import UTC, datetime
    from app.models.user import User
    from app.services.ticket_service import create_ticket

    m = User(name="HTMLTest", email="html@t.com", phone="4440001234",
             role="member", created_at=datetime.now(UTC))
    db.add(m)
    db.flush()

    t = create_ticket(db, member=m, category="Other",
                      description="<script>alert('xss')</script>Normal description text here.")
    assert "<script>" not in t.description
    assert "Normal description text here." in t.description


def test_unicode_accepted(db):
    from datetime import UTC, datetime
    from app.models.user import User
    from app.services.ticket_service import create_ticket

    m = User(name="UnicodeTest", email="uni@t.com", phone="4440005678",
             role="member", created_at=datetime.now(UTC))
    db.add(m)
    db.flush()

    t = create_ticket(db, member=m, category="Other",
                      description="मुझे भुगतान नहीं मिला। कृपया जांच करें।")
    assert t.public_id.startswith("TKT-")
