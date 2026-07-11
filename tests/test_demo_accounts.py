import pytest
from unittest.mock import patch
from tests.conftest import FakeSupabase

def test_demo_staff_login_success(client):
    response = client.post(
        "/api/staff/login",
        json={"username": "demo_staff", "password": "demostaff123"}
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["username"] == "demo_staff"
    assert body["role"] == "staff"
    assert "token" in body

def test_demo_admin_login_success(client):
    response = client.post(
        "/api/staff/login",
        json={"username": "demo_admin", "password": "demoadmin123"}
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["username"] == "demo_admin"
    assert body["role"] == "admin"
    assert "token" in body

def test_demo_admin_mutating_requests_blocked(client):
    # Log in as demo_admin to get token
    login_resp = client.post(
        "/api/staff/login",
        json={"username": "demo_admin", "password": "demoadmin123"}
    )
    token = login_resp.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt POST to an admin endpoint
    fake_db = FakeSupabase({"products": []})
    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.post(
            "/api/v1/admin/products",
            json={
                "product_code": "SKU-DEMO-001",
                "product_name": "Demo Blocked Product",
                "is_active": True,
            },
            headers=headers
        )

    assert response.status_code == 403
    body = response.get_json()
    assert "Akun Demo Admin" in body["error"]
