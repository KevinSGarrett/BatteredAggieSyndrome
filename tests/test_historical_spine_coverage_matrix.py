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

    def test_graph_exhaustion_with_failures_is_not_capture_complete(self) -> None:
        self.add_discovery(2024, failures=0)
        self.add_discovery(2025, failures=2)

        payload = coverage.build_matrix(self.data_root)

        self.assertEqual(payload["schema_version"], "1.1.0")
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


if __name__ == "__main__":
    unittest.main()
