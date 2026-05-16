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
            row = {"id": "batch-1", **payload}
            self.db.inserted = row
            return SimpleNamespace(data=[row])
        rows = list(self.db.rows.get(self.table, []))
        for field, value in self.filters:
            rows = [row for row in rows if row.get(field) == value]
        return SimpleNamespace(data=rows)


class BatchDb:
    def __init__(self):
        self.rows = {"products": [{"id": "product-1", "product_code": "SKU-1", "product_name": "Soup"}]}
        self.inserted = None
        self.inserted_products = []

    def table(self, table):
        return BatchQuery(table, self)


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


def test_create_batch_requires_batch_code(client, staff_headers):
    response = client.post("/api/batch/create", headers=staff_headers, json={"product_id": "SKU-1"})

    assert response.status_code == 400
    assert response.get_json()["message"] == "Field batch_code is required"
