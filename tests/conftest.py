"""pytest configuration and fixtures."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.clock import clock
from app.db import get_db
from app.models import Base
from app.models.ticket_counter import TicketCounter


@pytest.fixture
def db():
    """Per-test in-memory SQLite — clean slate each time."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    from sqlalchemy import event

    @event.listens_for(eng, "connect")
    def _pragmas(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng, autocommit=False, autoflush=False)
    session = Session()
    # Seed counter
    session.add(TicketCounter(id=1, last_number=0))
    session.commit()
    yield session
    session.close()
    eng.dispose()


@pytest.fixture
def app_client(db):
    from app.main import app

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_clock():
    """Controllable clock fixture."""
    clock.reset()
    yield clock
    clock.reset()
