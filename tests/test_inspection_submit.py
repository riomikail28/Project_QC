from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch


class InsertQuery:
    def __init__(self, table, db):
        self.table = table
        self.db = db
        self.payload = None

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        if self.payload is None:
            return SimpleNamespace(data=[])
        row = {"id": f"{self.table}-1", **self.payload}
        self.db.inserted.setdefault(self.table, []).append(row)
        return SimpleNamespace(data=[row])


class InsertDb:
    def __init__(self):
        self.inserted = {}

    def table(self, table):
        return InsertQuery(table, self)


class MissingColumnInsertQuery(InsertQuery):
    def execute(self):
        if self.payload is not None and self.table == "qc_reports" and "staff_name" in self.payload:
            raise Exception({
                "code": "PGRST204",
                "details": None,
                "hint": None,
                "message": "Could not find the 'staff_name' column of 'qc_reports' in the schema cache",
            })
        return super().execute()


class MissingColumnInsertDb(InsertDb):
    def table(self, table):
        return MissingColumnInsertQuery(table, self)


def test_submit_inspection_without_photo_succeeds(client, staff_headers):
    db = InsertDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"barcode": "MANUAL-001", "qc_stage": "final_check", "qc_status": "pass"},
        )

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert db.inserted["qc_reports"][0]["barcode"] == "MANUAL-001"


def test_submit_inspection_retries_when_staff_name_missing_from_schema_cache(client, staff_headers):
    db = MissingColumnInsertDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "barcode": "MANUAL-001",
                "qc_stage": "final_check",
                "qc_status": "pass",
                "staff_name": "Siti QC",
            },
        )

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert "staff_name" not in db.inserted["qc_reports"][0]
    assert db.inserted["qc_reports"][0]["inspector_name"] == "Siti QC"


def test_submit_inspection_with_photo_succeeds(client, staff_headers):
    db = InsertDb()
    upload = SimpleNamespace(
        url="https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/staff-1/inspection/photo.jpg",
        storage_path="staff/staff-1/inspection/photo.jpg",
        file_name="photo.jpg",
        file_type="image/jpeg",
        file_size=10,
        bucket="qc-evidence",
    )
    with patch("backend.services.inspection_service.get_client", return_value=db), patch(
        "backend.services.inspection_service.upload_file_storage", return_value=upload
    ):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "barcode": "MANUAL-002",
                "qc_stage": "final_check",
                "qc_status": "pass",
                "photo": (BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 10), "photo.jpg"),
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    assert db.inserted["qc_reports"][0]["storage_path"] == "staff/staff-1/inspection/photo.jpg"
    assert db.inserted["qc_evidence"][0]["mime_type"] == "image/jpeg"


def test_submit_inspection_missing_barcode_has_clear_error(client, staff_headers):
    with patch("backend.services.inspection_service.get_client", return_value=InsertDb()):
        response = client.post("/api/inspection/submit", headers=staff_headers, data={})

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert "sku" in body["message"].lower() or "barcode" in body["message"].lower()
