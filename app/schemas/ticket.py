"""Pydantic v2 schemas for tickets."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

_UPI_RE = re.compile(r"^[\w.\-]{2,256}@[a-zA-Z]{2,64}$")

VALID_CATEGORIES = ("Payment", "Profile change", "Survey issue", "Eligibility", "Other")
VALID_PRIORITIES = ("Low", "Medium", "High")
VALID_FIELDS = ("Name", "City", "Date of birth", "UPI ID")


class TicketCreateRequest(BaseModel):
    category: str
    description: str
    survey_ref: Optional[str] = None
    requested_field: Optional[str] = None
    requested_value: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Category must be one of: {VALID_CATEGORIES}")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Description must be at least 10 characters.")
        if len(v) > 2000:
            raise ValueError("Description must be at most 2000 characters.")
        return v

    @field_validator("requested_field")
    @classmethod
    def validate_requested_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_FIELDS:
            raise ValueError(f"Requested field must be one of: {VALID_FIELDS}")
        return v

    @model_validator(mode="after")
    def validate_profile_change(self) -> "TicketCreateRequest":
        if self.category == "Profile change":
            if not self.requested_field:
                raise ValueError("requested_field is required for Profile change tickets.")
            if not self.requested_value or not self.requested_value.strip():
                raise ValueError("requested_value is required for Profile change tickets.")
            if self.requested_field == "UPI ID":
                if not _UPI_RE.match(self.requested_value.strip()):
                    raise ValueError("Invalid UPI ID format. Expected: name@bank")
            if self.requested_field == "Date of birth":
                import datetime as _dt
                try:
                    dob = _dt.date.fromisoformat(self.requested_value.strip())
                    today = _dt.date.today()
                    age = (today - dob).days // 365
                    if age < 18:
                        raise ValueError("Date of birth: must be at least 18 years old.")
                    if dob > today:
                        raise ValueError("Date of birth cannot be in the future.")
                except ValueError as e:
                    if "fromisoformat" in str(e) or "invalid" in str(e).lower():
                        raise ValueError("Date of birth must be in YYYY-MM-DD format.")
                    raise
        return self


class PriorityChangeRequest(BaseModel):
    priority: str
    reason: str

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITIES:
            raise ValueError(f"Priority must be one of: {VALID_PRIORITIES}")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Reason must be at least 5 characters.")
        return v.strip()


class ReopenRequest(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Reason must be at least 5 characters.")
        return v.strip()


class MessageRequest(BaseModel):
    body: str
    is_internal_note: bool = False

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message body cannot be empty.")
        if len(v) > 2000:
            raise ValueError("Message must be at most 2000 characters.")
        return v


class RequestInfoRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Please provide the information you need from the member.")
        return v


class ResolveRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("A closing message is required when resolving a ticket.")
        return v


class AssignRequest(BaseModel):
    assignee_id: int


class InternalTicketRequest(BaseModel):
    team: str
    title: str
    note: str

    @field_validator("team")
    @classmethod
    def validate_team(cls, v: str) -> str:
        if v not in ("Rewards", "Tech", "Finance"):
            raise ValueError("Team must be one of: Rewards, Tech, Finance")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title is required.")
        return v.strip()
