"""
Auto Reporter
==============
Generates QC summary reports for production batches.
Compiles CCP data, violations, and status into structured output.
"""

import logging
from datetime import datetime

from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.reporter")


def generate_batch_report(batch_id: str) -> dict:
    """Generate a complete QC report for a production batch.

    Args:
        batch_id: UUID of the production batch

    Returns:
        dict with report data including status, violations, and timestamps
    """
    sb = get_client()
    if not sb:
        return {"error": "Database offline", "batch_id": batch_id}

    try:
        # Fetch batch details
        batch_columns = (
            "id,product_id,product_name,batch_code,batch_sequence,production_date,expired_date,status,created_by,"
            "cook_name,quantity,production_shift,ph_value,brix_value,tds_value,ph_status,brix_status,tds_status,"
            "parameter_notes,parameter_checked_by,parameter_checked_at,shift,operator_id,qc_officer_id,photo_url,"
            "storage_path,created_at,updated_at,products(product_code, product_name)"
        )
        batch_res = sb.table("production_batches").select(batch_columns).eq("id", batch_id).execute()

        if not batch_res.data:
            return {"error": "Batch not found", "batch_id": batch_id}

        batch = batch_res.data[0]

        # Fetch CCP logs
        log_columns = (
            "id,batch_id,stage,operator_id,photo_url,stage_qc_status,metrics,recorded_at,storage_path,"
            "raw_temp_c,core_temp_c,ph_value_extracted,brix_value_extracted,tds_value,room_temp_c,"
            "raw_temp_status,core_temp_status,ph_value_status,brix_value_status,tds_value_status,room_temp_status"
        )
        logs_res = (
            sb.table("production_batch_logs")
            .select(log_columns)
            .eq("batch_id", batch_id)
            .order("recorded_at")
            .execute()
        )
        logs = logs_res.data or []

        # Analyze violations
        violations = []
        stages_status = {}

        for log in logs:
            stage = log.get("stage", "UNKNOWN")
            stage_status = log.get("stage_qc_status", "pending_review")
            stages_status[stage] = stage_status

            if stage_status == "fail":
                violations.append(
                    {
                        "stage": stage,
                        "recorded_at": log.get("recorded_at"),
                        "details": _extract_violation_details(log),
                    }
                )

        # Determine final status
        if any(s == "fail" for s in stages_status.values()):
            final_status = "FAIL"
        elif all(s == "pass" for s in stages_status.values()) and stages_status:
            final_status = "PASS"
        else:
            final_status = "PENDING"

        # Update batch final status
        if final_status in ("PASS", "FAIL"):
            sb.table("production_batches").update(
                {
                    "final_qc_status": final_status.lower(),
                    "status": "completed",
                }
            ).eq("id", batch_id).execute()

        product = batch.get("products", {})

        return {
            "batch_id": batch_id,
            "batch_code": batch.get("batch_code"),
            "product": {
                "code": product.get("product_code"),
                "name": product.get("product_name"),
            },
            "production_date": batch.get("production_date"),
            "shift": batch.get("shift"),
            "final_status": final_status,
            "stages": stages_status,
            "violations": violations,
            "total_stages": len(stages_status),
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Report generation failed: %s", e)
        return {"error": str(e), "batch_id": batch_id}


def _extract_violation_details(log: dict) -> str:
    """Extract human-readable violation details from a CCP log entry."""
    details = []

    if log.get("raw_temp_status") == "fail":
        details.append(f"Raw temp: {log.get('raw_temp_c')}°C (exceeds limit)")

    if log.get("core_temp_status") == "fail":
        details.append(f"Core temp: {log.get('core_temp_c')}°C (below minimum)")

    if log.get("ph_value_status") == "fail":
        details.append(f"pH: {log.get('ph_value_extracted')} (out of range)")

    if log.get("brix_value_status") == "fail":
        details.append(f"Brix: {log.get('brix_value_extracted')} (out of range)")

    if log.get("tds_value_status") == "fail":
        details.append(f"TDS: {log.get('tds_value')} (out of range)")

    if log.get("room_temp_status") == "fail":
        details.append(f"Room temp: {log.get('room_temp_c')}°C (exceeds limit)")

    return "; ".join(details) if details else "Unspecified violation"
