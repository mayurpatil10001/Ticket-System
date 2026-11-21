"""TAT pure-function tests."""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from app.services.tat import (
    WorkCalendar,
    add_working_time,
    clock_start_for_ticket,
    compute_due_at,
    is_queued_for_next_shift,
    is_working_instant,
    next_working_start,
    working_minutes_between,
)

IST = ZoneInfo("Asia/Kolkata")


def ist(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=IST).astimezone(UTC)


DEFAULT_CAL = WorkCalendar()  # Mon-Sat 09:00-21:00 IST


class TestIsWorkingInstant:
    def test_inside_window(self):
        assert is_working_instant(ist(2026, 11, 23, 10, 0), DEFAULT_CAL)  # Monday 10:00

    def test_before_window(self):
        assert not is_working_instant(ist(2026, 11, 23, 8, 59), DEFAULT_CAL)

    def test_at_window_end_is_not_working(self):
        assert not is_working_instant(ist(2026, 11, 23, 21, 0), DEFAULT_CAL)

    def test_sunday(self):
        assert not is_working_instant(ist(2026, 11, 22, 12, 0), DEFAULT_CAL)  # Sunday

    def test_holiday(self):
        cal = WorkCalendar(holidays=frozenset([date(2026, 11, 26)]))
        assert not is_working_instant(ist(2026, 11, 26, 10, 0), cal)


class TestNextWorkingStart:
    def test_saturday_11pm_gives_monday_9am(self):
        # Saturday 23:00 IST → Monday 09:00 IST (Sunday off)
        sat_11pm = ist(2026, 11, 21, 23, 0)  # 2026-11-21 is Saturday
        result = next_working_start(sat_11pm, DEFAULT_CAL)
        expected = ist(2026, 11, 23, 9, 0)  # Monday
        assert result == expected

    def test_inside_hours_returns_same(self):
        mon_10am = ist(2026, 11, 23, 10, 0)
        assert next_working_start(mon_10am, DEFAULT_CAL) == mon_10am

    def test_sunday_gives_monday(self):
        sun_noon = ist(2026, 11, 22, 12, 0)
        expected = ist(2026, 11, 23, 9, 0)
        assert next_working_start(sun_noon, DEFAULT_CAL) == expected


class TestAddWorkingTime:
    def test_saturday_11pm_plus_4h_gives_monday_1pm(self):
        # Canonical case from spec
        sat_11pm = ist(2026, 11, 21, 23, 0)
        result = add_working_time(sat_11pm, 240, DEFAULT_CAL)
        expected = ist(2026, 11, 23, 13, 0)  # Monday 13:00 IST
        assert result == expected

    def test_friday_8pm_plus_4h(self):
        # Starts Fri 20:00 on a Mon-Fri calendar: 1h left today, 3h spills to Mon
        # (Using 5-day calendar so Saturday is off)
        fri_fri_cal = WorkCalendar(working_days=(0, 1, 2, 3, 4))  # Mon-Fri
        fri_8pm = ist(2026, 11, 20, 20, 0)  # Friday
        result = add_working_time(fri_8pm, 240, fri_fri_cal)
        # 1h left Friday (until 21:00), 3h remaining on Monday → Mon 09:00+3h = 12:00
        expected = ist(2026, 11, 23, 12, 0)  # Monday 12:00 IST
        assert result == expected

    def test_zero_minutes(self):
        mon_10am = ist(2026, 11, 23, 10, 0)
        assert add_working_time(mon_10am, 0, DEFAULT_CAL) == mon_10am

    def test_exact_window_boundary(self):
        # Starting exactly at 21:00 — zero available today, jumps to next day
        mon_9pm = ist(2026, 11, 23, 21, 0)
        result = add_working_time(mon_9pm, 60, DEFAULT_CAL)
        expected = ist(2026, 11, 24, 10, 0)  # Tuesday 10:00
        assert result == expected

    def test_start_on_holiday(self):
        cal = WorkCalendar(holidays=frozenset([date(2026, 11, 23)]))  # Monday holiday
        mon_10am = ist(2026, 11, 23, 10, 0)
        result = add_working_time(mon_10am, 60, cal)
        expected = ist(2026, 11, 24, 10, 0)  # Tuesday 10:00
        assert result == expected

    def test_start_on_sunday(self):
        sun_noon = ist(2026, 11, 22, 12, 0)
        result = add_working_time(sun_noon, 60, DEFAULT_CAL)
        expected = ist(2026, 11, 23, 10, 0)  # Monday 10:00
        assert result == expected

    def test_48h_low_across_sunday(self):
        # 48 working hours = 4 working days (Mon–Thu)
        mon_9am = ist(2026, 11, 23, 9, 0)
        result = add_working_time(mon_9am, 48 * 60, DEFAULT_CAL)
        # Mon 12h + Tue 12h + Wed 12h + Thu 12h = 48h, Thu 21:00
        expected = ist(2026, 11, 26, 21, 0)
        # Thu 2026-11-26 is a holiday in our seed but NOT in DEFAULT_CAL
        assert result == expected

    def test_24x7_mode(self):
        sat_11pm = ist(2026, 11, 21, 23, 0)
        result = compute_due_at(sat_11pm, 240, 0, DEFAULT_CAL, mode="24x7")
        expected = sat_11pm.astimezone(UTC) + __import__("datetime").timedelta(minutes=240)
        assert result == expected


class TestWorkingMinutesBetween:
    def test_basic(self):
        a = ist(2026, 11, 23, 9, 0)   # Mon 09:00
        b = ist(2026, 11, 23, 11, 0)  # Mon 11:00
        assert working_minutes_between(a, b, DEFAULT_CAL) == 120

    def test_across_weekend(self):
        # Using Mon-Fri calendar so Saturday counts as weekend
        fri_fri_cal = WorkCalendar(working_days=(0, 1, 2, 3, 4))
        a = ist(2026, 11, 20, 20, 0)  # Fri 20:00 — 1h of Friday left
        b = ist(2026, 11, 23, 10, 0)  # Mon 10:00 — 1h into Monday
        assert working_minutes_between(a, b, fri_fri_cal) == 120

    def test_b_before_a(self):
        a = ist(2026, 11, 23, 11, 0)
        b = ist(2026, 11, 23, 9, 0)
        assert working_minutes_between(a, b, DEFAULT_CAL) == 0


class TestQueuedFlag:
    def test_outside_hours_is_queued(self):
        sat_11pm = ist(2026, 11, 21, 23, 0)
        assert is_queued_for_next_shift(sat_11pm, DEFAULT_CAL)

    def test_inside_hours_is_not_queued(self):
        mon_10am = ist(2026, 11, 23, 10, 0)
        assert not is_queued_for_next_shift(mon_10am, DEFAULT_CAL)
