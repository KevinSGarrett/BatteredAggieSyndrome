from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.action_play_summary import classify_summary_pair, stable_hash


def source_row(subtype: str, *, play_number: int = 7, drive_number: int | None = 2) -> dict:
    action_id = 101 if subtype == "start" else 102
    action = {
        "id": action_id,
        "game_id": 55,
        "game_period_id": 3,
        "period_number": 1,
        "play_number": play_number,
        "play_by_play_text": "Runner gains four yards.",
        "game_drive_id": 88,
        "game_drive_number": drive_number,
        "down_no": 1,
        "location": "TAMU25",
        "context": "H,1,10,H25",
        "yard_line": 25,
        "yards_to_go": 10,
        "home_score": 0,
        "visitor_score": 0,
        "scoring_play": False,
        "play_action_type": "play",
        "play_action_sub_type": subtype,
        "play_by_play_id": None if subtype == "start" else 101,
    }
    return {
        "season": 2014,
        "wmt_game_id": "55",
        "boxscore_id": "box55",
        "game_date": "2014-09-01T00:00:00.000Z",
        "game_date_utc": None,
        "record_id": f"record-{subtype}",
        "record_ordinal": 1 if subtype == "start" else 2,
        "normalized_record_json": json.dumps({"action": action}, sort_keys=True),
        "source_json_pointer": f"$.actions[{0 if subtype == 'start' else 1}]",
        "source_record_sha256": ("a" if subtype == "start" else "b") * 64,
        "source_record_evidence_sha256": ("c" if subtype == "start" else "d") * 64,
        "source_response_sha256": "e" * 64,
        "source_capture_id": "cap-55",
        "source_capture_manifest_path": "manifests/captures/source.json",
        "historical_known_at_state": "UNKNOWN_EXACT_HISTORICAL_PUBLICATION_TIME_POSTGAME_EVIDENCE_ONLY",
    }


class ActionPlaySummaryTests(unittest.TestCase):
    def test_valid_pair_becomes_candidate_without_downstream_authority(self) -> None:
        disposition, row = classify_summary_pair(source_row("start"), source_row("end"))
        self.assertEqual("CANDIDATE", disposition)
        self.assertEqual("GAME_PERIOD_PLAY_NUMBER_ACTION_DERIVED_SUMMARY", row["grain"])
        self.assertEqual("Runner gains four yards.", row["play_text"])
        self.assertFalse(row["native_play_collection_present"])
        self.assertFalse(row["historical_known_at_eligible"])
        self.assertFalse(row["feature_or_training_admission"])
        declared = row["row_lineage_sha256"]
        core = dict(row)
        core.pop("row_lineage_sha256")
        self.assertEqual(stable_hash(core), declared)

    def test_nonpositive_play_number_is_preserved_as_exclusion(self) -> None:
        disposition, row = classify_summary_pair(
            source_row("start", play_number=0), source_row("end", play_number=0)
        )
        self.assertEqual("EXCLUDED", disposition)
        self.assertIn("PLAY_NUMBER_NOT_POSITIVE", row["reason_codes"])
        self.assertFalse(row["canonical_admission"])

    def test_missing_drive_is_not_imputed(self) -> None:
        disposition, row = classify_summary_pair(
            source_row("start", drive_number=None), source_row("end", drive_number=None)
        )
        self.assertEqual("EXCLUDED", disposition)
        self.assertIn("DRIVE_NUMBER_MISSING", row["reason_codes"])

    def test_broken_pair_link_is_rejected(self) -> None:
        end = source_row("end")
        payload = json.loads(end["normalized_record_json"])
        payload["action"]["play_by_play_id"] = 999
        end["normalized_record_json"] = json.dumps(payload, sort_keys=True)
        disposition, row = classify_summary_pair(source_row("start"), end)
        self.assertEqual("EXCLUDED", disposition)
        self.assertIn("END_NOT_LINKED_TO_START", row["reason_codes"])

    def test_missing_pair_member_is_explicit(self) -> None:
        disposition, row = classify_summary_pair(source_row("start"), None)
        self.assertEqual("EXCLUDED", disposition)
        self.assertIn("END_RECORD_MISSING", row["reason_codes"])


if __name__ == "__main__":
    unittest.main()
