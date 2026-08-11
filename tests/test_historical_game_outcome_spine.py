from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.data.historical_game_outcome_spine import (
    _classify_sportsdataverse_row,
    _outcome_result,
    _validate_contract_authority,
)


ROOT = Path(__file__).resolve().parents[1]


class HistoricalGameOutcomeSpineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "configs" / "historical_game_outcome_spine_contract.json").read_text(
                encoding="utf-8"
            )
        )

    def test_authority_is_reference_only(self) -> None:
        _validate_contract_authority(self.contract)
        authority = self.contract["authority"]
        self.assertTrue(authority["outcome_reference_use"])
        self.assertTrue(authority["preliminary_outcome_label_candidate"])
        for key in (
            "historical_pit_admission",
            "same_day_chronology_admission",
            "preliminary_feature_direct_admission",
            "protected_training_admission",
            "protected_evaluation_admission",
            "champion_or_production_promotion",
            "forecast_publication",
        ):
            self.assertFalse(authority[key])

    def test_completed_outcome_result_preserves_ties(self) -> None:
        self.assertEqual(_outcome_result(21, 14), "HOME_WIN")
        self.assertEqual(_outcome_result(14, 21), "AWAY_WIN")
        self.assertEqual(_outcome_result(7, 7), "TIE")

    def test_cross_source_final_and_postponed_alias_are_distinct(self) -> None:
        cfbd = {"raw": {"homePoints": 16, "awayPoints": 10}}
        final = {"raw": {"status": "STATUS_FINAL", "home_score": 16, "away_score": 10}}
        postponed = {
            "raw": {"status": "STATUS_POSTPONED", "home_score": 0, "away_score": 0}
        }
        self.assertEqual(
            _classify_sportsdataverse_row(final, cfbd),
            ("CROSS_SOURCE_FINAL_SCORE_EXACT", True),
        )
        self.assertEqual(
            _classify_sportsdataverse_row(postponed, cfbd),
            ("CROSS_SOURCE_POSTPONED_RESCHEDULE_ALIAS", False),
        )

    def test_conflicting_final_and_nonzero_postponed_fail_closed(self) -> None:
        cfbd = {"raw": {"homePoints": 16, "awayPoints": 10}}
        with self.assertRaises(ValueError):
            _classify_sportsdataverse_row(
                {"raw": {"status": "STATUS_FINAL", "home_score": 17, "away_score": 10}},
                cfbd,
            )
        with self.assertRaises(ValueError):
            _classify_sportsdataverse_row(
                {
                    "raw": {
                        "status": "STATUS_POSTPONED",
                        "home_score": 1,
                        "away_score": 0,
                    }
                },
                cfbd,
            )

    def test_provider_derived_postgame_fields_are_forbidden(self) -> None:
        fields = self.contract["fields"]
        configured = set(fields["completed_outcome_fields"]) | set(fields["schedule_only_fields"])
        self.assertFalse(configured & set(fields["forbidden_output_fields"]))
        self.assertIn("homePostgameElo", fields["forbidden_output_fields"])
        self.assertNotIn("homePostgameElo", fields["completed_outcome_fields"])


if __name__ == "__main__":
    unittest.main()
