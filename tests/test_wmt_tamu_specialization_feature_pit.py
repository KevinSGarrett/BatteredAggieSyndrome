from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.wmt_tamu_specialization_feature_pit import (
    _assert_output_boundary,
    _build_tamu_identity_map,
    _build_target_features,
    _domain_metrics,
    _record_is_tamu,
)


ROOT = Path(__file__).resolve().parents[1]


class WmtTamuSpecializationFeaturePitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "configs" / "wmt_tamu_specialization_feature_pit_contract.json").read_text(encoding="utf-8")
        )

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_identity_requires_exactly_one_official_school_id(self) -> None:
        rows = []
        for ordinal, school_id in enumerate((697, 123), start=1):
            value = {"schoolId": school_id, "id": 100 + ordinal, "teamId": 200 + ordinal, "homeContest": ordinal == 1}
            rows.append(
                {
                    "season": 2020,
                    "wmt_game_id": "game-1",
                    "game_date": "2020-09-01T00:00:00Z",
                    "record_id": f"record-{ordinal}",
                    "source_record_sha256": str(ordinal) * 64,
                    "normalized_record_json": json.dumps(value),
                }
            )
        contract = json.loads(json.dumps(self.contract))
        contract["acceptance"]["expected_identity_games"] = 1
        contract["acceptance"]["expected_competitor_rows"] = 2
        frame, mapping = _build_tamu_identity_map(pl.DataFrame(rows), contract)
        self.assertEqual(frame.height, 1)
        self.assertEqual(mapping["game-1"]["wmt_tamu_competitor_id"], "101")
        self.assertFalse(mapping["game-1"]["name_only_merge"])
        rows[1]["normalized_record_json"] = json.dumps({"schoolId": 697, "id": 102, "teamId": 202})
        with self.assertRaises(ValueError):
            _build_tamu_identity_map(pl.DataFrame(rows), contract)

    def test_record_attribution_uses_per_game_provider_ids(self) -> None:
        identity = {"wmt_tamu_competitor_id": "11", "wmt_tamu_team_id": "22"}
        self.assertTrue(_record_is_tamu("actions", {"competitor_id": 11}, identity))
        self.assertFalse(_record_is_tamu("actions", {"competitor_id": 12}, identity))
        self.assertTrue(_record_is_tamu("drives", {"competitor_id": 11, "team_id": 22}, identity))
        self.assertFalse(_record_is_tamu("drives", {"competitor_id": 11, "team_id": 23}, identity))
        self.assertTrue(_record_is_tamu("players", {"team_id": 22}, identity))

    def test_domain_metrics_keep_partial_domains_explicit(self) -> None:
        rows = [
            {
                "domain": "actions",
                "wmt_game_id": "g1",
                "available_at_utc": "2020-01-01T00:00:00Z",
                "action_type": "pass",
                "action_subtype": "complete",
                "scoring_play": True,
                "drive_plays": None,
                "drive_yards": None,
                "drive_result": None,
                "game_player_id": None,
                "player_started": None,
            },
            {
                "domain": "drives",
                "wmt_game_id": "g1",
                "available_at_utc": "2020-01-01T00:00:00Z",
                "action_type": None,
                "action_subtype": None,
                "scoring_play": None,
                "drive_plays": 10.0,
                "drive_yards": 75.0,
                "drive_result": "TD",
                "game_player_id": None,
                "player_started": None,
            },
        ]
        metrics = _domain_metrics(rows, self.contract)
        self.assertEqual(metrics["actions_record_count"], 1)
        self.assertEqual(metrics["plays_record_count"], 0)
        self.assertEqual(metrics["action_pass_rate"], 1.0)
        self.assertIsNone(metrics["play_pass_rate"])
        self.assertEqual(metrics["drive_touchdown_rate"], 1.0)
        self.assertEqual(metrics["player_participant_count"], 0)

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_target_features_exclude_records_at_or_after_cutoff(self) -> None:
        tamu_id = self.contract["source_contract"]["canonical_tamu_team_id"]
        targets = pl.DataFrame(
            {
                "game_id": ["target"],
                "season": [2023],
                "season_type": ["regular"],
                "week": [1],
                "start_utc": ["2023-09-02T00:00:00Z"],
                "cutoff_lead_hours": [24],
                "home_team_id": [tamu_id],
                "away_team_id": ["opponent"],
                "neutral_site": [False],
            }
        )
        base = {
            "domain": "drives",
            "season": 2022,
            "wmt_game_id": "prior",
            "record_id": "r1",
            "source_json_pointer": "$.x",
            "source_record_sha256": "a" * 64,
            "source_response_sha256": "b" * 64,
            "provider_known_at_utc": "2022-10-01T00:00:00Z",
            "effective_at_utc": "2022-09-01T00:00:00Z",
            "available_at_utc": "2022-10-01T00:00:00Z",
            "canonical_tamu_team_id": tamu_id,
            "wmt_tamu_competitor_id": "11",
            "wmt_tamu_team_id": "22",
            "action_type": None,
            "action_subtype": None,
            "scoring_play": None,
            "drive_plays": 8.0,
            "drive_yards": 70.0,
            "drive_result": "TD",
            "player_id": None,
            "game_player_id": None,
            "player_started": None,
            "authority": "DEVELOPMENT_ONLY_PIT",
            "protected_eligible": False,
        }
        future = {**base, "record_id": "r2", "wmt_game_id": "target-source", "effective_at_utc": "2023-09-02T00:00:00Z", "available_at_utc": "2023-09-02T00:00:00Z"}
        contract = json.loads(json.dumps(self.contract))
        contract["acceptance"]["expected_tamu_target_games"] = 1
        features = _build_target_features(targets, pl.DataFrame([base, future]), contract)
        row = features.row(0, named=True)
        self.assertEqual(row["source_record_count"], 1)
        self.assertEqual(row["drives_record_count"], 1)
        self.assertEqual(row["drive_touchdown_rate"], 1.0)
        self.assertLess(row["latest_source_effective_at_utc"], row["cutoff_utc"])
        self.assertFalse(row["protected_eligible"])

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_forbidden_output_fields_fail_closed(self) -> None:
        _assert_output_boundary((pl.DataFrame({"safe_feature": [1.0]}),), self.contract)
        with self.assertRaises(ValueError):
            _assert_output_boundary((pl.DataFrame({"winner": [True]}),), self.contract)

    def test_contract_keeps_protected_and_direct_scientific_authority_closed(self) -> None:
        authority = self.contract["authority"]
        self.assertTrue(authority["development_pit_state_admission"])
        self.assertTrue(authority["preliminary_unprotected_feature_candidate"])
        self.assertTrue(authority["preliminary_unprotected_training_requires_separate_replay_unit"])
        self.assertFalse(authority["protected_training_admission"])
        self.assertFalse(authority["champion_or_production_promotion"])


if __name__ == "__main__":
    unittest.main()
