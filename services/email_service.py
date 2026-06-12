"""
IntelliDesk Email Service
Uses Brevo API for public email notifications.
"""

import os
import requests
from typing import Optional


BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "intellideskitsupport@gmail.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "IntelliDesk Support")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    if not BREVO_API_KEY:
        print("[EMAIL] BREVO_API_KEY is missing. Email not sent.")
        return False

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
            },
            json={
                "sender": {
                    "name": EMAIL_FROM_NAME,
                    "email": EMAIL_FROM,
                },
                "to": [
                    {
                        "email": to_email,
                    }
                ],
                "subject": subject,
                "htmlContent": html_body,
            },
            timeout=20,
        )

        if response.status_code in [200, 201, 202]:
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

        <p>If the button does not work, copy and paste this link:</p>
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
    ticket_link = f"{BASE_URL}/tickets/{ticket_id}"

    subject = f"IntelliDesk Ticket Notification - #{ticket_id}"

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


# Compatibility wrapper functions for old IntelliDesk code

def send_ticket_opened_email(
    user_email=None,
    user_name="User",
    ticket_id=None,
    ticket_subject="Support Ticket",
    ticket_display_id=None,
    **kwargs
):
    return send_ticket_notification(user_email, user_name, ticket_id, ticket_subject)


def send_ticket_status_update_email(
    user_email=None,
    user_name="User",
    ticket_id=None,
    ticket_subject="Support Ticket",
    ticket_display_id=None,
    **kwargs
):
    return send_ticket_notification(user_email, user_name, ticket_id, ticket_subject)


def send_ticket_reply_email(
    user_email=None,
    user_name="User",
    ticket_id=None,
    ticket_subject="Support Ticket",
    ticket_display_id=None,
    **kwargs
):
    return send_ticket_notification(user_email, user_name, ticket_id, ticket_subject)


def send_ticket_closed_email(
    user_email=None,
    user_name="User",
    ticket_id=None,
    ticket_subject="Support Ticket",
    ticket_display_id=None,
    **kwargs
):
    return send_ticket_notification(user_email, user_name, ticket_id, ticket_subject)
