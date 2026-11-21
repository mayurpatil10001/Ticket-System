"""State machine transition tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import IllegalTransition, ReasonRequired
from app.services.state_machine import validate_transition


# (from, to, actor, reason, should_pass)
TRANSITION_TABLE = [
    # Allowed transitions
    ("Open", "In Progress", "agent", None, True),
    ("Open", "In Progress", "head", None, True),
    ("Open", "Escalated", "system", "TAT breached: target 240 min elapsed 300 min.", True),
    ("Open", "Resolved", "agent", None, True),
    ("In Progress", "Escalated", "system", "TAT breached: 5 hours overdue now.", True),
    ("In Progress", "Resolved", "agent", None, True),
    ("In Progress", "Resolved", "head", None, True),
    ("Escalated", "In Progress", "agent", None, True),
    ("Escalated", "In Progress", "head", None, True),
    ("Escalated", "Resolved", "agent", None, True),
    ("Resolved", "Closed", "member", None, True),
    ("Resolved", "Closed", "system", None, True),
    ("Resolved", "Reopened", "member", "Payment still not received in my UPI.", True),
    ("Reopened", "In Progress", "agent", None, True),
    ("Reopened", "Escalated", "system", "TAT breached again after reopen event.", True),
    ("Reopened", "Resolved", "agent", None, True),

    # Blocked by actor
    ("Open", "In Progress", "member", None, False),
    ("Resolved", "Reopened", "agent", "some reason here ok", False),
    ("Resolved", "Closed", "agent", None, False),
    ("Closed", "Open", "agent", None, False),
    ("Closed", "Resolved", "member", None, False),

    # Blocked by missing/short reason
    ("Open", "Escalated", "system", None, False),
    ("Open", "Escalated", "system", "    ", False),
    ("Resolved", "Reopened", "member", "ok", False),  # < 5 chars
    ("In Progress", "Escalated", "system", "nope", False),  # 4 chars

    # Non-existent transition
    ("Open", "Closed", "agent", None, False),
    ("Resolved", "In Progress", "agent", None, False),
]


@pytest.mark.parametrize("from_s,to_s,actor,reason,should_pass", TRANSITION_TABLE)
def test_transition(from_s, to_s, actor, reason, should_pass):
    if should_pass:
        validate_transition(from_s, to_s, actor, reason)  # should not raise
    else:
        with pytest.raises((IllegalTransition, ReasonRequired)):
            validate_transition(from_s, to_s, actor, reason)
