from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_monitoring_structure_requires_auth(client):
    response = client.get("/api/facility/structure")

    assert response.status_code == 401


def test_monitoring_latest_returns_error_when_supabase_offline(client, staff_headers):
    with patch("backend.api.temperature_routes.get_client", return_value=None):
        response = client.get("/api/monitoring/latest", headers=staff_headers)

    assert response.status_code == 503
    assert response.get_json()["success"] is False


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

    def gte(self, field, value):
        self.filters.append((field, value, "gte"))
        return self

    def lte(self, field, value):
        self.filters.append((field, value, "lte"))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            payload = self.payload[0] if isinstance(self.payload, list) else self.payload
            self.db.inserted[self.table_name] = payload
            return type("Result", (), {"data": [{"id": f"{self.table_name}-1", **payload}]})()
        rows = list(self.db.fixtures.get(self.table_name, []))
        for item in self.filters:
            field, value = item[0], item[1]
            op = item[2] if len(item) > 2 else "eq"
            if op == "gte":
                rows = [row for row in rows if str(row.get(field, "")) >= str(value)]
            elif op == "lte":
                rows = [row for row in rows if str(row.get(field, "")) <= str(value)]
            else:
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
    assert "zone" not in payload
    assert "device_type" not in payload
    assert "temperature" not in payload
    assert "status" not in payload
    assert payload["threshold_c"] == 4.0
    assert payload["humidity_rh"] == 55
    assert payload["notes"] == "normal check"
    assert payload["photo_url"].endswith("/temp.jpg")
    assert payload["storage_path"] == "staff/2026-05-16/temp.jpg"


def test_monitoring_structure_returns_default_room_unit_matrix(monkeypatch):
    from backend.monitoring import facility_manager

    monkeypatch.setattr(facility_manager, "get_client", lambda: None)
    monkeypatch.setattr(facility_manager, "direct_db_query", lambda *args, **kwargs: [])

    structure = facility_manager.get_monitoring_structure()

    assert len(structure) == 6
    assert [room["name"] for room in structure] == ["PPIC", "Grouper", "Pack Basah", "Pack Kering", "Ruang Kopi", "Kitchen"]
    assert all([device["name"] for device in room["devices"]] == ["Suhu Ruangan", "Chiller", "Freezer"] for room in structure)


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

    assert len(structure) == 6
    ppic = next(room for room in structure if room["name"] == "PPIC")
    kitchen = next(room for room in structure if room["name"] == "Kitchen")
    assert [device["name"] for device in ppic["devices"]] == ["Suhu Ruangan", "Chiller", "Freezer"]
    assert next(device for device in ppic["devices"] if device["type"] == "chiller")["last_temperature_c"] == 3.5
    assert next(device for device in kitchen["devices"] if device["type"] == "freezer")["last_temperature_c"] == -19


def test_monitoring_structure_merges_logs_when_master_devices_empty(monkeypatch):
    from backend.monitoring import facility_manager

    def fake_direct(table, method="GET", payload=None, filters=""):
        if table == "facility_rooms":
            return [{"id": "room-ppic", "name": "PPIC"}, {"id": "room-grouper", "name": "Grouper"}]
        if table == "facility_devices":
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
                }
            ]
        return []

    monkeypatch.setattr(facility_manager, "get_client", lambda: None)
    monkeypatch.setattr(facility_manager, "direct_db_query", fake_direct)

    structure = facility_manager.get_monitoring_structure()

    ppic = next(room for room in structure if room["name"] == "PPIC")
    grouper = next(room for room in structure if room["name"] == "Grouper")
    assert next(device for device in ppic["devices"] if device["type"] == "chiller")["last_temperature_c"] == 3.5
    assert [device["name"] for device in grouper["devices"]] == ["Suhu Ruangan", "Chiller", "Freezer"]


def test_monitoring_latest_falls_back_to_temperature_logs_when_facility_logs_empty():
    from backend.services.monitoring_service import MonitoringService

    class Query:
        def __init__(self, table):
            self.table = table

        def select(self, *args, **kwargs):
            return self

        def order(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def execute(self):
            rows = [] if self.table == "facility_logs" else [{"id": "temp-1", "zone": "Kitchen", "device_type": "freezer"}]
            return type("Result", (), {"data": rows})()

    class DB:
        def table(self, table):
            return Query(table)

    assert MonitoringService(DB()).latest_logs()[0]["zone"] == "Kitchen"


def test_delete_default_facility_device_is_not_locked_permanently(client, admin_headers):
    response = client.delete(
        "/api/facility/devices/default-room-ruang-kopi-chiller",
        headers=admin_headers,
    )

    body = response.get_json()
    assert response.status_code != 409
    assert "Default unit" not in body.get("detail", "")
