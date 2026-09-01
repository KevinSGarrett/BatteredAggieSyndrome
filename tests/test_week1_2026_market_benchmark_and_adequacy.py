from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from aggie_analytics.data.week1_2026_market_benchmark_and_adequacy import (  # noqa: E402
        american_implied_probability,
        consensus_from_books,
        crosswalk_quotes,
        home_expected_margin_from_home_handicap,
        multiplicative_devig,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by core-only CI
    raise unittest.SkipTest(
        "the market benchmark and adequacy tests require the optional modeling dependencies"
    ) from exc


class MoneylineDevigMutationTests(unittest.TestCase):
    def test_one_sided_moneyline_is_rejected(self) -> None:
        result = multiplicative_devig(-150, None, same_book=True, same_snapshot=True)
        self.assertFalse(result["accepted"])
        self.assertEqual("ONE_SIDED_OR_MALFORMED_MONEYLINE", result["rejection"])

    def test_cross_book_pairing_is_rejected(self) -> None:
        result = multiplicative_devig(-150, 130, same_book=False, same_snapshot=True)
        self.assertEqual("CROSS_BOOK_PRICE_PAIRING", result["rejection"])

    def test_cross_timestamp_pairing_is_rejected(self) -> None:
        result = multiplicative_devig(-150, 130, same_book=True, same_snapshot=False)
        self.assertEqual("CROSS_TIMESTAMP_PRICE_PAIRING", result["rejection"])

    def test_negative_overround_is_rejected(self) -> None:
        result = multiplicative_devig(0, 0, same_book=True, same_snapshot=True)
        self.assertFalse(result["accepted"])

    def test_valid_pair_devigs_to_one(self) -> None:
        result = multiplicative_devig(-150, 130, same_book=True, same_snapshot=True)
        self.assertTrue(result["accepted"])
        self.assertAlmostEqual(
            result["devigged_home"] + result["devigged_away"], 1.0, places=9
        )


class SpreadSignAndMatchMutationTests(unittest.TestCase):
    def test_home_favorite_spread_is_positive_expected_home_margin(self) -> None:
        self.assertEqual(38.5, home_expected_margin_from_home_handicap(-38.5))
        self.assertEqual(-3.0, home_expected_margin_from_home_handicap(3.0))

    def test_reversed_teams_are_quarantined(self) -> None:
        contests = [
            {
                "contest_identity": "abc",
                "ncaa_contest_id": "1",
                "home_normalized_name_key": "texas a&m",
                "away_normalized_name_key": "missouri st",
                "official_kickoff_utc": "2026-09-05T23:00:00Z",
            }
        ]
        quotes = [
            {
                "home_normalized_name_key": "missouri st",
                "away_normalized_name_key": "texas a&m",
                "provider_kickoff_utc": "2026-09-05T23:00:00Z",
                "capture_timestamp_utc": "2026-09-01T12:00:00Z",
                "quote_status": "QUOTED",
                "row_identity": "q1",
                "provider": "CollegeFootballData",
                "provider_event_id": 1,
            }
        ]
        walk = crosswalk_quotes(quotes=quotes, contests=contests)
        self.assertEqual([], walk["matched"])
        self.assertEqual(
            "HOME_AWAY_SWAP_OR_REVERSED_TEAMS", walk["quarantines"][0]["reason"]
        )

    def test_name_only_without_orientation_does_not_match_reversed_as_canonical(
        self,
    ) -> None:
        contests = [
            {
                "contest_identity": "abc",
                "ncaa_contest_id": "1",
                "home_normalized_name_key": "texas a&m",
                "away_normalized_name_key": "missouri st",
                "official_kickoff_utc": "2026-09-05T23:00:00Z",
            }
        ]
        quotes = [
            {
                "home_normalized_name_key": "aggies",
                "away_normalized_name_key": "bears",
                "provider_kickoff_utc": "2026-09-05T23:00:00Z",
                "capture_timestamp_utc": "2026-09-01T12:00:00Z",
                "quote_status": "QUOTED",
                "row_identity": "q2",
                "provider": "CollegeFootballData",
                "provider_event_id": 2,
            }
        ]
        walk = crosswalk_quotes(quotes=quotes, contests=contests)
        self.assertEqual(
            "UNMATCHED_PROVIDER_EVENT",
            walk["unmatched_provider_events"][0]["match_state"],
        )

    def test_post_kickoff_quote_is_quarantined(self) -> None:
        contests = [
            {
                "contest_identity": "abc",
                "ncaa_contest_id": "1",
                "home_normalized_name_key": "texas a&m",
                "away_normalized_name_key": "missouri st",
                "official_kickoff_utc": "2026-09-05T23:00:00Z",
            }
        ]
        quotes = [
            {
                "home_normalized_name_key": "texas a&m",
                "away_normalized_name_key": "missouri st",
                "provider_kickoff_utc": "2026-09-05T23:00:00Z",
                "capture_timestamp_utc": "2026-09-06T00:00:00Z",
                "quote_status": "QUOTED",
                "row_identity": "q3",
                "provider": "CollegeFootballData",
                "provider_event_id": 3,
            }
        ]
        walk = crosswalk_quotes(quotes=quotes, contests=contests)
        self.assertEqual(
            "POST_KICKOFF_QUOTE_PRESENTED_AS_PREGAME", walk["quarantines"][0]["reason"]
        )

    def test_insufficient_sources_are_not_labeled_consensus(self) -> None:
        quotes = [
            {
                "sportsbook": "DraftKings",
                "devig": {"accepted": True, "devigged_home": 0.91},
            }
        ]
        result = consensus_from_books(quotes, minimum_books=3)
        self.assertEqual("SINGLE_SOURCE_MARKET_REFERENCE", result["label"])
        self.assertNotEqual("MARKET_CONSENSUS", result["label"])


class FreezeAndClaimMutationTests(unittest.TestCase):
    def test_american_odds_round_trip_bounds(self) -> None:
        self.assertIsNone(american_implied_probability(0))
        self.assertGreater(american_implied_probability(-10000), 0.99)
        self.assertLess(american_implied_probability(5000), 0.03)

    def test_contract_forbids_spread_to_probability_and_bas_claims(self) -> None:
        import json

        contract = json.loads(
            (
                ROOT / "configs/week1_2026_market_benchmark_and_adequacy_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(contract["spread_to_exact_win_probability_authorized"])
        self.assertFalse(contract["scientific_nonclaims"]["a_and_m_adjustment"])
        self.assertFalse(contract["scientific_nonclaims"]["bas_or_aggie_excess_claim"])
        self.assertFalse(
            contract["scientific_nonclaims"]["champion_or_production_promotion"]
        )
        self.assertFalse(
            contract["scientific_nonclaims"]["roughly_40_point_spread_assumed"]
        )
        self.assertFalse(
            contract["scientific_nonclaims"]["market_enters_model_fitting"]
        )
        self.assertEqual("OPEN", contract["checkpoints"]["t_minus_24h_state"])
        self.assertEqual("OPEN", contract["checkpoints"]["t_minus_90m_state"])
        self.assertEqual("EARLY_MARKET", contract["snapshot_id"])


if __name__ == "__main__":
    unittest.main()
