from app.core.database import supabase
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def save_memory(worker_id: str, tenant_id: str, content: str):
    embedding = get_embedding(content)
    supabase.table("memory_entries").insert({
        "worker_id": worker_id,
        "tenant_id": tenant_id,
        "content": content,
        "embedding": embedding,
    }).execute()

def search_memory(worker_id: str, query: str, limit: int = 5) -> list[str]:
    embedding = get_embedding(query)
    result = supabase.rpc("match_memories", {
        "query_embedding": embedding,
        "worker_id_filter": worker_id,
        "match_count": limit,
    }).execute()
    return [r["content"] for r in result.data]