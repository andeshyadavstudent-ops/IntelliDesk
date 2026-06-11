"""
IntelliDesk Ticket Routes
User ticket operations, IT-only manual ticket creation, attachments, feedback, and notifications.
"""

import os
import shutil
from uuid import uuid4
from fastapi import APIRouter, Depends, Request, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import get_db
from models import User
from auth import get_current_user
from services.ticket_service import (
    create_ticket,
    get_ticket,
    get_ticket_messages,
    add_message,
    search_user_tickets,
    submit_feedback,
    get_user_notification_count,
    mark_ticket_messages_read,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Manual ticket creation should be restricted to IT-related support.
IT_KEYWORDS = [
    "password", "login", "log in", "sign in", "account", "mfa", "2fa",
    "wifi", "wi-fi", "internet", "network", "vpn", "ethernet", "router", "dns",
    "software", "install", "installation", "update", "upgrade", "application", "app", "program", "license",
    "windows", "mac", "macos", "linux", "computer", "laptop", "pc", "desktop", "operating system",
    "keyboard", "mouse", "printer", "monitor", "screen", "hardware", "charger", "usb", "webcam", "headset",
    "access", "permission", "sharepoint", "onedrive", "folder", "shared drive", "admin rights", "denied",
    "email", "outlook", "teams", "browser", "chrome", "edge", "firewall", "security", "malware", "virus",
    "error", "bug", "crash", "not working", "broken", "slow", "freeze", "technical", "device", "system issue",
]

NON_IT_KEYWORDS = [
    "restaurant", "table", "dinner", "lunch", "breakfast", "reservation", "book a table", "booking table",
    "hotel", "flight", "travel", "movie", "cinema", "shopping", "order food", "pizza", "taxi", "uber",
    "homework", "assignment", "essay", "recipe", "weather", "capital of",
]

IT_CATEGORIES = {"network", "software", "hardware", "access", "password"}


def is_manual_ticket_it_related(subject: str, description: str, category: str) -> bool:
    text = f"{subject} {description}".lower()

    if any(word in text for word in NON_IT_KEYWORDS) and not any(word in text for word in IT_KEYWORDS):
        return False

    if category in IT_CATEGORIES:
        return True

    return any(word in text for word in IT_KEYWORDS)


def save_upload_file(upload: UploadFile, prefix: str) -> str | None:
    """Save an uploaded file into static/uploads and return browser path."""
    if not upload or not upload.filename:
        return None

    safe_name = upload.filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"{prefix}_{uuid4().hex}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    return "/" + file_path


@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    q: str = "",
    status: str = "all",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tickets = search_user_tickets(db, user.id, q, status)
    all_tickets = search_user_tickets(db, user.id, "", "all")

    open_count = sum(1 for t in all_tickets if t.status.value == "open")
    in_progress_count = sum(1 for t in all_tickets if t.status.value == "in_progress")
    closed_count = sum(1 for t in all_tickets if t.status.value == "closed")
    notification_count = get_user_notification_count(db, user.id)

    return templates.TemplateResponse(
        "user_dashboard.html",
        {
            "request": request,
            "user": user,
            "tickets": tickets,
            "open_count": open_count,
            "in_progress_count": in_progress_count,
            "closed_count": closed_count,
            "notification_count": notification_count,
            "search_query": q,
            "current_status": status,
        },
    )


@router.get("/tickets/new", response_class=HTMLResponse)
async def new_ticket_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "create_ticket.html",
        {"request": request, "user": user, "error": None},
    )


@router.post("/tickets/new")
async def submit_ticket(
    request: Request,
    subject: str = Form(...),
    description: str = Form(...),
    category: str = Form("general"),
    priority: str = Form("medium"),
    attachment: UploadFile = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_manual_ticket_it_related(subject, description, category):
        return templates.TemplateResponse(
            "create_ticket.html",
            {
                "request": request,
                "user": user,
                "error": "This request is outside the scope of IntelliDesk IT Support. No ticket has been created.",
                "subject_value": subject,
                "description_value": description,
                "category_value": category,
                "priority_value": priority,
            },
            status_code=400,
        )

    attachment_path = save_upload_file(attachment, f"ticket_user_{user.id}")

    ticket = create_ticket(
        db=db,
        user_id=user.id,
        subject=subject,
        description=description,
        category=category,
        priority=priority,
        attachment_path=attachment_path,
    )
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
async def view_ticket(
    request: Request,
    ticket_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if user.role.value != "admin" and ticket.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    mark_ticket_messages_read(db, ticket_id, user.role.value, user.id)
    messages = get_ticket_messages(db, ticket_id)

    return templates.TemplateResponse(
        "view_ticket.html",
        {"request": request, "user": user, "ticket": ticket, "messages": messages},
    )


@router.post("/tickets/{ticket_id}/message")
async def add_ticket_message(
    ticket_id: int,
    content: str = Form(""),
    attachment: UploadFile = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if user.role.value != "admin" and ticket.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not content.strip() and not (attachment and attachment.filename):
        raise HTTPException(status_code=400, detail="Please enter a message or attach a file.")

    sender = "admin" if user.role.value == "admin" else "user"
    attachment_path = save_upload_file(attachment, f"reply_{sender}_{user.id}")

    add_message(
        db=db,
        ticket_id=ticket_id,
        sender=sender,
        content=content or "File attached.",
        attachment_path=attachment_path,
    )
    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/feedback")
async def submit_ticket_feedback(
    ticket_id: int,
    rating: int = Form(...),
    comment: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = submit_feedback(db, ticket_id, user.id, rating, comment)
    if not ticket:
        raise HTTPException(status_code=400, detail="Feedback can only be submitted for your closed ticket.")
    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)
