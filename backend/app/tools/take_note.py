from langchain.tools import tool
from app.core.database import supabase
from datetime import datetime

@tool
def take_note(worker_id: str, content: str) -> str:
    """Save an important fact or note to long-term memory."""
    supabase.table("memory_entries").insert({
        "worker_id": worker_id,
        "tenant_id": "placeholder",  # will be passed via agent context later
        "content": content,
    }).execute()
    return f"Note saved: {content}"