from unittest.mock import patch

from tests.test_batch_create import BatchDb
from tests.conftest import FakeSupabase


def _db_with_standards():
    db = BatchDb()
    db.rows["products"] = [{
        "id": "11111111-1111-4111-8111-111111111111",
        "product_code": "SKU-1",
        "product_name": "Soup",
        "ph_min": 4.5,
        "ph_max": 7,
        "brix_min": 11,
        "brix_max": 14,
        "tds_min": 100,
        "tds_max": 150,
    }]
    return db


def _create(client, staff_headers, payload):
    db = _db_with_standards()
    with patch("backend.services.batch_service.get_client", return_value=db), patch("backend.api.batch_routes.write_audit"):
        response = client.post("/api/batch/create", headers=staff_headers, json={
            "product_id": "SKU-1",
            "production_date": "2026-05-17",
            **payload,
        })
    return response, db


def test_create_batch_without_optional_parameters_succeeds(client, staff_headers):
    response, db = _create(client, staff_headers, {})

    assert response.status_code == 201
    assert db.inserted["ph_status"] == "not_checked"
    assert db.inserted["brix_status"] == "not_checked"
    assert db.inserted["tds_status"] == "not_checked"
    assert "ph_value" not in db.inserted


def test_create_batch_with_ph_succeeds(client, staff_headers):
    response, db = _create(client, staff_headers, {"ph_value": 5.2})

    assert response.status_code == 201
    assert db.inserted["ph_value"] == 5.2


def test_create_batch_with_brix_succeeds(client, staff_headers):
    response, db = _create(client, staff_headers, {"brix_value": 12})

    assert response.status_code == 201
    assert db.inserted["brix_value"] == 12


def test_create_batch_with_tds_succeeds(client, staff_headers):
    response, db = _create(client, staff_headers, {"tds_value": 120})

    assert response.status_code == 201
    assert db.inserted["tds_value"] == 120


def test_ph_in_range_is_pass(client, staff_headers):
    _, db = _create(client, staff_headers, {"ph_value": 5})
    assert db.inserted["ph_status"] == "pass"


def test_ph_out_of_range_is_warning(client, staff_headers):
    _, db = _create(client, staff_headers, {"ph_value": 9})
    assert db.inserted["ph_status"] == "warning"


def test_brix_in_range_is_pass(client, staff_headers):
    _, db = _create(client, staff_headers, {"brix_value": 12})
    assert db.inserted["brix_status"] == "pass"


def test_brix_out_of_range_is_warning(client, staff_headers):
    _, db = _create(client, staff_headers, {"brix_value": 20})
    assert db.inserted["brix_status"] == "warning"


def test_tds_in_range_is_pass(client, staff_headers):
    _, db = _create(client, staff_headers, {"tds_value": 120})
    assert db.inserted["tds_status"] == "pass"


def test_tds_out_of_range_is_warning(client, staff_headers):
    _, db = _create(client, staff_headers, {"tds_value": 300})
    assert db.inserted["tds_status"] == "warning"


def test_admin_batch_report_displays_ph_brix_tds(client, admin_headers):
    db = FakeSupabase({"production_batches": [{
        "id": "batch-1",
        "batch_code": "QC-20260517-001",
        "product_name": "Soup",
        "ph_value": 5.1,
        "ph_status": "pass",
        "brix_value": 12,
        "brix_status": "pass",
        "tds_value": 170,
        "tds_status": "warning",
        "parameter_notes": "Brix OK",
        "parameter_checked_by": "staff-1",
        "parameter_checked_at": "2026-05-17T01:00:00Z",
        "created_at": "2026-05-17T01:00:00Z",
    }]})

    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/v1/admin/reports/batches", headers=admin_headers)

    row = response.get_json()["data"][0]
    assert response.status_code == 200
    assert row["ph_value"] == 5.1
    assert row["brix_value"] == 12
    assert row["tds_status"] == "warning"
    assert row["parameter_notes"] == "Brix OK"


def test_admin_batch_report_empty_parameters_are_not_checked_not_zero(client, admin_headers):
    db = FakeSupabase({"production_batches": [{
        "id": "batch-1",
        "batch_code": "QC-20260517-002",
        "product_name": "Soup",
        "created_at": "2026-05-17T01:00:00Z",
    }]})

    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/v1/admin/reports/batches", headers=admin_headers)

    row = response.get_json()["data"][0]
    assert row["ph_value"] is None
    assert row["brix_value"] is None
    assert row["tds_value"] is None
    assert row["ph_status"] == "not_checked"
    assert row["brix_status"] == "not_checked"
    assert row["tds_status"] == "not_checked"
