from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class Query:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.filters = []
        self.payload = None
        self._limit = None
        self._order = None
        self._desc = True

    def select(self, *args, **kwargs):
        return self

    def update(self, payload):
        self.payload = payload
        return self

    def eq(self, field, value):
        self.filters.append(("eq", field, value))
        return self

    def gte(self, field, value):
        self.filters.append(("gte", field, value))
        return self

    def lte(self, field, value):
        self.filters.append(("lte", field, value))
        return self

    def order(self, field, desc=True):
        self._order = field
        self._desc = desc
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        rows = [dict(row) for row in self.db.rows.get(self.table, [])]
        for op, field, value in self.filters:
            if op == "eq":
                rows = [row for row in rows if row.get(field) == value]
            if op == "gte":
                rows = [row for row in rows if str(row.get(field) or "") >= str(value)]
            if op == "lte":
                rows = [row for row in rows if str(row.get(field) or "") <= str(value)]
        if self.payload is not None:
            source = self.db.rows.get(self.table, [])
            ids = {row.get("id") for row in rows}
            for row in source:
                if row.get("id") in ids:
                    row.update(self.payload)
            rows = [dict(row) for row in source if row.get("id") in ids]
        if self._order:
            rows.sort(key=lambda row: row.get(self._order) or "", reverse=self._desc)
        if self._limit:
            rows = rows[: self._limit]
        return SimpleNamespace(data=rows, count=len(rows))


class Db:
    def __init__(self):
        self.rows = {
            "qc_findings": [{
                "id": "finding-1",
                "reason": "Area kotor",
                "status": "OPEN",
                "staff_name": "Rio",
                "created_at": "2026-06-07T02:00:00Z",
            }],
            "facility_rooms": [{"id": "room-1", "name": "PPIC"}],
            "facility_devices": [{
                "id": "device-1",
                "room_id": "room-1",
                "name": "Chiller",
                "device_type": "chiller",
                "min_temperature": 0,
                "max_temperature": 5,
            }],
            "facility_logs": [{
                "id": "log-1",
                "room_id": "room-1",
                "device_id": "device-1",
                "room_name": "PPIC",
                "device_name": "Chiller",
                "temperature_c": 4.4,
                "is_normal": True,
                "slot_time": "07:00",
                "staff_name": "Rio",
                "recorded_at": "2026-06-07T00:10:00Z",
                "monitoring_date": "2026-06-07",
            }, {
                "id": "log-old",
                "room_id": "room-1",
                "device_id": "device-1",
                "room_name": "PPIC",
                "device_name": "Chiller",
                "temperature_c": 9.9,
                "is_normal": False,
                "slot_time": "13:00",
                "staff_name": "Dina",
                "recorded_at": "2026-06-06T06:10:00Z",
                "monitoring_date": "2026-06-06",
            }],
            "temperature_logs": [],
            "staff_accounts": [],
            "users": [],
        }

    def table(self, table):
        return Query(self, table)


def test_admin_qc_finding_status_endpoint_updates_lifecycle(client, admin_headers):
    db = Db()
    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.patch(
            "/api/v1/admin/qc-findings/finding-1/status",
            headers=admin_headers,
            json={"status": "IN_PROGRESS"},
        )

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["status"] == "IN_PROGRESS"
    assert db.rows["qc_findings"][0]["status"] == "IN_PROGRESS"


def test_admin_monitoring_daily_returns_slots_for_selected_date_only(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=Db()):
        response = client.get("/api/v1/admin/monitoring/daily?date=2026-06-07", headers=admin_headers)

    body = response.get_json()
    device = body["data"]["devices"][0]
    slots = {slot["slot_time"]: slot for slot in device["slots"]}

    assert response.status_code == 200
    assert body["data"]["date"] == "2026-06-07"
    assert device["latest_temperature"] == 4.4
    assert slots["07:00"]["temperature"] == 4.4
    assert slots["13:00"]["temperature"] is None
    assert slots["13:00"]["staff_name"] is None


def test_admin_frontend_qc_findings_ticket_status_contract():
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "findingLifecycleStatus" in js
    assert "findingSeverityStatus" in js
    assert "findingStatusButton" in js
    assert "updateFindingStatus" in js
    assert "/qc-findings/" in js and "/status" in js
    assert "Status temuan berhasil diubah ke" in js
    assert "data-finding-id" in js


def test_admin_frontend_monitoring_daily_date_history_contract():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "monitoring-date-label" in html
    assert "Hari ini" in html
    assert "Kemarin" in html
    assert "Pilih tanggal" in html
    assert "/monitoring/daily?date=" in js
    assert "Tanggal monitoring:" in js
    assert "Belum ada input monitoring pada tanggal ini." in js
    assert "monitoring-slot-row" in js
    assert "Timeline Slot" in js
