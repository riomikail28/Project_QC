from backend.core.di import clear, register
from backend.repositories.qc_repository import QCRepository
from backend.services.qc_service import QCService
from tests.conftest import FakeSupabase


class FailingStorage:
    def upload_file_storage(self, *args, **kwargs):
        raise AssertionError("Backend storage upload should not run when photo_url is provided")


def test_qc_finding_accepts_preuploaded_photo_url_in_production(client, staff_headers, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    fake_db = FakeSupabase({"qc_findings": []})
    clear()
    register("qc_service", QCService(QCRepository(fake_db), storage_service=FailingStorage()))

    try:
        response = client.post(
            "/api/qc/findings",
            headers=staff_headers,
            data={
                "reason": "Foreign object found on packing table",
                "photo_url": "https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/2026-05-16/finding.jpg",
                "storage_path": "staff/2026-05-16/finding.jpg",
            },
        )
    finally:
        clear()

    assert response.status_code == 200
    body = response.get_json()
    assert body["photo_url"].endswith("/finding.jpg")
    assert body["storage_path"] == "staff/2026-05-16/finding.jpg"
    assert body["reason"] == "Foreign object found on packing table"


def test_qc_finding_json_payload_accepts_preuploaded_photo_url(client, staff_headers):
    fake_db = FakeSupabase({"qc_findings": []})
    clear()
    register("qc_service", QCService(QCRepository(fake_db), storage_service=FailingStorage()))

    try:
        response = client.post(
            "/api/qc/findings",
            headers=staff_headers,
            json={
                "reason": "Damaged seal",
                "photo_url": "https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/finding.webp",
                "storage_path": "staff/finding.webp",
            },
        )
    finally:
        clear()

    assert response.status_code == 200
    body = response.get_json()
    assert body["photo_url"].endswith("/finding.webp")
    assert body["storage_path"] == "staff/finding.webp"
