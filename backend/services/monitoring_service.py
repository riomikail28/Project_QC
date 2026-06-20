"""Business logic for facility temperature monitoring."""

import logging
from datetime import datetime, timedelta, timezone

from backend.database.supabase_client import direct_db_query, get_last_db_error
from backend.services.alert_service import generate_temperature_alert, save_alert_to_db
from backend.services.audit_service import write_audit
from backend.services.base_service import BaseService
from backend.services.google_apps_script_service import send_monitoring_log
from backend.services.qc_engine import validate_temperature
from backend.services.storage_service import delete_photo, upload_file_storage

logger = logging.getLogger("qc.services.monitoring")


class MonitoringService(BaseService):
    def __init__(self, supabase_client, audit_writer=write_audit):
        super().__init__(supabase_client)
        self.audit_writer = audit_writer

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

            photo_urls = []
            storage_paths = []
            if data.photo_url:
                photo_urls.extend([item for item in str(data.photo_url).split(";") if item])
            if data.storage_path:
                storage_paths.extend([item for item in str(data.storage_path).split(";") if item])

            for photo_file in files.getlist("photo"):
                if photo_file:
                    uploaded = upload_file_storage(
                        photo_file, staff_id=staff_id, category="temperature", related_id=room_id
                    )
                    uploaded_files.append(uploaded)
                    photo_urls.append(uploaded.url)
                    storage_paths.append(uploaded.storage_path)

            photo_url = ";".join(photo_urls) if photo_urls else None
            storage_path = ";".join(storage_paths) if storage_paths else None
            threshold = target_temp

            recorded_at = datetime.now(timezone.utc).isoformat()
            log_payload = {
                "device_id": device_id or None,
                "room_id": room_id,
                "temperature_c": float(temperature),
                "threshold_c": threshold,
                "humidity_rh": float(humidity) if humidity not in (None, "") else None,
                "is_normal": is_normal,
                "staff_id": staff_id or None,
                "notes": reason,
                "photo_url": photo_url,
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
            if storage_path:
                log_payload["storage_path"] = storage_path

            try:
                inserted_rows = self._insert_rows("facility_logs", log_payload)
            except Exception:
                for uploaded in uploaded_files:
                    delete_photo(uploaded.storage_path)
                raise

            log_data = inserted_rows[0] if inserted_rows else None
            log_id = log_data.get("id") if log_data else None
            self.audit_writer(
                "submit_temperature", "facility_log", str(log_id) if log_id else None, after=log_data or log_payload
            )
            if uploaded_files:
                self.audit_writer(
                    "upload_temperature_photo",
                    "facility_log",
                    str(log_id) if log_id else None,
                    metadata={"storage_paths": [item.storage_path for item in uploaded_files]},
                )
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
                photo_url=photo_url,
                storage_path=storage_path,
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
            self._record_evidence(
                uploaded_files=uploaded_files,
                staff_id=staff_id,
                related_id=log_id,
                photo_urls=photo_urls,
                storage_paths=storage_paths,
                created_at=recorded_at,
            )

            alert = None
            if not is_normal:
                alert = generate_temperature_alert(room_name, unit_type, float(temperature), status.upper())
                if log_data:
                    save_alert_to_db(
                        zone=room_name,
                        temperature=float(temperature),
                        threshold=threshold,
                        log_id=log_data["id"],
                        device_id=device_id,
                    )

            send_monitoring_log(
                {
                    "date": monitoring_date or recorded_at[:10],
                    "slot_time": slot_time,
                    "room": room_name,
                    "device": (device_info or {}).get("name") or device_id,
                    "temperature": float(temperature),
                    "status": qc_status or status.upper(),
                    "staff_name": staff_id,
                    "submitted_at": submitted_at or recorded_at,
                    "notes": reason,
                }
            )

            return {
                "success": True,
                "message": "Temperature log saved",
                "status": qc_status or status.upper(),
                "computed_status": status,
                "alert": alert,
                "data": {
                    "log_id": log_id,
                    "photo_url": photo_url,
                    "storage_path": storage_path,
                },
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

    def _record_temperature_log(
        self,
        room_name,
        room_id,
        device_id,
        device_type,
        device_name,
        temperature,
        threshold,
        status,
        is_normal,
        photo_url,
        storage_path,
        staff_id,
        notes,
        recorded_at,
        log_id,
        monitoring_date=None,
        slot_time=None,
        schedule_status=None,
        submitted_at=None,
        is_late=None,
    ):
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
            rows.append(
                {
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
                }
            )
        if not rows and photo_urls:
            rows = [
                {
                    "bucket": "qc-evidence",
                    "public_url": url,
                    "uploaded_by": staff_id or None,
                    "related_type": "temperature",
                    "related_id": related_id,
                    "created_at": created_at,
                }
                for url in photo_urls
            ]
        for row in rows:
            try:
                self._insert_rows("qc_evidence", {k: v for k, v in row.items() if v is not None})
            except Exception:
                logger.warning("Temperature evidence metadata insert skipped", exc_info=True)

    def latest_logs(self):
        try:
            facility_columns = (
                "id,room_id,device_id,temperature_c,recorded_at,is_normal,notes,storage_path,photo_url,monitoring_date,slot_time,"
                "status,submitted_by,submitted_at,is_late,schedule_status,facility_rooms(name),facility_devices(name,type,threshold_temp)"
            )
            facility_fallback_columns = (
                "id,room_id,device_id,temperature_c,recorded_at,is_normal,notes,storage_path,photo_url,monitoring_date,slot_time,"
                "status,submitted_by,submitted_at,is_late,schedule_status"
            )
            temp_columns = (
                "id,room_id,device_id,temperature,status,notes,submitted_by,submitted_at,is_late,schedule_status,"
                "temperature_c,is_normal,recorded_at,storage_path,photo_url"
            )
            if self.sb:
                rows = []
                try:
                    res = (
                        self.sb.table("facility_logs")
                        .select(facility_columns)
                        .order("recorded_at", desc=True)
                        .limit(50)
                        .execute()
                    )
                    rows = res.data or []
                except Exception as exc:
                    logger.warning("Fetch facility logs with relations failed: %s", exc)
                    res = (
                        self.sb.table("facility_logs")
                        .select(facility_fallback_columns)
                        .order("recorded_at", desc=True)
                        .limit(50)
                        .execute()
                    )
                    rows = res.data or []
                if rows:
                    return rows
                temp_res = (
                    self.sb.table("temperature_logs")
                    .select(temp_columns)
                    .order("recorded_at", desc=True)
                    .limit(50)
                    .execute()
                )
                return temp_res.data or []
            try:
                rows = direct_db_query(
                    "facility_logs", "GET", None, f"select={facility_columns}&order=recorded_at.desc&limit=50"
                )
            except Exception as exc:
                logger.warning("Direct facility logs with relations failed: %s", exc)
                rows = direct_db_query(
                    "facility_logs", "GET", None, f"select={facility_fallback_columns}&order=recorded_at.desc&limit=50"
                )
            if rows:
                return rows
            return direct_db_query(
                "temperature_logs", "GET", None, f"select={temp_columns}&order=recorded_at.desc&limit=50"
            )
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
            select_cols = "*"
            for part in (filters or "").split("&"):
                if part.startswith("select="):
                    select_cols = part.split("=", 1)[1]
                    break
            query = self.sb.table(table).select(select_cols)
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

    def get_realtime_monitoring(self):
        if not self.sb:
            return self._empty([])
        try:
            try:
                res = (
                    self.sb.table("facility_logs")
                    .select(
                        "id,room_id,device_id,temperature_c,recorded_at,is_normal,notes,storage_path,photo_url,"
                        "monitoring_date,slot_time,status,submitted_by,submitted_at,is_late,schedule_status,"
                        "facility_rooms(name),facility_devices(name,type,device_type,threshold_temp)"
                    )
                    .order("recorded_at", desc=True)
                    .limit(50)
                    .execute()
                )
            except Exception as exc:
                logger.warning("Realtime facility_logs query failed, using temperature_logs: %s", exc)
                temp_columns = (
                    "id,room_id,device_id,temperature,status,notes,submitted_by,submitted_at,is_late,schedule_status,"
                    "temperature_c,is_normal,recorded_at,storage_path,photo_url"
                )
                res = (
                    self.sb.table("temperature_logs")
                    .select(temp_columns)
                    .order("recorded_at", desc=True)
                    .limit(50)
                    .execute()
                )
            latest = {}
            for row in res.data or []:
                key = row.get("device_id") or row.get("zone") or row.get("device_type") or row.get("id")
                latest.setdefault(key, row)
            devices = [
                {
                    "id": row.get("id"),
                    "name": (row.get("facility_devices") or {}).get("name")
                    or row.get("device_name")
                    or row.get("zone")
                    or row.get("device_type")
                    or "Temperature Point",
                    "type": (row.get("facility_devices") or {}).get("type")
                    or (row.get("facility_devices") or {}).get("device_type")
                    or row.get("device_type")
                    or "ambient",
                    "threshold_temp": row.get("threshold_c")
                    or (row.get("facility_devices") or {}).get("threshold_temp"),
                    "facility_rooms": {
                        "name": (row.get("facility_rooms") or {}).get("name") or row.get("zone") or "QC Area"
                    },
                    "latest_log": {
                        "temperature_c": row.get("temperature_c") or row.get("temperature"),
                        "humidity_rh": row.get("humidity_rh") or row.get("humidity"),
                        "is_normal": row.get("is_normal", not row.get("is_abnormal", False)),
                        "recorded_at": row.get("recorded_at"),
                        "photo_url": self.normalize_evidence_url(dict(row)).get("photo_url"),
                        "storage_path": row.get("storage_path"),
                        "notes": row.get("notes") or row.get("reason"),
                    },
                }
                for row in latest.values()
            ]
            return self._empty(devices)
        except Exception as exc:
            logger.error("Realtime monitoring failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def get_daily_monitoring(self, date=None):
        date = date or self._jakarta_today()
        slots = ("07:00", "13:00", "16:00", "19:00")
        try:
            rooms = self._fetch("facility_rooms", order_by="name", limit=1000)
            room_lookup = {str(room.get("id")): room for room in rooms}
            devices = self._fetch("facility_devices", order_by="name", limit=2000)
            logs = self._daily_temperature_rows(date, 5000)

            # Pre-parse timestamps and compute local minutes for logs once
            jakarta_tz = timezone(timedelta(hours=7))
            for log in logs:
                value = log.get("created_at") or log.get("submitted_at")
                if value:
                    try:
                        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                        local = dt.astimezone(jakarta_tz)
                        log["_local_minutes"] = local.hour * 60 + local.minute
                        log["_parsed_local"] = local
                    except Exception:
                        log["_local_minutes"] = None
                        log["_parsed_local"] = None
                else:
                    log["_local_minutes"] = None
                    log["_parsed_local"] = None

            logs_by_device = {}
            fallback_logs = {}
            for log in logs:
                key = str(log.get("device_id") or "")
                if key:
                    logs_by_device.setdefault(key, []).append(log)
                fallback_key = (str(log.get("room") or "").lower(), str(log.get("device") or "").lower())
                fallback_logs.setdefault(fallback_key, []).append(log)

            data = []
            for device in devices:
                room_id = device.get("room_id")
                room = room_lookup.get(str(room_id), {})
                room_name = room.get("name") or device.get("room_name") or "Unassigned"
                device_name = (
                    device.get("name") or device.get("device_name") or device.get("device_type") or "Temperature Point"
                )
                device_logs = logs_by_device.get(str(device.get("id") or ""), [])
                if not device_logs:
                    device_logs = fallback_logs.get((str(room_name).lower(), str(device_name).lower()), [])
                slot_rows = [self._daily_slot_row(slot, device_logs, date) for slot in slots]
                submitted = [slot for slot in slot_rows if slot.get("temperature") is not None]
                latest = max(submitted, key=lambda row: row.get("submitted_at") or "") if submitted else None
                data.append(
                    {
                        "device_id": device.get("id"),
                        "room_id": room_id,
                        "room": room_name,
                        "device_name": device_name,
                        "type": device.get("device_type") or device.get("type") or "room_temp",
                        "threshold_min": device.get("min_temperature"),
                        "threshold_max": device.get("max_temperature"),
                        "threshold_temp": device.get("threshold_temp"),
                        "latest_temperature": latest.get("temperature") if latest else None,
                        "latest_status": latest.get("status") if latest else None,
                        "daily_status": self._daily_device_status(slot_rows, date),
                        "slots": slot_rows,
                    }
                )

            return self._empty({"date": date, "devices": data})
        except Exception as exc:
            logger.error("Daily monitoring failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def _daily_slot_row(self, slot, logs, date):
        match = self._slot_log(logs, slot)
        if not match:
            return {
                "slot_time": slot,
                "temperature": None,
                "status": self._missing_slot_status(slot, date),
                "staff_name": None,
                "submitted_at": None,
                "photo_url": None,
                "notes": None,
            }
        status = str(match.get("status") or "").upper()
        if status in {"FAIL", "WARNING"} or str(match.get("is_normal", "")).lower() == "false":
            normalized_status = "WARNING"
        else:
            normalized_status = "PASS"
        return {
            "slot_time": slot,
            "temperature": match.get("temperature"),
            "status": normalized_status,
            "staff_name": match.get("staff_display_name") or match.get("staff_name"),
            "submitted_at": match.get("created_at") or match.get("submitted_at"),
            "photo_url": match.get("photo_url"),
            "notes": match.get("notes"),
        }

    def _slot_log(self, logs, slot):
        exact = [row for row in logs if str(row.get("slot_time") or "")[:5] == slot]
        if exact:
            return max(exact, key=lambda row: row.get("created_at") or row.get("submitted_at") or "")
        target = int(slot[:2]) * 60 + int(slot[3:])
        best = None
        best_diff = 9999
        for row in logs:
            local_mins = row.get("_local_minutes")
            if local_mins is None:
                value = row.get("created_at") or row.get("submitted_at")
                if not value:
                    continue
                try:
                    date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                    local = date.astimezone(timezone(timedelta(hours=7)))
                    local_mins = local.hour * 60 + local.minute
                except Exception:
                    continue
            diff = abs(local_mins - target)
            if diff <= 120 and diff < best_diff:
                best = row
                best_diff = diff
        return best

    def _missing_slot_status(self, slot, date):
        today = self._jakarta_today()
        if date < today:
            return "MISSED"
        if date > today:
            return "BELUM_INPUT"
        now = datetime.now(timezone(timedelta(hours=7)))
        slot_time = datetime.fromisoformat(f"{date}T{slot}:00").replace(tzinfo=timezone(timedelta(hours=7)))
        return "MISSED" if now > slot_time else "BELUM_INPUT"

    def _daily_device_status(self, slots, date):
        statuses = {str(slot.get("status") or "").upper() for slot in slots}
        if "WARNING" in statuses or "FAIL" in statuses:
            return "WARNING"
        if "MISSED" in statuses:
            return "MISSED"
        if "BELUM_INPUT" in statuses:
            return "PENDING"
        return "PASS"

    def _daily_temperature_rows(self, date, limit):
        rows = self._fetch_daily_candidates(
            "facility_logs",
            date,
            limit,
            timestamp_fields=("recorded_at", "submitted_at", "created_at"),
            date_fields=("monitoring_date",),
            order_by="recorded_at",
        )
        if not rows:
            rows = self._fetch_daily_candidates(
                "temperature_logs",
                date,
                limit,
                timestamp_fields=("recorded_at", "submitted_at", "created_at"),
                date_fields=("monitoring_date",),
                order_by="recorded_at",
            )
        self._prefetch_for_rows(rows, ("staff_id", "created_by", "submitted_by", "operator_id"))
        return [self._temperature_report_row(row) for row in rows[:limit]]

    def _temperature_report_row(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by"))
        room = (
            row.get("zone")
            or row.get("room_name")
            or (row.get("facility_rooms") or {}).get("name")
            or row.get("room_id")
        )
        device = (
            row.get("device_name")
            or row.get("device_type")
            or (row.get("facility_devices") or {}).get("name")
            or row.get("device_id")
        )
        raw_status = row.get("status")
        normalized_status = (
            str(raw_status).lower()
            if raw_status
            else ("pass" if row.get("is_normal", not row.get("is_abnormal", False)) else "fail")
        )
        staff_name = row.get("staff_name")
        if self._is_uuid_like(staff_name):
            staff_name = item.get("staff_display_name")
        return self.normalize_evidence_url(
            {
                "id": row.get("id"),
                "staff_id": item.get("staff_id") or row.get("created_by"),
                "staff_name": staff_name,
                "staff_display_name": item.get("staff_display_name"),
                "staff_role": item.get("staff_role"),
                "staff_email": item.get("staff_email"),
                "room_id": row.get("room_id"),
                "room": room,
                "device_id": row.get("device_id"),
                "device": device,
                "device_type": row.get("device_type")
                or (row.get("facility_devices") or {}).get("type")
                or (row.get("facility_devices") or {}).get("device_type"),
                "temperature": row.get("temperature_c") or row.get("temperature"),
                "humidity": row.get("humidity_rh") or row.get("humidity"),
                "status": normalized_status,
                "slot_time": row.get("slot_time"),
                "photo_url": row.get("photo_url"),
                "storage_path": row.get("storage_path"),
                "notes": row.get("reason") or row.get("notes"),
                "created_at": row.get("recorded_at") or row.get("created_at"),
                "submitted_at": row.get("submitted_at") or row.get("recorded_at") or row.get("created_at"),
            }
        )
