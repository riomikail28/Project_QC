from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from tests.conftest import FakeSupabase
from tests.test_monitoring import RecordingSupabase


def test_task3_staff_submit_inspection_with_photo_admin_report_and_pending_approval(
    client, staff_headers, admin_headers
):
    db = RecordingSupabase()
    db.fixtures["products"] = []
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
        patch("backend.services.inspection_service.write_audit"),
    ):
        submit = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "sku_code": "SKU-100",
                "qc_stage": "final_check",
                "qc_status": "hold",
                "staff_id": "staff-1",
                "photo": (BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 12), "photo.jpg"),
            },
            content_type="multipart/form-data",
        )

    assert submit.status_code == 200
    report_row = {"id": "qc_reports-1", **db.inserted["qc_reports"], "created_at": "2026-05-16T02:00:00Z"}
    approval_row = {"id": "approval-1", **db.inserted["approvals"], "created_at": "2026-05-16T02:01:00Z"}
    admin_db = FakeSupabase({"qc_reports": [report_row], "approvals": [approval_row]})
    with patch("backend.services.admin_service.get_client", return_value=admin_db):
        reports = client.get("/api/admin/reports/inspection?date=2026-05-16", headers=admin_headers)
        approvals = client.get("/api/admin/approvals", headers=admin_headers)

    assert reports.status_code == 200
    assert reports.get_json()["data"][0]["approval_status"] == "pending"
    assert reports.get_json()["data"][0]["photo_url"].endswith("/photo.jpg")
    assert approvals.status_code == 200
    assert approvals.get_json()[0]["approval_status"] == "pending"
