from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.temporal.rankings_pit import (
    RankingsIndex,
    build_feature_rows,
    build_state_row,
    conservative_date_interval,
    poll_admission_reason,
    team_row_admission_reason,
)


def source_row() -> dict:
    return {
        "season": 2023,
        "poll_id": 7,
        "poll_order": 3,
        "poll_label": "September 10",
        "poll_date": "2023-09-10",
        "candidate_canonical_team_id": "team_a",
        "source_team_id": 10,
        "school": "Example",
        "rank": 4,
        "rank_state": "RANKED",
        "points_decimal": "1000",
        "first_place_votes_decimal": "2",
        "source_capture_id": "cap_a",
        "source_response_sha256": "a" * 64,
        "source_url": "https://example.invalid/poll",
        "record_sha256": "b" * 64,
    }


class HistoricalRankingsPitTests(unittest.TestCase):
    def test_date_interval_is_wide_and_eligibility_uses_only_upper_bound(self):
        self.assertEqual(
            conservative_date_interval("2023-09-10"),
            ("2023-09-09T00:00:00Z", "2023-09-12T00:00:00Z"),
        )

    def test_poll_admission_is_exact_and_dated(self):
        self.assertIsNone(
            poll_admission_reason(
                {
                    "cpa_poll_phase": "DATED_WEEKLY",
                    "cpa_poll_date": "2023-09-10",
                    "alignment_state": "EXACT_HIGH_COVERAGE_UNIQUE",
                }
            )
        )
        self.assertEqual(
            poll_admission_reason(
                {
                    "cpa_poll_phase": "PRESEASON",
                    "cpa_poll_date": None,
                    "alignment_state": "EXACT_HIGH_COVERAGE_UNIQUE",
                }
            ),
            "UNDATED_PRESEASON_OR_FINAL",
        )
        self.assertEqual(
            poll_admission_reason(
                {
                    "cpa_poll_phase": "DATED_WEEKLY",
                    "cpa_poll_date": "2023-09-10",
                    "alignment_state": "HIGH_COVERAGE_UNIQUE_WITH_CONFLICTS",
                }
            ),
            "DATED_POLL_NOT_EXACT_HIGH_COVERAGE_UNIQUE",
        )

    def test_name_only_or_missing_identity_fails_closed(self):
        self.assertEqual(
            team_row_admission_reason(
                {
                    "identity_resolution_state": "AMBIGUOUS_NAME_ONLY",
                    "candidate_canonical_team_id": "team_a",
                }
            ),
            "TEAM_IDENTITY_NOT_EXACT_VERIFIED",
        )
        self.assertEqual(
            team_row_admission_reason(
                {
                    "identity_resolution_state": "EXACT_VERIFIED_ALIAS_CANDIDATE",
                    "candidate_canonical_team_id": None,
                }
            ),
            "CANONICAL_TEAM_ID_MISSING",
        )

    def test_state_row_never_claims_exact_publication_time(self):
        state = build_state_row(source_row())
        self.assertEqual(state["publication_time_state"], "DATE_ONLY_INTERVAL_EXACT_TIME_UNKNOWN")
        self.assertEqual(state["first_eligible_at_utc"], "2023-09-12T00:00:00Z")
        self.assertNotIn("published_at", state)

    def test_future_poll_is_not_selected(self):
        state = build_state_row(source_row())
        index = RankingsIndex([state])
        self.assertIsNone(index.latest(2023, "2023-09-11T23:59:59Z"))
        self.assertEqual(index.latest(2023, "2023-09-12T00:00:00Z").poll_id, 7)

    def test_feature_missingness_is_explicit_and_target_outcome_absent(self):
        state = build_state_row(source_row())
        games = [
            {
                "game_id": "game_1",
                "season": 2023,
                "season_type": "regular",
                "start_utc": "2023-09-16T20:00:00Z",
                "home_team_id": "team_a",
                "away_team_id": "team_unlisted",
            }
        ]
        rows = build_feature_rows(games, [state])
        self.assertEqual(len(rows), 2)
        home = next(row for row in rows if row["team_side"] == "HOME")
        away = next(row for row in rows if row["team_side"] == "AWAY")
        self.assertEqual(home["rank"], 4)
        self.assertEqual(away["missingness_disposition"], "TEAM_NOT_LISTED_IN_LATEST_ELIGIBLE_POLL")
        self.assertIsNone(away["rank"])
        self.assertFalse(any("points_for" in row or "outcome" in row for row in rows))

    def test_contract_preserves_protected_boundary(self):
        contract = json.loads(
            (ROOT / "configs/historical_rankings_pit_contract.json").read_text(encoding="utf-8")
        )
        self.assertTrue(contract["eligibility"]["pit_state"])
        self.assertTrue(contract["eligibility"]["development_and_preliminary_feature_use"])
        self.assertFalse(contract["eligibility"]["protected_evaluation"])
        self.assertFalse(contract["eligibility"]["production_promotion"])


if __name__ == "__main__":
    unittest.main()
