"""InternalTicket model — sub-tasks routed to Rewards / Tech / Finance."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import TZDateTime
from app.models.base import Base


class InternalTicket(Base):
    __tablename__ = "internal_tickets"
    __table_args__ = (
        CheckConstraint("team IN ('Rewards','Tech','Finance')", name="ck_internal_team"),
        CheckConstraint("status IN ('Open','Done')", name="ck_internal_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    team: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="Open")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    done_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(UTC)
    )
    done_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)

    parent_ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="internal_tickets")  # type: ignore
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])  # type: ignore
    done_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[done_by])  # type: ignore
