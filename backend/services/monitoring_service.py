"""Business logic for facility temperature monitoring."""

import logging
import os
import sys
import threading
from datetime import datetime, timezone
from types import SimpleNamespace

is_testing = "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules or "unittest" in sys.modules

from backend.database.supabase_client import direct_db_query, get_last_db_error
from backend.services.alert_service import generate_temperature_alert, save_alert_to_db
from backend.services.audit_service import write_audit
from backend.services.google_apps_script_service import send_monitoring_log
from backend.services.qc_engine import validate_temperature
from backend.services.storage_service import delete_photo, upload_file_storage, upload_photo_result

logger = logging.getLogger("qc.services.monitoring")


class MonitoringService:
    def __init__(self, supabase_client, audit_writer=write_audit):
        self.sb = supabase_client
        self.audit_writer = audit_writer

    def check_edit_tolerance(self, slot_time, monitoring_date, current_time_local):
        deadlines = {
            "07:00": "23:59",
            "13:00": "23:59",
            "16:00": "23:59",
            "19:00": "23:59",
        }
        deadline_time_str = deadlines.get(slot_time)
        if not deadline_time_str:
            return True
        try:
            hour, minute = map(int, deadline_time_str.split(":"))
            date_parts = [int(p) for p in monitoring_date.split("-")]
            deadline_dt = datetime(date_parts[0], date_parts[1], date_parts[2], hour, minute, 59, tzinfo=current_time_local.tzinfo)
            return current_time_local <= deadline_dt
        except Exception as exc:
            logger.warning("Error parsing deadline check: %s", exc)
            return True

    def log_facility_data(self, data, files):
        device_id = data.device_id
        room_id = data.room_id
        staff_id = data.staff_id
        temperature = data.temperature
        humidity = data.humidity
        reason = data.reason or getattr(data, "notes", None)
        monitoring_date = getattr(data, "monitoring_date", None)
        slot_time = getattr(data, "slot_time", None)
        schedule_status = getattr(data, "schedule_status", None)
        submitted_at = getattr(data, "submitted_at", None)
        is_late = getattr(data, "is_late", None)

        if not all([room_id, temperature is not None]):
            return {"success": False, "error": "Room and Temperature are required"}, 400

        existing_log = None
        if monitoring_date and slot_time:
            device_filter = f"&device_id=eq.{device_id}" if device_id else "&device_id=is.null"
            query_str = f"room_id=eq.{room_id}&monitoring_date=eq.{monitoring_date}&slot_time=eq.{slot_time}{device_filter}&select=id,created_at,photo_url,storage_path"
            existing_rows = self._select_rows("facility_logs", query_str)
            if existing_rows:
                existing_log = existing_rows[0]

        if existing_log:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo("Asia/Jakarta")
            now_local = datetime.now(tz)
            if not self.check_edit_tolerance(slot_time, monitoring_date, now_local):
                return {"success": False, "error": f"Batas waktu edit untuk slot {slot_time} sudah lewat."}, 400

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
                    unit_type = device_info.get("type") or device_info.get("device_type") or "ambient"
                    if unit_type == "undercounter":
                        unit_type = "chiller"
                    elif unit_type == "room_temp":
                        unit_type = "ambient"

            min_temp = self._coerce_float((device_info or {}).get("min_temperature"), None)
            max_temp = self._coerce_float((device_info or {}).get("max_temperature"), None)
            target_temp = self._coerce_float(
                (device_info or {}).get("target_temperature")
                or (device_info or {}).get("threshold_temp")
                or data.threshold,
                self._default_threshold(unit_type),
            )
            qc_status = None
            if min_temp is not None and max_temp is not None:
                temp_value = float(temperature)
                if min_temp <= temp_value <= max_temp:
                    status = "normal"
                elif (min_temp - 2) <= temp_value <= (max_temp + 2):
                    status = "warning"
                else:
                    status = "critical"
                qc_status = {"normal": "PASS", "warning": "WARNING", "critical": "FAIL"}[status]
            else:
                qc_status = validate_temperature(unit_type, float(temperature))
                status = {"PASS": "normal", "WARNING": "warning", "FAIL": "critical"}.get(qc_status, qc_status.lower())
            is_normal = status == "normal"

            # Read photo bytes in main thread to process upload in background
            photos_to_upload = []
            for photo_file in files.getlist("photo"):
                if photo_file and photo_file.filename:
                    try:
                        file_bytes = photo_file.read()
                        if file_bytes:
                            photos_to_upload.append((file_bytes, photo_file.filename, photo_file.content_type))
                    except Exception as e:
                        logger.error("Failed to read photo file bytes: %s", e)

            photo_urls = []
            storage_paths = []
            if getattr(data, "photo_url", None):
                photo_urls.extend([item for item in str(data.photo_url).split(";") if item])
            if getattr(data, "storage_path", None):
                storage_paths.extend([item for item in str(data.storage_path).split(";") if item])

            photo_url = ";".join(photo_urls) if photo_urls else None
            storage_path = ";".join(storage_paths) if storage_paths else None
            threshold = target_temp
            recorded_at = datetime.now(timezone.utc).isoformat()

            alert = None
            if not is_normal:
                alert = generate_temperature_alert(room_name, unit_type, float(temperature), status.upper())

            staff_name = staff_id or "Unknown User"
            if staff_id and len(str(staff_id)) == 36 and str(staff_id).count("-") == 4:
                try:
                    user_rows = self._select_rows("users", f"staff_account_id=eq.{staff_id}&select=full_name")
                    if user_rows and user_rows[0].get("full_name"):
                        staff_name = user_rows[0]["full_name"]
                    else:
                        staff_rows = self._select_rows("staff_accounts", f"id=eq.{staff_id}&select=username")
                        if staff_rows and staff_rows[0].get("username"):
                            staff_name = staff_rows[0]["username"]
                except Exception as exc:
                    logger.warning("Failed to resolve staff name: %s", exc)

            # Store computed details inside mutable container for bg execution
            result_container = {"log_id": None, "photo_url": photo_url, "storage_path": storage_path}

            def bg_upload_and_sync():
                try:
                    bg_uploaded = []
                    bg_urls = list(photo_urls)
                    bg_paths = list(storage_paths)
                    
                    for f_bytes, f_name, c_type in photos_to_upload:
                        wrap = SimpleNamespace(
                            read=lambda: f_bytes,
                            filename=f_name,
                            mimetype=c_type
                        )
                        uploaded = upload_file_storage(
                            wrap,
                            staff_id=staff_id,
                            category="temperature",
                            related_id=room_id
                        )
                        bg_uploaded.append(uploaded)
                        bg_urls.append(uploaded.url)
                        bg_paths.append(uploaded.storage_path)
                        
                    final_photo_url = ";".join(bg_urls) if bg_urls else None
                    final_storage_path = ";".join(bg_paths) if bg_paths else None
                    
                    result_container["photo_url"] = final_photo_url
                    result_container["storage_path"] = final_storage_path

                    if existing_log:
                        log_payload = {
                            "temperature_c": float(temperature),
                            "threshold_c": threshold,
                            "humidity_rh": float(humidity) if humidity not in (None, "") else None,
                            "is_normal": is_normal,
                            "staff_id": staff_id or None,
                            "notes": reason,
                            "recorded_at": recorded_at,
                        }
                        if final_photo_url:
                            log_payload["photo_url"] = final_photo_url
                        if final_storage_path:
                            log_payload["storage_path"] = final_storage_path

                        updated_rows = self._update_row("facility_logs", existing_log["id"], log_payload)
                        log_data = updated_rows[0] if updated_rows else None
                        log_id = existing_log["id"]
                    else:
                        log_payload = {
                            "device_id": device_id or None,
                            "room_id": room_id,
                            "temperature_c": float(temperature),
                            "threshold_c": threshold,
                            "humidity_rh": float(humidity) if humidity not in (None, "") else None,
                            "is_normal": is_normal,
                            "staff_id": staff_id or None,
                            "notes": reason,
                            "recorded_at": recorded_at,
                            "created_at": recorded_at,
                        }
                        if monitoring_date:
                            log_payload["monitoring_date"] = monitoring_date
                        if slot_time:
                            log_payload["slot_time"] = slot_time
                        if schedule_status:
                            log_payload["schedule_status"] = schedule_status
                        if submitted_at:
                            log_payload["submitted_at"] = submitted_at
                        if is_late is not None:
                            log_payload["is_late"] = bool(is_late)
                        if final_photo_url:
                            log_payload["photo_url"] = final_photo_url
                        if final_storage_path:
                            log_payload["storage_path"] = final_storage_path

                        inserted_rows = self._insert_rows("facility_logs", log_payload)
                        log_data = inserted_rows[0] if inserted_rows else None
                        log_id = log_data.get("id") if log_data else None

                    result_container["log_id"] = log_id

                    action_name = "update_temperature" if existing_log else "submit_temperature"
                    self.audit_writer(action_name, "facility_log", str(log_id) if log_id else None, after=log_data or log_payload)

                    self._record_temperature_log(
                        room_name=room_name,
                        room_id=room_id,
                        device_id=device_id,
                        device_type=unit_type,
                        device_name=(device_info or {}).get("name"),
                        temperature=temperature,
                        threshold=threshold,
                        status=status,
                        is_normal=is_normal,
                        photo_url=final_photo_url,
                        storage_path=final_storage_path,
                        staff_id=staff_id,
                        notes=reason,
                        recorded_at=recorded_at,
                        log_id=log_id,
                        monitoring_date=monitoring_date,
                        slot_time=slot_time,
                        schedule_status=schedule_status,
                        submitted_at=submitted_at,
                        is_late=is_late,
                    )

                    if bg_uploaded and log_id:
                        self.audit_writer(
                            "upload_temperature_photo",
                            "facility_log",
                            str(log_id),
                            metadata={"storage_paths": [item.storage_path for item in bg_uploaded]},
                        )
                        
                        self._record_evidence(
                            uploaded_files=bg_uploaded,
                            staff_id=staff_id,
                            related_id=log_id,
                            photo_urls=bg_urls,
                            storage_paths=bg_paths,
                            created_at=recorded_at,
                        )

                    if not is_normal and log_data:
                        save_alert_to_db(
                            zone=room_name,
                            temperature=float(temperature),
                            threshold=threshold,
                            log_id=log_data["id"],
                            device_id=device_id,
                        )

                    sheets_payload = {
                        "date": monitoring_date or recorded_at[:10],
                        "slot_time": slot_time,
                        "room": room_name,
                        "device": (device_info or {}).get("name") or device_id,
                        "temperature": float(temperature),
                        "status": qc_status or status.upper(),
                        "staff_name": staff_name,
                        "submitted_at": submitted_at or recorded_at,
                        "notes": reason,
                    }
                    if final_photo_url:
                        sheets_payload["photo_url"] = final_photo_url

                    send_monitoring_log(sheets_payload, background=True)

                except Exception as e:
                    logger.error("Background photo upload or sync failed: %s", e)
                    for uploaded in bg_uploaded:
                        delete_photo(uploaded.storage_path)

            if is_testing:
                bg_upload_and_sync()
            else:
                thread = threading.Thread(target=bg_upload_and_sync, daemon=True)
                thread.start()

            return {
                "success": True,
                "message": "Temperature log saved",
                "status": qc_status or status.upper(),
                "computed_status": status,
                "alert": alert,
                "data": result_container,
            }, 200
        except ValueError as exc:
            logger.error("Upload validation error: %s", exc)
            return {"success": False, "error": "Upload gagal", "detail": str(exc)}, 400
        except Exception as exc:
            logger.exception("Monitoring log database error")
            return {
                "success": False,
                "message": f"Facility log insert failed: {str(exc)}",
                "error": "Database save failed",
                "detail": str(exc),
                "db_detail": get_last_db_error(),
            }, 500

    def _record_temperature_log(self, room_name, room_id, device_id, device_type, device_name, temperature, threshold, status, is_normal, photo_url, storage_path, staff_id, notes, recorded_at, log_id, monitoring_date=None, slot_time=None, schedule_status=None, submitted_at=None, is_late=None):
        payload = {
            "zone": room_name or "QC Area",
            "room_id": room_id,
            "device_id": device_id,
            "device_type": device_type if device_type != "ambient" else "room_temp",
            "device_name": device_name,
            "temperature": float(temperature),
            "temperature_c": float(temperature),
            "threshold_c": threshold,
            "is_abnormal": not is_normal,
            "status": status,
            "staff_id": staff_id or None,
            "photo_url": photo_url,
            "storage_path": storage_path,
            "notes": notes,
            "created_at": recorded_at,
            "recorded_at": recorded_at,
            "facility_log_id": log_id,
        }
        if monitoring_date:
            payload["monitoring_date"] = monitoring_date
        if slot_time:
            payload["slot_time"] = slot_time
        if schedule_status:
            payload["schedule_status"] = schedule_status
        if submitted_at:
            payload["submitted_at"] = submitted_at
        if is_late is not None:
            payload["is_late"] = bool(is_late)
        existing_temp_rows = []
        if log_id:
            existing_temp_rows = self._select_rows("temperature_logs", f"facility_log_id=eq.{log_id}&select=id")
        
        if existing_temp_rows:
            try:
                self.sb.table("temperature_logs").update({k: v for k, v in payload.items() if v is not None}).eq("id", existing_temp_rows[0]["id"]).execute()
            except Exception:
                logger.warning("temperature_logs compatibility update skipped", exc_info=True)
        else:
            try:
                self._insert_rows("temperature_logs", {k: v for k, v in payload.items() if v is not None})
            except Exception:
                logger.warning("temperature_logs compatibility insert skipped", exc_info=True)

    def _default_threshold(self, unit_type):
        if unit_type == "freezer":
            return -18.0
        if unit_type in {"chiller", "undercounter"}:
            return 5.0
        return 25.0

    def _coerce_float(self, value, default):
        if value in (None, ""):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _record_evidence(self, uploaded_files, staff_id, related_id, photo_urls, storage_paths, created_at):
        if not (uploaded_files or photo_urls or storage_paths):
            return
        rows = []
        uploaded_by_path = {item.storage_path: item for item in uploaded_files}
        for index, storage_path in enumerate(storage_paths or []):
            uploaded = uploaded_by_path.get(storage_path)
            rows.append({
                "file_name": getattr(uploaded, "file_name", None) if uploaded else None,
                "file_type": getattr(uploaded, "file_type", None) if uploaded else None,
                "mime_type": getattr(uploaded, "file_type", None) if uploaded else None,
                "file_size": getattr(uploaded, "file_size", None) if uploaded else None,
                "bucket": getattr(uploaded, "bucket", "qc-evidence") if uploaded else "qc-evidence",
                "storage_path": storage_path,
                "public_url": (photo_urls or [None])[index] if index < len(photo_urls or []) else None,
                "uploaded_by": staff_id or None,
                "related_type": "temperature",
                "related_id": related_id,
                "created_at": created_at,
            })
        if not rows and photo_urls:
            rows = [{
                "bucket": "qc-evidence",
                "public_url": url,
                "uploaded_by": staff_id or None,
                "related_type": "temperature",
                "related_id": related_id,
                "created_at": created_at,
            } for url in photo_urls]
        for row in rows:
            try:
                self._insert_rows("qc_evidence", {k: v for k, v in row.items() if v is not None})
            except Exception:
                logger.warning("Temperature evidence metadata insert skipped", exc_info=True)

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

    def _update_row(self, table, row_id, payload):
        if self.sb:
            res = self.sb.table(table).update(payload).eq("id", row_id).execute()
            return res.data or []
        return direct_db_query(table, "PATCH", payload, f"id=eq.{row_id}")
