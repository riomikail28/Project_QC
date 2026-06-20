from types import SimpleNamespace
from unittest.mock import patch


class QCQuery:
    def __init__(self, table, db):
        self.table = table
        self.db = db
        self.payload = None
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self.filters.append(("eq", field, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def update(self, payload):
        self.payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            row = {"id": f"{self.table}-{len(self.db.inserted.get(self.table, [])) + 1}", **self.payload}
            self.db.inserted.setdefault(self.table, []).append(row)
            self.db.fixtures.setdefault(self.table, []).append(row)
            return SimpleNamespace(data=[row])
        rows = list(self.db.fixtures.get(self.table, []))
        for _, field, value in self.filters:
            rows = [row for row in rows if row.get(field) == value]
        return SimpleNamespace(data=rows)


class QCDb:
    def __init__(self):
        self.fixtures = {
            "products": [{"id": "product-1", "product_code": "SKU-1", "product_name": "Nasi Ayam", "is_active": True}],
            "production_batches": [
                {
                    "id": "batch-1",
                    "batch_code": "BATCH-1",
                    "product_id": "product-1",
                    "product_name": "Nasi Ayam",
                    "status": "in_progress",
                    "created_at": "2026-05-27T00:00:00Z",
                }
            ],
            "qc_reports": [],
        }
        self.inserted = {}

    def table(self, table):
        return QCQuery(table, self)


def test_qc_active_endpoint_returns_lock_detail(client, staff_headers):
    db = QCDb()
    db.fixtures["qc_reports"] = [
        {
            "id": "inspection-active",
            "batch_id": "batch-1",
            "batch_code": "BATCH-1",
            "staff_id": "staff-2",
            "inspector_name": "Budi",
            "qc_stage": "cooking_check",
            "is_active": True,
            "created_at": "2026-05-27T07:00:00Z",
        }
    ]

    with patch("backend.api.qc_routes.get_client", return_value=db):
        response = client.get("/api/qc/active?batch=batch-1", headers=staff_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["data"]["active"]["staff"] == "Budi"
    assert body["data"]["active"]["qc_type"] == "cooking_check"
    assert body["data"]["active"]["batch"] == "BATCH-1"


def test_qc_history_endpoint_returns_latest_completed_detail(client, staff_headers):
    db = QCDb()
    db.fixtures["qc_reports"] = [
        {
            "id": "inspection-1",
            "batch_id": "batch-1",
            "batch_code": "BATCH-1",
            "staff_id": "staff-1",
            "inspector_name": "Sari",
            "qc_stage": "final_check",
            "status": "pass",
            "temperature": "82",
            "photo_url": "https://example.test/photo.jpg",
            "is_active": False,
            "completed_at": "2026-05-27T07:15:00Z",
            "created_at": "2026-05-27T07:14:00Z",
        }
    ]

    with patch("backend.api.qc_routes.get_client", return_value=db):
        response = client.get("/api/qc/history/batch-1", headers=staff_headers)

    latest = response.get_json()["data"]["latest"]
    assert response.status_code == 200
    assert latest["temperature"] == "82"
    assert latest["status"] == "pass"
    assert latest["photo_url"].endswith("photo.jpg")
    assert latest["staff"] == "Sari"
    assert latest["completed_at"] == "2026-05-27T07:15:00Z"


def test_staff_submit_is_blocked_when_batch_has_active_qc(client, staff_headers):
    db = QCDb()
    db.fixtures["qc_reports"] = [
        {
            "id": "inspection-active",
            "batch_id": "batch-1",
            "batch_code": "BATCH-1",
            "staff_id": "staff-2",
            "inspector_name": "Budi",
            "is_active": True,
            "created_at": "2026-05-27T07:00:00Z",
        }
    ]

    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "sku_code": "SKU-1",
                "batch_id": "batch-1",
                "batch_code": "BATCH-1",
                "qc_stage": "final_check",
                "qc_status": "pass",
            },
        )

    assert response.status_code == 409
    assert response.get_json()["message"] == "Sedang diperiksa oleh Budi"
    assert "qc_reports" not in db.inserted


def test_admin_submit_can_override_active_qc_lock(client, admin_headers):
    db = QCDb()
    db.fixtures["qc_reports"] = [
        {
            "id": "inspection-active",
            "batch_id": "batch-1",
            "batch_code": "BATCH-1",
            "staff_id": "staff-2",
            "inspector_name": "Budi",
            "is_active": True,
        }
    ]

    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=admin_headers,
            data={
                "sku_code": "SKU-1",
                "batch_id": "batch-1",
                "batch_code": "BATCH-1",
                "qc_stage": "final_check",
                "qc_status": "pass",
            },
        )

    assert response.status_code == 200
    assert db.inserted["qc_reports"][0]["is_active"] is False
    assert db.inserted["qc_reports"][0]["completed_at"]


def test_recheck_submit_increments_round_and_sets_parent(client, staff_headers):
    db = QCDb()
    db.fixtures["qc_reports"] = [
        {
            "id": "inspection-old",
            "batch_id": "batch-1",
            "batch_code": "BATCH-1",
            "inspection_round": 1,
            "is_active": False,
        }
    ]

    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "sku_code": "SKU-1",
                "batch_id": "batch-1",
                "batch_code": "BATCH-1",
                "qc_stage": "final_check",
                "qc_status": "pass",
                "parent_inspection": "inspection-old",
            },
        )

    report = db.inserted["qc_reports"][0]
    assert response.status_code == 200
    assert report["inspection_round"] == 2
    assert report["parent_inspection"] == "inspection-old"


def test_inspection_ui_contains_qc_concurrency_history_panel():
    from pathlib import Path

    html = Path("frontend/staff/inspection.html").read_text(encoding="utf-8")
    js = Path("frontend/js/inspection.js").read_text(encoding="utf-8")
    assert "qcConcurrencyPanel" in html
    assert "Lihat Detail" in html
    assert "Tambah Re-check" in html
    assert "/qc/active" in js
    assert "/qc/history/" in js
    assert "parent_inspection" in js
    assert "🟢 Sedang diperiksa" in js
    assert "🔵 Selesai" in html
    assert "🟠 Re-check" in js
    assert "🔴 HOLD" in js
