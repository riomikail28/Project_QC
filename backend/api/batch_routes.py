"""
Batch Routes
=============
Blueprint for production batch lifecycle endpoints.
Handles batch CRUD, QC scoring, and dashboard analytics.

Supabase tables: production_batches, production_batch_logs, products
"""

from flask import Blueprint, g, request, jsonify
import logging

from backend.services.batch_service import (
    determine_batch_status,
    calculate_qc_score,
    get_batches,
    get_batch_detail,
    create_batch,
    generate_batch_code,
    get_daily_summary,
    is_duplicate_batch_code_error,
)
from backend.database.supabase_client import get_client
from backend.services.storage_service import delete_photo, upload_file_storage
from backend.middleware.security_middleware import require_auth, require_role
from backend.services.audit_service import write_audit
from backend.services.request_validation import BatchCreateRequest, request_payload, validate_model

logger = logging.getLogger("qc.routes.batch")

batch_bp = Blueprint("batch_bp", __name__)


# ---------------------------------------------------------------------------
# POST /api/batch/status — Evaluate batch status from results
# ---------------------------------------------------------------------------
@batch_bp.route("/api/batch/status", methods=["POST"])
def batch_status():
    """Evaluate batch status from a list of check results.

    Request JSON:
        results (list): List of status strings, e.g. ['PASS', 'WARNING', 'FAIL']

    Returns:
        JSON with batch_status and qc_score
    """
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        data = request.form
    else:
        data = request.get_json(silent=True) or {}
    results = data.get("results", [])

    status = determine_batch_status(results)
    total = len(results)
    passed = results.count("PASS")
    score = calculate_qc_score(total, passed)

    return jsonify({
        "batch_status": status,
        "qc_score": score,
        "total_checks": total,
        "passed_checks": passed,
    })


# ---------------------------------------------------------------------------
# GET /api/batches — List recent production batches
# ---------------------------------------------------------------------------
@batch_bp.route("/api/batches", methods=["GET"])
@batch_bp.route("/api/batch/list", methods=["GET"])
@require_auth
def list_batches():
    """Fetch recent production batches with product details.

    Query params:
        limit (int): Max number of records (default 50)

    Returns:
        JSON list of batch records
    """
    limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    batches = get_batches(limit=limit)
    return jsonify(batches)


# ---------------------------------------------------------------------------
# GET /api/batch/<batch_id> — Get batch detail with CCP logs
# ---------------------------------------------------------------------------
@batch_bp.route("/api/batch/<batch_id>", methods=["GET"])
@require_auth
def get_batch(batch_id):
    """Fetch a single batch with all CCP inspection logs.

    Returns:
        JSON with batch and ccp_logs
    """
    detail = get_batch_detail(batch_id)
    if not detail.get("batch"):
        return jsonify({"error": "Batch not found"}), 404
    return jsonify(detail)


# ---------------------------------------------------------------------------
# POST /api/batch/create — Create a new production batch
# ---------------------------------------------------------------------------
@batch_bp.route("/api/batch/create", methods=["POST"])
@require_auth
def create_new_batch():
    """Create a new production batch record.

    Request JSON:
        product_id (str): Product UUID or product_code
        batch_code (str): Unique batch identifier
        production_date (str): YYYY-MM-DD
        shift (str, optional): 'Pagi', 'Siang', or 'Malam'
        operator_id (str, optional): Staff UUID
        qc_officer_id (str, optional): Staff UUID

    Returns:
        JSON with created batch record
    """
    payload = request_payload()
    # Legacy/mobile clients may still send `reason` for note-like text. Batch
    # creation persists the user-facing note as `notes`/`parameter_notes`, so
    # ignore `reason` here instead of surfacing an unknown_fields error.
    payload.pop("reason", None)
    data = validate_model(BatchCreateRequest, payload)

    product_id = data.product_id
    manual_batch_code = bool(data.batch_code)
    batch_code = data.batch_code or generate_batch_code()

    try:
        uploaded = None
        photo_url = None
        storage_path = None
        photo = request.files.get("photo")
        if photo:
            uploaded = upload_file_storage(photo, staff_id=data.operator_id or "system")
            photo_url = uploaded.url
            storage_path = uploaded.storage_path

        try:
            for attempt in range(3):
                try:
                    batch = create_batch(
                        product_id=product_id,
                        product_name=data.product_name,
                        batch_code=batch_code,
                        production_date=data.production_date,
                        expired_date=data.expired_date,
                        shift=data.shift,
                        operator_id=data.operator_id,
                        qc_officer_id=data.qc_officer_id,
                        photo_url=photo_url,
                        storage_path=storage_path,
                        ph_value=data.ph_value,
                        brix_value=data.brix_value,
                        tds_value=data.tds_value,
                        parameter_notes=data.notes,
                        parameter_checked_by=data.operator_id or (getattr(g, "current_user", {}) or {}).get("id"),
                    )
                    break
                except Exception as exc:
                    if is_duplicate_batch_code_error(exc) and not manual_batch_code and attempt < 2:
                        batch_code = generate_batch_code()
                        continue
                    raise
        except Exception:
            if uploaded:
                delete_photo(uploaded.storage_path)
            raise
        if isinstance(batch, dict) and batch.get("error"):
            if uploaded:
                delete_photo(uploaded.storage_path)
            return jsonify({"success": False, "message": batch["error"], "db_detail": batch.get("db_detail")}), 503
        write_audit("create_batch", "production_batch", str(batch.get("id")) if isinstance(batch, dict) else None, after=batch)
        if any(value is not None for value in (data.ph_value, data.brix_value, data.tds_value)):
            write_audit(
                "batch_parameter_check",
                "production_batch",
                str(batch.get("id")) if isinstance(batch, dict) else None,
                metadata={
                    "product_id": product_id,
                    "batch_code": batch_code,
                    "ph_value": data.ph_value,
                    "ph_status": (batch or {}).get("ph_status"),
                    "brix_value": data.brix_value,
                    "brix_status": (batch or {}).get("brix_status"),
                    "tds_value": data.tds_value,
                    "tds_status": (batch or {}).get("tds_status"),
                },
                after=batch,
            )

        return jsonify({
            "success": True,
            "batch": batch,
            "message": "Batch created. Proceed to inspection.",
            "photo_url": photo_url,
            "storage_path": storage_path,
        }), 201
    except ValueError as e:
        logger.error("Batch photo validation failed: %s", e)
        return jsonify({"success": False, "error": f"Upload gagal: {str(e)}"}), 400
    except Exception as e:
        if is_duplicate_batch_code_error(e):
            return jsonify({
                "success": False,
                "error_code": "DUPLICATE_BATCH_CODE",
                "message": "Kode batch sudah digunakan. Gunakan kode lain atau kosongkan agar sistem membuat otomatis.",
            }), 409
        logger.error("Failed to create batch: %s", e)
        return jsonify({"success": False, "message": f"Gagal membuat batch: {str(e)}"}), 503


# ---------------------------------------------------------------------------
# GET /api/analytics/summary — Dashboard analytics summary
# ---------------------------------------------------------------------------
@batch_bp.route("/api/analytics/summary", methods=["GET"])
@require_auth
def analytics_summary():
    """Fetch aggregated dashboard summary for a given day.

    Query params:
        day (str): ISO date string (default: today)

    Returns:
        JSON with batch counts, alerts, and facility readings
    """
    day = request.args.get("day")
    summary = get_daily_summary(day=day)
    return jsonify(summary)


# ---------------------------------------------------------------------------
# GET /api/products — List active products
# ---------------------------------------------------------------------------
@batch_bp.route("/api/products", methods=["GET"])
@require_auth
def list_products():
    """Fetch all active products with SOP thresholds.

    Falls back to local catalog if database is unavailable.

    Returns:
        JSON list of products
    """
    sb = get_client()
    if sb:
        try:
            res = (
                sb.table("products")
                .select("*")
                .eq("is_active", True)
                .order("product_code")
                .execute()
            )
            if res.data:
                for item in res.data:
                    if "product_code" not in item and item.get("sku_code"):
                        item["product_code"] = item["sku_code"]
                return jsonify(res.data)
        except Exception as e:
            logger.warning("Product DB unavailable, using local catalog: %s", e)

    # Fallback to local catalog
    from backend.qc.product_catalog import CENTRAL_KITCHEN_PRODUCTS
    return jsonify(CENTRAL_KITCHEN_PRODUCTS)
