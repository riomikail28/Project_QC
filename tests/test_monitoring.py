from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_monitoring_structure_requires_auth(client):
    response = client.get("/api/facility/structure")

    assert response.status_code == 401


def test_monitoring_latest_returns_empty_when_supabase_offline(client, staff_headers):
    with patch("backend.api.temperature_routes.get_client", return_value=None):
        response = client.get("/api/monitoring/latest", headers=staff_headers)

    assert response.status_code == 200
    assert response.get_json() == []


def test_temperature_log_validates_empty_request(client, staff_headers):
    response = client.post("/api/monitoring/log", headers=staff_headers, json={})

    assert response.status_code == 400
    assert "room_id" in response.get_json()["details"]


def test_temperature_log_saves_normal_reading(client, staff_headers):
    fake_db = FakeSupabase({
        "facility_rooms": [{"name": "Chiller Room"}],
        "facility_devices": [{"id": "device-1", "type": "chiller", "threshold_temp": 4}],
    })

    with patch("backend.api.temperature_routes.get_client", return_value=fake_db), patch(
        "backend.api.temperature_routes.write_audit"
    ):
        response = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            json={"room_id": "room-1", "device_id": "device-1", "temperature": 3.2},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["status"] == "PASS"
