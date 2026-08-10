from __future__ import annotations

import csv
import hashlib
import json
import tomllib
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs" / "open_source_integration_registry.json"
MATRIX = ROOT / "artifacts" / "open_source" / "repository_review_decisions.csv"


class OpenSourceIntegrationRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.records = cls.payload["records"]

    def test_every_supplied_repository_has_one_reviewed_disposition(self) -> None:
        self.assertEqual(42, self.payload["candidate_count"])
        self.assertEqual(42, len(self.records))
        self.assertEqual(42, len({record["candidate_id"] for record in self.records}))
        self.assertEqual(42, len({record["requested_repository"] for record in self.records}))
        allowed = {
            "ADOPT_NOW",
            "ADAPT_NOW",
            "ADOPT_AT_DEPENDENCY",
            "ADAPT_AT_DEPENDENCY",
            "DEFER_CONDITIONAL",
            "REFERENCE_ONLY",
            "REJECT_NOT_FIT",
        }
        self.assertEqual(allowed, {record["decision"] for record in self.records})
        self.assertEqual(
            self.payload["decision_counts"],
            dict(sorted(Counter(record["decision"] for record in self.records).items())),
        )

    def test_each_record_is_pinned_actionable_and_private(self) -> None:
        for record in self.records:
            with self.subTest(repository=record["requested_repository"]):
                self.assertRegex(record["reviewed_commit"], r"^[0-9a-f]{40}$")
                self.assertGreater(record["repository_evidence"]["tree_entries"], 0)
                self.assertGreater(record["repository_evidence"]["representative_files_captured"], 0)
                self.assertTrue(record["rationale"])
                self.assertTrue(record["risk_and_constraint"])
                self.assertTrue(record["current_action"])
                self.assertEqual("ALLOWED", record["private_research_acquisition"])
                self.assertEqual("DENIED", record["raw_third_party_publication"])
                if record["decision"].startswith(("ADOPT", "ADAPT")):
                    self.assertTrue(record["integration_boundary"])
                    self.assertTrue(record["empirical_admission_gate"])

    def test_machine_registry_and_human_matrix_are_exactly_aligned(self) -> None:
        with MATRIX.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        expected = {(record["candidate_id"], record["requested_repository"], record["decision"]) for record in self.records}
        actual = {(row["candidate_id"], row["requested_repository"], row["decision"]) for row in rows}
        self.assertEqual(expected, actual)

    def test_immediate_runtime_dependencies_are_exactly_pinned(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        extras = pyproject["project"]["optional-dependencies"]
        required_groups = {
            "data",
            "entity-resolution",
            "source-clients",
            "sportsdataverse",
            "modeling",
            "evaluation",
            "experimentation",
            "test",
        }
        self.assertTrue(required_groups.issubset(extras))
        for group in required_groups:
            self.assertTrue(extras[group])
            self.assertTrue(all("==" in requirement for requirement in extras[group]))
        self.assertIn("sportsdataverse==0.0.75", extras["sportsdataverse"])
        self.assertIn("xgboost==3.2.0", extras["sportsdataverse"])
        self.assertNotIn("sportsdataverse==0.0.75", extras.get("data", ()))

    def test_high_value_negative_and_isolation_decisions_are_preserved(self) -> None:
        by_repo = {record["canonical_repository"]: record for record in self.records}
        self.assertEqual("ADAPT_NOW", by_repo["sportsdataverse/sportsdataverse-py"]["decision"])
        self.assertIn("isolated", by_repo["sportsdataverse/sportsdataverse-py"]["integration_boundary"].lower())
        self.assertEqual("REJECT_NOT_FIT", by_repo["chrispm15/AggieFYI"]["decision"])
        self.assertIn("no unique", by_repo["chrispm15/AggieFYI"]["rationale"].lower())

    def test_validation_manifest_binds_every_versioned_output(self) -> None:
        manifest = json.loads(
            (ROOT / "artifacts" / "open_source" / "integration_validation_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(42, manifest["scope"]["repository_candidates"])
        self.assertFalse(manifest["protected_claims"]["production_model_promoted"])
        for output in manifest["versioned_outputs"]:
            path = ROOT / output["path"]
            with self.subTest(path=output["path"]):
                self.assertTrue(path.is_file())
                self.assertEqual(output["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
