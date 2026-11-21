"""Common Pydantic schemas: pagination, error envelope."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None
    allowed: list[str] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
