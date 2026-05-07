import os
import unittest

os.environ["JWT_SECRET_KEY"] = "test-secret"

from backend import create_app


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.token = self.app.extensions["security"].generate_token({
            "id": "00000000-0000-0000-0000-000000000001",
            "username": "admin",
            "role": "admin",
            "name": "Test Admin",
        })
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_health_check_is_public(self):
        response = self.client.get("/api/qc/health")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_auth(self):
        response = self.client.get("/api/qc/dashboard")
        self.assertEqual(response.status_code, 401)

    def test_dashboard_with_auth(self):
        response = self.client.get("/api/qc/dashboard", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("health_score", response.get_json())

    def test_staff_list_requires_admin(self):
        response = self.client.get("/api/staff", headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_login_without_database_does_not_use_demo_fallback(self):
        response = self.client.post(
            "/api/staff/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 401)

    def test_qc_validation_rejects_bad_temperature(self):
        response = self.client.post(
            "/api/qc/validate",
            headers=self.headers,
            json={"unit_type": "chiller", "temperature": 999},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
