from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from tests.conftest import FakeSupabase
from tests.test_monitoring import DEVICE_ID, ROOM_ID, RecordingSupabase


def test_task3_staff_submit_monitoring_with_photo_then_admin_reads_report(client, staff_headers, admin_headers):
    db = RecordingSupabase()
    uploaded = SimpleNamespace(
        url="https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/staff-1/temperature/photo.jpg",
        storage_path="staff/staff-1/temperature/photo.jpg",
        file_name="photo.jpg",
        file_type="image/jpeg",
        file_size=16,
        bucket="qc-evidence",
    )

    with (
        patch("backend.api.temperature_routes.get_client", return_value=db),
        patch("backend.services.monitoring_service.upload_file_storage", return_value=uploaded),
        patch("backend.api.temperature_routes.write_audit"),
    ):
        submit = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            data={
                "room_id": ROOM_ID,
                "device_id": DEVICE_ID,
                "temperature": "3.5",
                "humidity": "55",
                "photo": (BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 12), "photo.jpg"),
            },
            content_type="multipart/form-data",
        )

    assert submit.status_code == 200
    admin_db = FakeSupabase(
        {
            "facility_logs": [
                {
                    **db.inserted["facility_logs"],
                    "id": "facility_logs-1",
                    "facility_rooms": {"name": "Chiller Room"},
                    "facility_devices": {"name": "Chiller", "type": "chiller"},
                }
            ],
        }
    )
    with patch("backend.services.admin_service.get_client", return_value=admin_db):
        report = client.get("/api/admin/reports/temperature", headers=admin_headers)

    assert report.status_code == 200
    row = report.get_json()["data"][0]
    assert row["room"] == "Chiller Room"
    assert row["device"] == "Chiller"
    assert row["humidity"] == 55.0
    assert row["photo_url"].endswith("/photo.jpg")


def test_task3_monitoring_rejects_synthetic_room_id(client, staff_headers):
    response = client.post(
        "/api/monitoring/log",
        headers=staff_headers,
        json={"room_id": "default-room-kitchen", "device_id": DEVICE_ID, "temperature": 4},
    )

    body = response.get_json()
    assert response.status_code == 400
    assert body["error_code"] == "INVALID_ROOM_ID"
    assert "default-room-kitchen" in body["message"]
