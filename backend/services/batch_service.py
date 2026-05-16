"""
Batch Service
=============
Business logic for production batch lifecycle management.
Handles batch creation, status determination, and QC scoring.
"""

import logging
from datetime import date
from uuid import UUID
from backend.database.supabase_client import direct_db_query, get_client, get_last_db_error

logger = logging.getLogger("qc.batch")


def _looks_like_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


def determine_batch_status(results: list) -> str:
    """Determine final batch status from a list of individual check results.

    Args:
        results: List of status strings, e.g. ['PASS', 'PASS', 'FAIL']

    Returns:
        'FAIL' if any check failed, 'WARNING' if any warned, else 'PASS'
    """
    if "FAIL" in results:
        return "FAIL"
    elif "WARNING" in results:
        return "WARNING"
    return "PASS"


def calculate_qc_score(total_checks: int, passed_checks: int) -> float:
    """Calculate QC score as percentage.

    Args:
        total_checks: Total number of checks performed
        passed_checks: Number of checks that passed

    Returns:
        Score as a percentage (0–100), rounded to 2 decimal places
    """
    if total_checks == 0:
        return 0.0
    return round((passed_checks / total_checks) * 100, 2)


def get_batches(limit: int = 50) -> list:
    """Fetch recent production batches from Supabase.

    Returns a list of batch records with product info joined.
    """
    sb = get_client()
    if not sb:
        return []

    try:
        res = (
            sb.table("production_batches")
            .select(
                "id, batch_code, production_date, shift, status, "
                "final_qc_status, report_url, created_at, "
                "products(*)"
            )
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error("Failed to fetch batches: %s", e)
        return []


def get_batch_detail(batch_id: str) -> dict:
    """Fetch a single batch with all CCP logs.

    Returns dict with 'batch' and 'ccp_logs' keys.
    """
    sb = get_client()
    if not sb:
        return {"batch": None, "ccp_logs": []}

    try:
        batch_res = sb.table("production_batches").select("*").eq("id", batch_id).execute()
        if not batch_res.data:
            return {"batch": None, "ccp_logs": []}

        logs = (
            sb.table("production_batch_logs")
            .select("*")
            .eq("batch_id", batch_id)
            .order("recorded_at")
            .execute()
        )
        return {
            "batch": batch_res.data[0],
            "ccp_logs": logs.data or [],
        }
    except Exception as e:
        logger.error("Failed to fetch batch detail: %s", e)
        return {"batch": None, "ccp_logs": []}


def create_batch(
    batch_code: str,
    product_id: str = None,
    product_name: str = None,
    production_date: str = None,
    expired_date: str = None,
    shift: str = None,
    operator_id: str = None,
    qc_officer_id: str = None,
    photo_url: str = None,
    storage_path: str = None,
) -> dict:
    """Create a new production batch record in Supabase.

    Returns the created batch record or raises on failure.
    """
    sb = get_client()

    resolved_product_id = product_id
    resolved_product_name = product_name
    if sb and product_id and not _looks_like_uuid(product_id):
        for code_column in ("product_code", "sku_code"):
            try:
                product_res = (
                    sb.table("products")
                    .select("id, product_name")
                    .eq(code_column, product_id)
                    .limit(1)
                    .execute()
                )
                if product_res.data:
                    resolved_product_id = product_res.data[0]["id"]
                    resolved_product_name = resolved_product_name or product_res.data[0].get("product_name")
                    break
            except Exception as e:
                logger.warning("Could not resolve product code via %s: %s", code_column, e)
    if resolved_product_id and not _looks_like_uuid(resolved_product_id):
        resolved_product_name = resolved_product_name or resolved_product_id
        resolved_product_id = None
    if not resolved_product_id:
        default_product = _ensure_default_product(sb)
        resolved_product_id = default_product.get("id") if default_product else None
        resolved_product_name = resolved_product_name or (default_product or {}).get("product_name") or "General QC Product"

    payload = {
        "product_id": resolved_product_id,
        "product_name": resolved_product_name,
        "batch_code": batch_code,
        "production_date": production_date or date.today().isoformat(),
        "expired_date": expired_date,
        "status": "in_progress",
        "created_by": operator_id,
    }
    payload = {key: value for key, value in payload.items() if value not in (None, "")}
    if shift:
        payload["shift"] = shift
    if operator_id:
        payload["operator_id"] = operator_id
    if qc_officer_id:
        payload["qc_officer_id"] = qc_officer_id
    if photo_url:
        payload["photo_url"] = photo_url
    if storage_path:
        payload["storage_path"] = storage_path

    try:
        if sb:
            res = sb.table("production_batches").insert([payload]).execute()
            if res.data:
                logger.info("Batch created: %s", batch_code)
                return res.data[0]
        rows = direct_db_query("production_batches", "POST", payload)
        if rows:
            logger.info("Batch created via direct query: %s", batch_code)
            return rows[0]
    except Exception as e:
        logger.error("Failed to create batch: %s", e)
        raise

    return {"error": "Database offline or no data returned", "db_detail": get_last_db_error()}


def _ensure_default_product(sb=None) -> dict | None:
    """Return the GENERAL-QC product, creating it if needed.

    Production schema keeps production_batches.product_id NOT NULL, so every
    batch needs a real product UUID even when staff enters a free-form batch.
    """
    payload = {
        "product_code": "GENERAL-QC",
        "product_name": "General QC Product",
        "is_active": True,
    }
    try:
        if sb:
            existing = (
                sb.table("products")
                .select("id, product_code, product_name")
                .eq("product_code", "GENERAL-QC")
                .limit(1)
                .execute()
            )
            if existing.data:
                return existing.data[0]
            created = sb.table("products").insert([payload]).execute()
            return created.data[0] if created.data else None

        rows = direct_db_query("products", "GET", None, "product_code=eq.GENERAL-QC&limit=1")
        if rows:
            return rows[0]
        created = direct_db_query("products", "POST", payload)
        return created[0] if created else None
    except Exception as exc:
        logger.error("Failed to ensure default product GENERAL-QC: %s", exc)
        return None


def get_daily_summary(day: str = None) -> dict:
    """Fetch dashboard summary data for a given day.

    Returns aggregated counts and recent facility readings.
    """
    sb = get_client()
    selected_day = day or date.today().isoformat()

    if not sb:
        return _empty_summary(selected_day)

    try:
        # Batch stats for the day
        batches = (
            sb.table("production_batches")
            .select(
                "id, batch_code, production_date, shift, status, "
                "final_qc_status, created_at, "
                "products(*)"
            )
            .eq("production_date", selected_day)
            .order("created_at", desc=True)
            .execute()
        ).data or []

        # Open alerts count
        alerts = (
            sb.table("facility_alerts")
            .select("id")
            .eq("status", "open")
            .execute()
        ).data or []

        # Latest facility readings
        facility_logs = (
            sb.table("facility_logs")
            .select("temperature_c, is_normal, recorded_at, facility_rooms(name), facility_devices(name, type, threshold_temp)")
            .order("recorded_at", desc=True)
            .limit(50)
            .execute()
        ).data or []

        # Deduplicate: latest per zone
        latest_by_zone = {}
        for row in facility_logs:
            room_name = (row.get("facility_rooms") or {}).get("name") or "Unknown"
            device = row.get("facility_devices") or {}
            zone = f"{room_name} - {device.get('name', 'Suhu Ruangan')}"
            latest_by_zone.setdefault(zone, {
                "zone": zone,
                "temperature_c": row.get("temperature_c"),
                "threshold_c": device.get("threshold_temp", 25.0),
                "is_normal": row.get("is_normal", True),
                "recorded_at": row.get("recorded_at"),
            })

        return {
            "date": selected_day,
            "batch_today": len(batches),
            "batch_pass": sum(1 for b in batches if b.get("final_qc_status") == "pass"),
            "batch_fail": sum(1 for b in batches if b.get("final_qc_status") == "fail"),
            "open_alerts": len(alerts),
            "latest_facility": list(latest_by_zone.values()),
            "recent_batches": batches[:10],
        }
    except Exception as e:
        logger.error("Dashboard summary error: %s", e)
        return _empty_summary(selected_day)


def _empty_summary(day: str) -> dict:
    return {
        "date": day,
        "batch_today": 0,
        "batch_pass": 0,
        "batch_fail": 0,
        "open_alerts": 0,
        "latest_facility": [],
        "recent_batches": [],
    }
