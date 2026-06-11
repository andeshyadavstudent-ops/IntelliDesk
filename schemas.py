"""
IntelliDesk Pydantic Schemas
Request and response validation models
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth Schemas ----------

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=150)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenData(BaseModel):
    user_id: int
    email: str
    role: str


# ---------- Ticket Schemas ----------

class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    category: str = "general"
    priority: str = "medium"

class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None

class TicketResponse(BaseModel):
    id: int
    user_id: int
    subject: str
    description: str
    category: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Message Schemas ----------

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)

class MessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Chat Schemas ----------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    user_input: str
    detected_intent: Optional[str]
    confidence: Optional[float]
    ai_response: str
    ticket_created: Optional[int] = None


# ---------- Analytics Schemas ----------

class AnalyticsResponse(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    closed_tickets: int
    ai_resolved: int
    escalated: int
    avg_resolution_hours: float
    tickets_by_category: dict
    tickets_by_priority: dict
    recent_tickets: List[TicketResponse]
