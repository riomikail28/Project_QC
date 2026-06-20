from types import SimpleNamespace
from unittest.mock import patch

from backend.database import supabase_client

SERVICE_ROLE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV4YW1wbGUiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxLCJleHAiOjQxMDI0NDQ4MDB9."
    "signature"
)
ANON_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV4YW1wbGUiLCJyb2xlIjoiYW5vbiIsImlhdCI6MSwiZXhwIjo0MTAyNDQ0ODAwfQ."
    "signature"
)


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
    monkeypatch.setenv("SUPABASE_ANON_KEY", ANON_JWT)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    supabase_client.reset_client()

    result = supabase_client.validate_supabase_connection()

    assert result["success"] is False
    assert result["error_code"] == "SUPABASE_SERVICE_ROLE_KEY_INVALID"
    assert "service_role JWT" in result["message"]


def test_supabase_cli_secret_returns_specific_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_example")
    monkeypatch.setenv("SUPABASE_ANON_KEY", ANON_JWT)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    supabase_client.reset_client()

    result = supabase_client.validate_supabase_connection()

    assert result["success"] is False
    assert result["error_code"] == "SUPABASE_SERVICE_ROLE_KEY_INVALID"
    assert "CLI Secret" in result["message"]


def test_supabase_health_checks_database_schema_and_storage(monkeypatch):
    class FakeStorage:
        def get_bucket(self, bucket):
            assert bucket == "qc-evidence"
            return {"name": bucket}

    class FakeClient:
        storage = FakeStorage()

        def table(self, table_name):
            assert table_name == "facility_rooms"
            return self

        def select(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", SERVICE_ROLE_JWT)
    monkeypatch.setenv("SUPABASE_ANON_KEY", ANON_JWT)
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "qc-evidence")
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    supabase_client.reset_client()

    with patch("backend.database.supabase_client.create_client", return_value=FakeClient()):
        result = supabase_client.validate_supabase_connection()

    assert result["success"] is True
    assert result["checks"]["database"]["success"] is True
    assert result["checks"]["schema"]["success"] is True
    assert result["checks"]["storage"]["success"] is True


def test_supabase_health_endpoint_does_not_expose_secret(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "invalid-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", ANON_JWT)
    supabase_client.reset_client()

    response = client.get("/api/health/supabase")

    body = response.get_json()
    assert response.status_code == 503
    assert body["success"] is False
    assert "invalid-key" not in response.get_data(as_text=True)
