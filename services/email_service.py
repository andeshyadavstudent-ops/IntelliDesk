"""
IntelliDesk Email Service
Sends account verification/welcome emails and ticket notification emails.
"""

import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from typing import Optional

# Load .env explicitly from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

print(f"[EMAIL DEBUG] USER={EMAIL_USER}")
print(f"[EMAIL DEBUG] PASSWORD FOUND={bool(EMAIL_PASSWORD)}")


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a plain text email using Gmail SMTP."""
    if not EMAIL_PASSWORD:
        print("[EMAIL] EMAIL_PASSWORD is missing in .env. Email not sent.")
        return False

    try:
        msg = EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"[EMAIL] Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send email: {e}")
        return False


def send_verification_email(user_email: str, user_name: str, verification_link: Optional[str] = None) -> bool:
    body = f"""Hello {user_name},

Welcome to IntelliDesk.

Your profile has been created successfully.
"""
    if verification_link:
        body += f"Please verify your account using this link:\n{verification_link}\n\n"
    else:
        body += "Your account is ready to use.\n\n"

    body += "Regards,\nIntelliDesk IT Support\n"
    return send_email(user_email, "Welcome to IntelliDesk - Account Created", body)


def send_ticket_opened_email(user_email: str, user_name: str, ticket_display_id: str, subject_text: str) -> bool:
    body = f"""Hello {user_name},

Your IntelliDesk support ticket has been created successfully.

Ticket ID: {ticket_display_id}
Subject: {subject_text}
Status: Open

Our IT support team will review your request and provide an update.

Regards,
IntelliDesk IT Support
"""
    return send_email(user_email, f"Ticket Created - {ticket_display_id}", body)


def send_ticket_reply_email(user_email: str, user_name: str, ticket_display_id: str, reply_text: str) -> bool:
    body = f"""Hello {user_name},

A new reply has been added to your IntelliDesk support ticket.

Ticket ID: {ticket_display_id}

Reply:
{reply_text}

Please log in to IntelliDesk to view the full conversation.

Regards,
IntelliDesk IT Support
"""
    return send_email(user_email, f"New Reply on Ticket - {ticket_display_id}", body)


def send_ticket_closed_email(user_email: str, user_name: str, ticket_display_id: str, subject_text: str) -> bool:
    body = f"""Hello {user_name},

Your IntelliDesk support ticket has been closed.

Ticket ID: {ticket_display_id}
Subject: {subject_text}
Status: Closed

Please log in to IntelliDesk and submit feedback about your support experience.

Regards,
IntelliDesk IT Support
"""
    return send_email(user_email, f"Ticket Closed - {ticket_display_id}", body)
