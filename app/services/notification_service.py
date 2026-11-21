"""Notification service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.clock import clock
from app.models.notification import Notification
from app.models.user import User


def create_notification(
    db: Session,
    *,
    user_id: int,
    ticket_id: int | None,
    kind: str,
    body: str,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        ticket_id=ticket_id,
        kind=kind,
        body=body,
        created_at=clock.now(),
    )
    db.add(notif)
    return notif


def notify_all_heads(
    db: Session,
    *,
    ticket_id: int | None,
    kind: str,
    body: str,
) -> list[Notification]:
    heads = db.query(User).filter(User.role == "head", User.is_active.is_(True)).all()
    notifs = []
    for head in heads:
        notifs.append(create_notification(db, user_id=head.id, ticket_id=ticket_id, kind=kind, body=body))
    return notifs


def unread_count(db: Session, user_id: int) -> int:
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    ).count()
