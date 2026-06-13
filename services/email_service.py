import os
from dotenv import load_dotenv
load_dotenv()
import requests
from typing import Optional

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "intellideskitsupport@gmail.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "IntelliDesk Support")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    if not to_email:
        print("[EMAIL] Missing recipient email. Email not sent.")
        return False

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
                "to": [{"email": to_email}],
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


def _ticket_email(
    user_email=None,
    user_name="User",
    ticket_id=None,
    ticket_subject="Support Ticket",
    ticket_display_id=None,
    notification_type="Ticket Update",
    message="Your IntelliDesk ticket has been updated.",
    **kwargs
):
    ticket_ref = ticket_display_id or ticket_id or kwargs.get("display_id") or kwargs.get("id") or "N/A"
    subject_text = ticket_subject or kwargs.get("subject") or kwargs.get("title") or "Support Ticket"
    ticket_link = f"{BASE_URL}/tickets/{ticket_id}" if ticket_id else BASE_URL

    subject = f"IntelliDesk {notification_type} - #{ticket_ref}"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2>Hello {user_name},</h2>

        <p>{message}</p>

        <p><strong>Ticket ID:</strong> #{ticket_ref}</p>
        <p><strong>Subject:</strong> {subject_text}</p>

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
        <p>Your IntelliDesk account has been created successfully.</p>
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


def send_account_verified_email(user_email, user_name="User", **kwargs):
    subject = "Your IntelliDesk account has been verified"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2>Hello {user_name},</h2>
        <p>Your IntelliDesk account has been successfully verified.</p>
        <p>You can now log in and use the AI helpdesk and ticket system.</p>

        <p>
            <a href="{BASE_URL}/login"
               style="background-color:#2563eb;color:white;padding:12px 18px;
               text-decoration:none;border-radius:6px;display:inline-block;">
               Login to IntelliDesk
            </a>
        </p>

        <br>
        <p>Regards,<br>IntelliDesk Support Team</p>
    </div>
    """

    return _send_email(user_email, subject, html_body)


def send_ticket_notification(
    user_email=None,
    user_name="User",
    ticket_id=None,
    ticket_subject="Support Ticket",
    **kwargs
):
    return _ticket_email(
        user_email=user_email,
        user_name=user_name,
        ticket_id=ticket_id,
        ticket_subject=ticket_subject,
        notification_type="Ticket Notification",
        message="Your IntelliDesk support ticket has been created or updated.",
        **kwargs
    )


def send_ticket_opened_email(**kwargs):
    return _ticket_email(
        notification_type="Ticket Created",
        message="Your support ticket has been created successfully. Our support team will review it shortly.",
        **kwargs
    )


def send_ticket_reply_email(**kwargs):
    return _ticket_email(
        notification_type="Ticket Reply",
        message="A new reply has been added to your support ticket.",
        **kwargs
    )


def send_ticket_status_update_email(**kwargs):
    return _ticket_email(
        notification_type="Ticket Status Updated",
        message="The status of your support ticket has been updated.",
        **kwargs
    )


def send_ticket_closed_email(**kwargs):
    return _ticket_email(
        notification_type="Ticket Closed",
        message="Your support ticket has been closed. If the issue still continues, please create a new ticket.",
        **kwargs
    )
