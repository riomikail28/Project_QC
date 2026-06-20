from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_task3_finding_appears_in_admin_report_with_normalized_photo(client, admin_headers):
    db = FakeSupabase(
        {
            "qc_findings": [
                {
                    "id": "finding-1",
                    "staff_id": "staff-1",
                    "reason": "Kemasan rusak",
                    "storage_path": "staff/staff-1/findings/finding.jpg",
                    "created_at": "2026-05-16T03:00:00Z",
                }
            ]
        }
    )

    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/admin/reports/findings?date=2026-05-16", headers=admin_headers)

    row = response.get_json()["data"][0]
    assert response.status_code == 200
    assert row["report_type"] == "qc_finding"
    assert row["has_photo"] is True
    assert row["photo_url"].startswith("https://example.supabase.co/storage/v1/object/public/qc-evidence/")
