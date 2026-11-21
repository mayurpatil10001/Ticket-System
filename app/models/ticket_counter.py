"""TicketCounter model — single row, incremented under BEGIN IMMEDIATE."""
from __future__ import annotations

from sqlalchemy import Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TicketCounter(Base):
    __tablename__ = "ticket_counter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1, server_default=text("1"))
    last_number: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
