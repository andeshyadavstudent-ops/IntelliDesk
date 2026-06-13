"""
IntelliDesk Auth Routes
Login, Register, Logout + Email Verification
"""

import secrets
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import get_db, settings
from models import User, UserRole
from auth import hash_password, verify_password, create_access_token, get_current_user_optional
from services.email_service import send_verification_email

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _base_url(request: Request) -> str:
    return getattr(settings, "BASE_URL", str(request.base_url).rstrip("/"))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user:
        if user.role.value == "admin":
            return RedirectResponse(url="/admin", status_code=303)
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
        )

    if not user.is_verified:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Please verify your email before logging in. Check your inbox for the activation link.",
            },
        )

    token = create_access_token(
        data={"user_id": user.id, "email": user.email, "role": user.role.value}
    )

    response = RedirectResponse(
        url="/admin" if user.role.value == "admin" else "/dashboard",
        status_code=303,
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register")
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Passwords do not match"},
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password must be at least 6 characters"},
        )

    existing_email = db.query(User).filter(
        User.email == email.strip().lower()
    ).first()

    if existing_email:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "This email address is already taken."},
        )

    existing_name = db.query(User).filter(
        User.name == name.strip()
    ).first()

    if existing_name:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "This username is already taken."},
        )

    token = secrets.token_urlsafe(32)
    new_user = User(
        name=name.strip(),
        email=email.strip().lower(),
        password_hash=hash_password(password),
        role=UserRole.USER,
        is_verified=False,
        verification_token=token,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verification_link = f"{_base_url(request)}/verify-email?token={token}"
    send_verification_email(
        user_email=new_user.email,
        user_name=new_user.name,
        verification_link=verification_link,
    )

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "error": None,
            "success": f"Account created. We sent a verification email to {new_user.email}.",
        },
    )


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid or expired activation link."},
        )

    user.is_verified = True
    user.verification_token = None
    db.commit()

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None, "success": "Account verified. You can now log in."},
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
