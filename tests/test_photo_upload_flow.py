from io import BytesIO
from unittest.mock import patch


class FakeStorageBucket:
    def upload(self, path, file, file_options=None):
        self.path = path
        return {"path": path}

    def get_public_url(self, path):
        return f"https://example.supabase.co/storage/v1/object/public/qc-evidence/{path}"


class FakeStorage:
    def __init__(self):
        self.bucket = FakeStorageBucket()

    def from_(self, bucket):
        assert bucket == "qc-evidence"
        return self.bucket


class FakeDb:
    def __init__(self):
        self.storage = FakeStorage()


def test_storage_path_uses_qc_evidence_staff_temperature_layout():
    from backend.services.storage_service import upload_photo_result

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 10
    with patch("backend.services.storage_service.get_client", return_value=FakeDb()):
        uploaded = upload_photo_result(
            png,
            "temp.png",
            staff_id="staff-1",
            content_type="image/png",
            category="temperature",
        )

    assert uploaded.bucket == "qc-evidence"
    assert uploaded.storage_path.startswith("staff/staff-1/temperature/")
    assert uploaded.file_type == "image/png"
    assert uploaded.file_size == len(png)


def test_storage_upload_rejects_invalid_mime(client, staff_headers):
    response = client.post(
        "/api/storage/upload",
        headers=staff_headers,
        data={"photo": (BytesIO(b"not-an-image"), "bad.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
