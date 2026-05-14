import logging
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.services.dashboard")


class DashboardService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def _ok(self, data, message="OK"):
        return {"success": True, "data": data, "message": message}

    def _empty(self, data=None):
        return self._ok(data if data is not None else {}, "No data available yet")

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
            logger.warning("Dashboard query skipped for %s: %s", table, exc)
            return []

    def _today_bounds(self):
        today = datetime.now(timezone.utc).date()
        start = f"{today.isoformat()}T00:00:00Z"
        end = f"{today.isoformat()}T23:59:59Z"
        return today, start, end

    def summary(self):
        if not self.sb:
            return self._empty({
                "total_batches_today": 0,
                "total_alerts": 0,
                "qc_success_rate": None,
                "pending_approval": 0,
                "avg_freezer_temperature": None,
                "health_score": None,
            })

        today, start, end = self._today_bounds()
        batches = self._fetch("production_batches", filters=[("eq", "production_date", today.isoformat())])
        if not batches:
            batches = self._fetch("production_batches", filters=[("gte", "created_at", start), ("lte", "created_at", end)])

        qc_reports = self._fetch("qc_reports", filters=[("gte", "created_at", start), ("lte", "created_at", end)])
        passed_qc = sum(1 for row in qc_reports if self._norm_status(row.get("status") or row.get("final_qc_status")) == "pass")
        qc_success_rate = round((passed_qc / len(qc_reports)) * 100, 1) if qc_reports else None

        pending_reports = self._fetch("qc_reports", filters=[("eq", "approval_status", "pending")])
        approvals = self._fetch("approvals", filters=[("eq", "status", "pending")])
        pending_approval = len(approvals) if approvals else len(pending_reports)

        abnormal_logs = self._temperature_logs(abnormal_only=True, limit=200)
        open_alerts = self._fetch("facility_alerts", filters=[("eq", "status", "open")])
        total_alerts = len(open_alerts) if open_alerts else len(abnormal_logs)

        freezer_logs = [
            row for row in self._temperature_logs(limit=100)
            if self._device_type(row) == "freezer" and row.get("temperature_c") is not None
        ]
        avg_freezer = None
        if freezer_logs:
            avg_freezer = round(sum(float(row.get("temperature_c")) for row in freezer_logs) / len(freezer_logs), 1)

        health_score = qc_success_rate
        if health_score is None and freezer_logs:
            normal = sum(1 for row in freezer_logs if self._is_normal(row))
            health_score = round((normal / len(freezer_logs)) * 100, 1)

        return self._ok({
            "total_batches_today": len(batches),
            "total_alerts": total_alerts,
            "qc_success_rate": qc_success_rate,
            "pending_approval": pending_approval,
            "avg_freezer_temperature": avg_freezer,
            "health_score": health_score,
            "has_data": bool(batches or qc_reports or abnormal_logs or open_alerts or freezer_logs),
        })

    def production_trend(self):
        today = datetime.now(timezone.utc).date()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        start = f"{days[0].isoformat()}T00:00:00Z"
        rows = self._fetch("production_batches", order_by="created_at", desc=False, filters=[("gte", "created_at", start)])
        counts = {day.isoformat(): 0 for day in days}
        for row in rows:
            key = row.get("production_date") or self._date_from_iso(row.get("created_at"))
            if key in counts:
                counts[key] += 1
        return self._ok([{"date": day, "count": count} for day, count in counts.items()])

    def qc_status(self):
        rows = self._fetch("qc_reports", limit=1000)
        counter = Counter({"pass": 0, "warning": 0, "fail": 0, "pending": 0})
        for row in rows:
            status = self._norm_status(row.get("status") or row.get("final_qc_status"))
            if status in counter:
                counter[status] += 1
        total = sum(counter.values())
        return self._ok({
            "total": total,
            "items": [{"status": key, "count": counter[key]} for key in ("pass", "warning", "fail", "pending")],
        })

    def realtime_monitoring(self):
        rows = self._temperature_logs(limit=100)
        latest = {}
        for row in rows:
            key = row.get("device_id") or row.get("room_id") or row.get("zone") or row.get("id")
            latest.setdefault(key, {
                "id": row.get("id"),
                "room": self._room_name(row),
                "device": self._device_name(row),
                "device_type": self._device_type(row),
                "temperature_c": row.get("temperature_c"),
                "threshold_c": self._threshold(row),
                "is_normal": self._is_normal(row),
                "recorded_at": row.get("recorded_at") or row.get("created_at"),
            })
        return self._ok(list(latest.values()))

    def alerts(self):
        facility_alerts = self._fetch("facility_alerts", order_by="created_at", limit=20, filters=[("eq", "status", "open")])
        if facility_alerts:
            return self._ok([{
                "id": row.get("id"),
                "zone": row.get("zone") or row.get("room_name") or "QC Area",
                "temperature_c": row.get("temperature_c"),
                "status": row.get("status") or "open",
                "severity": row.get("severity") or "critical",
                "created_at": row.get("created_at"),
                "description": row.get("description") or row.get("message"),
            } for row in facility_alerts])

        rows = self._temperature_logs(abnormal_only=True, limit=20)
        return self._ok([{
            "id": row.get("id"),
            "zone": self._room_name(row),
            "temperature_c": row.get("temperature_c"),
            "status": "open",
            "severity": "critical",
            "created_at": row.get("recorded_at") or row.get("created_at"),
            "description": row.get("reason") or "Temperature abnormal",
        } for row in rows])

    def today_summary(self):
        today, start, end = self._today_bounds()
        reports = self._fetch("qc_reports", order_by="created_at", filters=[("gte", "created_at", start), ("lte", "created_at", end)])
        photos = sum(1 for row in reports if row.get("product_photo_url") or row.get("temperature_photo_url") or row.get("barcode_photo_url"))
        logs = self._temperature_logs(limit=300)
        today_logs = [row for row in logs if (row.get("recorded_at") or row.get("created_at") or "").startswith(today.isoformat())]
        labels = self._fetch("barcode_labels", filters=[("gte", "created_at", start), ("lte", "created_at", end)])
        staff_activity = self._fetch("staff_activity", order_by="created_at", limit=50, filters=[("gte", "created_at", start), ("lte", "created_at", end)])

        return self._ok({
            "qc_submitted": len(reports),
            "photo_evidence": photos,
            "temperature_logs": len(today_logs),
            "barcode_labels": len(labels),
            "staff_activity": staff_activity[:10],
            "has_data": bool(reports or today_logs or labels or staff_activity),
        })

    def _temperature_logs(self, abnormal_only=False, limit=100):
        filters = []
        if abnormal_only:
            filters.append(("eq", "is_abnormal", True))
        rows = self._fetch("temperature_logs", order_by="recorded_at", limit=limit, filters=filters)
        if rows:
            return rows
        filters = []
        if abnormal_only:
            filters.append(("eq", "is_normal", False))
        return self._fetch(
            "facility_logs",
            select="*, facility_rooms(name), facility_devices(name, type, threshold_temp)",
            order_by="recorded_at",
            limit=limit,
            filters=filters,
        )

    def _norm_status(self, status):
        value = str(status or "pending").lower()
        if value == "failed":
            return "fail"
        if value not in {"pass", "warning", "fail", "pending"}:
            return "pending"
        return value

    def _date_from_iso(self, value):
        return str(value or "")[:10]

    def _room_name(self, row):
        return row.get("zone") or (row.get("facility_rooms") or {}).get("name") or row.get("room_name") or "QC Area"

    def _device_name(self, row):
        return (row.get("facility_devices") or {}).get("name") or row.get("device_name") or row.get("device_type") or "Temperature Point"

    def _device_type(self, row):
        return row.get("device_type") or (row.get("facility_devices") or {}).get("type") or "ambient"

    def _threshold(self, row):
        return row.get("threshold_c") or row.get("threshold_temp") or (row.get("facility_devices") or {}).get("threshold_temp")

    def _is_normal(self, row):
        if "is_abnormal" in row:
            return not bool(row.get("is_abnormal"))
        return bool(row.get("is_normal", True))
