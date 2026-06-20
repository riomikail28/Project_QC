from pathlib import Path

from backend.services.admin_service import AdminService

ROOT = Path(__file__).resolve().parents[1]


def test_admin_evidence_normalizes_storage_path_to_photo_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    service = AdminService(sb_client=None)
    record = service.normalize_evidence_url(
        {
            "bucket": "qc-evidence",
            "storage_path": "staff/staff-1/temperature/photo.jpg",
        }
    )

    assert record["has_photo"] is True
    assert (
        record["photo_url"]
        == "https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/staff-1/temperature/photo.jpg"
    )
    assert record["storage_path"] == "staff/staff-1/temperature/photo.jpg"


def test_admin_render_evidence_cell_uses_thumbnail_not_storage_path_text():
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "Evidence photo" in js
    assert "width:80px;height:80px" in js
    assert "No photo" in js
    assert "admin-evidence-path" not in js
