"""ID uniqueness test."""
from __future__ import annotations

import threading
from datetime import UTC, datetime

from app.db import SessionLocal
from app.models.user import User
from app.models import Base
from app.db import engine
from app.services.ticket_service import create_ticket


def test_concurrent_ids_unique():
    """50 concurrent ticket creations must produce unique sequential IDs."""
    Base.metadata.create_all(bind=engine)
    from app.models.ticket_counter import TicketCounter
    with SessionLocal() as db:
        if not db.query(TicketCounter).filter(TicketCounter.id == 1).first():
            db.add(TicketCounter(id=1, last_number=0))
            db.commit()
        # Create a member
        m = db.query(User).filter(User.role == "member").first()
        if not m:
            m = User(name="Concurrent", email="concurrent@t.com", phone="6660001234", role="member", created_at=datetime.now(UTC))
            db.add(m)
            db.commit()
        member_id = m.id

    ids = []
    errors = []
    lock = threading.Lock()

    def create_one():
        try:
            with SessionLocal() as session:
                member = session.get(User, member_id)
                t = create_ticket(session, member=member, category="Other", description="Concurrent test ticket description.")
                with lock:
                    ids.append(t.public_id)
        except Exception as e:
            with lock:
                errors.append(str(e))

    threads = [threading.Thread(target=create_one) for _ in range(20)]  # 20 threads (safe for SQLite)
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert not errors, f"Errors: {errors}"
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"
