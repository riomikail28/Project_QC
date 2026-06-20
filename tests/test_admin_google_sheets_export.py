from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1C5OVfOEYQuLRWXoyiUtKYybxb6MztDfK5mSroJlUYTI/edit?gid=0#gid=0"


def test_admin_sidebar_has_google_sheets_menu():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")

    assert "Google Sheets" in html
    assert 'href="#section-google-sheets"' in html
    assert 'data-target="google-sheets"' in html


def test_admin_google_sheets_section_and_button_url():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert 'id="section-google-sheets"' in html
    assert "QC Google Sheets Export" in html or "Google Sheets Export" in html
    assert "Data monitoring suhu dan QC report yang dikirim melalui Google Apps Script." in html
    assert SHEET_URL in html
    assert 'target="_blank"' in html
    assert "Test Export" in html
    assert "Export All Monitoring" in html
    assert "Export All QC Reports" in html
    assert "Export by Date Range" in html
    assert 'id="googleSheetsStartDate"' in html
    assert 'id="googleSheetsEndDate"' in html
    assert "/admin/google-sheets/test" in js
    assert "/admin/google-sheets/status" in js
    assert "/admin/google-sheets/export/${type}" in js
    assert "exportGoogleSheetsData" in js
    assert "googleSheetsErrorDetail" in js
    assert "Webhook URL belum valid. Gunakan Web App URL yang berakhiran /exec." in js
    assert "Test export gagal: status ${status} - ${responseText}" in js
    assert "iframe" not in html.lower()
    assert "loadGoogleSheetsExport" in js


def test_admin_google_sheets_quick_info_present():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")

    assert "Monitoring Logs" in html
    assert "QC Reports" in html
    assert "Export via Google Apps Script" in html
    assert "Google Apps Script" in html
    assert "Google Sheet" in html
    assert "Last Export" in html
