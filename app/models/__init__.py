"""Models package — import all so SQLAlchemy registers them."""
from app.models.base import Base
from app.models.user import User
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.ticket_event import TicketEvent
from app.models.settings import Setting, CategoryPriorityMap
from app.models.holiday import Holiday
from app.models.saved_reply import SavedReply
from app.models.notification import Notification
from app.models.internal_ticket import InternalTicket
from app.models.ticket_counter import TicketCounter

__all__ = [
    "Base",
    "User",
    "Ticket",
    "TicketMessage",
    "TicketEvent",
    "Setting",
    "CategoryPriorityMap",
    "Holiday",
    "SavedReply",
    "Notification",
    "InternalTicket",
    "TicketCounter",
]
