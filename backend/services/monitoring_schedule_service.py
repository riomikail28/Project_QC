"""Daily monitoring schedule logic for staff temperature checks."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger("qc.services.monitoring_schedule")

MONITORING_SLOTS = ("07:00", "13:00", "16:00", "19:00")
LOCAL_TZ = ZoneInfo("Asia/Jakarta")


class MonitoringScheduleService:
    def __init__(self, supabase_client, now: datetime | None = None):
        self.sb = supabase_client
        self.now = (now or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ)

    def today(self):
        monitoring_date = self.now.date().isoformat()
        rows = self._logs_for_date(monitoring_date)
        devices = self._active_devices()
        total_devices = len(devices)
        completed_by_slot = self._completed_by_slot(rows)
        completed_by_device_slot = self._completed_by_device_slot(rows)
        slots = []

        for index, slot in enumerate(MONITORING_SLOTS):
            slot_dt = self._slot_datetime(slot)
            next_dt = self._slot_datetime(MONITORING_SLOTS[index + 1]) if index + 1 < len(MONITORING_SLOTS) else None
            completed_rows = completed_by_slot.get(slot, [])
            completed_count = len(completed_rows)
            slot_complete = total_devices > 0 and completed_count >= total_devices
            late = bool(completed_rows and any(row.get("schedule_status") == "late" for row in completed_rows))

            if slot_complete:
                status = "late" if late else "completed"
                label = "Selesai terlambat" if late else "Selesai"
            elif self.now < slot_dt:
                status = "upcoming"
                label = "Belum waktunya"
            elif next_dt and self.now >= next_dt:
                status = "missed"
                label = "Terlewat"
            else:
                status = "pending"
                label = "Menunggu input"

            slots.append({
                "time": slot,
                "status": status,
                "label": label,
                "completed": slot_complete,
                "completed_count": completed_count,
                "total_devices": total_devices,
                "unit_progress_text": f"{completed_count}/{total_devices} unit selesai",
                "late": late,
                "submitted_at": completed_rows[-1].get("submitted_at") or completed_rows[-1].get("recorded_at") if completed_rows else None,
                "room_id": completed_rows[-1].get("room_id") if completed_rows else None,
                "device_id": completed_rows[-1].get("device_id") if completed_rows else None,
                "temperature_c": completed_rows[-1].get("temperature_c") if completed_rows else None,
            })

        total_completed = sum(item["completed_count"] for item in slots)
        total_required = total_devices * len(MONITORING_SLOTS)
        current_slot = next((item for item in slots if item["status"] == "pending"), None)
        next_slot = current_slot or next((item for item in slots if item["status"] == "upcoming"), None)
        all_done = total_required > 0 and total_completed >= total_required
        active_slot_time = (current_slot or {}).get("time")

        return {
            "success": True,
            "data": {
                "date": monitoring_date,
                "timezone": "Asia/Jakarta",
                "slots": slots,
                "total_devices": total_devices,
                "completed_per_slot": {slot["time"]: slot["completed_count"] for slot in slots},
                "total_required": total_required,
                "total_completed": total_completed,
                "completed_count": total_completed,
                "total_slots": len(MONITORING_SLOTS),
                "progress_text": f"{total_completed}/{total_required} monitoring selesai hari ini.",
                "current_slot": current_slot,
                "next_slot": next_slot,
                "next_active_slot": next_slot,
                "device_statuses": self._device_statuses(devices, completed_by_device_slot, active_slot_time),
                "message": (
                    "Monitoring hari ini selesai. Tugas berikutnya besok pukul 07:00."
                    if all_done else self._active_message(next_slot)
                ),
            },
            "message": "OK",
        }

    def resolve_submission(self, slot_time: str | None = None, device_id: str | None = None, room_id: str | None = None, allow_duplicate: bool = False):
        schedule = self.today()["data"]
        active_slot = schedule.get("current_slot")
        next_slot = schedule.get("next_slot")
        slot = self._normalize_slot(slot_time) or (active_slot or next_slot or {}).get("time")
        if slot not in MONITORING_SLOTS:
            return {
                "success": False,
                "status": 400,
                "message": "Slot monitoring tidak valid",
            }
        if schedule.get("total_required", 0) > 0 and schedule.get("total_completed", 0) >= schedule.get("total_required", 0):
            return {
                "success": False,
                "status": 409,
                "message": "Monitoring hari ini sudah selesai.",
                "schedule": schedule,
            }
        slot_data = next(item for item in schedule["slots"] if item["time"] == slot)
        if active_slot and slot != active_slot.get("time"):
            if slot_data["status"] == "upcoming":
                return {
                    "success": False,
                    "status": 409,
                    "message": f"Slot {slot} belum waktunya.",
                    "schedule": schedule,
                }
            if slot_data["completed"] and not allow_duplicate:
                return {
                    "success": False,
                    "status": 409,
                    "message": f"Slot {slot} sudah selesai.",
                    "schedule": schedule,
                }
        if slot_data["status"] == "upcoming":
            return {
                "success": False,
                "status": 409,
                "message": f"Slot {slot} belum waktunya.",
                "schedule": schedule,
            }
        if not allow_duplicate and self._has_device_log(schedule["date"], slot, device_id, room_id):
            return {
                "success": False,
                "status": 409,
                "message": f"Unit ini sudah diinput untuk slot {slot}.",
                "schedule": schedule,
            }
        if slot_data["completed"] and not allow_duplicate:
            return {
                "success": False,
                "status": 409,
                "message": f"Slot {slot} sudah selesai.",
                "schedule": schedule,
            }
        is_late = self.now > self._slot_datetime(slot)
        return {
            "success": True,
            "monitoring_date": schedule["date"],
            "slot_time": slot,
            "schedule_status": "late" if is_late else "completed",
            "is_late": is_late,
            "submitted_at": self.now.isoformat(),
        }

    def _logs_for_date(self, monitoring_date):
        try:
            if not self.sb:
                return []
            res = (
                self.sb.table("facility_logs")
                .select("*")
                .eq("monitoring_date", monitoring_date)
                .execute()
            )
            return res.data or []
        except Exception:
            logger.warning("Daily monitoring schedule query failed", exc_info=True)
            return []

    def _active_devices(self):
        try:
            if not self.sb:
                return []
            rows = (
                self.sb.table("facility_devices")
                .select("id, room_id, name, type, device_type, is_active, facility_rooms(name)")
                .eq("is_active", True)
                .execute()
            ).data or []
            return [row for row in rows if row.get("id")]
        except Exception:
            logger.warning("Active monitoring device query failed", exc_info=True)
            return []

    def _completed_by_slot(self, rows):
        completed = {}
        for row in rows or []:
            slot = self._normalize_slot(row.get("slot_time"))
            if not slot:
                continue
            completed.setdefault(slot, {})
            device_key = row.get("device_id") or row.get("room_id") or row.get("id") or f"legacy-{slot}-{len(completed[slot])}"
            if device_key and device_key not in completed[slot]:
                completed[slot][device_key] = row
        return {slot: list(items.values()) for slot, items in completed.items()}

    def _completed_by_device_slot(self, rows):
        completed = {}
        for row in rows or []:
            slot = self._normalize_slot(row.get("slot_time"))
            device_key = row.get("device_id") or row.get("room_id")
            if slot and device_key:
                completed[(str(device_key), slot)] = row
        return completed

    def _has_device_log(self, monitoring_date, slot, device_id, room_id):
        rows = self._logs_for_date(monitoring_date)
        key = str(device_id or room_id or "")
        for row in rows:
            row_key = str(row.get("device_id") or row.get("room_id") or "")
            if row_key == key and self._normalize_slot(row.get("slot_time")) == slot:
                return True
        return False

    def _device_statuses(self, devices, completed_by_device_slot, active_slot_time):
        statuses = {}
        for device in devices:
            device_id = str(device.get("id"))
            slot_statuses = {}
            for slot in MONITORING_SLOTS:
                completed = completed_by_device_slot.get((device_id, slot))
                slot_dt = self._slot_datetime(slot)
                next_index = MONITORING_SLOTS.index(slot) + 1
                next_dt = self._slot_datetime(MONITORING_SLOTS[next_index]) if next_index < len(MONITORING_SLOTS) else None
                if completed:
                    status = "completed"
                    label = "Selesai"
                elif next_dt and self.now >= next_dt:
                    status = "missed"
                    label = "Terlewat"
                elif self.now < slot_dt:
                    status = "upcoming"
                    label = "Belum waktunya"
                else:
                    status = "pending"
                    label = "Belum input"
                slot_statuses[slot] = {
                    "status": status,
                    "label": label,
                    "submitted_at": completed.get("submitted_at") or completed.get("recorded_at") if completed else None,
                    "temperature_c": completed.get("temperature_c") if completed else None,
                    "humidity_rh": completed.get("humidity_rh") if completed else None,
                    "notes": completed.get("notes") or completed.get("reason") if completed else None,
                    "photo_url": completed.get("photo_url") if completed else None,
                    "storage_path": completed.get("storage_path") if completed else None,
                }
            active_status = slot_statuses.get(active_slot_time) if active_slot_time else None
            statuses[device_id] = {
                "device_id": device_id,
                "room_id": device.get("room_id"),
                "device_name": device.get("name"),
                "room_name": (device.get("facility_rooms") or {}).get("name"),
                "active_slot": active_slot_time,
                "active_status": active_status,
                "slots": slot_statuses,
            }
        return statuses

    def _slot_datetime(self, slot):
        hour, minute = [int(part) for part in slot.split(":", 1)]
        return datetime.combine(self.now.date(), time(hour, minute), LOCAL_TZ)

    def _normalize_slot(self, value):
        raw = str(value or "").strip()[:5]
        return raw if raw in MONITORING_SLOTS else None

    def _active_message(self, slot):
        if not slot:
            tomorrow = self.now.date() + timedelta(days=1)
            return f"Tugas berikutnya {tomorrow.isoformat()} pukul 07:00."
        return f"Slot aktif berikutnya pukul {slot['time']}: {slot['label']}."
