from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.modeling import schedule_stress_augmented as subject


ROOT = Path(__file__).resolve().parents[1]


class ScheduleStressAblationTests(unittest.TestCase):
    def test_contract_matches_module_and_closes_protected_authority(self) -> None:
        contract = json.loads((ROOT / "configs/preliminary_schedule_stress_ablation_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(subject.CLASSIFICATION, contract["classification"])
        self.assertEqual(list(subject.PROFILE_FIELDS), contract["candidate_profile_fields"])
        self.assertFalse(contract["chronology_policy"]["protected_split_opened"])
        self.assertFalse(any(contract["protected_nonclaims"].values()))

    def test_signed_differences_and_cutoff(self) -> None:
        target = {"target_game_id": "g", "season": 2024, "start_utc": "2024-09-01T00:00:00Z", "cutoff_utc": "2024-08-31T18:00:00Z", "home_team_id": "h", "away_team_id": "a"}
        rows = []
        for role, team, opponent, value in (("HOME", "h", "a", 3.0), ("AWAY", "a", "h", 1.0)):
            row = {"game_id": "g", "team_role": role, "team_id": team, "opponent_team_id": opponent, "cold_start": False, "historical_original_pit_eligible": False, "protected_eligible": False, "event_chronology_eligible": True, "evidence_source_start_utc_max": "2024-08-20T00:00:00Z", "evidence_game_ids_sha256": team * 64, "prior_game_count": 10, "prior_season_game_count": 1}
            row.update({name: value for name in subject.PROFILE_FIELDS})
            rows.append(row)
        built = subject.build_game_profile(target, rows)
        self.assertEqual(2.0, built[subject.DIFFERENCE_FIELDS[0]])
        self.assertFalse(built[subject.PROTECTED_FIELD])


if __name__ == "__main__":
    unittest.main()
