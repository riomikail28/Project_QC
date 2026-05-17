from unittest.mock import patch


ROOM_ID = "11111111-1111-4111-8111-111111111111"
DEVICE_ID = "22222222-2222-4222-8222-222222222222"


def test_monitoring_submit_rejects_synthetic_room_id(client, staff_headers):
    response = client.post(
        "/api/monitoring/log",
        headers=staff_headers,
        json={"room_id": "default-room-kitchen", "device_id": DEVICE_ID, "temperature": 4.2},
    )

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["error_code"] == "INVALID_ROOM_ID"
    assert "default-room-kitchen" in body["message"]


def test_monitoring_submit_rejects_synthetic_device_id(client, staff_headers):
    response = client.post(
        "/api/monitoring/log",
        headers=staff_headers,
        json={"room_id": ROOM_ID, "device_id": "default-device-kitchen-chiller", "temperature": 4.2},
    )

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["error_code"] == "INVALID_DEVICE_ID"


def test_monitoring_submit_with_uuid_valid_succeeds(client, staff_headers):
    from tests.conftest import FakeSupabase

    fake_db = FakeSupabase({
        "facility_rooms": [{"id": ROOM_ID, "name": "Kitchen"}],
        "facility_devices": [{"id": DEVICE_ID, "room_id": ROOM_ID, "type": "chiller", "threshold_temp": 5}],
    })

    with patch("backend.api.temperature_routes.get_client", return_value=fake_db), patch(
        "backend.api.temperature_routes.write_audit"
    ):
        response = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            json={"room_id": ROOM_ID, "device_id": DEVICE_ID, "temperature": 4.2},
        )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
