from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.play_drive import (
    normalize_drive_candidate,
    normalize_play_candidate,
    stable_hash,
)


CONTEXT = {
    "source_request_id": "req_test",
    "source_capture_id": "cap_test",
    "source_response_sha256": "a" * 64,
    "source_immutable_path": "raw/SRC-002/plays/example.json",
    "source_row_number": 0,
    "source_retrieved_at_utc": "2026-08-09T00:00:00Z",
    "source_capture_known_at_utc": "2026-08-09T00:00:00Z",
    "source_season_type": "regular",
}


class SupplementalPlayDriveTests(unittest.TestCase):
    def test_exact_play_requires_canonical_game_and_drive_link(self) -> None:
        raw = {
            "id": "p1", "gameId": 10, "driveId": "d1", "clock": {"minutes": 4, "seconds": 2},
            "period": 2, "playText": "Run", "scoring": False, "ppa": 0.5,
        }
        row = normalize_play_candidate(
            season=2023, raw=raw, canonical_game_id="game_10",
            known_drive_ids={"d1"}, source_context=CONTEXT,
        )
        self.assertEqual("CANDIDATE_EXACT_CANONICAL_GAME_AND_DRIVE", row["reconciliation_disposition"])
        self.assertFalse(row["quarantined"])
        self.assertFalse(row["historical_known_at_eligible"])
        declared = row["row_lineage_sha256"]
        core = dict(row); core.pop("row_lineage_sha256")
        self.assertEqual(stable_hash(core), declared)

    def test_play_missing_drive_link_is_quarantined(self) -> None:
        row = normalize_play_candidate(
            season=2020, raw={"id": "p1", "gameId": 10, "driveId": "d1"},
            canonical_game_id="game_10", known_drive_ids=set(), source_context=CONTEXT,
        )
        self.assertEqual("QUARANTINE_DRIVE_LINK_MISSING", row["reconciliation_disposition"])
        self.assertTrue(row["quarantined"])

    def test_missing_canonical_game_is_never_name_mapped(self) -> None:
        row = normalize_play_candidate(
            season=2020, raw={"id": "p1", "gameId": 10, "driveId": "d1", "home": "Texas A&M"},
            canonical_game_id=None, known_drive_ids={"d1"}, source_context=CONTEXT,
        )
        self.assertEqual("QUARANTINE_CANONICAL_GAME_ID_MISSING", row["reconciliation_disposition"])
        self.assertIsNone(row["canonical_game_id"])

    def test_drive_without_play_rows_remains_explicit_partial_candidate(self) -> None:
        context = dict(CONTEXT); context["source_immutable_path"] = "raw/SRC-002/drives/example.json"
        row = normalize_drive_candidate(
            season=2020, raw={"id": "d1", "gameId": 10, "driveResult": "PUNT"},
            canonical_game_id="game_10", play_linked_drive_ids=set(), source_context=context,
        )
        self.assertEqual(
            "CANDIDATE_EXACT_CANONICAL_GAME_DRIVE_WITHOUT_PLAY_ROWS",
            row["reconciliation_disposition"],
        )
        self.assertFalse(row["quarantined"])
        self.assertFalse(row["play_rows_present"])

    def test_invalid_core_is_quarantined_and_authority_stays_closed(self) -> None:
        context = dict(CONTEXT); context["source_immutable_path"] = "raw/SRC-002/drives/example.json"
        row = normalize_drive_candidate(
            season=2011, raw={"gameId": 10}, canonical_game_id="game_10",
            play_linked_drive_ids=set(), source_context=context,
        )
        self.assertEqual("QUARANTINE_INVALID_DRIVE_CORE", row["reconciliation_disposition"])
        self.assertTrue(row["quarantined"])
        self.assertFalse(row["canonical_or_pit_admission"])
        self.assertFalse(row["feature_or_training_admission"])
        self.assertFalse(row["protected_use_admission"])


if __name__ == "__main__":
    unittest.main()
