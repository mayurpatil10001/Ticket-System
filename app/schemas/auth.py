"""Pydantic schemas for auth."""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    user_id: int


class SavedReplyCreateRequest(BaseModel):
    title: str
    body: str
    category: str | None = None


class SavedReplyUpdateRequest(BaseModel):
    title: str
    body: str
    category: str | None = None
