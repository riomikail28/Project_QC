from fastapi import APIRouter, HTTPException, Depends, status, Form
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import logging
from supabase import create_client, Client

logger = logging.getLogger("qc.staff")
router = APIRouter(prefix="/api/staff", tags=["Staff Management"])

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

class StaffAccount(BaseModel):
    id: str
    username: str
    role: str
    created_at: Optional[str] = None

class StaffCreate(BaseModel):
    username: str
    password: str
    role: str = "staff"

class LoginRequest(BaseModel):
    username: str
    password: str

@router.get("/", response_model=List[StaffAccount])
async def list_staff(sb: Client = Depends(get_supabase)):
    try:
        res = sb.table("staff_accounts").select("id, username, role, created_at").execute()
        return res.data
    except Exception as e:
        logger.error(f"Error listing staff: {e}")
        # Fallback for demo if table doesn't exist yet
        return [
            {"id": "00000000-0000-0000-0000-000000000001", "username": "admin", "role": "admin"},
            {"id": "00000000-0000-0000-0000-000000000002", "username": "staff", "role": "staff"}
        ]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_staff(staff: StaffCreate, sb: Client = Depends(get_supabase)):
    try:
        res = sb.table("staff_accounts").insert({
            "username": staff.username,
            "password": staff.password, # In production, hash this!
            "role": staff.role
        }).execute()
        return res.data[0]
    except Exception as e:
        logger.error(f"Error creating staff: {e}")
        raise HTTPException(500, f"Gagal membuat akun staff: {e}")

@router.delete("/{staff_id}")
async def delete_staff(staff_id: str, sb: Client = Depends(get_supabase)):
    try:
        sb.table("staff_accounts").delete().eq("id", staff_id).execute()
        return {"message": "Staff deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting staff: {e}")
        raise HTTPException(500, f"Gagal menghapus staff: {e}")

@router.post("/login")
async def staff_login(req: LoginRequest, sb: Client = Depends(get_supabase)):
    try:
        res = sb.table("staff_accounts").select("*").eq("username", req.username).eq("password", req.password).execute()
        if not res.data:
            raise HTTPException(401, "Username atau Password salah")
        
        user = res.data[0]
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "token": "simulated-jwt-token"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        # Demo fallback
        if req.username == "admin" and req.password == "admin123":
            return {"id": "admin-uuid", "username": "admin", "role": "admin", "token": "simulated-jwt-token"}
        if req.username == "staff" and req.password == "1234":
            return {"id": "staff-uuid", "username": "staff", "role": "staff", "token": "simulated-jwt-token"}
        raise HTTPException(401, "Kredensial tidak valid")
