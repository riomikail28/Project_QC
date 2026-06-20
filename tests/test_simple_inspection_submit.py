from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_monitoring import RecordingSupabase


def test_inspection_submit_manual_sku_without_notes_or_photo(client, staff_headers):
    db = RecordingSupabase()
    db.fixtures["products"] = []

    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"sku_code": "SKU-MANUAL-1", "qc_stage": "final_check", "qc_status": "pass", "staff_id": "staff-1"},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    report = db.inserted["qc_reports"]
    assert report["barcode"] == "SKU-MANUAL-1"
    assert report["product_name"] == "Manual SKU"
    assert report["status"] == "pass"
    assert report["approval_status"] == "pending"
    assert "notes" not in report


def test_inspection_submit_with_photo_records_evidence(client, staff_headers):
    db = RecordingSupabase()
    uploaded = SimpleNamespace(
        url="https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/staff-1/inspection/photo.jpg",
        storage_path="staff/staff-1/inspection/photo.jpg",
        file_name="photo.jpg",
        file_type="image/jpeg",
        file_size=16,
        bucket="qc-evidence",
    )

    with (
        patch("backend.services.inspection_service.get_client", return_value=db),
        patch("backend.services.inspection_service.upload_file_storage", return_value=uploaded),
    ):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "sku_code": "SKU-MANUAL-2",
                "qc_stage": "final_check",
                "qc_status": "hold",
                "staff_id": "staff-1",
                "notes": "Label kurang jelas",
                "photo": (BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 12), "photo.jpg"),
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    assert db.inserted["qc_reports"]["status"] == "hold"
    assert db.inserted["qc_reports"]["notes"] == "Label kurang jelas"
    assert db.inserted["qc_evidence"]["related_type"] == "qc_report"
    assert db.inserted["qc_evidence"]["storage_path"] == "staff/staff-1/inspection/photo.jpg"
