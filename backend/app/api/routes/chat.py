from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.worker_agent import run_agent
from app.core.database import supabase

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    worker_id: str
    tenant_id: str
    message: str
    conversation_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: str

@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Get or create conversation
    if req.conversation_id:
        conv_id = req.conversation_id
    else:
        conv_result = supabase.table("conversations").insert({
            "worker_id": req.worker_id,
            "tenant_id": req.tenant_id,
            "channel": "web",
        }).execute()
        conv_id = conv_result.data[0]["id"]

    # Get worker
    worker_result = supabase.table("workers") \
        .select("*").eq("id", req.worker_id).single().execute()
    worker = worker_result.data

    # Get tenant context
    tenant_result = supabase.table("tenants") \
        .select("business_context").eq("id", req.tenant_id).single().execute()
    business_context = tenant_result.data.get("business_context", "")

    # Get history
    history_result = supabase.table("messages") \
        .select("role, content") \
        .eq("conversation_id", conv_id) \
        .order("created_at") \
        .limit(20) \
        .execute()
    history = history_result.data or []

    # Run agent
    reply = await run_agent(
        user_message=req.message,
        conversation_history=history,
        worker_name=worker["name"],
        worker_role=worker["role"],
        business_context=business_context,
        tenant_id=req.tenant_id,
        worker_id=req.worker_id,
    )

    # Save messages
    supabase.table("messages").insert([
        {"conversation_id": conv_id, "role": "user", "content": req.message},
        {"conversation_id": conv_id, "role": "assistant", "content": reply},
    ]).execute()

    return {"reply": reply, "conversation_id": conv_id}