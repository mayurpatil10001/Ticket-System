"""Messages API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.ticket import MessageRequest
from app.services.message_service import add_message
from app.services.ticket_service import get_ticket_or_404

router = APIRouter(tags=["messages"])


@router.post("/tickets/{public_id}/messages", status_code=201)
async def api_add_message(
    public_id: str,
    body: MessageRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, public_id, actor)
    msg = add_message(
        db,
        ticket=ticket,
        author=actor,
        body=body.body,
        is_internal_note=body.is_internal_note,
    )
    return {
        "id": msg.id,
        "body": msg.body,
        "is_internal_note": msg.is_internal_note,
        "created_at": msg.created_at.isoformat(),
    }
