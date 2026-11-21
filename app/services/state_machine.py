"""
State machine — single source of truth for ticket status transitions.

All transitions go through `apply_transition()`. Direct writes to
Ticket.status must never happen outside this module.
"""
from __future__ import annotations

from app.core.exceptions import IllegalTransition, ReasonRequired

# ---------------------------------------------------------------------------
# Transition table
# Format: (from_status, to_status) -> {"actors": set, "needs_reason": bool}
# actor "system" = automated sweep; "member", "agent", "head" = humans
# ---------------------------------------------------------------------------
_TRANSITIONS: dict[tuple[str, str], dict] = {
    # (new) → Open: handled at creation, not via this machine
    ("Open", "In Progress"):    {"actors": {"agent", "head"}, "needs_reason": False},
    ("Open", "Escalated"):      {"actors": {"system"},        "needs_reason": True},
    ("Open", "Resolved"):       {"actors": {"agent", "head"}, "needs_reason": False},

    ("In Progress", "Escalated"):  {"actors": {"system"},        "needs_reason": True},
    ("In Progress", "Resolved"):   {"actors": {"agent", "head"}, "needs_reason": False},

    ("Escalated", "In Progress"):  {"actors": {"agent", "head"}, "needs_reason": False},
    ("Escalated", "Resolved"):     {"actors": {"agent", "head"}, "needs_reason": False},
    ("Escalated", "Escalated"):    {"actors": {"system"},        "needs_reason": True},  # re-sweep guard

    ("Resolved", "Closed"):    {"actors": {"member", "system"}, "needs_reason": False},
    ("Resolved", "Reopened"):  {"actors": {"member"},           "needs_reason": True},

    ("Reopened", "In Progress"): {"actors": {"agent", "head"}, "needs_reason": False},
    ("Reopened", "Escalated"):   {"actors": {"system"},        "needs_reason": True},
    ("Reopened", "Resolved"):    {"actors": {"agent", "head"}, "needs_reason": False},

    # Closed is terminal — no transitions out
}

TERMINAL_STATUSES = frozenset({"Closed"})


def allowed_next_statuses(current_status: str, actor_role: str) -> list[str]:
    """Return all statuses the given actor can transition to from current_status."""
    result = []
    for (frm, to), meta in _TRANSITIONS.items():
        if frm == current_status and actor_role in meta["actors"]:
            result.append(to)
    return sorted(set(result))


def validate_transition(
    from_status: str,
    to_status: str,
    actor_role: str,
    reason: str | None = None,
) -> None:
    """
    Validate a proposed transition. Raises:
    - IllegalTransition if the (from, to, actor) combo is not in the table.
    - ReasonRequired if a reason is needed but absent/too short.
    """
    key = (from_status, to_status)
    meta = _TRANSITIONS.get(key)

    if meta is None or actor_role not in meta["actors"]:
        allowed = allowed_next_statuses(from_status, actor_role)
        raise IllegalTransition(from_status, to_status, allowed)

    if meta["needs_reason"]:
        if not reason or len(reason.strip()) < 5:
            raise ReasonRequired("reason")


def apply_transition(
    ticket,  # Ticket ORM object — avoid circular import by keeping untyped
    to_status: str,
    actor_role: str,
    reason: str | None = None,
) -> None:
    """
    Validate and apply a status transition to a Ticket instance.
    The caller is responsible for flushing/committing the session.
    """
    validate_transition(ticket.status, to_status, actor_role, reason)
    ticket.status = to_status
