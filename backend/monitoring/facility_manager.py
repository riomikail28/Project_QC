"""
Facility Management Skill
=========================
Handles CRUD operations for Rooms and Devices (Chillers/Freezers).
Used by Admin for kitchen configuration.
"""

import logging
from backend.database.supabase_client import direct_db_query, get_client

logger = logging.getLogger("qc.facility")

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

def add_room(name: str, description: str = ""):
    """Add a new monitoring room."""
    sb = get_client()
    if not sb: return None
    try:
        res = sb.table("facility_rooms").insert({"name": name, "description": description}).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("Add room error: %s", e)
        return None

def delete_room(room_id: str):
    """Delete a room and all its devices."""
    sb = get_client()
    if not sb: return False
    try:
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

def add_device(room_id: str, name: str, device_type: str, threshold: float):
    """Add a new device (chiller/freezer/etc) to a room."""
    sb = get_client()
    if not sb: return None
    try:
        payload = {
            "room_id": room_id,
            "name": name,
            "type": device_type,
            "threshold_temp": threshold,
        }
        res = sb.table("facility_devices").insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("Add device error: %s", e)
        return None

def delete_device(device_id: str):
    """Delete a specific device."""
    sb = get_client()
    if not sb: return False
    try:
        sb.table("facility_devices").delete().eq("id", device_id).execute()
        return True
    except Exception as e:
        logger.error("Delete device error: %s", e)
        return False

def get_monitoring_structure():
    """Returns a nested structure of Rooms -> Devices for the UI.
    """
    rooms = list_rooms()
    devices = list_devices()
    
    structure = []
    for room in rooms:
        room_devices = [d for d in devices if d["room_id"] == room["id"]]
        structure.append({
            "id": room["id"],
            "name": room["name"],
            "devices": room_devices
        })
    return structure

def update_room(room_id: str, data: dict):
    """Update a monitoring room."""
    sb = get_client()
    if not sb: return None
    payload = {}
    if data.get("name"):
        payload["name"] = data["name"]
    if "description" in data:
        payload["description"] = data.get("description") or ""
    if not payload:
        return None
    try:
        res = sb.table("facility_rooms").update(payload).eq("id", room_id).execute()
        return res.data[0] if res.data else {"id": room_id, **payload}
    except Exception as e:
        logger.error("Update room error: %s", e)
        return None

def update_device(device_id: str, data: dict):
    """Update a facility device."""
    sb = get_client()
    if not sb: return None
    payload = {}
    if data.get("name"):
        payload["name"] = data["name"]
    if data.get("type"):
        payload["type"] = data["type"]
    if "threshold" in data:
        payload["threshold_temp"] = data.get("threshold")
    if "threshold_temp" in data:
        payload["threshold_temp"] = data.get("threshold_temp")
    if not payload:
        return None
    try:
        res = sb.table("facility_devices").update(payload).eq("id", device_id).execute()
        return res.data[0] if res.data else {"id": device_id, **payload}
    except Exception as e:
        logger.error("Update device error: %s", e)
        return None
