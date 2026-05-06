"""
Temperature Routes
==================
Blueprint for facility temperature monitoring endpoints.
Handles temperature logging, validation, and alert generation.

Supabase tables: facility_logs, facility_alerts
"""

from flask import Blueprint, request, jsonify
import logging

from backend.service.qc_engine import validate_temperature
from backend.service.alert_service import generate_temperature_alert, save_alert_to_db
from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.routes.temperature")

temperature_bp = Blueprint("temperature_bp", __name__)


# ---------------------------------------------------------------------------
# POST /api/temperature — Log a temperature reading
# ---------------------------------------------------------------------------
@temperature_bp.route("/api/temperature", methods=["POST"])
def create_temperature_log():
    """Log a temperature reading and return validation result with alert.

    Request JSON:
        room_name (str): Zone/room name
        unit_type (str): 'chiller', 'freezer', or 'ambient'
        temperature (float): Temperature reading in °C

    Returns:
        JSON with status, alert info, and validation result
    """
    data = request.json

    # Validate input
    room_name = data.get("room_name")
    unit_type = data.get("unit_type")
    temperature = data.get("temperature")

    if not all([room_name, unit_type, temperature is not None]):
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    temperature = float(temperature)

    # Run QC validation
    status = validate_temperature(unit_type, temperature)

    # Generate alert
    alert = generate_temperature_alert(room_name, unit_type, temperature, status)

    # Determine threshold for the unit type
    threshold = _get_threshold(unit_type)

    # Persist to Supabase
    sb = get_client()
    log_id = None
    if sb:
        try:
            res = sb.table("facility_logs").insert({
                "zone": room_name,
                "temperature_c": temperature,
                "threshold_c": threshold,
                "is_normal": status == "PASS",
            }).execute()

            if res.data:
                log_id = res.data[0].get("id")
        except Exception as e:
            logger.error("Failed to persist temperature log: %s", e)

    # Save alert if status is not PASS
    if status != "PASS" and log_id:
        save_alert_to_db(
            zone=room_name,
            temperature=temperature,
            threshold=threshold,
            log_id=log_id,
        )

    return jsonify({
        "success": True,
        "data": {
            "room_name": room_name,
            "unit_type": unit_type,
            "temperature": temperature,
            "threshold": threshold,
            "status": status,
            "alert": alert,
        }
    })


# ---------------------------------------------------------------------------
# GET /api/temperature/latest — Get latest readings per zone
# ---------------------------------------------------------------------------
@temperature_bp.route("/api/temperature/latest", methods=["GET"])
def get_latest_temperatures():
    """Fetch the most recent temperature reading per zone.

    Returns:
        JSON list of latest readings
    """
    sb = get_client()
    if not sb:
        return jsonify([])

    try:
        res = (
            sb.table("facility_logs")
            .select("zone, temperature_c, threshold_c, is_normal, recorded_at")
            .order("recorded_at", desc=True)
            .limit(100)
            .execute()
        )
        # Deduplicate: keep only latest per zone
        latest = {}
        for row in (res.data or []):
            latest.setdefault(row["zone"], row)

        return jsonify(list(latest.values()))
    except Exception as e:
        logger.error("Failed to fetch latest temperatures: %s", e)
        return jsonify([])


# ---------------------------------------------------------------------------
# GET /api/temperature/history — Get temperature history for a zone
# ---------------------------------------------------------------------------
@temperature_bp.route("/api/temperature/history", methods=["GET"])
def get_temperature_history():
    """Fetch temperature history for a specific zone.

    Query params:
        zone (str): Zone name to filter by
        limit (int): Max number of records (default 50)

    Returns:
        JSON list of historical readings
    """
    zone = request.args.get("zone")
    limit = int(request.args.get("limit", 50))

    sb = get_client()
    if not sb:
        return jsonify([])

    try:
        query = (
            sb.table("facility_logs")
            .select("zone, temperature_c, threshold_c, is_normal, recorded_at")
            .order("recorded_at", desc=True)
            .limit(limit)
        )
        if zone:
            query = query.eq("zone", zone)

        res = query.execute()
        return jsonify(res.data or [])
    except Exception as e:
        logger.error("Failed to fetch temperature history: %s", e)
        return jsonify([])


# ---------------------------------------------------------------------------
# GET /api/alerts — Get open alerts
# ---------------------------------------------------------------------------
@temperature_bp.route("/api/alerts", methods=["GET"])
def get_open_alerts():
    """Fetch all open facility alerts.

    Returns:
        JSON list of open alerts
    """
    sb = get_client()
    if not sb:
        return jsonify([])

    try:
        res = (
            sb.table("facility_alerts")
            .select("*")
            .eq("status", "open")
            .order("created_at", desc=True)
            .execute()
        )
        return jsonify(res.data or [])
    except Exception as e:
        logger.error("Failed to fetch alerts: %s", e)
        return jsonify([])


# ---------------------------------------------------------------------------
# POST /api/alerts/<alert_id>/resolve — Resolve an alert
# ---------------------------------------------------------------------------
@temperature_bp.route("/api/alerts/<alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    """Mark an alert as resolved.

    Returns:
        JSON with updated alert status
    """
    sb = get_client()
    if not sb:
        return jsonify({"error": "Database offline"}), 503

    try:
        res = (
            sb.table("facility_alerts")
            .update({"status": "resolved"})
            .eq("id", alert_id)
            .execute()
        )
        return jsonify({"success": True, "alert_id": alert_id, "status": "resolved"})
    except Exception as e:
        logger.error("Failed to resolve alert: %s", e)
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _get_threshold(unit_type: str) -> float:
    """Return the SOP threshold for a given unit type."""
    thresholds = {
        "chiller": 5.0,
        "freezer": -18.0,
        "ambient": 25.0,
    }
    return thresholds.get(unit_type, 5.0)