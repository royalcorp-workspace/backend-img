from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class MessageCreate(BaseModel):
    text: str


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: str
    sender_type: str
    text: str
    is_read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: UUID
    customer_id: Optional[UUID] = None
    subject: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
