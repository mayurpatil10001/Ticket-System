# Video Walkthrough Script
## Concave Insights — Support Ticketing System

> **Target duration:** 7–9 minutes  
> **Login credentials:** Printed on screen by `python -m app.seed`  
> **Sections map directly to assessment requirements A → E + Bonus**

---

## OPENING — 30 seconds

> *Show the terminal. Type:*

```powershell
cd "d:\Ticket System"
python -m app.seed
```

Point to the printed login table on screen.

> **Say:** *"Fresh seed — 16 demo users, 15 pre-loaded tickets. The whole app starts with one command. Let me walk through every requirement."*

Open browser → `http://localhost:8000`

---

## SECTION A — Raising a Ticket (mobile-first) — ~90 seconds

**Requirement:** Member picks category, gets a ticket ID, sees all their tickets.

### Step 1 — Log in as a Member
- Login page: type user ID **5** (Priya Nair, member)
- Land on **My Tickets** → show the list with statuses and last-updated times

> **Say:** *"Members have three screens — My Tickets, Raise, and Profile. This is a mobile-first layout: bottom navigation, 48-pixel touch targets, full-width inputs."*

### Step 2 — Raise a Ticket
- Click **Raise** (bottom nav)
- **Step 1:** Show the 5 category tiles — Payment, Profile Change, Survey Issue, Eligibility, Other
- Click **Payment**
- **Step 2:** Show the form:
  - Point to the TAT hint: *"Typical reply: within 4 working hours"*
  - Type description: `I completed the Beauty Products survey on 15 Nov but have not received my payment of ₹300.`
  - Show the **character counter** in mono font
  - Leave survey ref blank → submit empty → show inline validation error
  - Fill in survey ref: `Beauty Products Study Nov 2026`
  - Click **Submit ticket**
- **Success page** → show `TKT-0016` (or whichever number appears)

> **Say:** *"The ticket ID is generated atomically — no race conditions. Priority is automatically set to High for Payment tickets, based on the admin's category-priority map."*

### Step 3 — My Tickets list
- Click **My Tickets** → new ticket appears at top with status **Open**
- Click the ticket → show the **ticket detail** page:
  - Status marker + priority ticks
  - TAT meter (e.g. "3h 48m left")
  - Empty thread: *"Our team will respond within the expected time."*

---

## SECTION B — Support Queue — ~90 seconds

**Requirement:** Agents see all tickets, filter, assign, reply, change status.

### Step 1 — Log in as Agent
- Log out → login as user ID **2** (Asha Iyer, agent)
- Land on **Agent Queue** — split-pane layout

> **Say:** *"The agent view is a split pane: ticket list on the left, thread and composer on the right."*

### Step 2 — Filters
- Show **filter bar**: status, priority, overdue checkbox
- Filter by **Priority: High** → queue narrows to High tickets only
- Clear filter → search `TKT` → shows results
- Clear search

### Step 3 — Assign and Reply
- Click the new ticket (Payment, TKT-016x)
- Right pane loads — show:
  - Member info: name, phone, **masked UPI → click reveal**
  - TAT meter ticking live
- Click **Assign to me** → status changes to **In Progress** in the queue row

> **Say:** *"Status moves from Open to In Progress on assignment."*

- In the composer, type: `Hi Priya, your payment is under review. We will process it within 2 working days.`
- Click **Reply** — message appears in the thread with agent's name + IST timestamp

### Step 4 — All 6 Statuses
> **Say while pointing to filter dropdown:** *"The system supports six statuses: Open, In Progress, Resolved, Closed, Reopened, and Escalated — each with its own visual marker, no colored pills."*

---

## SECTION C — TAT and Escalation — ~60 seconds

**Requirement:** TAT per priority, ticket escalates when overdue, alert to Support Head.

### Step 1 — TAT Design Decision
> **Say:** *"Two open decisions I had to make:"*  
> *"One — a High-priority ticket at 11 PM Saturday: the TAT clock does NOT run overnight. It queues until Monday 9 AM IST. The meter shows: QUEUED / next shift 9:00 AM Mon."*  
> *"Two — if support asks for a screenshot and the member takes 2 days: the TAT clock is PAUSED. It resumes the moment the member replies."*

### Step 2 — Show it in the app
- Find a ticket in **In Progress** state → show the TAT meter
- Click **Request info (pauses clock)** in the composer → type a message → submit
- TAT meter now shows: **CLOCK PAUSED / waiting for member**

### Step 3 — Escalation (fast-forward demo)
> *Open a second terminal:*

```powershell
cd "d:\Ticket System"
.venv\Scripts\python.exe fast_forward.py +300
```

- Refresh the queue → one or more tickets now show **OVERDUE Xh XXm** in red
- Log in as **Head (user ID 1)** → dashboard shows **Escalated** count increased
- **Escalation Inbox** table lists the overdue tickets with a View button

```powershell
.venv\Scripts\python.exe fast_forward.py 0   # reset clock
```

---

## SECTION D — Closing and Reopening — ~75 seconds

**Requirement:** Member confirms → Closed. Reopen with mandatory reason. Mandatory reasons everywhere.

### Step 1 — Resolve and Confirm
- Log back in as **Agent (user ID 2)**
- Click the Payment ticket → composer → type a reply → click **Reply and resolve**
- Status in queue changes to **Resolved**
- Log in as **Member (user ID 5)** → open the ticket
- Show the prompt: **"Was this sorted?"** with two buttons — *Yes, close it* and *No, reopen*
- Click **Yes, close it** → status becomes **Closed**

> **Say:** *"The member explicitly confirms resolution. Auto-close also kicks in after X days if they don't respond — that's configurable by the admin."*

### Step 2 — Reopen with Mandatory Reason
- Open a **Resolved** ticket (use another from the list)
- Click **No, reopen** → bottom sheet slides up
- Try to submit with an empty reason → show inline error
- Type a reason under 5 characters → show error: *"At least 5 characters"*
- Type a valid reason: `Payment still not credited to my account`
- Submit → status becomes **Reopened** (amber marker)

> **Say:** *"Mandatory reasons are enforced in three places: the Pydantic validator, the service layer, and a database CHECK constraint — the app physically cannot save a reopen without a reason."*

### Step 3 — Priority Change Reason (agent side)
- As agent, open a ticket → click **Priority** dropdown
- Try to submit without a reason → browser HTML5 required attribute blocks it
- Fill reason → submit → History tab logs: `priority_changed: Medium → High (reason: ...)`

---

## SECTION E — Roles and Dashboard — ~60 seconds

**Requirement:** 3 roles, each with their own screens. Dashboard with all KPIs.

### Step 1 — The 3 Portals
> **Say:** *"Three completely separate portals — same codebase, server-side role check on every route."*

- **Member:** mobile bottom-nav, ticket list, raise form, profile, notifications
- **Agent:** desktop split-pane queue
- **Support Head:** top-nav dashboard

### Step 2 — Head Dashboard (all KPIs)
- Log in as **Head (user ID 1)**
- Point to the stat row:
  - **Open** count
  - **Overdue** (red when > 0)
  - **Escalated** (red when > 0)
  - **Resolved Today**
  - **Avg Resolution** (hours/minutes)
- **Tickets by Category** bar chart
- **Agent Load** table (open tickets + overdue per agent + avg first response)
- **Escalation Inbox** with direct View links

### Step 3 — Mocked Login
> **Say:** *"Login is mocked — no password, just pick a user ID from the seed table. In production this would be replaced with real auth."*

---

## BONUS FEATURES — ~60 seconds

**Say:** *"All four bonus features are implemented."*

### Internal Tickets
- As agent, on a Payment ticket → Internal Notes tab → type a note referencing the Rewards team
- Show the `InternalTicket` model (optional: open the code briefly)

> *"Internal sub-tickets are linked to the parent. The member's ticket shows when it's resolved."*

### Auto-Close
- Head settings → **Auto-resolve and Auto-close** section
- Show the configurable fields: *"Auto-close resolved tickets after X days with no member action"*

### History Log
- Agent queue → open any ticket → click **History** tab
- Show the event log: status changes, assignments, priority changes — all with actor name + IST timestamp

### Saved Replies
- In composer → type `/` → saved reply picker appears (or show the picker button)
- Click a saved reply title → body auto-fills in the textarea

> *"Agents can manage saved replies from the Head settings panel."*

---

## CLOSING — 30 seconds

> *Back to terminal, show:*

```powershell
cd "d:\Ticket System"
.venv\Scripts\python.exe -m pytest tests\ -v
# → 78 passed
git log --oneline | measure-object -line
# → 46 commits
```

> **Say:** *"78 tests covering TAT logic, state machine transitions, mandatory reason enforcement, authorization, and input validation. 46 conventional commits — one logical change per commit, no squashing."*

> *"Built with FastAPI + SQLAlchemy 2 + Jinja2 + HTMX — no npm, no build step, no Tailwind. Under 5-minute setup. Thank you."*

---

## Quick Login Reference

| Role | User ID | Name |
|------|---------|------|
| Support Head | 1 | Karan Mehta |
| Agent | 2 | Asha Iyer |
| Agent | 3 | Rohan Desai |
| Member | 5 | Priya Nair |
| Member | 6 | Amit Sharma |

> Full table printed by `python -m app.seed`

---

## Screen Order Cheat-Sheet

```
1. Terminal — seed output
2. /login → user 5 (member)
3. /member/tickets → list
4. /member/raise → category tiles → step 2 form → success
5. /member/tickets/{id} → TAT meter
6. /login → user 2 (agent)
7. /agent/queue → filters → assign → reply → request info → TAT paused
8. Terminal → fast_forward.py +300
9. /agent/queue → overdue tickets
10. /login → user 1 (head)
11. /head/dashboard → all KPIs, escalation inbox
12. /login → user 2 (agent) → resolve ticket
13. /login → user 5 (member) → confirm / reopen flow
14. /head/settings → auto-close, saved replies, TAT settings
15. Terminal → pytest + git log
```
