"""
Staff Management Skill
======================
Handles authentication and staff account CRUD.
Supports both Supabase-backed accounts and demo fallback.
"""

import os
from urllib.parse import quote
import secrets
import logging
from werkzeug.security import check_password_hash, generate_password_hash
from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.staff")

def hash_password(password: str) -> str:
    """Generate a modern salted password hash."""
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

def password_matches(user: dict, password: str) -> bool:
    """Check if provided password matches the stored hash."""
    stored = user.get("password_hash") or user.get("password", "")
    stored = str(stored)
    if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
        return check_password_hash(stored, password)

    # Backward compatibility for legacy/demo rows. Do not create new plain hashes.
    import hashlib
    legacy_sha256 = hashlib.sha256(password.encode()).hexdigest()
    return secrets.compare_digest(stored, legacy_sha256) or secrets.compare_digest(stored, password)

def login(username: str, password: str) -> dict:
    """Validate credentials and return user session data."""
    from backend.database.supabase_client import direct_db_query
    
    try:
        # Use direct query with filter
        filters = f"username=eq.{quote(username, safe='')}"
        res_data = direct_db_query("staff_accounts", method="GET", filters=filters)
        
        if res_data and password_matches(res_data[0], password):
            user = res_data[0]
            return {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "name": user.get("full_name", user["username"]),
            }
    except Exception as e:
        logger.error("Login DB error: %s", e)

    raise ValueError("Username atau Password salah")

def list_staff():
    """List all staff accounts (Admin only)."""
    from backend.database.supabase_client import direct_db_query
    
    try:
        # Use direct query to bypass library validation
        res_data = direct_db_query("staff_accounts", method="GET")
        staff = res_data or []
        for item in staff:
            item.pop("password_hash", None)
            item.pop("password", None)
        return staff
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
            "full_name": full_name,
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

def update_staff(staff_id: str, data: dict):
    """Update an existing staff account."""
    from backend.database.supabase_client import direct_db_query

    payload = {}
    if data.get("username"):
        payload["username"] = data["username"]
    if data.get("full_name"):
        payload["full_name"] = data["full_name"]
    if data.get("role"):
        role_input = data["role"].lower()
        payload["role"] = "admin" if "admin" in role_input else "staff"
    if data.get("password"):
        payload["password_hash"] = hash_password(data["password"])

    if not payload:
        raise ValueError("Tidak ada data yang diubah")

    try:
        res_data = direct_db_query(
            "staff_accounts",
            method="PATCH",
            payload=payload,
            filters=f"id=eq.{staff_id}",
        )
        return res_data[0] if res_data else {"id": staff_id, **payload}
    except Exception as e:
        logger.error("Failed to update staff: %s", e)
        raise ValueError(f"Gagal mengubah staf: {str(e)}")


def get_staff_by_id(staff_id: str):
    """Retrieve a single staff account by id."""
    from backend.database.supabase_client import direct_db_query
    try:
        res = direct_db_query('staff_accounts', method='GET', filters=f'id=eq.{staff_id}')
        if res:
            user = res[0]
            user.pop('password_hash', None)
            user.pop('password', None)
            return user
    except Exception as e:
        logger.error("Failed to get staff by id: %s", e)
    return None
