from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.database import supabase

router = APIRouter(prefix="/conversations", tags=["conversations"])

class ConversationCreate(BaseModel):
    worker_id: str
    tenant_id: str
    channel: str
    external_id: Optional[str] = None

@router.post("/")
async def create_conversation(conv: ConversationCreate):
    result = supabase.table("conversations").insert(conv.model_dump()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    return result.data[0]

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    result = supabase.table("conversations").select("*").eq("id", conversation_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Not found")
    return result.data
