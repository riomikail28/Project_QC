"""
Supabase Client Singleton
=========================
Manages the connection to the Supabase database.
Ensures only one client instance exists throughout the application.
"""

import os
import logging
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qc.db.supabase")

# Shared singleton instance
_client: Client = None
_failed: bool = False
_last_error: str = ""

def get_client():
    """Get or initialize the Supabase client singleton."""
    global _client, _failed, _last_error
    
    if _client is not None:
        return _client
        
    # Fetch environment variables dynamically
    url = os.getenv("SUPABASE_URL", "").strip().strip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY", "")).strip()
    
    if not url or not key:
        _last_error = "SUPABASE_URL or KEY is missing in environment"
        return None
    
    try:
        _client = create_client(url, key)
        return _client
    except Exception as e:
        _last_error = str(e)
        print(f"CRITICAL: Supabase creation failed: {_last_error}")
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