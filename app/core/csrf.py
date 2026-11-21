"""CSRF token generation and verification for form POSTs."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from starlette.requests import Request

from app.core.config import config

_TOKEN_MAX_AGE = 3600  # 1 hour


def _sign(value: str) -> str:
    return hmac.new(config.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def generate_csrf_token(request: Request) -> str:
    """Generate a time-stamped CSRF token and store it in the session."""
    token = secrets.token_urlsafe(32)
    ts = str(int(time.time()))
    signed = f"{ts}:{token}:{_sign(ts + token)}"
    request.session["csrf_token"] = signed
    return signed


def verify_csrf_token(request: Request, submitted: str | None) -> bool:
    """Return True if the submitted token matches the session token and is fresh."""
    stored = request.session.get("csrf_token")
    if not stored or not submitted:
        return False
    if not hmac.compare_digest(stored, submitted):
        return False
    try:
        ts, _, _ = stored.split(":", 2)
        if time.time() - int(ts) > _TOKEN_MAX_AGE:
            return False
    except (ValueError, TypeError):
        return False
    return True


def get_csrf_token(request: Request) -> str:
    """Return existing token from session, or generate a fresh one."""
    stored = request.session.get("csrf_token", "")
    if stored:
        try:
            ts, _, _ = stored.split(":", 2)
            if time.time() - int(ts) <= _TOKEN_MAX_AGE:
                return stored
        except (ValueError, TypeError):
            pass
    return generate_csrf_token(request)
