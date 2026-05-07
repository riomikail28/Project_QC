"""
Batch Routes
=============
Blueprint for production batch lifecycle endpoints.
Handles batch CRUD, QC scoring, and dashboard analytics.

Supabase tables: production_batches, production_batch_logs, products
"""

from flask import Blueprint, request, jsonify
import logging

from backend.service.batch_service import (
    determine_batch_status,
    calculate_qc_score,
    get_batches,
    get_batch_detail,
    create_batch,
    get_daily_summary,
)
from backend.database.supabase_client import get_client
from backend.service.storage_service import upload_photo

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
def list_batches():
    """Fetch recent production batches with product details.

    Query params:
        limit (int): Max number of records (default 50)

    Returns:
        JSON list of batch records
    """
    limit = int(request.args.get("limit", 50))
    batches = get_batches(limit=limit)
    return jsonify(batches)


# ---------------------------------------------------------------------------
# GET /api/batch/<batch_id> — Get batch detail with CCP logs
# ---------------------------------------------------------------------------
@batch_bp.route("/api/batch/<batch_id>", methods=["GET"])
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
    data = request.json

    product_id = data.get("product_id")
    batch_code = data.get("batch_code")

    if not product_id or not batch_code:
        return jsonify({"error": "product_id and batch_code are required"}), 400

    try:
        photo_url = None
        photo = request.files.get("photo")
        if photo:
            photo_url = upload_photo(photo.read(), photo.filename)

        batch = create_batch(
            product_id=product_id,
            batch_code=batch_code,
            production_date=data.get("production_date"),
            shift=data.get("shift"),
            operator_id=data.get("operator_id"),
            qc_officer_id=data.get("qc_officer_id"),
            photo_url=photo_url,
        )
        return jsonify({
            "success": True,
            "batch": batch,
            "message": "Batch created. Proceed to inspection.",
        }), 201
    except Exception as e:
        logger.error("Failed to create batch: %s", e)
        return jsonify({"error": f"Gagal membuat batch: {str(e)}"}), 503


# ---------------------------------------------------------------------------
# GET /api/analytics/summary — Dashboard analytics summary
# ---------------------------------------------------------------------------
@batch_bp.route("/api/analytics/summary", methods=["GET"])
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
    from backend.skills.product_catalog import CENTRAL_KITCHEN_PRODUCTS
    return jsonify(CENTRAL_KITCHEN_PRODUCTS)
