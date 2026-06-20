from unittest.mock import patch


def test_facility_structure_empty_when_supabase_has_no_facility_rows(client, staff_headers):
    from tests.conftest import FakeSupabase

    fake_db = FakeSupabase({"facility_rooms": [], "facility_devices": []})
    with patch("backend.monitoring.facility_manager.get_client", return_value=fake_db):
        response = client.get("/api/facility/structure", headers=staff_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body == {"success": True, "data": [], "message": "OK"}


def test_facility_structure_filters_non_uuid_rows(client, staff_headers):
    from tests.conftest import FakeSupabase

    room_id = "11111111-1111-4111-8111-111111111111"
    device_id = "22222222-2222-4222-8222-222222222222"
    fake_db = FakeSupabase(
        {
            "facility_rooms": [
                {"id": "default-room-kitchen", "name": "Synthetic"},
                {"id": room_id, "name": "Kitchen", "slug": "kitchen"},
            ],
            "facility_devices": [
                {"id": "default-device", "room_id": room_id, "name": "Fake", "device_type": "chiller"},
                {
                    "id": device_id,
                    "room_id": room_id,
                    "name": "Chiller",
                    "device_type": "chiller",
                    "target_temperature": 5,
                },
            ],
        }
    )
    with patch("backend.monitoring.facility_manager.get_client", return_value=fake_db):
        response = client.get("/api/facility/structure", headers=staff_headers)

    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == room_id
    assert data[0]["devices"][0]["id"] == device_id
