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
    frozen_now = datetime(2026, 5, 27, 7, 15, tzinfo=JAKARTA)

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.services.monitoring_service.upload_file_storage"
    ), patch("backend.api.facility_routes.write_audit"), patch(
        "backend.api.facility_routes.MonitoringScheduleService",
        side_effect=lambda sb: MonitoringScheduleService(sb, now=frozen_now),
    ):
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
    assert db.inserted["facility_logs"]["monitoring_date"] == "2026-05-27"
    assert str(db.inserted["facility_logs"]["slot_time"]).startswith("07:00")
    assert db.inserted["facility_logs"]["schedule_status"] == "late"
    assert body["schedule"]["completed_count"] == 1
    assert body["schedule"]["total_slots"] == 4
    assert body["schedule"]["total_required"] == 4


def test_submit_slot_0700_before_0700_returns_409(client, staff_headers):
    db = ScheduleDb()
    frozen_now = datetime(2026, 5, 27, 6, 45, tzinfo=JAKARTA)

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.api.facility_routes.MonitoringScheduleService",
        side_effect=lambda sb: MonitoringScheduleService(sb, now=frozen_now),
    ):
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

    body = response.get_json()
    assert response.status_code == 409
    assert body["success"] is False
    assert body["message"] == "Slot 07:00 belum waktunya."
    assert "facility_logs" not in db.inserted


def test_submit_slot_0700_after_0700_succeeds(client, staff_headers):
    db = ScheduleDb()
    frozen_now = datetime(2026, 5, 27, 7, 15, tzinfo=JAKARTA)

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.services.monitoring_service.upload_file_storage"
    ), patch("backend.api.facility_routes.write_audit"), patch(
        "backend.api.facility_routes.MonitoringScheduleService",
        side_effect=lambda sb: MonitoringScheduleService(sb, now=frozen_now),
    ):
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

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert db.inserted["facility_logs"]["monitoring_date"] == "2026-05-27"
    assert db.inserted["facility_logs"]["slot_time"] == "07:00"


def test_one_of_sixteen_devices_keeps_0700_active_and_progress_one_of_sixty_four(client, staff_headers):
    db = ScheduleDb(device_count=16)
    frozen_now = datetime(2026, 5, 27, 7, 15, tzinfo=JAKARTA)

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.services.monitoring_service.upload_file_storage"
    ), patch("backend.api.facility_routes.write_audit"), patch(
        "backend.api.facility_routes.MonitoringScheduleService",
        side_effect=lambda sb: MonitoringScheduleService(sb, now=frozen_now),
    ):
        first = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[0], "temperature": "4.2", "slot_time": "07:00"},
        )
        second = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[1], "temperature": "4.1", "slot_time": "07:00"},
        )

    body = first.get_json()
    assert first.status_code == 200
    assert body["schedule"]["total_devices"] == 16
    assert body["schedule"]["total_required"] == 64
    assert body["schedule"]["total_completed"] == 1
    assert body["schedule"]["progress_text"] == "1/64 monitoring selesai hari ini."
    assert body["schedule"]["current_slot"]["time"] == "07:00"
    assert body["schedule"]["slots"][0]["completed_count"] == 1
    assert body["schedule"]["slots"][0]["total_devices"] == 16
    assert second.status_code == 200


def test_same_device_cannot_submit_same_slot_twice(client, staff_headers):
    db = ScheduleDb(device_count=16)
    frozen_now = datetime(2026, 5, 27, 7, 15, tzinfo=JAKARTA)

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.services.monitoring_service.upload_file_storage"
    ), patch("backend.api.facility_routes.write_audit"), patch(
        "backend.api.facility_routes.MonitoringScheduleService",
        side_effect=lambda sb: MonitoringScheduleService(sb, now=frozen_now),
    ):
        first = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[0], "temperature": "4.2", "slot_time": "07:00"},
        )
        duplicate = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[0], "temperature": "4.3", "slot_time": "07:00"},
        )

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.get_json()["message"] == "Unit ini sudah diinput untuk slot 07:00."


def test_three_devices_can_submit_active_0700_then_duplicate_and_future_slot_reject(client, staff_headers):
    db = ScheduleDb(device_count=3)
    frozen_now = datetime(2026, 5, 27, 7, 15, tzinfo=JAKARTA)

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.services.monitoring_service.upload_file_storage"
    ), patch("backend.api.facility_routes.write_audit"), patch(
        "backend.api.facility_routes.MonitoringScheduleService",
        side_effect=lambda sb: MonitoringScheduleService(sb, now=frozen_now),
    ):
        first = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[0], "temperature": "4.2", "slot_time": "07:00"},
        )
        second = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[1], "temperature": "4.1", "slot_time": "07:00"},
        )
        third = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[2], "temperature": "4.0", "slot_time": "07:00"},
        )
        duplicate = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[0], "temperature": "4.3", "slot_time": "07:00"},
        )
        future = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[0], "temperature": "4.3", "slot_time": "13:00"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert third.get_json()["schedule"]["total_completed"] == 3
    assert third.get_json()["schedule"]["slots"][0]["completed"] is True
    assert duplicate.status_code == 409
    assert duplicate.get_json()["message"] == "Unit ini sudah diinput untuk slot 07:00."
    assert future.status_code == 409
    assert future.get_json()["message"] == "Slot 13:00 belum waktunya."


def test_after_all_devices_submit_0700_active_slot_moves_to_1300():
    db = ScheduleDb(device_count=16)
    db.rows["facility_logs"] = [
        {
            "id": f"log-{index}",
            "monitoring_date": "2026-05-27",
            "slot_time": "07:00",
            "device_id": device_id,
            "room_id": ROOM_ID,
            "schedule_status": "completed",
        }
        for index, device_id in enumerate(db.device_ids, start=1)
    ]
    service = MonitoringScheduleService(db, now=datetime(2026, 5, 27, 13, 15, tzinfo=JAKARTA))

    result = service.today()["data"]

    assert result["slots"][0]["completed"] is True
    assert result["slots"][0]["completed_count"] == 16
    assert result["current_slot"]["time"] == "13:00"
    assert result["total_completed"] == 16


def test_submit_1300_before_1300_returns_409_after_0700_complete(client, staff_headers):
    db = ScheduleDb(device_count=16)
    db.rows["facility_logs"] = [
        {
            "id": f"log-{index}",
            "monitoring_date": "2026-05-27",
            "slot_time": "07:00",
            "device_id": device_id,
            "room_id": ROOM_ID,
            "schedule_status": "completed",
        }
        for index, device_id in enumerate(db.device_ids, start=1)
    ]
    frozen_now = datetime(2026, 5, 27, 12, 30, tzinfo=JAKARTA)

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.api.facility_routes.MonitoringScheduleService",
        side_effect=lambda sb: MonitoringScheduleService(sb, now=frozen_now),
    ):
        response = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[0], "temperature": "4.2", "slot_time": "13:00"},
        )

    assert response.status_code == 409
    assert response.get_json()["message"] == "Slot 13:00 belum waktunya."


def test_submit_1300_after_1300_succeeds_after_0700_complete(client, staff_headers):
    db = ScheduleDb(device_count=16)
    db.rows["facility_logs"] = [
        {
            "id": f"log-{index}",
            "monitoring_date": "2026-05-27",
            "slot_time": "07:00",
            "device_id": device_id,
            "room_id": ROOM_ID,
            "schedule_status": "completed",
        }
        for index, device_id in enumerate(db.device_ids, start=1)
    ]
    frozen_now = datetime(2026, 5, 27, 13, 15, tzinfo=JAKARTA)

    with patch("backend.api.facility_routes.get_client", return_value=db), patch(
        "backend.services.monitoring_service.upload_file_storage"
    ), patch("backend.api.facility_routes.write_audit"), patch(
        "backend.api.facility_routes.MonitoringScheduleService",
        side_effect=lambda sb: MonitoringScheduleService(sb, now=frozen_now),
    ):
        response = client.post(
            "/api/facility/monitoring/submit",
            headers=staff_headers,
            data={"room_id": ROOM_ID, "device_id": db.device_ids[0], "temperature": "4.2", "slot_time": "13:00"},
        )

    assert response.status_code == 200
    assert db.inserted["facility_logs"]["slot_time"] == "13:00"


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
    def __init__(self, device_count=1):
        self.device_ids = [DEVICE_ID] + [
            f"22222222-2222-4222-8222-{index:012d}"
            for index in range(2, device_count + 1)
        ]
        self.rows = {
            "facility_rooms": [{"id": ROOM_ID, "name": "Chiller Room"}],
            "facility_devices": [
                {"id": device_id, "room_id": ROOM_ID, "type": "chiller", "device_type": "chiller", "threshold_temp": 5, "is_active": True}
                for device_id in self.device_ids
            ],
            "facility_logs": [],
            "temperature_logs": [],
        }
        self.inserted = {}

    def table(self, table_name):
        return ScheduleQuery(table_name, self)
