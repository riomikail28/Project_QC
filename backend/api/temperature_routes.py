"""
Temperature & Facility Monitoring Routes
========================================
Handles temperature/humidity logging for specific devices and rooms.
Supports photo uploads for findings and optional reason for abnormalities.
"""

import logging

from flask import Blueprint, jsonify, request

from backend.database.supabase_client import get_client, get_last_db_error, supabase_error_response
from backend.middleware.security_middleware import require_auth
from backend.monitoring.facility_manager import is_uuid
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
        storage_path (str, optional)
    """
    data = validate_model(TemperatureLogRequest, request_payload())
    if not is_uuid(data.room_id):
        return jsonify(
            {
                "success": False,
                "error": "Invalid room_id",
                "error_code": "INVALID_ROOM_ID",
                "message": f"room_id must be a valid UUID. Received synthetic id: {data.room_id}",
            }
        ), 400
    if data.device_id and not is_uuid(data.device_id):
        return jsonify(
            {
                "success": False,
                "error": "Invalid device_id",
                "error_code": "INVALID_DEVICE_ID",
                "message": f"device_id must be a valid UUID. Received synthetic id: {data.device_id}",
            }
        ), 400

    staff_id = data.staff_id or current_actor_id()
    data = TemperatureLogRequest(
        room_id=data.room_id,
        device_id=data.device_id,
        staff_id=staff_id,
        temperature=data.temperature,
        humidity=data.humidity,
        reason=data.reason or data.notes,
        notes=data.notes,
        photo_url=data.photo_url,
        storage_path=data.storage_path,
        threshold=data.threshold,
        monitoring_date=data.monitoring_date,
        slot_time=data.slot_time,
        schedule_status=data.schedule_status,
        submitted_at=data.submitted_at,
        is_late=data.is_late,
    )

    try:
        sb = get_client()
        if not sb:
            body, status_code = supabase_error_response()
            return jsonify(body), status_code
        body, status_code = MonitoringService(sb, audit_writer=write_audit).log_facility_data(data, request.files)
        return jsonify(body), status_code
    except Exception as e:
        logger.exception("Logging error")
        return jsonify(
            {
                "success": False,
                "error": "Monitoring log failed",
                "detail": str(e),
                "db_detail": get_last_db_error(),
            }
        ), 500


@monitoring_bp.route("/api/monitoring/latest", methods=["GET"])
@monitoring_bp.route("/api/temperature/history", methods=["GET"])
@require_auth
def get_latest_logs():
    """Fetch latest logs for the dashboard."""
    sb = get_client()
    if not sb:
        body, status_code = supabase_error_response()
        return jsonify(body), status_code
    return jsonify(MonitoringService(sb).latest_logs())


@monitoring_bp.route("/api/monitoring/stats", methods=["GET"])
@require_auth
def get_monitoring_stats():
    """Aggregate stats for analytics charts."""
    sb = get_client()
    if not sb:
        body, status_code = supabase_error_response()
        return jsonify(body), status_code
    body, status_code = MonitoringService(sb).monitoring_stats()
    return jsonify(body), status_code
