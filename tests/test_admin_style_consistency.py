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
        "Dashboard",
        "Monitoring",
        "Batch Production",
        "QC Inspection",
        "Alerts",
        "Reports",
        "Staff",
        "Learning ITDV",
        "Settings",
    ):
        assert label in html
    assert "dashboard.html#admin" not in html


def test_admin_uses_explicit_html_route_for_role_routing():
    admin_page = ROOT / "frontend" / "admin" / "admin_panel.html"
    alias = ROOT / "frontend" / "admin" / "dashboard"

    assert admin_page.exists()
    assert not alias.exists()
