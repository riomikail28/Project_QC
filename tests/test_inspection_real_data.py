from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_inspection_summary_empty_database(client, staff_headers):
    with patch("backend.services.inspection_service.get_client", return_value=FakeSupabase({})):
        response = client.get("/api/inspection/summary", headers=staff_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["pass"] == 0
    assert body["data"]["hold_pending"] == 0
    assert body["data"]["active_batches"] == 0
    assert body["data"]["has_data"] is False


def test_inspection_summary_uses_real_tables(client, staff_headers):
    fake_db = FakeSupabase({
        "production_batches": [
            {"id": "batch-1", "batch_code": "B-1", "status": "pending"},
            {"id": "batch-2", "batch_code": "B-2", "status": "done"},
        ],
        "qc_reports": [
            {"id": "qc-1", "status": "pass"},
            {"id": "qc-2", "status": "warning"},
        ],
        "approvals": [{"id": "approval-1", "status": "pending"}],
        "barcode_labels": [{"id": "label-1"}],
    })

    with patch("backend.services.inspection_service.get_client", return_value=fake_db):
        response = client.get("/api/inspection/summary", headers=staff_headers)

    body = response.get_json()
    assert body["data"]["pass"] == 1
    assert body["data"]["hold_pending"] == 1
    assert body["data"]["active_batches"] == 1
    assert body["data"]["barcode_labels"] == 1


def test_inspection_product_shortcuts(client, staff_headers):
    fake_db = FakeSupabase({
        "products": [
            {"id": "p1", "product_code": "SKU-1", "product_name": "Product 1", "is_active": True},
            {"id": "p2", "product_code": "SKU-2", "product_name": "Product 2", "is_active": False},
        ]
    })

    with patch("backend.services.inspection_service.get_client", return_value=fake_db):
        response = client.get("/api/inspection/product-shortcuts", headers=staff_headers)

    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["product_code"] == "SKU-1"


def test_inspection_service_uses_direct_supabase_when_sdk_unavailable(monkeypatch):
    from backend.services import inspection_service

    def fake_direct(table, method="GET", payload=None, filters=""):
        assert method == "GET"
        if table == "production_batches":
            return [{"id": "batch-1", "batch_code": "B-1", "status": "pending", "product_name": "Soup"}]
        if table == "qc_reports":
            return [{"id": "report-1", "status": "pass"}]
        return []

    monkeypatch.setattr(inspection_service, "get_client", lambda: None)
    monkeypatch.setattr(inspection_service, "direct_db_query", fake_direct)

    service = inspection_service.InspectionService()

    assert service.summary()["data"]["active_batches"] == 1
    assert service.active_batches()["data"][0]["batch_code"] == "B-1"
