from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.architecture.contracts import AsOfContext
from tools.validate_architecture import validate_registry


class ArchitectureContractTests(unittest.TestCase):
    def test_architecture_registry_is_valid(self) -> None:
        registry = json.loads((ROOT / "configs/architecture_registry.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_registry(registry), [])

    def test_asof_context_rejects_future_cutoff(self) -> None:
        prediction = datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            AsOfContext(prediction_timestamp_utc=prediction, data_cutoff_utc=prediction + timedelta(seconds=1))

    def test_asof_context_requires_timezone(self) -> None:
        naive = datetime(2026, 9, 1, 18, 0)
        aware = naive.replace(tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            AsOfContext(prediction_timestamp_utc=aware, data_cutoff_utc=naive)


if __name__ == "__main__":
    unittest.main()
