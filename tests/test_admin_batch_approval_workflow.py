from pathlib import Path
from unittest.mock import patch

from tests.conftest import FakeSupabase


ROOT = Path(__file__).resolve().parents[1]


def test_batch_production_endpoint_returns_production_batches(client, admin_headers):
    fake_db = FakeSupabase({
        "production_batches": [{
            "id": "batch-1",
            "batch_code": "BATCH-001",
            "product_code": "SKU-001",
            "product_name": "Chicken Teriyaki",
            "batch_sequence": 2,
            "cook_name": "Andi",
            "quantity": 120,
            "production_date": "2026-06-07",
            "created_at": "2026-06-07T02:30:00Z",
        }],
        "qc_reports": [{
            "id": "qc-1",
            "batch_id": "batch-1",
            "batch_code": "BATCH-001",
            "status": "pass",
            "staff_id": "staff-1",
            "created_at": "2026-06-07T03:00:00Z",
        }],
        "approvals": [{
            "id": "approval-1",
            "related_type": "qc_report",
            "related_id": "qc-1",
            "status": "pending",
            "batch_code": "BATCH-001",
            "created_at": "2026-06-07T03:02:00Z",
        }],
    })

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.get("/api/v1/admin/batches?date=2026-06-07", headers=admin_headers)

    body = response.get_json()
    assert response.status_code == 200
    row = body["data"]["rows"][0]
    assert row["batch_code"] == "BATCH-001"
    assert row["product_name"] == "Chicken Teriyaki"
    assert row["qc_status"] == "PASS"
    assert row["approval_status"] == "Pending Approval"


def test_batch_production_empty_state_contract():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert 'id="table-batch-production"' in html
    assert "Belum ada batch produksi pada tanggal ini." in js
    assert "Buka Staff QC Check" in js
    assert "Buat Batch Baru" in js


def test_approvals_list_has_review_button_not_direct_decision():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    approval_section = html.split('id="section-approval"', 1)[1].split('id="section-audit"', 1)[0]
    assert "QC Result" in approval_section
    assert "Submitted At" in approval_section
    assert "openApprovalReview" in js
    assert "> Review</button>" in js
    assert "resolveApproval('${row.id}', true)" not in js
    assert "resolveApproval('${row.id}', false)" not in js


def test_approval_detail_endpoint_returns_qc_fields(client, admin_headers):
    fake_db = FakeSupabase({
        "approvals": [{
            "id": "approval-1",
            "related_type": "qc_report",
            "related_id": "qc-1",
            "status": "pending",
            "created_at": "2026-06-07T03:02:00Z",
        }],
        "qc_reports": [{
            "id": "qc-1",
            "batch_id": "batch-1",
            "batch_code": "BATCH-001",
            "product_name": "Chicken Teriyaki",
            "status": "hold",
            "qc_stage": "cooking_check",
            "temperature": 72,
            "ph_value": 6.1,
            "brix_value": 12,
            "tds_value": 90,
            "notes": "Need recheck",
            "product_photo_url": "https://img/evidence.jpg",
            "staff_id": "staff-1",
            "created_at": "2026-06-07T03:00:00Z",
        }],
        "production_batches": [{
            "id": "batch-1",
            "batch_code": "BATCH-001",
            "product_name": "Chicken Teriyaki",
            "batch_sequence": 2,
            "cook_name": "Andi",
            "quantity": 120,
            "created_at": "2026-06-07T02:30:00Z",
        }],
    })

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.get("/api/v1/admin/approvals/approval-1", headers=admin_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["temperature"] == 72
    assert body["ph"] == 6.1
    assert body["brix"] == 12
    assert body["tds"] == 90
    assert body["notes"] == "Need recheck"
    assert body["evidence_url"] == "https://img/evidence.jpg"


def test_reject_requires_reason_frontend_contract():
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "async rejectCurrentApproval()" in js
    assert "Reject reason wajib diisi." in js
    assert "approval-reject-reason" in js
    assert "await this.resolveApproval(this.currentApprovalId, false, reason)" in js


def test_approve_success_refreshes_approvals_and_batch_production():
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "await this.loadApprovals()" in js
    assert "await this.loadProductionBoard().catch" in js
    assert "Approval berhasil diproses." in js


def test_batch_production_and_approvals_use_different_renderers():
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "async loadBatchProduction()" in js
    assert "async loadProductionBoard" in js
    assert "renderBatchProduction(rows)" in js
    assert "renderApprovals(rows = [])" in js
    assert "case 'daily-reports': this.loadProductionBoard(); break;" in js
    assert "case 'approval': this.loadApprovals(); break;" in js


def test_production_qc_board_is_activity_based_not_product_master_based():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")
    load_block = js[js.index("async loadProductionBoard"):js.index("groupProductionBySku", js.index("async loadProductionBoard"))]
    group_start = js.index("groupProductionBySku(batches = [])")
    group_block = js[group_start:js.index("renderProductionBoardSummary", group_start)]

    assert 'id="production-board-summary"' in html
    assert "this.fetchAdminData(endpoint" in load_block
    assert "this.fetchAdminData(`${this.apiBase}/products`)" not in load_block
    assert "products.forEach" not in group_block
    assert "return Array.from(groups.values()).filter(group => group.batches.length)" in group_block


def test_production_qc_board_summary_and_empty_state_contract():
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "css" / "admin_enterprise.css").read_text(encoding="utf-8")

    assert "renderProductionBoardSummary(groups, batches" in js
    assert "SKU Diproduksi" in js
    assert "Total Batch" in js
    assert "Pending Approval" in js
    assert "Belum ada produksi pada tanggal ini." in js
    assert "Buka Staff QC Check" in js
    assert "Buat Batch Baru" in js
    assert ".production-board-summary" in css
    assert ".production-empty-actions" in css


def test_production_qc_board_detail_lists_batches_for_selected_date():
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")
    detail_block = js[js.index("openSkuBoard(group)"):js.index("async openBatchBoardDetail", js.index("openSkuBoard(group)"))]

    assert "const batches = group.batches || []" in detail_block
    assert "Batch #${this.escapeHtml(batch.batch_sequence || index + 1)}" in detail_block
    assert "Cook:" in detail_block
    assert "Jam:" in detail_block
    assert "batch.qc_status || 'Belum QC'" in detail_block
    assert "batch.approval_status || 'Pending Approval'" in detail_block
