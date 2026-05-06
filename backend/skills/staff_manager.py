"""
Staff Management Skill
======================
Handles authentication and staff account CRUD.
Supports both Supabase-backed accounts and demo fallback.
"""

import os
import hashlib
import secrets
import logging
from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.staff")

def hash_password(password: str) -> str:
    """Generate SHA-256 hash of password."""
    return hashlib.sha256(password.encode()).hexdigest()

def password_matches(user: dict, password: str) -> bool:
    """Check if provided password matches the stored hash."""
    stored = user.get("password_hash") or user.get("password", "")
    return secrets.compare_digest(str(stored), hash_password(password))

def login(username: str, password: str) -> dict:
    """Validate credentials and return user session data."""
    sb = get_client()
    
    if sb:
        try:
            res = sb.table("staff_accounts").select("*").eq("username", username).execute()
            if res.data and password_matches(res.data[0], password):
                user = res.data[0]
                return {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"],
                    "name": user.get("full_name", user["username"]),
                    "token": f"session-{secrets.token_hex(16)}"
                }
        except Exception as e:
            logger.error("Login DB error: %s", e)

    # Demo fallback
    demo_users = {
        "admin": {"password": "admin123", "role": "admin", "id": "admin-uuid", "name": "System Admin"},
        "staff": {"password": "staff123", "role": "staff", "id": "staff-uuid", "name": "QC Staff"},
    }

    demo = demo_users.get(username)
    if demo and demo["password"] == password:
        return {
            "id": demo["id"],
            "username": username,
            "role": demo["role"],
            "name": demo["name"],
            "token": f"demo-token-{secrets.token_hex(8)}"
        }

    raise ValueError("Username atau Password salah")

def list_staff():
    """List all staff accounts (Admin only)."""
    from backend.database.supabase_client import direct_db_query
    
    try:
        # Use direct query to bypass library validation
        res_data = direct_db_query("staff_accounts", method="GET")
        return res_data or []
    except Exception as e:
        logger.error("Failed to list staff: %s", e)
        return []

def create_staff(data: dict):
    """Create a new staff account."""
    # Check database connectivity with detailed info
    import os
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY"))
    
    from backend.database.supabase_client import get_client, get_last_db_error, direct_db_query
    
    username = data.get("username")
    password = data.get("password")
    role_input = data.get("role", "staff").lower()
    full_name = data.get("full_name", username)

    # Database constraint only allows 'admin' or 'staff'
    db_role = "admin" if "admin" in role_input else "staff"

    if not username or not password:
        raise ValueError("Username dan Password wajib diisi")

    try:
        payload = {
            "username": username,
            "password_hash": hash_password(password),
            "role": db_role,
            "is_active": True
        }
        
        # Use direct query to bypass library validation issues
        res_data = direct_db_query("staff_accounts", method="POST", payload=payload)
        return res_data[0] if res_data else None
    except Exception as e:
        logger.error("Failed to create staff: %s", e)
        err_msg = str(e)
        if "unique_violation" in err_msg or "duplicate" in err_msg:
            raise ValueError(f"Username '{username}' sudah terdaftar")
        raise ValueError(f"Gagal menambah staf: {err_msg}")

def delete_staff(staff_id: str):
    """Delete a staff account."""
    from backend.database.supabase_client import direct_db_query
    
    try:
        # PostgREST format for filters
        filters = f"id=eq.{staff_id}"
        direct_db_query("staff_accounts", method="DELETE", filters=filters)
        return True
    except Exception as e:
        logger.error("Failed to delete staff: %s", e)
        return False
