from unittest.mock import patch

from backend import create_app


def test_staff_login_success_sets_access_token_and_cookie():
    with patch(
        "backend.auth.staff_manager.login",
        return_value={"id": "staff-1", "username": "staff", "role": "staff"},
    ):
        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()
        response = client.post("/api/staff/login", json={"username": "staff", "password": "pass"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["role"] == "staff"
    assert body["token"]
    assert any("refresh_token" in value for value in response.headers.get_all("Set-Cookie"))


def test_staff_login_empty_request_returns_validation_error(client):
    response = client.post("/api/staff/login", json={})

    assert response.status_code == 400
    assert "username" in response.get_json()["details"]


def test_admin_role_can_access_staff_list():
    with patch("backend.auth.staff_manager.list_staff", return_value=[{"id": "staff-1"}]):
        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()
        token = app.extensions["security"].generate_token(
            {
                "id": "admin-1",
                "username": "admin",
                "role": "admin",
            }
        )
        admin_headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/staff", headers=admin_headers)

    assert response.status_code == 200
    assert response.get_json() == [{"id": "staff-1"}]


def test_staff_role_cannot_access_staff_list(client, staff_headers):
    response = client.get("/api/staff", headers=staff_headers)

    assert response.status_code == 403


def test_logout_requires_valid_session(client):
    response = client.post("/api/staff/logout")

    assert response.status_code == 401
