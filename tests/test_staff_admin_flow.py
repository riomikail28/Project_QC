from unittest.mock import patch

from tests.test_inspection_submit import InsertDb


def test_staff_submit_then_admin_can_read_qc_report(client, staff_headers, admin_headers):
    db = InsertDb()

    with patch("backend.services.inspection_service.get_client", return_value=db):
        submit = client.post(
            "/api/inspection/submit",
            headers=staff_headers,
            data={"barcode": "FLOW-001", "qc_status": "pass"},
        )

    assert submit.status_code == 200

    class Query:
        def __init__(self, table):
            self.table = table

        def select(self, *args, **kwargs):
            return self

        def order(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def execute(self):
            return type("Result", (), {"data": db.inserted.get(self.table, [])})()

    class ReportDb:
        def table(self, table):
            return Query(table)

    with patch("backend.services.admin_service.get_client", return_value=ReportDb()):
        report = client.get("/api/v1/admin/reports/inspection", headers=admin_headers)

    assert report.status_code == 200
    assert report.get_json()["data"][0]["batch_code"] == "FLOW-001"
