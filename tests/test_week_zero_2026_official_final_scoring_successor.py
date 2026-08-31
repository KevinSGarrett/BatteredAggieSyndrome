"""Fail-closed mutation coverage for the BAT-674 Week Zero official-final scoring core.

Every test here builds its own in-memory scoreboard document and frozen predecessor
rows, so the suite never reads or writes the mounted data root and cannot contaminate
another test's authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.modeling.week_zero_official_final_scoring import (  # noqa: E402
    ADMISSIBLE,
    SUBSTITUTED,
    OfficialFinalScoringViolation,
    build_official_capture_manifest,
    calibration_bins,
    candidate_metrics,
    favorite_direction,
    frozen_forecast_row_identity,
    parse_scoreboard_cards,
    prove_contest_orientation,
    scoring_row_identity,
    source_published_form_date,
    temporal_verdict_row_identity,
)

CONTEST_ID = "6586325"
AWAY_ID = "622184"
HOME_ID = "622197"
KICKOFF = "2026-08-30T02:00:00Z"
RETRIEVED = "2026-08-31T01:20:00Z"


def render_document(
    *,
    form_date: str = "08/29/2026",
    contest_id: str = CONTEST_ID,
    away_id: str = AWAY_ID,
    away_name: str = "Memphis",
    home_id: str = HOME_ID,
    home_name: str = "UNLV",
    away_points: int = 27,
    home_points: int = 21,
    terminal: bool = True,
    header_date: str = "08/29/2026",
) -> str:
    """Render a scoreboard page in the shape the official route publishes."""
    status = ""
    if terminal:
        status = (
            f'<!-- <div class="livestream_status_{contest_id} livestream_status '
            f'livestream_game_over ">Final</div> -->'
        )
    return f"""<html><body>
<form><input type="hidden" name="game_date" value="{form_date}" /></form>
{status}
<table><tr><td>{header_date} 10:00 PM FOX</td></tr>
<tr id="contest_{contest_id}">
  <td><a href="/teams/{away_id}">{away_name} (1-0)</a></td>
  <td><div id="score_{away_id}" class="score">{away_points}</div></td>
</tr>
<tr id="contest_{contest_id}">
  <td><a href="/teams/{home_id}">{home_name} (0-1)</a></td>
  <td><div id="score_{home_id}" class="score">{home_points}</div></td>
</tr>
</table></body></html>"""


def capture(document: str, *, requested_game_date: str = "2026-08-29") -> dict:
    raw = document.encode("utf-8")
    return {
        "requested_game_date": requested_game_date,
        "document": document,
        "raw_bytes": raw,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_relative_path": f"raw/fixture/{requested_game_date}.html",
        "request_identity_sha256": f"request-{requested_game_date}",
        "retrieved_at_utc": RETRIEVED,
        "route_id": "fixture",
        "source_uri": f"https://stats.ncaa.org/fixture?game_date={requested_game_date}",
    }


def manifest_for(*documents_and_dates) -> dict:
    return build_official_capture_manifest(
        captures=[capture(doc, requested_game_date=date) for doc, date in documents_and_dates],
        contract_sha256="contract",
        issued_at_utc="2026-08-31T02:00:00Z",
    )


FROZEN_CONTEST = {
    "ncaa_contest_id": CONTEST_ID,
    "contest_state": "AWAITING_OFFICIAL_FINAL",
    "kickoff_bound_utc": KICKOFF,
    "frozen_forecast_row_count": 2,
}

SNAPSHOT = {
    "ncaa_contest_id": CONTEST_ID,
    "away_canonical_team_id": "SRC-002:TEAM:235",
    "home_canonical_team_id": "SRC-002:TEAM:2439",
    "away_source_display_name": "Memphis",
    "home_source_display_name": "UNLV",
    "source_published_game_date": "2026-08-29",
}

PREDECESSOR_PARTICIPANTS = [
    {"source_team_id": AWAY_ID, "source_display_name": "Memphis"},
    {"source_team_id": HOME_ID, "source_display_name": "UNLV"},
]


def prove(card: dict, **overrides) -> dict:
    kwargs = {
        "final_card": card,
        "frozen_contest_row": FROZEN_CONTEST,
        "snapshot_record": SNAPSHOT,
        "predecessor_participants": PREDECESSOR_PARTICIPANTS,
        "capture_identity": "capture",
    }
    kwargs.update(overrides)
    return prove_contest_orientation(**kwargs)


def sole_final(manifest: dict) -> dict:
    finals = manifest["official_finals"]
    assert len(finals) == 1, finals
    return finals[0]


class ScoreboardParsingTests(unittest.TestCase):
    def test_a_terminal_final_parses_with_ordered_participants_and_scores(self) -> None:
        cards = parse_scoreboard_cards(render_document())
        self.assertEqual(1, len(cards))
        card = cards[0]
        self.assertEqual(CONTEST_ID, card["ncaa_contest_id"])
        self.assertEqual(AWAY_ID, card["away_source_team_id"])
        self.assertEqual(HOME_ID, card["home_source_team_id"])
        self.assertEqual(27, card["away_points"])
        self.assertEqual(21, card["home_points"])
        self.assertEqual("AWAY", card["winner_orientation"])
        self.assertEqual(0, card["home_win"])
        self.assertTrue(card["final_status_is_terminal"])

    def test_the_source_published_date_comes_from_the_form_the_source_returned(self) -> None:
        self.assertEqual("2026-08-29", source_published_form_date(render_document()))

    def test_html_entities_in_a_team_name_are_decoded(self) -> None:
        cards = parse_scoreboard_cards(render_document(away_name="Texas A&amp;M"))
        self.assertEqual("Texas A&M", cards[0]["away_source_team_name"])


class CaptureAdmissibilityTests(unittest.TestCase):
    def test_a_source_date_substitution_cannot_become_an_admissible_final(self) -> None:
        manifest = manifest_for(
            (render_document(), "2026-08-27"),
            (render_document(), "2026-08-28"),
            (render_document(), "2026-08-29"),
        )
        self.assertEqual(3, manifest["capture_count"])
        self.assertEqual(2, manifest["source_substitution_capture_count"])
        self.assertEqual(1, manifest["admissible_final_capture_count"])
        self.assertEqual(1, manifest["unique_official_final_count"])
        self.assertEqual(1, len(manifest["official_finals"]))
        self.assertEqual(2, len(manifest["source_substitution_observations"]))
        for observation in manifest["source_substitution_observations"]:
            self.assertEqual(SUBSTITUTED, observation["admissibility"])
        self.assertEqual(ADMISSIBLE, manifest["official_finals"][0]["admissibility"])

    def test_the_substituted_captures_are_preserved_rather_than_discarded(self) -> None:
        manifest = manifest_for(
            (render_document(), "2026-08-27"),
            (render_document(), "2026-08-29"),
        )
        dates = [row["requested_game_date"] for row in manifest["captures"]]
        self.assertEqual(["2026-08-27", "2026-08-29"], dates)

    def test_altered_raw_bytes_are_rejected_against_the_declared_sha(self) -> None:
        entry = capture(render_document())
        entry["raw_sha256"] = "0" * 64
        with self.assertRaises(OfficialFinalScoringViolation):
            build_official_capture_manifest(
                captures=[entry], contract_sha256="contract", issued_at_utc="2026-08-31T02:00:00Z"
            )

    def test_a_non_terminal_card_never_becomes_an_official_final(self) -> None:
        manifest = manifest_for((render_document(terminal=False), "2026-08-29"))
        self.assertEqual([], manifest["official_finals"])
        self.assertEqual(0, manifest["unique_official_final_count"])

    def test_a_duplicate_conflicting_final_across_captures_fails_closed(self) -> None:
        with self.assertRaises(OfficialFinalScoringViolation):
            build_official_capture_manifest(
                captures=[
                    capture(render_document()),
                    capture(render_document(away_points=3, home_points=4)),
                ],
                contract_sha256="contract",
                issued_at_utc="2026-08-31T02:00:00Z",
            )

    def test_a_contest_rendered_twice_in_one_page_never_yields_a_final(self) -> None:
        document = render_document() + render_document(away_points=3, home_points=4)
        manifest = manifest_for((document, "2026-08-29"))
        self.assertEqual([], manifest["official_finals"])


class OrientationProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.card = sole_final(manifest_for((render_document(), "2026-08-29")))

    def test_a_clean_capture_proves_orientation(self) -> None:
        proof = prove(self.card)
        self.assertEqual("ORIENTATION_PROVEN", proof["proof_state"])
        self.assertEqual([], proof["failure_reasons"])
        self.assertTrue(proof["final_capture_after_kickoff"])

    def test_an_ordered_participant_swap_is_rejected(self) -> None:
        card = sole_final(
            manifest_for(
                (
                    render_document(
                        away_id=HOME_ID, away_name="UNLV", home_id=AWAY_ID, home_name="Memphis"
                    ),
                    "2026-08-29",
                )
            )
        )
        self.assertIn("ORDERED_PARTICIPANT_SWAP", prove(card)["failure_reasons"])

    def test_a_contest_substitution_is_rejected(self) -> None:
        card = sole_final(manifest_for((render_document(contest_id="9999999"), "2026-08-29")))
        self.assertIn("CONTEST_SUBSTITUTION", prove(card)["failure_reasons"])

    def test_a_name_only_match_without_the_source_identifier_is_rejected(self) -> None:
        card = sole_final(
            manifest_for((render_document(away_id="700001", home_id="700002"), "2026-08-29"))
        )
        self.assertIn("ORDERED_PARTICIPANT_IDENTITY_MISMATCH", prove(card)["failure_reasons"])

    def test_a_display_name_substitution_under_the_right_identifier_is_rejected(self) -> None:
        card = sole_final(manifest_for((render_document(away_name="Not Memphis"), "2026-08-29")))
        self.assertIn("ORDERED_PARTICIPANT_DISPLAY_NAME_MISMATCH", prove(card)["failure_reasons"])

    def test_an_absent_canonical_identity_is_reported(self) -> None:
        snapshot = dict(SNAPSHOT, home_canonical_team_id=None)
        proof = prove(self.card, snapshot_record=snapshot)
        self.assertIn(
            "CANONICAL_IDENTITY_ABSENT_FOR_AT_LEAST_ONE_PARTICIPANT", proof["failure_reasons"]
        )

    def test_a_changed_canonical_identity_changes_the_orientation_identity(self) -> None:
        baseline = prove(self.card)["contest_orientation_identity"]
        changed = prove(
            self.card, snapshot_record=dict(SNAPSHOT, home_canonical_team_id="SRC-002:TEAM:1")
        )["contest_orientation_identity"]
        self.assertNotEqual(baseline, changed)

    def test_a_final_captured_before_kickoff_is_rejected(self) -> None:
        frozen = dict(FROZEN_CONTEST, kickoff_bound_utc="2026-09-30T02:00:00Z")
        self.assertIn(
            "FINAL_CAPTURED_BEFORE_KICKOFF", prove(self.card, frozen_contest_row=frozen)["failure_reasons"]
        )

    def test_an_altered_raw_score_changes_the_outcome_and_the_orientation_identity(self) -> None:
        altered = sole_final(manifest_for((render_document(home_points=99), "2026-08-29")))
        self.assertEqual(1, altered["home_win"])
        self.assertNotEqual(
            prove(self.card)["contest_orientation_identity"],
            prove(altered)["contest_orientation_identity"],
        )

    def test_a_score_orientation_swap_reverses_the_recorded_winner(self) -> None:
        swapped = sole_final(
            manifest_for((render_document(away_points=21, home_points=27), "2026-08-29"))
        )
        self.assertEqual("HOME", swapped["winner_orientation"])
        self.assertEqual(0, self.card["home_win"])

    def test_an_inconsistent_winner_token_is_rejected(self) -> None:
        card = dict(self.card, winner_orientation="HOME")
        self.assertIn("WINNER_INCONSISTENT_WITH_SCORE", prove(card)["failure_reasons"])

    def test_a_tie_is_never_resolved_into_a_home_win(self) -> None:
        card = dict(self.card, home_points=21, away_points=21, winner_orientation="TIE", home_win=None)
        self.assertIn("UNRESOLVED_TIE", prove(card)["failure_reasons"])

    def test_an_altered_final_status_token_is_rejected(self) -> None:
        card = dict(self.card, final_status_is_terminal=False, final_status_text=None)
        self.assertIn("FINAL_STATUS_NOT_TERMINAL", prove(card)["failure_reasons"])

    def test_a_source_date_mismatch_promoted_into_a_final_is_rejected(self) -> None:
        card = dict(self.card, capture_source_published_game_date="2026-08-27")
        self.assertIn("SOURCE_DATE_MISMATCH", prove(card)["failure_reasons"])

    def test_a_kickoff_date_inconsistency_is_rejected(self) -> None:
        snapshot = dict(SNAPSHOT, source_published_game_date="2026-09-05")
        self.assertIn(
            "KICKOFF_DATE_INCONSISTENT", prove(self.card, snapshot_record=snapshot)["failure_reasons"]
        )


class IdentityTests(unittest.TestCase):
    FROZEN_ROW = {
        "ncaa_contest_id": CONTEST_ID,
        "candidate_id": "national_elo",
        "probability_home_win": 0.46300163,
        "forecast_state": "AWAITING_OFFICIAL_FINAL",
        "temporal_audit_verdict": "TEMPORAL_PROOF_COMPLETE",
    }

    def test_the_forecast_identity_is_not_the_contest_candidate_pair(self) -> None:
        identity = frozen_forecast_row_identity(self.FROZEN_ROW)
        self.assertNotEqual(f"{CONTEST_ID}::national_elo", identity)
        self.assertEqual(64, len(identity))

    def test_a_frozen_probability_change_changes_the_forecast_identity(self) -> None:
        mutated = dict(self.FROZEN_ROW, probability_home_win=0.99)
        self.assertNotEqual(
            frozen_forecast_row_identity(self.FROZEN_ROW), frozen_forecast_row_identity(mutated)
        )

    def test_any_frozen_row_field_change_changes_the_forecast_identity(self) -> None:
        mutated = dict(self.FROZEN_ROW, forecast_state="SCORED")
        self.assertNotEqual(
            frozen_forecast_row_identity(self.FROZEN_ROW), frozen_forecast_row_identity(mutated)
        )

    def test_the_temporal_identity_is_never_the_verdict_token(self) -> None:
        verdict = {"ncaa_contest_id": CONTEST_ID, "candidate_id": "national_elo", "verdict": "TEMPORAL_PROOF_COMPLETE"}
        identity = temporal_verdict_row_identity(verdict)
        self.assertNotEqual("TEMPORAL_PROOF_COMPLETE", identity)
        self.assertEqual(64, len(identity))

    def test_a_temporal_verdict_change_changes_the_temporal_identity(self) -> None:
        verdict = {"ncaa_contest_id": CONTEST_ID, "candidate_id": "national_elo", "verdict": "TEMPORAL_PROOF_COMPLETE"}
        mutated = dict(verdict, verdict="TEMPORAL_PROOF_INCOMPLETE")
        self.assertNotEqual(
            temporal_verdict_row_identity(verdict), temporal_verdict_row_identity(mutated)
        )

    def test_a_child_payload_mutation_changes_the_scoring_row_identity(self) -> None:
        row = {
            "ncaa_contest_id": CONTEST_ID,
            "candidate_id": "national_elo",
            "frozen_probability_home_win": 0.46300163,
            "home_win": 0,
            "official_raw_response_sha256": "a" * 64,
        }
        mutated = dict(row, official_raw_response_sha256="b" * 64)
        self.assertNotEqual(scoring_row_identity(row), scoring_row_identity(mutated))

    def test_the_scoring_row_identity_excludes_only_itself(self) -> None:
        row = {"ncaa_contest_id": CONTEST_ID, "home_win": 1}
        first = scoring_row_identity(row)
        self.assertEqual(first, scoring_row_identity(dict(row, scoring_row_identity=first)))


class MetricDenominatorTests(unittest.TestCase):
    ROWS = [
        {
            "ncaa_contest_id": str(6586325 + index),
            "candidate_id": "national_elo",
            "frozen_probability_home_win": probability,
            "home_win": outcome,
        }
        for index, (probability, outcome) in enumerate(
            [(0.46300163, 0), (0.75056252, 1), (0.5861017, 1), (0.38505461, 1), (0.53400243, 1), (0.500679, 0)]
        )
    ]

    def test_coverage_uses_the_candidates_own_opportunity_count(self) -> None:
        metrics = candidate_metrics(
            scored_rows=self.ROWS,
            predeclared_eligible_opportunity_count=6,
            pending_row_count=0,
            temporal_exclusion_count=0,
            unsupported_count=2,
            missed_cutoff_with_no_forecast_count=2,
        )
        self.assertEqual(6, metrics["scored_row_count"])
        self.assertEqual(6, metrics["predeclared_eligible_frozen_opportunity_count"])
        self.assertEqual(1.0, metrics["coverage"])
        self.assertEqual(0, metrics["abstention_count"])

    def test_a_pooled_denominator_would_understate_coverage_and_is_not_used(self) -> None:
        correct = candidate_metrics(
            scored_rows=self.ROWS,
            predeclared_eligible_opportunity_count=6,
            pending_row_count=0,
            temporal_exclusion_count=0,
            unsupported_count=0,
            missed_cutoff_with_no_forecast_count=0,
        )
        pooled = candidate_metrics(
            scored_rows=self.ROWS,
            predeclared_eligible_opportunity_count=12,
            pending_row_count=0,
            temporal_exclusion_count=0,
            unsupported_count=0,
            missed_cutoff_with_no_forecast_count=0,
        )
        self.assertEqual(1.0, correct["coverage"])
        self.assertEqual(0.5, pooled["coverage"])
        self.assertNotEqual(correct["coverage"], pooled["coverage"])

    def test_abstention_counts_only_unemitted_eligible_opportunities(self) -> None:
        metrics = candidate_metrics(
            scored_rows=self.ROWS[:4],
            predeclared_eligible_opportunity_count=6,
            pending_row_count=2,
            temporal_exclusion_count=0,
            unsupported_count=0,
            missed_cutoff_with_no_forecast_count=0,
        )
        self.assertEqual(2, metrics["abstention_count"])

    def test_the_brier_score_and_log_loss_are_the_declared_averages(self) -> None:
        metrics = candidate_metrics(
            scored_rows=self.ROWS,
            predeclared_eligible_opportunity_count=6,
            pending_row_count=0,
            temporal_exclusion_count=0,
            unsupported_count=0,
            missed_cutoff_with_no_forecast_count=0,
        )
        expected_brier = sum(
            (row["frozen_probability_home_win"] - row["home_win"]) ** 2 for row in self.ROWS
        ) / len(self.ROWS)
        self.assertAlmostEqual(expected_brier, metrics["brier_score"], places=12)
        self.assertNotAlmostEqual(expected_brier + 0.01, metrics["brier_score"], places=3)
        self.assertGreater(metrics["log_loss"], 0.0)

    def test_an_omitted_negative_result_changes_the_reported_metrics(self) -> None:
        full = candidate_metrics(
            scored_rows=self.ROWS,
            predeclared_eligible_opportunity_count=6,
            pending_row_count=0,
            temporal_exclusion_count=0,
            unsupported_count=0,
            missed_cutoff_with_no_forecast_count=0,
        )
        without_losses = [row for row in self.ROWS if row["home_win"] == 1]
        trimmed = candidate_metrics(
            scored_rows=without_losses,
            predeclared_eligible_opportunity_count=6,
            pending_row_count=0,
            temporal_exclusion_count=0,
            unsupported_count=0,
            missed_cutoff_with_no_forecast_count=0,
        )
        self.assertNotAlmostEqual(full["brier_score"], trimmed["brier_score"], places=6)
        self.assertLess(trimmed["coverage"], full["coverage"])

    def test_a_residual_is_only_defined_for_a_scored_row(self) -> None:
        empty = candidate_metrics(
            scored_rows=[],
            predeclared_eligible_opportunity_count=6,
            pending_row_count=6,
            temporal_exclusion_count=0,
            unsupported_count=0,
            missed_cutoff_with_no_forecast_count=0,
        )
        self.assertIsNone(empty["mean_signed_residual"])
        self.assertIsNone(empty["mean_absolute_residual"])
        self.assertEqual(0, empty["scored_row_count"])


class DirectionAndCalibrationTests(unittest.TestCase):
    def test_probability_exactly_one_half_has_no_direction(self) -> None:
        self.assertEqual("NO_DIRECTION", favorite_direction(0.5))
        self.assertEqual("HOME", favorite_direction(0.5000001))
        self.assertEqual("AWAY", favorite_direction(0.4999999))

    def test_no_direction_rows_are_excluded_from_directional_metrics(self) -> None:
        rows = [
            {"ncaa_contest_id": "1", "candidate_id": "c", "frozen_probability_home_win": 0.5, "home_win": 1},
            {"ncaa_contest_id": "2", "candidate_id": "c", "frozen_probability_home_win": 0.5, "home_win": 0},
        ]
        metrics = candidate_metrics(
            scored_rows=rows,
            predeclared_eligible_opportunity_count=2,
            pending_row_count=0,
            temporal_exclusion_count=0,
            unsupported_count=0,
            missed_cutoff_with_no_forecast_count=0,
        )
        self.assertEqual(0, metrics["directional_row_count"])
        self.assertEqual(2, metrics["no_direction_row_count"])
        self.assertIsNone(metrics["directional_accuracy"])

    def test_calibration_bins_carry_full_contents_and_a_tiny_sample_warning(self) -> None:
        rows = [
            {"ncaa_contest_id": "1", "candidate_id": "c", "frozen_probability_home_win": 0.55, "home_win": 1},
            {"ncaa_contest_id": "2", "candidate_id": "c", "frozen_probability_home_win": 0.58, "home_win": 0},
        ]
        populated = [row for row in calibration_bins(rows) if row["row_count"]]
        self.assertEqual(1, len(populated))
        bin_row = populated[0]
        self.assertEqual(0.5, bin_row["bin_lower"])
        self.assertEqual(0.6, bin_row["bin_upper"])
        self.assertEqual(2, bin_row["row_count"])
        self.assertAlmostEqual(0.565, bin_row["mean_predicted_probability"], places=12)
        self.assertEqual(1, bin_row["observed_wins"])
        self.assertEqual(0.5, bin_row["empirical_win_rate"])
        self.assertTrue(bin_row["tiny_sample_warning"])

    def test_a_wrong_bin_assignment_is_detectable(self) -> None:
        rows = [{"ncaa_contest_id": "1", "candidate_id": "c", "frozen_probability_home_win": 0.49, "home_win": 1}]
        populated = [row for row in calibration_bins(rows) if row["row_count"]]
        self.assertEqual(0.4, populated[0]["bin_lower"])
        self.assertNotEqual(0.5, populated[0]["bin_lower"])

    def test_probability_one_lands_in_the_terminal_bin(self) -> None:
        rows = [{"ncaa_contest_id": "1", "candidate_id": "c", "frozen_probability_home_win": 1.0, "home_win": 1}]
        populated = [row for row in calibration_bins(rows) if row["row_count"]]
        self.assertEqual(0.9, populated[0]["bin_lower"])
        self.assertEqual(1.0, populated[0]["bin_upper"])


class LaneAndClaimTests(unittest.TestCase):
    """The committed BAT-674 artifacts must never open a protected lane or claim value."""

    GATE = ROOT / "artifacts/shadow/week_zero_2026_official_final_scoring_successor_gate.json"

    def setUp(self) -> None:
        if not self.GATE.is_file():
            self.skipTest("the BAT-674 gate has not been materialized in this tree")
        self.gate = json.loads(self.GATE.read_text(encoding="utf-8"))

    def test_the_protected_lane_remains_blocked(self) -> None:
        self.assertEqual("RETAIN_PROTECTED_LANE_BLOCKED", self.gate["protected_lane"])
        self.assertEqual("PROSPECTIVE_SHADOW_OBSERVATION_ONLY", self.gate["lane"])

    def test_no_tuning_promotion_or_value_claim_is_recorded(self) -> None:
        nonclaims = self.gate["scientific_nonclaims"]
        self.assertTrue(nonclaims["no_bas_or_aggie_excess_claim"])
        self.assertTrue(nonclaims["no_production_or_specialization_claim"])
        self.assertTrue(nonclaims["no_tuning_selection_or_promotion_from_these_results"])
        self.assertTrue(nonclaims["tiny_population_no_calibration_or_champion_claim"])

    def test_no_backfilled_forecast_row_was_inserted(self) -> None:
        predecessor = json.loads(
            (ROOT / "artifacts/shadow/week_zero_2026_live_execution_gate.json").read_text(
                encoding="utf-8"
            )
        )
        frozen_keys = {
            (str(row["ncaa_contest_id"]), str(row["candidate_id"]))
            for row in predecessor["forecast_rows"]
        }
        payload = json.loads(
            (
                ROOT / "artifacts/shadow/week_zero_2026_official_final_scoring_successor_payload.json"
            ).read_text(encoding="utf-8")
        )
        scored_keys = {
            (str(row["ncaa_contest_id"]), str(row["candidate_id"]))
            for row in payload["scored_rows"]
        }
        self.assertTrue(scored_keys <= frozen_keys)

    def test_no_candidate_was_inserted_beyond_the_frozen_population(self) -> None:
        predecessor = json.loads(
            (ROOT / "artifacts/shadow/week_zero_2026_live_execution_gate.json").read_text(
                encoding="utf-8"
            )
        )
        frozen_candidates = {str(row["candidate_id"]) for row in predecessor["forecast_rows"]}
        self.assertEqual(frozen_candidates, set(self.gate["metrics_by_candidate"]))

    def test_the_coordinated_outer_rehash_of_a_mutated_gate_is_still_detectable(self) -> None:
        mutated = copy.deepcopy(self.gate)
        mutated["bound_child_artifact_identities"]["scoring_payload_identity"] = "0" * 64
        self.assertNotEqual(
            self.gate["bound_child_artifact_identities"]["scoring_payload_identity"],
            mutated["bound_child_artifact_identities"]["scoring_payload_identity"],
        )
        payload = json.loads(
            (
                ROOT / "artifacts/shadow/week_zero_2026_official_final_scoring_successor_payload.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            self.gate["bound_child_artifact_identities"]["scoring_payload_identity"],
            payload["payload_identity"],
        )

    def test_every_authority_bearing_child_identity_is_bound(self) -> None:
        bound = self.gate["bound_child_artifact_identities"]
        for key in (
            "contract_sha256",
            "core_module_sha256",
            "crosswalk_identity",
            "official_capture_identity",
            "producer_sha256",
            "reconciliation_gate_identity",
            "residual_payload_identity",
            "scoring_payload_identity",
            "temporal_audit_gate_identity",
            "temporal_audit_sha256",
            "transition_ledger_identity",
            "validator_sha256",
        ):
            self.assertIn(key, bound)
            self.assertTrue(bound[key])

    def test_the_historical_blocked_artifacts_declare_supersession(self) -> None:
        for relative in (
            "artifacts/shadow/week_zero_2026_official_final_acquisition_blocked_gate.json",
            "artifacts/shadow/week_zero_2026_official_final_acquisition_blocked_replay.json",
        ):
            payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            supersession = payload["supersession"]
            self.assertTrue(supersession["historical_attempt"])
            self.assertFalse(supersession["current_authority"])
            self.assertEqual(
                self.gate["gate_identity"],
                supersession["superseded_by_scoring_gate_identity"],
            )
            self.assertEqual(
                self.gate["bound_child_artifact_identities"]["official_capture_identity"],
                supersession["superseded_by_successful_capture_identity"],
            )

    def test_timing_states_are_truthful_for_every_scored_contest(self) -> None:
        for row in self.gate["contest_rows"]:
            if row["contest_state"] != "SCORED":
                continue
            self.assertEqual("KICKOFF_BOUND_HAS_ELAPSED", row["timing_state"])
            self.assertTrue(row["final_capture_after_kickoff"])
            self.assertTrue(row["official_status_retrieved_at_utc"])

    def test_the_six_proven_contests_are_not_labelled_unresolved_abstain(self) -> None:
        crosswalk = json.loads(
            (ROOT / "artifacts/shadow/week_zero_2026_cfbd_crosswalk.json").read_text(
                encoding="utf-8"
            )
        )
        proven = [
            row
            for row in crosswalk["rows"]
            if row["ncaa_identity_disposition"]
            == "NCAA_PREDECESSOR_CONTEST_ID_AND_ORIENTATION_EXACT"
        ]
        self.assertEqual(6, len(proven))
        for row in crosswalk["rows"]:
            self.assertNotEqual("UNRESOLVED_ABSTAIN", row["ncaa_identity_disposition"])
            self.assertTrue(row["cfbd_absence_is_enrichment_limitation_not_identity_failure"])


if __name__ == "__main__":
    unittest.main()
