"""
QC Routes
=========
Blueprint for QC dashboard and inspection endpoints.
Provides realtime dashboard data and QC decision support.

Supabase tables: facility_logs, facility_alerts, production_batches
"""

import logging

from flask import Blueprint, g, jsonify, request

from backend.database.supabase_client import get_client
from backend.middleware.security_middleware import require_auth
from backend.services.audit_service import current_actor_id, write_audit
from backend.services.qc_engine import calculate_health_score, validate_temperature
from backend.services.request_validation import QCValidateRequest, validate_model

logger = logging.getLogger("qc.routes.qc")

qc_bp = Blueprint("qc_bp", __name__)


def _qc_report_view(row):
    if not row:
        return None
    staff = row.get("staff_name") or row.get("inspector_name") or row.get("staff_id") or "-"
    batch = row.get("batch_code") or row.get("batch_id") or "-"
    status = row.get("status") or row.get("final_qc_status") or "-"
    qc_type = row.get("qc_stage") or row.get("ccp_stage") or "-"
    started_at = row.get("started_at") or row.get("created_at")
    completed_at = row.get("completed_at") or row.get("updated_at") or row.get("created_at")
    return {
        "id": row.get("id"),
        "batch_id": row.get("batch_id"),
        "batch_code": row.get("batch_code"),
        "batch": batch,
        "product_name": row.get("product_name"),
        "staff": staff,
        "staff_id": row.get("staff_id"),
        "start_time": started_at,
        "started_at": started_at,
        "qc_type": qc_type,
        "qc_stage": qc_type,
        "temperature": row.get("temperature"),
        "status": status,
        "photo_url": row.get("photo_url")
        or row.get("product_photo_url")
        or row.get("cooking_photo_url")
        or row.get("barcode_photo_url")
        or row.get("temperature_photo_url"),
        "created_at": row.get("created_at"),
        "completed_at": completed_at,
        "notes": row.get("notes"),
        "inspection_round": row.get("inspection_round") or 1,
        "parent_inspection": row.get("parent_inspection"),
        "is_active": bool(row.get("is_active")),
    }


def _fetch_qc_reports(filters, limit=20):
    sb = get_client()
    if not sb:
        return []
    qc_cols = (
        "id,batch_id,batch_code,status,final_qc_status,qc_stage,ccp_stage,started_at,created_at,completed_at,"
        "updated_at,photo_url,product_photo_url,cooking_photo_url,barcode_photo_url,temperature_photo_url,"
        "notes,inspection_round,parent_inspection,is_active,product_name,staff_id,staff_name,inspector_name,temperature"
    )
    query = sb.table("qc_reports").select(qc_cols)
    for field, value in filters:
        query = query.eq(field, value)
    return query.order("created_at", desc=True).limit(limit).execute().data or []


def _reports_for_batch(batch):
    rows = _fetch_qc_reports([("batch_id", batch)], limit=50)
    if not rows:
        rows = _fetch_qc_reports([("batch_code", batch)], limit=50)
    return rows


def _active_for_batch(batch):
    if batch:
        rows = _fetch_qc_reports([("batch_id", batch), ("is_active", True)], limit=1)
        if not rows:
            rows = _fetch_qc_reports([("batch_code", batch), ("is_active", True)], limit=1)
        return rows[0] if rows else None
    return (_fetch_qc_reports([("is_active", True)], limit=20) or [None])[0]


# ---------------------------------------------------------------------------
# GET /api/qc/dashboard — Main QC decision dashboard
# ---------------------------------------------------------------------------
@qc_bp.route("/api/qc/dashboard", methods=["GET"])
@require_auth
def dashboard():
    """Return QC decision dashboard data.

    Aggregates health score, critical issues, temperature readings,
    and recent alerts into a single dashboard payload.

    Returns:
        JSON with health_score, critical_issues, temperature_rooms, alerts
    """
    sb = get_client()

    # Default response structure
    response = {
        "health_score": 0,
        "critical_issues": [],
        "temperature_rooms": [],
        "open_alerts": 0,
        "recent_alerts": [],
    }

    if not sb:
        return jsonify(response)

    try:
        # Fetch latest facility logs
        logs = (
            sb.table("facility_logs")
            .select(
                "temperature_c, is_normal, recorded_at, facility_rooms(name), facility_devices(name, type, threshold_temp)"
            )
            .order("recorded_at", desc=True)
            .limit(100)
            .execute()
        ).data or []

        # Fetch open alerts
        alerts = (
            sb.table("facility_alerts")
            .select(
                "id,zone,temperature_c,threshold_c,deviation_c,status,log_id,device_id,created_at,resolved_at,notes,resolved_by"
            )
            .eq("status", "open")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        ).data or []

        # Deduplicate: latest reading per zone
        latest_by_zone = {}
        for row in logs:
            room_name = (row.get("facility_rooms") or {}).get("name") or "Unknown"
            device_name = (row.get("facility_devices") or {}).get("name") or "Suhu Ruangan"
            latest_by_zone.setdefault(f"{room_name} - {device_name}", row)

        # Build temperature rooms data
        temperature_rooms = []
        critical_issues = []
        total_checks = 0
        passed_checks = 0
        warning_checks = 0

        for zone, reading in latest_by_zone.items():
            temp = reading["temperature_c"]
            device = reading.get("facility_devices") or {}
            threshold = device.get("threshold_temp", 25.0)
            is_normal = reading.get("is_normal", True)

            unit_type = device.get("type") or "ambient"
            if unit_type == "undercounter":
                unit_type = "chiller"
            elif unit_type == "room_temp":
                unit_type = "ambient"

            status = validate_temperature(unit_type, temp)
            total_checks += 1

            if status == "PASS":
                passed_checks += 1
            elif status == "WARNING":
                warning_checks += 1

            temperature_rooms.append(
                {
                    "room": zone,
                    "temperature": f"{temp}°C",
                    "threshold": f"{threshold}°C",
                    "unit_type": unit_type,
                    "status": status,
                }
            )

            # Track critical issues
            if status in ("FAIL", "WARNING"):
                critical_issues.append(
                    {
                        "title": zone,
                        "value": f"{temp}°C",
                        "status": status,
                        "unit_type": unit_type,
                    }
                )

        # Calculate health score
        health_score = calculate_health_score(total_checks, passed_checks, warning_checks)

        response.update(
            {
                "health_score": health_score,
                "critical_issues": critical_issues,
                "temperature_rooms": temperature_rooms,
                "open_alerts": len(alerts),
                "recent_alerts": alerts[:5],
            }
        )

    except Exception as e:
        logger.error("Dashboard data error: %s", e)

    return jsonify(response)


@qc_bp.route("/api/qc/active", methods=["GET"])
@require_auth
def active_qc():
    """Return active QC lock for a batch or the latest active QC."""
    try:
        batch = (
            request.args.get("batch") or request.args.get("batch_id") or request.args.get("batch_code") or ""
        ).strip()
        active = _active_for_batch(batch)
        return jsonify({"success": True, "data": {"active": _qc_report_view(active)}})
    except Exception as exc:
        logger.warning("Active QC lookup failed: %s", exc)
        return jsonify({"success": False, "message": "Gagal memuat QC aktif"}), 500


@qc_bp.route("/api/qc/history/<batch>", methods=["GET"])
@require_auth
def qc_history(batch):
    """Return QC inspection history for a batch id or batch code."""
    try:
        rows = _reports_for_batch(batch)
        history = [_qc_report_view(row) for row in rows]
        active = next((item for item in history if item.get("is_active")), None)
        completed = [item for item in history if not item.get("is_active")]
        return jsonify(
            {
                "success": True,
                "data": {
                    "batch": batch,
                    "active": active,
                    "latest": completed[0] if completed else (history[0] if history else None),
                    "history": history,
                },
            }
        )
    except Exception as exc:
        logger.warning("QC history lookup failed for %s: %s", batch, exc)
        return jsonify({"success": False, "message": "Gagal memuat riwayat QC"}), 500


@qc_bp.route("/api/alerts", methods=["GET"])
@require_auth
def list_alerts():
    """List active facility alerts for the alerts page."""
    sb = get_client()
    if not sb:
        return jsonify([])
    try:
        status = request.args.get("status", "open")
        res = (
            sb.table("facility_alerts")
            .select(
                "id,zone,temperature_c,threshold_c,deviation_c,status,log_id,device_id,created_at,resolved_at,notes,resolved_by"
            )
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return jsonify(res.data or [])
    except Exception as e:
        logger.error("Alerts list error: %s", e)
        return jsonify([])


@qc_bp.route("/api/alerts/<alert_id>/resolve", methods=["POST"])
@require_auth
def resolve_alert(alert_id):
    """Mark an alert as resolved."""
    sb = get_client()
    if not sb:
        return jsonify({"success": False, "error": "Database offline"}), 503
    try:
        payload = request.get_json(silent=True) or {}
        update = {
            "status": "resolved",
            "resolved_at": payload.get("resolved_at"),
            "corrective_action": payload.get("corrective_action", "Resolved from admin panel"),
        }
        update = {key: value for key, value in update.items() if value is not None}
        res = sb.table("facility_alerts").update(update).eq("id", alert_id).execute()
        write_audit("resolve", "facility_alert", alert_id, after=update)
        return jsonify({"success": True, "alert": res.data[0] if res.data else None})
    except Exception as e:
        logger.error("Resolve alert error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/qc/validate — Inline QC validation
# ---------------------------------------------------------------------------
@qc_bp.route("/api/qc/validate", methods=["POST"])
@require_auth
def validate_qc():
    """Validate a single QC parameter against SOP rules.

    Request JSON:
        unit_type (str): 'chiller', 'freezer', or 'ambient'
        temperature (float): Temperature reading in °C

    Returns:
        JSON with status and recommendation
    """
    data = validate_model(QCValidateRequest, request.get_json(silent=True) or {})
    unit_type = data.unit_type
    if unit_type == "undercounter":
        unit_type = "chiller"
    elif unit_type == "room_temp":
        unit_type = "ambient"
    temperature = data.temperature

    status = validate_temperature(unit_type, temperature)

    recommendations = {
        "PASS": "Suhu dalam batas aman. Lanjutkan proses.",
        "WARNING": "Suhu mendekati batas. Lakukan pengecekan unit pendingin.",
        "FAIL": "PERINGATAN: Suhu melebihi batas SOP. Segera lakukan tindakan korektif.",
    }

    return jsonify(
        {
            "unit_type": unit_type,
            "temperature": temperature,
            "status": status,
            "recommendation": recommendations.get(status, ""),
        }
    )


# ---------------------------------------------------------------------------
# POST /api/qc/findings — Report finding with photo
# ---------------------------------------------------------------------------
@qc_bp.route("/api/qc/findings", methods=["POST"])
@require_auth
def report_finding():
    """Report a field finding with optional photo and mandatory reason."""
    # Use DI-resolved service when available; otherwise construct a conservative fallback
    from backend.core.di import resolve
    from backend.repositories.qc_repository import QCRepository
    from backend.services.qc_service import QCService

    body = request.get_json(silent=True) or {}
    reason = request.form.get("reason") or body.get("reason")
    actor = getattr(g, "current_user", {}) or {}
    staff_id = actor.get("id") or actor.get("sub") or current_actor_id()
    staff_name = (
        actor.get("full_name") or actor.get("name") or actor.get("username") or actor.get("email") or "Unknown Staff"
    )
    photo_url = request.form.get("photo_url") or body.get("photo_url")
    storage_path = request.form.get("storage_path") or body.get("storage_path")
    photo_files = request.files.getlist("photo")

    if not reason:
        return jsonify({"detail": "Reason is required"}), 400

    # Try resolve a pre-registered service from DI container
    qc_service = resolve("qc_service")

    if qc_service is None:
        # Fallback: create minimal dependencies
        sb = get_client()
        repo = QCRepository(sb)

        # Storage wrapper around existing upload helper if available
        storage = None
        try:
            from backend.services.storage_service import delete_photo as _delete_fn
            from backend.services.storage_service import upload_file_storage as _upload_file_fn
            from backend.services.storage_service import upload_photo as _upload_fn

            class _StorageWrap:
                def upload_photo(self, data, filename):
                    return _upload_fn(data, filename)

                def upload_file_storage(self, file_storage, staff_id="system", category=None, related_id=None):
                    return _upload_file_fn(file_storage, staff_id=staff_id, category=category, related_id=related_id)

                def delete_photo(self, storage_path):
                    return _delete_fn(storage_path)

            storage = _StorageWrap()
        except Exception:
            storage = None

        # Audit module provides write_audit
        try:
            from backend.services import audit_service as audit_mod
        except Exception:
            audit_mod = None
        qc_service = QCService(repo, storage_service=storage, audit_service=audit_mod, external_sync=None)

    try:
        result = qc_service.report_finding(
            staff_id,
            reason,
            photo_files,
            photo_url=photo_url,
            storage_path=storage_path,
            staff_name=staff_name,
        )
        return jsonify(result)
    except Exception as e:
        logger.exception("Report finding failed: %s", e)
        return jsonify({"detail": str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/qc/health — System health check
# ---------------------------------------------------------------------------
@qc_bp.route("/api/qc/health", methods=["GET"])
def health_check():
    """API health check endpoint.

    Returns:
        JSON with system status and database connectivity
    """
    sb = get_client()
    db_status = "connected" if sb else "offline"

    return jsonify(
        {
            "status": "ok",
            "system": "QC Central Kitchen API v2.0.0",
            "database": db_status,
        }
    )
