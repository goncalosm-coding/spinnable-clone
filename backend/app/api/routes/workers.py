from fastapi import APIRouter, HTTPException
from app.models.worker import WorkerCreate, WorkerOut
from app.core.database import supabase

router = APIRouter(prefix="/workers", tags=["workers"])

@router.post("/", response_model=WorkerOut)
async def create_worker(worker: WorkerCreate):
    result = supabase.table("workers").insert(worker.model_dump(mode="json")).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create worker")
    return result.data[0]

@router.get("/{worker_id}", response_model=WorkerOut)
async def get_worker(worker_id: str):
    result = supabase.table("workers").select("*").eq("id", worker_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Worker not found")
    return result.data

@router.get("/tenant/{tenant_id}", response_model=list[WorkerOut])
async def list_workers(tenant_id: str):
    result = supabase.table("workers").select("*").eq("tenant_id", tenant_id).execute()
    return result.data