"""
Temperature & Facility Monitoring Routes
========================================
Handles temperature/humidity logging for specific devices and rooms.
Supports photo uploads for findings and optional reason for abnormalities.
"""

from flask import Blueprint, request, jsonify
import logging
import os
from backend.services.qc_engine import validate_temperature
from backend.services.alert_service import generate_temperature_alert, save_alert_to_db
from backend.database.supabase_client import get_client
from backend.services.storage_service import upload_photo
from backend.middleware.security_middleware import require_auth
from backend.services.audit_service import current_actor_id, write_audit
from backend.services.request_validation import TemperatureLogRequest, request_payload, validate_model

logger = logging.getLogger("qc.routes.monitoring")

monitoring_bp = Blueprint("monitoring_bp", __name__)

@monitoring_bp.route("/api/monitoring/log", methods=["POST"])
@require_auth
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
    data = validate_model(TemperatureLogRequest, request_payload())

    device_id = data.device_id
    room_id = data.room_id
    staff_id = data.staff_id or current_actor_id()
    temperature = data.temperature
    humidity = data.humidity
    reason = data.reason
    photo_url = data.photo_url
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

        # 3. Save Log (Hybrid: File or URL)
        photo_urls = []
        
        # Check for pre-uploaded URL in body
        if data.get("photo_url"):
            photo_urls.append(data.get("photo_url"))
            
        # Check for files
        photo_files = request.files.getlist("photo")
        for p_file in photo_files:
            if p_file:
                p_url = upload_photo(p_file.read(), p_file.filename, staff_id=staff_id)
                photo_urls.append(p_url)
        
        photo_url = ";".join(photo_urls) if photo_urls else None

        threshold = float(device_info.get("threshold_temp", 25.0)) if device_info else float(data.threshold or 25.0)

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
        write_audit("create", "facility_log", str(log_data.get("id")) if log_data else None, after=log_data or log_payload)

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
@require_auth
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
@require_auth
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
