"""
Fast-forward CLI tool.
Usage:
  python -m app.tools.fast_forward --hours 5     # advance clock by 5 hours + run sweep
  python -m app.tools.fast_forward --reset       # reset clock offset
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

OFFSET_FILE = Path(".clock_offset")


def main():
    parser = argparse.ArgumentParser(description="Fast-forward the application clock.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hours", type=float, help="Advance clock by N hours")
    group.add_argument("--reset", action="store_true", help="Reset clock to real time")
    args = parser.parse_args()

    if args.reset:
        if OFFSET_FILE.exists():
            OFFSET_FILE.unlink()
        print("Clock reset to real time.")
        return

    # Read existing offset
    existing_offset = 0.0
    if OFFSET_FILE.exists():
        try:
            existing_offset = float(json.loads(OFFSET_FILE.read_text()).get("offset_seconds", 0))
        except Exception:
            pass

    new_offset = existing_offset + args.hours * 3600
    OFFSET_FILE.write_text(json.dumps({"offset_seconds": new_offset}))
    print(f"Clock advanced by {args.hours}h. Total offset: {new_offset / 3600:.2f}h.")

    # Run escalation sweep with the new clock
    from app.db import SessionLocal
    from app.services.escalation import auto_close_resolved, auto_resolve_awaiting, escalation_sweep

    with SessionLocal() as db:
        esc = escalation_sweep(db)
        auto_r = auto_resolve_awaiting(db)
        auto_c = auto_close_resolved(db)
        print(f"Sweep results: {esc} escalated, {auto_r} auto-resolved, {auto_c} auto-closed.")


if __name__ == "__main__":
    main()
