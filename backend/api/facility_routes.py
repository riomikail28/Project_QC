"""Facility management routes for rooms and devices."""

from flask import Blueprint, g, jsonify, request

from backend.middleware.security_middleware import require_auth, require_role
from backend.services.audit_service import write_audit

facility_bp = Blueprint("facility_bp", __name__)


@facility_bp.route("/api/facility/structure", methods=["GET"])
@facility_bp.route("/api/admin/facility/structure", methods=["GET"])
@require_auth
def facility_structure():
    from backend.monitoring.facility_manager import get_monitoring_structure

    return jsonify(get_monitoring_structure())


@facility_bp.route("/api/facility/rooms", methods=["GET", "POST"])
@facility_bp.route("/api/admin/facility/rooms", methods=["GET", "POST"])
@require_role("admin")
def facility_rooms():
    from backend.monitoring.facility_manager import add_room, list_rooms

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        room = add_room(data.get("name"), data.get("description", ""), data.get("is_active", True))
        if not room:
            return jsonify({"success": False, "message": "Gagal menambah ruangan. Database belum terhubung atau data tidak valid."}), 503
        write_audit("create", "facility_room", str(room.get("id")), after=room)
        return jsonify({"success": True, "data": room, "message": "Room created"}), 201
    return jsonify({"success": True, "data": list_rooms(), "message": "OK"})


@facility_bp.route("/api/facility/rooms/<room_id>", methods=["PATCH", "PUT", "DELETE"])
@facility_bp.route("/api/admin/facility/rooms/<room_id>", methods=["PATCH", "PUT", "DELETE"])
@require_role("admin")
def facility_room_detail(room_id):
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
    return jsonify({"success": success, "data": {"id": room_id}, "message": "Room deleted" if success else "Gagal menghapus ruangan"}), status


@facility_bp.route("/api/facility/devices", methods=["GET", "POST"])
@facility_bp.route("/api/admin/facility/devices", methods=["GET", "POST"])
@require_role("admin")
def facility_devices():
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
        )
        if not device:
            return jsonify({"success": False, "message": "Gagal menambah unit. Database belum terhubung atau data tidak valid."}), 503
        write_audit("create", "facility_device", str(device.get("id")), after=device)
        return jsonify({"success": True, "data": device, "message": "Device created"}), 201
    return jsonify({"success": True, "data": list_devices(request.args.get("room_id")), "message": "OK"})


@facility_bp.route("/api/facility/devices/<device_id>", methods=["PATCH", "PUT", "DELETE"])
@facility_bp.route("/api/admin/facility/devices/<device_id>", methods=["PATCH", "PUT", "DELETE"])
@require_role("admin")
def facility_device_detail(device_id):
    from backend.monitoring.facility_manager import delete_device, update_device

    if request.method in ("PATCH", "PUT"):
        device = update_device(device_id, request.get_json(silent=True) or {})
        if not device:
            return jsonify({"success": False, "message": "Gagal mengubah unit"}), 503
        write_audit("update", "facility_device", device_id, after=device)
        return jsonify({"success": True, "data": device, "message": "Device updated"})

    success = delete_device(device_id)
    write_audit("delete", "facility_device", device_id, after={"success": success})
    status = 200 if success else 503
    return jsonify({"success": success, "data": {"id": device_id}, "message": "Device deleted" if success else "Gagal menghapus unit"}), status
