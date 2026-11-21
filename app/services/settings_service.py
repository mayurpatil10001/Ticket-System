"""Settings service — loads, caches, and validates application settings."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.holiday import Holiday
from app.models.settings import CategoryPriorityMap, Setting
from app.services.tat import WorkCalendar

# Default values (applied if no DB row exists)
DEFAULTS: dict[str, Any] = {
    "tat_minutes": {"High": 240, "Medium": 1440, "Low": 2880},
    "tat_mode": {"High": "working_hours", "Medium": "working_hours", "Low": "working_hours"},
    "working_hours": {
        "days": [0, 1, 2, 3, 4, 5],  # Mon–Sat
        "start": "09:00",
        "end": "21:00",
        "tz": "Asia/Kolkata",
    },
    "reopen_window_days": 7,
    "max_reopens": 2,
    "awaiting_member_auto_resolve_days": 3,
    "auto_close_days": 3,
    "escalation_recipients": "all_heads",
}

DEFAULT_CATEGORY_PRIORITY = {
    "Payment": "High",
    "Eligibility": "Medium",
    "Survey issue": "Medium",
    "Profile change": "Low",
    "Other": "Low",
}


@dataclass
class AppSettings:
    tat_minutes: dict[str, int]
    tat_mode: dict[str, str]
    working_hours: dict
    reopen_window_days: int
    max_reopens: int
    awaiting_member_auto_resolve_days: int
    auto_close_days: int
    escalation_recipients: str
    category_priority: dict[str, str]
    work_calendar: WorkCalendar


# Simple TTL cache
_cache: dict[str, Any] = {}
_CACHE_TTL = 60  # seconds


def _get_setting(db: Session, key: str) -> Any:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        return json.loads(row.value)
    return DEFAULTS[key]


def load_settings(db: Session) -> AppSettings:
    """Load AppSettings from DB, with 60s TTL cache."""
    now = time.time()
    if "data" in _cache and now - _cache.get("ts", 0) < _CACHE_TTL:
        return _cache["data"]

    tat_minutes = _get_setting(db, "tat_minutes")
    tat_mode = _get_setting(db, "tat_mode")
    working_hours = _get_setting(db, "working_hours")
    reopen_window_days = _get_setting(db, "reopen_window_days")
    max_reopens = _get_setting(db, "max_reopens")
    awaiting_auto = _get_setting(db, "awaiting_member_auto_resolve_days")
    auto_close = _get_setting(db, "auto_close_days")
    esc_recipients = _get_setting(db, "escalation_recipients")

    # Category priority map
    rows = db.query(CategoryPriorityMap).all()
    if rows:
        cat_prio = {r.category: r.priority for r in rows}
    else:
        cat_prio = dict(DEFAULT_CATEGORY_PRIORITY)

    # Holidays
    holiday_rows = db.query(Holiday).all()
    holiday_set = frozenset(date.fromisoformat(h.date) for h in holiday_rows)

    start_h, start_m = map(int, working_hours["start"].split(":"))
    end_h, end_m = map(int, working_hours["end"].split(":"))

    cal = WorkCalendar(
        working_days=tuple(working_hours["days"]),
        start_hour=start_h,
        start_minute=start_m,
        end_hour=end_h,
        end_minute=end_m,
        holidays=holiday_set,
    )

    settings = AppSettings(
        tat_minutes=tat_minutes,
        tat_mode=tat_mode,
        working_hours=working_hours,
        reopen_window_days=reopen_window_days,
        max_reopens=max_reopens,
        awaiting_member_auto_resolve_days=awaiting_auto,
        auto_close_days=auto_close,
        escalation_recipients=esc_recipients,
        category_priority=cat_prio,
        work_calendar=cal,
    )

    _cache["data"] = settings
    _cache["ts"] = now
    return settings


def invalidate_cache() -> None:
    _cache.clear()


def save_setting(db: Session, key: str, value: Any, actor_id: int | None = None) -> None:
    from app.core.clock import clock
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = json.dumps(value)
        row.updated_by = actor_id
        row.updated_at = clock.now()
    else:
        db.add(Setting(key=key, value=json.dumps(value), updated_by=actor_id, updated_at=clock.now()))
    db.commit()
    invalidate_cache()


def get_priority_for_category(db: Session, category: str) -> str:
    settings = load_settings(db)
    return settings.category_priority.get(category, "Medium")
