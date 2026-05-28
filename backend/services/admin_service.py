import logging
import csv
import io
import os
from datetime import datetime, timedelta, timezone

from backend.database.supabase_client import get_client
from backend.qc.product_catalog import CENTRAL_KITCHEN_PRODUCTS
from backend.services.google_apps_script_service import send_monitoring_log, send_qc_report

logger = logging.getLogger("qc.services.admin")


class AdminService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def _empty(self, data):
        return {"success": True, "data": data, "message": "OK"}

    def _fail(self, message):
        return {"success": False, "data": None, "message": message, "detail": message}

    def _first_non_empty(self, *values):
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return value
        return None

    def _staff_identity(self, row, id_fields=("staff_id", "actor_id", "created_by", "operator_id", "uploaded_by", "requested_by")):
        row = row or {}
        nested_sources = (
            row.get("staff_accounts"),
            row.get("users"),
            row.get("profile"),
            row.get("staff_profile"),
            row.get("staff"),
        )
        nested_values = []
        for source in nested_sources:
            if isinstance(source, dict):
                nested_values.extend([
                    source.get("full_name"),
                    source.get("name"),
                    source.get("username"),
                    source.get("email"),
                ])
        direct_values = [
            row.get("staff_display_name"),
            row.get("actor_display_name"),
            row.get("full_name"),
            row.get("name"),
            row.get("username"),
            row.get("email"),
            row.get("staff_name"),
            row.get("inspector_name"),
            row.get("actor_name"),
        ]
        staff_id = self._first_non_empty(*(row.get(field) for field in id_fields))
        display_name = self._first_non_empty(*(nested_values + direct_values), staff_id)
        return display_name, staff_id

    def _with_staff_display(self, row, id_fields=("staff_id", "actor_id", "created_by", "operator_id", "uploaded_by", "requested_by")):
        item = dict(row or {})
        display_name, staff_id = self._staff_identity(item, id_fields)
        if staff_id and not item.get("staff_id") and "staff_id" in id_fields:
            item["staff_id"] = staff_id
        item["staff_display_name"] = display_name
        return item

    def _count(self, table: str, filters: list[tuple[str, str, object]] | None = None) -> int:
        if not self.sb:
            return 0
        query = self.sb.table(table).select("id", count="exact")
        for op, field, value in filters or []:
            query = getattr(query, op)(field, value)
        res = query.execute()
        return res.count if getattr(res, "count", None) is not None else len(res.data or [])

    def get_dashboard_overview(self):
        try:
            from backend.services.dashboard_service import DashboardService
            summary = DashboardService(self.sb).summary().get("data", {})
            data = {
                "total_batches_today": summary.get("total_batches_today", 0),
                "total_failed_batches": self._count("qc_reports", [("eq", "status", "failed")]),
                "total_qc_pending": summary.get("pending_approval", 0),
                "total_qc_completed": self._count("qc_reports", [("neq", "approval_status", "pending")]),
                "total_open_alerts": summary.get("total_alerts", 0),
                "total_active_staff": self._count("staff_activity", [("gte", "created_at", f"{datetime.now(timezone.utc).date().isoformat()}T00:00:00Z")]),
                "qc_success_rate": summary.get("qc_success_rate"),
            }
            return self._empty(data)
        except Exception as exc:
            logger.error("Dashboard overview failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def get_realtime_monitoring(self):
        if not self.sb:
            return self._empty([])
        try:
            try:
                res = (
                    self.sb.table("facility_logs")
                    .select("*, facility_rooms(name), facility_devices(name,type,device_type,threshold_temp)")
                    .order("recorded_at", desc=True)
                    .limit(50)
                    .execute()
                )
            except Exception as exc:
                logger.warning("Realtime facility_logs query failed, using temperature_logs: %s", exc)
                res = (
                    self.sb.table("temperature_logs")
                    .select("*")
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
                    "name": (row.get("facility_devices") or {}).get("name") or row.get("device_name") or row.get("zone") or row.get("device_type") or "Temperature Point",
                    "type": (row.get("facility_devices") or {}).get("type") or (row.get("facility_devices") or {}).get("device_type") or row.get("device_type") or "ambient",
                    "threshold_temp": row.get("threshold_c") or (row.get("facility_devices") or {}).get("threshold_temp"),
                    "facility_rooms": {"name": (row.get("facility_rooms") or {}).get("name") or row.get("zone") or "QC Area"},
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

    def get_qc_reports(self, page=1, limit=20, status_filter=None):
        if not self.sb:
            return {"success": True, "data": [], "count": 0}
        try:
            offset = (page - 1) * limit
            query = self.sb.table("qc_reports").select("*", count="exact")
            if status_filter:
                query = query.eq("status", status_filter)
            query = query.order("created_at", desc=True)
            if hasattr(query, "range"):
                query = query.range(offset, offset + limit - 1)
            else:
                query = query.limit(limit)
            report_res = query.execute()
            reports = [self._normalize_qc_report(row) for row in (report_res.data or [])]

            finding_query = self.sb.table("qc_findings").select("*").order("created_at", desc=True)
            if hasattr(finding_query, "range"):
                finding_query = finding_query.range(offset, offset + limit - 1)
            else:
                finding_query = finding_query.limit(limit)
            finding_res = finding_query.execute()
            findings = [
                self._normalize_qc_finding(row)
                for row in (finding_res.data or [])
                if self._include_finding_for_status(row, status_filter)
            ]

            combined = sorted(
                reports + findings,
                key=lambda row: row.get("created_at") or "",
                reverse=True,
            )
            return {
                "success": True,
                "data": combined[:limit],
                "count": (getattr(report_res, "count", None) or len(reports)) + len(findings),
            }
        except Exception as exc:
            logger.error("QC reports failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def _normalize_qc_report(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by", "operator_id"))
        item.setdefault("report_type", "qc_report")
        item.setdefault("display_title", item.get("batch_code") or item.get("batch_id") or "QC Report")
        item["qc_stage"] = item.get("qc_stage") or item.get("ccp_stage")
        item["staff_name"] = item.get("staff_name") or item.get("inspector_name") or item.get("staff_display_name")
        item["product_code"] = item.get("product_code") or item.get("sku_code") or item.get("barcode")
        item["photo_url"] = (
            item.get("photo_url")
            or item.get("cooking_photo_url")
            or item.get("barcode_photo_url")
            or item.get("label_photo_url")
            or item.get("product_photo_url")
            or item.get("temperature_photo_url")
        )
        self.normalize_evidence_url(item)
        for prefix in ("cooking", "barcode", "label"):
            url_key = f"{prefix}_photo_url"
            path_key = f"{prefix}_storage_path"
            if not item.get(url_key) and item.get(path_key):
                item[url_key] = self._signed_storage_url(item.get(path_key), item.get("bucket") or "qc-evidence") or self._public_storage_url(item.get(path_key), item.get("bucket") or "qc-evidence")
        return item

    def _normalize_qc_finding(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by", "operator_id"))
        item["report_type"] = "qc_finding"
        item["status"] = item.get("status") or "finding"
        item["approval_status"] = item.get("approval_status") or "pending"
        item["display_title"] = item.get("reason") or "QC Finding"
        item["product_name"] = item.get("product_name") or "QC Finding"
        item["inspector_name"] = item.get("inspector_name") or item.get("staff_name") or item.get("staff_display_name")
        self.normalize_evidence_url(item)
        return item

    def _include_finding_for_status(self, row, status_filter):
        if not status_filter:
            return True
        status = (row.get("status") or "finding").lower()
        approval_status = (row.get("approval_status") or "pending").lower()
        return status_filter.lower() in {status, approval_status, "finding"}

    def get_traceability(self, barcode=None, limit=50):
        try:
            rows = self._fetch("barcode_labels", order_by="created_at", limit=limit)
            if barcode:
                rows = [row for row in rows if row.get("barcode_value") == barcode]
            if not rows:
                rows = self._traceability_from_staff_submissions(limit)
                if barcode:
                    needle = barcode.lower()
                    rows = [
                        row for row in rows
                        if needle in str(row.get("barcode_value") or "").lower()
                        or needle in str(row.get("batch_code") or row.get("batch_id") or "").lower()
                    ]
            return self._empty(rows[:limit])
        except Exception as exc:
            logger.error("Traceability failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def get_pending_approvals(self, limit=50):
        try:
            rows = self._fetch("approvals", order_by="created_at", limit=limit, filters=[("eq", "status", "pending")])
            if rows:
                return self._empty([self._approval_with_related(row) for row in rows[:limit]])

            rows = []
            reports = self._fetch("qc_reports", order_by="created_at", limit=limit)
            rows.extend(self._approval_from_qc_report(row) for row in reports if self._needs_approval(row))
            findings = self._fetch("qc_findings", order_by="created_at", limit=limit)
            rows.extend(self._approval_from_finding(row) for row in findings if self._needs_approval(row, default=True))
            temp_logs = self._fetch("facility_logs", order_by="recorded_at", limit=limit)
            if not temp_logs:
                temp_logs = self._fetch("temperature_logs", order_by="recorded_at", limit=limit)
            rows.extend(self._approval_from_temperature(row) for row in temp_logs if self._temperature_needs_review(row))

            rows = sorted(rows, key=lambda row: row.get("created_at") or "", reverse=True)
            return self._empty(rows[:limit])
        except Exception as exc:
            logger.error("Approvals failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def get_audit_trail(self, limit=50, date=None, action=None, user=None):
        try:
            filters = self._date_filters("created_at", date)
            if action:
                filters.append(("eq", "action", action))
            if user:
                filters.append(("eq", "actor_id", user))
            rows = self._fetch("audit_logs", select="*", order_by="created_at", limit=limit, filters=filters)
            if not rows:
                rows = self._audit_from_staff_submissions(limit)
                if date:
                    rows = [row for row in rows if str(row.get("created_at") or "").startswith(date)]
                if action:
                    rows = [row for row in rows if row.get("action") == action]
                if user:
                    rows = [row for row in rows if user in {row.get("actor_id"), row.get("staff_id")}]
            actor_profiles = self._actor_profiles(rows[:limit])
            return self._empty([self._normalize_audit_row(row, actor_profiles) for row in rows[:limit]])
        except Exception as exc:
            logger.error("Audit trail failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def _date_filters(self, field, date_value):
        if not date_value:
            return []
        start = f"{date_value}T00:00:00Z"
        end = (datetime.fromisoformat(date_value) + timedelta(days=1)).date().isoformat() + "T00:00:00Z"
        return [("gte", field, start), ("lte", field, end)]

    def get_temperature_report(self, limit=100, date=None, staff_id=None, status_filter=None):
        filters = self._date_filters("recorded_at", date)
        if staff_id:
            filters.append(("eq", "staff_id", staff_id))
        rows = self._fetch(
            "facility_logs",
            select="*, facility_rooms(name), facility_devices(name,type,threshold_temp)",
            order_by="recorded_at",
            limit=limit,
            filters=filters,
        )
        if not rows:
            rows = self._fetch("temperature_logs", order_by="recorded_at", limit=limit, filters=filters)
        data = [self._temperature_report_row(row) for row in rows]
        if status_filter:
            data = [row for row in data if str(row.get("status", "")).lower() == status_filter.lower()]
        return self._empty(data)

    def get_alert_report(self, limit=100):
        rows = self._fetch("facility_alerts", order_by="created_at", limit=limit)
        data = []
        for row in rows:
            item = self._with_staff_display(row, ("staff_id", "created_by", "resolved_by"))
            data.append({
                "id": item.get("id"),
                "created_at": item.get("created_at"),
                "room": item.get("zone") or item.get("room") or item.get("room_name"),
                "device": item.get("device_name") or item.get("device_id"),
                "temperature": item.get("temperature") or item.get("temperature_c"),
                "status": item.get("status") or item.get("severity") or "warning",
                "message": item.get("message") or item.get("title") or item.get("corrective_action"),
                "staff_id": item.get("staff_id") or item.get("created_by") or item.get("resolved_by"),
                "staff_display_name": item.get("staff_display_name"),
            })
        return self._empty(data)

    def export_google_sheets_monitoring(self, start_date=None, end_date=None, limit=5000):
        rows = self.get_temperature_report(limit=limit).get("data", [])
        rows = self._filter_rows_by_date(rows, start_date, end_date, "created_at")
        summary = self._export_summary("monitoring")
        for row in rows:
            payload = self._google_sheets_monitoring_payload(row)
            if not payload.get("source_id"):
                summary["skipped"] += 1
                continue
            if send_monitoring_log(payload):
                summary["exported"] += 1
            else:
                self._record_export_failure(summary, payload)
        return self._finalize_export_summary(summary)

    def export_google_sheets_qc(self, start_date=None, end_date=None, limit=5000):
        reports = self.get_inspection_report(limit=limit).get("data", [])
        findings = self.get_findings_report(limit=limit).get("data", [])
        rows = self._filter_rows_by_date(reports + findings, start_date, end_date, "created_at")
        summary = self._export_summary("qc")
        for row in rows:
            payload = self._google_sheets_qc_payload(row)
            if not payload.get("source_id"):
                summary["skipped"] += 1
                continue
            if send_qc_report(payload):
                summary["exported"] += 1
            else:
                self._record_export_failure(summary, payload)
        return self._finalize_export_summary(summary)

    def _export_summary(self, export_type):
        return {
            "success": True,
            "status": "success",
            "export_type": export_type,
            "exported": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

    def _record_export_failure(self, summary, payload):
        summary["failed"] += 1
        if len(summary["errors"]) < 5:
            summary["errors"].append({
                "source_type": payload.get("source_type"),
                "source_id": payload.get("source_id"),
                "message": "Google Apps Script webhook failed",
            })

    def _finalize_export_summary(self, summary):
        if summary["failed"] and summary["exported"]:
            summary["success"] = False
            summary["status"] = "partial"
        elif summary["failed"]:
            summary["success"] = False
            summary["status"] = "failed"
        return summary

    def _filter_rows_by_date(self, rows, start_date=None, end_date=None, date_field="created_at"):
        if not start_date and not end_date:
            return rows
        filtered = []
        for row in rows:
            row_date = str(row.get(date_field) or row.get("submitted_at") or "")[:10]
            if start_date and row_date < start_date:
                continue
            if end_date and row_date > end_date:
                continue
            filtered.append(row)
        return filtered

    def _google_sheets_monitoring_payload(self, row):
        submitted_at = row.get("created_at") or row.get("submitted_at")
        return {
            "date": row.get("date") or row.get("monitoring_date") or str(submitted_at or "")[:10],
            "slot_time": row.get("slot_time") or "",
            "room": row.get("room") or row.get("room_name") or "",
            "device": row.get("device") or row.get("device_name") or row.get("device_id") or "",
            "temperature": row.get("temperature"),
            "status": row.get("status"),
            "staff_name": row.get("staff_display_name") or row.get("staff_name") or row.get("staff_id") or "",
            "submitted_at": submitted_at,
            "notes": row.get("notes") or "",
            "source_type": "monitoring_log",
            "source_id": row.get("id"),
        }

    def _google_sheets_qc_payload(self, row):
        return {
            "batch_id": row.get("batch_id") or row.get("id"),
            "batch_code": row.get("batch_code") or row.get("barcode") or row.get("batch_id") or "",
            "product_name": row.get("product_name") or "",
            "status": row.get("status") or row.get("approval_status") or "",
            "temperature": row.get("temperature"),
            "photo_url": row.get("photo_url") or row.get("product_photo_url") or row.get("temperature_photo_url"),
            "staff_name": row.get("staff_display_name") or row.get("staff_name") or row.get("inspector_name") or row.get("staff_id") or "",
            "created_at": row.get("created_at"),
            "notes": row.get("notes") or row.get("reason") or "",
            "source_type": row.get("report_type") or "qc_report",
            "source_id": row.get("id"),
        }

    def get_inspection_report(self, limit=100, status_filter=None, date=None, staff_id=None):
        filters = self._date_filters("created_at", date)
        if status_filter:
            filters.append(("eq", "status", status_filter))
        if staff_id:
            filters.append(("eq", "staff_id", staff_id))
        rows = self._fetch("qc_reports", order_by="created_at", limit=limit, filters=filters)
        return self._empty([self._normalize_qc_report(row) for row in rows])

    def get_findings_report(self, limit=100, date=None, staff_id=None, status_filter=None):
        filters = self._date_filters("created_at", date)
        if staff_id:
            filters.append(("eq", "staff_id", staff_id))
        rows = self._fetch("qc_findings", order_by="created_at", limit=limit, filters=filters)
        data = [self._normalize_qc_finding(row) for row in rows]
        if status_filter:
            needle = status_filter.lower()
            data = [row for row in data if needle in {str(row.get("status") or "").lower(), str(row.get("approval_status") or "").lower(), "finding"}]
        return self._empty(data)

    def get_evidence_report(self, limit=100, date=None, staff_id=None):
        filters = self._date_filters("created_at", date)
        if staff_id:
            filters.append(("eq", "uploaded_by", staff_id))
        rows = self._fetch("qc_evidence", order_by="created_at", limit=limit, filters=filters)
        if not rows:
            report_rows = self._fetch("qc_reports", order_by="created_at", limit=limit, filters=self._date_filters("created_at", date))
            rows = self._evidence_from_reports(report_rows)
            temp_rows = self._fetch("facility_logs", order_by="recorded_at", limit=limit, filters=self._date_filters("recorded_at", date))
            rows.extend(self._evidence_from_temperature(temp_rows))
        normalized = []
        for row in rows[:limit]:
            item = dict(row or {})
            self.normalize_evidence_url(item)
            normalized.append(item)
        return self._empty(normalized)

    def normalize_evidence_url(self, record):
        url = (
            record.get("public_url")
            or record.get("signed_url")
            or record.get("photo_url")
            or record.get("product_photo_url")
            or record.get("temperature_photo_url")
            or record.get("barcode_photo_url")
        )
        storage_path = record.get("storage_path") or record.get("product_storage_path") or record.get("temperature_storage_path") or record.get("barcode_storage_path")
        if not url and storage_path:
            url = self._signed_storage_url(storage_path, record.get("bucket") or "qc-evidence") or self._public_storage_url(storage_path, record.get("bucket") or "qc-evidence")
        record["photo_url"] = url
        record["storage_path"] = storage_path
        record["has_photo"] = bool(url)
        return record

    def _signed_storage_url(self, storage_path, bucket="qc-evidence"):
        first_path = str(storage_path or "").split(";")[0].strip()
        if not first_path or first_path.startswith(("http://", "https://")):
            return first_path or None
        try:
            storage = getattr(self.sb, "storage", None)
            if not storage or not hasattr(storage, "from_"):
                return None
            result = storage.from_(bucket).create_signed_url(first_path.lstrip("/"), 3600)
            if isinstance(result, dict):
                return result.get("signedURL") or result.get("signed_url") or result.get("url")
            return getattr(result, "signed_url", None) or getattr(result, "signedURL", None) or getattr(result, "url", None)
        except Exception as exc:
            logger.warning("Signed evidence URL generation skipped: %s", exc)
            return None

    def _public_storage_url(self, storage_path, bucket="qc-evidence"):
        first_path = str(storage_path or "").split(";")[0].strip()
        if not first_path:
            return None
        if first_path.startswith("http://") or first_path.startswith("https://"):
            return first_path
        base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        if not base:
            return None
        return f"{base}/storage/v1/object/public/{bucket}/{first_path.lstrip('/')}"

    def get_daily_staff_report(self, date=None, staff_id=None, status_filter=None, limit=500):
        date = date or datetime.now(timezone.utc).date().isoformat()
        temperature = self.get_temperature_report(limit=limit, date=date, staff_id=staff_id, status_filter=status_filter).get("data", [])
        inspection = self.get_inspection_report(limit=limit, date=date, staff_id=staff_id, status_filter=status_filter).get("data", [])
        findings = self.get_findings_report(limit=limit, date=date, staff_id=staff_id, status_filter=status_filter).get("data", [])
        evidence = self.get_evidence_report(limit=limit, date=date, staff_id=staff_id).get("data", [])
        approval_filters = self._date_filters("created_at", date)
        if staff_id:
            approval_filters.append(("eq", "requested_by", staff_id))
        approvals = self._fetch("approvals", order_by="created_at", limit=limit, filters=approval_filters)
        rows = []
        rows.extend(self._daily_temperature_row(row) for row in temperature)
        rows.extend(self._daily_inspection_row(row) for row in inspection)
        rows.extend(self._daily_finding_row(row) for row in findings)
        rows = sorted(rows, key=lambda row: row.get("created_at") or "", reverse=True)
        return self._empty({
            "date": date,
            "summary": {
                "temperature_logs": len(temperature),
                "inspection_reports": len(inspection),
                "findings": len(findings),
                "evidence": len(evidence),
                "approvals_pending": len([row for row in approvals if str(row.get("status") or "").lower() == "pending"])
                or len([row for row in inspection if str(row.get("approval_status") or "").lower() == "pending"]),
                "approvals_approved": len([row for row in approvals if str(row.get("status") or "").lower() == "approved"])
                or len([row for row in inspection if str(row.get("approval_status") or "").lower() == "approved"]),
                "approvals_rejected": len([row for row in approvals if str(row.get("status") or "").lower() == "rejected"])
                or len([row for row in inspection if str(row.get("approval_status") or "").lower() == "rejected"]),
                "temperature": len(temperature),
                "inspection": len(inspection),
            },
            "temperature": temperature,
            "inspection": inspection,
            "findings": findings,
            "evidence": evidence,
            "rows": rows[:limit],
        })

    def export_daily_report_csv(self, date=None, staff_id=None, status_filter=None):
        report = self.get_daily_staff_report(date=date, staff_id=staff_id, status_filter=status_filter, limit=2000)
        data = report.get("data") or {}
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "Date", "Time", "Report Type", "Staff", "Room", "Device", "SKU/Barcode",
            "Product", "Temperature", "QC Status", "Approval Status", "Notes", "Photo URL",
        ])
        writer.writeheader()
        for row in data.get("rows", []):
            writer.writerow({
                "Date": data.get("date"),
                "Time": str(row.get("created_at") or "")[11:19],
                "Report Type": row.get("type"),
                "Staff": row.get("staff"),
                "Room": row.get("room"),
                "Device": row.get("device"),
                "SKU/Barcode": row.get("sku"),
                "Product": row.get("product"),
                "Temperature": row.get("temperature"),
                "QC Status": row.get("status"),
                "Approval Status": row.get("approval_status"),
                "Notes": row.get("notes"),
                "Photo URL": row.get("photo_url"),
            })
        return output.getvalue()

    def _daily_temperature_row(self, row):
        return {
            "type": "temperature",
            "staff": row.get("staff_display_name") or row.get("staff_name") or row.get("staff_id") or "-",
            "room": row.get("room"),
            "device": row.get("device"),
            "sku": "",
            "product": "",
            "temperature": row.get("temperature"),
            "status": row.get("status"),
            "approval_status": "",
            "notes": row.get("notes"),
            "photo_url": row.get("photo_url"),
            "created_at": row.get("created_at"),
        }

    def _daily_inspection_row(self, row):
        return {
            "type": "inspection",
            "staff": row.get("staff_display_name") or row.get("inspector_name") or row.get("staff_name") or row.get("staff_id") or "-",
            "room": "",
            "device": "",
            "sku": row.get("barcode") or row.get("batch_code") or row.get("batch_id"),
            "product": row.get("product_name"),
            "temperature": row.get("temperature"),
            "status": row.get("status"),
            "approval_status": row.get("approval_status"),
            "notes": row.get("notes") or row.get("qc_stage") or row.get("ccp_stage"),
            "photo_url": row.get("photo_url") or row.get("product_photo_url"),
            "created_at": row.get("created_at"),
        }

    def _daily_finding_row(self, row):
        return {
            "type": "finding",
            "staff": row.get("staff_display_name") or row.get("inspector_name") or row.get("staff_name") or row.get("staff_id") or "-",
            "room": "",
            "device": "",
            "sku": row.get("batch_code") or "",
            "product": row.get("product_name") or "QC Finding",
            "temperature": "",
            "status": row.get("status") or row.get("approval_status") or "finding",
            "approval_status": row.get("approval_status"),
            "notes": row.get("reason"),
            "photo_url": row.get("photo_url"),
            "created_at": row.get("created_at"),
        }

    def get_batch_report(self, limit=100):
        rows = self._fetch("production_batches", select="*, products(*)", order_by="created_at", limit=limit)
        data = []
        for row in rows:
            item = self._with_staff_display(row, ("staff_id", "created_by", "operator_id", "qc_officer_id"))
            data.append({
                "id": item.get("id"),
                "batch_code": item.get("batch_code"),
                "product_name": item.get("product_name") or (item.get("products") or {}).get("product_name"),
                "batch_sequence": item.get("batch_sequence"),
                "quantity": item.get("quantity"),
                "cook_name": item.get("cook_name"),
                "production_shift": item.get("production_shift") or item.get("shift"),
                "production_date": item.get("production_date"),
                "expired_date": item.get("expired_date"),
                "status": item.get("status") or item.get("final_qc_status") or "pending",
                "created_by": item.get("created_by") or item.get("operator_id"),
                "staff_id": item.get("staff_id") or item.get("created_by") or item.get("operator_id"),
                "staff_display_name": item.get("staff_display_name"),
                "ph_value": item.get("ph_value"),
                "ph_status": item.get("ph_status") or "not_checked",
                "brix_value": item.get("brix_value"),
                "brix_status": item.get("brix_status") or "not_checked",
                "tds_value": item.get("tds_value"),
                "tds_status": item.get("tds_status") or "not_checked",
                "parameter_notes": item.get("parameter_notes"),
                "parameter_checked_by": item.get("parameter_checked_by"),
                "parameter_checked_at": item.get("parameter_checked_at"),
                "created_at": item.get("created_at"),
            })
        return self._empty(data)

    def get_staff_activity_report(self, limit=100):
        rows = self._fetch("staff_activity", order_by="created_at", limit=limit)
        if not rows:
            rows = self._audit_from_staff_submissions(limit)
        return self._empty(rows[:limit])

    def approve_item(self, approval_id, actor_id=None, comment=None, approved=True):
        status = "approved" if approved else "rejected"
        approved_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "status": status,
            "approval_status": status,
            "approved_by": actor_id,
            "approved_at": approved_at,
        }
        if not approved:
            payload["rejection_reason"] = comment or "Rejected by admin"
        approval_update = {"status": status, "comment": comment, "approved_by": actor_id, "approved_at": approved_at}
        if not approved:
            approval_update["rejection_reason"] = comment or "Rejected by admin"
        approval_rows = self._update_by_id("approvals", approval_id, approval_update)
        rows = approval_rows
        related_id = None
        if approval_rows:
            related_id = approval_rows[0].get("related_id") or approval_rows[0].get("report_id")
        if not approval_rows:
            existing = self._fetch("approvals", limit=1, filters=[("eq", "related_id", approval_id)])
            if existing:
                related_id = approval_id
                rows = self._update_by_id("approvals", existing[0].get("id"), approval_update)
        if related_id:
            report_rows = self._update_by_id("qc_reports", related_id, payload)
            rows = report_rows or rows
        if not related_id and not rows:
            report_rows = self._update_by_id("qc_reports", approval_id, payload)
            if report_rows:
                related_id = approval_id
                rows = report_rows
        if not rows:
            return self._fail("Approval item not found")
        try:
            from backend.services.audit_service import write_audit
            write_audit("approve_qc" if approved else "reject_qc", "qc_report", related_id or approval_id, after=payload)
        except Exception:
            pass
        return self._empty(rows[0])

    def _update_by_id(self, table, row_id, payload):
        if not self.sb:
            return []
        try:
            return self.sb.table(table).update({k: v for k, v in payload.items() if v is not None}).eq("id", row_id).execute().data or []
        except Exception as exc:
            logger.warning("Admin update skipped for %s: %s", table, exc)
            return []

    def _temperature_report_row(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by"))
        room = row.get("zone") or row.get("room_name") or (row.get("facility_rooms") or {}).get("name") or row.get("room_id")
        device = row.get("device_name") or row.get("device_type") or (row.get("facility_devices") or {}).get("name") or row.get("device_id")
        raw_status = row.get("status")
        normalized_status = str(raw_status).lower() if raw_status else ("pass" if row.get("is_normal", not row.get("is_abnormal", False)) else "fail")
        return self.normalize_evidence_url({
            "id": row.get("id"),
            "staff_id": item.get("staff_id") or row.get("created_by"),
            "staff_name": row.get("staff_name"),
            "staff_display_name": item.get("staff_display_name"),
            "room_id": row.get("room_id"),
            "room": room,
            "device_id": row.get("device_id"),
            "device": device,
            "device_type": row.get("device_type") or (row.get("facility_devices") or {}).get("type") or (row.get("facility_devices") or {}).get("device_type"),
            "temperature": row.get("temperature_c") or row.get("temperature"),
            "humidity": row.get("humidity_rh") or row.get("humidity"),
            "status": normalized_status,
            "photo_url": row.get("photo_url"),
            "storage_path": row.get("storage_path"),
            "notes": row.get("reason") or row.get("notes"),
            "created_at": row.get("recorded_at") or row.get("created_at"),
        })

    def _evidence_from_reports(self, rows):
        evidence = []
        for row in rows:
            urls = row.get("product_photo_url") or row.get("temperature_photo_url") or row.get("barcode_photo_url") or row.get("photo_url")
            paths = row.get("product_storage_path") or row.get("temperature_storage_path") or row.get("barcode_storage_path") or row.get("storage_path")
            if urls or paths:
                evidence.append({
                    "related_type": "inspection",
                    "related_id": row.get("id"),
                    "public_url": urls,
                    "storage_path": paths,
                    "uploaded_by": row.get("staff_id"),
                    "created_at": row.get("created_at"),
                })
        return evidence

    def _evidence_from_temperature(self, rows):
        evidence = []
        for row in rows:
            if row.get("photo_url") or row.get("storage_path"):
                evidence.append({
                    "related_type": "temperature",
                    "related_id": row.get("id"),
                    "public_url": row.get("photo_url"),
                    "storage_path": row.get("storage_path"),
                    "uploaded_by": row.get("staff_id"),
                    "created_at": row.get("recorded_at") or row.get("created_at"),
                })
        return evidence

    def _fetch(self, table, select="*", order_by=None, desc=True, limit=None, filters=None):
        if not self.sb:
            return []
        try:
            query = self.sb.table(table).select(select)
            for op, field, value in filters or []:
                query = getattr(query, op)(field, value)
            if order_by:
                query = query.order(order_by, desc=desc)
            if limit:
                query = query.limit(limit)
            return query.execute().data or []
        except Exception as exc:
            logger.warning("Admin fallback query skipped for %s: %s", table, exc)
            return []

    def _needs_approval(self, row, default=False):
        status = str(row.get("approval_status") or row.get("status") or "").lower()
        return status in {"", "pending", "hold", "warning", "finding", "fail", "failed"} or (default and not status)

    def _temperature_needs_review(self, row):
        if row.get("is_normal") is False or row.get("is_abnormal") is True:
            return True
        return bool(row.get("reason") or row.get("photo_url") or row.get("storage_path"))

    def _approval_from_qc_report(self, row):
        item = dict(row or {})
        item.setdefault("approval_id", item.get("id"))
        item.setdefault("source", "qc_report")
        item.setdefault("approval_status", item.get("approval_status") or "pending")
        item.setdefault("status", item.get("status") or "pending")
        item.setdefault("qc_stage", item.get("ccp_stage"))
        item.setdefault("inspector_name", item.get("inspector_name") or item.get("staff_name") or item.get("staff_id") or item.get("operator_id"))
        item.setdefault("product_photo_url", item.get("product_photo_url") or item.get("photo_url"))
        return item

    def _approval_with_related(self, row):
        item = dict(row or {})
        related_type = item.get("related_type")
        related_id = item.get("related_id") or item.get("report_id")
        if related_type == "qc_report" and related_id:
            reports = self._fetch("qc_reports", limit=1, filters=[("eq", "id", related_id)])
            if reports:
                report = self._approval_from_qc_report(reports[0])
                report["approval_id"] = item.get("id")
                report["id"] = item.get("id")
                report["related_id"] = related_id
                report["approval_status"] = item.get("status") or report.get("approval_status") or "pending"
                report["status"] = report.get("status") or item.get("status") or "pending"
                report["created_at"] = item.get("created_at") or report.get("created_at")
                return report
        item.setdefault("approval_id", item.get("id"))
        item.setdefault("source", related_type or "approval")
        item.setdefault("approval_status", item.get("status") or "pending")
        return item

    def _approval_from_finding(self, row):
        item = dict(row or {})
        item["source"] = "qc_finding"
        item["batch_code"] = item.get("batch_code") or item.get("finding_type") or "QC Finding"
        item["status"] = item.get("status") or "finding"
        item["approval_status"] = item.get("approval_status") or "pending"
        item["inspector_name"] = item.get("inspector_name") or item.get("staff_name") or item.get("staff_id")
        item["product_photo_url"] = item.get("photo_url")
        return item

    def _approval_from_temperature(self, row):
        room = row.get("zone") or row.get("room_name") or (row.get("facility_rooms") or {}).get("name") or row.get("room_id") or "Temperature"
        device = row.get("device_type") or row.get("device_name") or (row.get("facility_devices") or {}).get("name") or row.get("device_id") or "Log"
        return {
            "id": row.get("id"),
            "source": "temperature_log",
            "batch_code": f"{room} - {device}",
            "batch_id": row.get("room_id") or row.get("device_id"),
            "status": "warning" if self._temperature_needs_review(row) else "pending",
            "approval_status": "pending",
            "staff_id": row.get("staff_id") or row.get("created_by"),
            "inspector_name": row.get("staff_name") or row.get("staff_id") or row.get("created_by"),
            "product_photo_url": row.get("photo_url"),
            "storage_path": row.get("storage_path"),
            "created_at": row.get("recorded_at") or row.get("created_at"),
        }

    def _audit_from_staff_submissions(self, limit):
        rows = []
        rows.extend(self._audit_rows("qc_findings", "submit", "qc_finding", "created_at", limit))
        rows.extend(self._audit_rows("facility_logs", "input_temperature", "facility_log", "recorded_at", limit))
        if not any(row["entity_type"] == "facility_log" for row in rows):
            rows.extend(self._audit_rows("temperature_logs", "input_temperature", "temperature_log", "recorded_at", limit))
        rows.extend(self._audit_rows("qc_reports", "submit", "qc_report", "created_at", limit))
        rows.extend(self._audit_rows("production_batch_logs", "submit", "production_batch_log", "recorded_at", limit))
        return sorted(rows, key=lambda row: row.get("created_at") or "", reverse=True)[:limit]

    def _audit_rows(self, table, action, entity_type, timestamp_field, limit):
        rows = self._fetch(table, order_by=timestamp_field, limit=limit)
        result = []
        for row in rows:
            actor = row.get("staff_id") or row.get("operator_id") or row.get("created_by") or row.get("qc_officer_id")
            display_name = row.get("staff_name") or row.get("inspector_name") or actor or "Staff"
            result.append({
                "id": f"{entity_type}-{row.get('id')}",
                "action": action,
                "entity_type": entity_type,
                "entity_id": row.get("id") or row.get("batch_id") or row.get("batch_code"),
                "actor_id": actor,
                "staff_id": actor,
                "staff_accounts": {"username": display_name},
                "staff_display_name": display_name,
                "actor_display_name": display_name,
                "ip_address": row.get("ip_address") or "-",
                "created_at": row.get(timestamp_field) or row.get("created_at"),
            })
        return result

    def _actor_profiles(self, rows):
        actor_ids = {
            row.get("actor_id") or row.get("staff_id") or row.get("created_by") or row.get("operator_id") or row.get("qc_officer_id")
            for row in rows or []
        }
        actor_ids = {actor_id for actor_id in actor_ids if actor_id}
        profiles = {}
        for actor_id in actor_ids:
            account = (self._fetch("staff_accounts", limit=1, filters=[("eq", "id", actor_id)]) or [None])[0] or {}
            user = {}
            users = self._fetch("users", limit=1, filters=[("eq", "staff_account_id", actor_id)])
            if not users:
                users = self._fetch("users", limit=1, filters=[("eq", "id", actor_id)])
            if users:
                user = users[0] or {}
            profile = {
                "full_name": user.get("full_name") or account.get("full_name"),
                "name": user.get("name") or account.get("name"),
                "username": account.get("username") or user.get("username"),
                "email": user.get("email") or account.get("email"),
                "role": user.get("role") or account.get("role"),
            }
            profiles[actor_id] = {key: value for key, value in profile.items() if value}
        return profiles

    def _normalize_audit_row(self, row, actor_profiles=None):
        item = dict(row or {})
        actor_id = item.get("actor_id") or item.get("staff_id") or item.get("created_by")
        profile = (actor_profiles or {}).get(actor_id, {})
        if profile:
            item["staff_accounts"] = {
                **(item.get("staff_accounts") if isinstance(item.get("staff_accounts"), dict) else {}),
                **profile,
            }
        item = self._with_staff_display(item, ("actor_id", "staff_id", "created_by", "operator_id", "qc_officer_id"))
        if actor_id:
            item["actor_id"] = actor_id
        item["actor_display_name"] = item.get("staff_display_name") or actor_id or "Unknown User"
        item["staff_display_name"] = item["actor_display_name"]
        nested = item.get("staff_accounts") if isinstance(item.get("staff_accounts"), dict) else {}
        item["actor_role"] = item.get("actor_role") or item.get("role") or nested.get("role") or "staff"
        item["role"] = item.get("role") or item["actor_role"]
        item["actor_email"] = item.get("actor_email") or item.get("email") or nested.get("email")
        return item

    def _traceability_from_staff_submissions(self, limit):
        rows = []
        batches = {row.get("id"): row for row in self._fetch("production_batches", select="*, products(*)", order_by="created_at", limit=limit)}
        rows.extend(self._traceability_from_reports(limit, batches))
        rows.extend(self._traceability_from_temperature(limit))
        rows.extend(self._traceability_from_findings(limit))
        rows.extend(self._traceability_from_batch_logs(limit, batches))
        return sorted(rows, key=lambda row: row.get("created_at") or "", reverse=True)[:limit]

    def _traceability_from_reports(self, limit, batches):
        result = []
        for row in self._fetch("qc_reports", order_by="created_at", limit=limit):
            batch = batches.get(row.get("batch_id"), {})
            product = batch.get("products") or {}
            result.append({
                "barcode_value": row.get("barcode_value") or row.get("batch_code") or row.get("batch_id") or row.get("id"),
                "batch_code": row.get("batch_code") or batch.get("batch_code") or row.get("batch_id"),
                "batch_id": row.get("batch_id"),
                "product_name": row.get("product_name") or product.get("product_name") or batch.get("product_name"),
                "product_id": row.get("product_id") or batch.get("product_id"),
                "staff_name": row.get("inspector_name") or row.get("staff_name") or row.get("staff_id"),
                "staff_id": row.get("staff_id"),
                "photo_url": row.get("product_photo_url") or row.get("temperature_photo_url") or row.get("barcode_photo_url") or row.get("photo_url"),
                "storage_path": row.get("storage_path") or row.get("product_storage_path") or row.get("temperature_storage_path") or row.get("barcode_storage_path"),
                "created_at": row.get("created_at"),
            })
        return result

    def _traceability_from_temperature(self, limit):
        logs = self._fetch("facility_logs", order_by="recorded_at", limit=limit)
        if not logs:
            logs = self._fetch("temperature_logs", order_by="recorded_at", limit=limit)
        result = []
        for row in logs:
            room = row.get("zone") or row.get("room_name") or (row.get("facility_rooms") or {}).get("name") or row.get("room_id") or "Room"
            device = row.get("device_type") or row.get("device_name") or (row.get("facility_devices") or {}).get("name") or row.get("device_id") or "Unit"
            result.append({
                "barcode_value": f"{room} / {device}",
                "batch_code": row.get("batch_code") or row.get("batch_id") or "-",
                "batch_id": row.get("batch_id") or row.get("device_id"),
                "product_name": f"{room} - {device}",
                "staff_name": row.get("staff_name") or row.get("staff_id") or row.get("created_by"),
                "staff_id": row.get("staff_id") or row.get("created_by"),
                "photo_url": row.get("photo_url"),
                "storage_path": row.get("storage_path"),
                "created_at": row.get("recorded_at") or row.get("created_at"),
            })
        return result

    def _traceability_from_findings(self, limit):
        result = []
        for row in self._fetch("qc_findings", order_by="created_at", limit=limit):
            result.append({
                "barcode_value": row.get("finding_type") or "QC Finding",
                "batch_code": row.get("batch_code") or row.get("source") or "QC Finding",
                "batch_id": row.get("batch_id") or row.get("id"),
                "product_name": row.get("product_name") or row.get("reason") or "QC Finding",
                "staff_name": row.get("staff_name") or row.get("staff_id"),
                "staff_id": row.get("staff_id"),
                "photo_url": row.get("photo_url"),
                "storage_path": row.get("storage_path"),
                "created_at": row.get("created_at"),
            })
        return result

    def _traceability_from_batch_logs(self, limit, batches):
        result = []
        for row in self._fetch("production_batch_logs", order_by="recorded_at", limit=limit):
            batch = batches.get(row.get("batch_id"), {})
            product = batch.get("products") or {}
            result.append({
                "barcode_value": row.get("barcode_value") or row.get("batch_id") or row.get("id"),
                "batch_code": batch.get("batch_code") or row.get("batch_id"),
                "batch_id": row.get("batch_id"),
                "product_name": product.get("product_name") or batch.get("product_name") or row.get("stage"),
                "staff_name": row.get("staff_name") or row.get("staff_id"),
                "staff_id": row.get("staff_id"),
                "photo_url": row.get("photo_url"),
                "storage_path": row.get("storage_path"),
                "created_at": row.get("recorded_at") or row.get("created_at"),
            })
        return result

    def list_products(self):
        if not self.sb:
            return self._empty(CENTRAL_KITCHEN_PRODUCTS)
        try:
            res = self.sb.table("products").select("*").order("product_code").execute()
            products = res.data or []
            for item in products:
                if "product_code" not in item and item.get("sku_code"):
                    item["product_code"] = item["sku_code"]
            return self._empty(products)
        except Exception as exc:
            logger.warning("Product admin list failed, using local catalog: %s", exc)
            return self._empty(CENTRAL_KITCHEN_PRODUCTS)

    def create_product(self, payload):
        if not self.sb:
            return {"success": False, "detail": "Database belum terhubung"}
        try:
            try:
                res = self.sb.table("products").insert([payload]).execute()
            except Exception:
                compact_payload = {k: v for k, v in payload.items() if k != "sku_code"}
                res = self.sb.table("products").insert([compact_payload]).execute()
            return self._empty((res.data or [None])[0])
        except Exception as exc:
            logger.error("Create product failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def update_product(self, product_id, payload):
        if not self.sb:
            return {"success": False, "detail": "Database belum terhubung"}
        try:
            try:
                res = self.sb.table("products").update(payload).eq("id", product_id).execute()
            except Exception:
                compact_payload = {k: v for k, v in payload.items() if k != "sku_code"}
                res = self.sb.table("products").update(compact_payload).eq("id", product_id).execute()
            return self._empty((res.data or [None])[0])
        except Exception as exc:
            logger.error("Update product failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def delete_product(self, product_id):
        if not self.sb:
            return {"success": False, "detail": "Database belum terhubung"}
        try:
            self.sb.table("products").delete().eq("id", product_id).execute()
            return self._empty({"success": True})
        except Exception as exc:
            logger.error("Delete product failed: %s", exc)
            return {"success": False, "detail": str(exc)}
