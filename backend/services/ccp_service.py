"""
CCP Service
===========
Business logic for Critical Control Point (CCP) inspections.
Handles photo uploads, OCR processing, and CCP log persistence.
"""

import os
import logging
import uuid
from datetime import datetime
from backend.database.supabase_client import get_client
from backend.services.storage_service import upload_photo as upload_general_photo
from backend.services.qc_engine import determine_overall_status

logger = logging.getLogger("qc.ccp")

"""
CCP Service
===========
Business logic for Critical Control Point (CCP) inspections.
Handles photo uploads, OCR processing, and CCP log persistence.
"""

import os
import logging
import uuid
from datetime import datetime
from backend.database.supabase_client import get_client
from backend.services.storage_service import upload_photo as upload_general_photo
from backend.services.qc_engine import determine_overall_status

logger = logging.getLogger("qc.ccp")

# ---------------------------------------------------------------------------
# OCR and Storage Config
# ---------------------------------------------------------------------------
STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "qc-evidence")
    stack is Vercel + Supabase. The image is still uploaded and attached to the
    QC record; operators can enter measured values manually.
    """
    return {"raw_text": "", "status": "manual_review_required"}


def submit_ccp_log(
    batch_id: str,
    stage: str,
    operator_id: str = None,
    photo_url: str = None,
    metrics: dict = None
) -> dict:
    """Persist a CCP inspection log to Supabase.

    Args:
        batch_id: UUID of the batch
        stage: CCP stage name (e.g., 'Incoming', 'Cooking')
        operator_id: UUID of the staff performing check
        photo_url: URL of the supporting photo
        metrics: Dict of readings (temp, ph, brix, tds, etc.)

    Returns:
        The created log record.
    """
    sb = get_client()
    if not sb:
        return {"error": "Database offline"}

    metrics = metrics or {}
    
    # Determine stage status from metrics
    statuses = [v.get("status", "PASS") for v in metrics.values() if isinstance(v, dict) and "status" in v]
    overall_status = determine_overall_status(*statuses)

    payload = {
        "batch_id": batch_id,
        "stage": stage,
        "operator_id": operator_id,
        "photo_url": photo_url,
        "stage_qc_status": overall_status.lower(),
        "metrics": metrics,
        "recorded_at": datetime.utcnow().isoformat(),
    }

    # Flatten metrics into the flat schema used by Supabase
    # This maps the modular metrics dict back to the fixed table columns
    mapping = {
        "temperature": "raw_temp_c",
        "core_temp": "core_temp_c",
        "ph": "ph_value_extracted",
        "brix": "brix_value_extracted",
        "tds": "tds_value",
        "room_temp": "room_temp_c"
    }

    for key, col in mapping.items():
        if key in metrics:
            val = metrics[key]
            if isinstance(val, dict):
                payload[col] = val.get("value")
                payload[f"{col}_status"] = val.get("status", "pass").lower()
            else:
                payload[col] = val

    try:
        res = sb.table("production_batch_logs").insert(payload).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        logger.error("Failed to submit CCP log: %s", e)
        raise

    return {"error": "Failed to create log"}
