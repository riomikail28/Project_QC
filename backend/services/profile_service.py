"""Real-data service for staff profile and activity."""

from __future__ import annotations

import logging

from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.services.profile")


class ProfileService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def _ok(self, data, message="OK"):
        return {"success": True, "data": data, "message": message}

    def _fail(self, message):
        return {"success": False, "data": None, "message": message}

    def _fetch(self, table, select="*", order_by=None, desc=True, limit=None, filters=None):
        if not self.sb:
            return []
        try:
            query = self.sb.table(table).select(select)
            for method, field, value in filters or []:
                query = getattr(query, method)(field, value)
            if order_by:
                query = query.order(order_by, desc=desc)
            if limit:
                query = query.limit(limit)
            return query.execute().data or []
        except Exception as exc:
            logger.warning("Profile query skipped for %s: %s", table, exc)
            return []

    def me(self, user):
        user = user or {}
        user_id = user.get("id") or user.get("user_id") or user.get("sub")
        account = None
        if user_id:
            rows = self._fetch("staff_accounts", filters=[("eq", "id", user_id)], limit=1)
            account = rows[0] if rows else None
        data = {
            "id": user_id,
            "username": (account or {}).get("username") or user.get("username"),
            "full_name": (account or {}).get("full_name") or (account or {}).get("name") or user.get("full_name") or user.get("name") or user.get("username"),
            "role": (account or {}).get("role") or user.get("role", "staff"),
            "department": (account or {}).get("department"),
            "shift": (account or {}).get("shift"),
            "last_login": (account or {}).get("last_login_at") or (account or {}).get("last_login"),
            "has_account_record": bool(account),
        }
        return self._ok(data)

    def activity_summary(self, user):
        user = user or {}
        user_id = user.get("id") or user.get("user_id") or user.get("sub")
        filters = [("eq", "staff_id", user_id)] if user_id else []
        reports = self._fetch("qc_reports", filters=filters, limit=1000)
        temp_logs = self._fetch("temperature_logs", filters=filters, limit=1000)
        if not temp_logs:
            temp_logs = self._fetch("facility_logs", filters=filters, limit=1000)
        labels = self._fetch("barcode_labels", filters=filters, limit=1000)
        audits = self._fetch("audit_logs", filters=[("eq", "actor_id", user_id)] if user_id else [], order_by="created_at", limit=5)

        evidence_count = 0
        for row in reports:
            if row.get("product_photo_url") or row.get("temperature_photo_url") or row.get("barcode_photo_url") or row.get("photo_url"):
                evidence_count += 1
        evidence_count += sum(1 for row in temp_logs if row.get("photo_url"))
        evidence_count += sum(1 for row in labels if row.get("barcode_photo_url"))

        pass_count = sum(1 for row in reports if self._norm_status(row.get("status") or row.get("final_qc_status")) == "pass")
        accuracy = round((pass_count / len(reports)) * 100, 1) if reports else None
        data = {
            "qc_submitted": len(reports),
            "upload_evidence": evidence_count,
            "temperature_logs": len(temp_logs),
            "barcode_labels": len(labels),
            "accuracy": accuracy,
            "recent_activity": audits,
            "has_activity": bool(reports or temp_logs or labels or audits),
        }
        return self._ok(data)

    def _norm_status(self, value):
        value = str(value or "").lower()
        return {"passed": "pass", "success": "pass", "failed": "fail"}.get(value, value)
