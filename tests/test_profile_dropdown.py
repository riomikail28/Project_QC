from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_profile_menu_script_is_loaded_on_admin_and_staff_topbars():
    pages = [
        ROOT / "frontend" / "admin" / "admin_panel.html",
        ROOT / "frontend" / "staff" / "dashboard.html",
        ROOT / "frontend" / "staff" / "monitoring.html",
        ROOT / "frontend" / "staff" / "inspection.html",
        ROOT / "frontend" / "staff" / "profile.html",
        ROOT / "frontend" / "staff" / "alerts.html",
    ]

    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert "../js/profile-menu.js" in html, page.name


def test_profile_dropdown_click_outside_logout_and_routes_are_wired():
    js = (ROOT / "frontend" / "js" / "profile-menu.js").read_text(encoding="utf-8")

    assert "avatar.addEventListener('click'" in js
    assert "event.target.closest('.profile-menu-wrap')" in js
    assert "this.closeAll()" in js
    assert "Auth.logout()" in js
    assert 'href="/staff/profile.html"' in js
    assert 'href="/admin/admin_panel.html#section-facility"' in js


def test_profile_dropdown_staff_and_admin_menu_rules_are_role_based():
    js = (ROOT / "frontend" / "js" / "profile-menu.js").read_text(encoding="utf-8")

    assert "Auth.canAccessAdmin(user.role)" in js
    assert "isAdmin ?" in js
    assert "Settings" in js
    assert "Profile" in js
    assert "Logout" in js


def test_profile_dropdown_styles_include_animation_and_hover():
    css = (ROOT / "frontend" / "styles" / "global.css").read_text(encoding="utf-8")

    assert ".profile-dropdown" in css
    assert "transition: opacity" in css
    assert ".profile-menu-wrap.open .profile-dropdown" in css
    assert ".profile-dropdown-item:hover" in css
    assert "top: calc(100% + 10px)" in css
