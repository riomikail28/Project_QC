"""
Supabase Client Singleton
=========================
Manages the connection to the Supabase database.
Ensures only one client instance exists throughout the application.
"""

import os
import logging
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qc.db.supabase")
STORAGE_BUCKET = "qc-evidence"

# Shared singleton instance
_client: Client = None
_failed: bool = False
_last_error: str = ""


def _supabase_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or ""
    ).strip()

def get_client():
    """Get or initialize the Supabase client singleton."""
    global _client, _failed, _last_error
    
    if _client is not None:
        return _client
        
    # Fetch environment variables dynamically
    url = os.getenv("SUPABASE_URL", "").strip().strip("/")
    key = _supabase_key()

    if not create_client or not Client:
        _last_error = "Package supabase belum terinstall"
        logger.warning(_last_error)
        return None

    if not url or not key:
        _last_error = "SUPABASE_URL dan Supabase key belum dikonfigurasi"
        logger.warning(_last_error)
        return None
    
    try:
        # Standard initialization
        _client = create_client(url, key)
        return _client
    except Exception as e:
        # Fallback for new-format keys (sb_secret_...) which might trip up JWT validation in some SDK versions
        error_msg = str(e)
        logger.warning("Supabase standard client creation failed; trying fallback: %s", error_msg)
        
        try:
            # Manually construct client components if create_client is too picky
            _client = Client(url, key)
            return _client
        except Exception as e2:
            _last_error = f"{error_msg} | Fallback failed: {str(e2)}"
            logger.error("Supabase creation failed: %s", _last_error)
            return None

def get_last_db_error():
    """Return the last encountered database error message."""
    global _last_error
    return _last_error

def reset_client():
    """Reset the singleton instance (useful for testing or reconnecting)."""
    global _client, _failed
    _client = None
    _failed = False

def direct_db_query(table: str, method: str = "GET", payload: dict = None, filters: str = ""):
    """Perform a direct HTTP query to Supabase (bypass library validation)."""
    import json
    from urllib import request, error
    
    url = os.getenv("SUPABASE_URL", "").strip().strip("/")
    key = _supabase_key()
    if not url or not key:
        raise ValueError("SUPABASE_URL dan Supabase key belum dikonfigurasi")
    
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
