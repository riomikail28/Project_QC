"""
Staff Management Skill
======================
Handles authentication and staff account CRUD.
Supports both Supabase-backed accounts and demo fallback.
"""

import logging
import os
from urllib.parse import quote as _uri_encode

from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger("qc.staff")


def hash_password(password: str) -> str:
    """Generate a modern salted password hash."""
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def password_matches(user: dict, password: str) -> bool:
    """Check if provided password matches the stored hash.

    Only modern salted hashes (pbkdf2, scrypt) are accepted.
    Legacy plaintext or raw SHA-256 comparisons have been removed.
    The raw ``password`` column is intentionally ignored — only
    ``password_hash`` is checked.
    """
    stored = str(user.get("password_hash") or "")
    if not stored:
        logger.warning("Rejected login attempt: account has no password_hash")
        return False
    if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
        return check_password_hash(stored, password)
    # No fallback - reject accounts with unhashed passwords.
    logger.warning("Rejected login attempt: account has unsupported password format")
    return False


def login(username: str, password: str) -> dict:
    from backend.database.supabase_client import direct_db_query

    try:
        # Use direct query with filter — URL-encode user input to prevent
        # PostgREST filter injection via characters like '&', '=', or '.'.
        safe_username = _uri_encode(str(username), safe="")
        filters = f"username=eq.{safe_username}"
        res_data = direct_db_query(
            "staff_accounts",
            method="GET",
            filters=f"{filters}&select=id,username,role,password_hash",
        )

        if res_data and password_matches(res_data[0], password):
            user = res_data[0]
            profile = _user_profile_for_staff(user["id"])
            return {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "name": profile.get("full_name") or user.get("full_name") or user["username"],
            }
    except Exception as e:
        logger.error("Login DB error: %s", e)

    raise ValueError("Username atau Password salah")


def list_staff():
    """List all staff accounts (Admin only)."""
    from backend.database.supabase_client import direct_db_query

    try:
        # Use direct query to bypass library validation
        res_data = direct_db_query("staff_accounts", method="GET", filters="select=id,username,role")
        staff = res_data or []
        profiles = _profiles_by_staff_id([item.get("id") for item in staff])
        for item in staff:
            profile = profiles.get(item.get("id"), {})
            item["full_name"] = profile.get("full_name") or item.get("full_name") or item.get("username")
            item["name"] = item["full_name"]
            item.pop("password_hash", None)
            item.pop("password", None)
        return staff
    except Exception as e:
        logger.error("Failed to list staff: %s", e)
        return []


def create_staff(data: dict):
    """Create a new staff account."""
    # Check database connectivity with detailed info

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY"))

    from backend.database.supabase_client import direct_db_query

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
        }

        # Use direct query to bypass library validation issues
        res_data = direct_db_query("staff_accounts", method="POST", payload=payload)
        staff = res_data[0] if res_data else None
        if staff and full_name:
            _upsert_user_profile(staff.get("id"), full_name, db_role)
            staff["full_name"] = full_name
            staff["name"] = full_name
        _sanitize_staff(staff)
        return staff
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
        # PostgREST format for filters — URL-encode to prevent injection.
        filters = f"id=eq.{_uri_encode(str(staff_id), safe='')}"
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
        full_name = data["full_name"]
    else:
        full_name = None
    if data.get("role"):
        role_input = data["role"].lower()
        payload["role"] = "admin" if "admin" in role_input else "staff"
    if data.get("password"):
        payload["password_hash"] = hash_password(data["password"])

    if not payload and not full_name:
        raise ValueError("Tidak ada data yang diubah")

    try:
        if payload:
            res_data = direct_db_query(
                "staff_accounts",
                method="PATCH",
                payload=payload,
                filters=f"id=eq.{_uri_encode(str(staff_id), safe='')}",
            )
            staff = res_data[0] if res_data else {"id": staff_id, **payload}
        else:
            staff = get_staff_by_id(staff_id) or {"id": staff_id}
        if full_name:
            _upsert_user_profile(staff_id, full_name, staff.get("role") or payload.get("role") or "staff")
            staff["full_name"] = full_name
            staff["name"] = full_name
        _sanitize_staff(staff)
        return staff
    except Exception as e:
        logger.error("Failed to update staff: %s", e)
        raise ValueError(f"Gagal mengubah staf: {str(e)}")


def get_staff_by_id(staff_id: str):
    """Retrieve a single staff account by id."""
    from backend.database.supabase_client import direct_db_query

    try:
        res = direct_db_query(
            "staff_accounts",
            method="GET",
            filters=f"id=eq.{_uri_encode(str(staff_id), safe='')}&select=id,username,role",
        )
        if res:
            user = res[0]
            profile = _user_profile_for_staff(staff_id)
            user["full_name"] = profile.get("full_name") or user.get("username")
            user["name"] = user["full_name"]
            user.pop("password_hash", None)
            user.pop("password", None)
            return user
    except Exception as e:
        logger.error("Failed to get staff by id: %s", e)
    return None


def _user_profile_for_staff(staff_id: str) -> dict:
    if not staff_id:
        return {}
    try:
        from backend.database.supabase_client import direct_db_query

        rows = direct_db_query(
            "users",
            method="GET",
            filters=f"staff_account_id=eq.{_uri_encode(str(staff_id), safe='')}&select=id,staff_account_id,full_name,role&limit=1",
        )
        return rows[0] if rows else {}
    except Exception as exc:
        logger.info("Staff profile lookup skipped: %s", exc)
        return {}


def _profiles_by_staff_id(staff_ids: list[str]) -> dict:
    ids = []
    seen = set()
    for staff_id in staff_ids or []:
        if not staff_id:
            continue
        key = str(staff_id)
        if key not in seen:
            seen.add(key)
            ids.append(key)
    if not ids:
        return {}
    try:
        from backend.database.supabase_client import direct_db_query

        safe_ids = ",".join(_uri_encode(str(i), safe="") for i in ids)
        rows = direct_db_query(
            "users",
            method="GET",
            filters=f"staff_account_id=in.({safe_ids})&select=id,staff_account_id,full_name,role",
        )
        return {str(row.get("staff_account_id")): row for row in rows or [] if row.get("staff_account_id")}
    except Exception as exc:
        logger.info("Batch staff profile lookup skipped: %s", exc)
        return {}


def _upsert_user_profile(staff_id: str, full_name: str, role: str) -> None:
    if not staff_id or not full_name:
        return
    try:
        from backend.database.supabase_client import direct_db_query

        existing = direct_db_query(
            "users",
            method="GET",
            filters=f"staff_account_id=eq.{_uri_encode(str(staff_id), safe='')}&select=id,staff_account_id&limit=1",
        )
        payload = {
            "staff_account_id": staff_id,
            "full_name": full_name,
            "role": "admin" if role == "admin" else "qc_staff",
        }
        if existing:
            direct_db_query(
                "users",
                method="PATCH",
                payload=payload,
                filters=f"id=eq.{_uri_encode(str(existing[0]['id']), safe='')}",
            )
        else:
            direct_db_query("users", method="POST", payload=payload)
    except Exception as exc:
        logger.info("Staff profile sync skipped: %s", exc)


def _sanitize_staff(staff: dict | None) -> None:
    if not staff:
        return
    staff.pop("password_hash", None)
    staff.pop("password", None)
