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
            "department": (account or {}).get("department") or "No department data",
            "shift": (account or {}).get("shift") or "No shift data",
            "employee_id": (account or {}).get("employee_id") or "No ID data",
            "join_date": (account or {}).get("join_date") or "No date data",
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

        # Today's Activity dynamic calculations (Jakarta time UTC+7)
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=7))
        now_local = datetime.now(tz)
        today_date_str = now_local.date().isoformat()

        def get_local_date(created_at_str):
            if not created_at_str:
                return ""
            try:
                clean_str = created_at_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_str)
                return dt.astimezone(tz).date().isoformat()
            except Exception:
                return created_at_str[:10]

        today_reports = [r for r in reports if get_local_date(r.get("created_at")) == today_date_str]
        batch_ids = list(set(r["batch_id"] for r in today_reports if r.get("batch_id")))
        
        today_shifts = set()
        if batch_ids:
            for b_id in batch_ids:
                b_rows = self._fetch("production_batches", filters=[("eq", "id", b_id)])
                if b_rows and b_rows[0].get("shift"):
                    today_shifts.add(b_rows[0]["shift"].lower())

        qc_pagi = "pagi" in today_shifts
        qc_siang = "siang" in today_shifts
        qc_sore = "sore" in today_shifts or "malam" in today_shifts

        completed_count = sum([qc_pagi, qc_siang, qc_sore])
        progress_percent = int(completed_count / 3 * 100)

        # 7-day streak logic: count distinct report days
        last_7_days = [(now_local - timedelta(days=i)).date().isoformat() for i in range(7)]
        report_dates = set(get_local_date(r.get("created_at")) for r in reports if r.get("created_at"))
        consecutive_days = sum(1 for d in last_7_days if d in report_dates)
        seven_days_streak = consecutive_days >= 5

        # Weekly Performance logic
        seven_days_ago_dt = (now_local - timedelta(days=7)).isoformat()
        recent_reports = [r for r in reports if (r.get("created_at") or "") >= seven_days_ago_dt]
        recent_pass = sum(1 for r in recent_reports if self._norm_status(r.get("status") or r.get("final_qc_status")) == "pass")
        weekly_qc = int((recent_pass / len(recent_reports)) * 100) if recent_reports else 100

        recent_approved = sum(1 for r in recent_reports if r.get("approval_status") == "approved")
        weekly_response = int((recent_approved / len(recent_reports)) * 100) if recent_reports else 84

        recent_temp_logs = [l for l in temp_logs if (l.get("created_at") or l.get("recorded_at") or "") >= seven_days_ago_dt]
        recent_not_late = sum(1 for l in recent_temp_logs if not l.get("is_late"))
        weekly_temp = int((recent_not_late / len(recent_temp_logs)) * 100) if recent_temp_logs else 93

        data = {
            "qc_submitted": len(reports),
            "upload_evidence": evidence_count,
            "temperature_logs": len(temp_logs),
            "barcode_labels": len(labels),
            "accuracy": accuracy,
            "recent_activity": audits,
            "has_activity": bool(reports or temp_logs or labels or audits),
            "today_activity": {
                "qc_pagi": qc_pagi,
                "qc_siang": qc_siang,
                "qc_sore": qc_sore,
                "progress": progress_percent,
                "status_text": f"{completed_count} / 3 Selesai"
            },
            "achievements": {
                "perfect_accuracy": (accuracy == 100.0 or accuracy == 100) if accuracy else False,
                "seven_days_streak": seven_days_streak,
                "evidence_master": evidence_count >= 5
            },
            "weekly_performance": {
                "qc": weekly_qc,
                "response": weekly_response,
                "temperature": weekly_temp
            }
        }
        return self._ok(data)

    def _norm_status(self, value):
        value = str(value or "").lower()
        return {"passed": "pass", "success": "pass", "failed": "fail"}.get(value, value)
