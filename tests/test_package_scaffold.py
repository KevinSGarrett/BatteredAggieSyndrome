import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import aggie_analytics


class PackageScaffoldTests(unittest.TestCase):
    def test_version_and_maturity_are_explicit(self):
        self.assertEqual(aggie_analytics.__version__, "0.19.0.dev19")
        self.assertEqual(aggie_analytics.__maturity__, "DATA_ENTITY_FEATURE_FUNCTIONAL_STARTER")


if __name__ == "__main__":
    unittest.main()
