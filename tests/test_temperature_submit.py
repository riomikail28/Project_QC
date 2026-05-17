from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_monitoring import RecordingSupabase

ROOM_ID = "11111111-1111-4111-8111-111111111111"
DEVICE_ID = "22222222-2222-4222-8222-222222222222"


def test_submit_temperature_without_photo_succeeds(client, staff_headers):
    db = RecordingSupabase()

    with patch("backend.api.temperature_routes.get_client", return_value=db), patch(
        "backend.api.temperature_routes.write_audit"
    ):
        response = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": DEVICE_ID, "temperature": "4.5"},
        )

    assert response.status_code == 200
    payload = db.inserted["facility_logs"]
    assert payload["temperature_c"] == 4.5
    assert "device_type" not in payload
    assert "zone" not in payload


def test_submit_temperature_with_photo_succeeds(client, staff_headers):
    db = RecordingSupabase()
    uploaded = SimpleNamespace(
        url="https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/staff-1/temperature/photo.jpg",
        storage_path="staff/staff-1/temperature/photo.jpg",
    )

    with patch("backend.api.temperature_routes.get_client", return_value=db), patch(
        "backend.services.monitoring_service.upload_file_storage", return_value=uploaded
    ), patch("backend.api.temperature_routes.write_audit"):
        response = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            data={
                "room_id": ROOM_ID,
                "device_id": DEVICE_ID,
                "temperature": "4.5",
                "photo": (BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 10), "temp.jpg"),
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    assert db.inserted["facility_logs"]["storage_path"] == "staff/staff-1/temperature/photo.jpg"
