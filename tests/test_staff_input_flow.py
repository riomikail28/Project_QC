from unittest.mock import patch


class RecordingQuery:
    def __init__(self, table, db):
        self.table = table
        self.db = db
        self.payload = None
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        if self.payload is not None:
            row = {"id": f"{self.table}-1", **self.payload}
            self.db.inserted.setdefault(self.table, []).append(row)
            return type("Result", (), {"data": [row]})()
        rows = list(self.db.fixtures.get(self.table, []))
        for field, value in self.filters:
            rows = [row for row in rows if row.get(field) == value]
        return type("Result", (), {"data": rows})()


class RecordingDb:
    def __init__(self, fixtures=None):
        self.fixtures = fixtures or {}
        self.inserted = {}

    def table(self, table):
        return RecordingQuery(table, self)


def test_staff_submit_inspection_persists_qc_report_and_barcode(client, staff_headers):
    db = RecordingDb()
    with patch("backend.services.inspection_service.get_client", return_value=db):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={
                "barcode": "BATCH-001",
                "batch_code": "BATCH-001",
                "temperature": "4.2",
                "ccp_stage": "Packing",
                "qc_status": "pass",
                "staff_id": "staff-1",
            },
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert db.inserted["qc_reports"][0]["batch_code"] == "BATCH-001"
    assert db.inserted["qc_reports"][0]["inspection_result"]["ccp_stage"] == "Packing"
    assert db.inserted["barcode_labels"][0]["barcode_value"] == "BATCH-001"


def test_staff_submit_inspection_requires_batch_identifier(client, staff_headers):
    with patch("backend.services.inspection_service.get_client", return_value=RecordingDb()):
        response = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"temperature": "4.2", "qc_status": "pass", "staff_id": "staff-1"},
        )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
