import logging
from datetime import datetime, timezone

from backend.database.supabase_client import get_client
from backend.qc.product_catalog import CENTRAL_KITCHEN_PRODUCTS

logger = logging.getLogger("qc.services.admin")


class AdminService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def _empty(self, data):
        return {"success": True, "data": data}

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
            res = (
                self.sb.table("temperature_logs")
                .select("*")
                .order("recorded_at", desc=True)
                .limit(50)
                .execute()
            )
            latest = {}
            for row in res.data or []:
                key = row.get("zone") or row.get("device_type") or row.get("id")
                latest.setdefault(key, row)
            devices = [
                {
                    "id": row.get("id"),
                    "name": row.get("zone") or row.get("device_type") or "Temperature Point",
                    "type": row.get("device_type") or "ambient",
                    "threshold_temp": row.get("threshold_c"),
                    "facility_rooms": {"name": row.get("zone") or "QC Area"},
                    "latest_log": {
                        "temperature_c": row.get("temperature_c"),
                        "is_normal": not row.get("is_abnormal", False),
                        "recorded_at": row.get("recorded_at"),
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
        item = dict(row or {})
        item.setdefault("report_type", "qc_report")
        item.setdefault("display_title", item.get("batch_code") or item.get("batch_id") or "QC Report")
        item.setdefault("photo_url", item.get("product_photo_url") or item.get("temperature_photo_url") or item.get("barcode_photo_url"))
        return item

    def _normalize_qc_finding(self, row):
        item = dict(row or {})
        item["report_type"] = "qc_finding"
        item["status"] = item.get("status") or "finding"
        item["approval_status"] = item.get("approval_status") or "pending"
        item["display_title"] = item.get("reason") or "QC Finding"
        item["product_name"] = item.get("product_name") or "QC Finding"
        item["inspector_name"] = item.get("inspector_name") or item.get("staff_name") or item.get("staff_id")
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
                return self._empty(rows[:limit])

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

    def get_audit_trail(self, limit=50):
        try:
            rows = self._fetch("audit_logs", select="*, staff_accounts(username)", order_by="created_at", limit=limit)
            if not rows:
                rows = self._audit_from_staff_submissions(limit)
            return self._empty(rows[:limit])
        except Exception as exc:
            logger.error("Audit trail failed: %s", exc)
            return {"success": False, "detail": str(exc)}

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
        item.setdefault("source", "qc_report")
        item.setdefault("approval_status", item.get("approval_status") or "pending")
        item.setdefault("status", item.get("status") or "pending")
        item.setdefault("inspector_name", item.get("inspector_name") or item.get("staff_name") or item.get("staff_id") or item.get("operator_id"))
        item.setdefault("product_photo_url", item.get("product_photo_url") or item.get("photo_url"))
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
            result.append({
                "id": f"{entity_type}-{row.get('id')}",
                "action": action,
                "entity_type": entity_type,
                "entity_id": row.get("id") or row.get("batch_id") or row.get("batch_code"),
                "staff_id": actor,
                "staff_accounts": {"username": row.get("staff_name") or row.get("inspector_name") or actor or "Staff"},
                "ip_address": row.get("ip_address") or "-",
                "created_at": row.get(timestamp_field) or row.get("created_at"),
            })
        return result

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
