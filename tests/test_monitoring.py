from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_monitoring_structure_requires_auth(client):
    response = client.get("/api/facility/structure")

    assert response.status_code == 401


def test_monitoring_latest_returns_empty_when_supabase_offline(client, staff_headers):
    with patch("backend.api.temperature_routes.get_client", return_value=None):
        response = client.get("/api/monitoring/latest", headers=staff_headers)

    assert response.status_code == 200
    assert response.get_json() == []


def test_temperature_log_validates_empty_request(client, staff_headers):
    response = client.post("/api/monitoring/log", headers=staff_headers, json={})

    assert response.status_code == 400
    assert "room_id" in response.get_json()["details"]


def test_temperature_log_saves_normal_reading(client, staff_headers):
    fake_db = FakeSupabase({
        "facility_rooms": [{"name": "Chiller Room"}],
        "facility_devices": [{"id": "device-1", "type": "chiller", "threshold_temp": 4}],
    })

    with patch("backend.api.temperature_routes.get_client", return_value=fake_db), patch(
        "backend.api.temperature_routes.write_audit"
    ):
        response = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            json={"room_id": "room-1", "device_id": "device-1", "temperature": 3.2},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["status"] == "PASS"


class RecordingQuery:
    def __init__(self, table_name, db):
        self.table_name = table_name
        self.db = db
        self.payload = None
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            self.db.inserted[self.table_name] = self.payload
            return type("Result", (), {"data": [{"id": f"{self.table_name}-1", **self.payload}]})()
        rows = list(self.db.fixtures.get(self.table_name, []))
        for field, value in self.filters:
            rows = [row for row in rows if row.get(field) == value]
        return type("Result", (), {"data": rows})()


class RecordingSupabase:
    def __init__(self):
        self.fixtures = {
            "facility_rooms": [{"id": "room-1", "name": "Chiller Room"}],
            "facility_devices": [{"id": "device-1", "type": "chiller", "threshold_temp": 4}],
        }
        self.inserted = {}

    def table(self, table_name):
        return RecordingQuery(table_name, self)


def test_temperature_log_saves_preuploaded_photo_metadata(client, staff_headers):
    fake_db = RecordingSupabase()

    with patch("backend.api.temperature_routes.get_client", return_value=fake_db), patch(
        "backend.api.temperature_routes.write_audit"
    ):
        response = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            data={
                "room_id": "room-1",
                "device_id": "device-1",
                "temperature": "3.2",
                "humidity": "55",
                "reason": "normal check",
                "photo_url": "https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/temp.jpg",
                "storage_path": "staff/2026-05-16/temp.jpg",
            },
        )

    assert response.status_code == 200
    payload = fake_db.inserted["facility_logs"]
    assert payload["temperature_c"] == 3.2
    assert payload["humidity_rh"] == 55
    assert payload["reason"] == "normal check"
    assert payload["photo_url"].endswith("/temp.jpg")
    assert payload["storage_path"] == "staff/2026-05-16/temp.jpg"


def test_monitoring_structure_has_no_local_room_fallback(monkeypatch):
    from backend.monitoring import facility_manager

    monkeypatch.setattr(facility_manager, "get_client", lambda: None)
    monkeypatch.setattr(facility_manager, "direct_db_query", lambda *args, **kwargs: [])

    assert facility_manager.get_monitoring_structure() == []


def test_monitoring_structure_falls_back_to_recent_logs(monkeypatch):
    from backend.monitoring import facility_manager

    def fake_direct(table, method="GET", payload=None, filters=""):
        if table == "facility_rooms" or table == "facility_devices":
            return []
        if table == "facility_logs":
            return [
                {
                    "id": "log-1",
                    "room_id": "room-ppic",
                    "device_id": "device-chiller",
                    "temperature_c": 3.5,
                    "facility_rooms": {"name": "PPIC"},
                    "facility_devices": {"name": "Chiller", "type": "chiller", "threshold_temp": 5},
                },
                {
                    "id": "log-2",
                    "room_id": "room-kitchen",
                    "device_id": "device-freezer",
                    "temperature_c": -19,
                    "facility_rooms": {"name": "Kitchen"},
                    "facility_devices": {"name": "Freezer", "type": "freezer", "threshold_temp": -18},
                },
            ]
        return []

    monkeypatch.setattr(facility_manager, "get_client", lambda: None)
    monkeypatch.setattr(facility_manager, "direct_db_query", fake_direct)

    structure = facility_manager.get_monitoring_structure()

    assert [room["name"] for room in structure] == ["PPIC", "Kitchen"]
    assert structure[0]["devices"][0]["name"] == "Chiller"
    assert structure[1]["devices"][0]["type"] == "freezer"
