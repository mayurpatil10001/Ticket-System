"""Holiday calendar."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Holiday(Base):
    __tablename__ = "holidays"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD
    label: Mapped[str] = mapped_column(String(200), nullable=False)
