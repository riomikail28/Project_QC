from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_admin_imports_global_design_system():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "css" / "admin_enterprise.css").read_text(encoding="utf-8")
    global_css = (ROOT / "frontend" / "styles" / "global.css").read_text(encoding="utf-8")

    assert "../styles/global.css" in html
    for var_name in ("--app-bg", "--card-bg", "--primary", "--text-main", "--border-soft"):
        assert var_name in global_css
        assert var_name in css


def test_admin_navigation_is_internal_sections():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    for label in (
        "Overview",
        "Products",
        "Staff",
        "QC Reports",
        "Temperature Logs",
        "Barcode Traceability",
        "Approvals",
        "Audit Trail",
        "Settings",
    ):
        assert label in html
    assert "dashboard.html#admin" not in html
