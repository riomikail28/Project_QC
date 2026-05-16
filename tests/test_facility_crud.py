from tests.test_facility_rooms_devices import FacilityDb
from unittest.mock import patch


def test_facility_crud_admin_endpoints_roundtrip(client, admin_headers):
    db = FacilityDb()

    with patch("backend.monitoring.facility_manager.get_client", return_value=db):
        room_response = client.post(
            "/api/admin/facility/rooms",
            headers=admin_headers,
            json={"name": "Cold Prep", "description": "Prep area", "is_active": True},
        )
        room = room_response.get_json()["data"]

        device_response = client.post(
            "/api/admin/facility/devices",
            headers=admin_headers,
            json={
                "room_id": room["id"],
                "name": "Chiller Line",
                "device_type": "chiller",
                "target_temperature": 5,
                "min_temperature": 0,
                "max_temperature": 8,
            },
        )
        device = device_response.get_json()["data"]

        updated = client.put(
            f"/api/admin/facility/devices/{device['id']}",
            headers=admin_headers,
            json={"name": "Freezer Line", "device_type": "freezer", "target_temperature": -18},
        )
        deleted = client.delete(f"/api/admin/facility/devices/{device['id']}", headers=admin_headers)

    assert room_response.status_code == 201
    assert device_response.status_code == 201
    assert updated.status_code == 200
    assert updated.get_json()["data"]["device_type"] == "freezer"
    assert deleted.status_code == 200
