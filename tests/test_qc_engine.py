import unittest
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.service.qc_engine import QCEngine

class TestQCEngine(unittest.TestCase):
    def setUp(self):
        self.engine = QCEngine()

    def test_chiller_validation(self):
        # Chiller SOP: 0 - 5
        self.assertEqual(self.engine.validate_temp('Chiller Kitchen', 3.0), 'PASS')
        self.assertEqual(self.engine.validate_temp('Chiller Kitchen', 6.0), 'FAIL')
        self.assertEqual(self.engine.validate_temp('Chiller Kitchen', -1.0), 'FAIL')

    def test_freezer_validation(self):
        # Freezer SOP: <= -18
        self.assertEqual(self.engine.validate_temp('Freezer Central', -20.0), 'PASS')
        self.assertEqual(self.engine.validate_temp('Freezer Central', -10.0), 'FAIL')

if __name__ == '__main__':
    unittest.main()
