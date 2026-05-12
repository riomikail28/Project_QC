import logging
from datetime import datetime, timezone

from backend.database.supabase_client import get_client

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
        today = datetime.now(timezone.utc).date().isoformat()
        try:
            data = {
                "total_batches_today": self._count("qc_reports", [("gte", "created_at", f"{today}T00:00:00Z")]),
                "total_failed_batches": self._count("qc_reports", [("eq", "status", "failed")]),
                "total_qc_pending": self._count("qc_reports", [("eq", "approval_status", "pending")]),
                "total_qc_completed": self._count("qc_reports", [("neq", "approval_status", "pending")]),
                "total_open_alerts": self._count("temperature_logs", [("eq", "is_abnormal", True)]),
                "total_active_staff": self._count("staff_activity", [("gte", "created_at", f"{today}T00:00:00Z")]),
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
            res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            return {"success": True, "data": res.data or [], "count": res.count or 0}
        except Exception as exc:
            logger.error("QC reports failed: %s", exc)
            return {"success": False, "detail": str(exc)}

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
