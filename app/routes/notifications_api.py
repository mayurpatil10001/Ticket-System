"""Notifications API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.security import get_current_user
from app.db import get_db
from app.models.notification import Notification
from app.models.user import User
from app.services import escalation

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
async def api_list_notifications(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    escalation.escalation_sweep(db)
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == actor.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": n.id,
            "ticket_id": n.ticket_id,
            "kind": n.kind,
            "body": n.body,
            "read": n.read_at is not None,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]


@router.post("/notifications/{notif_id}/read")
async def api_read_notification(
    notif_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    n = db.query(Notification).filter(
        Notification.id == notif_id, Notification.user_id == actor.id
    ).first()
    if n and not n.read_at:
        n.read_at = clock.now()
        db.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
async def api_read_all_notifications(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    now = clock.now()
    db.query(Notification).filter(
        Notification.user_id == actor.id,
        Notification.read_at.is_(None),
    ).update({"read_at": now})
    db.commit()
    return {"ok": True}
