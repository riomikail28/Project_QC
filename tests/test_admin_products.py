from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_admin_can_list_products(client, admin_headers):
    fake_db = FakeSupabase({
        "products": [
            {
                "id": "product-1",
                "product_code": "SKU-TEST-001",
                "product_name": "Test Product",
                "is_active": True,
            }
        ]
    })

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.get("/api/v1/admin/products", headers=admin_headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body[0]["product_code"] == "SKU-TEST-001"


def test_staff_cannot_create_admin_product(client, staff_headers):
    response = client.post(
        "/api/v1/admin/products",
        json={"product_code": "SKU-TEST-002", "product_name": "Staff Product"},
        headers=staff_headers,
    )

    assert response.status_code == 403


def test_admin_can_create_product(client, admin_headers):
    fake_db = FakeSupabase({"products": []})

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.post(
            "/api/v1/admin/products",
            json={
                "product_code": "SKU-TEST-003",
                "product_name": "Admin Product",
                "ph_min": 4,
                "ph_max": 6,
                "is_active": True,
            },
            headers=admin_headers,
        )

    assert response.status_code == 201
    body = response.get_json()
    assert body["product_code"] == "SKU-TEST-003"
    assert body["ph_min"] == 4.0
