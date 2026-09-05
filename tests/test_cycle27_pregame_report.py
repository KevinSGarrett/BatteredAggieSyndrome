"""Cycle 27 pregame report and disagreement adversarial tests.

Isolated fixtures: quoted transcripts are not captures; incompatible
spread/total pairs are withheld; margin-only output is not two scores;
contributions must sum; exploratory subgroups stay exploratory.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.cycle27_pregame_reporting import (  # noqa: E402
    INTERIM_LABEL,
    T24H_EVIDENCE_LABEL,
    T90M_EVIDENCE_LABEL,
    ContributionSumError,
    PregameReportingError,
    admit_market_quote,
    build_score_model_readiness,
    captured_focus_quote_count,
    classify_disagreement,
    classify_external_model_attribution,
    classify_implied_score_label,
    classify_linear_contributions_as_causal,
    classify_spread_sign,
    classify_subgroup_analysis,
    independent_scores_from_margin_only,
    market_line_implied_score,
    render_pregame_report,
    ridge_contributions,
)


class Cycle27PregameReportTests(unittest.TestCase):
    def test_quoted_transcript_is_not_capture(self) -> None:
        rejected = admit_market_quote(
            {
                "source": "quoted_transcript",
                "home_spread": -40.5,
                "total": 53.5,
                "sportsbook": "user said so",
            }
        )
        self.assertFalse(rejected["admitted"])
        self.assertEqual(rejected["reason"], "QUOTED_TRANSCRIPT_IS_NOT_CAPTURE")
        also = admit_market_quote(
            {"acquisition_source": "user_quotation", "home_spread": -22.5}
        )
        self.assertFalse(also["admitted"])
        admitted = admit_market_quote(
            {
                "acquisition_source": "provider_retrieval_receipt",
                "home_spread": -7.5,
                "raw_response_sha256": "abc",
            }
        )
        self.assertTrue(admitted["admitted"])

    def test_fuzzy_team_name_is_not_a_captured_quote(self) -> None:
        counted = captured_focus_quote_count(
            consensus={
                "ncaa_contest_id": "6607349",
                "quote_count": 0,
                "label": "INSUFFICIENT_MARKET_COVERAGE",
            },
            quote_rows=[
                {
                    "home_normalized_name_key": "texas a&m",
                    "away_normalized_name_key": "missouri state",
                    "home_spread": -40.5,
                    "total": 53.5,
                }
            ],
        )
        self.assertEqual(counted["quote_count"], 0)
        self.assertEqual(counted["exact_contest_id_quote_rows"], 0)
        self.assertFalse(counted["name_key_fuzzy_match_used"])
        self.assertEqual(counted["status"], "ABSENT")
        self.assertEqual(counted["label"], "INSUFFICIENT_MARKET_COVERAGE")

    def test_incompatible_spread_total_is_withheld(self) -> None:
        mismatched_books = market_line_implied_score(
            total=53.5,
            home_spread=-40.5,
            sportsbook=None,
            spread_book="BookA",
            total_book="BookB",
            spread_as_of_utc="2026-09-04T12:00:00Z",
            total_as_of_utc="2026-09-04T12:00:00Z",
        )
        self.assertEqual(mismatched_books["status"], "INCOMPATIBLE_SCORE_REFERENCE")
        self.assertIsNone(mismatched_books["home_points"])
        negative = market_line_implied_score(
            total=30.0,
            home_spread=-40.5,
            sportsbook="BookA",
            spread_book="BookA",
            total_book="BookA",
            spread_as_of_utc="2026-09-04T12:00:00Z",
            total_as_of_utc="2026-09-04T12:00:00Z",
        )
        self.assertEqual(negative["status"], "INCOMPATIBLE_SCORE_REFERENCE")
        self.assertEqual(negative["reason"], "NEGATIVE_IMPLIED_TEAM_POINTS")
        self.assertFalse(negative["clamped"])
        compatible = market_line_implied_score(
            total=53.5,
            home_spread=-40.5,
            sportsbook="BookA",
            spread_book="BookA",
            total_book="BookA",
            spread_as_of_utc="2026-09-04T12:00:00Z",
            total_as_of_utc="2026-09-04T12:00:00Z",
        )
        self.assertEqual(compatible["status"], "MARKET_LINE_IMPLIED_SCORE_REFERENCE")
        self.assertEqual(compatible["home_points"], 47.0)
        self.assertEqual(compatible["away_points"], 6.5)
        self.assertFalse(compatible["independent_bas_score"])

    def test_margin_only_is_not_two_team_scores(self) -> None:
        scores = independent_scores_from_margin_only(22.2506043541)
        self.assertIsNone(scores["independent_predicted_score"])
        self.assertEqual(
            scores["blocker"], "MARGIN_ALONE_CANNOT_IDENTIFY_BOTH_TEAM_SCORES"
        )
        blended = independent_scores_from_margin_only(22.25, total=53.5)
        self.assertIsNone(blended["independent_predicted_score"])
        self.assertIn("BLEND", blended["blocker"])

    def test_contributions_must_sum(self) -> None:
        rows = ridge_contributions(
            ["intercept", "is_home"],
            [1.0, 1.0],
            [2.0, 3.0],
            reconstructed_margin=5.0,
        )
        self.assertEqual(sum(row["contribution"] for row in rows), 5.0)
        with self.assertRaises(ContributionSumError):
            ridge_contributions(
                ["intercept", "is_home"],
                [1.0, 1.0],
                [2.0, 3.0],
                reconstructed_margin=40.5,
            )

    def test_exploratory_cannot_be_relabeled_confirmation(self) -> None:
        exploratory = classify_subgroup_analysis(
            motivated_by_observed_disagreement=True,
            labeled_as="EXPLORATORY",
        )
        self.assertEqual(exploratory["status"], "EXPLORATORY")
        self.assertFalse(exploratory["independent_confirmation"])
        with self.assertRaises(PregameReportingError):
            classify_subgroup_analysis(
                motivated_by_observed_disagreement=True,
                labeled_as="INDEPENDENT_CONFIRMATION",
            )
        with self.assertRaises(PregameReportingError):
            classify_subgroup_analysis(
                motivated_by_observed_disagreement=True,
                labeled_as="CONFIRMATION",
            )

    def test_score_readiness_is_null_and_does_not_enable_deprecated(self) -> None:
        readiness = build_score_model_readiness(
            issued_at_utc="2026-09-04T16:45:00Z",
            week1_candidates=["national_base_rate", "national_margin_ridge"],
            ridge_emits_margin=True,
            joint_score_interface_present=True,
            poisson_runtime_present=True,
            elo_offense_defense_exposed_seasons=[2023, 2024, 2025],
            unprotected_baseline_target_seasons=[2023, 2024, 2025],
            eligible_week1_score_candidate=False,
        )
        self.assertIsNone(readiness["independent_predicted_score"])
        self.assertIn(
            "NO_ELIGIBLE_WEEK1", readiness["independent_predicted_score_blocker"]
        )
        self.assertFalse(readiness["deprecated_experiments_enabled"])
        self.assertTrue(readiness["protected_seasons_2024_2025_not_blind"])
        self.assertIn(
            2024,
            readiness["experimental_score_models"][
                "elo_offense_defense_score_components"
            ]["report_only_exposed_seasons"],
        )

    def test_interim_report_is_not_t24_or_t90(self) -> None:
        markdown = render_pregame_report(
            issued_at_utc="2026-09-04T16:45:00Z",
            candidates=[
                {
                    "candidate_id": "national_base_rate",
                    "probability_home": 0.5,
                    "probability_away": 0.5,
                    "expected_margin_home": None,
                    "margin_interval_home": None,
                    "nominal_interval_level": None,
                    "trust_classification": "UNTRUSTED_SHADOW",
                    "never_recommended": True,
                }
            ],
            market={
                "status": "ABSENT",
                "quote_count": 0,
                "label": "INSUFFICIENT_MARKET_COVERAGE",
            },
            implied_score={
                "status": "INCOMPATIBLE_SCORE_REFERENCE",
                "reason": "MISSING_BOOK_IDENTITY",
            },
            coaching={
                "national_domain": "SOURCE_ABSENT",
                "registry_coach_entry_present": False,
                "home_fetch": "BLOCKED",
                "away_fetch": "RETRIEVED",
            },
            disagreement={
                "classes": classify_disagreement(
                    [
                        "CONFIRMED_IMPLEMENTATION_DEFECT",
                        "INPUT_LIMITATION",
                        "MODEL_SPECIFICATION_LIMITATION",
                        "UNEXPLAINED_DISAGREEMENT",
                    ]
                ),
                "narrative": "Fixture narrative.",
            },
            score_readiness={
                "independent_predicted_score": None,
                "independent_predicted_score_blocker": "NO_ELIGIBLE_WEEK1_JOINT_SCORE_OR_TOTAL_CANDIDATE",
            },
            consumption=[
                {"domain": "coaching", "label": "CONTEXT_ONLY", "note": "not consumed"}
            ],
            other_models=[],
        )
        self.assertIn(INTERIM_LABEL, markdown)
        self.assertIn("not a T-24H or T-90M packet", markdown)
        self.assertIn("No actual-score column", markdown)
        self.assertNotIn("| Actual score", markdown)
        self.assertIn("control (never recommended)", markdown)
        self.assertIn("ABSENT", markdown)
        self.assertNotIn("womens-golf", markdown)
        self.assertNotIn(
            "{",
            markdown.split("## Market reference", 1)[1].split("## Market-line", 1)[0],
        )

    def test_t24h_evidence_report_does_not_relabel_early_week1_as_frozen(self) -> None:
        markdown = render_pregame_report(
            issued_at_utc="2026-09-04T22:20:00Z",
            candidates=[
                {
                    "candidate_id": "national_base_rate",
                    "probability_home": 0.5,
                    "probability_away": 0.5,
                    "expected_margin_home": None,
                    "margin_interval_home": None,
                    "nominal_interval_level": None,
                    "trust_classification": "UNTRUSTED_SHADOW",
                    "never_recommended": True,
                }
            ],
            market={
                "status": "ABSENT",
                "quote_count": 0,
                "label": "INSUFFICIENT_MARKET_COVERAGE",
            },
            implied_score={
                "status": "INCOMPATIBLE_SCORE_REFERENCE",
                "reason": "MISSING_BOOK_IDENTITY",
            },
            coaching={"national_domain": "SOURCE_ABSENT"},
            disagreement={"classes": [], "narrative": "Fixture narrative."},
            score_readiness={
                "independent_predicted_score": None,
                "independent_predicted_score_blocker": "NO_ELIGIBLE_WEEK1_JOINT_SCORE_OR_TOTAL_CANDIDATE",
            },
            consumption=[],
            other_models=[],
            evidence_checkpoint={
                "checkpoint_label": "T-24H",
                "forecast_frozen": False,
            },
        )
        self.assertIn(T24H_EVIDENCE_LABEL, markdown)
        self.assertIn("not a new T-24H freeze", markdown)
        self.assertNotIn("FORECAST_FROZEN", markdown.split("Label", 1)[0])
        self.assertIn(
            "May not treat this T-24H evidence packet as FORECAST_FROZEN or as a T-90M freeze.",
            markdown,
        )
        self.assertNotIn("May not treat this report as T-24H or T-90M.", markdown)

    def test_t90m_evidence_report_does_not_relabel_early_week1_as_frozen(self) -> None:
        markdown = render_pregame_report(
            issued_at_utc="2026-09-05T21:20:00Z",
            candidates=[
                {
                    "candidate_id": "national_base_rate",
                    "probability_home": 0.5,
                    "probability_away": 0.5,
                    "expected_margin_home": None,
                    "margin_interval_home": None,
                    "nominal_interval_level": None,
                    "trust_classification": "UNTRUSTED_SHADOW",
                    "never_recommended": True,
                }
            ],
            market={
                "status": "ABSENT",
                "quote_count": 0,
                "label": "INSUFFICIENT_MARKET_COVERAGE",
            },
            implied_score={
                "status": "INCOMPATIBLE_SCORE_REFERENCE",
                "reason": "MISSING_BOOK_IDENTITY",
            },
            coaching={"national_domain": "SOURCE_ABSENT"},
            disagreement={"classes": [], "narrative": "Fixture narrative."},
            score_readiness={
                "independent_predicted_score": None,
                "independent_predicted_score_blocker": "NO_ELIGIBLE_WEEK1_JOINT_SCORE_OR_TOTAL_CANDIDATE",
            },
            consumption=[],
            other_models=[],
            evidence_checkpoint={
                "checkpoint_label": "T-90M",
                "forecast_frozen": False,
            },
        )
        self.assertIn(T90M_EVIDENCE_LABEL, markdown)
        self.assertIn("not a new T-90M freeze", markdown)
        self.assertIn(
            "May not treat this T-90M evidence packet as FORECAST_FROZEN.",
            markdown,
        )

    def test_wrong_external_model_attribution_is_rejected(self) -> None:
        coincidental = classify_external_model_attribution(
            attributed_source="ESPN FPI",
            captured_source_id="numberFire",
            probability_coincides=True,
        )
        matched = classify_external_model_attribution(
            attributed_source="numberFire",
            captured_source_id="numberFire",
        )
        self.assertFalse(coincidental["admitted"])
        self.assertEqual(coincidental["reason"], "WRONG_EXTERNAL_MODEL_ATTRIBUTION")
        self.assertTrue(coincidental["probability_coincidence_is_not_identity"])
        self.assertTrue(matched["admitted"])

    def test_spread_sign_reversal_and_nonfinite_implied_inputs(self) -> None:
        reversed_sign = classify_spread_sign(
            quoted_home_spread=40.5,
            captured_home_spread=-40.5,
        )
        self.assertEqual(reversed_sign["status"], "SIGN_REVERSAL_REJECTED")
        withheld = market_line_implied_score(
            total=float("nan"),
            home_spread=-7.5,
            sportsbook="book-a",
            spread_book="book-a",
            total_book="book-a",
            spread_as_of_utc="2026-09-05T12:00:00Z",
            total_as_of_utc="2026-09-05T12:00:00Z",
        )
        self.assertEqual(withheld["status"], "INCOMPATIBLE_SCORE_REFERENCE")
        self.assertEqual(withheld["reason"], "NONFINITE_OR_MISSING_NUMERIC_INPUTS")
        nonpositive = market_line_implied_score(
            total=0,
            home_spread=-7.5,
            sportsbook="book-a",
            spread_book="book-a",
            total_book="book-a",
            spread_as_of_utc="2026-09-05T12:00:00Z",
            total_as_of_utc="2026-09-05T12:00:00Z",
        )
        self.assertEqual(nonpositive["reason"], "NONPOSITIVE_TOTAL")
        negative_points = market_line_implied_score(
            total=10.0,
            home_spread=-40.5,
            sportsbook="book-a",
            spread_book="book-a",
            total_book="book-a",
            spread_as_of_utc="2026-09-05T12:00:00Z",
            total_as_of_utc="2026-09-05T12:00:00Z",
        )
        self.assertEqual(negative_points["reason"], "NEGATIVE_IMPLIED_TEAM_POINTS")
        self.assertIsNone(negative_points.get("home_points"))

    def test_implied_score_is_not_independent_bas_and_contributions_are_not_causal(
        self,
    ) -> None:
        implied = market_line_implied_score(
            total=53.5,
            home_spread=-7.5,
            sportsbook="book-a",
            spread_book="book-a",
            total_book="book-a",
            spread_as_of_utc="2026-09-05T12:00:00Z",
            total_as_of_utc="2026-09-05T12:00:00Z",
        )
        labeled = classify_implied_score_label(implied)
        self.assertFalse(labeled["independent_bas_score"])
        self.assertFalse(labeled["mislabeled_as_independent_bas"])
        causal = classify_linear_contributions_as_causal(interpret_as_causal=True)
        self.assertTrue(causal["rejected"])
        self.assertFalse(causal["causal_interpretation"])


if __name__ == "__main__":
    unittest.main()
