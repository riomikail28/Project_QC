"""
Supabase Client Singleton
=========================
Centralized database connection for QC Central Kitchen.
Uses environment variables from .env for credentials.
"""

import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("qc.database")

# ---------------------------------------------------------------------------
# Supabase Credentials
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY", ""))
STORAGE_BUCKET: str = "qc-photos"

# ---------------------------------------------------------------------------
# Singleton client (lazy-initialized)
# ---------------------------------------------------------------------------
_client: Client = None


def get_client() -> Client:
    """Return the initialized Supabase client.
    
    If credentials are invalid or missing, returns None to allow 
    fallback to offline/demo modes.
    """
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase credentials not set — running in offline mode")
            return None
        
        try:
            _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            # Catching invalid API keys or malformed URLs
            logger.error("Supabase initialization failed (check your API keys): %s", e)
            return None
            
    return _client