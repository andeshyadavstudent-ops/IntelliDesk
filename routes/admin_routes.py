"""
IntelliDesk Admin Routes
Admin dashboard, ticket management, search, edit, analytics, and notifications.
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import get_db
from models import User
from auth import require_admin
from services.ticket_service import (
    get_all_tickets,
    get_ticket,
    update_ticket_status,
    update_ticket_priority,
    update_ticket,
    search_tickets,
    get_analytics_data,
    get_admin_notification_count,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    status: str = "all",
    category: str = "all",
    priority: str = "all",
    q: str = "",
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin dashboard with filter, search, and unread notification badges."""
    if q and q.strip():
        tickets = search_tickets(
            db=db,
            query=q.strip(),
            status_filter=status,
            category_filter=category,
            priority_filter=priority,
        )
    else:
        tickets = get_all_tickets(
            db,
            status_filter=status,
            category_filter=category,
            priority_filter=priority,
        )

    all_tickets = get_all_tickets(db)
    total_all = len(all_tickets)
    open_all = sum(1 for t in all_tickets if t.status.value == "open")
    in_progress_all = sum(1 for t in all_tickets if t.status.value == "in_progress")
    closed_all = sum(1 for t in all_tickets if t.status.value == "closed")
    notification_count = get_admin_notification_count(db)

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "user": user,
            "tickets": tickets,
            "total": total_all,
            "open_count": open_all,
            "in_progress_count": in_progress_all,
            "closed_count": closed_all,
            "notification_count": notification_count,
            "current_status": status,
            "current_category": category,
            "current_priority": priority,
            "search_query": q,
        },
    )


@router.post("/admin/tickets/{ticket_id}/status")
async def change_ticket_status(
    ticket_id: int,
    status: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = update_ticket_status(db, ticket_id, status)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/admin/tickets/{ticket_id}/priority")
async def change_ticket_priority(
    ticket_id: int,
    priority: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = update_ticket_priority(db, ticket_id, priority)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.get("/admin/tickets/{ticket_id}/edit", response_class=HTMLResponse)
async def edit_ticket_page(
    request: Request,
    ticket_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return templates.TemplateResponse(
        "edit_ticket.html",
        {
            "request": request,
            "user": user,
            "ticket": ticket,
        },
    )


@router.post("/admin/tickets/{ticket_id}/edit")
async def edit_ticket_submit(
    ticket_id: int,
    subject: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    priority: str = Form(...),
    status: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = update_ticket(
        db=db,
        ticket_id=ticket_id,
        subject=subject,
        description=description,
        category=category,
        priority=priority,
        status=status,
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = get_analytics_data(db)

    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "user": user,
            "analytics": data,
        },
    )


@router.get("/api/analytics")
async def analytics_api(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = get_analytics_data(db)
    data["recent_tickets"] = [
        {
            "id": t.id,
            "display_id": t.display_id,
            "subject": t.subject,
            "category": t.category.value,
            "priority": t.priority.value,
            "status": t.status.value,
            "created_at": t.created_at.isoformat(),
        }
        for t in data["recent_tickets"]
    ]
    return JSONResponse(data)
