"""
Batch Routes
=============
Blueprint for production batch lifecycle endpoints.
Handles batch CRUD, QC scoring, and dashboard analytics.

Supabase tables: production_batches, production_batch_logs, products
"""

from flask import Blueprint, g, request, jsonify
import logging
from datetime import datetime, timedelta, timezone

from backend.services.batch_service import (
    determine_batch_status,
    calculate_qc_score,
    get_batches,
    get_batch_detail,
    create_batch,
    generate_batch_code,
    generate_product_batch_code,
    preview_next_batch_code,
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


def _jakarta_today():
    return datetime.now(timezone(timedelta(hours=7))).date().isoformat()


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


@batch_bp.route("/api/batch/next-code", methods=["GET"])
@require_auth
def next_batch_code():
    product_id = request.args.get("product_id") or request.args.get("sku") or ""
    production_date = request.args.get("production_date") or None
    product_name = request.args.get("product_name") or None
    return jsonify({"success": True, "data": preview_next_batch_code(product_id, production_date, product_name)})


@batch_bp.route("/api/batch/next", methods=["POST"])
@require_auth
def create_next_batch():
    """Create the next cooking batch for a product/date from QC Check."""
    sb = get_client()
    if not sb:
        return jsonify({"success": False, "message": "Database belum terhubung"}), 503
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    production_date = data.get("production_date") or _jakarta_today()
    cook_name = (data.get("cook_name") or "").strip()
    production_shift = (data.get("production_shift") or data.get("shift") or "").strip()
    if not product_id:
        return jsonify({"success": False, "message": "product_id wajib diisi"}), 400
    if not cook_name:
        return jsonify({"success": False, "message": "cook_name wajib diisi"}), 400
    if not production_shift:
        return jsonify({"success": False, "message": "production_shift wajib diisi"}), 400
    try:
        quantity = float(data.get("quantity"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "quantity harus angka"}), 400
    if quantity <= 0:
        return jsonify({"success": False, "message": "quantity harus lebih dari 0"}), 400

    def optional_number(field, minimum=None, maximum=None):
        value = data.get(field)
        if value in (None, ""):
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} harus angka")
        if minimum is not None and parsed < minimum:
            raise ValueError(f"{field} tidak boleh kurang dari {minimum}")
        if maximum is not None and parsed > maximum:
            raise ValueError(f"{field} tidak boleh lebih dari {maximum}")
        return parsed

    try:
        ph_value = optional_number("ph", 0, 14) if "ph" in data else optional_number("ph_value", 0, 14)
        brix_value = optional_number("brix", 0, 100) if "brix" in data else optional_number("brix_value", 0, 100)
        tds_value = optional_number("tds", 0, 1000000) if "tds" in data else optional_number("tds_value", 0, 1000000)
        product_rows = sb.table("products").select("*").eq("id", product_id).limit(1).execute().data or []
        if not product_rows:
            product_rows = sb.table("products").select("*").eq("product_code", product_id).limit(1).execute().data or []
        product = product_rows[0] if product_rows else {"id": product_id, "product_code": product_id, "product_name": data.get("product_name")}
        sku = product.get("product_code") or product.get("sku_code") or product_id
        existing = (
            sb.table("production_batches")
            .select("batch_sequence, batch_code")
            .eq("product_id", product.get("id") or product_id)
            .eq("production_date", production_date)
            .execute()
            .data
            or []
        )
        next_sequence = max([int(row.get("batch_sequence") or 0) for row in existing] or [0]) + 1
        batch_code = generate_product_batch_code(sku, production_date, next_sequence)
        payload = {
            "product_id": product.get("id") or product_id,
            "product_name": product.get("product_name") or data.get("product_name"),
            "production_date": production_date,
            "batch_sequence": next_sequence,
            "batch_code": batch_code,
            "cook_name": cook_name,
            "quantity": quantity,
            "production_shift": production_shift,
            "shift": production_shift,
            "ph_value": ph_value,
            "brix_value": brix_value,
            "tds_value": tds_value,
            "parameter_notes": data.get("notes"),
            "status": "in_progress",
            "final_qc_status": "PENDING_REVIEW",
            "created_by": (getattr(g, "current_user", {}) or {}).get("id"),
        }
        row = (sb.table("production_batches").insert({k: v for k, v in payload.items() if v not in (None, "")}).execute().data or [payload])[0]
        write_audit("create_next_batch", "production_batch", str(row.get("id") or batch_code), after=row)
        return jsonify({"success": True, "data": row, "batch": row, "message": "Pemasakan berhasil disimpan"}), 201
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        logger.error("Failed to create next batch: %s", exc)
        return jsonify({"success": False, "message": f"Gagal menyimpan pemasakan: {str(exc)}"}), 500


@batch_bp.route("/api/batch/by-product/<product_id>", methods=["GET"])
@require_auth
def batches_by_product(product_id):
    """Return production batches grouped for a selected product/SKU card."""
    sb = get_client()
    operational_date = request.args.get("date") or _jakarta_today()
    if not sb:
        return jsonify({"success": True, "data": {"date": operational_date, "product": None, "batches": []}})
    try:
        product_rows = (
            sb.table("products")
            .select("*")
            .eq("id", product_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not product_rows:
            product_rows = (
                sb.table("products")
                .select("*")
                .eq("product_code", product_id)
                .limit(1)
                .execute()
                .data
                or []
            )
        product = product_rows[0] if product_rows else {"id": product_id, "product_code": product_id}
        product_code = product.get("product_code") or product.get("sku_code") or product_id

        batch_rows = (
            sb.table("production_batches")
            .select("*")
            .eq("product_id", product.get("id") or product_id)
            .eq("production_date", operational_date)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )
        if not batch_rows and product_code:
            batch_rows = (
                sb.table("production_batches")
                .select("*")
                .eq("product_code", product_code)
                .eq("production_date", operational_date)
                .order("created_at", desc=True)
                .limit(100)
                .execute()
                .data
                or []
            )

        reports = sb.table("qc_reports").select("*").order("created_at", desc=True).limit(500).execute().data or []
        report_map = {}
        for report in reports:
            keys = [report.get("batch_id"), report.get("batch_code")]
            for key in keys:
                if key and key not in report_map:
                    report_map[key] = report

        batches = []
        for row in batch_rows:
            last_qc = report_map.get(row.get("id")) or report_map.get(row.get("batch_code")) or {}
            qc_status = last_qc.get("status") or row.get("final_qc_status") or row.get("status") or "pending"
            batches.append({
                "id": row.get("id"),
                "batch_code": row.get("batch_code"),
                "batch_sequence": row.get("batch_sequence"),
                "cook_name": row.get("cook_name"),
                "quantity": row.get("quantity"),
                "production_shift": row.get("production_shift") or row.get("shift"),
                "production_time": row.get("production_time") or row.get("created_at"),
                "qc_status": qc_status,
                "last_qc": last_qc or None,
                "inspection_round": last_qc.get("inspection_round") or 0,
            })

        return jsonify({"success": True, "data": {"date": operational_date, "product": product, "batches": batches}})
    except Exception as exc:
        logger.error("Failed to fetch batches by product: %s", exc)
        return jsonify({"success": False, "message": "Gagal memuat batch produk"}), 500


# ---------------------------------------------------------------------------
# GET /api/batch/<batch_id> — Get batch detail with CCP logs
# ---------------------------------------------------------------------------
@batch_bp.route("/api/batch/today", methods=["GET"])
@require_auth
def today_batches():
    """Return production batches for the selected operational date grouped by product."""
    sb = get_client()
    operational_date = request.args.get("date") or _jakarta_today()
    if not sb:
        return jsonify({"success": True, "data": {"date": operational_date, "products": []}})
    try:
        batch_rows = (
            sb.table("production_batches")
            .select("*")
            .eq("production_date", operational_date)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )
        product_rows = sb.table("products").select("*").limit(1000).execute().data or []
        product_map = {row.get("id"): row for row in product_rows if row.get("id")}
        reports = sb.table("qc_reports").select("*").order("created_at", desc=True).limit(1000).execute().data or []
        report_map = {}
        for report in reports:
            for key in (report.get("batch_id"), report.get("batch_code")):
                if key and key not in report_map:
                    report_map[key] = report

        grouped = {}
        for row in batch_rows:
            product = product_map.get(row.get("product_id")) or {}
            product_id = row.get("product_id") or product.get("id") or row.get("product_code") or row.get("sku_code")
            sku = product.get("product_code") or product.get("sku_code") or row.get("product_code") or row.get("sku_code") or row.get("barcode") or product_id
            key = str(product_id or sku)
            group = grouped.setdefault(key, {
                "product_id": product_id,
                "sku": sku,
                "product_name": product.get("product_name") or row.get("product_name") or "Produk",
                "category": product.get("category") or row.get("category") or row.get("product_category"),
                "batch_count": 0,
                "status_summary": {"pending": 0, "pass": 0, "hold": 0, "fail": 0},
                "batches": [],
            })
            last_qc = report_map.get(row.get("id")) or report_map.get(row.get("batch_code")) or {}
            qc_status = last_qc.get("status") or row.get("final_qc_status") or row.get("status") or "pending"
            normalized = str(qc_status or "pending").lower()
            if normalized in {"passed", "completed"}:
                normalized = "pass"
            elif normalized == "failed":
                normalized = "fail"
            elif normalized == "on_hold":
                normalized = "hold"
            elif normalized not in {"pass", "hold", "fail"}:
                normalized = "pending"
            group["batch_count"] += 1
            group["status_summary"][normalized] += 1
            group["batches"].append({
                "id": row.get("id"),
                "batch_code": row.get("batch_code"),
                "batch_sequence": row.get("batch_sequence"),
                "cook_name": row.get("cook_name"),
                "quantity": row.get("quantity"),
                "production_shift": row.get("production_shift") or row.get("shift"),
                "production_date": row.get("production_date"),
                "production_time": row.get("production_time") or row.get("created_at"),
                "qc_status": qc_status,
                "last_qc": last_qc or None,
                "inspection_round": last_qc.get("inspection_round") or 0,
            })

        return jsonify({"success": True, "data": {"date": operational_date, "products": list(grouped.values())}})
    except Exception as exc:
        logger.error("Failed to fetch today's batches: %s", exc)
        return jsonify({"success": False, "message": "Gagal memuat batch hari ini"}), 500


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
    batch_code = data.batch_code

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
                        batch_sequence=data.batch_sequence,
                        production_date=data.production_date,
                        expired_date=data.expired_date,
                        shift=data.shift or data.production_shift,
                        production_shift=data.production_shift or data.shift,
                        cook_name=data.cook_name,
                        quantity=data.quantity,
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
