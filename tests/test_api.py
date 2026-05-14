from unittest.mock import patch


def test_health_endpoint_is_public(client):
    response = client.get("/api/qc/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_qc_validate_rejects_malformed_payload(client, staff_headers):
    response = client.post(
        "/api/qc/validate",
        headers={**staff_headers, "Content-Type": "application/json"},
        data="{bad json",
    )

    assert response.status_code == 400
    assert "temperature" in response.get_json()["details"]


def test_qc_validate_rejects_unknown_field(client, staff_headers):
    response = client.post(
        "/api/qc/validate",
        headers=staff_headers,
        json={"temperature": 4, "unit_type": "chiller", "unexpected": True},
    )

    assert response.status_code == 400
    assert "unknown_fields" in response.get_json()["details"]


def test_batch_status_accepts_empty_request(client):
    response = client.post("/api/batch/status", json={})

    assert response.status_code == 200
    body = response.get_json()
    assert body["total_checks"] == 0
    assert body["qc_score"] == 0


def test_products_endpoint_has_local_fallback(client, staff_headers):
    response = client.get("/api/products", headers=staff_headers)

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_admin_analytics_endpoint_uses_admin_service(client, admin_headers):
    fake_service = type(
        "FakeAdminService",
        (),
        {"get_dashboard_overview": lambda self: {"success": True, "data": {"total_batches_today": 3}}},
    )
    with patch("backend.api.admin_routes.AdminService", fake_service):
        response = client.get("/api/v1/admin/analytics/overview", headers=admin_headers)

    assert response.status_code == 200
    assert response.get_json()["total_batches_today"] == 3


def test_staff_cannot_access_admin_analytics(client, staff_headers):
    response = client.get("/api/v1/admin/analytics/overview", headers=staff_headers)

    assert response.status_code == 403
