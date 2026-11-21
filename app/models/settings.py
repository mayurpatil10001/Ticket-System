"""Settings key-value store."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import TZDateTime
from app.models.base import Base


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(UTC)
    )

    updater: Mapped[Optional["User"]] = relationship("User")  # type: ignore


class CategoryPriorityMap(Base):
    __tablename__ = "category_priority_map"

    category: Mapped[str] = mapped_column(String(30), primary_key=True)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
