from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class LearningQuery:
    def __init__(self, table, db):
        self.table = table
        self.db = db
        self.payload = None
        self.update_payload = None
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def gte(self, field, value):
        self.filters.append((field, value, "gte"))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            payload = self.payload[0] if isinstance(self.payload, list) else self.payload
            if self.table == "itdv_modules" and any(
                row.get("slug") == payload.get("slug") for row in self.db.rows[self.table]
            ):
                raise Exception('duplicate key value violates unique constraint "itdv_modules_pkey" 23505')
            row = {"id": f"{self.table}-{len(self.db.rows.setdefault(self.table, [])) + 1}", **payload}
            self.db.rows.setdefault(self.table, []).append(row)
            self.db.inserted[self.table] = row
            return SimpleNamespace(data=[row])
        rows = list(self.db.rows.get(self.table, []))
        for item in self.filters:
            field, value = item[0], item[1]
            rows = [row for row in rows if row.get(field) == value]
        if self.update_payload is not None:
            updated = []
            for row in rows:
                row.update(self.update_payload)
                updated.append(row)
            if not updated and self.filters:
                row = {self.filters[0][0]: self.filters[0][1], **self.update_payload}
                self.db.rows.setdefault(self.table, []).append(row)
                updated.append(row)
            self.db.updated[self.table] = updated[0] if updated else self.update_payload
            return SimpleNamespace(data=updated)
        return SimpleNamespace(data=rows)


class LearningDb:
    def __init__(self):
        self.rows = {
            "itdv_modules": [
                {
                    "slug": "haccp",
                    "title": "HACCP",
                    "description": "Food safety",
                    "summary": "Food safety",
                    "duration_minutes": 20,
                    "sort_order": 1,
                    "published": True,
                    "archived": False,
                }
            ],
            "itdv_module_mini_quizzes": [],
            "itdv_simulations": [],
            "itdv_quiz_questions": [],
            "itdv_progress": [],
            "itdv_simulation_attempts": [],
            "itdv_quiz_attempts": [],
            "itdv_certificates": [],
        }
        self.inserted = {}
        self.updated = {}

    def table(self, table):
        return LearningQuery(table, self)


def test_admin_can_list_learning_modules(client, admin_headers):
    db = LearningDb()
    with patch("backend.services.admin_learning_service.get_client", return_value=db):
        response = client.get("/api/admin/learning/modules", headers=admin_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][0]["slug"] == "haccp"


def test_admin_can_create_learning_module(client, admin_headers):
    db = LearningDb()
    with patch("backend.services.admin_learning_service.get_client", return_value=db):
        response = client.post(
            "/api/admin/learning/modules",
            headers=admin_headers,
            json={"title": "Cold Chain", "slug": "cold-chain", "estimated_time": 30, "order_number": 2},
        )

    body = response.get_json()
    assert response.status_code == 201
    assert body["success"] is True
    assert db.inserted["itdv_modules"]["slug"] == "cold-chain"
    assert db.inserted["itdv_modules"]["duration_minutes"] == 30


def test_admin_can_update_learning_module(client, admin_headers):
    db = LearningDb()
    with patch("backend.services.admin_learning_service.get_client", return_value=db):
        response = client.put(
            "/api/admin/learning/modules/haccp",
            headers=admin_headers,
            json={"title": "HACCP Updated", "estimated_time": 40},
        )

    assert response.status_code == 200
    assert db.updated["itdv_modules"]["title"] == "HACCP Updated"
    assert db.updated["itdv_modules"]["duration_minutes"] == 40


def test_admin_soft_deletes_learning_module(client, admin_headers):
    db = LearningDb()
    with patch("backend.services.admin_learning_service.get_client", return_value=db):
        response = client.delete("/api/admin/learning/modules/haccp", headers=admin_headers)

    assert response.status_code == 200
    assert db.updated["itdv_modules"]["published"] is False
    assert db.updated["itdv_modules"]["archived"] is True


def test_staff_cannot_access_admin_learning(client, staff_headers):
    response = client.get("/api/admin/learning/modules", headers=staff_headers)

    assert response.status_code in {401, 403}


def test_admin_learning_invalid_payload_returns_400(client, admin_headers):
    db = LearningDb()
    with patch("backend.services.admin_learning_service.get_client", return_value=db):
        response = client.post("/api/admin/learning/modules", headers=admin_headers, json={"slug": "missing-title"})

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert "Title wajib" in body["message"]


def test_admin_learning_duplicate_slug_returns_409(client, admin_headers):
    db = LearningDb()
    with patch("backend.services.admin_learning_service.get_client", return_value=db):
        response = client.post(
            "/api/admin/learning/modules", headers=admin_headers, json={"title": "HACCP", "slug": "haccp"}
        )

    body = response.get_json()
    assert response.status_code == 409
    assert body["error_code"] == "DUPLICATE_SLUG"
    assert body["message"] == "Slug sudah digunakan. Gunakan slug lain."


def test_admin_ui_has_learning_itdv_section():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "Learning ITDV" in html
    assert "Admin Learning Management" in html
    assert 'data-learning-tab="modules"' in html
    assert 'data-learning-tab="mini-quiz"' in html
    assert 'data-learning-tab="simulation"' in html
    assert 'data-learning-tab="quiz"' in html
    assert "Certificates/Progress" in html
    assert "/admin/learning/modules" in js


def test_existing_learning_route_still_serves_page(client):
    response = client.get("/learning/")

    assert response.status_code == 200
    assert b"Learning" in response.data or b"ITDV" in response.data
