"""
IntelliDesk Ticket Service
Business logic for ticket operations, notifications, feedback, attachments, and search.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, cast, String

from models import (
    Ticket, Message, User, TicketStatus, TicketPriority,
    TicketCategory, SenderType, ChatLog, now_sydney
)
from services.email_service import (
    send_ticket_opened_email,
    send_ticket_reply_email,
    send_ticket_closed_email,
)


def _safe_category(category: str) -> TicketCategory:
    try:
        return TicketCategory(category)
    except Exception:
        return TicketCategory.GENERAL


def _safe_priority(priority: str) -> TicketPriority:
    try:
        return TicketPriority(priority)
    except Exception:
        return TicketPriority.MEDIUM


def _safe_status(status: str) -> TicketStatus:
    try:
        return TicketStatus(status)
    except Exception:
        return TicketStatus.OPEN


def get_next_user_ticket_number(db: Session, user_id: int) -> int:
    """Generate ticket number separately for each user."""
    last_number = (
        db.query(func.max(Ticket.user_ticket_number))
        .filter(Ticket.user_id == user_id)
        .scalar()
    )
    return int(last_number or 0) + 1


def create_ticket(
    db: Session,
    user_id: int,
    subject: str,
    description: str,
    category: str = "general",
    priority: str = "medium",
    attachment_path: Optional[str] = None,
) -> Ticket:
    """Create a new IT support ticket and email the user."""
    ticket = Ticket(
        user_id=user_id,
        user_ticket_number=get_next_user_ticket_number(db, user_id),
        subject=subject.strip(),
        description=description.strip(),
        category=_safe_category(category),
        priority=_safe_priority(priority),
        status=TicketStatus.OPEN,
        attachment_path=attachment_path,
        created_at=now_sydney(),
        updated_at=now_sydney(),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Initial message is unread for admin, so admin dashboard can show notification.
    initial_message = Message(
        ticket_id=ticket.id,
        sender=SenderType.USER,
        content=description.strip(),
        attachment_path=attachment_path,
        is_read=False,
        created_at=now_sydney(),
    )
    db.add(initial_message)
    db.commit()
    db.refresh(ticket)

    if ticket.user and ticket.user.email:
        send_ticket_opened_email(
            user_email=ticket.user.email,
            user_name=ticket.user.name,
            ticket_display_id=ticket.display_id,
            subject_text=ticket.subject,
        )

    return ticket


def get_ticket(db: Session, ticket_id: int) -> Optional[Ticket]:
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def get_user_tickets(db: Session, user_id: int) -> List[Ticket]:
    return (
        db.query(Ticket)
        .filter(Ticket.user_id == user_id)
        .order_by(desc(Ticket.created_at))
        .all()
    )


def search_user_tickets(
    db: Session,
    user_id: int,
    query: str = "",
    status_filter: str = "all",
) -> List[Ticket]:
    """Search tickets for the logged-in user."""
    ticket_query = db.query(Ticket).filter(Ticket.user_id == user_id)

    if status_filter and status_filter != "all":
        ticket_query = ticket_query.filter(Ticket.status == _safe_status(status_filter))

    search = (query or "").strip().lower()
    if search:
        filters = [
            func.lower(Ticket.subject).like(f"%{search}%"),
            func.lower(Ticket.description).like(f"%{search}%"),
            func.lower(cast(Ticket.category, String)).like(f"%{search}%"),
            func.lower(cast(Ticket.status, String)).like(f"%{search}%"),
            func.lower(cast(Ticket.priority, String)).like(f"%{search}%"),
        ]
        if search.isdigit():
            filters.append(Ticket.id == int(search))
            filters.append(Ticket.user_ticket_number == int(search))
        ticket_query = ticket_query.filter(or_(*filters))

    tickets = ticket_query.order_by(desc(Ticket.created_at)).all()
    attach_user_unread_flags(db, tickets, user_id)
    return tickets


def get_all_tickets(
    db: Session,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
) -> List[Ticket]:
    query = db.query(Ticket)

    if status_filter and status_filter != "all":
        query = query.filter(Ticket.status == _safe_status(status_filter))
    if category_filter and category_filter != "all":
        query = query.filter(Ticket.category == _safe_category(category_filter))
    if priority_filter and priority_filter != "all":
        query = query.filter(Ticket.priority == _safe_priority(priority_filter))

    tickets = query.order_by(desc(Ticket.created_at)).all()
    attach_admin_unread_flags(db, tickets)
    return tickets


def search_tickets(
    db: Session,
    query: str,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
) -> List[Ticket]:
    search = (query or "").strip().lower()
    ticket_query = db.query(Ticket).join(User)

    if status_filter and status_filter != "all":
        ticket_query = ticket_query.filter(Ticket.status == _safe_status(status_filter))
    if category_filter and category_filter != "all":
        ticket_query = ticket_query.filter(Ticket.category == _safe_category(category_filter))
    if priority_filter and priority_filter != "all":
        ticket_query = ticket_query.filter(Ticket.priority == _safe_priority(priority_filter))

    if search:
        filters = [
            func.lower(Ticket.subject).like(f"%{search}%"),
            func.lower(Ticket.description).like(f"%{search}%"),
            func.lower(User.name).like(f"%{search}%"),
            func.lower(User.email).like(f"%{search}%"),
            func.lower(cast(Ticket.category, String)).like(f"%{search}%"),
            func.lower(cast(Ticket.status, String)).like(f"%{search}%"),
            func.lower(cast(Ticket.priority, String)).like(f"%{search}%"),
        ]

        numeric_part = "".join(ch for ch in search if ch.isdigit())
        if search.isdigit():
            filters.append(Ticket.id == int(search))
            filters.append(Ticket.user_ticket_number == int(search))

        if search.startswith("u") and "-t" in search:
            try:
                user_part, ticket_part = search.replace("u", "").split("-t")
                filters.append(
                    (Ticket.user_id == int(user_part)) &
                    (Ticket.user_ticket_number == int(ticket_part))
                )
            except Exception:
                pass
        elif numeric_part and "t" in search:
            try:
                filters.append(Ticket.user_ticket_number == int(numeric_part))
            except Exception:
                pass

        ticket_query = ticket_query.filter(or_(*filters))

    tickets = ticket_query.order_by(desc(Ticket.created_at)).all()
    attach_admin_unread_flags(db, tickets)
    return tickets


def update_ticket_status(db: Session, ticket_id: int, status: str) -> Optional[Ticket]:
    """Update ticket status and email the user when closed."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return None

    old_status = ticket.status.value if ticket.status else None
    ticket.status = _safe_status(status)
    ticket.updated_at = now_sydney()
    db.commit()
    db.refresh(ticket)

    if status == "closed" and old_status != "closed" and ticket.user and ticket.user.email:
        send_ticket_closed_email(
            user_email=ticket.user.email,
            user_name=ticket.user.name,
            ticket_display_id=ticket.display_id,
            subject_text=ticket.subject,
        )

    return ticket


def update_ticket_priority(db: Session, ticket_id: int, priority: str) -> Optional[Ticket]:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket:
        ticket.priority = _safe_priority(priority)
        ticket.updated_at = now_sydney()
        db.commit()
        db.refresh(ticket)
    return ticket


def update_ticket(
    db: Session,
    ticket_id: int,
    subject: str,
    description: str,
    category: str,
    priority: str,
    status: str,
) -> Optional[Ticket]:
    """Admin update for full ticket details."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return None

    old_status = ticket.status.value if ticket.status else None
    ticket.subject = subject.strip()
    ticket.description = description.strip()
    ticket.category = _safe_category(category)
    ticket.priority = _safe_priority(priority)
    ticket.status = _safe_status(status)
    ticket.updated_at = now_sydney()
    db.commit()
    db.refresh(ticket)

    if status == "closed" and old_status != "closed" and ticket.user and ticket.user.email:
        send_ticket_closed_email(ticket.user.email, ticket.user.name, ticket.display_id, ticket.subject)

    return ticket


def add_message(
    db: Session,
    ticket_id: int,
    sender: str,
    content: str,
    attachment_path: Optional[str] = None,
) -> Optional[Message]:
    """Add a message/reply to a ticket. Supports image attachments and notifications."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return None

    message = Message(
        ticket_id=ticket_id,
        sender=SenderType(sender),
        content=content.strip(),
        attachment_path=attachment_path,
        is_read=False,
        created_at=now_sydney(),
    )
    db.add(message)
    ticket.updated_at = now_sydney()
    db.commit()
    db.refresh(message)

    if sender == "admin" and ticket.user and ticket.user.email:
        send_ticket_reply_email(
            user_email=ticket.user.email,
            user_name=ticket.user.name,
            ticket_display_id=ticket.display_id,
            reply_text=content.strip(),
        )

    return message


def submit_feedback(
    db: Session,
    ticket_id: int,
    user_id: int,
    rating: int,
    comment: str = "",
) -> Optional[Ticket]:
    """User submits feedback after a ticket is closed."""
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.user_id == user_id)
        .first()
    )
    if not ticket or ticket.status.value != "closed":
        return None

    ticket.feedback_rating = max(1, min(5, int(rating)))
    ticket.feedback_comment = (comment or "").strip()
    ticket.feedback_submitted = True
    ticket.updated_at = now_sydney()
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_messages(db: Session, ticket_id: int) -> List[Message]:
    return (
        db.query(Message)
        .filter(Message.ticket_id == ticket_id)
        .order_by(Message.created_at)
        .all()
    )


def get_user_notification_count(db: Session, user_id: int) -> int:
    """Unread admin replies for a specific user."""
    return (
        db.query(Message)
        .join(Ticket, Message.ticket_id == Ticket.id)
        .filter(
            Ticket.user_id == user_id,
            Message.sender == SenderType.ADMIN,
            Message.is_read == False,
        )
        .count()
    )


def get_admin_notification_count(db: Session) -> int:
    """Unread user messages/new tickets for admin."""
    return (
        db.query(Message)
        .filter(
            Message.sender == SenderType.USER,
            Message.is_read == False,
        )
        .count()
    )


def get_user_ticket_unread_count(db: Session, ticket_id: int, user_id: int) -> int:
    return (
        db.query(Message)
        .join(Ticket, Message.ticket_id == Ticket.id)
        .filter(
            Ticket.id == ticket_id,
            Ticket.user_id == user_id,
            Message.sender == SenderType.ADMIN,
            Message.is_read == False,
        )
        .count()
    )


def get_admin_ticket_unread_count(db: Session, ticket_id: int) -> int:
    return (
        db.query(Message)
        .filter(
            Message.ticket_id == ticket_id,
            Message.sender == SenderType.USER,
            Message.is_read == False,
        )
        .count()
    )


def attach_user_unread_flags(db: Session, tickets: List[Ticket], user_id: int) -> List[Ticket]:
    for ticket in tickets:
        count = get_user_ticket_unread_count(db, ticket.id, user_id)
        ticket.unread_count = count
        ticket.has_unread = count > 0
    return tickets


def attach_admin_unread_flags(db: Session, tickets: List[Ticket]) -> List[Ticket]:
    for ticket in tickets:
        count = get_admin_ticket_unread_count(db, ticket.id)
        ticket.unread_count = count
        ticket.has_unread = count > 0
    return tickets


def mark_ticket_messages_read(db: Session, ticket_id: int, viewer_role: str, user_id: Optional[int] = None) -> int:
    """
    Mark messages as read when a ticket is opened.
    - User opening ticket marks admin replies as read.
    - Admin opening ticket marks user messages as read.
    """
    query = db.query(Message).filter(Message.ticket_id == ticket_id, Message.is_read == False)

    if viewer_role == "admin":
        query = query.filter(Message.sender == SenderType.USER)
    else:
        query = query.join(Ticket, Message.ticket_id == Ticket.id).filter(
            Ticket.user_id == user_id,
            Message.sender == SenderType.ADMIN,
        )

    messages = query.all()
    for msg in messages:
        msg.is_read = True

    if messages:
        db.commit()

    return len(messages)


def get_analytics_data(db: Session) -> dict:
    total = db.query(Ticket).count()
    open_count = db.query(Ticket).filter(Ticket.status == TicketStatus.OPEN).count()
    in_progress = db.query(Ticket).filter(Ticket.status == TicketStatus.IN_PROGRESS).count()
    closed = db.query(Ticket).filter(Ticket.status == TicketStatus.CLOSED).count()

    by_category = {cat.value: db.query(Ticket).filter(Ticket.category == cat).count() for cat in TicketCategory}
    by_priority = {pri.value: db.query(Ticket).filter(Ticket.priority == pri).count() for pri in TicketPriority}

    recent = db.query(Ticket).order_by(desc(Ticket.created_at)).limit(10).all()
    ai_resolved = db.query(ChatLog).filter(ChatLog.ticket_created.is_(None)).count()
    escalated = db.query(ChatLog).filter(ChatLog.ticket_created.isnot(None)).count()

    return {
        "total_tickets": total,
        "open_tickets": open_count,
        "in_progress_tickets": in_progress,
        "closed_tickets": closed,
        "ai_resolved": ai_resolved,
        "escalated": escalated,
        "avg_resolution_hours": 0.0,
        "tickets_by_category": by_category,
        "tickets_by_priority": by_priority,
        "recent_tickets": recent,
    }
