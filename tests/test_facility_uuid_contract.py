from unittest.mock import patch

ROOM_ID = "11111111-1111-4111-8111-111111111111"
DEVICE_ID = "22222222-2222-4222-8222-222222222222"


def test_facility_structure_does_not_contain_synthetic_ids(client, staff_headers):
    from tests.test_facility_rooms_devices import FacilityDb

    db = FacilityDb()
    with patch("backend.monitoring.facility_manager.get_client", return_value=db):
        response = client.get("/api/facility/structure", headers=staff_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    text = response.get_data(as_text=True)
    assert "default-room-" not in text
    assert "log-room-" not in text
    assert body["data"][0]["id"] == ROOM_ID
    assert body["data"][0]["devices"][0]["id"] == DEVICE_ID


def test_delete_device_with_synthetic_id_returns_400(client, admin_headers):
    response = client.delete("/api/facility/devices/default-room-kitchen-chiller", headers=admin_headers)

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["error_code"] == "INVALID_DEVICE_ID"
