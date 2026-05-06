"""
Staff Manager
=============
Authentication and staff account management.
Handles login, registration, and staff CRUD.

Supabase table: staff_accounts
"""

import hashlib
import secrets
import logging
from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.staff")


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def password_matches(user: dict, password: str) -> bool:
    """Check if a password matches the stored hash.

    Supports both password_hash and legacy plaintext password fields.
    """
    if user.get("password_hash"):
        return secrets.compare_digest(user["password_hash"], hash_password(password))
    # Backward compatibility for older demo rows
    return secrets.compare_digest(str(user.get("password", "")), password)


def login(username: str, password: str) -> dict:
    """Authenticate a staff member.

    Returns user data with a session token on success.
    Raises ValueError on invalid credentials.
    """
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
                    "token": secrets.token_urlsafe(32),
                }
        except Exception as e:
            logger.error("Login DB error: %s", e)

    # Demo fallback credentials (untuk testing tanpa database)
    demo_users = {
        "admin": {"password": "admin123", "role": "admin", "id": "admin-uuid"},
        "staff_kitchen": {"password": "staff123", "role": "staff", "id": "staff-uuid"},
        "qc_lead": {"password": "qc123", "role": "qc_lead", "id": "qc-uuid"},
    }

    demo = demo_users.get(username)
    if demo and demo["password"] == password:
        return {
            "id": demo["id"],
            "username": username,
            "role": demo["role"],
            "token": secrets.token_urlsafe(32),
        }

    raise ValueError("Username atau Password salah")


def list_staff() -> list:
    """Fetch all staff accounts (without sensitive fields)."""
    sb = get_client()
    if not sb:
        return []

    try:
        res = sb.table("staff_accounts").select("id, username, role, created_at").execute()
        return res.data or []
    except Exception as e:
        logger.error("Error listing staff: %s", e)
        return []


def create_staff(username: str, password: str, role: str = "staff") -> dict:
    """Create a new staff account.

    Returns the created user record (without password hash).
    """
    sb = get_client()
    if not sb:
        raise ConnectionError("Database offline")

    try:
        res = sb.table("staff_accounts").insert([{
            "username": username,
            "password_hash": hash_password(password),
            "role": role,
        }]).execute()
        if res.data:
            row = res.data[0]
            row.pop("password_hash", None)
            row.pop("password", None)
            return row
    except Exception as e:
        logger.error("Error creating staff: %s", e)
        raise

    return {"error": "Failed to create staff"}


def delete_staff(staff_id: str) -> bool:
    """Delete a staff account by ID."""
    sb = get_client()
    if not sb:
        return False

    try:
        sb.table("staff_accounts").delete().eq("id", staff_id).execute()
        return True
    except Exception as e:
        logger.error("Error deleting staff: %s", e)
        return False
