"""SavedReply CRUD service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.saved_reply import SavedReply
from app.models.user import User


def list_saved_replies(db: Session, category: str | None = None) -> list[SavedReply]:
    q = db.query(SavedReply)
    if category:
        q = q.filter((SavedReply.category == category) | (SavedReply.category.is_(None)))
    return q.order_by(SavedReply.title).all()


def create_saved_reply(
    db: Session, *, title: str, body: str, category: str | None, actor: User
) -> SavedReply:
    sr = SavedReply(title=title.strip(), body=body.strip(), category=category, created_by=actor.id)
    db.add(sr)
    db.commit()
    db.refresh(sr)
    return sr


def update_saved_reply(
    db: Session, *, reply_id: int, title: str, body: str, category: str | None
) -> SavedReply:
    sr = db.query(SavedReply).filter(SavedReply.id == reply_id).first()
    if not sr:
        from app.core.exceptions import NotFound
        raise NotFound("SavedReply")
    sr.title = title.strip()
    sr.body = body.strip()
    sr.category = category
    db.commit()
    db.refresh(sr)
    return sr


def delete_saved_reply(db: Session, *, reply_id: int) -> None:
    sr = db.query(SavedReply).filter(SavedReply.id == reply_id).first()
    if sr:
        db.delete(sr)
        db.commit()
