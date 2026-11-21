"""Security helpers: current user extraction and role enforcement."""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import Forbidden, NotFound
from app.db import get_db
from app.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Extract the logged-in user from the session. Raises Forbidden if not logged in."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise Forbidden("You must be logged in to access this resource.")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        request.session.clear()
        raise Forbidden("Session expired. Please log in again.")
    return user


def require_role(*roles: str):
    """FastAPI dependency factory that enforces one of the given roles."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise Forbidden(
                f"This action requires one of these roles: {list(roles)}. "
                f"Your role is '{user.role}'."
            )
        return user

    return _dep


def require_member(user: User = Depends(get_current_user)) -> User:
    return require_role("member")(user)


def require_agent_or_head(user: User = Depends(get_current_user)) -> User:
    return require_role("agent", "head")(user)


def require_head(user: User = Depends(get_current_user)) -> User:
    return require_role("head")(user)
