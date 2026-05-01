from fastapi import APIRouter, Request
from app.channels.whatsapp import parse_incoming_whatsapp, send_whatsapp_message
from app.agents.worker_agent import run_agent
from app.core.database import supabase
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    data = dict(form_data)
    
    logger.info(f"Incoming WhatsApp webhook: {data}")

    parsed = parse_incoming_whatsapp(data)
    phone_number = parsed["from"]
    user_message = parsed["body"]

    logger.info(f"From: {phone_number}, Message: {user_message}")

    # Find conversation
    conv_result = supabase.table("conversations") \
        .select("*, workers(*)") \
        .eq("external_id", phone_number) \
        .eq("channel", "whatsapp") \
        .limit(1) \
        .execute()

    logger.info(f"Conversation lookup result: {conv_result.data}")

    if not conv_result.data:
        logger.warning(f"No worker assigned for {phone_number}")
        send_whatsapp_message(phone_number, "No worker assigned to this number yet.")
        return {"status": "no_worker"}

    conversation = conv_result.data[0]
    worker = conversation["workers"]

    logger.info(f"Found worker: {worker['name']}")

    # Load history
    history_result = supabase.table("messages") \
        .select("role, content") \
        .eq("conversation_id", conversation["id"]) \
        .order("created_at", desc=False) \
        .limit(20) \
        .execute()
    history = history_result.data or []

    # Get tenant context
    tenant_result = supabase.table("tenants") \
        .select("business_context") \
        .eq("id", conversation["tenant_id"]) \
        .single() \
        .execute()
    business_context = tenant_result.data.get("business_context", "") if tenant_result.data else ""

    # Run agent
    logger.info("Running agent...")
    reply = await run_agent(
        user_message=user_message,
        conversation_history=history,
        worker_name=worker["name"],
        worker_role=worker["role"],
        business_context=business_context,
        tenant_id=str(conversation["tenant_id"]),
        worker_id=str(worker["id"]),
        user_id=phone_number,
    )

    logger.info(f"Agent reply: {reply}")

    # Save messages
    conv_id = conversation["id"]
    supabase.table("messages").insert([
        {"conversation_id": conv_id, "role": "user", "content": user_message},
        {"conversation_id": conv_id, "role": "assistant", "content": reply},
    ]).execute()

    # Send reply
    send_whatsapp_message(phone_number, reply)
    logger.info(f"Reply sent to {phone_number}")

    return {"status": "ok"}
