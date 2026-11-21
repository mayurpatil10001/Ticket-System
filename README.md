# Concave Insights — Support Ticketing System

A production-quality support ticketing system for Concave Insights, a Mumbai-based market-research firm that pays panel members to complete consumer surveys. Members currently raise queries by phone/WhatsApp; this system digitises and tracks every support interaction.

---

## Quick Start (under 5 minutes)

### Unix / macOS / WSL

```bash
git clone <repo-url>
cd "Ticket System"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

### Windows PowerShell

```powershell
git clone <repo-url>
cd "Ticket System"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.venv\Scripts\python.exe -m app.seed
.venv\Scripts\uvicorn.exe app.main:app --reload
```

Open **http://localhost:8000/login** — click any persona card to sign in. No password required (mocked auth per spec).

The seed script is **idempotent**: running it again prints the login table and exits without touching the database.

---

## Demo Login Table

| Role   | Name          | Email                               |
|--------|---------------|-------------------------------------|
| head   | Karan Mehta   | karan.mehta@concaveinsights.com     |
| agent  | Asha Iyer     | asha.iyer@concaveinsights.com       |
| agent  | Rohan Desai   | rohan.desai@concaveinsights.com     |
| agent  | Fatima Sheikh | fatima.sheikh@concaveinsights.com   |
| member | Priya Nair    | priya.nair@gmail.com                |
| member | Ajay Verma    | ajay.verma@gmail.com (reopened)     |
| member | Meera Joshi   | meera.joshi@gmail.com (escalated)   |
| member | Dinesh Rao    | dinesh.rao@gmail.com (resolved)     |
| member | Kavita Singh  | kavita.singh@gmail.com (closed)     |
| …      | (12 members total)                               |

---

## Three Portals

| Portal | URL | Who |
|--------|-----|-----|
| **Member** | `/member/tickets` | Panel members — raise tickets, track status, reply, confirm/reopen |
| **Agent** | `/agent/queue` | Support agents — split-pane queue, reply, resolve, request info |
| **Head** | `/head/dashboard` | Support head — real-time stats, escalation inbox, team load, settings |

---

## Architecture

```
routes/   (thin HTTP: validate form, call service, render template / return JSON)
  ↓
services/ (all business logic: state machine, TAT, escalation, notifications)
  ↓
models/   (SQLAlchemy 2.x mapped classes — Ticket, User, TicketEvent, …)
```

**No business logic in templates or routes.** Every route handler is ≤10 lines of "validate → call service → respond."

### Tech stack

| Layer | Choice |
|-------|--------|
| Web framework | FastAPI + Starlette |
| ORM | SQLAlchemy 2.x (typed `Mapped[]`) |
| DB | SQLite (WAL mode, FK enforcement) |
| Templates | Jinja2 (server-rendered, autoescape) |
| Interactivity | HTMX + vanilla JS modules |
| Styling | Hand-written CSS with design tokens, no build step |
| Auth | Starlette `SessionMiddleware` (mocked persona selector) |
| Scheduling | APScheduler (escalation sweep every 60s) |
| Testing | pytest + FastAPI `TestClient` |

---

## Key Design Decisions

### TAT (Time-to-Achieve-Target)

- Stored in **working minutes** (Mon–Sat 09:00–21:00 IST by default, configurable).
- Clock **pauses** when an agent sends "request info" and **resumes** on the next member reply.
- Clock **queues** for next shift when a ticket is raised outside working hours.
- Paused working-minutes accumulate in `paused_seconds_working`; `due_at` is recomputed on resume.
- Priority TAT defaults: High = 4h, Medium = 24h, Low = 48h (all configurable by head).

### 6-State Machine

```
Open → In Progress → Resolved → Closed
         ↓               ↑
      Escalated       Reopened
```

- Transitions enforced in three places: `state_machine.py`, `ticket_service.py`, and DB `CHECK` constraints.
- **Mandatory reasons** for `reopen`, `priority_changed`, and `escalated`: Pydantic validator (≥5 chars) → service layer (`ReasonRequired`) → DB `CHECK` on `ticket_events`.

### Reopen Rules

- Member has `reopen_window_days` (default 7) from `resolved_at` to reopen.
- Maximum `max_reopens` (default 2) reopen attempts allowed.
- Each reopen resets the TAT clock fresh from reopen time.

### Escalation

- APScheduler sweeps every 60s; also runs lazily on queue/dashboard page loads.
- Idempotent: atomic `UPDATE … WHERE status IN ('Open','In Progress','Reopened')` guard prevents double-escalation.
- Notifies all head users once per ticket (deduplicates by checking existing unread notification).

### Auto-Resolution / Auto-Close

- If a member doesn't reply within `awaiting_member_auto_resolve_days` (default 3) of a "request info" pause → auto-resolved.
- If a ticket stays Resolved for `auto_close_days` (default 3) with no member action → auto-closed.

### Security

- CSRF token on every form POST (server-side verify via `SessionMiddleware` signed cookie).
- All user text sanitised with `nh3` (strips HTML tags) before storage.
- Global exception handler: no stack traces exposed; custom 403/404/500 error pages.
- Request body size limit via `app_max_request_size` in config.
- Parameterised queries only (SQLAlchemy ORM — no raw string interpolation).

### Datetime Handling

- All storage: **UTC** via `TZDateTime` type decorator (re-attaches `UTC` on read from SQLite).
- All display: **Asia/Kolkata** via the `|ist` Jinja filter (Windows-safe, no `%-d` format codes).
- Clock injection: `app.core.clock.Clock` — never `datetime.now()` in services. Tests use `test_clock` fixture to control time.

---

## Running Tests

```bash
pytest tests/ -v
# 78 tests: TAT, state machine, reasons, reopen rules, escalation, authz, validation
```

Coverage report:

```bash
pytest tests/ --cov=app/services --cov-report=term-missing
```

---

## Project Structure

```
app/
  core/         config, clock, csrf, exceptions, security
  models/       SQLAlchemy ORM models
  services/     all business logic (tat, state_machine, ticket_service, escalation, …)
  routes/       thin HTTP handlers (member_ui, agent_ui, head_ui, tickets_api, …)
  schemas/      Pydantic v2 request/response shapes
  tools/        fast_forward CLI (time-travel for demos)
  main.py       FastAPI app, middleware, scheduler, error handlers
  seed.py       idempotent demo data
static/
  css/          tokens.css, base.css, components.css, member.css, agent.css, head.css
  js/           csrf.js, toast.js, tat-live.js, queue-shortcuts.js, composer.js
templates/
  base.html, base_member.html, login.html, 403/404/500.html
  components/   macros.html (status_marker, priority_ticks, tat_meter, ticket_id)
  member/       tickets, raise_step1/2/success, ticket_detail, profile
  agent/        queue (split pane)
  head/         dashboard, settings
tests/
  conftest.py   per-test in-memory SQLite + TestClient fixture
  test_tat.py, test_state_machine.py, test_reasons.py, test_reopen_rules.py,
  test_escalation.py, test_authz.py, test_validation.py, test_ids.py
design/
  README.md     design decisions and ambiguity resolutions
  user-flow.mmd Mermaid user flow diagram
  db-diagram.mmd ER diagram
```

---

## Configuration

All settings live in the DB `settings` table and are editable by the head via `/head/settings`.  
Defaults are in `app/services/settings_service.py::DEFAULTS`.

| Key | Default | Description |
|-----|---------|-------------|
| `tat_minutes` | High=240, Medium=1440, Low=2880 | Per-priority TAT in working minutes |
| `tat_mode` | `working_hours` for all | `working_hours` or `24x7` per priority |
| `working_hours` | Mon-Sat 09:00-21:00 IST | Working calendar |
| `reopen_window_days` | 7 | Days from resolved_at member can reopen |
| `max_reopens` | 2 | Max reopen attempts per ticket |
| `awaiting_member_auto_resolve_days` | 3 | Auto-resolve if member silent this long |
| `auto_close_days` | 3 | Auto-close resolved tickets after this many days |

---

## Fast-Forward Tool (Demo)

Advance the system clock without changing actual time — useful for demonstrating escalation, auto-resolve, and reopen-window expiry in a demo:

```bash
# Advance clock 2 days forward
python -m app.tools.fast_forward --hours 48

# Reset to real time
python -m app.tools.fast_forward --reset
```

---

## Environment Variables

Copy `.env.example` to `.env` and set:

```
SECRET_KEY=your-secret-key-at-least-32-chars
DATABASE_URL=sqlite:///./concave_tickets.db
```

---

## Git History

This project uses **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).  
Each commit is a single logical change — 36+ commits from init to fully working system.

---

## What Was Intentionally Omitted

- **Email / SMS notifications** — no SMTP config in scope; in-app notification bell is implemented.
- **File attachments** — mentioned in design but not built; would require object storage.
- **Dark mode** — tokens.css has the `prefers-color-scheme` stub but it's not implemented (time constraint).
- **Member notifications page** — bell badge and count is wired; `/member/notifications` route would need a template added.
- **Fast-forward tool** — written but not end-to-end tested; use at own risk in demo.
