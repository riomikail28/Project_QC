from unittest.mock import patch

from backend.database import supabase_client


def test_supabase_env_missing_returns_clear_error(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    supabase_client.reset_client()

    result = supabase_client.validate_supabase_connection()

    assert result["success"] is False
    assert result["message"] == "SUPABASE_URL is not configured"
    assert result["supabase_url_configured"] is False


def test_supabase_invalid_key_returns_clear_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "invalid-key")
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    supabase_client.reset_client()

    with patch("backend.database.supabase_client.create_client", side_effect=Exception("Invalid API key")), patch(
        "backend.database.supabase_client.Client", side_effect=Exception("Invalid API key")
    ):
        result = supabase_client.validate_supabase_connection()

    assert result["success"] is False
    assert result["message"] == "Invalid Supabase API key"


def test_supabase_health_endpoint_does_not_expose_secret(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "invalid-key")
    supabase_client.reset_client()

    with patch("backend.database.supabase_client.create_client", side_effect=Exception("Invalid API key")), patch(
        "backend.database.supabase_client.Client", side_effect=Exception("Invalid API key")
    ):
        response = client.get("/api/health/supabase")

    body = response.get_json()
    assert response.status_code == 503
    assert body["success"] is False
    assert "invalid-key" not in response.get_data(as_text=True)
