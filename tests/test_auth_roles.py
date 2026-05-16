from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_qc_staff_token_keeps_legacy_staff_role_for_frontend_compatibility(app):
    token = app.extensions["security"].generate_token({
        "id": "staff-1",
        "username": "staff",
        "role": "staff",
    })
    payload = app.extensions["security"].verify_token(token)

    assert payload["role"] == "staff"


def test_supervisor_can_access_admin_reports(client, app):
    token = app.extensions["security"].generate_token({
        "id": "supervisor-1",
        "username": "supervisor",
        "role": "supervisor",
    })
    with patch("backend.services.admin_service.get_client", return_value=FakeSupabase({})):
        response = client.get(
            "/api/v1/admin/reports/inspection",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code != 403
