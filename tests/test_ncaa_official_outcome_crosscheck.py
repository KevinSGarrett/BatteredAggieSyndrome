from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from aggie_analytics.data.ncaa_official_outcome_crosscheck import (
    _validate_authority,
    _write_immutable,
    compare_mapping,
)


ROOT = Path(__file__).resolve().parents[1]


def mapping() -> dict[str, object]:
    return {
        "season": 2023,
        "season_type": "regular",
        "canonical_game_id": "game-1",
        "ncaa_contest_id": "123",
        "canonical_home_team_id": "home-1",
        "canonical_away_team_id": "away-1",
        "canonical_home_points": 24,
        "canonical_away_points": 20,
        "mapping_method": "TWO_SIDED_EXACT_PARTICIPANTS_DATE_SCORE_CONTEXT",
        "name_only_promotion": False,
    }


def payload(home: int = 24, away: int = 20) -> dict[str, object]:
    records = [
        {"home_away": "away", "team": "Away", "period": "1", "points": away, "final": away},
        {"home_away": "home", "team": "Home", "period": "1", "points": home, "final": home},
    ]
    return {
        "payload": {
            "records": records,
            "normalization_identity": "a" * 64,
            "source_raw_sha256": "b" * 64,
            "source_uri": "https://stats.ncaa.org/contests/123/box_score",
        },
        "evidence": {"payload_sha256": "c" * 64},
    }


class NcaaOfficialOutcomeCrosscheckTests(unittest.TestCase):
    def test_contract_keeps_all_non_postgame_authority_closed(self) -> None:
        contract = json.loads((ROOT / "configs/ncaa_official_outcome_crosscheck_contract.json").read_text(encoding="utf-8"))
        _validate_authority(contract)
        self.assertEqual(contract["acceptance"]["expected_mapping_rows"], 1536)
        changed = json.loads(json.dumps(contract))
        changed["authority"]["training_admission"] = True
        with self.assertRaisesRegex(ValueError, "authority is open"):
            _validate_authority(changed)

    def test_comparison_partitions_agreement_conflict_and_missing(self) -> None:
        agreed = compare_mapping(mapping(), payload())
        self.assertEqual(agreed["status"], "AGREEMENT")
        conflict = compare_mapping(mapping(), payload(home=23, away=24))
        self.assertEqual(conflict["status"], "CONFLICT_FINAL_SCORE")
        missing = compare_mapping(mapping(), None)
        self.assertEqual(missing["status"], "MISSING_OFFICIAL_LINESCORE")
        self.assertIsNone(missing["official_home_points"])

    def test_invalid_period_sum_is_not_promoted(self) -> None:
        bundle = payload()
        bundle["payload"]["records"][0]["points"] = 19
        result = compare_mapping(mapping(), bundle)
        self.assertEqual(result["status"], "INVALID_OFFICIAL_LINESCORE")
        self.assertFalse(result["training_eligible"])

    def test_immutable_writer_replays_and_rejects_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.jsonl"
            _write_immutable(path, b"first\n")
            _write_immutable(path, b"first\n")
            with self.assertRaisesRegex(ValueError, "immutable cross-check collision"):
                _write_immutable(path, b"second\n")


if __name__ == "__main__":
    unittest.main()
