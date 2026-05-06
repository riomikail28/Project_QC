import unittest
import json
from backend.app import create_app

class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_health_check(self):
        response = self.client.get('/api/qc/dashboard')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('health_score', data)

    def test_temperature_history(self):
        response = self.client.get('/api/temperature/history')
        self.assertEqual(response.status_code, 200)

    def test_batch_list(self):
        response = self.client.get('/api/batch/list')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
