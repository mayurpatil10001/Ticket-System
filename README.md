# Concave Insights — Support Ticketing System

> **Status:** Under construction — see Implementation Plan for phase tracking.

## 1. Project Overview

A full-stack support ticketing system for Concave Insights, a Mumbai-based market-research firm whose panel members complete consumer surveys and refer others. Members raise queries (payment not received, wrong UPI ID, profile changes, broken survey links, eligibility questions) through the portal; agents triage and reply; a support head monitors the team and configures the system.

Built as a hiring take-home assessment. Core stack: FastAPI + SQLAlchemy 2.x + SQLite + Jinja2 + HTMX — no npm, no build step, running in under 5 minutes.

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI 0.115.5 |
| ORM | SQLAlchemy 2.0.36 (typed `Mapped[]`) |
| Database | SQLite (WAL mode, FK ON, CHECK constraints) |
| Migrations | Alembic 1.14.0 |
| Validation | Pydantic v2.10.2 |
| Scheduler | APScheduler 3.10.4 |
| Sessions | Starlette `SessionMiddleware` + itsdangerous |
| Templates | Jinja2 3.1.4 |
| Frontend interactivity | HTMX (CDN, pinned) + Alpine.js (CDN, pinned) |
| HTML sanitization | nh3 0.2.18 |
| Testing | pytest 8.3.4 + httpx 0.28.0 |
| Time zones | Python `zoneinfo` (stdlib ≥ 3.9) |

## 3. Setup and Run (under 5 minutes)

### macOS / Linux
```bash
git clone <repo-url>
cd ticket-system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

### Windows (PowerShell)
```powershell
git clone <repo-url>
cd "ticket-system"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Open http://localhost:8000 — the seed script prints all demo logins.

> **Note:** If `Activate.ps1` is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first.

## 4. Demo Logins and Test Data

The seed creates 16 users. After seeding, the app prints:

| Role | Name | Description |
|------|------|-------------|
| Head | Karan Mehta | Full access, sees escalations |
| Agent | Asha Iyer | 8 open tickets assigned |
| Agent | Rohan Desai | 6 open tickets assigned |
| Agent | Fatima Sheikh | 4 open tickets assigned |
| Member | Priya Nair | 1 late payment + 1 reopened ticket |
| Member | (12 total) | Covers every ticket state and category |

Login is **mocked** — the login page shows all personas as selectable rows. No passwords.

## 5. Features

*(Updated as phases complete)*

| Feature | Status |
|---------|--------|
| Member: raise ticket (5 categories) | 🔲 Not done |
| Member: view/track tickets | 🔲 Not done |
| Member: reply, confirm, reopen | 🔲 Not done |
| Agent: queue with filter/search | 🔲 Not done |
| Agent: reply, request info, resolve | 🔲 Not done |
| Head: dashboard with stats | 🔲 Not done |
| Head: settings (TAT, hours, rules) | 🔲 Not done |
| Working-hours TAT calculation | 🔲 Not done |
| Clock pause on "request info" | 🔲 Not done |
| Escalation sweep (every 60s) | 🔲 Not done |
| Auto-resolve / auto-close | 🔲 Not done |
| Internal tickets | 🔲 Not done |
| History Log tab | 🔲 Not done |
| `fast_forward` CLI tool | 🔲 Not done |

## 6. Database Design

See [`/design/README.md`](design/README.md) for key decisions.
Full ER diagram: [`/design/db-diagram.mmd`](design/db-diagram.mmd) / [`/design/db-diagram.png`](design/db-diagram.png).

**Tables:** users, tickets, ticket_messages, ticket_events, settings, category_priority_map, holidays, saved_replies, notifications, internal_tickets, ticket_counter.

## 7. API Endpoints

*(Populated after Phase 3)*

| Method | URL | Purpose |
|--------|-----|---------|
| GET | /healthz | Health check |
| POST | /api/auth/login | Set session (mocked) |
| ... | ... | ... |

## 8. Assumptions and Decisions

### Decision 1: Working Hours for TAT
**Question:** A High ticket arrives at 11 PM Saturday. Does the 4-hour TAT run overnight?

**Decision:** TAT counts **working time only** (Mon–Sat 09:00–21:00 IST by default; each priority can be switched to `24x7` in Settings). An outside-hours ticket is flagged `queued_for_next_shift = true`. The member sees an honest message: *"Our team is offline. First reply expected by Mon 1:00 PM."* The ticket pins to the top of the queue at shift open.

**Rationale:** Escalating at 3 AM to a head who cannot act creates alert noise and trains the team to ignore escalations. Silence is also unfair to the member, so we give an honest ETA instead.

### Decision 2: Waiting for the Member (Clock Pause)
**Question:** An agent requests a screenshot and the member takes two days to reply. Does the clock keep running?

**Decision:** The clock **pauses**. "Request info" sets `awaiting_member = true` and records `paused_at`. A member reply resumes the clock automatically: elapsed working minutes are stored in `paused_seconds_working` and `due_at` is recomputed. If no reply arrives within `awaiting_member_auto_resolve_days` (default 3), the system auto-resolves with a logged reason.

**Rationale:** The delay is the member's; charging it to support creates false escalations and penalizes agents for factors outside their control. Paused time is also excluded from the average-resolution calculation so reporting stays honest.

### Other assumptions
- **Profile-change tickets do not auto-edit the `users` table.** Agents manually apply changes after identity verification, then click "Applied to profile" which logs a `profile_applied` event and resolves the ticket. Automation here creates liability.
- **Escalation notifies all Heads** (configurable via `escalation_recipients` setting).
- **Sunday is off by default** (Mon–Sat 09:00–21:00 IST); configurable in Settings → Working Hours.
- **UPI IDs are masked for agents** by default (`ra***@okhdfc`) with a reveal toggle, to limit data exposure.
- **Login is mocked** (persona selector). A real system would use OAuth or OTP-to-phone.
- **SQLite** is used for portability. Swapping to PostgreSQL requires only changing `DATABASE_URL` and removing the `BEGIN IMMEDIATE` ticket-counter workaround (use `SERIAL`).

## 9. Known Issues and Next Steps

*(Updated as phases complete — will be honest about anything not fully delivered)*

---

*Concave Insights Support Ticketing System — Take-home Assessment 2026*
