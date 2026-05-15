import io
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.services.storage_service import upload_file_storage, upload_photo_result


JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 32


class FakeStorageBucket:
    def __init__(self):
        self.uploads = []

    def upload(self, path, file, file_options=None):
        self.uploads.append((path, file, file_options or {}))
        return SimpleNamespace()

    def get_public_url(self, storage_path):
        return f"https://example.supabase.co/storage/v1/object/public/qc-evidence/{storage_path}"


class FakeStorage:
    def __init__(self, bucket):
        self.bucket = bucket

    def from_(self, bucket_name):
        assert bucket_name == "qc-evidence"
        return self.bucket


class FakeSupabaseStorageClient:
    def __init__(self):
        self.bucket = FakeStorageBucket()
        self.storage = FakeStorage(self.bucket)


class FakeFileStorage:
    filename = "evidence.jpg"
    mimetype = "image/jpeg"

    def read(self):
        return JPEG_BYTES


def test_upload_uses_supabase_storage_without_local_filesystem(monkeypatch):
    client = FakeSupabaseStorageClient()
    monkeypatch.setenv("VERCEL", "1")

    with patch("backend.services.storage_service.get_client", return_value=client), patch(
        "backend.services.storage_service.os.makedirs"
    ) as makedirs:
        uploaded = upload_file_storage(FakeFileStorage(), staff_id="staff/one")

    assert uploaded.bucket == "qc-evidence"
    assert uploaded.url.startswith("https://example.supabase.co/storage/v1/object/public/qc-evidence/")
    assert uploaded.storage_path.startswith("staff_one/")
    assert client.bucket.uploads
    assert client.bucket.uploads[0][2]["content-type"] == "image/jpeg"
    makedirs.assert_not_called()


def test_upload_fails_when_supabase_unavailable_instead_of_local_fallback(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)

    with patch("backend.services.storage_service.get_client", return_value=None), patch(
        "backend.services.storage_service.os.makedirs"
    ) as makedirs:
        with pytest.raises(RuntimeError, match="Supabase client unavailable"):
            upload_photo_result(JPEG_BYTES, "evidence.jpg", content_type="image/jpeg")

    makedirs.assert_not_called()


def test_app_factory_does_not_create_backend_upload_directories(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")

    with patch("backend.__init__.os.makedirs") as makedirs:
        from backend import create_app

        app = create_app()

    assert app is not None
    makedirs.assert_not_called()


def test_supabase_client_uses_anon_key_when_backend_key_alias_missing(monkeypatch):
    from backend.database import supabase_client

    monkeypatch.setenv("SUPABASE_URL", "https://example-ref.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    supabase_client.reset_client()

    with patch("backend.database.supabase_client.create_client", return_value="client") as create_client:
        client = supabase_client.get_client()

    assert client == "client"
    create_client.assert_called_once_with("https://example-ref.supabase.co", "anon-key")
    supabase_client.reset_client()
