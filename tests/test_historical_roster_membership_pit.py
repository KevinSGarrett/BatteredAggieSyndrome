from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.roster_membership_pit import _disposition, parse_utc


ROOT = Path(__file__).resolve().parents[1]


class HistoricalRosterMembershipPitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs" / "historical_roster_membership_pit_contract.json").read_text(encoding="utf-8"))

    def test_source_known_at_precedes_approved_target_cutoff(self) -> None:
        source = self.contract["source_contract"]
        self.assertLess(parse_utc(source["source_known_at_utc"]), parse_utc(self.contract["acceptance"]["expected_minimum_target_cutoff_utc"]))
        self.assertFalse(self.contract["authority"]["backcast_before_source_known_at"])

    def test_contract_closes_availability_and_protected_authority(self) -> None:
        authority = self.contract["authority"]
        self.assertTrue(authority["pit_state_admission"])
        self.assertTrue(authority["season_membership_only"])
        for key in ("effective_day_inferred", "transfer_order_inferred", "depth_or_starter_inferred", "participation_or_usage_inferred", "availability_or_injury_inferred", "eligibility_inferred", "protected_training_admission", "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication"):
            self.assertFalse(authority[key])

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_only_exact_membership_is_admitted_and_nulls_are_preserved(self) -> None:
        contract = json.loads(json.dumps(self.contract))
        contract["acceptance"].update({"expected_admitted_rows": 1, "expected_nonadmitted_rows": 1, "expected_distinct_players": 1, "expected_distinct_teams": 1, "expected_multi_team_player_seasons": 0, "expected_nonadmitted_dispositions": {"CANDIDATE_VERSIONED_REPOSITORY_ROSTER_SOURCE_LEVEL_ONLY": 1}})
        common = {field: None for field in contract["admission"]["admitted_fields"]}
        common.update({"athlete_id": "1", "canonical_player_id": "p1", "canonical_membership_player_id": "p1", "canonical_team_id": "t1", "canonical_team_label": "Team", "team": "Team", "first_name": "A", "last_name": "B", "season": 2022, "source_commit_sha": "c", "source_known_at_utc": "2023-05-05T03:50:21Z", "athlete_id_occurrence": 0, "canonical_membership_resolution_state": "AUTO_ACCEPTED_VERIFIED", "team_label_exact_match": True, "canonical_membership_option_count": 1, "canonical_membership_exact_team_option_count": 1, "canonical_membership_ambiguous": False})
        rows = [
            {**common, "observation_id": "o1", "reconciliation_disposition": contract["admission"]["eligible_disposition"]},
            {**common, "observation_id": "o2", "canonical_player_id": None, "canonical_membership_player_id": None, "canonical_team_id": None, "reconciliation_disposition": "CANDIDATE_VERSIONED_REPOSITORY_ROSTER_SOURCE_LEVEL_ONLY"},
        ]
        admitted, nonadmitted, validation = _disposition(pl.DataFrame(rows), contract)
        self.assertEqual(admitted.height, 1)
        self.assertEqual(nonadmitted.height, 1)
        self.assertEqual(validation["duplicate_natural_keys"], 0)
        self.assertIsNone(admitted["position"].item())
        self.assertFalse(admitted["game_time_availability"].item())
        self.assertFalse(admitted["protected_eligible"].item())


if __name__ == "__main__":
    unittest.main()
