from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.team_membership_pit import _admit, _transition_count, parse_utc

ROOT = Path(__file__).resolve().parents[1]


class HistoricalTeamMembershipPitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs" / "historical_team_membership_pit_contract.json").read_text(encoding="utf-8"))

    def test_chronology_and_authority_are_bounded(self) -> None:
        self.assertLess(parse_utc(self.contract["source_contract"]["source_known_at_utc"]), parse_utc(self.contract["acceptance"]["expected_minimum_target_cutoff_utc"]))
        authority = self.contract["authority"]
        self.assertTrue(authority["team_season_membership_only"])
        for key in ("backcast_before_source_known_at", "effective_day_inferred", "conference_or_division_imputed", "venue_or_capacity_inferred", "branding_effective_time_inferred", "protected_training_admission", "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication"):
            self.assertFalse(authority[key])

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_exact_membership_preserves_null_division_and_excludes_branding(self) -> None:
        contract = json.loads(json.dumps(self.contract)); contract["acceptance"].update({"expected_admitted_rows": 1, "expected_source_rows": 1, "expected_distinct_teams": 1, "expected_conference_nulls": 0, "expected_division_nulls": 1, "expected_transitions": 0})
        row = {field: None for field in contract["admission"]["admitted_fields"]}; row.update({"observation_id": "o1", "season": 2020, "source_team_id": "1", "canonical_team_id": "t1", "school": "Team", "conference": "League", "division": None, "canonical_resolution_state": "AUTO_ACCEPTED_VERIFIED", "canonical_source_id_option_count": 1, "venue_fields_present": False, "reconciliation_disposition": contract["admission"]["eligible_disposition"]})
        admitted, validation = _admit(pl.DataFrame([row]), contract)
        self.assertEqual(validation["division_nulls"], 1); self.assertIsNone(admitted["division"].item()); self.assertFalse(admitted["venue_or_capacity_truth"].item()); self.assertNotIn("mascot", admitted.columns)

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_transition_count_preserves_conference_and_division_changes(self) -> None:
        frame = pl.DataFrame({"canonical_team_id": ["t", "t", "t"], "season": [2010, 2011, 2012], "conference": ["A", "A", "B"], "division": [None, "East", "East"]})
        self.assertEqual(_transition_count(frame), 2)


if __name__ == "__main__": unittest.main()
