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
from backend.service.storage_service import upload_photo as upload_general_photo
from backend.service.qc_engine import determine_overall_status

logger = logging.getLogger("qc.ccp")

# ---------------------------------------------------------------------------
# OCR and Storage Config
# ---------------------------------------------------------------------------
STORAGE_BUCKET = "qc-photos"


def upload_photo(file_bytes: bytes, filename: str, folder: str = "ccp") -> str:
    """Upload a photo to Supabase storage.

    Returns the public URL of the uploaded file.
    """
    sb = get_client()
    if not sb:
        logger.warning("Supabase offline - photo not uploaded")
        return upload_general_photo(file_bytes, filename)

    try:
        path = f"{folder}/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}_{filename}"
        sb.storage.from_(STORAGE_BUCKET).upload(path, file_bytes)
        res = sb.storage.from_(STORAGE_BUCKET).get_public_url(path)
        return res
    except Exception as e:
        logger.error("Photo upload failed: %s", e)
        return upload_general_photo(file_bytes, filename)


def process_ocr(image_content: bytes) -> dict:
    """Process an image with Google Cloud Vision OCR.

    Extracts text to identify temperature, pH, or Brix readings.
    Returns a dictionary of found values.
    """
    # Note: Implementation requires google-cloud-vision package
    # For now, we return a placeholder or use a lightweight regex-based parser
    # if the user doesn't have GCP set up.
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_content)
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if not texts:
            return {}
            
        full_text = texts[0].description
        logger.info("OCR Result: %s", full_text)
        
        # Simple extraction logic (can be expanded)
        return {"raw_text": full_text}
    except Exception as e:
        logger.warning("OCR failed or not configured: %s", e)
        return {}


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
