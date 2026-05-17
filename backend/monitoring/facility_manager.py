"""
Facility Management Skill
=========================
Handles CRUD operations for Rooms and Devices (Chillers/Freezers).
Used by Admin for kitchen configuration.
"""

import logging
from uuid import UUID
from datetime import datetime, timezone
from backend.database.supabase_client import direct_db_query, get_client

logger = logging.getLogger("qc.facility")

DEFAULT_MONITORING_ROOMS = ("PPIC", "Grouper", "Pack Basah", "Pack Kering", "Ruang Kopi", "Kitchen")
DEFAULT_MONITORING_UNITS = (
    ("room_temp", "Suhu Ruangan", 25.0),
    ("chiller", "Chiller", 5.0),
    ("freezer", "Freezer", -18.0),
)

def list_rooms():
    """List all monitoring rooms."""
    sb = get_client()
    try:
        if not sb:
            return direct_db_query("facility_rooms", "GET", None, "select=*&order=name.asc")
        res = sb.table("facility_rooms").select("*").order("name").execute()
        return res.data or []
    except Exception as e:
        logger.error("List rooms error: %s", e)
        return []

def add_room(name: str, description: str = "", is_active: bool = True):
    """Add a new monitoring room."""
    sb = get_client()
    try:
        clean_name = str(name or "").strip()
        if not clean_name:
            return None
        payload = {
            "name": clean_name,
            "slug": _slug(clean_name),
            "description": description or "",
            "is_active": bool(is_active),
        }
        if not sb:
            rows = direct_db_query("facility_rooms", "POST", payload)
            return rows[0] if rows else None
        res = sb.table("facility_rooms").insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("Add room error: %s", e)
        return None

def delete_room(room_id: str):
    """Delete a room and all its devices."""
    if _is_synthetic_id(room_id):
        logger.info("Ignoring delete for synthetic room id: %s", room_id)
        return True
    try:
        sb = get_client()
        if not sb:
            direct_db_query("facility_rooms", "DELETE", None, f"id=eq.{room_id}")
            return True
        sb.table("facility_rooms").delete().eq("id", room_id).execute()
        return True
    except Exception as e:
        logger.error("Delete room error: %s", e)
        return False

def list_devices(room_id: str = None):
    """List devices, optionally filtered by room."""
    sb = get_client()
    try:
        if not sb:
            filters = "select=*,facility_rooms(name)&order=name.asc"
            if room_id:
                filters = f"room_id=eq.{room_id}&{filters}"
            return direct_db_query("facility_devices", "GET", None, filters)
        query = sb.table("facility_devices").select("*, facility_rooms(name)")
        if room_id:
            query = query.eq("room_id", room_id)
        res = query.order("name").execute()
        return res.data or []
    except Exception as e:
        logger.error("List devices error: %s", e)
        return []

def add_device(
    room_id: str,
    name: str,
    device_type: str,
    threshold: float = None,
    min_temperature: float = None,
    max_temperature: float = None,
    is_active: bool = True,
):
    """Add a new device (chiller/freezer/etc) to a room."""
    sb = get_client()
    try:
        clean_name = str(name or "").strip()
        normalized_type = _normalize_device_type(device_type)
        if not room_id or not clean_name or not normalized_type:
            return None
        target = _coerce_float(threshold, _default_threshold(normalized_type))
        payload = {
            "room_id": room_id,
            "name": clean_name,
            "slug": _slug(clean_name),
            "device_type": normalized_type,
            "type": normalized_type,
            "target_temperature": target,
            "threshold_temp": target,
            "min_temperature": _coerce_float(min_temperature, None),
            "max_temperature": _coerce_float(max_temperature, None),
            "is_default": False,
            "is_active": bool(is_active),
        }
        if not sb:
            rows = direct_db_query("facility_devices", "POST", payload)
            return rows[0] if rows else None
        res = sb.table("facility_devices").insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("Add device error: %s", e)
        return None

def delete_device(device_id: str):
    """Delete a specific persisted device with clear API-level failure reasons."""
    device_id = str(device_id or "").strip()
    logger.info("Delete facility device requested: device_id=%s", device_id)
    if not device_id:
        return _delete_result(False, None, "Device id is required", "FACILITY_DEVICE_INVALID_ID", 400)
    if not is_uuid(device_id):
        logger.info("Rejecting delete for non-UUID device id: %s", device_id)
        return _delete_result(
            False,
            {"id": device_id},
            "device_id must be a valid UUID. Received synthetic id: " + device_id,
            "INVALID_DEVICE_ID",
            400,
        )
    if _is_synthetic_id(device_id):
        logger.info("Rejecting delete for synthetic device id: %s", device_id)
        return _delete_result(False, {"id": device_id}, "device_id must be a valid UUID. Received synthetic id: " + device_id, "INVALID_DEVICE_ID", 400)
    try:
        sb = get_client()
        if not sb:
            existing = direct_db_query("facility_devices", "GET", None, f"id=eq.{device_id}&limit=1")
            logger.info("Direct device lookup response: device_id=%s response=%s", device_id, _safe_log(existing))
            if not existing:
                return _delete_result(False, {"id": device_id}, "Device not found", "FACILITY_DEVICE_NOT_FOUND", 404)
            conflict = _direct_device_log_conflict(device_id)
            if conflict:
                return conflict
            deleted = direct_db_query("facility_devices", "DELETE", None, f"id=eq.{device_id}")
            logger.info("Direct device delete response: device_id=%s response=%s", device_id, _safe_log(deleted))
            return _delete_result(True, {"id": device_id}, None, None, 200)

        lookup = sb.table("facility_devices").select("*").eq("id", device_id).limit(1).execute()
        logger.info("Supabase device lookup response: device_id=%s response=%s", device_id, _safe_log(getattr(lookup, "data", None)))
        device = (lookup.data or [None])[0]
        if not device:
            return _delete_result(False, {"id": device_id}, "Device not found", "FACILITY_DEVICE_NOT_FOUND", 404)

        conflict = _supabase_device_log_conflict(sb, device_id)
        if conflict:
            return conflict

        res = sb.table("facility_devices").delete().eq("id", device_id).execute()
        logger.info("Supabase device delete response: device_id=%s response=%s", device_id, _safe_log(getattr(res, "data", None)))
        return _delete_result(True, {"id": device_id, **device}, None, None, 200)
    except Exception as e:
        logger.exception("Delete device exception: device_id=%s exception=%s", device_id, e)
        if _is_relation_conflict(e):
            return _delete_result(
                False,
                {"id": device_id},
                "Device cannot be deleted because it is still referenced by monitoring logs",
                "FACILITY_DEVICE_IN_USE",
                409,
            )
        return _delete_result(False, {"id": device_id}, str(e), "FACILITY_DEVICE_DELETE_FAILED", 500)


def _delete_result(success: bool, data, error: str | None, error_code: str | None, status: int):
    return {
        "success": success,
        "data": data,
        "error": error,
        "error_code": error_code,
        "status": status,
    }


def _supabase_device_log_conflict(sb, device_id: str):
    for table in ("facility_logs", "temperature_logs"):
        try:
            res = sb.table(table).select("id").eq("device_id", device_id).limit(1).execute()
            logger.info("Supabase device relation check: device_id=%s table=%s response=%s", device_id, table, _safe_log(getattr(res, "data", None)))
            if res.data:
                return _delete_result(
                    False,
                    {"id": device_id, "related_table": table},
                    "Device cannot be deleted because it is still referenced by monitoring logs",
                    "FACILITY_DEVICE_IN_USE",
                    409,
                )
        except Exception as exc:
            logger.warning("Device relation check skipped: device_id=%s table=%s exception=%s", device_id, table, exc)
    return None


def _direct_device_log_conflict(device_id: str):
    for table in ("facility_logs", "temperature_logs"):
        try:
            rows = direct_db_query(table, "GET", None, f"device_id=eq.{device_id}&limit=1")
            logger.info("Direct device relation check: device_id=%s table=%s response=%s", device_id, table, _safe_log(rows))
            if rows:
                return _delete_result(
                    False,
                    {"id": device_id, "related_table": table},
                    "Device cannot be deleted because it is still referenced by monitoring logs",
                    "FACILITY_DEVICE_IN_USE",
                    409,
                )
        except Exception as exc:
            logger.warning("Direct device relation check skipped: device_id=%s table=%s exception=%s", device_id, table, exc)
    return None


def _is_relation_conflict(exc: Exception) -> bool:
    text = str(exc).lower()
    return "foreign key" in text or "violates" in text and "constraint" in text or "23503" in text


def _safe_log(value):
    text = str(value)
    return text[:1000]


def is_default_device_id(device_id: str) -> bool:
    return str(device_id or "").startswith("default-")


def is_uuid(value: str | None) -> bool:
    try:
        UUID(str(value or ""))
        return True
    except (TypeError, ValueError):
        return False


def _is_synthetic_id(value: str) -> bool:
    raw = str(value or "")
    return raw.startswith(("default-", "default-room-", "log-room-", "log-device-"))

def get_monitoring_structure():
    """Return persisted facility rooms/devices only.

    Synthetic default-room/log-room IDs must never be used for database writes.
    Seed default facility rows through migration 013 instead.
    """
    rooms = [room for room in list_rooms() if is_uuid(room.get("id"))]
    devices = [device for device in list_devices() if is_uuid(device.get("id")) and is_uuid(device.get("room_id"))]
    return _build_room_unit_matrix(rooms, devices)


def _build_room_unit_matrix(rooms, devices):
    by_room = {}
    for room in rooms:
        room_id = room.get("id")
        if not is_uuid(room_id):
            continue
        by_room[room_id] = {
            **room,
            "id": room_id,
            "name": room.get("name") or "QC Area",
            "devices": [],
        }

    for device in devices or []:
        room_id = device.get("room_id")
        if not is_uuid(room_id) or not is_uuid(device.get("id")):
            continue
        room = by_room.get(room_id)
        if not room:
            continue
        device_type = _log_device_type(device)
        normalized = _normalize_device(device, room["name"], device_type)
        room["devices"].append(normalized)

    merged = list(by_room.values())
    preferred = {name: index for index, name in enumerate(DEFAULT_MONITORING_ROOMS)}
    return sorted(merged, key=lambda room: (preferred.get(room.get("name"), 999), room.get("name") or ""))


def _normalize_device(device, room_name, device_type):
    name = _log_device_name(device, room_name, device_type)
    room_id = device.get("room_id")
    normalized = {
        **device,
        "id": device.get("id"),
        "room_id": room_id,
        "name": name,
        "display_name": f"{room_name} - {name}",
        "type": device_type,
        "device_type": device_type,
        "threshold_temp": _log_threshold(device, device_type),
        "target_temperature": device.get("target_temperature") or _log_threshold(device, device_type),
    }
    return normalized


def _log_room_name(row):
    return (
        row.get("zone")
        or (row.get("facility_rooms") or {}).get("name")
        or row.get("room_name")
        or "QC Area"
    )


def _log_device_type(row):
    facility_device = row.get("facility_devices") or {}
    device_type = row.get("device_type") or row.get("type") or facility_device.get("device_type") or facility_device.get("type") or "room_temp"
    if device_type in {"ambient", "room"}:
        return "room_temp"
    return device_type


def _log_device_name(row, room_name, device_type):
    return (
        row.get("name")
        or (row.get("facility_devices") or {}).get("name")
        or row.get("device_name")
        or row.get("unit_name")
        or {"freezer": "Freezer", "chiller": "Chiller", "undercounter": "UC Chiller"}.get(device_type)
        or ("Suhu Ruangan" if room_name in DEFAULT_MONITORING_ROOMS else "Temperature Point")
    )


def _log_threshold(row, device_type):
    facility_device = row.get("facility_devices") or {}
    value = (
        row.get("threshold_temp")
        or row.get("target_temperature")
        or row.get("threshold_c")
        or facility_device.get("threshold_temp")
        or facility_device.get("target_temperature")
    )
    if value is not None:
        return value
    if device_type == "freezer":
        return -18.0
    if device_type in {"chiller", "undercounter"}:
        return 5.0
    return 25.0


def _slug(value):
    return "".join(char.lower() if char.isalnum() else "-" for char in str(value)).strip("-") or "unit"


def _normalize_device_type(value):
    normalized = str(value or "").strip().lower()
    if normalized in {"ambient", "room"}:
        return "room_temp"
    if normalized in {"room_temp", "chiller", "freezer"}:
        return normalized
    return None


def _default_threshold(device_type):
    if device_type == "freezer":
        return -18.0
    if device_type == "chiller":
        return 5.0
    return 25.0


def _coerce_float(value, default):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def update_room(room_id: str, data: dict):
    """Update a monitoring room."""
    payload = {}
    if data.get("name"):
        payload["name"] = data["name"]
        payload["slug"] = _slug(data["name"])
    if "description" in data:
        payload["description"] = data.get("description") or ""
    if "is_active" in data:
        payload["is_active"] = bool(data.get("is_active"))
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    if not payload:
        return None
    try:
        sb = get_client()
        if not sb:
            rows = direct_db_query("facility_rooms", "PATCH", payload, f"id=eq.{room_id}")
            return rows[0] if rows else {"id": room_id, **payload}
        res = sb.table("facility_rooms").update(payload).eq("id", room_id).execute()
        return res.data[0] if res.data else {"id": room_id, **payload}
    except Exception as e:
        logger.error("Update room error: %s", e)
        return None

def update_device(device_id: str, data: dict):
    """Update a facility device."""
    payload = {}
    if data.get("name"):
        payload["name"] = data["name"]
        payload["slug"] = _slug(data["name"])
    raw_type = data.get("device_type") or data.get("type")
    if raw_type:
        device_type = _normalize_device_type(raw_type)
        if not device_type:
            return None
        payload["device_type"] = device_type
        payload["type"] = device_type
    if "threshold" in data or "threshold_temp" in data or "target_temperature" in data:
        target = _coerce_float(data.get("target_temperature", data.get("threshold_temp", data.get("threshold"))), None)
        payload["target_temperature"] = target
        payload["threshold_temp"] = target
    if "min_temperature" in data:
        payload["min_temperature"] = _coerce_float(data.get("min_temperature"), None)
    if "max_temperature" in data:
        payload["max_temperature"] = _coerce_float(data.get("max_temperature"), None)
    if "is_active" in data:
        payload["is_active"] = bool(data.get("is_active"))
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    if not payload:
        return None
    try:
        sb = get_client()
        if not sb:
            rows = direct_db_query("facility_devices", "PATCH", payload, f"id=eq.{device_id}")
            return rows[0] if rows else {"id": device_id, **payload}
        res = sb.table("facility_devices").update(payload).eq("id", device_id).execute()
        return res.data[0] if res.data else {"id": device_id, **payload}
    except Exception as e:
        logger.error("Update device error: %s", e)
        return None
