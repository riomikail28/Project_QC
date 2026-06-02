from unittest.mock import patch

import httpx

from backend.services.google_apps_script_service import build_qc_finding_payload, google_sheets_status, send_monitoring_log, send_qc_finding, send_qc_report
from tests.test_qc_check_cooking_final_flow import FlowDb
from tests.test_inspection_submit import InsertDb
from tests.test_monitoring import DEVICE_ID, ROOM_ID, RecordingSupabase
from tests.conftest import FakeSupabase


def test_google_apps_script_skips_when_env_empty(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", raising=False)

    with patch("backend.services.google_apps_script_service.httpx.post") as post:
        assert send_monitoring_log({"temperature": 4.0}) is False
        assert send_qc_report({"status": "pass"}) is False
        assert send_qc_finding({"temuan": "Area kotor"}) is False

    post.assert_not_called()
    assert google_sheets_status()["webhook_configured"] is False


def test_admin_google_sheets_test_endpoint_sends_payload(client, admin_headers, monkeypatch):
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")

    with patch("backend.services.google_apps_script_service.httpx.post") as post:
        post.return_value = httpx.Response(200, text="ok", request=httpx.Request("POST", "https://script.test"))
        response = client.post("/api/admin/google-sheets/test", headers=admin_headers, json={})

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    payload = post.call_args.kwargs["json"]
    assert payload["type"] == "test"
    assert payload["message"] == "QC Enterprise webhook test"
    assert payload["source"] == "admin"
    assert payload["timestamp"]


def test_google_sheets_status_records_webhook_failure(client, admin_headers, monkeypatch):
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")

    with patch("backend.services.google_apps_script_service.httpx.post") as post:
        post.return_value = httpx.Response(500, text="apps script exploded", request=httpx.Request("POST", "https://script.test"))
        response = client.post("/api/admin/google-sheets/test", headers=admin_headers, json={})

    assert response.status_code == 502
    status = client.get("/api/admin/google-sheets/status", headers=admin_headers).get_json()["data"]
    assert status["webhook_configured"] is True
    assert status["last_export_status"] == "error"
    assert status["last_http_status"] == 500
    assert status["last_response_text"] == "apps script exploded"
    assert status["last_exception_message"]
    assert "status_code=500" in status["last_export_error"]
    assert "apps script exploded" in status["last_export_error"]
    assert status["last_payload_type"] == "test"


def test_google_apps_script_follows_302_redirect_and_treats_final_success(monkeypatch):
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")
    first = httpx.Response(
        302,
        headers={"Location": "https://script.googleusercontent.com/macros/echo?user_content_key=abc"},
        request=httpx.Request("POST", "https://script.google.com/macros/s/test/exec"),
    )
    final = httpx.Response(
        200,
        json={"success": True},
        request=httpx.Request("POST", "https://script.googleusercontent.com/macros/echo?user_content_key=abc"),
    )

    with patch("backend.services.google_apps_script_service.httpx.post", return_value=first) as post, patch(
        "backend.services.google_apps_script_service.httpx.get", return_value=final
    ) as get:
        assert send_qc_report({"status": "pass"}) is True

    post.assert_called_once()
    assert post.call_args.args[0] == "https://script.google.com/macros/s/test/exec"
    assert post.call_args.kwargs["json"]["type"] == "qc_report"
    get.assert_called_once()
    assert get.call_args.args[0].startswith("https://script.googleusercontent.com/macros/echo")
    status = google_sheets_status()
    assert status["last_export_status"] == "success"
    assert status["final_status_code"] == 200
    assert '"success":true' in status["final_response_text"].replace(" ", "")


def test_google_apps_script_does_not_post_to_302_redirect_location(monkeypatch):
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")
    redirect = httpx.Response(
        302,
        headers={"Location": "https://script.googleusercontent.com/macros/echo?user_content_key=abc"},
        request=httpx.Request("POST", "https://script.google.com/macros/s/test/exec"),
    )
    success = httpx.Response(
        200,
        text="ok",
        request=httpx.Request("GET", "https://script.googleusercontent.com/macros/echo?user_content_key=abc"),
    )

    with patch("backend.services.google_apps_script_service.httpx.post", return_value=redirect) as post, patch(
        "backend.services.google_apps_script_service.httpx.get", return_value=success
    ) as get:
        assert send_monitoring_log({"temperature": 4.0}) is True

    post.assert_called_once()
    assert "script.googleusercontent.com" not in post.call_args.args[0]
    get.assert_called_once()
    assert "script.googleusercontent.com" in get.call_args.args[0]


def test_admin_google_sheets_test_rejects_invalid_webhook_url(client, admin_headers, monkeypatch):
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/test/dev")

    with patch("backend.services.google_apps_script_service.httpx.post") as post:
        response = client.post("/api/admin/google-sheets/test", headers=admin_headers, json={})

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert "berakhiran /exec" in body["message"]
    assert body["data"]["webhook_configured"] is True
    assert body["data"]["webhook_url_ends_with_exec"] is False
    assert body["data"]["webhook_valid"] is False
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
    status = google_sheets_status()
    assert status["last_export_status"] == "error"
    assert "webhook unavailable" in status["last_export_error"]


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
                "ph_value": "4.27",
                "brix_value": "10",
                "tds_value": "150",
                "photo_url": "https://example.test/photo.jpg",
                "staff_name": "Siti QC",
                "notes": "recheck needed",
            },
        )

    assert response.status_code == 200
    send.assert_called_once()
    payload = send.call_args.args[0]
    assert payload["batch_code"]
    assert payload["product_name"] == "Soup Base"
    assert payload["inspection_type"] == "Cek Masakan"
    assert payload["status"] == "HOLD"
    assert payload["temperature"] == "74.5"
    assert payload["ph"] == "4.27"
    assert payload["brix"] == "10"
    assert payload["tds"] == "150"
    assert payload["photo_url"] == "https://example.test/photo.jpg"
    assert payload["staff_name"] == "Siti QC"
    assert payload["timestamp"]
    assert payload["date"]
    assert payload["notes"] == "recheck needed"
    assert payload["inspection_round"] == 1
    assert payload["is_recheck"] is False
    assert payload["source_type"] == "qc_report"
    assert payload["source_id"] == "qc_reports-1"


def test_qc_google_apps_script_payload_marks_recheck_round(client, staff_headers):
    db = FlowDb()
    db.fixtures["production_batches"][0].update({"cook_name": "Andi", "quantity": 50})
    db.fixtures["qc_reports"] = [{
        "id": "parent-qc",
        "batch_id": "batch-1",
        "batch_code": "QC-20260517-001",
        "qc_stage": "cooking_check",
        "status": "hold",
        "inspection_round": 1,
        "created_at": "2026-05-17T03:00:00Z",
    }]

    with patch("backend.services.inspection_service.get_client", return_value=db), patch(
        "backend.services.inspection_service.send_qc_report"
    ) as send:
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "product_id": "product-1",
                "sku_code": "SKU-CK",
                "batch_id": "batch-1",
                "batch_code": "QC-20260517-001",
                "qc_stage": "cooking_check",
                "qc_status": "pass",
                "temperature": "82",
                "parent_inspection": "parent-qc",
                "staff_name": "Rio QC",
                "operational_date": "2026-05-17",
            },
        )

    assert response.status_code == 200
    payload = send.call_args.args[0]
    assert payload["inspection_round"] == 2
    assert payload["is_recheck"] is True
    assert payload["status"] == "PASS"
    assert payload["batch_sequence"] == 1
    assert payload["cook_name"] == "Andi"
    assert payload["quantity"] == 50


def test_google_apps_script_webhook_payloads_are_flat_with_type(monkeypatch):
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")

    with patch("backend.services.google_apps_script_service.httpx.post") as post:
        post.return_value = httpx.Response(200, text="ok", request=httpx.Request("POST", "https://script.test"))
        assert send_monitoring_log({
            "date": "2026-05-27",
            "slot_time": "07:00",
            "room": "Chiller",
            "device": "Unit 1",
            "temperature": 3.2,
            "status": "PASS",
            "staff_name": "Siti",
            "submitted_at": "2026-05-27T00:05:00Z",
            "notes": "normal",
        }) is True
        assert send_qc_report({
            "batch_id": "batch-1",
            "batch_code": "SAL-20260527-001",
            "product_name": "Salad",
            "qc_stage": "cooking_check",
            "status": "pass",
            "temperature": 82,
            "staff_name": "Budi",
            "created_at": "2026-05-27T00:05:00Z",
            "notes": "ok",
        }) is True

    monitoring_payload = post.call_args_list[0].kwargs["json"]
    qc_payload = post.call_args_list[1].kwargs["json"]
    assert monitoring_payload["type"] == "monitoring_log"
    assert monitoring_payload["date"] == "2026-05-27"
    assert "payload" not in monitoring_payload
    assert qc_payload["type"] == "qc_report"
    assert qc_payload["batch_code"] == "SAL-20260527-001"
    assert "payload" not in qc_payload


def test_admin_export_monitoring_without_date_exports_all(client, admin_headers):
    db = FakeSupabase({
        "facility_logs": [
            {"id": "log-1", "zone": "Chiller", "device_id": "dev-1", "temperature_c": 3.2, "is_normal": True, "staff_name": "Siti", "recorded_at": "2026-05-01T07:05:00Z"},
            {"id": "log-2", "zone": "Freezer", "device_id": "dev-2", "temperature_c": -18, "is_normal": True, "staff_name": "Budi", "recorded_at": "2026-05-02T07:05:00Z"},
        ]
    })
    with patch("backend.services.admin_service.get_client", return_value=db), patch(
        "backend.services.admin_service.send_monitoring_log", return_value=True
    ) as send:
        response = client.post("/api/admin/google-sheets/export/monitoring", headers=admin_headers, json={})

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["exported"] == 2
    assert body["failed"] == 0
    assert send.call_count == 2
    payload = send.call_args_list[0].args[0]
    assert payload["source_type"] == "monitoring_log"
    assert payload["source_id"] == "log-1"


def test_admin_export_monitoring_with_date_range_filters_rows(client, admin_headers):
    db = FakeSupabase({
        "facility_logs": [
            {"id": "log-old", "temperature_c": 3.2, "is_normal": True, "recorded_at": "2026-04-30T07:05:00Z"},
            {"id": "log-in", "temperature_c": 3.4, "is_normal": True, "recorded_at": "2026-05-10T07:05:00Z"},
        ]
    })
    with patch("backend.services.admin_service.get_client", return_value=db), patch(
        "backend.services.admin_service.send_monitoring_log", return_value=True
    ) as send:
        response = client.post(
            "/api/admin/google-sheets/export/monitoring",
            headers=admin_headers,
            json={"start_date": "2026-05-01", "end_date": "2026-05-28"},
        )

    body = response.get_json()
    assert response.status_code == 200
    assert body["exported"] == 1
    send.assert_called_once()
    assert send.call_args.args[0]["source_id"] == "log-in"


def test_admin_export_qc_without_date_exports_reports(client, admin_headers):
    db = FakeSupabase({
        "qc_reports": [{
            "id": "qc-1",
            "batch_id": "batch-1",
            "batch_code": "SAL-20260501-001",
            "product_name": "Salad",
            "qc_stage": "cooking_check",
            "status": "pass",
            "temperature": 75,
            "ph_value": 4.2,
            "brix_value": 10,
            "tds_value": 150,
            "photo_url": "https://example.test/qc.jpg",
            "notes": "ok",
            "inspection_round": 2,
            "parent_inspection": "qc-0",
            "staff_name": "Rio",
            "created_at": "2026-05-01T08:00:00Z",
        }],
        "production_batches": [{
            "id": "batch-1",
            "batch_code": "SAL-20260501-001",
            "batch_sequence": 3,
            "cook_name": "Andi",
            "quantity": 50,
            "product_name": "Salad",
            "created_at": "2026-05-01T07:00:00Z",
        }],
        "qc_findings": [],
    })
    with patch("backend.services.admin_service.get_client", return_value=db), patch(
        "backend.services.admin_service.send_qc_report", return_value=True
    ) as send:
        response = client.post("/api/admin/google-sheets/export/qc", headers=admin_headers, json={})

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["exported"] == 1
    send.assert_called_once()
    payload = send.call_args.args[0]
    assert payload["source_type"] == "qc_report"
    assert payload["source_id"] == "qc-1"
    assert payload["batch_code"] == "SAL-20260501-001"
    assert payload["batch_sequence"] == 3
    assert payload["cook_name"] == "Andi"
    assert payload["quantity"] == 50
    assert payload["inspection_type"] == "Cek Masakan"
    assert payload["temperature"] == 75
    assert payload["ph"] == 4.2
    assert payload["brix"] == 10
    assert payload["tds"] == 150
    assert payload["status"] == "PASS"
    assert payload["photo_url"] == "https://example.test/qc.jpg"
    assert payload["notes"] == "ok"
    assert payload["inspection_round"] == 2
    assert payload["is_recheck"] is True


def test_qc_finding_payload_targets_qc_temuan_sheet():
    payload = build_qc_finding_payload({
        "id": "finding-1",
        "staff_display_name": "Rio Mikail",
        "area": "Packing",
        "reason": "Label salah",
        "photo_url": "https://example.test/finding.jpg",
        "status": "warning",
        "finding_date": "2026-05-01",
        "created_at": "2026-05-01T09:00:00Z",
    })

    assert payload == {
        "timestamp": "2026-05-01T09:00:00Z",
        "staff": "Rio Mikail",
        "area": "Packing",
        "temuan": "Label salah",
        "photo_url": "https://example.test/finding.jpg",
        "status": "WARNING",
        "tanggal": "2026-05-01",
        "source_type": "qc_finding",
        "source_id": "finding-1",
    }


def test_admin_export_qc_findings_routes_to_qc_temuan_payload(client, admin_headers):
    db = FakeSupabase({
        "qc_reports": [],
        "production_batches": [],
        "qc_findings": [{
            "id": "finding-1",
            "staff_name": "Rio",
            "area": "Kitchen",
            "reason": "Area kotor",
            "photo_url": "https://example.test/finding.jpg",
            "status": "warning",
            "created_at": "2026-05-01T08:30:00Z",
        }],
    })
    with patch("backend.services.admin_service.get_client", return_value=db), patch(
        "backend.services.admin_service.send_qc_report", return_value=True
    ) as send_report, patch(
        "backend.services.admin_service.send_qc_finding", return_value=True
    ) as send_finding:
        response = client.post("/api/admin/google-sheets/export/qc", headers=admin_headers, json={})

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["exported"] == 1
    send_report.assert_not_called()
    send_finding.assert_called_once()
    payload = send_finding.call_args.args[0]
    assert payload["source_type"] == "qc_finding"
    assert payload["source_id"] == "finding-1"
    assert payload["staff"] == "Rio"
    assert payload["area"] == "Kitchen"
    assert payload["temuan"] == "Area kotor"
    assert payload["photo_url"] == "https://example.test/finding.jpg"
    assert payload["status"] == "WARNING"
    assert payload["tanggal"] == "2026-05-01"


def test_admin_export_monitoring_reports_partial_failure(client, admin_headers):
    db = FakeSupabase({
        "facility_logs": [
            {"id": "log-1", "temperature_c": 3.2, "is_normal": True, "recorded_at": "2026-05-01T07:05:00Z"},
            {"id": "log-2", "temperature_c": 3.4, "is_normal": True, "recorded_at": "2026-05-01T08:05:00Z"},
        ]
    })
    with patch("backend.services.admin_service.get_client", return_value=db), patch(
        "backend.services.admin_service.send_monitoring_log", side_effect=[True, False]
    ):
        response = client.post("/api/admin/google-sheets/export/monitoring", headers=admin_headers, json={})

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is False
    assert body["status"] == "partial"
    assert body["exported"] == 1
    assert body["failed"] == 1
    assert body["errors"][0]["source_id"] == "log-2"


def test_staff_cannot_access_google_sheets_reexport(client, staff_headers):
    response = client.post("/api/admin/google-sheets/export/monitoring", headers=staff_headers, json={})

    assert response.status_code == 403
