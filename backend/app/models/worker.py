from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class WorkerCreate(BaseModel):
    tenant_id: UUID
    name: str
    role: str
    persona: Optional[str] = None

class WorkerOut(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    role: str
    persona: Optional[str]
    is_active: bool