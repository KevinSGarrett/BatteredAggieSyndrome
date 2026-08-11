from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.play_enrichment_pit import (
    PLAYER_ID_COLUMNS,
    POSITION_COLUMNS,
    _build_features,
    _build_profiles,
    _row_flags,
    _unmapped_quarantine,
    cutoff_utc,
)


ROOT = Path(__file__).resolve().parents[1]


class HistoricalPlayEnrichmentPitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "configs" / "historical_play_enrichment_pit_contract.json").read_text(encoding="utf-8")
        )

    def test_cutoff_is_explicitly_before_target_start(self) -> None:
        self.assertEqual(cutoff_utc("2023-08-26T18:30:00Z", 24), "2023-08-25T18:30:00Z")

    def test_contract_requires_exact_links_and_forbids_name_only_mapping(self) -> None:
        source = self.contract["source_contract"]
        eligibility = self.contract["eligibility"]
        self.assertEqual(source["eligible_enrichment_disposition"], "CANDIDATE_EXACT_VALIDATED_PLAY_ENRICHMENT_LINK")
        self.assertNotIn(2020, source["exact_link_source_seasons"])
        self.assertEqual(source["partial_source_seasons"], [2020])
        self.assertTrue(eligibility["require_unique_exact_base_play_observation_link"])
        self.assertTrue(eligibility["require_verified_source_team_assignment"])
        self.assertFalse(eligibility["name_only_team_or_player_mapping_allowed"])
        self.assertEqual(eligibility["literal_question_mark_position_meaning"], "UNKNOWN")

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_position_and_source_player_flags_preserve_unknown_without_identity_promotion(self) -> None:
        row = {name: None for name in POSITION_COLUMNS + PLAYER_ID_COLUMNS}
        row["position_rush"] = "?"
        row["rush_player_id"] = 123
        flagged = _row_flags(pl.DataFrame([row])).row(0, named=True)
        self.assertTrue(flagged["has_position_candidate"])
        self.assertTrue(flagged["has_unknown_position_candidate"])
        self.assertTrue(flagged["has_source_player_id_candidate"])

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_unmapped_team_is_quarantined_with_no_name_only_policy(self) -> None:
        frame = pl.DataFrame(
            {
                "observation_id": ["e1"],
                "season": [2022],
                "game_id": [1],
                "sequence_number": [2],
                "canonical_game_id": ["g1"],
                "base_play_observation_id": ["b1"],
                "source_team_id": ["112358"],
                "team_id": [None],
                "pos_team": ["Long Island University"],
                "def_pos_team": ["Opponent"],
                "offense_team_id": [112358],
                "defense_team_id": [1],
                "source_known_at_utc": ["2023-05-05T03:50:21Z"],
                "effective_at_utc": ["2022-09-01T00:00:00Z"],
                "source_record_evidence_sha256": ["s"],
                "base_source_record_evidence_sha256": ["b"],
                "row_lineage_sha256": ["r"],
                "base_row_lineage_sha256": ["br"],
            }
        )
        quarantine = _unmapped_quarantine(frame)
        self.assertEqual(quarantine.height, 1)
        self.assertEqual(quarantine["quarantine_reason"].item(), "QUARANTINE_EXACT_PLAY_ENRICHMENT_SOURCE_TEAM_UNMAPPED")
        self.assertEqual(quarantine["identity_policy"].item(), "NO_NAME_ONLY_TEAM_MAPPING")

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_profiles_preserve_source_metric_nulls_and_revision_deltas(self) -> None:
        rows = []
        for index, epa in enumerate([1.0, None]):
            rows.append(
                {
                    "team_id": "t1",
                    "canonical_game_id": f"g{index}",
                    "season": 2022,
                    "has_position_candidate": index == 0,
                    "has_unknown_position_candidate": index == 0,
                    "has_source_player_id_candidate": index == 0,
                    "EPA": epa,
                    "wpa": None,
                    "success": 1,
                    "ppa": None,
                    "source_epa_delta_from_base": 0.25,
                    "source_wpa_delta_from_base": None,
                    "rush": 1,
                    "pass": 0,
                    "sack": 0,
                    "int": 0,
                    "completion": 0,
                    "pass_attempt": 0,
                    "target": 0,
                    "touchdown": 0,
                    "turnover": 0,
                    "penalty_flag": False,
                    "rz_play": 0,
                    "scoring_opp": 0,
                    "middle_8": False,
                    "stuffed_run": 0,
                    "source_known_at_utc": "2023-05-05T03:50:21Z",
                    "effective_at_utc": "2022-11-01T00:00:00Z",
                }
            )
        profile = _build_profiles(pl.DataFrame(rows)).row(0, named=True)
        self.assertEqual(profile["source_play_count"], 2)
        self.assertEqual(profile["source_epa_mean"], 1.0)
        self.assertIsNone(profile["source_wpa_mean"])
        self.assertEqual(profile["source_epa_revision_mean_abs"], 0.25)
        self.assertEqual(profile["unknown_position_rate"], 0.5)
        self.assertEqual(profile["metric_authority"], "SOURCE_MODEL_CANDIDATE_NOT_OFFICIAL")

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_target_features_preserve_cold_start_and_authority(self) -> None:
        profiles = pl.DataFrame(
            {
                "team_id": ["t1"],
                "source_play_count": [2],
                "source_game_count": [1],
                "source_known_at_utc": ["2023-05-05T03:50:21Z"],
                "authority": ["DEVELOPMENT_ONLY"],
                "official_stat_authority": [False],
                "protected_eligible": [False],
            }
        )
        targets = pl.DataFrame(
            {
                "game_id": ["target-1"],
                "season": [2023],
                "season_type": ["regular"],
                "week": [1],
                "start_utc": ["2023-08-26T18:30:00Z"],
                "cutoff_lead_hours": [24],
                "home_team_id": ["t1"],
                "away_team_id": ["t2"],
                "neutral_site": [False],
            }
        )
        features = _build_features(targets, profiles, self.contract)
        home = features.filter(pl.col("team_role") == "HOME").row(0, named=True)
        away = features.filter(pl.col("team_role") == "AWAY").row(0, named=True)
        self.assertFalse(home["cold_start"])
        self.assertTrue(away["cold_start"])
        self.assertFalse(home["protected_eligible"])
        self.assertFalse(home["official_stat_authority"])
        self.assertFalse(home["canonical_player_identity_promoted"])

    def test_contract_keeps_official_protected_and_production_authority_closed(self) -> None:
        authority = self.contract["authority"]
        self.assertTrue(authority["pit_state_admission"])
        self.assertTrue(authority["development_feature_admission"])
        self.assertFalse(authority["canonical_player_identity_promotion"])
        self.assertFalse(authority["official_stat_authority"])
        self.assertFalse(authority["protected_training_admission"])
        self.assertFalse(authority["protected_evaluation_admission"])
        self.assertFalse(authority["champion_or_production_promotion"])


if __name__ == "__main__":
    unittest.main()
