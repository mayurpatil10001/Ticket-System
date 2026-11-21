"""TicketEvent model (audit / history log)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import TZDateTime
from app.models.base import Base

# Valid event types
EVENT_TYPES = (
    "created",
    "status_changed",
    "assigned",
    "priority_changed",
    "escalated",
    "reopened",
    "paused",
    "resumed",
    "auto_resolved",
    "auto_closed",
    "profile_applied",
    "internal_ticket_created",
    "internal_ticket_done",
    "note_added",
    "message_sent",
)


class TicketEvent(Base):
    __tablename__ = "ticket_events"
    __table_args__ = (
        # DB-level enforcement: reason must exist and be non-trivial for sensitive event types
        CheckConstraint(
            """
            NOT (
                event_type IN ('reopened', 'priority_changed', 'escalated')
                AND (reason IS NULL OR length(trim(reason)) < 5)
            )
            """,
            name="ck_events_reason_required",
        ),
        Index("ix_events_ticket_created", "ticket_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(UTC)
    )

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="events")  # type: ignore
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="events")  # type: ignore

    def __repr__(self) -> str:
        return f"<TicketEvent id={self.id} type={self.event_type}>"
