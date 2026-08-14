from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools import build_historical_spine_coverage_matrix as coverage


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(coverage.canonical_json(value) + b"\n")


class HistoricalSpineCoverageMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.data_root = Path(self.temp.name)
        event = {
            "dataset_identity": "e" * 64,
            "population": {
                "target_counts_by_season": {
                    str(season): 100 + season - 2010 for season in coverage.DISCOVERY_SEASONS
                }
            },
        }
        write_json(
            self.data_root
            / "manifests/preliminary_event_chronology/sha256"
            / coverage.EVENT_RUN
            / "run_manifest.json",
            event,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_discovery(self, season: int, *, failures: int, remaining: int = 0) -> Path:
        core = {
            "schema_version": "1.0.0",
            "season": season,
            "state": "COMPLETE_GRAPH_EXHAUSTED" if remaining == 0 else "PARTIAL_MAXIMUM_TEAM_LIMIT_REACHED",
            "team_page_capture_count": 2,
            "team_failure_count": failures,
            "discovered_team_season_ids": ["1", "2"],
            "discovered_contest_ids": ["10", "11", "12"],
            "legacy_schedule_record_count": 0,
            "remaining_queue": [str(100 + index) for index in range(remaining)],
        }
        identity = hashlib.sha256(coverage.canonical_json(core)).hexdigest()
        manifest = {
            **core,
            "discovery_identity": identity,
            "issued_at_utc": "2026-08-12T00:00:00Z",
            "credentials_logged_or_persisted": False,
        }
        path = (
            self.data_root
            / "manifests/acquisition/BAT-554-NCAA-OFFICIAL-BOUNDED-V1/discovery"
            / str(season)
            / "sha256"
            / identity
            / "ncaa_team_graph_discovery_manifest.json"
        )
        write_json(path, manifest)
        return path

    def add_reconciliation(self, season: int) -> Path:
        identity_core = {
            "season": season,
            "population": {
                "captured_team_pages": 20,
                "parsed_team_pages": 19,
                "page_parse_failures": 1,
                "discovered_contests": 30,
                "reconciled_contests": 21,
                "reconciled_team_seasons": 12,
                "scored_schedule_observations": 52,
                "unresolved_contests": 9,
                "legacy_schedule_observations": 10,
                "reconciled_legacy_games": 4,
                "unresolved_legacy_observations": 2,
            },
            "inputs": {
                "discovery_manifest": {"sha256": "d" * 64},
            },
        }
        identity = hashlib.sha256(coverage.canonical_json(identity_core)).hexdigest()
        manifest = {
            "schema_version": "2.0.0",
            "dataset_identity": identity,
            "identity_core": identity_core,
            "unresolved_reason_counts": {
                "PARTICIPANT_ALIAS_NOT_UNIQUELY_RESOLVED": 9,
            },
            "authority": {
                "historical_pit_eligible": False,
                "training_eligible": False,
                "protected_evaluation_eligible": False,
                "production_eligible": False,
            },
        }
        path = (
            self.data_root
            / "manifests/ncaa_contest_reconciliation/sha256"
            / identity
            / "run_manifest.json"
        )
        write_json(path, manifest)
        return path

    def add_inflated_legacy_reconciliation(self, season: int) -> Path:
        path = self.add_reconciliation(season)
        item = json.loads(path.read_text(encoding="utf-8"))
        item["identity_core"]["population"]["unresolved_legacy_observations"] = 1000
        identity = hashlib.sha256(coverage.canonical_json(item["identity_core"])).hexdigest()
        item["dataset_identity"] = identity
        inflated = path.parents[1] / identity / "run_manifest.json"
        write_json(inflated, item)
        return inflated

    def test_graph_exhaustion_with_failures_is_not_capture_complete(self) -> None:
        self.add_discovery(2024, failures=0)
        self.add_discovery(2025, failures=2)

        payload = coverage.build_matrix(self.data_root)

        self.assertEqual(payload["schema_version"], "1.3.0")
        self.assertEqual(payload["discovery_summary"]["capture_complete_seasons"], [2024])
        self.assertEqual(
            payload["discovery_summary"]["graph_exhausted_with_quarantined_failures"],
            [2025],
        )
        row = next(
            item
            for item in payload["rows"]
            if item["season"] == 2025 and item["domain"] == "OFFICIAL_CONTEST_DISCOVERY"
        )
        self.assertEqual(row["coverage_state"], "GRAPH_EXHAUSTED_WITH_QUARANTINED_FAILURES")
        self.assertEqual(row["team_failure_count"], 2)
        self.assertEqual(row["eligibility_tiers"], [])
        self.assertIn("contest coverage is partial", row["missingness"])

    def test_partial_graph_preserves_remaining_queue(self) -> None:
        self.add_discovery(2023, failures=0, remaining=7)

        payload = coverage.build_matrix(self.data_root)
        row = next(
            item
            for item in payload["rows"]
            if item["season"] == 2023 and item["domain"] == "OFFICIAL_CONTEST_DISCOVERY"
        )
        self.assertEqual(row["coverage_state"], "PARTIAL_GRAPH_WITH_REMAINING_QUEUE")
        self.assertEqual(row["remaining_queue"], 7)
        self.assertIn(2023, payload["discovery_summary"]["partial_graph_seasons"])

    def test_tampered_discovery_manifest_fails_closed(self) -> None:
        path = self.add_discovery(2024, failures=0)
        item = json.loads(path.read_text(encoding="utf-8"))
        item["discovered_contest_ids"].append("13")
        write_json(path, item)

        with self.assertRaisesRegex(ValueError, "content identity mismatch"):
            coverage.select_strongest_discovery(self.data_root, 2024)

    def test_reconciliation_is_independent_candidate_only_domain(self) -> None:
        self.add_discovery(2022, failures=0)
        self.add_reconciliation(2022)

        payload = coverage.build_matrix(self.data_root)
        row = next(
            item
            for item in payload["rows"]
            if item["season"] == 2022 and item["domain"] == "CANONICAL_CONTEST_RECONCILIATION"
        )
        self.assertEqual(payload["discovery_summary"]["reconciled_seasons"], [2022])
        self.assertEqual(row["reconciled_contests"], 21)
        self.assertEqual(row["reconciled_legacy_games"], 4)
        self.assertEqual(row["canonical_games"], 25)
        self.assertEqual(row["unresolved_contests"], 9)
        self.assertEqual(row["eligibility_tiers"], [])
        self.assertFalse(row["authority"]["training_eligible"])
        self.assertIn("NO_NAME_ONLY_PROMOTION", row["reconciliation_quality"])

    def test_tampered_reconciliation_manifest_fails_closed(self) -> None:
        path = self.add_reconciliation(2022)
        item = json.loads(path.read_text(encoding="utf-8"))
        item["identity_core"]["population"]["reconciled_contests"] += 1
        write_json(path, item)

        with self.assertRaisesRegex(ValueError, "content identity mismatch"):
            coverage.select_strongest_reconciliation(self.data_root, 2022)

    def test_reconciliation_selection_penalizes_spurious_legacy_duplicates(self) -> None:
        correct = self.add_reconciliation(2018)
        self.add_inflated_legacy_reconciliation(2018)

        selected, _ = coverage.select_strongest_reconciliation(self.data_root, 2018)

        self.assertEqual(selected, correct)


if __name__ == "__main__":
    unittest.main()
