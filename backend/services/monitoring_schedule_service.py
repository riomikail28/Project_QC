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
        completed_by_slot = self._completed_by_slot(rows)
        slots = []

        for index, slot in enumerate(MONITORING_SLOTS):
            slot_dt = self._slot_datetime(slot)
            next_dt = self._slot_datetime(MONITORING_SLOTS[index + 1]) if index + 1 < len(MONITORING_SLOTS) else None
            completed = completed_by_slot.get(slot)
            late = bool(completed and completed.get("schedule_status") == "late")

            if completed:
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
                "completed": bool(completed),
                "late": late,
                "submitted_at": completed.get("submitted_at") or completed.get("recorded_at") if completed else None,
                "room_id": completed.get("room_id") if completed else None,
                "device_id": completed.get("device_id") if completed else None,
                "temperature_c": completed.get("temperature_c") if completed else None,
            })

        completed_count = sum(1 for item in slots if item["completed"])
        current_slot = next((item for item in slots if item["status"] == "pending"), None)
        next_slot = current_slot or next((item for item in slots if item["status"] == "upcoming"), None)
        all_done = completed_count == len(MONITORING_SLOTS)

        return {
            "success": True,
            "data": {
                "date": monitoring_date,
                "timezone": "Asia/Jakarta",
                "slots": slots,
                "completed_count": completed_count,
                "total_slots": len(MONITORING_SLOTS),
                "progress_text": f"{completed_count}/{len(MONITORING_SLOTS)} monitoring selesai hari ini.",
                "current_slot": current_slot,
                "next_slot": next_slot,
                "message": (
                    "Monitoring hari ini selesai. Tugas berikutnya besok pukul 07:00."
                    if all_done else self._active_message(next_slot)
                ),
            },
            "message": "OK",
        }

    def resolve_submission(self, slot_time: str | None = None):
        schedule = self.today()["data"]
        slot = self._normalize_slot(slot_time) or (
            schedule.get("current_slot") or schedule.get("next_slot") or {}
        ).get("time")
        if slot not in MONITORING_SLOTS:
            return {
                "success": False,
                "status": 400,
                "message": "Slot monitoring tidak valid",
            }
        if all(item["completed"] for item in schedule["slots"]):
            return {
                "success": False,
                "status": 409,
                "message": "Monitoring hari ini sudah selesai.",
                "schedule": schedule,
            }
        slot_data = next(item for item in schedule["slots"] if item["time"] == slot)
        if slot_data["status"] == "upcoming":
            return {
                "success": False,
                "status": 409,
                "message": f"Slot {slot} belum waktunya.",
                "schedule": schedule,
            }
        if slot_data["completed"]:
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

    def _completed_by_slot(self, rows):
        completed = {}
        for row in rows or []:
            slot = self._normalize_slot(row.get("slot_time"))
            if not slot:
                continue
            if slot not in completed:
                completed[slot] = row
        return completed

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
