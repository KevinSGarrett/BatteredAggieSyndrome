"""Cycle34 R34-03..09 regression tests for MR33-01/02/03/04/05/06/07/09/10.

Each test in this file fails against the preserved Cycle33 predecessor
(`C:\\BatteredAggieSyndrome.data\\worktrees\\cycle33-scr`, head
1981381c049669047e792b23c502bbbd2f050cc2 -- see
C:\\BatteredAggieSyndrome.data\\ops\\cycle34\\20260919T_R34_receipts\\PRESERVATION_RECEIPT.md
for the exact predecessor file hashes) and passes against this cycle34-repair
worktree. These are executable regression tests, not the manager's ad hoc
`probe_cycle33.py` synthetic challenge script (which used deliberately
insufficient fixtures and is not itself a committed regression suite).
"""

from __future__ import annotations

import math
import unittest
from datetime import datetime, timedelta, timezone

from aggie_analytics.cycle30.kernel_model import KernelModelError, fold_local_fit
from aggie_analytics.cycle33.all22_adapter import (
    encode_episode,
    verify_lossless_round_trip,
)
from aggie_analytics.cycle33.career_identity import join_occupant_to_pages
from aggie_analytics.cycle33.confirmed_spans import quarantine_unlocatable_cell
from aggie_analytics.cycle33.fit_integrity import (
    FitIntegrityError,
    validate_fit_population,
)
from aggie_analytics.cycle33.forecast_inventory import inspect_forecast_eligibility
from aggie_analytics.cycle33.neutral import NeutralVenueError, travel_context
from aggie_analytics.cycle33.official_finals import competing_observations
from aggie_analytics.cycle33.scoring_successor import (
    freeze_is_proven,
    score_unique_frozen_games,
)

FINAL = {
    "game_state": "F",
    "status_code_display": "final",
    "terminal_state": "TERMINAL_STATUS_ESTABLISHED",
}


def _receipt(*, contest, candidate, cohort, checkpoint, receipt_id, frozen_at):
    return {
        "receipt_id": receipt_id,
        "receipt_sha256": "a" * 64,
        "frozen_at_utc": frozen_at,
        "ncaa_contest_id": contest,
        "candidate_id": candidate,
        "cohort": cohort,
        "checkpoint": checkpoint,
    }


def _proven_forecast(*, probability, row_id, receipt_id="RECEIPT-1"):
    return {
        **FINAL,
        "ncaa_contest_id": "TEST:GAME:1",
        "candidate_id": "TEST:MODEL",
        "cohort": "TEST:COHORT",
        "checkpoint": "TEST:EARLY",
        "forecast_row_id": row_id,
        "frozen": True,
        "probability_home": probability,
        "freeze_receipt": _receipt(
            contest="TEST:GAME:1",
            candidate="TEST:MODEL",
            cohort="TEST:COHORT",
            checkpoint="TEST:EARLY",
            receipt_id=receipt_id,
            frozen_at="2026-01-01T00:00:00Z",
        ),
    }


class FreezeProofTests(unittest.TestCase):
    """MR33-01: a fake row id and an unparseable timestamp must not prove a freeze."""

    def test_row_id_reused_as_receipt_id_is_rejected(self) -> None:
        forecast = {
            "forecast_row_id": "NOT-A-RECEIPT",
            "frozen": True,
            "freeze_receipt": {
                "receipt_id": "NOT-A-RECEIPT",  # same as row id -- must be rejected
                "receipt_sha256": "a" * 64,
                "frozen_at_utc": "2026-01-01T00:00:00Z",
            },
        }
        self.assertFalse(freeze_is_proven(forecast))

    def test_invalid_timestamp_is_rejected(self) -> None:
        forecast = {
            "forecast_row_id": "ROW-1",
            "frozen": True,
            "freeze_receipt": {
                "receipt_id": "RECEIPT-1",
                "receipt_sha256": "a" * 64,
                "frozen_at_utc": "not-a-date",
            },
        }
        self.assertFalse(freeze_is_proven(forecast))

    def test_bare_frozen_boolean_without_receipt_mapping_is_rejected(self) -> None:
        forecast = {"frozen": True, "forecast_row_id": "ROW-2"}
        self.assertFalse(freeze_is_proven(forecast))

    def test_genuine_receipt_proves_freeze(self) -> None:
        forecast = _proven_forecast(probability=0.8, row_id="ROW-3")
        self.assertTrue(freeze_is_proven(forecast))

    def test_score_unique_frozen_games_rejects_the_original_synthetic_defect(self) -> None:
        game = {
            **FINAL,
            "ncaa_contest_id": "TEST:GAME:1",
            "home_points": 30,
            "away_points": 10,
            "home_name": "Home",
            "away_name": "Away",
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
        }
        forecast = {
            "ncaa_contest_id": "TEST:GAME:1",
            "candidate_id": "TEST:MODEL",
            "cohort": "TEST:COHORT",
            "checkpoint": "TEST:EARLY",
            "forecast_row_id": "NOT-A-RECEIPT",
            "frozen": True,
            "frozen_at_utc": "not-a-date",
            "probability_home": 0.8,
        }
        result = score_unique_frozen_games([game], forecasts=[forecast])
        self.assertEqual(result["scored_candidate_checkpoint_rows"], 0)


class ConflictingForecastOrderTests(unittest.TestCase):
    """MR33-02: conflicting proven forecasts quarantine; scoring is order-invariant."""

    def _game(self):
        return {
            **FINAL,
            "ncaa_contest_id": "TEST:GAME:1",
            "home_points": 30,
            "away_points": 10,
            "home_name": "Home",
            "away_name": "Away",
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
        }

    def test_conflicting_probabilities_are_quarantined_not_first_won(self) -> None:
        f1 = _proven_forecast(probability=0.8, row_id="ROW-A", receipt_id="RECEIPT-A")
        f2 = _proven_forecast(probability=0.2, row_id="ROW-B", receipt_id="RECEIPT-B")
        forward = score_unique_frozen_games([self._game()], forecasts=[f1, f2])
        reverse = score_unique_frozen_games([self._game()], forecasts=[f2, f1])
        self.assertEqual(forward["brier_mean"], reverse["brier_mean"])
        self.assertIsNone(forward["brier_mean"])
        self.assertEqual(forward["scored_candidate_checkpoint_rows"], 0)
        self.assertEqual(forward["quarantined_conflicting_forecast_keys"], 1)
        self.assertEqual(reverse["quarantined_conflicting_forecast_keys"], 1)

    def test_identical_duplicate_forecasts_deduplicate_and_score_once(self) -> None:
        f1 = _proven_forecast(probability=0.8, row_id="ROW-A", receipt_id="RECEIPT-A")
        f2 = _proven_forecast(probability=0.8, row_id="ROW-B", receipt_id="RECEIPT-B")
        result = score_unique_frozen_games([self._game()], forecasts=[f1, f2])
        self.assertEqual(result["scored_candidate_checkpoint_rows"], 1)
        self.assertEqual(result["rejected_duplicate_forecasts"], 1)


class OfficialFinalCanonicalIdTests(unittest.TestCase):
    """MR33-03: a display-name match must never hide a conflicting canonical ID."""

    def test_same_names_conflicting_canonical_ids_are_quarantined(self) -> None:
        game = {
            **FINAL,
            "ncaa_contest_id": "TEST:GAME:1",
            "home_points": 30,
            "away_points": 10,
            "home_name": "Home",
            "away_name": "Away",
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
        }
        conflicting = {**game, "home_canonical_team_id": "WRONG:PROGRAM"}
        result = competing_observations([game, conflicting])
        self.assertEqual(len(result["admitted_unique_games"]), 0)
        self.assertEqual(len(result["quarantined_conflicts"]), 1)

    def test_lawful_progression_still_admits_one_final(self) -> None:
        game = {
            **FINAL,
            "ncaa_contest_id": "TEST:GAME:1",
            "home_points": 30,
            "away_points": 10,
            "home_name": "Home",
            "away_name": "Away",
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
        }
        live = {**game, "game_state": "L", "status_code_display": "live"}
        result = competing_observations([live, game])
        self.assertEqual(len(result["admitted_unique_games"]), 1)
        self.assertEqual(result["quarantined_conflicts"], [])


class CareerJoinIdentityTests(unittest.TestCase):
    """MR33-04: the join itself rejects a wrong-person page, same employer or not."""

    def test_wrong_person_same_employer_page_is_rejected(self) -> None:
        page = {
            "title": "Different Person (American football)",
            "page_id": 123,
            "revision": 456,
            "episodes": [
                {
                    "person": "Different Person",
                    "program_raw": "Example University",
                    "sport": "American football",
                    "role": "HC",
                    "start_year": 2001,
                    "end_year": 2002,
                }
            ],
        }
        result = join_occupant_to_pages(
            person="Target Person", program_display="Example University", pages=[page]
        )
        self.assertNotEqual(result["career_join_state"], "EVIDENCE_BOUND_CAREER_JOIN")
        self.assertEqual(
            result["career_join_state"], "FOOTBALL_PAGE_PERSON_IDENTITY_UNMATCHED"
        )

    def test_correct_person_same_employer_page_is_bound(self) -> None:
        page = {
            "title": "Target Person (American football)",
            "page_id": 999,
            "revision": 1,
            "episodes": [
                {
                    "person": "Target Person",
                    "program_raw": "Example University",
                    "sport": "American football",
                    "role": "HC",
                    "start_year": 2001,
                    "end_year": 2002,
                }
            ],
        }
        result = join_occupant_to_pages(
            person="Target Person", program_display="Example University", pages=[page]
        )
        self.assertEqual(result["career_join_state"], "EVIDENCE_BOUND_CAREER_JOIN")


class PartialCellConservationTests(unittest.TestCase):
    """MR33-05: a supported + an unsupported-but-locatable episode both survive."""

    def test_unsupported_locatable_episode_is_quarantined_not_dropped(self) -> None:
        cell = {
            "disposition": "CONFIRMED_CO_SHARED_ROLE",
            "episode_refs": [
                {"person": "Supported", "role_claim_supported": True, "locatable": True},
                {
                    "person": "Unsupported",
                    "role_claim_supported": False,
                    "locatable": True,
                },
            ],
        }
        result = quarantine_unlocatable_cell(cell)
        kept = len(result["episode_refs"]) + len(
            result.get("quarantined_unlocatable_episodes", [])
        )
        self.assertEqual(kept, 2)
        self.assertEqual(len(result["quarantined_unlocatable_episodes"]), 1)
        self.assertEqual(
            result["quarantined_unlocatable_episodes"][0]["person"], "Unsupported"
        )


class LosslessTransportTests(unittest.TestCase):
    """MR33-06: identity/temporal/provenance fields must survive encode_episode."""

    def _episode(self):
        return {
            "person": "Example Person",
            "person_id": "PERSON:1",
            "program_id": "PROGRAM:1",
            "season": 2026,
            "role": "OC",
            "source_title": "Offensive Coordinator",
            "source_class": "OFFICIAL",
            "valid_time_precision": "DAY",
            "recorded_at_utc": "2026-09-01T00:00:00Z",
            "schema_version": "v1",
            "valid_from": "2026-01-01",
            "valid_to": None,
            "receipt_sha256": "a" * 64,
            "source_span": "p1:line10",
            "qualifiers": ["CO_SHARED"],
        }

    def test_encode_episode_preserves_mandatory_identity_fields(self) -> None:
        episode = self._episode()
        encoded = encode_episode(episode)
        missing = sorted(set(episode) - set(encoded))
        self.assertEqual(missing, [])
        for field in ("program_id", "person_id", "season", "valid_from", "receipt_sha256", "source_span"):
            self.assertEqual(encoded[field], episode[field])

    def test_verify_lossless_round_trip_reports_truthfully(self) -> None:
        report = verify_lossless_round_trip(self._episode())
        self.assertTrue(report["lossless"])
        self.assertEqual(report["missing_fields"], [])

    def test_verify_lossless_round_trip_catches_a_dropped_field(self) -> None:
        episode = self._episode()
        del episode["program_id"]
        report = verify_lossless_round_trip(episode)
        self.assertFalse(report["lossless"])


class NeutralTravelSemanticsTests(unittest.TestCase):
    """MR33-07: strict boolean neutral state and validated distances."""

    def test_none_neutral_site_stays_unknown_not_false(self) -> None:
        result = travel_context(
            {"neutral_site": None}, home_distance=50.0, away_distance=60.0, venue_confirmed=True
        )
        self.assertIsNone(result["neutral_site"])
        self.assertEqual(result["neutral_state"], "UNKNOWN")
        self.assertIsNone(result["ordinary_home_advantage"])

    def test_string_false_is_not_coerced_true(self) -> None:
        result = travel_context(
            {"neutral_site": "false"}, home_distance=50.0, away_distance=60.0, venue_confirmed=True
        )
        self.assertIs(result["neutral_site"], False)
        self.assertEqual(result["neutral_state"], "FALSE")

    def test_confirmed_neutral_has_zero_ordinary_home_exposure(self) -> None:
        result = travel_context(
            {"neutral_site": True}, home_distance=10.0, away_distance=10.0, venue_confirmed=True
        )
        self.assertEqual(result["ordinary_home_advantage"], 0.0)

    def test_negative_distance_is_rejected(self) -> None:
        with self.assertRaises(NeutralVenueError):
            travel_context(
                {"neutral_site": True}, home_distance=-1, away_distance=10.0, venue_confirmed=True
            )

    def test_nan_distance_is_rejected(self) -> None:
        with self.assertRaises(NeutralVenueError):
            travel_context(
                {"neutral_site": True},
                home_distance=10.0,
                away_distance=float("nan"),
                venue_confirmed=True,
            )


class FitPopulationIdentityTests(unittest.TestCase):
    """MR33-09: rows without a canonical game id must be rejected, not silently fit."""

    def test_validate_fit_population_rejects_unidentified_rows(self) -> None:
        with self.assertRaises(FitIntegrityError):
            validate_fit_population(
                [{"season": 2020}, {"season": 2020}],
                train_seasons=[2020],
                eval_seasons=[2021],
            )

    def test_fold_local_fit_public_entry_rejects_unidentified_rows(self) -> None:
        with self.assertRaises(KernelModelError):
            fold_local_fit(
                [
                    {"season": 2020, "home_win_label": 1},
                    {"season": 2021, "home_win_label": 0},
                ],
                candidate="intercept_only",
                train_seasons=[2020],
                eval_seasons=[2021],
            )

    def test_fold_local_fit_accepts_identified_rows(self) -> None:
        result = fold_local_fit(
            [
                {"season": 2020, "home_win_label": 1, "canonical_game_id": "G1"},
                {"season": 2021, "home_win_label": 0, "canonical_game_id": "G2"},
            ],
            candidate="intercept_only",
            train_seasons=[2020],
            eval_seasons=[2021],
        )
        self.assertEqual(result["train_games"], 1)
        self.assertEqual(result["eval_games"], 1)


class ForecastInventoryForgeryTests(unittest.TestCase):
    """MR33-10: a forged-metadata packet with no actual forecast is INELIGIBLE."""

    def test_forged_receipt_without_forecast_content_is_ineligible(self, tmp_path=None) -> None:
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_forecast.json"
            path.write_text(
                json.dumps(
                    {
                        "receipt_sha256": "fake",
                        "issued_at_utc": "not-a-date",
                        "known_at_utc": "not-a-date",
                        "contest_id": "TEST:1",
                    }
                ),
                encoding="utf-8",
            )
            result = inspect_forecast_eligibility(path)
            self.assertEqual(result["eligibility_verdict"], "INELIGIBLE")
            self.assertIn("RECEIPT_SHA256_NOT_WELL_FORMED", result["failed_predicates"])
            self.assertIn("MISSING_ACTUAL_FORECAST_CONTENT", result["failed_predicates"])

    def test_genuine_packet_with_forecast_content_is_eligible(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "genuine_forecast.json"
            path.write_text(
                json.dumps(
                    {
                        "receipt_sha256": "a" * 64,
                        "issued_at_utc": "2026-01-01T00:00:00Z",
                        "known_at_utc": "2026-01-01T00:00:00Z",
                        "contest_id": "TEST:1",
                        "probability_home": 0.62,
                    }
                ),
                encoding="utf-8",
            )
            result = inspect_forecast_eligibility(path)
            self.assertEqual(result["eligibility_verdict"], "ELIGIBLE")


if __name__ == "__main__":
    unittest.main()
