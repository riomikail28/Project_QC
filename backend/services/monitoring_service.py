"""Business logic for facility temperature monitoring."""

import logging

from backend.services.alert_service import generate_temperature_alert, save_alert_to_db
from backend.services.audit_service import write_audit
from backend.services.qc_engine import validate_temperature
from backend.services.storage_service import delete_photo, upload_file_storage

logger = logging.getLogger("qc.services.monitoring")


class MonitoringService:
    def __init__(self, supabase_client, audit_writer=write_audit):
        self.sb = supabase_client
        self.audit_writer = audit_writer

    def log_facility_data(self, data, files):
        if not self.sb:
            return {"success": False, "error": "Database offline"}, 503

        device_id = data.device_id
        room_id = data.room_id
        staff_id = data.staff_id
        temperature = data.temperature
        humidity = data.humidity
        reason = data.reason

        if not all([room_id, temperature is not None]):
            return {"success": False, "error": "Room and Temperature are required"}, 400

        uploaded_files = []
        try:
            device_info = None
            unit_type = "ambient"
            room_name = "Unknown"

            room_res = self.sb.table("facility_rooms").select("name").eq("id", room_id).execute()
            if room_res.data:
                room_name = room_res.data[0]["name"]

            if device_id:
                dev_res = self.sb.table("facility_devices").select("*").eq("id", device_id).execute()
                if dev_res.data:
                    device_info = dev_res.data[0]
                    unit_type = device_info["type"]
                    if unit_type == "undercounter":
                        unit_type = "chiller"
                    elif unit_type == "room_temp":
                        unit_type = "ambient"

            status = validate_temperature(unit_type, float(temperature))
            is_normal = status == "PASS"

            photo_urls = []
            storage_paths = []
            if data.photo_url:
                photo_urls.append(data.photo_url)

            for photo_file in files.getlist("photo"):
                if photo_file:
                    uploaded = upload_file_storage(photo_file, staff_id=staff_id)
                    uploaded_files.append(uploaded)
                    photo_urls.append(uploaded.url)
                    storage_paths.append(uploaded.storage_path)

            photo_url = ";".join(photo_urls) if photo_urls else None
            storage_path = ";".join(storage_paths) if storage_paths else None
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
            if storage_path:
                log_payload["storage_path"] = storage_path

            try:
                res = self.sb.table("facility_logs").insert(log_payload).execute()
            except Exception:
                for uploaded in uploaded_files:
                    delete_photo(uploaded.storage_path)
                raise

            log_data = res.data[0] if res.data else None
            self.audit_writer("create", "facility_log", str(log_data.get("id")) if log_data else None, after=log_data or log_payload)

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

            return {
                "success": True,
                "status": status,
                "alert": alert,
                "log_id": log_data["id"] if log_data else None,
                "photo_url": photo_url,
                "storage_path": storage_path,
            }, 200
        except ValueError as exc:
            logger.error("Upload validation error: %s", exc)
            return {"success": False, "error": f"Upload gagal: {str(exc)}"}, 400

    def latest_logs(self):
        if not self.sb:
            return []
        try:
            res = (
                self.sb.table("facility_logs")
                .select("*, facility_rooms(name), facility_devices(name, type, threshold_temp)")
                .order("recorded_at", desc=True)
                .limit(50)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            logger.error("Fetch logs error: %s", exc)
            return []

    def monitoring_stats(self):
        if not self.sb:
            return {}, 200
        try:
            res = self.sb.table("facility_logs").select("is_normal, recorded_at, temperature_c, facility_rooms(name)").execute()
            return res.data or [], 200
        except Exception as exc:
            return {"error": str(exc)}, 500
