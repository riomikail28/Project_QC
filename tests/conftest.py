import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from backend import create_app


class FakeQuery:
    def __init__(self, table_name, fixtures):
        self.table_name = table_name
        self.fixtures = fixtures
        self.payload = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def update(self, payload):
        self.payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            return SimpleNamespace(data=[{"id": f"{self.table_name}-1", **self.payload}])
        return SimpleNamespace(data=self.fixtures.get(self.table_name, []))


class FakeSupabase:
    def __init__(self, fixtures=None):
        self.fixtures = fixtures or {}

    def table(self, table_name):
        return FakeQuery(table_name, self.fixtures)


@pytest.fixture()
def app():
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def staff_headers(app):
    token = app.extensions["security"].generate_token({
        "id": "staff-1",
        "username": "staff",
        "role": "staff",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(app):
    token = app.extensions["security"].generate_token({
        "id": "admin-1",
        "username": "admin",
        "role": "admin",
    })
    return {"Authorization": f"Bearer {token}"}
