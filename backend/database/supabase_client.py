"""
Supabase Client Singleton
=========================
Manages the connection to the Supabase database.
Ensures only one client instance exists throughout the application.
"""

import os
import logging
from dataclasses import dataclass
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qc.db.supabase")
STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "qc-evidence")

# Shared singleton instance
_client: Client = None
_admin_client: Client = None
_failed: bool = False
_last_error: str = ""


INVALID_KEY_MESSAGE = "Invalid Supabase API key. Check Vercel SUPABASE_SERVICE_ROLE_KEY."
CONNECTION_FAILED_MESSAGE = "Supabase connection failed. Please check production environment variables."


@dataclass(frozen=True)
class SupabaseEnvStatus:
    success: bool
    message: str
    supabase_url_configured: bool
    service_role_key_configured: bool
    anon_key_configured: bool
    storage_bucket: str


def _supabase_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or ""
    ).strip()

def _anon_key() -> str:
    return (os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or "").strip()


def _service_key() -> str:
    return (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()


def _is_placeholder(value: str) -> bool:
    raw = str(value or "").strip().lower()
    return (
        not raw
        or raw.startswith("your-")
        or raw in {"test-key", "service-role-key", "replace-me"}
        or "your-project-ref" in raw
    )


def _is_invalid_key_error(error_text: str) -> bool:
    text = str(error_text or "").lower()
    return "invalid api key" in text or "jwt" in text and "invalid" in text


def validate_supabase_env(require_service_role: bool = True) -> SupabaseEnvStatus:
    """Validate required Supabase env without exposing secret values."""
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service_key = _service_key()
    anon_key = _anon_key()
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "qc-evidence").strip() or "qc-evidence"
    url_ok = bool(url) and not _is_placeholder(url)
    service_ok = bool(service_key) and not _is_placeholder(service_key)
    anon_ok = bool(anon_key) and not _is_placeholder(anon_key)
    if not url_ok:
        return SupabaseEnvStatus(False, "SUPABASE_URL is not configured", url_ok, service_ok, anon_ok, bucket)
    if require_service_role and not service_ok:
        return SupabaseEnvStatus(False, "Supabase service role key is not configured", url_ok, service_ok, anon_ok, bucket)
    if not require_service_role and not (service_ok or anon_ok):
        return SupabaseEnvStatus(False, "Supabase public anon key is not configured", url_ok, service_ok, anon_ok, bucket)
    return SupabaseEnvStatus(True, "OK", url_ok, service_ok, anon_ok, bucket)


def supabase_error_response(message: str | None = None) -> tuple[dict, int]:
    return {
        "success": False,
        "message": message or get_last_db_error() or CONNECTION_FAILED_MESSAGE,
    }, 503


def _client_with_key(key: str, key_name: str):
    global _last_error
    url = os.getenv("SUPABASE_URL", "").strip().strip("/")

    if not create_client or not Client:
        _last_error = "Package supabase belum terinstall"
        logger.warning(_last_error)
        return None
    if not url:
        _last_error = "SUPABASE_URL is not configured"
        logger.warning(_last_error)
        return None
    if not key:
        _last_error = f"{key_name} is not configured"
        logger.warning(_last_error)
        return None
    if _is_placeholder(key):
        _last_error = INVALID_KEY_MESSAGE if "SERVICE_ROLE" in key_name else "Invalid Supabase API key"
        logger.warning(_last_error)
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        error_msg = str(e)
        logger.warning("Supabase standard client creation failed; trying fallback: %s", error_msg)
        try:
            return Client(url, key)
        except Exception as e2:
            fallback_error = str(e2)
            _last_error = INVALID_KEY_MESSAGE if _is_invalid_key_error(f"{error_msg} {fallback_error}") else f"{error_msg} | Fallback failed: {fallback_error}"
            logger.error("Supabase creation failed: %s", _last_error)
            return None


def get_client():
    """Get or initialize the Supabase client singleton."""
    global _client, _failed, _last_error
    
    if _client is not None:
        return _client
    env = validate_supabase_env(require_service_role=False)
    if not env.success:
        _last_error = env.message
        return None
    _client = _client_with_key(_supabase_key() or _anon_key(), "SUPABASE_KEY")
    return _client


def get_supabase_client():
    """Backward-compatible alias for backend DB client."""
    return get_client()


def get_supabase_public_client():
    """Public Supabase client using anon key only."""
    global _client, _last_error
    if _client is not None:
        return _client
    env = validate_supabase_env(require_service_role=False)
    if not env.success:
        _last_error = env.message
        return None
    _client = _client_with_key(_anon_key(), "SUPABASE_ANON_KEY")
    return _client


def get_supabase_admin_client():
    """Privileged Supabase client for backend-only writes and Storage upload."""
    global _admin_client, _last_error
    if _admin_client is not None:
        return _admin_client
    env = validate_supabase_env(require_service_role=True)
    if not env.success:
        _last_error = env.message
        logger.warning(_last_error)
        return None
    key = _service_key()
    if not key:
        _last_error = "Supabase service role key is not configured"
        logger.warning(_last_error)
        return None
    _admin_client = _client_with_key(key, "SUPABASE_SERVICE_ROLE_KEY")
    return _admin_client


def validate_supabase_connection() -> dict:
    """Validate env and a lightweight Supabase REST connection."""
    env = validate_supabase_env(require_service_role=True)
    base = {
        "supabase_url_configured": env.supabase_url_configured,
        "service_role_key_configured": env.service_role_key_configured,
        "storage_bucket": env.storage_bucket,
    }
    if not env.success:
        return {"success": False, "message": env.message, **base}
    client = get_supabase_admin_client()
    if not client:
        message = get_last_db_error() or CONNECTION_FAILED_MESSAGE
        if "Invalid Supabase API key" in message:
            message = "Invalid Supabase API key"
        return {"success": False, "message": message, **base}
    try:
        client.table("facility_rooms").select("id").limit(1).execute()
        return {"success": True, "connection": "ok", **base}
    except Exception as exc:
        message = INVALID_KEY_MESSAGE if _is_invalid_key_error(str(exc)) else f"Supabase connection failed: {str(exc)}"
        return {"success": False, "message": message, **base}

def get_last_db_error():
    """Return the last encountered database error message."""
    global _last_error
    return _last_error

def reset_client():
    """Reset the singleton instance (useful for testing or reconnecting)."""
    global _client, _admin_client, _failed
    _client = None
    _admin_client = None
    _failed = False

def direct_db_query(table: str, method: str = "GET", payload: dict = None, filters: str = ""):
    """Perform a direct HTTP query to Supabase (bypass library validation)."""
    import json
    from urllib import request, error
    
    url = os.getenv("SUPABASE_URL", "").strip().strip("/")
    key = _supabase_key()
    env = validate_supabase_env(require_service_role=True)
    if not env.success:
        raise ValueError(env.message)
    
    api_url = f"{url}/rest/v1/{table}"
    if filters:
        api_url += f"?{filters}"
        
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    data = json.dumps(payload).encode() if payload else None
    req = request.Request(api_url, headers=headers, data=data, method=method)
    
    try:
        with request.urlopen(req) as response:
            res_body = response.read().decode()
            return json.loads(res_body) if res_body else []
    except error.HTTPError as e:
        err_msg = e.read().decode()
        logger.error("Direct DB Error: %s - %s", e.code, err_msg)
        raise ValueError(f"Database Error: {err_msg}")
    except Exception as e:
        logger.error("Direct DB Generic Error: %s", e)
        raise ValueError(f"Koneksi Database Gagal: {str(e)}")
