from unittest.mock import patch


def test_task3_supabase_health_success_contract(client):
    with patch(
        "backend.api.health_routes.validate_supabase_connection",
        return_value={
            "success": True,
            "supabase_url_configured": True,
            "service_role_key_configured": True,
            "storage_bucket": "qc-evidence",
            "connection": "ok",
            "message": "Supabase connection OK",
        },
    ):
        response = client.get("/api/health/supabase")

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["connection"] == "ok"
    assert body["storage_bucket"] == "qc-evidence"


def test_task3_supabase_health_failure_is_not_false_200(client):
    with patch(
        "backend.api.health_routes.validate_supabase_connection",
        return_value={
            "success": False,
            "message": "Invalid Supabase API key or missing production environment variable",
            "error_code": "SUPABASE_CLIENT_INIT_FAILED",
        },
    ):
        response = client.get("/api/health/supabase")

    body = response.get_json()
    assert response.status_code == 503
    assert body["success"] is False
    assert "Invalid Supabase API key" in body["message"]
