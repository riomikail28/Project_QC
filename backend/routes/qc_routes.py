"""
QC Routes
=========
Blueprint for QC dashboard and inspection endpoints.
Provides realtime dashboard data and QC decision support.

Supabase tables: facility_logs, facility_alerts, production_batches
"""

from flask import Blueprint, request, jsonify
import logging

from backend.service.qc_engine import validate_temperature, calculate_health_score, determine_overall_status
from backend.service.batch_service import get_daily_summary
from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.routes.qc")

qc_bp = Blueprint("qc_bp", __name__)


# ---------------------------------------------------------------------------
# GET /api/qc/dashboard — Main QC decision dashboard
# ---------------------------------------------------------------------------
@qc_bp.route("/api/qc/dashboard", methods=["GET"])
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
            .select("temperature_c, is_normal, recorded_at, facility_rooms(name), facility_devices(name, type, threshold_temp)")
            .order("recorded_at", desc=True)
            .limit(100)
            .execute()
        ).data or []

        # Fetch open alerts
        alerts = (
            sb.table("facility_alerts")
            .select("*")
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

            temperature_rooms.append({
                "room": zone,
                "temperature": f"{temp}°C",
                "threshold": f"{threshold}°C",
                "unit_type": unit_type,
                "status": status,
            })

            # Track critical issues
            if status in ("FAIL", "WARNING"):
                critical_issues.append({
                    "title": zone,
                    "value": f"{temp}°C",
                    "status": status,
                    "unit_type": unit_type,
                })

        # Calculate health score
        health_score = calculate_health_score(total_checks, passed_checks, warning_checks)

        response.update({
            "health_score": health_score,
            "critical_issues": critical_issues,
            "temperature_rooms": temperature_rooms,
            "open_alerts": len(alerts),
            "recent_alerts": alerts[:5],
        })

    except Exception as e:
        logger.error("Dashboard data error: %s", e)

    return jsonify(response)


@qc_bp.route("/api/alerts", methods=["GET"])
def list_alerts():
    """List active facility alerts for the alerts page."""
    sb = get_client()
    if not sb:
        return jsonify([])
    try:
        status = request.args.get("status", "open")
        res = (
            sb.table("facility_alerts")
            .select("*")
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
        return jsonify({"success": True, "alert": res.data[0] if res.data else None})
    except Exception as e:
        logger.error("Resolve alert error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/qc/validate — Inline QC validation
# ---------------------------------------------------------------------------
@qc_bp.route("/api/qc/validate", methods=["POST"])
def validate_qc():
    """Validate a single QC parameter against SOP rules.

    Request JSON:
        unit_type (str): 'chiller', 'freezer', or 'ambient'
        temperature (float): Temperature reading in °C

    Returns:
        JSON with status and recommendation
    """
    data = request.json
    unit_type = data.get("unit_type", "chiller")
    temperature = float(data.get("temperature", 0))

    status = validate_temperature(unit_type, temperature)

    recommendations = {
        "PASS": "Suhu dalam batas aman. Lanjutkan proses.",
        "WARNING": "Suhu mendekati batas. Lakukan pengecekan unit pendingin.",
        "FAIL": "PERINGATAN: Suhu melebihi batas SOP. Segera lakukan tindakan korektif.",
    }

    return jsonify({
        "unit_type": unit_type,
        "temperature": temperature,
        "status": status,
        "recommendation": recommendations.get(status, ""),
    })


# ---------------------------------------------------------------------------
# POST /api/qc/findings — Report finding with photo
# ---------------------------------------------------------------------------
@qc_bp.route("/api/qc/findings", methods=["POST"])
def report_finding():
    """Report a field finding with optional photo and mandatory reason."""
    from backend.service.storage_service import upload_photo
    
    reason = request.form.get("reason")
    staff_id = request.form.get("staff_id")
    photo_file = request.files.get("photo")
    
    if not reason:
        return jsonify({"detail": "Reason is required"}), 400
        
    sb = get_client()
    photo_url = None
    
    if photo_file:
        try:
            photo_url = upload_photo(photo_file.read(), photo_file.filename)
        except Exception as e:
            logger.error("Photo upload failed: %s", e)

    if sb:
        try:
            res = sb.table("qc_findings").insert({
                "staff_id": staff_id,
                "reason": reason,
                "photo_url": photo_url
            }).execute()
            return jsonify(res.data[0] if res.data else {"success": True})
        except Exception as e:
            return jsonify({"detail": str(e)}), 500
            
    return jsonify({"success": True, "photo_url": photo_url})


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

    return jsonify({
        "status": "ok",
        "system": "QC Central Kitchen API v2.0.0",
        "database": db_status,
    })
