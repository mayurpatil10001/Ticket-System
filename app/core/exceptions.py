"""Custom exception types used across services and routes."""
from __future__ import annotations


class ReasonRequired(ValueError):
    """Raised when a reason is mandatory but absent or too short."""

    def __init__(self, field: str = "reason") -> None:
        self.field = field
        super().__init__(f"A reason of at least 5 characters is required for '{field}'.")


class IllegalTransition(Exception):
    """Raised when a state-machine transition is not allowed."""

    def __init__(self, from_status: str, to_status: str, allowed: list[str]) -> None:
        self.from_status = from_status
        self.to_status = to_status
        self.allowed = allowed
        super().__init__(
            f"Cannot transition from '{from_status}' to '{to_status}'. "
            f"Allowed next states: {allowed or ['none (terminal)']}."
        )


class NotFound(Exception):
    """Resource not found (or hidden from the requesting user)."""

    def __init__(self, resource: str = "Ticket") -> None:
        self.resource = resource
        super().__init__(f"{resource} not found.")


class Forbidden(Exception):
    """Actor does not have permission for this action."""

    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(detail)


class ReopenWindowClosed(Exception):
    """Member attempted to reopen outside the allowed window."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class DuplicateSubmit(Exception):
    """Request appears to be a duplicate within the idempotency window."""
    pass
