from fastapi import APIRouter, Request, Form
from app.channels.whatsapp import parse_incoming_whatsapp, send_whatsapp_message
from app.agents.worker_agent import run_agent
from app.core.database import supabase

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    data = parse_incoming_whatsapp(dict(form_data))

    phone_number = data["from"]
    user_message = data["body"]

    # Find the conversation for this phone number
    conv_result = supabase.table("conversations") \
        .select("*, workers(*)") \
        .eq("external_id", phone_number) \
        .eq("channel", "whatsapp") \
        .limit(1) \
        .execute()

    if not conv_result.data:
        # No conversation found — use a default worker for demo purposes
        # In production: route to the right tenant's worker
        send_whatsapp_message(phone_number, "No worker assigned to this number yet.")
        return {"status": "no_worker"}

    conversation = conv_result.data[0]
    worker = conversation["workers"]

    # Load conversation history (last 20 messages)
    history_result = supabase.table("messages") \
        .select("role, content") \
        .eq("conversation_id", conversation["id"]) \
        .order("created_at", desc=False) \
        .limit(20) \
        .execute()

    history = history_result.data or []

    # Get tenant business context
    tenant_result = supabase.table("tenants") \
        .select("business_context") \
        .eq("id", conversation["tenant_id"]) \
        .single() \
        .execute()

    business_context = tenant_result.data.get("business_context", "") if tenant_result.data else ""

    # Run the agent
    reply = await run_agent(
        user_message=user_message,
        conversation_history=history,
        worker_name=worker["name"],
        worker_role=worker["role"],
        business_context=business_context,
        tenant_id=str(conversation["tenant_id"]),
        worker_id=str(worker["id"]),
    )

    # Save user message + assistant reply
    conv_id = conversation["id"]
    supabase.table("messages").insert([
        {"conversation_id": conv_id, "role": "user", "content": user_message},
        {"conversation_id": conv_id, "role": "assistant", "content": reply},
    ]).execute()

    # Send reply via WhatsApp
    send_whatsapp_message(phone_number, reply)

    return {"status": "ok"}