"""
Clock abstraction — the single source of `now()` for all services.

Usage in production:
    from app.core.clock import clock
    now = clock.now()   # timezone-aware UTC datetime

Usage in tests:
    from app.core.clock import clock
    clock.set_offset(timedelta(hours=5))  # shift forward 5 hours
    clock.reset()

The fast-forward CLI tool (app/tools/fast_forward.py) writes an offset
to a small file read by _FileOffsetClock so the running server picks it up.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol


OFFSET_FILE = Path(".clock_offset")


class ClockProtocol(Protocol):
    def now(self) -> datetime: ...


class _LiveClock:
    """Real clock — returns actual UTC time, optionally shifted by an offset file."""

    def now(self) -> datetime:
        base = datetime.now(UTC)
        if OFFSET_FILE.exists():
            try:
                data = json.loads(OFFSET_FILE.read_text())
                offset_seconds = float(data.get("offset_seconds", 0))
                return base + timedelta(seconds=offset_seconds)
            except Exception:
                pass
        return base

    # --- test/tooling helpers (also work in-process) ---
    _in_process_offset: timedelta = timedelta(0)

    def set_offset(self, delta: timedelta) -> None:
        self._in_process_offset = delta

    def reset(self) -> None:
        self._in_process_offset = timedelta(0)
        if OFFSET_FILE.exists():
            OFFSET_FILE.unlink()

    def now_with_in_process_offset(self) -> datetime:
        return datetime.now(UTC) + self._in_process_offset


# Singleton used throughout the application
clock = _LiveClock()
