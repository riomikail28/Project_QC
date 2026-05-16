from types import SimpleNamespace
from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_admin_temperature_report_uses_staff_logs(client, admin_headers):
    db = FakeSupabase({
        "facility_logs": [{
            "id": "log-1",
            "staff_id": "staff-1",
            "room_id": "room-1",
            "device_id": "device-1",
            "temperature_c": 3.5,
            "is_normal": True,
            "photo_url": "https://example.test/photo.jpg",
            "storage_path": "staff/staff-1/temperature/photo.jpg",
            "recorded_at": "2026-05-16T01:00:00Z",
        }]
    })
    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/v1/admin/reports/temperature", headers=admin_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][0]["staff_id"] == "staff-1"
    assert body["data"][0]["storage_path"].startswith("staff/staff-1/temperature")


def test_admin_inspection_report_uses_qc_reports(client, admin_headers):
    db = FakeSupabase({
        "qc_reports": [{
            "id": "qc-1",
            "batch_code": "BATCH-001",
            "product_name": "Soup",
            "staff_id": "staff-1",
            "status": "pass",
            "product_photo_url": "https://example.test/evidence.jpg",
            "created_at": "2026-05-16T01:00:00Z",
        }]
    })
    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/v1/admin/reports/inspection", headers=admin_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][0]["batch_code"] == "BATCH-001"
    assert body["data"][0]["photo_url"].endswith("evidence.jpg")


class ApprovalQuery:
    def __init__(self, table, db):
        self.table = table
        self.db = db
        self.payload = None
        self.row_id = None

    def update(self, payload):
        self.payload = payload
        return self

    def eq(self, field, value):
        if field == "id":
            self.row_id = value
        return self

    def execute(self):
        rows = self.db.rows.get(self.table, [])
        match = next((row for row in rows if row["id"] == self.row_id), None)
        if not match:
            return SimpleNamespace(data=[])
        match.update(self.payload)
        return SimpleNamespace(data=[match])


class ApprovalDb:
    def __init__(self):
        self.rows = {"approvals": [{"id": "approval-1", "status": "pending"}], "qc_reports": []}

    def table(self, table):
        return ApprovalQuery(table, self)


def test_admin_approve_endpoint_updates_approval(client, admin_headers):
    db = ApprovalDb()
    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.post(
            "/api/v1/admin/approvals/approval-1/approve",
            headers=admin_headers,
            json={"comment": "OK"},
        )

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["status"] == "approved"


def test_staff_role_cannot_access_admin_reports(client, staff_headers):
    response = client.get("/api/v1/admin/reports/inspection", headers=staff_headers)

    assert response.status_code == 403
