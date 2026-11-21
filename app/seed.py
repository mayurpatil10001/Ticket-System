"""
Seed script — idempotent, prints demo login table at the end.
Run: python -m app.seed
"""
from __future__ import annotations

import sys
from datetime import UTC, timedelta

from sqlalchemy.orm import Session

from app.core.clock import clock
from app.db import SessionLocal, engine
from app.models import Base
from app.models.settings import CategoryPriorityMap, Setting
from app.models.holiday import Holiday
from app.models.saved_reply import SavedReply
from app.models.ticket_counter import TicketCounter
from app.models.user import User
from app.services.settings_service import DEFAULTS, DEFAULT_CATEGORY_PRIORITY
import json

# Create tables
Base.metadata.create_all(bind=engine)


def _already_seeded(db: Session) -> bool:
    counter = db.query(TicketCounter).filter(TicketCounter.id == 1).first()
    return counter is not None and counter.last_number > 0


def seed():
    with SessionLocal() as db:
        if _already_seeded(db):
            print("\n[seed] Database already seeded. Printing login table.\n")
            _print_login_table(db)
            return

        now = clock.now()

        # ── Ticket counter ──────────────────────────────────────────────
        db.merge(TicketCounter(id=1, last_number=0))

        # ── Settings ────────────────────────────────────────────────────
        for key, value in DEFAULTS.items():
            if not db.query(Setting).filter(Setting.key == key).first():
                db.add(Setting(key=key, value=json.dumps(value), updated_at=now))

        for category, priority in DEFAULT_CATEGORY_PRIORITY.items():
            if not db.query(CategoryPriorityMap).filter(CategoryPriorityMap.category == category).first():
                db.add(CategoryPriorityMap(category=category, priority=priority))

        # ── Holidays (a few Indian ones) ─────────────────────────────────
        holidays = [
            ("2026-11-26", "Constitution Day"),
            ("2026-12-25", "Christmas"),
            ("2027-01-26", "Republic Day"),
        ]
        for date_str, label in holidays:
            if not db.query(Holiday).filter(Holiday.date == date_str).first():
                db.add(Holiday(date=date_str, label=label))

        db.flush()

        # ── Users ────────────────────────────────────────────────────────
        users_data = [
            # Heads
            dict(name="Karan Mehta", email="karan.mehta@concaveinsights.com",
                 phone="9820000001", role="head", city="Mumbai", dob="1985-03-15",
                 upi_id="karan.mehta@okhdfc"),
            # Agents
            dict(name="Asha Iyer", email="asha.iyer@concaveinsights.com",
                 phone="9820000002", role="agent", city="Mumbai", dob="1992-07-22",
                 upi_id="asha.iyer@ybl"),
            dict(name="Rohan Desai", email="rohan.desai@concaveinsights.com",
                 phone="9820000003", role="agent", city="Pune", dob="1990-11-05",
                 upi_id="rohan.desai@paytm"),
            dict(name="Fatima Sheikh", email="fatima.sheikh@concaveinsights.com",
                 phone="9820000004", role="agent", city="Mumbai", dob="1994-02-18",
                 upi_id="fatima.sheikh@okaxis"),
            # Members — 12
            dict(name="Priya Nair", email="priya.nair@gmail.com",
                 phone="9876543201", role="member", city="Mumbai", dob="1998-04-10",
                 upi_id="priya.nair@okaxis"),
            dict(name="Amit Sharma", email="amit.sharma@gmail.com",
                 phone="9876543202", role="member", city="Thane", dob="1995-08-25",
                 upi_id="amit.sharma@ybl"),
            dict(name="Sunita Patil", email="sunita.patil@gmail.com",
                 phone="9876543203", role="member", city="Pune", dob="2000-01-30",
                 upi_id="sunita.patil@paytm"),
            dict(name="Ravi Kumar", email="ravi.kumar@gmail.com",
                 phone="9876543204", role="member", city="Mumbai", dob="1993-12-05",
                 upi_id="ravi.kumar@okhdfc"),
            dict(name="Meera Joshi", email="meera.joshi@gmail.com",
                 phone="9876543205", role="member", city="Vasai-Virar", dob="1997-06-15",
                 upi_id="meera.joshi@ybl"),
            dict(name="Dinesh Rao", email="dinesh.rao@gmail.com",
                 phone="9876543206", role="member", city="Navi Mumbai", dob="1996-03-20",
                 upi_id="dinesh.rao@okaxis"),
            dict(name="Kavita Singh", email="kavita.singh@gmail.com",
                 phone="9876543207", role="member", city="Mumbai", dob="1999-09-08",
                 upi_id="kavita.singh@paytm"),
            dict(name="Ajay Verma", email="ajay.verma@gmail.com",
                 phone="9876543208", role="member", city="Thane", dob="1994-11-22",
                 upi_id="ajay.verma@ybl"),
            dict(name="Pooja Kulkarni", email="pooja.kulkarni@gmail.com",
                 phone="9876543209", role="member", city="Pune", dob="2001-05-17",
                 upi_id="pooja.kulkarni@okhdfc"),
            dict(name="Sanjay Bhosale", email="sanjay.bhosale@gmail.com",
                 phone="9876543210", role="member", city="Mumbai", dob="1992-07-30",
                 upi_id="sanjay.bhosale@okaxis"),
            dict(name="Rekha Pawar", email="rekha.pawar@gmail.com",
                 phone="9876543211", role="member", city="Vasai-Virar", dob="1998-02-14",
                 upi_id="rekha.pawar@ybl"),
            dict(name="Nilesh Gaikwad", email="nilesh.gaikwad@gmail.com",
                 phone="9876543212", role="member", city="Navi Mumbai", dob="1997-10-03",
                 upi_id="nilesh.gaikwad@paytm"),
        ]

        created_users = {}
        for u in users_data:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                user = User(created_at=now, is_active=True, **u)
                db.add(user)
                db.flush()
                created_users[u["email"]] = user
            else:
                created_users[u["email"]] = existing

        db.flush()

        # Shortcuts
        head = created_users["karan.mehta@concaveinsights.com"]
        asha = created_users["asha.iyer@concaveinsights.com"]
        rohan = created_users["rohan.desai@concaveinsights.com"]
        fatima = created_users["fatima.sheikh@concaveinsights.com"]
        priya = created_users["priya.nair@gmail.com"]
        amit = created_users["amit.sharma@gmail.com"]
        sunita = created_users["sunita.patil@gmail.com"]
        ravi = created_users["ravi.kumar@gmail.com"]
        meera = created_users["meera.joshi@gmail.com"]
        dinesh = created_users["dinesh.rao@gmail.com"]
        kavita = created_users["kavita.singh@gmail.com"]
        ajay = created_users["ajay.verma@gmail.com"]
        pooja = created_users["pooja.kulkarni@gmail.com"]
        sanjay = created_users["sanjay.bhosale@gmail.com"]
        rekha = created_users["rekha.pawar@gmail.com"]
        nilesh = created_users["nilesh.gaikwad@gmail.com"]

        # ── Saved replies ─────────────────────────────────────────────────
        saved_replies = [
            dict(title="Payment timeline", body="Payments are processed within 7 working days of project completion. If your payment is overdue, please share your UPI ID and we will investigate.", category="Payment", created_by=head.id),
            dict(title="UPI verification ask", body="To verify your payment, could you please confirm your UPI ID and the name of the project you completed? A screenshot of the survey completion screen would also be helpful.", category="Payment", created_by=head.id),
            dict(title="Screenshot request", body="Thank you for reaching out. To help us investigate further, could you please share a screenshot of the issue you are seeing? You can attach it in your next reply.", category="Survey issue", created_by=head.id),
            dict(title="Cool-off rule explanation", body="Our cool-off policy means that after completing a project, panel members are not eligible for another project for 90 days. This ensures fair distribution of opportunities. Your next eligibility date is noted in your profile.", category="Eligibility", created_by=head.id),
            dict(title="Partial completion policy", body="We are only able to process payments for surveys that are fully completed. Partial submissions are unfortunately not eligible for payment. If you believe you completed the survey fully, please share any confirmation you received.", category="Payment", created_by=head.id),
            dict(title="Broken link apology", body="We apologise for the inconvenience. We are aware of this issue and our tech team is working to restore the survey link. We will update you as soon as it is live again. Thank you for your patience.", category="Survey issue", created_by=head.id),
            dict(title="Profile change confirmation", body="We have noted your request to update your profile details. Your change has been reviewed and applied. Please allow up to 24 hours for the update to reflect across all systems.", category="Profile change", created_by=head.id),
            dict(title="Closing reply", body="Thank you for reaching out to Concave Insights support. I am glad we could resolve this for you. Please do not hesitate to raise a new ticket if you need any further assistance.", category=None, created_by=head.id),
            dict(title="Internal escalation note", body="Escalating to Finance team — payment not processed after 10 days. Please investigate and confirm UTR.", category="Payment", created_by=head.id),
        ]

        for sr_data in saved_replies:
            existing = db.query(SavedReply).filter(SavedReply.title == sr_data["title"]).first()
            if not existing:
                db.add(SavedReply(**sr_data))

        db.flush()
        db.commit()

        # ── Tickets ───────────────────────────────────────────────────────
        # Import after tables are created
        from app.services.ticket_service import create_ticket, resolve_ticket, reopen_ticket, request_info
        from app.services.message_service import add_message
        from app.services.ticket_service import assign_ticket, change_priority, confirm_ticket
        from app.services.event_service import log_event

        def make_ticket(member, category, description, days_ago=1, survey_ref=None, req_field=None, req_value=None):
            """Create a ticket with created_at shifted back."""
            ticket = create_ticket(
                db,
                member=member,
                category=category,
                description=description,
                survey_ref=survey_ref,
                requested_field=req_field,
                requested_value=req_value,
            )
            # Shift timestamps back
            shift = timedelta(days=days_ago, hours=2)
            ticket.created_at = now - shift
            ticket.updated_at = now - shift
            ticket.tat_clock_started_at = now - shift
            from app.services.tat import compute_due_at
            from app.services.settings_service import load_settings
            settings = load_settings(db)
            mode = settings.tat_mode.get(ticket.priority, "working_hours")
            ticket.due_at = compute_due_at(ticket.tat_clock_started_at, ticket.tat_minutes_snapshot, 0, settings.work_calendar, mode)
            ticket.last_member_activity_at = now - shift
            db.flush()
            return ticket

        # 1. Open payment ticket — Priya's late payment (High, overdue)
        t1 = make_ticket(priya, "Payment", "Completed the beauty-products survey on 8 Nov, payment still not showing after 12 days. UPI is priya.nair@okaxis.", days_ago=5)
        t1.due_at = now - timedelta(hours=3)  # Overdue
        t1.last_member_activity_at = now - timedelta(days=5)
        db.flush()

        # 2. In Progress — Amit's survey link broken
        t2 = make_ticket(amit, "Survey issue", "The link for the food habits survey is broken — keeps showing 'Session expired' after I fill the first page. Tried Chrome and Firefox.", days_ago=2)
        assign_ticket(db, ticket=t2, assignee=asha, actor=asha)
        add_message(db, ticket=t2, author=asha, body="Hi Amit, thanks for flagging this. I have reported the broken link to our tech team. Can you share a screenshot of the error you are seeing so we can pass it on?")
        add_message(db, ticket=t2, author=amit, body="Sure, the error says 'Your session has expired. Please restart the survey.' But I do not get a new link.")
        add_message(db, ticket=t2, author=asha, body="Understood. Our tech team is investigating. We will update you within 4 working hours. I am sorry for the inconvenience.")

        # 3. Awaiting member — clock paused
        t3 = make_ticket(ravi, "Payment", "My payment for the telecom survey completed on 10 Nov has not arrived. The amount should be Rs 450.", days_ago=3)
        assign_ticket(db, ticket=t3, assignee=rohan, actor=rohan)
        add_message(db, ticket=t3, author=rohan, body="Hi Ravi, could you confirm your UPI ID? The one on your profile may be outdated.")
        t3.awaiting_member = True
        t3.paused_at = now - timedelta(hours=18)
        db.flush()
        log_event(db, ticket_id=t3.id, actor_id=rohan.id, event_type="paused", created_at=now - timedelta(hours=18))

        # 4. Escalated — Meera
        t4 = make_ticket(meera, "Payment", "My payment is 15 days overdue. I have not received Rs 600 for the FMCG survey. This is urgent.", days_ago=6)
        assign_ticket(db, ticket=t4, assignee=asha, actor=asha)
        t4.status = "Escalated"
        t4.due_at = now - timedelta(hours=5)
        log_event(db, ticket_id=t4.id, actor_id=None, event_type="escalated", from_value="In Progress", to_value="Escalated",
                  reason="TAT breached: target 240 working min, elapsed ~360 working min.")
        db.flush()

        # 5. Resolved — waiting for confirm — Dinesh
        t5 = make_ticket(dinesh, "Survey issue", "Survey link for the automobile study was not working. I completed it on a different browser eventually.", days_ago=4)
        assign_ticket(db, ticket=t5, assignee=fatima, actor=fatima)
        add_message(db, ticket=t5, author=fatima, body="Hi Dinesh, I am glad you were able to complete it. I have logged the technical issue with our team. Your payment will be processed as normal within 7 working days.")
        resolve_ticket(db, ticket=t5, message="Your participation has been confirmed and payment is on its way. Thank you for your patience.", actor=fatima)

        # 6. Closed — Kavita
        t6 = make_ticket(kavita, "Eligibility", "Why am I not eligible for the new pharma project? I was eligible last week.", days_ago=10)
        assign_ticket(db, ticket=t6, assignee=asha, actor=asha)
        add_message(db, ticket=t6, author=asha, body="Hi Kavita, you completed the FMCG project on 2 Oct. Our cool-off policy means you are not eligible for another project for 90 days. Your next eligibility date is 1 Jan 2027.")
        resolve_ticket(db, ticket=t6, message="I hope this explains the eligibility policy. Please do not hesitate to reach out if you have more questions.", actor=asha)
        confirm_ticket(db, ticket=t6, actor=kavita)

        # 7. Reopened — Ajay (reopen_count=1)
        t7 = make_ticket(ajay, "Payment", "Payment of Rs 350 for the banking survey has not arrived. Project was completed on 1 Nov.", days_ago=8)
        assign_ticket(db, ticket=t7, assignee=rohan, actor=rohan)
        add_message(db, ticket=t7, author=rohan, body="Hi Ajay, I checked and the payment was processed on 5 Nov to ajay.verma@ybl. Please check your UPI app.")
        resolve_ticket(db, ticket=t7, message="Payment confirmed as sent on 5 Nov. Please allow 24 hours for it to reflect.", actor=rohan)
        reopen_ticket(db, ticket=t7, reason="I checked my UPI and there is no credit. Can you share the UTR number?", actor=ajay)

        # 8. Profile change — UPI ID — Sunita
        t8 = make_ticket(sunita, "Profile change", "My UPI ID has changed. Please update it.", days_ago=1,
                         req_field="UPI ID", req_value="sunita.patil@okaxis")
        assign_ticket(db, ticket=t8, assignee=fatima, actor=fatima)

        # 9. Profile change — Name — Pooja
        t9 = make_ticket(pooja, "Profile change", "My name was misspelled during registration as 'Pooja Kulkarni'. The correct spelling is 'Pooja Kulkarni'. Please correct.", days_ago=2,
                         req_field="Name", req_value="Pooja Kulkarni")

        # 10. Open — Nilesh eligibility
        t10 = make_ticket(nilesh, "Eligibility", "I tried to register for the healthcare project but it says I am not eligible. I last completed a project 4 months ago — the cool-off should be over.", days_ago=0)

        # 11. Open — Sanjay payment
        t11 = make_ticket(sanjay, "Payment", "Rs 500 for the education sector study completed on 15 Nov not received yet. It has been 6 days.", days_ago=1)

        # 12. Open — Rekha other
        t12 = make_ticket(rekha, "Other", "I am getting duplicate survey invitations. I keep receiving the same invite three times a day. Can you stop this?", days_ago=0)

        # 13. Escalated — second one
        t13 = make_ticket(priya, "Payment", "Still no payment for the second project I completed on 5 Nov.", days_ago=7)
        assign_ticket(db, ticket=t13, assignee=rohan, actor=rohan)
        t13.status = "Escalated"
        t13.due_at = now - timedelta(hours=2)
        log_event(db, ticket_id=t13.id, actor_id=None, event_type="escalated", from_value="In Progress", to_value="Escalated",
                  reason="TAT breached: target 240 working min, elapsed ~300 working min.")
        db.flush()

        # 14. Awaiting member — second
        t14 = make_ticket(amit, "Profile change", "Please update my city from Thane to Navi Mumbai.", days_ago=4,
                          req_field="City", req_value="Navi Mumbai")
        assign_ticket(db, ticket=t14, assignee=asha, actor=asha)
        add_message(db, ticket=t14, author=asha, body="Hi Amit, could you confirm your date of birth for identity verification?")
        t14.awaiting_member = True
        t14.paused_at = now - timedelta(hours=6)
        db.flush()

        # 15. Auto-resolved (simulated)
        t15 = make_ticket(meera, "Survey issue", "My survey link expired before I could finish.", days_ago=5)
        assign_ticket(db, ticket=t15, assignee=fatima, actor=fatima)
        add_message(db, ticket=t15, author=fatima, body="Hi Meera, we have sent a fresh link. Could you confirm once you have received it?")
        t15.awaiting_member = True
        t15.paused_at = now - timedelta(days=4)
        t15.status = "Resolved"
        t15.resolved_at = now - timedelta(days=1)
        t15.awaiting_member = False
        log_event(db, ticket_id=t15.id, actor_id=None, event_type="auto_resolved",
                  from_value="In Progress", to_value="Resolved",
                  reason="No reply from member for 3 days after info request.")
        db.flush()

        db.commit()
        print("\n[seed] Seeding complete!\n")
        _print_login_table(db)


def _print_login_table(db: Session):
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.role, User.name).all()
    print(f"{'Role':<10} {'Name':<20} {'Email':<40} {'ID':<5}")
    print("─" * 80)
    for u in users:
        print(f"{u.role:<10} {u.name:<20} {u.email:<40} {u.id:<5}")
    print("\nOpen http://localhost:8000/login and click any persona to sign in.\n")


if __name__ == "__main__":
    seed()
