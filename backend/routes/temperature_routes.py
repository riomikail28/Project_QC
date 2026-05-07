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
from backend.service.storage_service import upload_photo

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
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        data = request.form
    else:
        data = request.get_json(silent=True) or {}

    device_id = data.get("device_id")
    room_id = data.get("room_id")
    staff_id = data.get("staff_id")
    temperature = data.get("temperature")
    humidity = data.get("humidity")
    reason = data.get("reason")
    photo_url = data.get("photo_url")
    photo_file = request.files.get("photo")

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
        
        room_res = sb.table("facility_rooms").select("name").eq("id", room_id).execute()
        if room_res.data:
            room_name = room_res.data[0]["name"]

        if device_id:
            dev_res = sb.table("facility_devices").select("*").eq("id", device_id).execute()
            if dev_res.data:
                device_info = dev_res.data[0]
                unit_type = device_info["type"]
                if unit_type == "undercounter":
                    unit_type = "chiller"
                elif unit_type == "room_temp":
                    unit_type = "ambient"

        # 2. Validate
        status = validate_temperature(unit_type, float(temperature))
        is_normal = (status == "PASS")

        # 3. Save Log
        if photo_file:
            photo_url = upload_photo(photo_file.read(), photo_file.filename)

        threshold = float(device_info.get("threshold_temp", 25.0)) if device_info else float(data.get("threshold", 25.0))

        log_payload = {
            "device_id": device_id or None,
            "room_id": room_id,
            "temperature_c": float(temperature),
            "humidity_rh": float(humidity) if humidity not in (None, "") else None,
            "is_normal": is_normal,
            "staff_id": staff_id or None,
            "reason": reason,
            "photo_url": photo_url,
        }

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
                    threshold=threshold,
                    log_id=log_data["id"],
                    device_id=device_id,
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
@monitoring_bp.route("/api/temperature/history", methods=["GET"])
def get_latest_logs():
    """Fetch latest logs for the dashboard."""
    sb = get_client()
    if not sb: return jsonify([])
    try:
        res = (sb.table("facility_logs")
               .select("*, facility_rooms(name), facility_devices(name, type, threshold_temp)")
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
        res = sb.table("facility_logs").select("is_normal, recorded_at, temperature_c, facility_rooms(name)").execute()
        # In a real app, we would do SQL aggregation here
        return jsonify(res.data or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
