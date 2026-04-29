from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.database import supabase

router = APIRouter(prefix="/tenants", tags=["tenants"])

class TenantCreate(BaseModel):
    name: str
    business_context: Optional[str] = None

@router.post("/")
async def create_tenant(tenant: TenantCreate):
    result = supabase.table("tenants").insert(tenant.model_dump()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create tenant")
    return result.data[0]

@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str):
    result = supabase.table("tenants").select("*").eq("id", tenant_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result.data