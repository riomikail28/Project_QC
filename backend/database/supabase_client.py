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
    
    try:
        # Standard initialization
        _client = create_client(url, key)
        return _client
    except Exception as e:
        # Fallback for new-format keys (sb_secret_...) which might trip up JWT validation in some SDK versions
        error_msg = str(e)
        print(f"DEBUG: Standard creation failed: {error_msg}. Trying fallback...")
        
        try:
            from postgrest import SyncPostgrestClient
            from gotrue import SyncGoTrueClient
            from storage3 import SyncStorageClient
            
            # Manually construct client components if create_client is too picky
            _client = Client(url, key)
            return _client
        except Exception as e2:
            _last_error = f"{error_msg} | Fallback failed: {str(e2)}"
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