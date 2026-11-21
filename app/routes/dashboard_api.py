"""Dashboard API (head only)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.security import require_head
from app.db import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.services import escalation

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def api_dashboard(
    db: Session = Depends(get_db),
    actor=Depends(require_head),
):
    # Lazy sweep
    escalation.escalation_sweep(db)
    escalation.auto_resolve_awaiting(db)
    escalation.auto_close_resolved(db)

    now = clock.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    open_count = db.query(Ticket).filter(Ticket.status == "Open").count()
    overdue_count = db.query(Ticket).filter(
        Ticket.status.in_(["Open", "In Progress", "Reopened", "Escalated"]),
        Ticket.due_at <= now,
    ).count()
    escalated_count = db.query(Ticket).filter(Ticket.status == "Escalated").count()
    resolved_today = db.query(Ticket).filter(
        Ticket.status.in_(["Resolved", "Closed"]),
        Ticket.resolved_at >= today_start,
    ).count()

    # Avg resolution (exclude paused time — use resolved_at - created_at as simple proxy)
    resolved_all = db.query(Ticket).filter(Ticket.resolved_at.isnot(None)).all()
    if resolved_all:
        total_mins = sum(
            int((t.resolved_at - t.created_at).total_seconds() // 60)
            for t in resolved_all
            if t.resolved_at and t.created_at
        )
        avg_resolution = total_mins // len(resolved_all)
    else:
        avg_resolution = 0

    # By category
    category_rows = (
        db.query(Ticket.category, func.count(Ticket.id))
        .filter(Ticket.status.notin_(["Closed"]))
        .group_by(Ticket.category)
        .all()
    )
    by_category = [{"category": c, "count": n} for c, n in category_rows]

    # Agent load
    agents = db.query(User).filter(User.role == "agent", User.is_active.is_(True)).all()
    agent_load = []
    for agent in agents:
        open_a = db.query(Ticket).filter(
            Ticket.assignee_id == agent.id,
            Ticket.status.in_(["Open", "In Progress", "Reopened", "Escalated"]),
        ).count()
        overdue_a = db.query(Ticket).filter(
            Ticket.assignee_id == agent.id,
            Ticket.due_at <= now,
            Ticket.status.in_(["Open", "In Progress", "Reopened"]),
        ).count()
        # Avg first response (minutes)
        responded = db.query(Ticket).filter(
            Ticket.assignee_id == agent.id,
            Ticket.first_response_at.isnot(None),
        ).all()
        if responded:
            avg_fr = sum(
                int((t.first_response_at - t.created_at).total_seconds() // 60)
                for t in responded
                if t.first_response_at and t.created_at
            ) // len(responded)
        else:
            avg_fr = None

        agent_load.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "open": open_a,
            "overdue": overdue_a,
            "avg_first_response_minutes": avg_fr,
        })

    # Escalation inbox
    escalated = (
        db.query(Ticket)
        .filter(Ticket.status == "Escalated")
        .order_by(Ticket.due_at.asc())
        .all()
    )

    return {
        "open": open_count,
        "overdue": overdue_count,
        "escalated": escalated_count,
        "resolved_today": resolved_today,
        "avg_resolution_minutes": avg_resolution,
        "by_category": by_category,
        "agent_load": agent_load,
        "escalation_inbox": [
            {
                "public_id": t.public_id,
                "subject": t.subject,
                "priority": t.priority,
                "category": t.category,
                "assignee_id": t.assignee_id,
                "due_at": t.due_at.isoformat() if t.due_at else None,
            }
            for t in escalated
        ],
    }
