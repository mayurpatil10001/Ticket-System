"""Pydantic schemas for auth."""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    user_id: int | None = None
    email: str | None = None
    password: str | None = None

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str | None) -> str | None:
        return v.strip().lower() if v else None


class PasswordLoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class SavedReplyCreateRequest(BaseModel):
    title: str
    body: str
    category: str | None = None


class SavedReplyUpdateRequest(BaseModel):
    title: str
    body: str
    category: str | None = None
