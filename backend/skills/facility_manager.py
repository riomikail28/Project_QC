"""
Facility Management Skill
=========================
Handles CRUD operations for Rooms and Devices (Chillers/Freezers).
Used by Admin for kitchen configuration.
"""

import logging
from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.facility")

def list_rooms():
    """List all monitoring rooms."""
    sb = get_client()
    if not sb: return []
    try:
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
    if not sb: return []
    try:
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
            "threshold_temp": threshold
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
    Includes a hardcoded fallback if the database is offline.
    """
    sb = get_client()
    if not sb:
        # RETURN HARDCODED FALLBACK (Based on requested plan)
        return [
            {
                "id": "room-ppic", "name": "PPIC", "devices": [
                    {"id": "p-rt", "name": "Suhu Ruangan", "type": "room_temp", "threshold_temp": 25.0},
                    {"id": "p-c1", "name": "Chiller 1", "type": "chiller", "threshold_temp": 5.0},
                    {"id": "p-f1", "name": "Freezer 1", "type": "freezer", "threshold_temp": -18.0}
                ]
            },
            {
                "id": "room-kitchen", "name": "Kitchen", "devices": [
                    {"id": "k-rt", "name": "Suhu Ruangan", "type": "room_temp", "threshold_temp": 25.0},
                    {"id": "k-u1", "name": "Undercounter 1", "type": "undercounter", "threshold_temp": 5.0}
                ]
            }
        ]
    
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
