"""
IntelliDesk NLP Service
Intent detection, Groq response generation, and AI ticket decision logic.
"""

from typing import Optional, Tuple
from config import settings

try:
    from transformers import pipeline
except Exception as e:
    print(f"[NLP] Transformers import failed: {e}")
    pipeline = None

try:
    from groq import Groq
except Exception as e:
    print(f"[GROQ] Groq import failed: {e}")
    Groq = None

INTENT_LABELS = [
    "greeting or casual conversation",
    "password reset",
    "network connectivity issue",
    "software installation or update",
    "hardware malfunction",
    "access permission request",
    "operating system support",
    "general IT inquiry",
]

INTENT_TO_CATEGORY = {
    "greeting or casual conversation": "general",
    "password reset": "password",
    "network connectivity issue": "network",
    "software installation or update": "software",
    "hardware malfunction": "hardware",
    "access permission request": "access",
    "operating system support": "software",
    "general IT inquiry": "general",
}

INTENT_PRIORITY = {
    "greeting or casual conversation": "low",
    "password reset": "medium",
    "network connectivity issue": "medium",
    "software installation or update": "medium",
    "hardware malfunction": "high",
    "access permission request": "medium",
    "operating system support": "medium",
    "general IT inquiry": "low",
}

SYSTEM_PROMPT = """
You are IntelliDesk AI Assistant.

Primary role:
- Provide professional IT helpdesk support.
- Help users with software, hardware, Windows, networking, passwords, access requests and troubleshooting.

Response Guidelines:

1. Match answer length to question complexity.

2. Simple questions:
   - Give short direct answers.
   - Example:
     User: What is the capital of Nepal?
     AI: Kathmandu is the capital city of Nepal.

3. Medium questions:
   - Give 1-3 paragraphs.

4. Technical or troubleshooting questions:
   - Give detailed explanations.
   - Use headings.
   - Use bullet points.
   - Use numbered steps.

5. If the question is NOT IT-related:
   - Briefly mention:
     "This question is not related to IT support, but here's a quick answer:"
   - Then answer normally.
   - Do NOT write long essays unless user specifically asks for details.

6. Avoid unnecessary introductions.

7. Avoid repeating information.

8. Be conversational and natural.

9. Only provide very detailed explanations when:
   - User asks "explain"
   - User asks "how"
   - User asks "guide me"
   - User asks troubleshooting questions

10. If user requests ticket creation:
    - Explain the issue briefly.
    - Let IntelliDesk system show ticket confirmation.
"""
MODEL_LOADED = False
classifier = None
if pipeline:
    try:
        classifier = pipeline(
            "zero-shot-classification",
            model=getattr(settings, "NLP_MODEL", "facebook/bart-large-mnli"),
        )
        MODEL_LOADED = True
        print(f"[NLP] Model '{getattr(settings, 'NLP_MODEL', 'facebook/bart-large-mnli')}' loaded successfully.")
    except Exception as e:
        print(f"[NLP] Model loading failed, keyword fallback will be used: {e}")

GROQ_LOADED = False
groq_client = None
if Groq:
    try:
        api_key = getattr(settings, "GROQ_API_KEY", None)
        if api_key:
            groq_client = Groq(api_key=api_key)
            GROQ_LOADED = True
            print("[GROQ] Groq client loaded successfully.")
    except Exception as e:
        print(f"[GROQ] Groq client loading failed: {e}")

KNOWLEDGE_BASE = {
    "greeting or casual conversation": {
        "response": "Hello! I am **IntelliDesk AI Assistant**. I can help with password, network, software, hardware, Windows, and access issues."
    },
    "password reset": {
        "response": "**Password reset steps:**\n\n1. Go to the company login page.\n2. Click **Forgot Password**.\n3. Enter your username or employee email.\n4. Follow the verification link or code.\n\nIf you cannot reset it yourself, ask me to **create a ticket for password reset**."
    },
    "network connectivity issue": {
        "response": "**Network troubleshooting:**\n\n1. Restart Wi-Fi or reconnect Ethernet.\n2. Restart the router if available.\n3. Forget and reconnect to the Wi-Fi network.\n4. Test another website or device.\n\nIf the issue continues, I can create a network support ticket."
    },
    "software installation or update": {
        "response": "**Software support:**\n\n1. Confirm the software name and version.\n2. Check whether you have permission to install it.\n3. Restart the application or computer.\n4. Try installing updates from the official source."
    },
    "hardware malfunction": {
        "response": "**Hardware troubleshooting:**\n\n1. Check cables, power, and connections.\n2. Restart the device.\n3. Test with another port or accessory.\n4. Record any error messages or visible damage."
    },
    "access permission request": {
        "response": "**Access request support:**\n\nPlease provide the system, folder, application, or resource you need access to, plus the reason for access."
    },
    "operating system support": {
        "response": "**Windows reset support:**\n\nBefore resetting Windows, back up important files and connect the device to power.\n\n1. Open **Settings**.\n2. Go to **System > Recovery**.\n3. Select **Reset this PC**.\n4. Choose **Keep my files** or **Remove everything**.\n\nIf this is a work device, it is safer to create a ticket so IT can assist."
    },
    "general IT inquiry": {
        "response": "I can help with common IT issues such as **password resets**, **network problems**, **software issues**, **hardware faults**, **Windows reset**, and **access requests**."
    },
}

KEYWORD_MAP = {
    "password reset": ["password", "reset password", "forgot password", "login fail", "can't log in", "cannot log in", "locked out", "sign in"],
    "operating system support": ["reset windows", "windows reset", "reset my windows", "reset my pc", "reset this pc", "factory reset", "reinstall windows", "windows reinstall", "format pc", "reset laptop", "reset computer"],
    "network connectivity issue": ["wifi", "wi-fi", "internet", "network", "connection", "disconnect", "vpn", "ethernet", "slow connection"],
    "software installation or update": ["install", "software", "update", "download", "application", "app", "program", "upgrade", "license", "slow", "sluggish", "performance", "lagging", "freezing", "hanging", "not responding", "crash", "loading"],
    "hardware malfunction": ["hardware", "screen", "monitor", "keyboard", "mouse", "printer", "laptop", "broken", "not working", "blue screen", "usb", "drive", "device", "port", "headphones", "speaker", "webcam", "charger"],
    "access permission request": ["access", "permission", "role", "admin rights", "folder access", "shared drive", "authorize", "restricted", "denied", "can't access", "cannot access"],
    "greeting or casual conversation": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
    "general IT inquiry": ["help", "question", "how to", "what is", "support", "issue", "problem"],
}


def wants_ticket(message: str) -> bool:
    text = (message or "").lower()
    ticket_words = ["create ticket", "raise ticket", "open ticket", "log ticket", "submit ticket", "make ticket", "create a ticket", "raise a ticket", "open a ticket", "log a ticket"]
    return any(word in text for word in ticket_words)


def detect_intent_huggingface(text: str) -> Tuple[str, float]:
    result = classifier(text, INTENT_LABELS, multi_label=False)
    return result["labels"][0], round(float(result["scores"][0]), 4)


def detect_intent_keyword(text: str) -> Tuple[str, float]:
    text_lower = (text or "").lower()
    best_intent, best_score = "general IT inquiry", 0.0
    for intent, keywords in KEYWORD_MAP.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            score = min(0.5 + (matches * 0.15), 0.95)
            if score > best_score:
                best_score, best_intent = score, intent
    return best_intent, round(best_score or 0.3, 4)


def detect_intent(text: str) -> Tuple[str, float]:
    text_lower = (text or "").lower()
    if "password" in text_lower and ("reset" in text_lower or "forgot" in text_lower or "locked" in text_lower):
        return "password reset", 0.99
    if ("reset windows" in text_lower or "windows reset" in text_lower or "reset my windows" in text_lower or "reset my pc" in text_lower or "reset this pc" in text_lower or "factory reset" in text_lower or "reinstall windows" in text_lower or "format pc" in text_lower or "windows reinstall" in text_lower or "reset laptop" in text_lower or "reset computer" in text_lower):
        return "operating system support", 0.99
    if ("wifi" in text_lower or "wi-fi" in text_lower or "internet" in text_lower or "network" in text_lower or "vpn" in text_lower or "ethernet" in text_lower):
        return "network connectivity issue", 0.99
    if ("access" in text_lower or "permission" in text_lower or "admin rights" in text_lower or "folder access" in text_lower or "shared drive" in text_lower):
        return "access permission request", 0.95
    if ("hardware" in text_lower or "screen" in text_lower or "keyboard" in text_lower or "mouse" in text_lower or "printer" in text_lower or "monitor" in text_lower or "charger" in text_lower):
        return "hardware malfunction", 0.95
    if ("install" in text_lower or "software" in text_lower or "application" in text_lower or "app" in text_lower or "update" in text_lower or "operating system" in text_lower):
        return "software installation or update", 0.95

    keyword_intent, keyword_score = detect_intent_keyword(text)
    if keyword_score >= 0.90:
        return keyword_intent, keyword_score
    if MODEL_LOADED and classifier:
        try:
            hf_intent, hf_score = detect_intent_huggingface(text)
            if hf_score > keyword_score and hf_score >= 0.70:
                return hf_intent, hf_score
        except Exception as e:
            print(f"[NLP] HuggingFace detection failed: {e}")
    return keyword_intent, keyword_score


def generate_groq_response(user_message: str, intent: str, history: list = None) -> Optional[str]:
    if not GROQ_LOADED or not groq_client:
        return None
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            for h in history[-6:]:
                messages.append({"role": "user", "content": h.get("user", "")})
                messages.append({"role": "assistant", "content": h.get("assistant", "")})
        messages.append({"role": "user", "content": f"IT issue category: {intent}\n\nUser message: {user_message}\n\nGive a detailed, professional IT support response. "
"Use headings, bullet points, numbered steps, and **bold** important words. "
"Explain why each main step is needed. "
"If the topic is not IT-related, politely mention that it is outside IT support but still provide a general helpful answer."})
        chat = groq_client.chat.completions.create(
            model=getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=messages,
            temperature=0.55,
            max_tokens=700,
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GROQ] API error: {e}")
        return None


def generate_off_topic_response(user_message: str) -> str:
    return "I am mainly here for IT support. Please ask me about passwords, Wi-Fi, software, hardware, Windows, or access issues."


def is_it_related(user_message: str) -> bool:
    return True


def get_image_query(user_message: str, intent: str, is_it: bool = True) -> Optional[str]:
    if not is_it:
        return None
    text = (user_message or "").lower()
    if any(word in text for word in ["cable", "router", "printer", "monitor", "screen", "keyboard"]):
        return f"{intent} IT support"
    return None


def get_ai_response(user_message: str, intent: str, confidence: float, history: list = None) -> dict:
    no_ticket_intents = ["greeting or casual conversation"]
    if intent in no_ticket_intents:
        return {
            "response": KNOWLEDGE_BASE["greeting or casual conversation"]["response"],
            "should_create_ticket": False,
            "category": "general",
            "priority": "low",
            "confident": True,
            "image_query": None,
        }
    groq_response = generate_groq_response(user_message, intent, history) if GROQ_LOADED else None
    response_text = groq_response or KNOWLEDGE_BASE.get(intent, KNOWLEDGE_BASE["general IT inquiry"])["response"]
    return {
        "response": response_text,
        "should_create_ticket": wants_ticket(user_message),
        "category": INTENT_TO_CATEGORY.get(intent, "general"),
        "priority": INTENT_PRIORITY.get(intent, "low"),
        "confident": True,
        "image_query": get_image_query(user_message, intent, is_it=True),
    }
