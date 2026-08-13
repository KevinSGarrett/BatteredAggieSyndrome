from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from aggie_analytics.data.ncaa_contest_outcome_reference_adapter import _write_json_immutable


ROOT = Path(__file__).resolve().parents[1]


class NcaaContestOutcomeReferenceAdapterTests(unittest.TestCase):
    def test_contract_is_schema_only_and_fail_closed(self) -> None:
        contract = json.loads((ROOT / "configs/ncaa_contest_outcome_reference_adapter_contract.json").read_text(encoding="utf-8"))
        self.assertTrue(contract["authority"]["schema_adapter_materialization"])
        for key, value in contract["authority"].items():
            if key != "schema_adapter_materialization":
                self.assertFalse(value, key)
        self.assertEqual(contract["acceptance"]["expected_rows"], 46957)
        self.assertEqual(contract["field_map"]["canonical_game_id"], "target_game_id")
        self.assertEqual(contract["field_map"]["start_time_utc"], "start_utc")

    def test_manifest_write_is_immutable_and_collision_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sha256" / "manifest.json"
            _write_json_immutable({"identity": "first"}, path)
            original = path.read_bytes()

            _write_json_immutable({"identity": "first"}, path)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, "immutable adapter manifest collision"):
                _write_json_immutable({"identity": "different"}, path)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
