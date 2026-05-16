from unittest.mock import patch


def test_upload_storage_path_for_inspection_category():
    from backend.services.storage_service import upload_photo_result

    class Bucket:
        def upload(self, path, file, file_options=None):
            self.path = path

        def get_public_url(self, path):
            return f"https://example.supabase.co/storage/v1/object/public/qc-evidence/{path}"

    class Storage:
        def __init__(self):
            self.bucket = Bucket()

        def from_(self, bucket):
            return self.bucket

    class Db:
        def __init__(self):
            self.storage = Storage()

    with patch("backend.services.storage_service.get_client", return_value=Db()):
        uploaded = upload_photo_result(
            b"\xff\xd8\xff\xe0" + b"0" * 12,
            "evidence.jpg",
            staff_id="staff-1",
            content_type="image/jpeg",
            category="inspection",
        )

    assert uploaded.bucket == "qc-evidence"
    assert uploaded.storage_path.startswith("staff/staff-1/inspection/")
    assert uploaded.file_type == "image/jpeg"
