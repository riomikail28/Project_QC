from types import SimpleNamespace
from unittest.mock import patch


class MutableQuery:
    def __init__(self, table_name, db):
        self.table_name = table_name
        self.db = db
        self.filters = []
        self.payload = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self.filters.append(("eq", field, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def update(self, payload):
        self.payload = payload
        return self

    def execute(self):
        rows = list(self.db.fixtures.get(self.table_name, []))
        for _, field, value in self.filters:
            rows = [row for row in rows if row.get(field) == value]
        if self.payload is not None:
            for row in rows:
                row.update(self.payload)
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=rows)


class MutableSupabase:
    def __init__(self):
        self.fixtures = {
            "approvals": [{"id": "approval-1", "related_type": "qc_report", "related_id": "report-1", "status": "pending"}],
            "qc_reports": [{"id": "report-1", "approval_status": "pending", "status": "hold"}],
        }

    def table(self, table_name):
        return MutableQuery(table_name, self)


def test_task3_admin_approve_updates_approval_and_qc_report(client, admin_headers):
    db = MutableSupabase()
    with patch("backend.services.admin_service.get_client", return_value=db), patch("backend.services.audit_service.write_audit"):
        response = client.post("/api/admin/approvals/approval-1/approve", headers=admin_headers, json={"comment": "ok"})

    assert response.status_code == 200
    assert db.fixtures["approvals"][0]["status"] == "approved"
    assert db.fixtures["qc_reports"][0]["approval_status"] == "approved"


def test_task3_admin_reject_accepts_report_id_and_updates_pending_approval(client, admin_headers):
    db = MutableSupabase()
    with patch("backend.services.admin_service.get_client", return_value=db), patch("backend.services.audit_service.write_audit"):
        response = client.post("/api/admin/approvals/report-1/reject", headers=admin_headers, json={"comment": "foto blur"})

    assert response.status_code == 200
    assert db.fixtures["approvals"][0]["status"] == "rejected"
    assert db.fixtures["qc_reports"][0]["approval_status"] == "rejected"
    assert db.fixtures["qc_reports"][0]["rejection_reason"] == "foto blur"
