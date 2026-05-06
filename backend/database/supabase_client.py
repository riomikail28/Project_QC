"""
Supabase Client Singleton
=========================
Centralized database connection for QC Central Kitchen.
Uses environment variables from .env for credentials.

Tables used (unchanged schema):
  - facility_logs
  - facility_alerts
  - production_batches
  - production_batch_logs
  - corrective_actions
  - products
  - staff_accounts
  - facility_rooms
  - facility_devices
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
# Singleton client (lazy-initialized for test resilience)
# ---------------------------------------------------------------------------
_client: Client = None


def get_client() -> Client:
    """Return the initialized Supabase client.

    Lazily creates the client on first call so tests can patch env vars
    before the module is imported.
    """
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase credentials not set — running in offline mode")
            return None
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# Convenience alias
supabase = property(lambda self: get_client())