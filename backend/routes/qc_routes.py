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
            .select("zone, temperature_c, threshold_c, is_normal, recorded_at")
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
            latest_by_zone.setdefault(row["zone"], row)

        # Build temperature rooms data
        temperature_rooms = []
        critical_issues = []
        total_checks = 0
        passed_checks = 0
        warning_checks = 0

        for zone, reading in latest_by_zone.items():
            temp = reading["temperature_c"]
            threshold = reading["threshold_c"]
            is_normal = reading.get("is_normal", True)

            # Determine unit type from threshold
            if threshold <= -10:
                unit_type = "freezer"
            elif threshold <= 10:
                unit_type = "chiller"
            else:
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