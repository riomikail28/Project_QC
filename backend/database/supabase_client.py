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

def get_client():
    """Get or initialize the Supabase client singleton."""
    global _client, _failed
    
    if _failed:
        return None
        
    if _client is None:
        # Fetch environment variables dynamically (ensures Vercel updates are picked up)
        url = os.getenv("SUPABASE_URL", "").strip().strip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY", "")).strip()
        
        # Safe Diagnostics (Does not leak the key itself)
        key_src = "SUPABASE_SERVICE_ROLE_KEY" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "SUPABASE_KEY"
        print(f"INFO: Supabase URL found: {bool(url)}, Key found: {key_src} (len: {len(key)})")

        if not url or not key:
            print("CRITICAL: Supabase credentials missing in get_client!")
            # We don't set _failed = True here to allow retry if env vars are populated later
            return None
        
        try:
            _client = create_client(url, key)
            print("✅ Supabase client created successfully.")
        except Exception as e:
            print(f"CRITICAL: Supabase creation failed: {str(e)}")
            _failed = True
            return None
            
    return _client

def reset_client():
    """Reset the singleton instance (useful for testing or reconnecting)."""
    global _client, _failed
    _client = None
    _failed = False