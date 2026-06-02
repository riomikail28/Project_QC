from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from tests.conftest import FakeSupabase
from tests.test_monitoring import RecordingSupabase


def test_qc_finding_persists_and_records_evidence(client, staff_headers):
    db = RecordingSupabase()
    uploaded = SimpleNamespace(
        url="https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/staff-1/findings/finding.jpg",
        storage_path="staff/staff-1/findings/finding.jpg",
        file_name="finding.jpg",
        file_type="image/jpeg",
        file_size=16,
        bucket="qc-evidence",
    )

    with patch("backend.core.di.resolve", return_value=None), patch(
        "backend.api.qc_routes.get_client", return_value=db
    ), patch("backend.services.storage_service.upload_file_storage", return_value=uploaded), patch(
        "backend.services.qc_service.send_qc_finding", return_value=True
    ) as send_finding:
        response = client.post(
            "/api/qc/findings",
            headers=staff_headers,
            data={
                "reason": "Kemasan rusak",
                "staff_name": "Manual Name",
                "photo": (BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 12), "finding.jpg"),
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    assert db.inserted["qc_findings"]["reason"] == "Kemasan rusak"
    assert db.inserted["qc_findings"]["photo_url"].endswith("finding.jpg")
    assert db.inserted["qc_evidence"]["related_type"] == "qc_finding"
    assert db.inserted["qc_evidence"]["storage_path"] == "staff/staff-1/findings/finding.jpg"
    send_finding.assert_called_once()
    assert send_finding.call_args.args[0]["staff_name"] == "staff"


def test_qc_finding_appears_in_admin_report(client, admin_headers):
    db = FakeSupabase({"qc_findings": [{
        "id": "finding-1",
        "staff_id": "staff-1",
        "reason": "Kemasan rusak",
        "photo_url": "https://example.com/finding.jpg",
        "storage_path": "staff/staff-1/findings/finding.jpg",
        "created_at": "2026-05-16T03:00:00Z",
    }]})

    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/admin/reports/findings?date=2026-05-16", headers=admin_headers)

    assert response.status_code == 200
    rows = response.get_json()["data"]
    assert rows[0]["reason"] == "Kemasan rusak"
    assert rows[0]["report_type"] == "qc_finding"
