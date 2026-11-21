"""
TAT (Time-to-Action) pure functions.

All functions are pure: no DB access, no calls to clock.now().
They accept a WorkCalendar dataclass and datetime objects.
All datetime inputs must be timezone-aware UTC.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

IST = ZoneInfo("Asia/Kolkata")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkCalendar:
    """
    Immutable representation of the working calendar loaded from settings.

    working_days: list of weekday ints (0=Mon, 6=Sun). Default Mon-Sat = [0,1,2,3,4,5]
    start_hour, start_minute: start of working window in IST
    end_hour, end_minute: end of working window in IST
    holidays: set of date objects (IST date)
    """

    working_days: tuple[int, ...] = (0, 1, 2, 3, 4, 5)  # Mon–Sat
    start_hour: int = 9
    start_minute: int = 0
    end_hour: int = 21
    end_minute: int = 0
    holidays: frozenset[date] = field(default_factory=frozenset)

    def is_working_day(self, d: date) -> bool:
        return d.weekday() in self.working_days and d not in self.holidays

    def window_start(self, d: date) -> datetime:
        """Return the start of the working window on date d, as UTC."""
        ist_dt = datetime(d.year, d.month, d.day, self.start_hour, self.start_minute, tzinfo=IST)
        return ist_dt.astimezone(UTC)

    def window_end(self, d: date) -> datetime:
        """Return the end of the working window on date d, as UTC."""
        ist_dt = datetime(d.year, d.month, d.day, self.end_hour, self.end_minute, tzinfo=IST)
        return ist_dt.astimezone(UTC)

    def window_minutes(self) -> int:
        """Total working minutes in one day."""
        start = datetime(2000, 1, 1, self.start_hour, self.start_minute)
        end = datetime(2000, 1, 1, self.end_hour, self.end_minute)
        return int((end - start).total_seconds() // 60)


def is_working_instant(dt: datetime, cal: WorkCalendar) -> bool:
    """Return True if dt falls strictly inside the working window (start <= dt < end)."""
    ist = dt.astimezone(IST)
    d = ist.date()
    if not cal.is_working_day(d):
        return False
    ws = cal.window_start(d)
    we = cal.window_end(d)
    return ws <= dt < we


def next_working_start(dt: datetime, cal: WorkCalendar) -> datetime:
    """
    If dt is inside working hours, return dt unchanged.
    Otherwise return the next working-window start (09:00 IST on the next working day).
    """
    if is_working_instant(dt, cal):
        return dt
    ist = dt.astimezone(IST)
    d = ist.date()
    # If we're before today's window start and it's a working day, snap to today's start
    if cal.is_working_day(d):
        ws = cal.window_start(d)
        if dt < ws:
            return ws
    # Otherwise walk forward day by day
    candidate = d + timedelta(days=1)
    for _ in range(400):  # guard against infinite loop
        if cal.is_working_day(candidate):
            return cal.window_start(candidate)
        candidate += timedelta(days=1)
    raise ValueError("No working day found within 400 days — check WorkCalendar configuration.")


def add_working_time(start: datetime, minutes: int, cal: WorkCalendar) -> datetime:
    """
    Add `minutes` of working time to `start`, respecting the WorkCalendar.
    Returns the resulting UTC datetime.
    """
    if minutes <= 0:
        return start

    cursor = next_working_start(start, cal)
    remaining = minutes

    for _ in range(10_000):  # guard: 10 000 day-windows covers decades
        ist = cursor.astimezone(IST)
        d = ist.date()
        window_end = cal.window_end(d)
        available = int((window_end - cursor).total_seconds() // 60)

        if available <= 0:
            # Exactly at or past window end — jump to next working day
            cursor = next_working_start(window_end + timedelta(seconds=1), cal)
            continue

        if remaining <= available:
            return cursor + timedelta(minutes=remaining)

        remaining -= available
        cursor = next_working_start(window_end + timedelta(seconds=1), cal)

    raise ValueError("add_working_time did not converge — TAT too large or calendar misconfigured.")


def working_minutes_between(a: datetime, b: datetime, cal: WorkCalendar) -> int:
    """
    Count working minutes strictly between a and b (a < b).
    Returns 0 if b <= a or neither is in a working period.
    """
    if b <= a:
        return 0

    total = 0
    cursor = next_working_start(a, cal) if not is_working_instant(a, cal) else a

    for _ in range(10_000):
        if cursor >= b:
            break
        ist = cursor.astimezone(IST)
        d = ist.date()
        window_end = cal.window_end(d)
        chunk_end = min(window_end, b)
        chunk_minutes = int((chunk_end - cursor).total_seconds() // 60)
        total += chunk_minutes
        if chunk_end >= b:
            break
        cursor = next_working_start(window_end + timedelta(seconds=1), cal)

    return total


def compute_due_at(
    clock_started_at: datetime,
    tat_minutes: int,
    paused_seconds_working: int,
    cal: WorkCalendar,
    mode: str = "working_hours",
) -> datetime:
    """
    Compute the due_at datetime for a ticket.

    Args:
        clock_started_at: When the TAT clock started (UTC, timezone-aware).
        tat_minutes: Base TAT in minutes (snapshot from priority at time of creation/reopen).
        paused_seconds_working: Total working time (in seconds) the clock was paused.
        cal: The working calendar.
        mode: "working_hours" (default) or "24x7".

    Returns:
        due_at as timezone-aware UTC datetime.
    """
    total_minutes = tat_minutes + (paused_seconds_working // 60)

    if mode == "24x7":
        return clock_started_at + timedelta(minutes=total_minutes)
    else:
        return add_working_time(clock_started_at, total_minutes, cal)


def is_queued_for_next_shift(submit_time: datetime, cal: WorkCalendar) -> bool:
    """Return True if submit_time is outside working hours."""
    return not is_working_instant(submit_time, cal)


def clock_start_for_ticket(submit_time: datetime, cal: WorkCalendar) -> datetime:
    """
    Return the effective TAT clock start:
    - If inside working hours: submit_time.
    - If outside: the next working-window start.
    """
    return next_working_start(submit_time, cal)
