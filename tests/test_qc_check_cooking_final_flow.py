from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch


class FlowQuery:
    def __init__(self, table, db):
        self.table = table
        self.db = db
        self.payload = None
        self.update_payload = None
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self.filters.append(("eq", field, value))
        return self

    def gte(self, field, value):
        self.filters.append(("gte", field, value))
        return self

    def lte(self, field, value):
        self.filters.append(("lte", field, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            payload = self.payload[0] if isinstance(self.payload, list) else self.payload
            row = {"id": f"{self.table}-{len(self.db.inserted.get(self.table, [])) + 1}", **payload}
            self.db.inserted.setdefault(self.table, []).append(row)
            self.db.fixtures.setdefault(self.table, []).append(row)
            return SimpleNamespace(data=[row])
        rows = list(self.db.fixtures.get(self.table, []))
        for op, field, value in self.filters:
            if op == "gte":
                rows = [row for row in rows if str(row.get(field, "")) >= str(value)]
            elif op == "lte":
                rows = [row for row in rows if str(row.get(field, "")) <= str(value)]
            else:
                rows = [row for row in rows if row.get(field) == value]
        if self.update_payload is not None:
            for row in rows:
                row.update(self.update_payload)
            self.db.updated.setdefault(self.table, []).append({"filters": self.filters, "payload": self.update_payload})
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=rows)


class FlowDb:
    def __init__(self):
        self.fixtures = {
            "products": [{"id": "product-1", "product_code": "SKU-CK", "product_name": "Chicken Katsu", "is_active": True}],
            "production_batches": [{
                "id": "batch-1",
                "batch_code": "QC-20260517-001",
                "product_id": "product-1",
                "product_name": "Chicken Katsu",
                "production_date": "2026-05-17",
                "batch_sequence": 1,
                "status": "in_progress",
                "created_at": "2026-05-17T03:00:00Z",
            }],
            "qc_reports": [],
        }
        self.inserted = {}
        self.updated = {}

    def table(self, table):
        return FlowQuery(table, self)


def _upload(name):
    return SimpleNamespace(
        url=f"https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/staff-1/inspection/{name}",
        storage_path=f"staff/staff-1/inspection/{name}",
        file_name=name,
        file_type="image/jpeg",
        file_size=16,
        bucket="qc-evidence",
    )


def test_submit_cooking_check_with_sku_temperature_status_succeeds(client, staff_headers):
    db = FlowDb()
    with patch("backend.services.inspection_service.get_client", return_value=db), patch("backend.services.inspection_service.write_audit") as audit:
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"sku_code": "SKU-CK", "qc_stage": "cooking_check", "temperature": "82", "qc_status": "pass", "staff_id": "staff-a", "operational_date": "2026-05-17"},
        )

    body = response.get_json()
    report = db.inserted["qc_reports"][0]
    assert response.status_code == 200
    assert body["message"] == "QC check submitted"
    assert report["qc_stage"] == "cooking_check"
    assert report["ccp_stage"] == "cooking_check"
    assert report["temperature"] == "82"
    assert db.inserted["approvals"][0]["status"] == "pending"
    audit.assert_any_call("submit_inspection", "qc_report", "qc_reports-1", after=db.inserted["qc_reports"][0])


def test_submit_cooking_check_without_temperature_returns_400(client, staff_headers):
    db = FlowDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"sku_code": "SKU-CK", "qc_stage": "cooking_check", "qc_status": "pass"},
        )

    assert response.status_code == 400
    assert response.get_json()["message"] == "Temperature is required for Cooking Check"


def test_submit_final_check_without_temperature_succeeds(client, staff_headers):
    db = FlowDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"sku_code": "SKU-CK", "batch_id": "batch-1", "batch_code": "QC-20260517-001", "qc_stage": "final_check", "qc_status": "pass", "operational_date": "2026-05-17"},
        )

    report = db.inserted["qc_reports"][0]
    assert response.status_code == 200
    assert report["qc_stage"] == "final_check"
    assert "temperature" not in report


def test_submit_final_check_with_barcode_and_label_photos_succeeds(client, staff_headers):
    db = FlowDb()
    uploads = [_upload("barcode.jpg"), _upload("label.jpg")]
    with patch("backend.services.inspection_service.get_client", return_value=db), patch(
        "backend.services.inspection_service.upload_file_storage", side_effect=uploads
    ):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "sku_code": "SKU-CK",
                "batch_id": "batch-1",
                "qc_stage": "final_check",
                "qc_status": "pass",
                "operational_date": "2026-05-17",
                "barcode_photo": (BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 12), "barcode.jpg"),
                "label_photo": (BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 12), "label.jpg"),
            },
            content_type="multipart/form-data",
        )

    report = db.inserted["qc_reports"][0]
    assert response.status_code == 200
    assert report["barcode_photo_url"].endswith("barcode.jpg")
    assert report["label_photo_url"].endswith("label.jpg")
    assert len(db.inserted["qc_evidence"]) == 2


def test_staff_b_can_submit_final_check_on_same_batch_without_overwriting_cooking(client, staff_headers):
    db = FlowDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        first = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"sku_code": "SKU-CK", "batch_id": "batch-1", "qc_stage": "cooking_check", "temperature": "82", "qc_status": "pass", "staff_id": "staff-a", "operational_date": "2026-05-17"},
        )
        second = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"sku_code": "SKU-CK", "batch_id": "batch-1", "qc_stage": "final_check", "qc_status": "pass", "staff_id": "staff-b", "operational_date": "2026-05-17"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    reports = db.inserted["qc_reports"]
    assert len(reports) == 2
    assert {row["qc_stage"] for row in reports} == {"cooking_check", "final_check"}
    assert len(db.inserted["approvals"]) == 2


def test_admin_report_contains_cooking_and_final_stages(client, admin_headers):
    db = FlowDb()
    db.fixtures["qc_reports"] = [
        {"id": "r1", "batch_id": "batch-1", "batch_code": "QC-20260517-001", "barcode": "SKU-CK", "product_name": "Chicken Katsu", "qc_stage": "cooking_check", "status": "pass", "temperature": 82, "created_at": "2026-05-17T03:00:00Z"},
        {"id": "r2", "batch_id": "batch-1", "batch_code": "QC-20260517-001", "barcode": "SKU-CK", "product_name": "Chicken Katsu", "qc_stage": "final_check", "status": "pass", "created_at": "2026-05-17T06:00:00Z"},
    ]

    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/admin/reports/inspection?date=2026-05-17", headers=admin_headers)

    stages = {row["qc_stage"] for row in response.get_json()["data"]}
    assert response.status_code == 200
    assert stages == {"cooking_check", "final_check"}


def test_active_batch_endpoint_returns_active_batches_by_sku(client, staff_headers):
    db = FlowDb()
    db.fixtures["qc_reports"] = [{"id": "r1", "batch_id": "batch-1", "qc_stage": "cooking_check", "status": "pass", "created_at": "2026-05-17T03:00:00Z"}]
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.get("/api/inspection/batches/active?sku=SKU-CK", headers=staff_headers)

    batches = response.get_json()["data"]["active_batches"]
    assert response.status_code == 200
    assert batches[0]["batch_code"] == "QC-20260517-001"
    assert batches[0]["last_stage"] == "cooking_check"


def test_batch_by_product_endpoint_returns_batches_with_qc_status(client, staff_headers):
    db = FlowDb()
    db.fixtures["production_batches"][0].update({
        "batch_sequence": 1,
        "cook_name": "Rio",
        "quantity": 20,
        "production_shift": "Pagi",
    })
    db.fixtures["qc_reports"] = [{
        "id": "report-1",
        "batch_id": "batch-1",
        "batch_code": "QC-20260517-001",
        "status": "pass",
        "inspection_round": 1,
        "created_at": "2026-05-17T04:00:00Z",
    }]
    with patch("backend.api.batch_routes.get_client", return_value=db):
        response = client.get("/api/batch/by-product/product-1?date=2026-05-17", headers=staff_headers)

    body = response.get_json()["data"]
    assert response.status_code == 200
    assert body["product"]["product_code"] == "SKU-CK"
    assert body["batches"][0]["batch_code"] == "QC-20260517-001"
    assert body["batches"][0]["qc_status"] == "pass"
    assert body["batches"][0]["last_qc"]["id"] == "report-1"


def test_batch_by_product_filters_by_operational_date(client, staff_headers):
    db = FlowDb()
    db.fixtures["production_batches"].append({
        "id": "batch-old",
        "batch_code": "QC-20260516-001",
        "product_id": "product-1",
        "product_name": "Chicken Katsu",
        "production_date": "2026-05-16",
        "status": "in_progress",
        "created_at": "2026-05-16T03:00:00Z",
    })
    with patch("backend.api.batch_routes.get_client", return_value=db):
        response = client.get("/api/batch/by-product/product-1?date=2026-05-17", headers=staff_headers)

    codes = {row["batch_code"] for row in response.get_json()["data"]["batches"]}
    assert "QC-20260517-001" in codes
    assert "QC-20260516-001" not in codes


def test_batch_today_endpoint_returns_grouped_products(client, staff_headers):
    db = FlowDb()
    db.fixtures["production_batches"].append({
        "id": "batch-2",
        "batch_code": "QC-20260517-002",
        "product_id": "product-1",
        "product_name": "Chicken Katsu",
        "product_code": "SKU-CK",
        "production_date": "2026-05-17",
        "batch_sequence": 2,
        "status": "in_progress",
        "created_at": "2026-05-17T05:00:00Z",
    })
    db.fixtures["products"][0]["product_code"] = "SKU-CK"
    db.fixtures["production_batches"].append({
        "id": "batch-old",
        "batch_code": "QC-20260516-001",
        "product_id": "product-1",
        "product_name": "Chicken Katsu",
        "product_code": "SKU-CK",
        "production_date": "2026-05-16",
        "batch_sequence": 1,
        "status": "in_progress",
        "created_at": "2026-05-16T05:00:00Z",
    })
    db.fixtures["qc_reports"] = [{
        "id": "report-1",
        "batch_id": "batch-2",
        "status": "pass",
        "created_at": "2026-05-17T06:00:00Z",
    }]
    with patch("backend.api.batch_routes.get_client", return_value=db):
        response = client.get("/api/batch/today?date=2026-05-17", headers=staff_headers)

    data = response.get_json()["data"]
    assert response.status_code == 200
    assert data["date"] == "2026-05-17"
    assert len(data["products"]) == 1
    assert data["products"][0]["batch_count"] == 2
    assert data["products"][0]["status_summary"]["pass"] == 1
    assert {batch["batch_code"] for batch in data["products"][0]["batches"]} == {"QC-20260517-001", "QC-20260517-002"}


def test_batch_today_groups_by_product_id_not_batch_code(client, staff_headers):
    db = FlowDb()
    db.fixtures["production_batches"][0].pop("product_code", None)
    db.fixtures["production_batches"].append({
        "id": "batch-2",
        "batch_code": "GENERALQC-20260517-002",
        "product_id": "product-1",
        "product_name": "Chicken Katsu",
        "production_date": "2026-05-17",
        "batch_sequence": 2,
        "status": "in_progress",
        "created_at": "2026-05-17T05:00:00Z",
    })
    with patch("backend.api.batch_routes.get_client", return_value=db):
        response = client.get("/api/batch/today?date=2026-05-17", headers=staff_headers)

    products = response.get_json()["data"]["products"]
    assert len(products) == 1
    assert products[0]["product_id"] == "product-1"
    assert products[0]["batch_count"] == 2


def test_create_next_batch_endpoint_creates_next_sequence(client, staff_headers):
    db = FlowDb()
    with patch("backend.api.batch_routes.get_client", return_value=db), patch("backend.api.batch_routes.write_audit"):
        response = client.post(
            "/api/batch/next",
            headers=staff_headers,
            json={
                "product_id": "product-1",
                "production_date": "2026-05-17",
                "cook_name": "Andi",
                "quantity": 50,
                "production_shift": "Pagi",
            },
        )

    body = response.get_json()
    assert response.status_code == 201
    assert body["data"]["batch_sequence"] == 2
    assert body["data"]["batch_code"] == "SKUCK-20260517-002"
    assert body["data"]["cook_name"] == "Andi"
    assert body["data"]["quantity"] == 50.0
    assert "qc_status" not in body["data"]
    assert "final_qc_status" not in body["data"]


def test_create_next_batch_endpoint_returns_specific_validation_error(client, staff_headers):
    db = FlowDb()
    with patch("backend.api.batch_routes.get_client", return_value=db), patch("backend.api.batch_routes.write_audit"):
        response = client.post(
            "/api/batch/next",
            headers=staff_headers,
            json={
                "product_id": "product-1",
                "production_date": "2026-05-17",
                "cook_name": "Andi",
                "quantity": "abc",
                "production_shift": "Pagi",
            },
        )

    body = response.get_json()
    assert response.status_code == 400
    assert body["message"] == "quantity harus angka"


def test_submit_qc_rejects_batch_from_different_operational_date(client, staff_headers):
    db = FlowDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "sku_code": "SKU-CK",
                "batch_id": "batch-1",
                "batch_code": "QC-20260517-001",
                "qc_stage": "final_check",
                "qc_status": "pass",
                "staff_id": "staff-1",
                "operational_date": "2026-05-18",
            },
        )

    assert response.status_code == 409
    assert "Batch ini berasal dari tanggal berbeda" in response.get_json()["message"]


def test_empty_sku_returns_validation_error(client, staff_headers):
    with patch("backend.services.inspection_service.get_client", return_value=FlowDb()):
        response = client.post("/api/inspection/submit", headers=staff_headers, data={"qc_stage": "final_check", "qc_status": "pass"})

    assert response.status_code == 400
    assert "SKU" in response.get_json()["message"]


def test_qc_check_frontend_uses_single_batch_qc_form():
    from pathlib import Path

    html = Path("frontend/staff/inspection.html").read_text(encoding="utf-8").lower()
    js = Path("frontend/js/inspection.js").read_text(encoding="utf-8").lower()
    assert "qc check" in html
    assert "qcph" in html
    assert "qcbrix" in html
    assert "qctds" in html
    assert "foto evidence" in html
    assert "this.selectedstage = 'cooking_check'" in js
    assert "receiving" not in html
    assert "packing" not in html
    assert "preparation" not in html
    assert "receiving" not in js
    assert "packing" not in js
    assert "preparation" not in js
