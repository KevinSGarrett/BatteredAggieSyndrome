from __future__ import annotations

import json
import unittest
from pathlib import Path

from aggie_analytics.assistive_plane.schemas import validate_strict_schema


ROOT = Path(__file__).resolve().parents[1]


class LocalQwenQualificationTests(unittest.TestCase):
    def test_candidate_schema_is_strict(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/assistive/local_qwen_candidate.schema.json").read_text(encoding="utf-8")
        )
        validate_strict_schema(schema)

    def test_failed_models_are_not_admitted(self) -> None:
        summary = json.loads(
            (ROOT / "artifacts/assistive/local_qwen_qualification.json").read_text(encoding="utf-8")
        )
        self.assertEqual(summary["qualification_disposition"], "EMPIRICALLY_REJECTED_NO_OPERATIONAL_ROUTE")
        self.assertFalse(summary["acceptance_decision"]["operational_route_ready"])
        self.assertEqual(summary["acceptance_decision"]["admitted_models"], [])
        self.assertEqual(summary["aggregate"]["canonical_writes"], 0)
        self.assertEqual(summary["aggregate"]["protected_decisions"], 0)
        self.assertEqual(summary["aggregate"]["provider_calls"], 36)

    def test_each_run_preserves_failure_and_cleanup(self) -> None:
        summary = json.loads(
            (ROOT / "artifacts/assistive/local_qwen_qualification.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(summary["runs"]), 3)
        for run in summary["runs"]:
            self.assertEqual(run["result"], "FAIL_PRESERVE_NEGATIVE_EVIDENCE")
            self.assertTrue(run["metrics"]["unload_succeeded"])
            self.assertGreater(run["metrics"]["unsupported_fact_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
