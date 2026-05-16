from types import SimpleNamespace
from unittest.mock import patch


class FacilityQuery:
    def __init__(self, table, db):
        self.table = table
        self.db = db
        self.payload = None
        self.mode = None
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.mode = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.mode = "update"
        self.payload = payload
        return self

    def delete(self):
        self.mode = "delete"
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def execute(self):
        rows = self.db.rows.setdefault(self.table, [])
        if self.mode == "insert":
            row = {"id": f"{self.table}-{len(rows) + 1}", **self.payload}
            rows.append(row)
            return SimpleNamespace(data=[row])
        if self.mode == "update":
            for row in rows:
                if all(row.get(field) == value for field, value in self.filters):
                    row.update(self.payload)
                    return SimpleNamespace(data=[row])
            return SimpleNamespace(data=[])
        if self.mode == "delete":
            before = len(rows)
            self.db.rows[self.table] = [
                row for row in rows
                if not all(row.get(field) == value for field, value in self.filters)
            ]
            return SimpleNamespace(data=[{"deleted": before - len(self.db.rows[self.table])}])
        result = list(rows)
        for field, value in self.filters:
            result = [row for row in result if row.get(field) == value]
        return SimpleNamespace(data=result)


class FacilityDb:
    def __init__(self):
        self.rows = {
            "facility_rooms": [{"id": "room-1", "name": "PPIC", "slug": "ppic"}],
            "facility_devices": [{"id": "device-1", "room_id": "room-1", "name": "Chiller", "device_type": "chiller"}],
        }

    def table(self, table):
        return FacilityQuery(table, self)


def test_admin_get_facility_rooms(client, admin_headers):
    db = FacilityDb()
    with patch("backend.monitoring.facility_manager.get_client", return_value=db):
        response = client.get("/api/admin/facility/rooms", headers=admin_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][0]["name"] == "PPIC"


def test_admin_room_crud(client, admin_headers):
    db = FacilityDb()
    with patch("backend.monitoring.facility_manager.get_client", return_value=db):
        created = client.post("/api/admin/facility/rooms", headers=admin_headers, json={"name": "QA Lab"}).get_json()["data"]
        updated = client.put(
            f"/api/admin/facility/rooms/{created['id']}",
            headers=admin_headers,
            json={"name": "QA Lab 2", "is_active": False},
        ).get_json()["data"]
        deleted = client.delete(f"/api/admin/facility/rooms/{created['id']}", headers=admin_headers)

    assert updated["name"] == "QA Lab 2"
    assert deleted.status_code == 200


def test_admin_device_crud_allows_default_device_delete(client, admin_headers):
    db = FacilityDb()
    with patch("backend.monitoring.facility_manager.get_client", return_value=db):
        created = client.post(
            "/api/admin/facility/devices",
            headers=admin_headers,
            json={"room_id": "room-1", "name": "Freezer", "device_type": "freezer", "target_temperature": -18},
        ).get_json()["data"]
        updated = client.put(
            f"/api/admin/facility/devices/{created['id']}",
            headers=admin_headers,
            json={"name": "Freezer 2", "device_type": "freezer", "target_temperature": -20},
        ).get_json()["data"]
        deleted = client.delete("/api/admin/facility/devices/default-room-ppic-freezer", headers=admin_headers)

    assert updated["target_temperature"] == -20
    assert deleted.status_code in (200, 503)
    assert deleted.status_code != 409
