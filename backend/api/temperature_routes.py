"""
Temperature & Facility Monitoring Routes
========================================
Handles temperature/humidity logging for specific devices and rooms.
Supports photo uploads for findings and optional reason for abnormalities.
"""

from flask import Blueprint, request, jsonify
import logging
from backend.database.supabase_client import get_client
from backend.middleware.security_middleware import require_auth
from backend.services.audit_service import current_actor_id, write_audit
from backend.services.monitoring_service import MonitoringService
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

    staff_id = data.staff_id or current_actor_id()
    data = TemperatureLogRequest(
        room_id=data.room_id,
        device_id=data.device_id,
        staff_id=staff_id,
        temperature=data.temperature,
        humidity=data.humidity,
        reason=data.reason,
        photo_url=data.photo_url,
        threshold=data.threshold,
    )

    try:
        body, status_code = MonitoringService(get_client(), audit_writer=write_audit).log_facility_data(data, request.files)
        return jsonify(body), status_code
    except Exception as e:
        logger.error("Logging error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500

@monitoring_bp.route("/api/monitoring/latest", methods=["GET"])
@monitoring_bp.route("/api/temperature/history", methods=["GET"])
@require_auth
def get_latest_logs():
    """Fetch latest logs for the dashboard."""
    return jsonify(MonitoringService(get_client()).latest_logs())

@monitoring_bp.route("/api/monitoring/stats", methods=["GET"])
@require_auth
def get_monitoring_stats():
    """Aggregate stats for analytics charts."""
    body, status_code = MonitoringService(get_client()).monitoring_stats()
    return jsonify(body), status_code
