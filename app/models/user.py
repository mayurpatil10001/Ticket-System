"""User model."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import TZDateTime
from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('member','agent','head')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    upi_id: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dob: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # ISO date YYYY-MM-DD
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    owned_tickets: Mapped[list] = relationship(
        "Ticket", foreign_keys="Ticket.member_id", back_populates="member", lazy="select"
    )
    assigned_tickets: Mapped[list] = relationship(
        "Ticket", foreign_keys="Ticket.assignee_id", back_populates="assignee", lazy="select"
    )
    messages: Mapped[list] = relationship("TicketMessage", back_populates="author", lazy="select")
    events: Mapped[list] = relationship("TicketEvent", back_populates="actor", lazy="select")
    notifications: Mapped[list] = relationship("Notification", back_populates="user", lazy="select")
    saved_replies: Mapped[list] = relationship("SavedReply", back_populates="creator", lazy="select")

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r} role={self.role}>"
