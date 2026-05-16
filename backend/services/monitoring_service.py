"""Business logic for facility temperature monitoring."""

import logging

from backend.database.supabase_client import direct_db_query, get_last_db_error
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

            room_rows = self._select_rows("facility_rooms", f"id=eq.{room_id}&select=name")
            if room_rows:
                room_name = room_rows[0]["name"]

            if device_id:
                device_rows = self._select_rows("facility_devices", f"id=eq.{device_id}&select=*")
                if device_rows:
                    device_info = device_rows[0]
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
                photo_urls.extend([item for item in str(data.photo_url).split(";") if item])
            if data.storage_path:
                storage_paths.extend([item for item in str(data.storage_path).split(";") if item])

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
                inserted_rows = self._insert_rows("facility_logs", log_payload)
            except Exception:
                for uploaded in uploaded_files:
                    delete_photo(uploaded.storage_path)
                raise

            log_data = inserted_rows[0] if inserted_rows else None
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
            return {"success": False, "error": "Upload gagal", "detail": str(exc)}, 400
        except Exception as exc:
            logger.exception("Monitoring log database error")
            return {
                "success": False,
                "error": "Database save failed",
                "detail": str(exc),
                "db_detail": get_last_db_error(),
            }, 500

    def latest_logs(self):
        try:
            if self.sb:
                rows = []
                try:
                    res = (
                        self.sb.table("facility_logs")
                        .select("*, facility_rooms(name), facility_devices(name, type, threshold_temp)")
                        .order("recorded_at", desc=True)
                        .limit(50)
                        .execute()
                    )
                    rows = res.data or []
                except Exception as exc:
                    logger.warning("Fetch facility logs with relations failed: %s", exc)
                    res = self.sb.table("facility_logs").select("*").order("recorded_at", desc=True).limit(50).execute()
                    rows = res.data or []
                if rows:
                    return rows
                temp_res = self.sb.table("temperature_logs").select("*").order("recorded_at", desc=True).limit(50).execute()
                return temp_res.data or []
            try:
                rows = direct_db_query("facility_logs", "GET", None, "select=*,facility_rooms(name),facility_devices(name,type,threshold_temp)&order=recorded_at.desc&limit=50")
            except Exception as exc:
                logger.warning("Direct facility logs with relations failed: %s", exc)
                rows = direct_db_query("facility_logs", "GET", None, "select=*&order=recorded_at.desc&limit=50")
            if rows:
                return rows
            return direct_db_query("temperature_logs", "GET", None, "select=*&order=recorded_at.desc&limit=50")
        except Exception as exc:
            logger.error("Fetch logs error: %s", exc)
            return []

    def monitoring_stats(self):
        try:
            rows = self._select_rows("facility_logs", "select=is_normal,recorded_at,temperature_c")
            return rows, 200
        except Exception as exc:
            return {"error": "Monitoring stats failed", "detail": str(exc), "db_detail": get_last_db_error()}, 500

    def _select_rows(self, table, filters):
        if self.sb:
            query = self.sb.table(table).select("*")
            for part in filters.split("&"):
                if not part or part.startswith("select="):
                    continue
                name, raw_value = part.split("=", 1)
                if raw_value.startswith("eq."):
                    query = query.eq(name, raw_value[3:])
            res = query.execute()
            return res.data or []
        return direct_db_query(table, "GET", None, filters)

    def _insert_rows(self, table, payload):
        if self.sb:
            res = self.sb.table(table).insert(payload).execute()
            return res.data or []
        return direct_db_query(table, "POST", payload)
