import pytest
from unittest.mock import patch
from io import BytesIO
from types import SimpleNamespace
from backend.services.inspection_service import InspectionService
from backend.services.admin_service import AdminService
from backend.database.supabase_client import get_client

class MockQuery:
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

    def is_(self, field, value):
        self.filters.append(("is_", field, value))
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
        # Insert logic
        if self.payload is not None:
            payloads = self.payload if isinstance(self.payload, list) else [self.payload]
            rows = []
            for p in payloads:
                row = {"id": f"{self.table}-{len(self.db.fixtures.get(self.table, [])) + 1}", **p}
                self.db.fixtures.setdefault(self.table, []).append(row)
                rows.append(row)
            return SimpleNamespace(data=rows)

        # Query & Update logic
        rows = list(self.db.fixtures.get(self.table, []))
        for op, field, value in self.filters:
            if op == "eq":
                rows = [row for row in rows if row.get(field) == value]
            elif op == "is_":
                if value == "null" or value is None:
                    rows = [row for row in rows if row.get(field) is None]
                else:
                    rows = [row for row in rows if str(row.get(field)).lower() == str(value).lower()]
        
        if self.update_payload is not None:
            for row in rows:
                row.update(self.update_payload)
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=rows)


class MockDb:
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

    def table(self, table_name):
        return MockQuery(table_name, self)


def test_full_three_stage_qc_flow_with_recheck():
    db = MockDb()
    service = InspectionService(sb_client=db)
    admin_service = AdminService(sb_client=db)

    # 1. Submit Cooking Sensory (Round 1)
    payload_sensory = {
        "sku_code": "SKU-CK",
        "batch_id": "batch-1",
        "batch_code": "QC-20260517-001",
        "qc_stage": "cooking_sensory",
        "temperature": "82",
        "qc_status": "pass",
        "operational_date": "2026-05-17",
        "staff_id": "staff-1",
        "staff_name": "Test Staff",
        "created_at": "2026-05-17T04:00:00Z",
    }
    with patch("backend.services.inspection_service.write_audit"):
        res = service.submit_qc(payload_sensory, files={}, actor_role="staff")
        assert res["success"] is True
        sensory_row_id = res["data"]["id"]
        assert sensory_row_id is not None
        assert res["data"]["temperature"] == "82"
        assert res["data"]["inspection_round"] == 1

    # 2. Update/Save Draft for Cooking Sensory (Round 1) - Should update same row
    payload_sensory_update = {**payload_sensory, "temperature": "85"}
    with patch("backend.services.inspection_service.write_audit"):
        res = service.submit_qc(payload_sensory_update, files={}, actor_role="staff")
        assert res["success"] is True
        assert res["data"]["id"] == sensory_row_id
        assert res["data"]["temperature"] == "85"
        # Verify no duplicate row created
        reports = [r for r in db.fixtures["qc_reports"] if r["qc_stage"] == "cooking_sensory"]
        assert len(reports) == 1

    # 3. Submit Cooking Instrument (Round 1)
    payload_instrument = {
        "sku_code": "SKU-CK",
        "batch_id": "batch-1",
        "batch_code": "QC-20260517-001",
        "qc_stage": "cooking_instrument",
        "ph_value": "6.2",
        "brix_value": "12.5",
        "tds_value": "150",
        "qc_status": "pass",
        "operational_date": "2026-05-17",
        "staff_id": "staff-1",
        "staff_name": "Test Staff",
        "created_at": "2026-05-17T04:10:00Z",
    }
    with patch("backend.services.inspection_service.write_audit"):
        res = service.submit_qc(payload_instrument, files={}, actor_role="staff")
        assert res["success"] is True
        assert res["data"]["inspection_result"]["ph_value"] == "6.2"
        assert res["data"]["inspection_round"] == 1

    # 4. Submit Packing (Round 1)
    payload_packing = {
        "sku_code": "SKU-CK",
        "batch_id": "batch-1",
        "batch_code": "QC-20260517-001",
        "qc_stage": "packing",
        "gramasi_1": "90",
        "gramasi_2": "91",
        "gramasi_3": "90",
        "gramasi_4": "92",
        "gramasi_5": "90",
        "mfg_date": "2026-05-17",
        "exp_date": "2026-05-24",
        "qc_status": "pass",
        "operational_date": "2026-05-17",
        "staff_id": "staff-1",
        "staff_name": "Test Staff",
        "created_at": "2026-05-17T04:20:00Z",
    }
    with patch("backend.services.inspection_service.write_audit"):
        res = service.submit_qc(payload_packing, files={}, actor_role="staff")
        assert res["success"] is True
        packing_row_1_id = res["data"]["id"]
        assert res["data"]["inspection_round"] == 1

    # 5. Start Recheck (Round 2) by passing parent_inspection
    # Submit Cooking Sensory (Round 2)
    payload_sensory_r2 = {
        **payload_sensory,
        "parent_inspection": packing_row_1_id,
        "temperature": "88",
        "created_at": "2026-05-17T06:00:00Z",
    }
    with patch("backend.services.inspection_service.write_audit"):
        res = service.submit_qc(payload_sensory_r2, files={}, actor_role="staff")
        assert res["success"] is True
        sensory_row_2_id = res["data"]["id"]
        assert sensory_row_2_id != sensory_row_id # Different row ID
        assert res["data"]["inspection_round"] == 2
        assert res["data"]["parent_inspection"] == packing_row_1_id

    # 6. Update/Save Draft for Cooking Sensory (Round 2) - Should update Round 2 row, not Round 1
    payload_sensory_r2_update = {**payload_sensory_r2, "temperature": "89"}
    with patch("backend.services.inspection_service.write_audit"):
        res = service.submit_qc(payload_sensory_r2_update, files={}, actor_role="staff")
        assert res["success"] is True
        assert res["data"]["id"] == sensory_row_2_id
        assert res["data"]["temperature"] == "89"
        
        # Verify reports counts
        sensory_reports = [r for r in db.fixtures["qc_reports"] if r["qc_stage"] == "cooking_sensory"]
        assert len(sensory_reports) == 2 # One for Round 1, one for Round 2
        assert sensory_reports[0]["temperature"] == "85" # Round 1 temperature intact
        assert sensory_reports[1]["temperature"] == "89" # Round 2 temperature updated

    # 7. Submit Cooking Instrument (Round 2)
    payload_instrument_r2 = {
        **payload_instrument,
        "parent_inspection": packing_row_1_id,
        "ph_value": "6.5",
        "created_at": "2026-05-17T06:10:00Z",
    }
    with patch("backend.services.inspection_service.write_audit"):
        res = service.submit_qc(payload_instrument_r2, files={}, actor_role="staff")
        assert res["success"] is True
        assert res["data"]["inspection_result"]["ph_value"] == "6.5"
        assert res["data"]["inspection_round"] == 2

    # 8. Submit Packing (Round 2)
    payload_packing_r2 = {
        **payload_packing,
        "parent_inspection": packing_row_1_id,
        "gramasi_1": "95",
        "created_at": "2026-05-17T06:20:00Z",
    }
    with patch("backend.services.inspection_service.write_audit"):
        res = service.submit_qc(payload_packing_r2, files={}, actor_role="staff")
        assert res["success"] is True
        assert res["data"]["inspection_result"]["gramasi_1"] == "95"
        assert res["data"]["inspection_round"] == 2

    # Verify total rows created is exactly 6
    assert len(db.fixtures["qc_reports"]) == 6

    # Verify admin services aggregates data correctly from both rounds
    with patch("backend.services.admin_service.get_client", return_value=db):
        res = admin_service.get_batch_production(date="2026-05-17")
        rows = res["data"]["rows"]
        assert len(rows) == 1
        row = rows[0]
        # pH, Brix, TDS, Gramasi should match latest round (Round 2)
        assert row["ph"] == "6.5"
        assert row["brix"] == "12.5"
        assert row["tds"] == "150"
        assert row["temperature"] == "89"
        assert row["gramasi"] == ["95", "91", "90", "92", "90"]
