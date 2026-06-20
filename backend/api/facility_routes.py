"""Facility management routes for rooms and devices."""

import logging

from flask import Blueprint, current_app, g, jsonify, request

from backend.database.supabase_client import get_client, supabase_error_response
from backend.middleware.security_middleware import require_auth, require_role
from backend.monitoring.facility_manager import is_uuid
from backend.services.audit_service import current_actor_id, write_audit
from backend.services.monitoring_schedule_service import MonitoringScheduleService
from backend.services.monitoring_service import MonitoringService
from backend.services.request_validation import TemperatureLogRequest, request_payload, validate_model
from backend.utils.cache import monitoring_schedule_cache

facility_bp = Blueprint("facility_bp", __name__)
logger = logging.getLogger("qc.routes.facility")


def _require_supabase():
    if current_app.config.get("TESTING"):
        return True, None
    sb = get_client()
    if not sb:
        body, status = supabase_error_response()
        return None, (jsonify(body), status)
    return sb, None


@facility_bp.route("/api/facility/structure", methods=["GET"])
@facility_bp.route("/api/admin/facility/structure", methods=["GET"])
@require_auth
def facility_structure():
    _, error = _require_supabase()
    if error:
        return error
    from backend.monitoring.facility_manager import get_monitoring_structure

    return jsonify({"success": True, "data": get_monitoring_structure(), "message": "OK"})


@facility_bp.route("/api/facility/monitoring/schedule/today", methods=["GET"])
@require_auth
def monitoring_schedule_today():
    sb = get_client()
    if not sb:
        body, status = supabase_error_response()
        return jsonify(body), status
    return jsonify(MonitoringScheduleService(sb).today())


@facility_bp.route("/api/facility/monitoring/submit", methods=["POST"])
@require_auth
def monitoring_schedule_submit():
    payload = request_payload()
    allow_duplicate = str(payload.pop("recheck", payload.pop("override", ""))).lower() in {"1", "true", "yes"}
    actor = getattr(g, "current_user", {}) or {}
    allow_duplicate = allow_duplicate or str(actor.get("role", "")).lower() == "admin"
    data = validate_model(TemperatureLogRequest, payload)
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

    sb = get_client()
    if not sb:
        body, status = supabase_error_response()
        return jsonify(body), status

    resolved = MonitoringScheduleService(sb).resolve_submission(
        data.slot_time,
        device_id=data.device_id,
        room_id=data.room_id,
        allow_duplicate=allow_duplicate,
    )
    if not resolved.get("success"):
        return jsonify(
            {
                "success": False,
                "message": resolved.get("message"),
                "schedule": resolved.get("schedule"),
            }
        ), int(resolved.get("status") or 400)

    scheduled_data = TemperatureLogRequest(
        room_id=data.room_id,
        device_id=data.device_id,
        staff_id=data.staff_id or current_actor_id(),
        temperature=data.temperature,
        humidity=data.humidity,
        reason=data.reason or data.notes,
        notes=data.notes,
        photo_url=data.photo_url,
        storage_path=data.storage_path,
        threshold=data.threshold,
        monitoring_date=resolved["monitoring_date"],
        slot_time=resolved["slot_time"],
        schedule_status=resolved["schedule_status"],
        submitted_at=resolved["submitted_at"],
        is_late=resolved["is_late"],
    )
    body, status = MonitoringService(sb, audit_writer=write_audit).log_facility_data(scheduled_data, request.files)
    if body.get("success"):
        monitoring_schedule_cache.clear()
        body["schedule"] = MonitoringScheduleService(sb).today()["data"]
    return jsonify(body), status


@facility_bp.route("/api/facility/rooms", methods=["GET", "POST"])
@facility_bp.route("/api/admin/facility/rooms", methods=["GET", "POST"])
@require_role("admin")
def facility_rooms():
    _, error = _require_supabase()
    if error:
        return error
    from backend.monitoring.facility_manager import add_room, list_rooms

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        room = add_room(data.get("name"), data.get("description", ""), data.get("is_active", True))
        if not room:
            return jsonify(
                {"success": False, "message": "Gagal menambah ruangan. Database belum terhubung atau data tidak valid."}
            ), 503
        write_audit("create", "facility_room", str(room.get("id")), after=room)
        return jsonify({"success": True, "data": room, "message": "Room created"}), 201
    return jsonify({"success": True, "data": list_rooms(), "message": "OK"})


@facility_bp.route("/api/facility/rooms/<room_id>", methods=["PATCH", "PUT", "DELETE"])
@facility_bp.route("/api/admin/facility/rooms/<room_id>", methods=["PATCH", "PUT", "DELETE"])
@require_role("admin")
def facility_room_detail(room_id):
    _, error = _require_supabase()
    if error:
        return error
    from backend.monitoring.facility_manager import delete_room, update_room

    if request.method in ("PATCH", "PUT"):
        room = update_room(room_id, request.get_json(silent=True) or {})
        if not room:
            return jsonify({"success": False, "message": "Gagal mengubah ruangan"}), 503
        write_audit("update", "facility_room", room_id, after=room)
        return jsonify({"success": True, "data": room, "message": "Room updated"})

    success = delete_room(room_id)
    write_audit("delete", "facility_room", room_id, after={"success": success})
    status = 200 if success else 503
    return jsonify(
        {
            "success": success,
            "data": {"id": room_id},
            "message": "Room deleted" if success else "Gagal menghapus ruangan",
        }
    ), status


@facility_bp.route("/api/facility/devices", methods=["GET", "POST"])
@facility_bp.route("/api/admin/facility/devices", methods=["GET", "POST"])
@require_role("admin")
def facility_devices():
    _, error = _require_supabase()
    if error:
        return error
    from backend.monitoring.facility_manager import add_device, list_devices

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        device = add_device(
            data.get("room_id"),
            data.get("name"),
            data.get("device_type") or data.get("type"),
            data.get("target_temperature", data.get("threshold", data.get("threshold_temp"))),
            data.get("min_temperature"),
            data.get("max_temperature"),
            data.get("is_active", True),
            data.get("description") or data.get("notes") or "",
        )
        if not device:
            return jsonify(
                {"success": False, "message": "Gagal menambah unit. Database belum terhubung atau data tidak valid."}
            ), 503
        write_audit("create", "facility_device", str(device.get("id")), after=device)
        return jsonify({"success": True, "data": device, "message": "Device created"}), 201
    return jsonify({"success": True, "data": list_devices(request.args.get("room_id")), "message": "OK"})


@facility_bp.route("/api/facility/devices/<device_id>", methods=["PATCH", "PUT", "DELETE"])
@facility_bp.route("/api/admin/facility/devices/<device_id>", methods=["PATCH", "PUT", "DELETE"])
@require_role("admin")
def facility_device_detail(device_id):
    _, error = _require_supabase()
    if error:
        return error
    from backend.monitoring.facility_manager import delete_device, update_device

    payload = request.get_json(silent=True) or {}
    logger.info(
        "Facility device request: method=%s device_id=%s payload=%s",
        request.method,
        device_id,
        payload,
    )

    if request.method in ("PATCH", "PUT"):
        device = update_device(device_id, payload)
        if not device:
            return jsonify({"success": False, "message": "Gagal mengubah unit"}), 503
        write_audit("update", "facility_device", device_id, after=device)
        return jsonify({"success": True, "data": device, "message": "Device updated"})

    result = delete_device(device_id)
    status = int(result.get("status") or (200 if result.get("success") else 500))
    logger.info(
        "Facility device delete result: device_id=%s status=%s result=%s",
        device_id,
        status,
        result,
    )
    if result.get("success"):
        write_audit("delete", "facility_device", device_id, after=result.get("data") or {"id": device_id})
    return jsonify(
        {
            "success": bool(result.get("success")),
            "data": result.get("data"),
            "error": result.get("error"),
            "error_code": result.get("error_code"),
            "message": "Device deleted" if result.get("success") else result.get("error"),
        }
    ), status
