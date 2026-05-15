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
        if not self.sb:
            return self._empty([])
        try:
            query = self.sb.table("barcode_labels").select("*").order("created_at", desc=True).limit(limit)
            if barcode:
                query = query.eq("barcode_value", barcode)
            return self._empty(query.execute().data or [])
        except Exception as exc:
            logger.error("Traceability failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def get_pending_approvals(self, limit=50):
        if not self.sb:
            return self._empty([])
        try:
            res = (
                self.sb.table("qc_reports")
                .select("*")
                .eq("approval_status", "pending")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return self._empty(res.data or [])
        except Exception as exc:
            logger.error("Approvals failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def get_audit_trail(self, limit=50):
        if not self.sb:
            return self._empty([])
        try:
            res = self.sb.table("audit_logs").select("*").order("created_at", desc=True).limit(limit).execute()
            return self._empty(res.data or [])
        except Exception as exc:
            logger.error("Audit trail failed: %s", exc)
            return {"success": False, "detail": str(exc)}

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
