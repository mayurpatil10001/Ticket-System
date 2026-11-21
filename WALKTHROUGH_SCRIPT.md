# Video Walkthrough Script — Concave Insights Support

> **Duration target:** 6–8 minutes  
> **Tools needed:** Browser + terminal  
> **Start state:** fresh seed (`python -m app.seed`), server running on port 8000

---

## 0. Setup (off-camera or first 30s)

```powershell
cd "d:\Ticket System"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed          # prints login table — show this in terminal
uvicorn app.main:app --reload
```

Open `http://localhost:8000` in Chrome.

---

## 1. Member Portal — Raising a Ticket (90s)

**Login as member:**  
> User ID `5` — Priya Mehta (member, Mumbai)

1. Land on `/member/tickets` → show **empty state** ("Nothing raised yet…")
2. Click **Raise a ticket** → Step 1 form:
   - Category: **Payment**  
   - Subject: `Payment not received for Project Alpha`  
   - Demonstrate validation — submit empty → inline error
3. Click **Continue** → Step 2:
   - Body: `I completed the survey on 15 Nov but have not received ₹300 in my UPI account.`
   - Show character counter ticking up
4. Submit → **Success page** with ticket ID (e.g. `TKT-0016`)
5. Click **View ticket** → ticket detail:
   - TAT meter (green, e.g. "4h 00m left")
   - Status = **Open**, priority ticks

**Narrate:** *"Members raise tickets through a two-step mobile-first form. The TAT meter shows how long the team has to respond under our working-hours SLA."*

---

## 2. Agent Portal — Working the Queue (120s)

**Login as agent:**  
> User ID `9` — Asha Kulkarni (agent)

1. Land on `/agent/queue` → split-pane layout
2. Show filter bar: filter by **Priority: High** → queue narrows
3. Clear filter → click the ticket just raised (`TKT-0016`)
4. Right pane loads — show:
   - Member info row (name, phone, masked UPI → click **reveal**)
   - TAT meter live-updating
5. Click **Assign to me** → status changes to **In Progress** in queue row
6. Type a reply in the composer → click **Reply**
7. Demonstrate **Request info (pauses clock)**:
   - Type: `Could you share your registered UPI ID?`
   - Click **Request info** → TAT meter shows `CLOCK PAUSED / waiting for member`
8. Click **History** tab → show event log
9. Click **Internal note** checkbox → type a note → submit → shows hatched background in **Internal** tab

**Narrate:** *"Agents see all tickets in a split-pane queue. Pausing the clock freezes the TAT while waiting for the member, so agents aren't penalised for member delays."*

---

## 3. Member Portal — Replying and Closing (60s)

**Switch back to member (User ID `5`):**

1. Go to `/member/tickets` → ticket shows **In Progress** / CLOCK PAUSED banner
2. Open ticket → TAT note says "We've asked you for some information…"
3. Type a reply: `My UPI ID is priya@upi` → **Send reply**
4. TAT meter resumes (clock unpaused by member reply)

Switch back to **agent (User ID `9`):**

5. Click **Reply and resolve** in composer
6. Queue row disappears from active filter → ticket is **Resolved**

Switch back to **member (User ID `5`):**

7. Open ticket → prompt: **"Was this sorted?"** → show **Yes, close it** / **No, reopen** options
8. Click **No, reopen** → reopen sheet slides up → type reason → submit
9. Ticket status = **Reopened** → agent sees amber indicator in queue

**Narrate:** *"The member confirms resolution. If still unresolved, they can reopen with a mandatory reason (enforced in Pydantic, service layer, and DB constraint)."*

---

## 4. Support Head Portal — Dashboard (60s)

**Login as head:**  
> User ID `1` — Rahul Sharma (head)

1. Land on `/head/dashboard`:
   - Big numerals: Open, Overdue, Escalated, Resolved Today, Avg Resolution
   - Escalation Inbox table (if any escalated tickets)
   - Tickets by Category bar chart
   - Agent Load table

2. Navigate to **Settings**:
   - Change **High TAT** from `240` to `180` → **Save TAT settings** → toast "Settings saved."
   - Show **Saved Replies** section → add a new reply

**Narrate:** *"The head has a live operational dashboard and can tune SLA windows, reopen rules, and auto-resolve timers without touching code."*

---

## 5. Escalation Demo — Fast-Forward Tool (60s)

> *Use the CLI time-travel tool to simulate an overdue ticket.*

```powershell
# In a second terminal:
cd "d:\Ticket System"
.venv\Scripts\python.exe fast_forward.py +300   # advance clock 300 working minutes
```

1. Refresh `/agent/queue` → overdue ticket shows `OVERDUE Xh XXm` in brand red
2. Refresh `/head/dashboard` → Overdue and Escalated counts increase
3. Escalation Inbox shows the ticket

```powershell
# Reset clock
.venv\Scripts\python.exe fast_forward.py 0
```

**Narrate:** *"The injected `Clock` abstraction lets us fast-forward time in development without touching the database, making escalation and auto-resolve rules easy to test."*

---

## 6. Code Quality Highlights (30s — show in editor)

- `app/services/ticket_service.py` → business logic only, no HTTP
- `app/services/state_machine.py` → 6-state transition table
- `app/core/clock.py` → injectable `Clock` — `datetime.now()` never called directly in services
- `tests/test_state_machine.py` → shows reason enforcement in 3 layers
- `git log --oneline` → 42+ conventional commits

---

## 7. Close

```
http://localhost:8000/login
```

> *"Built with FastAPI + SQLAlchemy 2 + Jinja2 + HTMX — no npm, no build step, no Tailwind. Under 5-minute setup. 78/78 tests passing."*

---

## Demo Login Quick Reference

| Role | User ID | Name |
|------|---------|------|
| Member | 5 | Priya Mehta |
| Member | 6 | Arjun Nair |
| Agent | 9 | Asha Kulkarni |
| Agent | 10 | Ravi Desai |
| Head | 1 | Rahul Sharma |

> Full login table printed by `python -m app.seed`
