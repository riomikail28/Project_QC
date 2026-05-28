import logging
from flask import Blueprint, Response, current_app, g, request, jsonify

from backend.middleware.security_middleware import require_role
from backend.services.admin_service import AdminService
from backend.services.google_apps_script_service import google_sheets_status, send_test_payload
from backend.database.supabase_client import get_client, supabase_error_response

logger = logging.getLogger("qc.routes.admin")
admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")
admin_legacy_bp = Blueprint("admin_legacy", __name__, url_prefix="/api/admin")

def get_admin_service():
    return AdminService()


def _require_supabase():
    if current_app.config.get("TESTING"):
        return True, None
    sb = get_client()
    if not sb:
        body, status = supabase_error_response()
        return None, (jsonify(body), status)
    return sb, None


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
@admin_bp.route("/audit-logs", methods=["GET"])
@require_role("admin")
def audit_trail():
    limit = int(request.args.get("limit", 50))
    service = get_admin_service()
    res = service.get_audit_trail(
        limit=limit,
        date=request.args.get("date"),
        action=request.args.get("action"),
        user=request.args.get("user") or request.args.get("staff") or request.args.get("staff_id"),
    )
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


def _enveloped(res, ok_status=200):
    status = ok_status if res.get("success") else 500
    body = {
        "success": bool(res.get("success")),
        "data": res.get("data"),
        "message": res.get("message") or ("OK" if res.get("success") else res.get("detail", "Error")),
    }
    if not res.get("success"):
        body["error"] = res.get("detail") or res.get("message")
        body["error_code"] = res.get("error_code") or "ADMIN_API_ERROR"
    return jsonify(body), status


@admin_bp.before_request
def require_admin_supabase():
    if request.endpoint and request.endpoint.startswith("admin."):
        if "google_sheets" in request.endpoint:
            return None
        _, error = _require_supabase()
        if error:
            return error


@admin_legacy_bp.before_request
def require_legacy_admin_supabase():
    if request.endpoint and request.endpoint.startswith("admin_legacy."):
        if "google_sheets" in request.endpoint:
            return None
        _, error = _require_supabase()
        if error:
            return error


@admin_bp.route("/google-sheets/status", methods=["GET"])
@require_role("admin")
def google_sheets_status_route():
    return jsonify({"success": True, "data": google_sheets_status(), "message": "OK"})


@admin_bp.route("/google-sheets/test", methods=["POST"])
@require_role("admin")
def google_sheets_test_route():
    ok = send_test_payload()
    status = google_sheets_status()
    return jsonify({
        "success": ok,
        "data": status,
        "message": "Google Sheets test export sent" if ok else "Google Sheets test export failed",
    }), 200 if ok else 502


@admin_legacy_bp.route("/google-sheets/status", methods=["GET"])
@require_role("admin")
def legacy_google_sheets_status_route():
    return google_sheets_status_route()


@admin_legacy_bp.route("/google-sheets/test", methods=["POST"])
@require_role("admin")
def legacy_google_sheets_test_route():
    return google_sheets_test_route()


def _report_args(default_limit=100):
    return {
        "limit": min(max(int(request.args.get("limit", default_limit)), 1), 2000),
        "date": request.args.get("date"),
        "staff_id": request.args.get("staff") or request.args.get("staff_id"),
        "status_filter": request.args.get("status"),
    }


@admin_bp.route("/reports/temperature", methods=["GET"])
@require_role("admin")
def report_temperature():
    return _enveloped(get_admin_service().get_temperature_report(**_report_args()))


@admin_bp.route("/reports/summary", methods=["GET"])
@require_role("admin")
def report_summary():
    service = get_admin_service()
    today = request.args.get("date") or None
    temperature = service.get_temperature_report(limit=2000, date=today).get("data", [])
    inspection = service.get_inspection_report(limit=2000, date=today).get("data", [])
    overview = service.get_dashboard_overview().get("data", {})
    statuses = [str(row.get("status") or "").lower() for row in inspection]
    data = {
        "total_monitoring_today": len(temperature),
        "total_qc_today": len(inspection),
        "pass": sum(1 for status in statuses if status == "pass"),
        "hold_warning": sum(1 for status in statuses if status in {"hold", "warning", "pending_review"}),
        "fail": sum(1 for status in statuses if status in {"fail", "failed"}),
        "temperature_alerts": overview.get("total_open_alerts", 0),
        "pending_approval": overview.get("total_qc_pending", 0),
    }
    return _enveloped({"success": True, "data": data})


@admin_bp.route("/reports/monitoring", methods=["GET"])
@require_role("admin")
def report_monitoring():
    return report_temperature()


@admin_bp.route("/reports/qc", methods=["GET"])
@require_role("admin")
def report_qc():
    return report_inspection()


@admin_bp.route("/reports/alerts", methods=["GET"])
@require_role("admin")
def report_alerts():
    service = get_admin_service()
    rows = service._fetch("facility_alerts", order_by="created_at", limit=min(max(int(request.args.get("limit", 100)), 1), 500))
    data = [{
        "id": row.get("id"),
        "created_at": row.get("created_at"),
        "room": row.get("zone") or row.get("room") or row.get("room_name"),
        "device": row.get("device_name") or row.get("device_id"),
        "temperature": row.get("temperature") or row.get("temperature_c"),
        "status": row.get("status") or row.get("severity") or "warning",
        "message": row.get("message") or row.get("title") or row.get("corrective_action"),
        "staff_id": row.get("staff_id"),
    } for row in rows]
    return _enveloped({"success": True, "data": data})


@admin_bp.route("/reports/inspection", methods=["GET"])
@require_role("admin")
def report_inspection():
    return _enveloped(get_admin_service().get_inspection_report(**_report_args()))


@admin_bp.route("/reports/findings", methods=["GET"])
@require_role("admin")
def report_findings():
    return _enveloped(get_admin_service().get_findings_report(**_report_args()))


@admin_bp.route("/reports/evidence", methods=["GET"])
@require_role("admin")
def report_evidence():
    args = _report_args()
    args.pop("status_filter", None)
    return _enveloped(get_admin_service().get_evidence_report(**args))


@admin_bp.route("/reports/daily", methods=["GET"])
@require_role("admin")
def report_daily():
    args = _report_args(default_limit=500)
    return _enveloped(get_admin_service().get_daily_staff_report(**args))


@admin_bp.route("/export/daily-report", methods=["GET"])
@require_role("admin")
def export_daily_report():
    date = request.args.get("date")
    staff_id = request.args.get("staff") or request.args.get("staff_id")
    status_filter = request.args.get("status")
    csv_body = get_admin_service().export_daily_report_csv(date=date, staff_id=staff_id, status_filter=status_filter)
    try:
        from backend.services.audit_service import write_audit
        actor = getattr(g, "current_user", {}) or {}
        write_audit(
            "export_daily_report",
            "daily_report",
            date or "today",
            metadata={"date": date, "staff_id": staff_id, "status": status_filter},
            after={"exported_by": actor.get("id") or actor.get("sub")},
        )
    except Exception:
        pass
    filename_date = date or "today"
    response = Response(csv_body, mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=qc_daily_report_{filename_date}.csv"
    return response


@admin_legacy_bp.route("/reports/temperature", methods=["GET"])
@require_role("admin")
def legacy_report_temperature():
    return report_temperature()


@admin_legacy_bp.route("/reports/inspection", methods=["GET"])
@require_role("admin")
def legacy_report_inspection():
    return report_inspection()


@admin_legacy_bp.route("/reports/findings", methods=["GET"])
@require_role("admin")
def legacy_report_findings():
    return report_findings()


@admin_legacy_bp.route("/reports/evidence", methods=["GET"])
@require_role("admin")
def legacy_report_evidence():
    return report_evidence()


@admin_legacy_bp.route("/reports/daily", methods=["GET"])
@require_role("admin")
def legacy_report_daily():
    return report_daily()


@admin_legacy_bp.route("/export/daily-report", methods=["GET"])
@require_role("admin")
def legacy_export_daily_report():
    return export_daily_report()


@admin_legacy_bp.route("/approvals", methods=["GET"])
@require_role("admin")
def legacy_approvals():
    return approvals()


@admin_legacy_bp.route("/approvals/<approval_id>/approve", methods=["POST"])
@require_role("admin")
def legacy_approve(approval_id):
    return approve(approval_id)


@admin_legacy_bp.route("/approvals/<approval_id>/reject", methods=["POST"])
@require_role("admin")
def legacy_reject(approval_id):
    return reject(approval_id)


@admin_legacy_bp.route("/audit-trail", methods=["GET"])
@admin_legacy_bp.route("/audit-logs", methods=["GET"])
@require_role("admin")
def legacy_audit_trail():
    return audit_trail()


@admin_bp.route("/reports/batches", methods=["GET"])
@require_role("admin")
def report_batches():
    limit = min(max(int(request.args.get("limit", 100)), 1), 500)
    return _enveloped(get_admin_service().get_batch_report(limit=limit))


@admin_bp.route("/reports/staff-activity", methods=["GET"])
@require_role("admin")
def report_staff_activity():
    limit = min(max(int(request.args.get("limit", 100)), 1), 500)
    return _enveloped(get_admin_service().get_staff_activity_report(limit=limit))


@admin_bp.route("/approvals/<approval_id>/approve", methods=["POST"])
@require_role("admin")
def approve(approval_id):
    payload = request.get_json(silent=True) or {}
    actor = getattr(g, "current_user", {}) or {}
    return _enveloped(get_admin_service().approve_item(approval_id, actor_id=actor.get("id") or actor.get("sub"), comment=payload.get("comment"), approved=True))


@admin_bp.route("/approvals/<approval_id>/reject", methods=["POST"])
@require_role("admin")
def reject(approval_id):
    payload = request.get_json(silent=True) or {}
    actor = getattr(g, "current_user", {}) or {}
    return _enveloped(get_admin_service().approve_item(approval_id, actor_id=actor.get("id") or actor.get("sub"), comment=payload.get("comment"), approved=False))


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
