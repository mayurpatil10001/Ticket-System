"""Password hashing helpers (stdlib only — hashlib sha256 + per-user salt)."""
from __future__ import annotations

import hashlib
import secrets
import hmac

# A fixed application pepper (not secret in a demo, but good practice)
_PEPPER = "concave-insights-demo-2025"


def _derive(plain: str, salt: str) -> str:
    """PBKDF2-HMAC-SHA256 — 200k iterations, 32-byte digest, hex-encoded."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        (plain + _PEPPER).encode(),
        salt.encode(),
        iterations=200_000,
        dklen=32,
    )
    return dk.hex()


def hash_password(plain: str) -> str:
    """Return storable 'salt$hash' string."""
    salt = secrets.token_hex(16)
    return f"{salt}${_derive(plain, salt)}"


def verify_password(plain: str, stored: str) -> bool:
    """Return True if plain matches the stored 'salt$hash'."""
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    actual = _derive(plain, salt)
    return hmac.compare_digest(actual, expected)
