"""
IntelliDesk Chat Routes
AI chatbot interface, chat history, IT-only ticket creation and streaming.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from uuid import uuid4
import httpx
import json

from config import get_db, settings
from models import User, ChatLog, now_sydney
from auth import get_current_user
from services.nlp_service import (
    detect_intent,
    get_ai_response,
    get_image_query,
    groq_client,
    SYSTEM_PROMPT,
    INTENT_TO_CATEGORY,
    INTENT_PRIORITY,
    wants_ticket,
)
from services.ticket_service import create_ticket

router = APIRouter()
templates = Jinja2Templates(directory="templates")


IT_KEYWORDS = [
    "password", "login", "log in", "sign in", "account locked", "mfa", "2fa",
    "wifi", "wi-fi", "internet", "network", "vpn", "ethernet", "router", "dns", "ip address",
    "software", "install", "installation", "update", "upgrade", "application", "app", "program", "license",
    "windows", "mac", "macos", "linux", "computer", "laptop", "pc", "desktop", "operating system",
    "restart", "reboot", "shutdown", "turn off", "blue screen", "bsod", "driver",
    "keyboard", "mouse", "printer", "monitor", "screen", "hardware", "charger", "usb", "webcam", "headset",
    "access", "permission", "sharepoint", "onedrive", "folder", "shared drive", "admin rights", "denied",
    "email", "outlook", "teams", "browser", "chrome", "edge", "firewall", "security", "malware", "virus",
    "error", "bug", "crash", "not working", "broken", "slow", "freeze", "technical", "device", "system issue",
]

NON_IT_KEYWORDS = [
    "restaurant", "book a table", "booking table", "dinner", "lunch", "breakfast",
    "hotel", "flight", "travel", "movie", "cinema", "shopping", "order food",
    "pizza", "taxi", "uber", "homework", "assignment", "essay", "weather",
    "capital of", "recipe", "song", "game", "holiday package",
]

DELETE_TICKET_KEYWORDS = [
    "delete ticket", "delete the ticket", "remove ticket", "remove the ticket",
    "cancel ticket", "cancel the ticket", "close and delete", "erase ticket",
    "delete my ticket",
]


def make_title(message: str) -> str:
    title = " ".join((message or "").strip().split())
    return title[:42] + "..." if len(title) > 42 else title or "New chat"


def make_ticket_subject(intent: str, issue_text: str = "") -> str:
    text = (issue_text or "").lower()

    if "windows" in text and "update" in text:
        return "Windows Update Failure Support Request"
    if "password" in text:
        return "Password Reset Assistance Request"
    if "wifi" in text or "wi-fi" in text or "network" in text or "internet" in text:
        return "Network Connectivity Support Request"
    if "printer" in text:
        return "Printer Support Request"
    if "screen" in text or "monitor" in text or "hardware" in text:
        return "Hardware Support Request"
    if "access" in text or "permission" in text:
        return "Access Permission Request"

    mapping = {
        "password reset": "Password Reset Assistance Request",
        "network connectivity issue": "Network Connectivity Support Request",
        "software installation or update": "Software Installation or Update Request",
        "hardware malfunction": "Hardware Support Request",
        "access permission request": "Access Permission Request",
        "operating system support": "Windows / Operating System Support Request",
        "general IT inquiry": "General IT Support Request",
    }
    return mapping.get((intent or "").lower(), "IT Support Request")


def should_force_ticket(message: str) -> bool:
    return wants_ticket(message)


def is_delete_ticket_request(message: str) -> bool:
    text = (message or "").lower()
    return any(word in text for word in DELETE_TICKET_KEYWORDS)


def is_it_related(intent: str, message: str) -> bool:
    """
    Allow tickets only for clear IT support issues.
    This checks the full issue context, not only the latest message.
    """
    text = (message or "").lower()

    has_non_it = any(word in text for word in NON_IT_KEYWORDS)
    has_it = any(word in text for word in IT_KEYWORDS)

    if has_non_it and not has_it:
        return False

    if has_it:
        return True

    return False


def build_ticket_context(history: list, current_message: str) -> str:
    """
    Builds context from previous user messages.
    This fixes the issue where user first explains the problem,
    then only types 'create ticket'.
    """
    previous_user_messages = []

    if history:
        for item in history[-3:]:
            if item.get("user"):
                previous_user_messages.append(item["user"])

    previous_user_messages.append(current_message)

    return " ".join(previous_user_messages).strip()


def resolve_ticket_intent(original_intent: str, ticket_context: str):
    """
    Re-detect intent using the full issue context.
    """
    try:
        context_intent, context_confidence = detect_intent(ticket_context)
        return context_intent, context_confidence
    except Exception:
        return original_intent, 0.30


def no_ticket_message() -> str:
    return (
        "⚠️ **No ticket has been created.**\n\n"
        "This request is outside the scope of IntelliDesk IT Support. "
        "IntelliDesk only creates support tickets for technical IT issues such as "
        "password, network, software, hardware, device, email, access, Windows, or system problems."
    )


def no_delete_message() -> str:
    return (
        "For audit and compliance purposes, IntelliDesk does not allow tickets to be deleted or cancelled. "
        "If a ticket was created by mistake, it can be updated or closed by an administrator, "
        "but the record is kept for tracking and reporting."
    )


def save_chat_log(
    db: Session,
    user_id: int,
    conversation_id: str,
    user_message: str,
    intent: str,
    confidence: float,
    response: str,
    ticket_id: Optional[int],
    title: Optional[str] = None,
):
    log = ChatLog(
        user_id=user_id,
        conversation_id=conversation_id,
        title=title,
        user_input=user_message,
        detected_intent=intent,
        confidence_score=confidence,
        ai_response=response,
        ticket_created=ticket_id,
        created_at=now_sydney(),
    )
    db.add(log)
    db.commit()
    return log


def get_conversation_history(
    db: Session,
    user_id: int,
    conversation_id: str,
    limit: int = 8,
):
    logs = (
        db.query(ChatLog)
        .filter(
            ChatLog.user_id == user_id,
            ChatLog.conversation_id == conversation_id,
            ChatLog.is_deleted == False,
        )
        .order_by(ChatLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {"user": log.user_input, "assistant": log.ai_response}
        for log in reversed(logs)
        if log.ai_response
    ]


def get_sidebar_threads(db: Session, user_id: int):
    all_logs = (
        db.query(ChatLog)
        .filter(ChatLog.user_id == user_id, ChatLog.is_deleted == False)
        .order_by(ChatLog.created_at.desc())
        .all()
    )

    threads = []
    seen = set()

    for log in all_logs:
        conv_id = log.conversation_id or f"legacy-{log.id}"

        if conv_id in seen:
            continue

        seen.add(conv_id)

        threads.append(
            {
                "conversation_id": conv_id,
                "title": log.title or make_title(log.user_input),
                "detected_intent": log.detected_intent or "general IT inquiry",
                "created_at": log.created_at,
            }
        )

    return threads


async def fetch_unsplash_image(query: str) -> Optional[str]:
    if not query:
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": query,
                    "per_page": 1,
                    "orientation": "landscape",
                },
                headers={
                    "Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"
                },
                timeout=5.0,
            )

            data = resp.json()
            results = data.get("results", [])

            if results:
                return results[0]["urls"]["small"]

    except Exception as e:
        print(f"[Unsplash] Error: {e}")

    return None


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    conversation_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sidebar_threads = get_sidebar_threads(db, user.id)
    active_conversation_id = conversation_id

    if active_conversation_id == "new":
        active_conversation_id = None
        chat_history = []

    elif active_conversation_id:
        chat_history = (
            db.query(ChatLog)
            .filter(
                ChatLog.user_id == user.id,
                ChatLog.conversation_id == active_conversation_id,
                ChatLog.is_deleted == False,
            )
            .order_by(ChatLog.created_at.asc())
            .all()
        )

    elif sidebar_threads:
        active_conversation_id = sidebar_threads[0]["conversation_id"]
        chat_history = (
            db.query(ChatLog)
            .filter(
                ChatLog.user_id == user.id,
                ChatLog.conversation_id == active_conversation_id,
                ChatLog.is_deleted == False,
            )
            .order_by(ChatLog.created_at.asc())
            .all()
        )

    else:
        chat_history = []

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "user": user,
            "chat_history": chat_history,
            "sidebar_threads": sidebar_threads,
            "active_conversation_id": active_conversation_id,
        },
    )


@router.post("/api/chat")
async def process_chat(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = await request.json()
    user_message = body.get("message", "").strip()
    conversation_id = body.get("conversation_id") or str(uuid4())

    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    intent, confidence = detect_intent(user_message)
    history = get_conversation_history(db, user.id, conversation_id)
    first_log = not history

    if is_delete_ticket_request(user_message):
        response = no_delete_message()
        save_chat_log(
            db,
            user.id,
            conversation_id,
            user_message,
            "ticket management policy",
            confidence,
            response,
            None,
            make_title(user_message) if first_log else None,
        )

        return JSONResponse(
            {
                "response": response,
                "intent": "ticket management policy",
                "confidence": round(confidence * 100, 1),
                "ticket_id": None,
                "ticket_display_id": None,
                "conversation_id": conversation_id,
                "confident": True,
                "image_url": None,
            }
        )

    result = get_ai_response(user_message, intent, confidence, history)

    image_url = None
    if result.get("image_query"):
        image_url = await fetch_unsplash_image(result["image_query"])

    ticket_id = None
    ticket_display_id = None

    if result.get("should_create_ticket") or should_force_ticket(user_message):
        ticket_context = build_ticket_context(history, user_message)
        ticket_intent, ticket_confidence = resolve_ticket_intent(intent, ticket_context)

        if not is_it_related(ticket_intent, ticket_context):
            result["response"] += "\n\n" + no_ticket_message()

        else:
            ticket = create_ticket(
                db=db,
                user_id=user.id,
                subject=make_ticket_subject(ticket_intent, ticket_context),
                description=(
                    "Issue reported via IntelliDesk AI Assistant.\n\n"
                    f"User Request:\n{ticket_context}\n\n"
                    f"Detected Category: {ticket_intent.title()}\n"
                    f"Confidence Score: {round(ticket_confidence * 100, 1)}%\n"
                    f"Conversation Reference: {conversation_id}"
                ),
                category=INTENT_TO_CATEGORY.get(ticket_intent, "general"),
                priority=INTENT_PRIORITY.get(ticket_intent, "medium"),
            )

            ticket_id = ticket.id
            ticket_display_id = ticket.display_id

            result["response"] += (
                f"\n\n✅ **Ticket {ticket_display_id} has been created successfully.**\n\n"
                f"**Subject:** {make_ticket_subject(ticket_intent, ticket_context)}\n\n"
                "**Status:** Open\n\n"
                "**Next Step:** The IT support team will review this request."
            )

            intent = ticket_intent
            confidence = ticket_confidence

    save_chat_log(
        db,
        user.id,
        conversation_id,
        user_message,
        intent,
        confidence,
        result["response"],
        ticket_id,
        make_title(user_message) if first_log else None,
    )

    return JSONResponse(
        {
            "response": result["response"],
            "intent": intent,
            "confidence": round(confidence * 100, 1),
            "ticket_id": ticket_id,
            "ticket_display_id": ticket_display_id,
            "conversation_id": conversation_id,
            "confident": result.get("confident", True),
            "image_url": image_url,
        }
    )


@router.post("/api/chat/stream")
async def stream_chat(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = await request.json()
    user_message = body.get("message", "").strip()
    conversation_id = body.get("conversation_id") or str(uuid4())

    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    intent, confidence = detect_intent(user_message)
    history = get_conversation_history(db, user.id, conversation_id)

    ticket_context = build_ticket_context(history, user_message)
    ticket_intent, ticket_confidence = resolve_ticket_intent(intent, ticket_context)

    user_prompt = (
        f"Detected category: {ticket_intent}\n\n"
        f"User message: \"{user_message}\"\n\n"
        f"Conversation issue context: \"{ticket_context}\"\n\n"
        "Answer naturally and intelligently. "
        "If the question is simple, give a short direct answer. "
        "If the question is technical or asks 'how', 'explain', or 'guide me', give a detailed step-by-step answer. "
        "For IT support topics, use headings, bullet points, warnings, and numbered steps where useful. "
        "If the topic is not related to IT support, briefly say: "
        "'This is not directly related to IT support, but here is a quick answer:' "
        "Then answer briefly unless the user asks for more detail. "
        "If the user asks to create a ticket, explain the issue briefly only. "
        "Do not say the ticket is created until the system confirmation appears. "
        "Do not claim a ticket was cancelled, deleted, or removed. IntelliDesk keeps tickets for audit purposes."
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for h in history[-8:]:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["assistant"]})

    messages.append({"role": "user", "content": user_prompt})

    async def event_stream():
        full_response = []
        ticket_id = None
        ticket_display_id = None
        image_url = None
        complete_response = ""

        try:
            meta_payload = {
                "type": "meta",
                "intent": ticket_intent,
                "confidence": round(ticket_confidence * 100, 1),
                "ticket_id": None,
                "conversation_id": conversation_id,
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"

            first_message = len(history) == 0

            if is_delete_ticket_request(user_message):
                complete_response = no_delete_message()

                payload = {
                    "type": "chunk",
                    "content": complete_response,
                }
                yield f"data: {json.dumps(payload)}\n\n"

                save_chat_log(
                    db,
                    user.id,
                    conversation_id,
                    user_message,
                    "ticket management policy",
                    confidence,
                    complete_response,
                    None,
                    make_title(user_message) if first_message else None,
                )

                done_payload = {
                    "type": "done",
                    "ticket_id": None,
                    "ticket_display_id": None,
                    "conversation_id": conversation_id,
                    "image_url": None,
                }
                yield f"data: {json.dumps(done_payload)}\n\n"
                return

            if groq_client:
                stream = groq_client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    temperature=0.6,
                    max_tokens=1200,
                    stream=True,
                )

                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_response.append(delta)
                        chunk_payload = {
                            "type": "chunk",
                            "content": delta,
                        }
                        yield f"data: {json.dumps(chunk_payload)}\n\n"

                complete_response = "".join(full_response).strip()

            else:
                result = get_ai_response(user_message, ticket_intent, ticket_confidence, history)
                complete_response = result["response"]
                text_payload = {
                    "type": "text",
                    "content": complete_response,
                }
                yield f"data: {json.dumps(text_payload)}\n\n"

            if should_force_ticket(user_message):
                if not is_it_related(ticket_intent, ticket_context):
                    ticket_message = "\n\n" + no_ticket_message()

                else:
                    ticket = create_ticket(
                        db=db,
                        user_id=user.id,
                        subject=make_ticket_subject(ticket_intent, ticket_context),
                        description=(
                            "Issue reported via IntelliDesk AI Assistant.\n\n"
                            f"User Request:\n{ticket_context}\n\n"
                            f"Detected Category: {ticket_intent.title()}\n"
                            f"Confidence Score: {round(ticket_confidence * 100, 1)}%\n"
                            f"Conversation Reference: {conversation_id}"
                        ),
                        category=INTENT_TO_CATEGORY.get(ticket_intent, "general"),
                        priority=INTENT_PRIORITY.get(ticket_intent, "medium"),
                    )

                    ticket_id = ticket.id
                    ticket_display_id = ticket.display_id

                    ticket_message = (
                        f"\n\n✅ **Ticket {ticket_display_id} has been created successfully.**\n\n"
                        f"**Subject:** {make_ticket_subject(ticket_intent, ticket_context)}\n\n"
                        "**Status:** Open\n\n"
                        "**Next Step:** The IT support team will review this request and provide an update."
                    )

                complete_response += ticket_message

                ticket_payload = {
                    "type": "chunk",
                    "content": ticket_message,
                }
                yield f"data: {json.dumps(ticket_payload)}\n\n"

            save_chat_log(
                db,
                user.id,
                conversation_id,
                user_message,
                ticket_intent,
                ticket_confidence,
                complete_response,
                ticket_id,
                make_title(user_message) if first_message else None,
            )

            img_query_result = get_image_query(
                user_message,
                ticket_intent,
                is_it=is_it_related(ticket_intent, ticket_context),
            )

            if img_query_result:
                image_url = await fetch_unsplash_image(img_query_result)

            done_payload = {
                "type": "done",
                "ticket_id": ticket_id,
                "ticket_display_id": ticket_display_id,
                "conversation_id": conversation_id,
                "image_url": image_url,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            print(f"[STREAM] Error: {e}")
            error_payload = {
                "type": "error",
                "message": str(e),
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.put("/api/chat/{conversation_id}")
async def rename_chat(
    conversation_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = await request.json()
    title = (body.get("title") or "").strip()

    if not title:
        return JSONResponse({"error": "Title is required"}, status_code=400)

    logs = (
        db.query(ChatLog)
        .filter(
            ChatLog.user_id == user.id,
            ChatLog.conversation_id == conversation_id,
            ChatLog.is_deleted == False,
        )
        .all()
    )

    if not logs:
        raise HTTPException(status_code=404, detail="Chat not found")

    for log in logs:
        log.title = title[:255]

    db.commit()

    return JSONResponse({"success": True, "title": title[:255]})


@router.delete("/api/chat/{conversation_id}")
async def delete_chat(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    This only hides AI chat history.
    It does not delete support tickets.
    """
    logs = (
        db.query(ChatLog)
        .filter(
            ChatLog.user_id == user.id,
            ChatLog.conversation_id == conversation_id,
            ChatLog.is_deleted == False,
        )
        .all()
    )

    if not logs:
        raise HTTPException(status_code=404, detail="Chat not found")

    for log in logs:
        log.is_deleted = True

    db.commit()

    return JSONResponse({"success": True})