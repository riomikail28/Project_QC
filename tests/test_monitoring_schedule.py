from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from backend.services.monitoring_schedule_service import MonitoringScheduleService
from tests.test_monitoring import DEVICE_ID, ROOM_ID


JAKARTA = ZoneInfo("Asia/Jakarta")


def test_new_day_creates_four_monitoring_slots():
    service = MonitoringScheduleService(ScheduleDb(), now=datetime(2026, 5, 24, 6, 30, tzinfo=JAKARTA))

    result = service.today()

    assert result["success"] is True
    assert [slot["time"] for slot in result["data"]["slots"]] == ["07:00", "13:00", "16:00", "19:00"]
    assert result["data"]["completed_count"] == 0
    assert result["data"]["total_slots"] == 4
    assert result["data"]["slots"][0]["status"] == "upcoming"


def test_submit_slot_0700_succeeds_and_progress_becomes_one_of_four(client, staff_headers):
    db = ScheduleDb()

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.services.monitoring_service.upload_file_storage"
    ), patch("backend.api.facility_routes.write_audit"):
        response = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={
                "room_id": ROOM_ID,
                "device_id": DEVICE_ID,
                "temperature": "4.2",
                "slot_time": "07:00",
            },
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert db.inserted["facility_logs"]["monitoring_date"]
    assert str(db.inserted["facility_logs"]["slot_time"]).startswith("07:00")
    assert db.inserted["facility_logs"]["schedule_status"] in {"completed", "late"}
    assert body["schedule"]["completed_count"] == 1
    assert body["schedule"]["total_slots"] == 4


def test_four_completed_slots_show_finished_message():
    date = "2026-05-24"
    db = ScheduleDb()
    db.rows["facility_logs"] = [
        {"monitoring_date": date, "slot_time": slot, "schedule_status": "completed", "temperature_c": 4.0}
        for slot in ["07:00", "13:00", "16:00", "19:00"]
    ]
    service = MonitoringScheduleService(db, now=datetime(2026, 5, 24, 20, 0, tzinfo=JAKARTA))

    result = service.today()["data"]

    assert result["completed_count"] == 4
    assert result["message"] == "Monitoring hari ini selesai. Tugas berikutnya besok pukul 07:00."


def test_next_day_resets_monitoring_schedule():
    db = ScheduleDb()
    db.rows["facility_logs"] = [
        {"monitoring_date": "2026-05-24", "slot_time": slot, "schedule_status": "completed"}
        for slot in ["07:00", "13:00", "16:00", "19:00"]
    ]
    service = MonitoringScheduleService(db, now=datetime(2026, 5, 25, 7, 30, tzinfo=JAKARTA))

    result = service.today()["data"]

    assert result["date"] == "2026-05-25"
    assert result["completed_count"] == 0
    assert result["slots"][0]["status"] == "pending"


class ScheduleQuery:
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
            self.db.rows.setdefault(self.table_name, []).append({"id": f"{self.table_name}-1", **payload})
            return type("Result", (), {"data": [{"id": f"{self.table_name}-1", **payload}]})()
        rows = list(self.db.rows.get(self.table_name, []))
        for field, value in self.filters:
            rows = [row for row in rows if str(row.get(field)) == str(value)]
        return type("Result", (), {"data": rows})()


class ScheduleDb:
    def __init__(self):
        self.rows = {
            "facility_rooms": [{"id": ROOM_ID, "name": "Chiller Room"}],
            "facility_devices": [{"id": DEVICE_ID, "room_id": ROOM_ID, "type": "chiller", "threshold_temp": 5}],
            "facility_logs": [],
            "temperature_logs": [],
        }
        self.inserted = {}

    def table(self, table_name):
        return ScheduleQuery(table_name, self)
