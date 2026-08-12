from __future__ import annotations

import json
import unittest
from pathlib import Path

from aggie_analytics.assistive_plane.schemas import validate_strict_schema
from tools.run_local_coder_shadow import evaluate
from tools.run_local_embedding_shadow import cosine


ROOT = Path(__file__).resolve().parents[1]


class LocalQwenQualificationTests(unittest.TestCase):
    def test_candidate_schema_is_strict(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/assistive/local_qwen_candidate.schema.json").read_text(encoding="utf-8")
        )
        validate_strict_schema(schema)

    def test_local_coder_schema_and_allowed_patch_paths_fail_closed(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/assistive/local_coder_shadow.schema.json").read_text(encoding="utf-8")
        )
        validate_strict_schema(schema)
        packet = {
            "task_id": "bounded",
            "task_type": "TEST_GENERATION",
            "allowed_paths": ["tests/allowed.py"],
            "expected_terms": ["replay"],
            "patch_required": True,
        }
        output = {
            "task_id": "bounded",
            "task_type": "TEST_GENERATION",
            "disposition": "CANDIDATE",
            "summary": "replay test",
            "findings": [{"claim": "supported", "evidence_quote": "L001: replay", "severity": "LOW"}],
            "proposed_paths": ["tests/allowed.py"],
            "patch": "--- a/tests/forbidden.py\n+++ b/tests/forbidden.py\n@@ -1 +1 @@\n-old\n+new",
            "recommended_tests": ["targeted"],
            "unsupported_facts": [],
        }
        result = evaluate(packet, output, "L001: replay")
        self.assertFalse(result["allowed_paths_valid"])
        self.assertEqual("QUARANTINE_OR_REVIEW", result["disposition"])

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

    def test_coder_shadow_failure_is_exact_and_not_promoted(self) -> None:
        summary = json.loads(
            (ROOT / "artifacts/assistive/local_qwen_qualification.json").read_text(encoding="utf-8")
        )
        shadow = summary["shadow_qualifications"][0]
        self.assertEqual("FAIL_PRESERVE_NEGATIVE_EVIDENCE_EXACT_ROUTE_NOT_READY", shadow["result"])
        self.assertEqual(0, shadow["metrics"]["accepted_shadow_candidates"])
        readiness = json.loads(
            (ROOT / "configs/assistive_route_readiness.json").read_text(encoding="utf-8")
        )
        route = next(item for item in readiness["routes"] if item["model_digest"] == shadow["model_digest"])
        self.assertEqual("NOT_READY", route["state"])
        self.assertEqual(shadow["evaluation_sha256"], route["evidence_sha256"])

    def test_embedding_similarity_requires_matching_nonzero_dimensions(self) -> None:
        self.assertAlmostEqual(1.0, cosine([1.0, 2.0], [1.0, 2.0]))
        with self.assertRaisesRegex(ValueError, "EMBEDDING_DIMENSION_INVALID"):
            cosine([1.0], [1.0, 2.0])
        with self.assertRaisesRegex(ValueError, "EMBEDDING_ZERO_NORM"):
            cosine([0.0, 0.0], [1.0, 2.0])

    def test_embedding_route_is_narrowly_ready_without_rehabilitating_other_routes(self) -> None:
        summary = json.loads(
            (ROOT / "artifacts/assistive/local_qwen_qualification.json").read_text(encoding="utf-8")
        )
        self.assertEqual(0, summary["current_route_summary"]["evidence_critical_routes_ready"])
        self.assertEqual(0, summary["current_route_summary"]["coding_routes_ready"])
        self.assertEqual(1, summary["current_route_summary"]["embedding_candidate_routes_ready"])
        self.assertFalse(summary["current_route_summary"]["generalization_across_models_or_formats"])


if __name__ == "__main__":
    unittest.main()
