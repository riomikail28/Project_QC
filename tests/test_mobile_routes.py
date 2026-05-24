def test_admin_hash_route_redirect_pattern_serves_admin_panel(client):
    response = client.get("/admin/")

    assert response.status_code == 200
    assert b"QC Enterprise" in response.data


def test_admin_dashboard_alias_serves_redirect(client):
    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert b"/admin/" in response.data


def test_staff_dashboard_alias_serves_redirect(client):
    response = client.get("/staff/dashboard")

    assert response.status_code == 200
    assert b"/staff/dashboard.html" in response.data


def test_staff_mobile_routes_serve_pages(client):
    for path in ["/dashboard.html", "/monitoring.html", "/inspection.html", "/profile.html", "/alerts.html"]:
        response = client.get(path)
        assert response.status_code == 200
