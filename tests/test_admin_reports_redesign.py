from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reports_section_is_operational_not_audit_logs():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    section = html.split('id="section-reports"', 1)[1].split('id="section-daily-reports"', 1)[0]

    assert "Audit Trail & System Logs" not in section
    assert "Laporan operasional monitoring suhu" in section
    assert "Total Monitoring Hari Ini" in section
    assert "Total QC Check Hari Ini" in section
    assert "Pending Approval" in section


def test_reports_has_tabs_actions_and_filters():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")

    for label in ("Monitoring Report", "QC Inspection Report", "Batch Report", "Alert Report"):
        assert label in html
    for label in ("Tanggal mulai", "Tanggal akhir", "Produk", "Ruangan", "Status QC", "Staff"):
        assert label in html
    assert "Export CSV" in html
    assert "Buka Google Sheets" in html
    assert "Print/PDF" in html


def test_audit_trail_section_exists_with_human_readable_labels():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "Audit Trail / System Logs" in html
    assert ">Audit Trail<" in html
    assert "auditActionLabel" in js
    assert "INPUT_TEMPERATURE: 'Input Suhu'" in js
    assert "SUBMIT: 'Submit QC'" in js
    assert "CREATE_BATCH: 'Buat Batch'" in js
    assert "UPDATE: 'Update Data'" in js
    assert "DELETE: 'Hapus Data'" in js


def test_admin_reports_use_staff_display_name_as_primary_label():
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "staffCell(row" in js
    assert "row.staff_display_name" in js
    assert "row.staff_name || row.staff_id || '-'" not in js
    assert "row.staff_name || row.inspector_name || row.staff_id || '-'" not in js
    assert "const actorName = log.staff_display_name" in js
