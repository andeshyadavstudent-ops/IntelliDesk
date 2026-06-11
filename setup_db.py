"""
IntelliDesk Database Setup Script
Creates all tables and seeds with initial data:
    - 1 Admin user (admin@intellidesk.com / admin123)
    - 1 Demo user (user@intellidesk.com / user123)
    - Sample tickets and chat logs for demonstration

Usage:
    python setup_db.py
"""

import sys
from datetime import datetime, timedelta
from config import engine, Base, SessionLocal
from models import (
    User, Ticket, Message, ChatLog,
    UserRole, TicketStatus, TicketPriority, TicketCategory, SenderType
)
from auth import hash_password


def setup_database():
    print("=" * 50)
    print("IntelliDesk - Database Setup")
    print("=" * 50)

    # Create all tables
    print("\n[1/4] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("      Tables created successfully.")

    db = SessionLocal()

    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"\n[!] Database already has {existing_users} users.")
            answer = input("    Do you want to reset and re-seed? (y/N): ").strip().lower()
            if answer != 'y':
                print("    Skipping seed. Database unchanged.")
                return
            # Drop and recreate
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            print("    Tables reset.")

        # Create users
        print("\n[2/4] Creating users...")
        admin = User(
            name="Avi Bhutani",
            email="admin@intellidesk.com",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN
        )
        user1 = User(
            name="Andesh Yadav",
            email="andesh@intellidesk.com",
            password_hash=hash_password("user123"),
            role=UserRole.USER
        )
        user2 = User(
            name="Varun Kumar",
            email="varun@intellidesk.com",
            password_hash=hash_password("user123"),
            role=UserRole.USER
        )
        db.add_all([admin, user1, user2])
        db.commit()
        db.refresh(admin)
        db.refresh(user1)
        db.refresh(user2)
        print(f"      Admin:  admin@intellidesk.com / admin123  (Avi Bhutani)")
        print(f"      User 1: andesh@intellidesk.com / user123  (Andesh Yadav)")
        print(f"      User 2: varun@intellidesk.com / user123   (Varun Kumar)")

        # Create sample tickets
        print("\n[3/4] Creating sample tickets...")
        sample_tickets = [
            {
                "subject": "Cannot connect to office Wi-Fi",
                "description": "I've been unable to connect to the office Wi-Fi network since this morning. My laptop shows the network but gives an authentication error when I try to connect. I've restarted my laptop twice already.",
                "category": TicketCategory.NETWORK,
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.OPEN,
                "created_at": datetime.utcnow() - timedelta(hours=2)
            },
            {
                "subject": "Need Microsoft Office license",
                "description": "I recently joined the team and need a Microsoft Office 365 license for my work laptop. My manager has approved the request. Employee ID: E-2045.",
                "category": TicketCategory.SOFTWARE,
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.IN_PROGRESS,
                "created_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "subject": "Laptop screen flickering",
                "description": "My Dell laptop screen has been flickering intermittently for the past two days. It happens more frequently when the laptop is plugged in. The flickering makes it difficult to work.",
                "category": TicketCategory.HARDWARE,
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.OPEN,
                "created_at": datetime.utcnow() - timedelta(days=2)
            },
            {
                "subject": "Password reset for CRM system",
                "description": "I've been locked out of the CRM system after too many failed login attempts. I need my password reset so I can access my client records.",
                "category": TicketCategory.PASSWORD,
                "priority": TicketPriority.LOW,
                "status": TicketStatus.CLOSED,
                "created_at": datetime.utcnow() - timedelta(days=3)
            },
            {
                "subject": "Request access to shared drive",
                "description": "I need access to the Marketing team's shared drive on the network. My manager Sarah has approved this. I need read and write access for the Q1 campaign materials.",
                "category": TicketCategory.ACCESS,
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.IN_PROGRESS,
                "created_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "subject": "VPN not connecting from home",
                "description": "I'm working from home today and the VPN client keeps timing out. I've checked my internet connection and it's fine. The VPN was working yesterday.",
                "category": TicketCategory.NETWORK,
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.OPEN,
                "created_at": datetime.utcnow() - timedelta(hours=5)
            },
        ]

        for i, t_data in enumerate(sample_tickets):
            # Alternate tickets between the two users
            ticket_user = user1 if i % 2 == 0 else user2
            ticket = Ticket(
                user_id=ticket_user.id,
                subject=t_data["subject"],
                description=t_data["description"],
                category=t_data["category"],
                priority=t_data["priority"],
                status=t_data["status"],
                created_at=t_data["created_at"],
                updated_at=t_data["created_at"]
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)

            # Add initial message
            msg = Message(
                ticket_id=ticket.id,
                sender=SenderType.USER,
                content=t_data["description"],
                created_at=t_data["created_at"]
            )
            db.add(msg)

            # Add admin reply for some tickets
            if t_data["status"] in [TicketStatus.IN_PROGRESS, TicketStatus.CLOSED]:
                reply = Message(
                    ticket_id=ticket.id,
                    sender=SenderType.ADMIN,
                    content="Thank you for reporting this. We're looking into it and will update you shortly.",
                    created_at=t_data["created_at"] + timedelta(hours=1)
                )
                db.add(reply)

        db.commit()
        print(f"      Created {len(sample_tickets)} sample tickets with messages.")

        # Create sample chat logs
        print("\n[4/4] Creating sample chat logs...")
        chat_samples = [
            {
                "user_input": "I forgot my password",
                "detected_intent": "password reset",
                "confidence_score": 0.94,
                "ai_response": "I can help you with your password reset! Here are the steps:\n\n1. Go to the login page and click 'Forgot Password'\n2. Enter your registered email address\n3. Check your inbox for the password reset link",
                "ticket_created": None
            },
            {
                "user_input": "My printer is not printing anything",
                "detected_intent": "hardware malfunction",
                "confidence_score": 0.82,
                "ai_response": "I'm sorry to hear about the hardware issue. I've created a support ticket for our IT team to assist you in person.",
                "ticket_created": 3
            },
            {
                "user_input": "How do I install Zoom on my computer?",
                "detected_intent": "software installation or update",
                "confidence_score": 0.89,
                "ai_response": "Here's how to install Zoom:\n\n1. Visit zoom.us/download\n2. Click 'Download' under Zoom Workplace\n3. Run the installer\n4. Sign in with your company credentials",
                "ticket_created": None
            },
        ]

        for i, chat in enumerate(chat_samples):
            chat_user = user1 if i % 2 == 0 else user2
            log = ChatLog(
                user_id=chat_user.id,
                user_input=chat["user_input"],
                detected_intent=chat["detected_intent"],
                confidence_score=chat["confidence_score"],
                ai_response=chat["ai_response"],
                ticket_created=chat["ticket_created"],
                created_at=datetime.utcnow() - timedelta(hours=6)
            )
            db.add(log)

        db.commit()
        print(f"      Created {len(chat_samples)} sample chat logs.")

        print("\n" + "=" * 50)
        print("Setup complete!")
        print("=" * 50)
        print(f"\nLogin credentials:")
        print(f"  Admin:  admin@intellidesk.com / admin123  (Avi Bhutani)")
        print(f"  User 1: andesh@intellidesk.com / user123  (Andesh Yadav)")
        print(f"  User 2: varun@intellidesk.com / user123   (Varun Kumar)")
        print(f"\nStart the server:")
        print(f"  cd intellidesk")
        print(f"  uvicorn main:app --reload --port 8000")
        print(f"\nThen open: http://localhost:8000")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Setup failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    setup_database()
