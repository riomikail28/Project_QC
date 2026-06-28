import pytest
from unittest.mock import patch
from tests.conftest import FakeSupabase

def test_announcements_crud_flow(client, admin_headers):
    db = FakeSupabase({"announcements": []})
    with patch("backend.services.admin_service.get_client", return_value=db):
        # 1. Create announcement missing title/content
        resp = client.post("/api/admin/announcements", json={}, headers=admin_headers)
        assert resp.status_code == 400

        # 2. Create valid announcement
        payload = {"title": "Maintenance Notice", "content": "System update at 10 PM"}
        resp = client.post("/api/admin/announcements", json=payload, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Maintenance Notice"
        announcement_id = data["id"]

        # 3. List announcements
        resp = client.get("/api/admin/announcements", headers=admin_headers)
        assert resp.status_code == 200
        items = resp.get_json()
        assert isinstance(items, list)

        # 4. Get announcement detail
        resp = client.get(f"/api/admin/announcements/{announcement_id}", headers=admin_headers)
        assert resp.status_code == 200

        # 5. Update announcement
        resp = client.patch(f"/api/admin/announcements/{announcement_id}", json={"title": "Updated Title"}, headers=admin_headers)
        assert resp.status_code == 200

        # 6. Delete announcement
        resp = client.delete(f"/api/admin/announcements/{announcement_id}", headers=admin_headers)
        assert resp.status_code == 200

def test_staff_announcements_flow(client, staff_headers):
    mock_data = [
        {"id": "a-1", "title": "Staff Update", "content": "Hello Staff", "is_active": True},
        {"id": "a-2", "title": "Inactive Announcement", "content": "Secret info", "is_active": False}
    ]
    db = FakeSupabase({"announcements": mock_data})
    with patch("backend.services.admin_service.get_client", return_value=db):
        resp = client.get("/api/staff/announcements", headers=staff_headers)
        assert resp.status_code == 200
        items = resp.get_json()
        assert isinstance(items, list)
        # Should only get active announcements
        assert len(items) == 1
        assert items[0]["title"] == "Staff Update"
