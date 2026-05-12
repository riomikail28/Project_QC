import logging
from flask import Blueprint, request, jsonify

from backend.middleware.security_middleware import require_role
from backend.services.admin_service import AdminService

logger = logging.getLogger("qc.routes.admin")
admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")

def get_admin_service():
    return AdminService()

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
