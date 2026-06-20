import os
import unittest

os.environ["JWT_SECRET_KEY"] = "test-secret"

from unittest.mock import patch

from backend import create_app
from backend.services.session_store import MemoryStore


class TestAuthFlow(unittest.TestCase):
    def setUp(self):
        self.session_store = MemoryStore()

        patcher = patch("backend.services.session_store.get_session_store", lambda: self.session_store)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Patch staff_manager.login to return a valid user
        self.login_patcher = patch(
            "backend.auth.staff_manager.login", lambda u, p: {"id": "user-1", "username": "user-1", "role": "staff"}
        )
        self.login_patcher.start()
        self.addCleanup(self.login_patcher.stop)

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_login_refresh_logout_flow(self):
        # Login
        resp = self.client.post("/api/staff/login", json={"username": "user-1", "password": "pass"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("token", data)
        # Ensure refresh token cookie set
        cookies = resp.headers.get_all("Set-Cookie")
        self.assertTrue(any("refresh_token" in c for c in cookies))

        # Call refresh endpoint (client preserves cookie)
        r2 = self.client.post("/api/staff/refresh")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("token", r2.get_json())

        # Logout
        # Provide Authorization header with current access token
        token = data.get("token")
        r3 = self.client.post("/api/staff/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.get_json().get("success"), True)

        # After logout, calling refresh should fail
        r4 = self.client.post("/api/staff/refresh")
        self.assertEqual(r4.status_code, 401)


if __name__ == "__main__":
    unittest.main()
