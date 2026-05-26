from types import SimpleNamespace
from unittest.mock import patch


class BatchQuery:
    def __init__(self, table, db):
        self.table = table
        self.db = db
        self.payload = None
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            payload = self.payload[0] if isinstance(self.payload, list) else self.payload
            if self.table == "products":
                row = {"id": "general-product-1", **payload}
                self.db.rows.setdefault("products", []).append(row)
                self.db.inserted_products.append(row)
                return SimpleNamespace(data=[row])
            if self.table == "production_batches" and payload.get("batch_code") in self.db.duplicate_batch_codes:
                raise DuplicateBatchCodeError(payload.get("batch_code"))
            row = {"id": f"batch-{len(self.db.inserted_batches) + 1}", **payload}
            self.db.inserted = row
            self.db.inserted_batches.append(row)
            self.db.rows.setdefault(self.table, []).append(row)
            return SimpleNamespace(data=[row])
        rows = list(self.db.rows.get(self.table, []))
        for field, value in self.filters:
            rows = [row for row in rows if row.get(field) == value]
        return SimpleNamespace(data=rows)


class BatchDb:
    def __init__(self):
        self.rows = {
            "products": [{"id": "product-1", "product_code": "SKU-1", "product_name": "Soup"}],
            "production_batches": [],
        }
        self.inserted = None
        self.inserted_batches = []
        self.inserted_products = []
        self.duplicate_batch_codes = set()

    def table(self, table):
        return BatchQuery(table, self)


class DuplicateBatchCodeError(Exception):
    code = "23505"

    def __init__(self, batch_code):
        super().__init__(
            'duplicate key value violates unique constraint "production_batches_batch_code_key" '
            f"Key (batch_code)=({batch_code}) already exists."
        )


def test_create_batch_succeeds(client, staff_headers):
    db = BatchDb()
    with patch("backend.services.batch_service.get_client", return_value=db), patch(
        "backend.api.batch_routes.write_audit"
    ):
        response = client.post(
            "/api/batch/create",
            headers=staff_headers,
            json={"product_id": "SKU-1", "batch_code": "BATCH-001", "production_date": "2026-05-16"},
        )

    body = response.get_json()
    assert response.status_code == 201
    assert body["success"] is True
    assert db.inserted["batch_code"] == "BATCH-001"
    assert db.inserted["product_name"] == "Soup"


def test_create_batch_does_not_send_unresolved_sku_to_uuid_product_id(client, staff_headers):
    db = BatchDb()
    db.rows["products"] = []
    with patch("backend.services.batch_service.get_client", return_value=db), patch(
        "backend.api.batch_routes.write_audit"
    ):
        response = client.post(
            "/api/batch/create",
            headers=staff_headers,
            json={"product_id": "SKU-HONEY-001", "batch_code": "BATCH-002"},
        )

    assert response.status_code == 201
    assert db.inserted["product_id"] == "general-product-1"
    assert db.inserted["product_name"] == "SKU-HONEY-001"
    assert db.inserted_products[0]["product_code"] == "GENERAL-QC"


def test_create_batch_without_product_id_uses_default_product(client, staff_headers):
    db = BatchDb()
    db.rows["products"] = []
    with patch("backend.services.batch_service.get_client", return_value=db), patch(
        "backend.api.batch_routes.write_audit"
    ):
        response = client.post(
            "/api/batch/create",
            headers=staff_headers,
            json={"batch_code": "BATCH-003"},
        )

    assert response.status_code == 201
    assert db.inserted["product_id"] == "general-product-1"
    assert db.inserted["product_name"] == "General QC Product"
    assert db.inserted["status"] == "in_progress"


def test_create_batch_generates_batch_code_when_empty(client, staff_headers):
    db = BatchDb()
    with patch("backend.services.batch_service.get_client", return_value=db), patch(
        "backend.api.batch_routes.write_audit"
    ):
        response = client.post("/api/batch/create", headers=staff_headers, json={"product_id": "SKU-1"})

    assert response.status_code == 201
    assert response.get_json()["batch"]["batch_code"].startswith("SKU1-")
    assert response.get_json()["batch"]["batch_sequence"] == 1


def test_create_batch_without_batch_code_generates_unique_codes(client, staff_headers):
    db = BatchDb()
    with patch("backend.services.batch_service.get_client", return_value=db), patch(
        "backend.api.batch_routes.write_audit"
    ):
        first = client.post("/api/batch/create", headers=staff_headers, json={"product_id": "SKU-1", "production_date": "2026-05-27"})
        second = client.post("/api/batch/create", headers=staff_headers, json={"product_id": "SKU-1", "production_date": "2026-05-27"})

    assert first.status_code == 201
    assert second.status_code == 201
    codes = [row["batch_code"] for row in db.inserted_batches]
    assert len(codes) == 2
    assert len(set(codes)) == 2
    assert codes == ["SKU1-20260527-001", "SKU1-20260527-002"]


def test_create_batch_generates_product_date_sequence_code(client, staff_headers):
    db = BatchDb()
    db.rows["production_batches"] = [{
        "id": "batch-existing",
        "product_id": "general-product-1",
        "product_name": "Soup",
        "production_date": "2026-05-27",
        "batch_sequence": 5,
        "batch_code": "SKU1-20260527-005",
    }]
    with patch("backend.services.batch_service.get_client", return_value=db), patch(
        "backend.api.batch_routes.write_audit"
    ):
        response = client.post(
            "/api/batch/create",
            headers=staff_headers,
            json={
                "product_id": "SKU-1",
                "production_date": "2026-05-27",
                "quantity": 120,
                "production_shift": "Pagi",
                "cook_name": "Sari",
            },
        )

    batch = response.get_json()["batch"]
    assert response.status_code == 201
    assert batch["batch_code"] == "SKU1-20260527-006"
    assert batch["batch_sequence"] == 6
    assert batch["quantity"] == 120
    assert batch["production_shift"] == "Pagi"
    assert batch["cook_name"] == "Sari"


def test_next_batch_code_preview_returns_next_sequence(client, staff_headers):
    db = BatchDb()
    db.rows["production_batches"] = [{
        "id": "batch-existing",
        "product_id": "product-1",
        "product_name": "Soup",
        "production_date": "2026-05-27",
        "batch_sequence": 2,
        "batch_code": "SKU1-20260527-002",
    }]
    with patch("backend.services.batch_service.get_client", return_value=db):
        response = client.get(
            "/api/batch/next-code?product_id=SKU-1&production_date=2026-05-27",
            headers=staff_headers,
        )

    body = response.get_json()["data"]
    assert response.status_code == 200
    assert body["batch_code"] == "SKU1-20260527-003"
    assert body["batch_sequence"] == 3


def test_new_batch_ui_shows_cooking_sequence_fields():
    from pathlib import Path

    html = Path("frontend/staff/new_batch.html").read_text(encoding="utf-8")
    assert "Pemasakan ke" in html
    assert "quantity" in html
    assert "productionShift" in html
    assert "cookName" in html
    assert "Batch code otomatis" in html
    assert "/batch/next-code" in html


def test_create_batch_duplicate_manual_batch_code_returns_friendly_error(client, staff_headers):
    db = BatchDb()
    db.duplicate_batch_codes.add("BATCH-USED")

    with patch("backend.services.batch_service.get_client", return_value=db), patch(
        "backend.api.batch_routes.write_audit"
    ):
        response = client.post(
            "/api/batch/create",
            headers=staff_headers,
            json={"product_id": "SKU-1", "batch_code": "BATCH-USED"},
        )

    body = response.get_json()
    assert response.status_code == 409
    assert body["success"] is False
    assert body["error_code"] == "DUPLICATE_BATCH_CODE"
    assert body["message"] == "Kode batch sudah digunakan. Gunakan kode lain atau kosongkan agar sistem membuat otomatis."


def test_create_batch_without_batch_code_keeps_ph_brix_tds_optional(client, staff_headers):
    db = BatchDb()
    with patch("backend.services.batch_service.get_client", return_value=db), patch(
        "backend.api.batch_routes.write_audit"
    ):
        response = client.post("/api/batch/create", headers=staff_headers, json={"product_id": "SKU-1"})

    assert response.status_code == 201
    assert db.inserted["ph_status"] == "not_checked"
    assert db.inserted["brix_status"] == "not_checked"
    assert db.inserted["tds_status"] == "not_checked"
    assert "ph_value" not in db.inserted
    assert "brix_value" not in db.inserted
    assert "tds_value" not in db.inserted
