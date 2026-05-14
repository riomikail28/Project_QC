import logging
from flask import Blueprint, request, jsonify

from backend.middleware.security_middleware import require_role
from backend.services.admin_service import AdminService

logger = logging.getLogger("qc.routes.admin")
admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")

def get_admin_service():
    return AdminService()


def _nullable_number(value):
    if value in ("", None):
        return None
    return float(value)


def _nullable_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "no", "off")
    return bool(value)


def _product_payload(data):
    code = (data.get("product_code") or data.get("sku_code") or "").strip()
    name = (data.get("product_name") or "").strip()
    if not code or not name:
        raise ValueError("Kode SKU dan nama produk wajib diisi")

    return {
        "product_code": code,
        "sku_code": code,
        "product_name": name,
        "ph_min": _nullable_number(data.get("ph_min")),
        "ph_max": _nullable_number(data.get("ph_max")),
        "brix_min": _nullable_number(data.get("brix_min")),
        "brix_max": _nullable_number(data.get("brix_max")),
        "tds_min": _nullable_number(data.get("tds_min")),
        "tds_max": _nullable_number(data.get("tds_max")),
        "is_active": _nullable_bool(data.get("is_active"), True),
    }

@admin_bp.route("/analytics/overview", methods=["GET"])
@require_role("admin")
def analytics_overview():
    service = get_admin_service()
    res = service.get_dashboard_overview()
    if res.get("success"):
        return jsonify(res["data"])
    return jsonify({"detail": res.get("detail", "Error fetching analytics")}), 500

@admin_bp.route("/monitoring/realtime", methods=["GET"])
@require_role("admin")
def monitoring_realtime():
    service = get_admin_service()
    res = service.get_realtime_monitoring()
    if res.get("success"):
        return jsonify(res["data"])
    return jsonify({"detail": res.get("detail", "Error fetching monitoring data")}), 500

@admin_bp.route("/qc-reports", methods=["GET"])
@require_role("admin")
def qc_reports():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    status_filter = request.args.get("status")
    
    service = get_admin_service()
    res = service.get_qc_reports(page, limit, status_filter)
    if res.get("success"):
        return jsonify({"data": res["data"], "count": res.get("count", 0), "page": page, "limit": limit})
    return jsonify({"detail": res.get("detail", "Error fetching reports")}), 500

@admin_bp.route("/audit-trail", methods=["GET"])
@require_role("admin")
def audit_trail():
    limit = int(request.args.get("limit", 50))
    service = get_admin_service()
    res = service.get_audit_trail(limit)
    if res.get("success"):
        return jsonify(res["data"])
    return jsonify({"detail": res.get("detail", "Error fetching audit trail")}), 500


@admin_bp.route("/traceability", methods=["GET"])
@require_role("admin")
def traceability():
    limit = int(request.args.get("limit", 50))
    barcode = request.args.get("barcode")
    service = get_admin_service()
    res = service.get_traceability(barcode=barcode, limit=limit)
    if res.get("success"):
        return jsonify(res["data"])
    return jsonify({"detail": res.get("detail", "Error fetching traceability")}), 500


@admin_bp.route("/approvals", methods=["GET"])
@require_role("admin")
def approvals():
    limit = int(request.args.get("limit", 50))
    service = get_admin_service()
    res = service.get_pending_approvals(limit=limit)
    if res.get("success"):
        return jsonify(res["data"])
    return jsonify({"detail": res.get("detail", "Error fetching approvals")}), 500


@admin_bp.route("/products", methods=["GET", "POST"])
@require_role("admin")
def products():
    service = get_admin_service()
    if request.method == "POST":
        try:
            payload = _product_payload(request.get_json(silent=True) or {})
        except (TypeError, ValueError) as exc:
            return jsonify({"detail": str(exc)}), 400

        res = service.create_product(payload)
        if res.get("success"):
            return jsonify(res["data"]), 201
        return jsonify({"detail": res.get("detail", "Error creating product")}), 500

    res = service.list_products()
    if res.get("success"):
        return jsonify(res["data"])
    return jsonify({"detail": res.get("detail", "Error fetching products")}), 500


@admin_bp.route("/products/<product_id>", methods=["PATCH", "PUT", "DELETE"])
@require_role("admin")
def product_detail(product_id):
    service = get_admin_service()
    if request.method in ("PATCH", "PUT"):
        try:
            payload = _product_payload(request.get_json(silent=True) or {})
        except (TypeError, ValueError) as exc:
            return jsonify({"detail": str(exc)}), 400

        res = service.update_product(product_id, payload)
        if res.get("success"):
            return jsonify(res["data"])
        return jsonify({"detail": res.get("detail", "Error updating product")}), 500

    res = service.delete_product(product_id)
    if res.get("success"):
        return jsonify(res["data"])
    return jsonify({"detail": res.get("detail", "Error deleting product")}), 500
