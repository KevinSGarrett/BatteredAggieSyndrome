from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.modeling import sustainability_augmented as subject



ROOT = Path(__file__).resolve().parents[1]


def profile(role: str, team: str, opponent: str) -> dict[str, object]:
    row: dict[str, object] = {
        "classification": subject.CLASSIFICATION,
        "game_id": "g1",
        "team_role": role,
        "team_id": team,
        "opponent_team_id": opponent,
        "authority": "DEVELOPMENT_ONLY_RETROSPECTIVE",
        "protected_eligible": False,
        "historical_original_pit_eligible": False,
        "cold_start": False,
        "source_known_at_utc_max": "2023-05-06T07:52:16Z",
    }
    for index, name in enumerate(subject.PROFILE_FIELDS, 1):
        row[name] = float(index)
    for index, name in enumerate(subject.DIAGNOSTIC_SOURCE_FIELDS, 1):
        row[name] = float(index * 10)
    return row


class SustainabilityAblationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target = {
            "target_game_id": "g1",
            "season": 2024,
            "start_utc": "2024-09-01T00:00:00Z",
            "cutoff_utc": "2024-08-31T18:00:00Z",
            "home_team_id": "home",
            "away_team_id": "away",
        }

    def test_contract_preserves_exposure_and_nonclaim_boundaries(self) -> None:
        contract = json.loads(
            (ROOT / "configs/preliminary_sustainability_ablation_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(subject.CLASSIFICATION, contract["classification"])
        self.assertEqual(list(subject.PROFILE_FIELDS), contract["candidate_profile_fields"])
        self.assertFalse(contract["chronology_policy"]["protected_split_opened"])
        self.assertFalse(any(contract["protected_nonclaims"].values()))
        self.assertIn("2024-2025", contract["limitations"][1])

    def test_builds_signed_common_support_differences(self) -> None:
        home = profile("HOME", "home", "away")
        away = profile("AWAY", "away", "home")
        away[subject.PROFILE_FIELDS[0]] = -2.0
        built = subject.build_game_profile(self.target, [away, home])
        self.assertEqual(3.0, built[subject.DIFFERENCE_FIELDS[0]])
        self.assertEqual(0.0, built[subject.DIFFERENCE_FIELDS[1]])
        self.assertFalse(built[subject.PROTECTED_FIELD])
        self.assertEqual("2023-05-06T07:52:16Z", built[subject.SOURCE_KNOWN_AT_FIELD])
        self.assertEqual(64, len(built[subject.LINEAGE_FIELD]))

    def test_missing_close_game_evidence_stays_missing(self) -> None:
        home = profile("HOME", "home", "away")
        away = profile("AWAY", "away", "home")
        home["recent_close_win_share_minus_overall"] = None
        built = subject.build_game_profile(self.target, [home, away])
        self.assertIsNone(
            built["sustainability_recent_close_win_share_minus_overall_diff"]
        )

    def test_rejects_post_cutoff_or_protected_evidence(self) -> None:
        home = profile("HOME", "home", "away")
        away = profile("AWAY", "away", "home")
        home["source_known_at_utc_max"] = "2025-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "after target cutoff"):
            subject.build_game_profile(self.target, [home, away])
        home["source_known_at_utc_max"] = "2023-05-06T07:52:16Z"
        away["protected_eligible"] = True
        with self.assertRaisesRegex(ValueError, "protected authority"):
            subject.build_game_profile(self.target, [home, away])

    def test_cold_start_never_fabricates_values(self) -> None:
        home = profile("HOME", "home", "away")
        away = profile("AWAY", "away", "home")
        away["cold_start"] = True
        away["authority"] = None
        away["source_known_at_utc_max"] = None
        for name in subject.PROFILE_FIELDS:
            away[name] = None
        built = subject.build_game_profile(self.target, [home, away])
        self.assertEqual(1.0, built["away_profile_cold_start"])
        self.assertTrue(all(built[name] is None for name in subject.DIFFERENCE_FIELDS))

    def test_frozen_reference_direction_rejects_mixed_effect(self) -> None:
        comparison = {
            "candidate": {
                "2023": {"brier_delta_candidate_minus_frozen": 0.0},
                "2024": {"brier_delta_candidate_minus_frozen": -0.01},
                "2025": {"brier_delta_candidate_minus_frozen": 0.02},
            }
        }
        direction, decision, reference = subject.empirical_direction_from_comparisons(
            {}, comparison
        )
        self.assertEqual("MIXED_SEASON_OR_METRIC_DIRECTION", direction)
        self.assertEqual("REJECT_UNSTABLE_MIXED_SEASON_EFFECT", decision)
        self.assertEqual("UNCHANGED_FROZEN_BASELINE", reference)

    def test_pure_python_metrics_match_known_values(self) -> None:
        probability = subject.probability_metrics([0.0, 1.0], [0.25, 0.75])
        self.assertAlmostEqual(0.0625, probability["brier"])
        self.assertAlmostEqual(-__import__("math").log(0.75), probability["log_loss"])
        margin = subject.margin_metrics([1.0, -1.0], [2.0, 1.0])
        self.assertEqual(1.5, margin["mae"])
        self.assertAlmostEqual((2.5) ** 0.5, margin["rmse"])


if __name__ == "__main__":
    unittest.main()
