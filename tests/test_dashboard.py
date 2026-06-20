from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_dashboard_returns_empty_fallback_when_supabase_offline(client, staff_headers):
    with patch("backend.api.qc_routes.get_client", return_value=None):
        response = client.get("/api/qc/dashboard", headers=staff_headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["health_score"] == 0
    assert body["critical_issues"] == []


def test_dashboard_aggregates_temperature_and_alerts(client, staff_headers):
    fake_db = FakeSupabase(
        {
            "facility_logs": [
                {
                    "temperature_c": 3.0,
                    "is_normal": True,
                    "recorded_at": "2026-05-14T08:00:00Z",
                    "facility_rooms": {"name": "Chiller A"},
                    "facility_devices": {"name": "Unit 1", "type": "chiller", "threshold_temp": 4},
                },
                {
                    "temperature_c": -10.0,
                    "is_normal": False,
                    "recorded_at": "2026-05-14T08:05:00Z",
                    "facility_rooms": {"name": "Freezer B"},
                    "facility_devices": {"name": "Unit 2", "type": "freezer", "threshold_temp": -18},
                },
            ],
            "facility_alerts": [{"id": "alert-1", "status": "open"}],
        }
    )

    with patch("backend.api.qc_routes.get_client", return_value=fake_db):
        response = client.get("/api/qc/dashboard", headers=staff_headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["open_alerts"] == 1
    assert len(body["temperature_rooms"]) == 2
    assert body["critical_issues"]


def test_dashboard_page_and_check_alias_are_served(client):
    dashboard = client.get("/dashboard.html")
    check = client.get("/check.html")

    assert dashboard.status_code == 200
    assert check.status_code == 200
    assert b"QC Check" in check.data
