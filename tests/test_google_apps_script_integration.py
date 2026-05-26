from unittest.mock import patch

import httpx

from backend.services.google_apps_script_service import send_monitoring_log, send_qc_report
from tests.test_inspection_submit import InsertDb
from tests.test_monitoring import DEVICE_ID, ROOM_ID, RecordingSupabase


def test_google_apps_script_skips_when_env_empty(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", raising=False)

    with patch("backend.services.google_apps_script_service.httpx.post") as post:
        assert send_monitoring_log({"temperature": 4.0}) is False
        assert send_qc_report({"status": "pass"}) is False

    post.assert_not_called()


def test_monitoring_submit_still_succeeds_when_google_apps_script_fails(client, staff_headers, monkeypatch):
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")
    db = RecordingSupabase()

    with patch("backend.api.temperature_routes.get_client", return_value=db), patch(
        "backend.api.temperature_routes.write_audit"
    ), patch(
        "backend.services.google_apps_script_service.httpx.post",
        side_effect=httpx.ConnectError("webhook unavailable"),
    ):
        response = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            data={
                "room_id": ROOM_ID,
                "device_id": DEVICE_ID,
                "temperature": "3.2",
                "notes": "normal check",
            },
        )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert db.inserted["facility_logs"]["temperature_c"] == 3.2


def test_inspection_submit_still_succeeds_when_google_apps_script_fails(client, staff_headers, monkeypatch):
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")
    db = InsertDb()

    with patch("backend.services.inspection_service.get_client", return_value=db), patch(
        "backend.services.google_apps_script_service.httpx.post",
        side_effect=httpx.ReadTimeout("timeout"),
    ):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "barcode": "MANUAL-001",
                "qc_stage": "final_check",
                "qc_status": "pass",
                "notes": "label ok",
            },
        )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert db.inserted["qc_reports"][0]["barcode"] == "MANUAL-001"


def test_monitoring_google_apps_script_payload_is_correct(client, staff_headers):
    db = RecordingSupabase()

    with patch("backend.api.temperature_routes.get_client", return_value=db), patch(
        "backend.api.temperature_routes.write_audit"
    ), patch("backend.services.monitoring_service.send_monitoring_log") as send:
        response = client.post(
            "/api/monitoring/log",
            headers=staff_headers,
            data={
                "room_id": ROOM_ID,
                "device_id": DEVICE_ID,
                "temperature": "3.2",
                "monitoring_date": "2026-05-27",
                "slot_time": "07:00",
                "submitted_at": "2026-05-27T00:05:00Z",
                "notes": "normal check",
            },
        )

    assert response.status_code == 200
    send.assert_called_once()
    payload = send.call_args.args[0]
    assert payload == {
        "date": "2026-05-27",
        "slot_time": "07:00",
        "room": "Chiller Room",
        "device": DEVICE_ID,
        "temperature": 3.2,
        "status": "PASS",
        "staff_name": "staff-1",
        "submitted_at": "2026-05-27T00:05:00Z",
        "notes": "normal check",
    }


def test_qc_google_apps_script_payload_is_correct(client, staff_headers):
    db = InsertDb()

    with patch("backend.services.inspection_service.get_client", return_value=db), patch(
        "backend.services.inspection_service.send_qc_report"
    ) as send:
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "barcode": "MANUAL-002",
                "product_name": "Soup Base",
                "qc_stage": "cooking_check",
                "qc_status": "hold",
                "temperature": "74.5",
                "photo_url": "https://example.test/photo.jpg",
                "staff_name": "Siti QC",
                "notes": "recheck needed",
            },
        )

    assert response.status_code == 200
    send.assert_called_once()
    payload = send.call_args.args[0]
    assert payload["batch_id"]
    assert payload["product_name"] == "Soup Base"
    assert payload["status"] == "hold"
    assert payload["temperature"] == "74.5"
    assert payload["photo_url"] == "https://example.test/photo.jpg"
    assert payload["staff_name"] == "Siti QC"
    assert payload["created_at"]
    assert payload["notes"] == "recheck needed"
