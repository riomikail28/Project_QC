import unittest

from backend.services.qc_engine import calculate_health_score, determine_overall_status, validate_temperature


class TestQCEngine(unittest.TestCase):
    def test_chiller_validation(self):
        self.assertEqual(validate_temperature("chiller", 3.0), "PASS")
        self.assertEqual(validate_temperature("chiller", 6.0), "WARNING")
        self.assertEqual(validate_temperature("chiller", 9.0), "FAIL")

    def test_freezer_validation(self):
        self.assertEqual(validate_temperature("freezer", -20.0), "PASS")
        self.assertEqual(validate_temperature("freezer", -12.0), "WARNING")
        self.assertEqual(validate_temperature("freezer", -9.0), "FAIL")

    def test_overall_status(self):
        self.assertEqual(determine_overall_status("PASS", "WARNING"), "WARNING")
        self.assertEqual(determine_overall_status("PASS", "FAIL"), "FAIL")

    def test_health_score(self):
        self.assertEqual(calculate_health_score(4, 2, 2), 75.0)


if __name__ == "__main__":
    unittest.main()
