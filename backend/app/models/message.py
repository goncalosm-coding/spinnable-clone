from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class MessageIn(BaseModel):
    conversation_id: UUID
    role: str
    content: str
    metadata: Optional[dict] = None

class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime