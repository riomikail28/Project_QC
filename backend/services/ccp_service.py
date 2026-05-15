"""
CCP Service
===========
Business logic for Critical Control Point (CCP) inspections.
"""

import logging
from datetime import datetime

from backend.database.supabase_client import get_client
from backend.services.storage_service import upload_photo as upload_general_photo
from backend.services.qc_engine import determine_overall_status

logger = logging.getLogger("qc.ccp")


def upload_photo(file_bytes, filename: str, staff_id: str = "system") -> str:
    """Compatibility wrapper used by CCP routes."""
    return upload_general_photo(file_bytes, filename, staff_id=staff_id)


def process_ocr(file_bytes: bytes) -> dict:
    """OCR placeholder.

    OCR is optional in this deployment. The photo can still be uploaded and
    attached to QC records while operators enter measured values manually.
    """
    return {"raw_text": "", "status": "manual_review_required"}


def submit_ccp_log(
    batch_id: str,
    stage: str,
    operator_id: str = None,
    photo_url: str = None,
    metrics: dict = None,
    storage_path: str = None,
) -> dict:
    """Persist a CCP inspection log to Supabase."""
    sb = get_client()
    if not sb:
        return {"error": "Database offline"}

    metrics = metrics or {}
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
    if storage_path:
        payload["storage_path"] = storage_path

    mapping = {
        "temperature": "raw_temp_c",
        "core_temp": "core_temp_c",
        "ph": "ph_value_extracted",
        "brix": "brix_value_extracted",
        "tds": "tds_value",
        "room_temp": "room_temp_c",
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
