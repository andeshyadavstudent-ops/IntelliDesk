"""
IntelliDesk Email Service
Uses Resend HTTP API instead of Gmail SMTP.
This works better on Render Free because SMTP ports are blocked.
"""

import os
import httpx
from typing import Optional


RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send email using Resend API.
    Returns True if email is sent successfully, otherwise False.
    """
    if not RESEND_API_KEY:
        print("[EMAIL] RESEND_API_KEY is missing. Email not sent.")
        return False

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
            timeout=15,
        )

        if response.status_code in [200, 201]:
            print(f"[EMAIL] Email sent successfully to {to_email}")
            return True

        print(f"[EMAIL] Failed: {response.status_code} - {response.text}")
        return False

    except Exception as e:
        print(f"[EMAIL] Failed to send email: {e}")
        return False


def send_verification_email(
    user_email: str,
    user_name: str,
    verification_link: Optional[str] = None
) -> bool:
    """
    Send account verification email.
    This matches the existing auth_routes.py function call.
    """
    if verification_link is None:
        verification_link = BASE_URL

    subject = "Verify your IntelliDesk account"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2>Welcome to IntelliDesk, {user_name}!</h2>
        <p>Thank you for registering with IntelliDesk.</p>
        <p>Please click the button below to verify your account:</p>

        <p>
            <a href="{verification_link}"
               style="background-color:#2563eb;color:white;padding:12px 18px;
               text-decoration:none;border-radius:6px;display:inline-block;">
               Verify Account
            </a>
        </p>

        <p>If the button does not work, copy and paste this link into your browser:</p>
        <p>{verification_link}</p>

        <br>
        <p>Regards,<br>IntelliDesk Support Team</p>
    </div>
    """

    return _send_email(user_email, subject, html_body)


def send_ticket_notification(
    user_email: str,
    user_name: str,
    ticket_id: int,
    ticket_subject: str
) -> bool:
    """
    Send ticket creation/update notification.
    """
    ticket_link = f"{BASE_URL}/tickets/{ticket_id}"

    subject = f"IntelliDesk Ticket Update - #{ticket_id}"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2>Hello {user_name},</h2>
        <p>Your IntelliDesk support ticket has been created or updated.</p>

        <p><strong>Ticket ID:</strong> #{ticket_id}</p>
        <p><strong>Subject:</strong> {ticket_subject}</p>

        <p>
            <a href="{ticket_link}"
               style="background-color:#2563eb;color:white;padding:12px 18px;
               text-decoration:none;border-radius:6px;display:inline-block;">
               View Ticket
            </a>
        </p>

        <br>
        <p>Regards,<br>IntelliDesk Support Team</p>
    </div>
    """

    return _send_email(user_email, subject, html_body)
def send_ticket_opened_email(user_email, user_name, ticket_id, ticket_subject):
    return send_ticket_notification(
        user_email=user_email,
        user_name=user_name,
        ticket_id=ticket_id,
        ticket_subject=ticket_subject,
    )


def send_ticket_status_update_email(user_email, user_name, ticket_id, ticket_subject):
    return send_ticket_notification(
        user_email=user_email,
        user_name=user_name,
        ticket_id=ticket_id,
        ticket_subject=ticket_subject,
    )
