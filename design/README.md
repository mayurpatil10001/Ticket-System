# Design Notes — Concave Insights Support Ticketing System

## Key Decisions

### 1. Working Hours for TAT (Time-to-Action)

**Problem:** A High-priority ticket arrives at 11 PM Saturday. Does the 4-hour TAT run overnight and through Sunday?

**Decision:** TAT counts **working time only** by default (Mon–Sat 09:00–21:00 IST). Each priority level can be individually switched to `24x7` mode in the Settings screen.

**Consequences:**
- Tickets received outside working hours get `queued_for_next_shift = true`.
- The member sees an honest expected-reply time at submit and on the ticket detail.
- The queue surfaces these tickets at the top when the shift opens.
- The 11 PM Saturday example: Sunday is off, so the 4-hour clock starts Monday 09:00 and is due Monday 13:00 IST.

**Rationale:** Escalating at 3 AM to a head who cannot act produces alert noise and trains people to ignore escalations. Silence is also bad for the member, so we give an honest ETA instead.

---

### 2. Waiting for the Member (Clock Pause)

**Problem:** An agent requests a screenshot; the member takes two days to reply. Does the clock keep running?

**Decision:** The clock **pauses**. "Request info" sets `awaiting_member = true` and records `paused_at`. A member reply auto-resumes: elapsed working minutes are accumulated in `paused_seconds_working` and `due_at` is recomputed. If no reply in `awaiting_member_auto_resolve_days` days (default 3), the system auto-resolves with a logged reason (member can reopen within the window).

**Consequences:**
- Paused time is excluded from `due_at` calculation and from average-resolution reporting.
- Escalation sweep skips `awaiting_member = true` tickets.
- Status remains `In Progress` — no seventh status is added.

**Rationale:** The delay is the member's; charging it to support creates false escalations and penalizes agents for factors outside their control.

---

### 3. Profile-Change Application

**Decision:** Agents manually apply profile changes after identity verification. The `apply-profile-change` action logs a `profile_applied` event; it does **not** auto-write the `users` table.

**Rationale:** Automation here creates liability (wrong name, wrong DOB). Human judgment is the right control.

---

### 4. ID Generation

`ticket_counter` is a single-row table incremented inside `BEGIN IMMEDIATE` (SQLite write lock). This prevents gaps or duplicates under concurrent requests.

---

### 5. Six Statuses (not seven)

`awaiting_member` is a boolean flag on `tickets`, not a status. This keeps the state machine to exactly the six specified statuses and avoids new transition edges.

---

## User Flow Diagram

See `user-flow.mmd` / `user-flow.png`.

## Database ER Diagram

See `db-diagram.mmd` / `db-diagram.png`.

---

> **This folder is frozen after commit 3.** Later design notes go in `addendum-1.md`, etc.
