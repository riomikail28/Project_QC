from unittest.mock import patch

from tests.test_qc_check_cooking_final_flow import FlowDb


def test_inspection_products_returns_active_products_from_admin_catalog(client, staff_headers):
    db = FlowDb()
    db.fixtures["products"].append({
        "id": "product-2",
        "product_code": "SKU-BEEF-001",
        "product_name": "Finish Goods - Original beef 90gr",
        "is_active": True,
    })

    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.get("/api/inspection/products", headers=staff_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert {item["product_code"] for item in body["data"]} >= {"SKU-CK", "SKU-BEEF-001"}


def test_inspection_products_hides_inactive_products(client, staff_headers):
    db = FlowDb()
    db.fixtures["products"].append({
        "id": "inactive-1",
        "product_code": "SKU-OFF-001",
        "product_name": "Inactive product",
        "is_active": False,
    })

    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.get("/api/inspection/products", headers=staff_headers)

    codes = {item["product_code"] for item in response.get_json()["data"]}
    assert "SKU-OFF-001" not in codes


def test_submit_qc_with_product_id_uses_database_product_values(client, staff_headers):
    db = FlowDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "product_id": "product-1",
                "product_name": "Tampered Name",
                "sku_code": "TAMPERED-SKU",
                "qc_stage": "final_check",
                "qc_status": "pass",
                "staff_id": "staff-1",
                "operational_date": "2026-05-17",
            },
        )

    report = db.inserted["qc_reports"][0]
    assert response.status_code == 200
    assert report["product_id"] == "product-1"
    assert report["product_name"] == "Chicken Katsu"
    assert report["barcode"] == "SKU-CK"


def test_submit_qc_manual_sku_fallback_succeeds(client, staff_headers):
    db = FlowDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "sku_code": "MANUAL-001",
                "product_name": "Manual SKU",
                "qc_stage": "final_check",
                "qc_status": "hold",
                "staff_id": "staff-1",
            },
        )

    report = db.inserted["qc_reports"][0]
    assert response.status_code == 200
    assert report.get("product_id") is None
    assert report["product_name"] == "Manual SKU"
    assert report["barcode"] == "MANUAL-001"


def test_submit_without_product_and_without_manual_sku_fails(client, staff_headers):
    db = FlowDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"qc_stage": "final_check", "qc_status": "pass", "staff_id": "staff-1"},
        )

    assert response.status_code == 400
    assert "SKU" in response.get_json()["message"]


def test_new_admin_product_is_returned_to_staff_picker(client, staff_headers):
    db = FlowDb()
    db.fixtures["products"].append({
        "id": "product-new",
        "product_code": "SKU-CHKN-001",
        "product_name": "Finish Goods - Chilled/Frozen Teriyaki chicken 90gr - AK",
        "is_active": True,
    })

    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.get("/api/inspection/products", headers=staff_headers)

    names = {item["product_name"] for item in response.get_json()["data"]}
    assert "Finish Goods - Chilled/Frozen Teriyaki chicken 90gr - AK" in names


def test_admin_report_exposes_product_code_and_name(client, admin_headers):
    db = FlowDb()
    db.fixtures["qc_reports"] = [{
        "id": "report-1",
        "batch_code": "QC-20260517-001",
        "barcode": "SKU-CHKN-001",
        "product_name": "Chicken Katsu",
        "qc_stage": "final_check",
        "status": "pass",
        "approval_status": "pending",
        "created_at": "2026-05-17T06:00:00Z",
    }]

    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/admin/reports/inspection?date=2026-05-17", headers=admin_headers)

    row = response.get_json()["data"][0]
    assert response.status_code == 200
    assert row["product_code"] == "SKU-CHKN-001"
    assert row["product_name"] == "Chicken Katsu"
