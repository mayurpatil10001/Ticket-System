"""Ticket model."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import TZDateTime
from app.models.base import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "category IN ('Payment','Profile change','Survey issue','Eligibility','Other')",
            name="ck_tickets_category",
        ),
        CheckConstraint(
            "priority IN ('Low','Medium','High')",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            "status IN ('Open','In Progress','Resolved','Closed','Reopened','Escalated')",
            name="ck_tickets_status",
        ),
        Index("ix_tickets_status_due_at", "status", "due_at"),
        Index("ix_tickets_member_created", "member_id", "created_at"),
        Index("ix_tickets_assignee_status", "assignee_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="Open")
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    survey_ref: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    requested_field: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    requested_value: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    tat_minutes_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    due_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    tat_clock_started_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    awaiting_member: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    paused_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    paused_seconds_working: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    queued_for_next_shift: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    reopen_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    first_response_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    last_member_activity_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    member: Mapped["User"] = relationship("User", foreign_keys=[member_id], back_populates="owned_tickets")  # type: ignore
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tickets")  # type: ignore
    messages: Mapped[List["TicketMessage"]] = relationship("TicketMessage", back_populates="ticket", lazy="select", order_by="TicketMessage.created_at", uselist=True)  # type: ignore
    events: Mapped[List["TicketEvent"]] = relationship("TicketEvent", back_populates="ticket", lazy="select", order_by="TicketEvent.created_at", uselist=True)  # type: ignore
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="ticket", lazy="select", uselist=True)  # type: ignore
    internal_tickets: Mapped[List["InternalTicket"]] = relationship("InternalTicket", back_populates="parent_ticket", lazy="select", uselist=True)  # type: ignore

    def __repr__(self) -> str:
        return f"<Ticket {self.public_id} status={self.status}>"
