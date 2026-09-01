"""Independent scientific-reference metrics, coherence, market, and mutations."""

from __future__ import annotations

import math
import unittest

from aggie_analytics.data.national_foundation_status_successor import (
    FALSE_QUARANTINE_GAME_ID,
    classify_status_successor,
)
from aggie_analytics.data.protected_evaluation_replacement_protocol import (
    LANE_DECISION,
    replacement_protocol,
)
from aggie_analytics.data.tamu_corpus_derivative_integrity_successor import (
    classify_player_line,
    original_text_is_source,
    reject_placeholder,
    season_specific_rejection_count,
)
from aggie_analytics.data.week1_2026_current_contest_binding_successor import (
    build_current_contest_row,
    report_mismatches,
)
from aggie_analytics.data.week1_2026_game_grain_distribution_successor import (
    game_grain_forecast,
    oriented_rows_from_game,
)
from aggie_analytics.data.week1_2026_market_integrity_successor import (
    classify_crosswalk,
    consensus_from_quotes,
    focus_game_quote_count,
    freeze_vs_market,
)
from aggie_analytics.scientific_reference.binding import current_opponent_bound
from aggie_analytics.scientific_reference.coherence import (
    joint_distribution_coherent,
    pair_normalize,
    probability_from_normal_residual,
)
from aggie_analytics.scientific_reference.market import even_odd_median, overround
from aggie_analytics.scientific_reference.metrics import brier_score, log_loss


class IndependentReferenceTests(unittest.TestCase):
    def test_brier_and_log_loss(self) -> None:
        self.assertEqual(brier_score([0.0, 1.0], [0.0, 1.0]), 0.0)
        self.assertGreater(log_loss([0.2], [1.0]), 0.0)

    def test_even_odd_median(self) -> None:
        self.assertEqual(even_odd_median([1.0, 3.0, 2.0]), 2.0)
        self.assertEqual(even_odd_median([1.0, 3.0]), 2.0)

    def test_pair_and_distribution_coherence(self) -> None:
        pair = pair_normalize(0.7, 0.3, 4.0, -4.0)
        self.assertTrue(pair["coherent"])
        broken = pair_normalize(0.9, 0.2, 4.0, -1.0)
        self.assertFalse(broken["coherent"])
        probability = probability_from_normal_residual(0.0, 1.0)
        self.assertAlmostEqual(probability, 0.5, places=12)

    def test_ridge_style_incoherence_is_rejected(self) -> None:
        expected = 22.25
        stdev = 21.3
        logistic = 1.0 / (1.0 + math.exp(-(expected / 3.0)))
        lower = expected - 1.2815515655446004 * stdev
        upper = expected + 1.2815515655446004 * stdev
        result = joint_distribution_coherent(
            {
                "expected_margin_home": expected,
                "home_win_probability": logistic,
                "interval_lower": lower,
                "interval_upper": upper,
            },
            residual_stdev=stdev,
            quantile=1.2815515655446004,
        )
        self.assertFalse(result["coherent"])

    def test_false_quarantine_successor(self) -> None:
        row = {
            "canonical_game_id": FALSE_QUARANTINE_GAME_ID,
            "notes": "originally postponed then completed",
            "completed": True,
            "homePoints": 41,
            "awayPoints": 9,
            "status": "final",
            "season": 2011,
        }
        classified = classify_status_successor(row)
        self.assertTrue(classified["false_quarantine_corrected"])
        self.assertEqual(classified["disposition"], "RESTORE_FALSE_SUBSTRING_QUARANTINE")

    def test_current_contest_not_historical_transplant(self) -> None:
        row = build_current_contest_row(
            team_key="texas a&m",
            contests=[
                {
                    "contest_id": "week1-tamu-most",
                    "home_team_key": "texas a&m",
                    "away_team_key": "missouri state",
                }
            ],
            historical_priors={"texas a&m": {"n": 12}, "missouri state": {"n": 11}},
            current_conference="SEC",
            current_subdivision="FBS",
            current_rank=None,
            rank_admitted=False,
            official_2026_finals_known_before_cutoff={},
            trust_gate_open=False,
        )
        self.assertFalse(row["copied_from_terminal_historical_row"])
        self.assertEqual(row["opponent_key"], "missouri state")
        self.assertEqual(row["trust_classification"], "UNTRUSTED_SHADOW")
        bound = current_opponent_bound(
            row,
            {
                "home_team_key": "texas a&m",
                "away_team_key": "missouri state",
            },
        )
        self.assertTrue(bound["bound"])
        mismatches = report_mismatches(
            [
                {
                    "team_key": "texas a&m",
                    "opponent_key": "historic-fcs-opponent",
                    "copied_from_terminal_historical_row": True,
                }
            ],
            [row],
        )
        self.assertTrue(mismatches)

    def test_game_grain_oriented_rows(self) -> None:
        game = game_grain_forecast(
            contest_id="week1-tamu-most",
            home_team_key="texas a&m",
            away_team_key="missouri state",
            expected_margin_home=14.0,
            residual_stdev=12.0,
            trust_gate_open=False,
        )
        self.assertEqual(game["row_state"], "UNTRUSTED_SHADOW")
        self.assertAlmostEqual(
            game["home_win_probability"] + game["away_win_probability"], 1.0
        )
        rows = oriented_rows_from_game(game)
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]["expected_margin"] + rows[1]["expected_margin"], 0.0)

    def test_market_alias_median_overround(self) -> None:
        freeze = freeze_vs_market(
            model_freeze_utc=None,
            market_acquisition_utc="2026-09-01T00:00:00Z",
            acquisition_source="supplied_cli_time",
        )
        self.assertEqual(freeze, "PRE_MARKET_FREEZE_NOT_PROVEN")
        self.assertEqual(
            classify_crosswalk(
                participants_authoritative=False,
                schedule_evidence=False,
                name_date_only=True,
            ),
            "NAME_DATE_ONLY_NOT_STRONG_IDENTITY",
        )
        quotes = focus_game_quote_count(
            [
                {
                    "home_team": "Texas A&M",
                    "away_team": "Missouri St.",
                    "event_id": "e1",
                    "book": "Draft Kings",
                    "snapshot_id": "s1",
                    "home_price": -400,
                }
            ]
        )
        self.assertEqual(quotes["quote_count"], 1)
        consensus = consensus_from_quotes([0.8, 0.7], ["Draft Kings", "FanDuel"])
        self.assertEqual(consensus["median_devigged_home"], 0.75)
        pathological = overround(-110, -110)
        self.assertFalse(pathological["pathological"])
        bad = overround(-10000, -10000)
        self.assertTrue(bad["pathological"])

    def test_corpus_and_protected_protocol(self) -> None:
        self.assertEqual(reject_placeholder("owned by BAT-XXX"), "UNRESOLVED_BAT_XXX_PLACEHOLDER")
        self.assertTrue(
            classify_player_line("Smith/Jones 12-20")["do_not_attribute_to_first_token"]
        )
        parsed = {"parsed": 1}
        self.assertFalse(original_text_is_source(str(parsed), parsed))
        self.assertTrue(original_text_is_source("Smith 12 rush yards", parsed))
        self.assertEqual(
            season_specific_rejection_count(
                [{"season": 1996}, {"season": 1997}, {"season": 1996}], 1996
            ),
            2,
        )
        protocol = replacement_protocol(user_approved_activation=False)
        self.assertEqual(protocol["lane_decision"], LANE_DECISION)
        self.assertFalse(protocol["exposed_seasons"]["blind"])
        self.assertFalse(protocol["exposed_seasons"]["sealed"])

    def test_historical_opponent_transplant_mutation(self) -> None:
        bound = current_opponent_bound(
            {
                "team_key": "texas a&m",
                "opponent_key": "arkansas",
                "copied_from_terminal_historical_row": True,
            },
            {"home_team_key": "texas a&m", "away_team_key": "missouri state"},
        )
        self.assertFalse(bound["bound"])

    def test_noncomplementary_probabilities_mutation(self) -> None:
        result = pair_normalize(0.99, 0.99, 20.0, -20.0)
        self.assertFalse(result["coherent"])
        self.assertEqual(
            result["abstain_reason"], "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        )


if __name__ == "__main__":
    unittest.main()
