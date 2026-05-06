"""
Temperature & Facility Monitoring Routes
========================================
Handles temperature/humidity logging for specific devices and rooms.
Supports photo uploads for findings and optional reason for abnormalities.
"""

from flask import Blueprint, request, jsonify
import logging
import os
from backend.service.qc_engine import validate_temperature
from backend.service.alert_service import generate_temperature_alert, save_alert_to_db
from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.routes.monitoring")

monitoring_bp = Blueprint("monitoring_bp", __name__)

@monitoring_bp.route("/api/monitoring/log", methods=["POST"])
def log_facility_data():
    """Log data for a specific device or room.
    
    Request JSON:
        device_id (uuid)
        room_id (uuid)
        staff_id (uuid)
        temperature (float)
        humidity (float, optional)
        reason (str, optional)
        photo_url (str, optional)
    """
    data = request.json
    device_id = data.get("device_id")
    room_id = data.get("room_id")
    staff_id = data.get("staff_id")
    temperature = data.get("temperature")
    humidity = data.get("humidity")
    reason = data.get("reason")
    photo_url = data.get("photo_url")

    if not all([room_id, temperature is not None]):
        return jsonify({"success": False, "error": "Room and Temperature are required"}), 400

    sb = get_client()
    if not sb:
        return jsonify({"success": False, "error": "Database offline"}), 503

    try:
        # 1. Get device/room info for validation
        device_info = None
        unit_type = "ambient"
        room_name = "Unknown"
        
        room_res = sb.table("rooms").select("name").eq("id", room_id).execute()
        if room_res.data:
            room_name = room_res.data[0]["name"]

        if device_id:
            dev_res = sb.table("storage_units").select("*").eq("id", device_id).execute()
            if dev_res.data:
                device_info = dev_res.data[0]
                unit_type = device_info["unit_type"]

        # 2. Validate
        status = validate_temperature(unit_type, float(temperature))
        is_normal = (status == "PASS")

        # 3. Save Log
        log_payload = {
            "zone": room_name,
            "temperature_c": float(temperature),
            "threshold_c": float(device_info["unit_type"] if device_info else 25.0), # Temporary mapping
            "is_normal": is_normal,
            "recorder_id": staff_id,
            "notes": reason
        }
        
        # We need to handle the case where threshold_c is numeric but we might not have it
        if device_info and "threshold_temp" in device_info:
            log_payload["threshold_c"] = float(device_info["threshold_temp"])
        elif "threshold" in data:
            log_payload["threshold_c"] = float(data["threshold"])

        res = sb.table("facility_logs").insert(log_payload).execute()
        log_data = res.data[0] if res.data else None

        # 4. Generate Alert if abnormal
        alert = None
        if not is_normal:
            alert = generate_temperature_alert(room_name, unit_type, float(temperature), status)
            if log_data:
                save_alert_to_db(
                    zone=room_name,
                    temperature=float(temperature),
                    threshold=device_info["threshold_temp"] if device_info else 25.0,
                    log_id=log_data["id"]
                )

        return jsonify({
            "success": True,
            "status": status,
            "alert": alert,
            "log_id": log_data["id"] if log_data else None
        })

    except Exception as e:
        logger.error("Logging error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500

@monitoring_bp.route("/api/monitoring/latest", methods=["GET"])
def get_latest_logs():
    """Fetch latest logs for the dashboard."""
    sb = get_client()
    if not sb: return jsonify([])
    try:
        res = (sb.table("facility_logs")
               .select("*, rooms(name), storage_units(unit_name)")
               .order("recorded_at", desc=True)
               .limit(50)
               .execute())
        return jsonify(res.data or [])
    except Exception as e:
        logger.error("Fetch logs error: %s", e)
        return jsonify([])

@monitoring_bp.route("/api/monitoring/stats", methods=["GET"])
def get_monitoring_stats():
    """Aggregate stats for analytics charts."""
    sb = get_client()
    if not sb: return jsonify({})
    try:
        # Simple daily count for now
        res = sb.table("facility_logs").select("is_normal, recorded_at").execute()
        # In a real app, we would do SQL aggregation here
        return jsonify(res.data or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500