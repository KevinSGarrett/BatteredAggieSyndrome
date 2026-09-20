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

import hashlib
import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    resolve_receipt_evidence,
    score_unique_frozen_games,
)

FINAL = {
    "game_state": "F",
    "status_code_display": "final",
    "terminal_state": "TERMINAL_STATUS_ESTABLISHED",
}


def _write_real_evidence(
    tmp_dir: Path,
    *,
    contest="TEST:GAME:1",
    candidate="TEST:MODEL",
    cohort="TEST:COHORT",
    checkpoint="TEST:EARLY",
    probability,
    frozen_at="2026-01-01T00:00:00Z",
) -> str:
    """Write a REAL forecast-packet JSON file to disk and return its ACTUAL
    sha256 (computed from the bytes just written, never invented)."""

    payload = {
        "ncaa_contest_id": contest,
        "candidate_id": candidate,
        "cohort": cohort,
        "checkpoint": checkpoint,
        "probability_home": probability,
        "frozen_at_utc": frozen_at,
    }
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    (tmp_dir / f"forecast_{digest}.json").write_bytes(raw)
    return digest


def _evidence_bound_forecast(
    tmp_dir: Path,
    *,
    probability,
    row_id,
    receipt_id,
    contest="TEST:GAME:1",
    candidate="TEST:MODEL",
    cohort="TEST:COHORT",
    checkpoint="TEST:EARLY",
    frozen_at="2026-01-01T00:00:00Z",
    evidence_probability=None,
) -> dict:
    """A forecast row whose freeze_receipt resolves to REAL backing bytes on
    disk (not merely a self-declared hash string). `evidence_probability`
    lets a test deliberately write evidence that disagrees with the row's
    own claimed probability, to exercise the altered-evidence rejection."""

    digest = _write_real_evidence(
        tmp_dir,
        contest=contest,
        candidate=candidate,
        cohort=cohort,
        checkpoint=checkpoint,
        probability=evidence_probability if evidence_probability is not None else probability,
        frozen_at=frozen_at,
    )
    return {
        **FINAL,
        "ncaa_contest_id": contest,
        "candidate_id": candidate,
        "cohort": cohort,
        "checkpoint": checkpoint,
        "forecast_row_id": row_id,
        "frozen": True,
        "probability_home": probability,
        "freeze_receipt": {
            "receipt_id": receipt_id,
            "receipt_sha256": digest,
            "frozen_at_utc": frozen_at,
            "ncaa_contest_id": contest,
            "candidate_id": candidate,
            "cohort": cohort,
            "checkpoint": checkpoint,
        },
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


class FreezeProofEvidenceResolutionTests(unittest.TestCase):
    """MR33-01 re-repair: the manager's exact counterexample against HEAD
    4b1d4980 -- an invented receipt_id + receipt_sha256="a"*64 + a plausible
    historical timestamp + matching self-declared contest/candidate/cohort/
    checkpoint fields, with NO backing receipt or forecast artifact anywhere
    -- must fail closed. A NEW class, not a modification of FreezeProofTests
    above, per the manager's explicit requirement that this be a new test."""

    def test_invented_receipt_no_backing_artifact_is_rejected(self) -> None:
        """The exact manager counterexample. Note: `search_roots=()` makes
        the "no backing artifact anywhere" condition explicit and
        deterministic for the test -- resolve_receipt_evidence would also
        correctly return None against the real (empty-of-this-hash) default
        archive roots, but pinning search_roots removes any dependency on
        what else happens to exist on disk when this test runs."""

        forecast = {
            **FINAL,
            "ncaa_contest_id": "TEST:GAME:1",
            "candidate_id": "TEST:MODEL",
            "cohort": "TEST:COHORT",
            "checkpoint": "TEST:EARLY",
            "forecast_row_id": "SOME-OTHER-ROW-ID",
            "frozen": True,
            "probability_home": 0.8,
            "freeze_receipt": {
                "receipt_id": "INVENTED-RECEIPT-999",
                "receipt_sha256": "a" * 64,
                "frozen_at_utc": "2026-01-01T00:00:00Z",
                "ncaa_contest_id": "TEST:GAME:1",
                "candidate_id": "TEST:MODEL",
                "cohort": "TEST:COHORT",
                "checkpoint": "TEST:EARLY",
            },
        }
        self.assertFalse(freeze_is_proven(forecast, search_roots=()))
        # And through the full scoring entry point, not just the predicate:
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
        result = score_unique_frozen_games(
            [game], forecasts=[forecast], search_roots=()
        )
        self.assertEqual(result["scored_candidate_checkpoint_rows"], 0)

    def test_evidence_bound_receipt_with_real_backing_bytes_is_proven(self) -> None:
        """The required positive counterpart: a real, resolvable receipt
        with real backing bytes on disk correctly passes."""

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            forecast = _evidence_bound_forecast(
                tmp, probability=0.8, row_id="ROW-REAL", receipt_id="RECEIPT-REAL"
            )
            self.assertTrue(freeze_is_proven(forecast, search_roots=(tmp,)))
            resolved = resolve_receipt_evidence(
                forecast["freeze_receipt"]["receipt_sha256"], search_roots=(tmp,)
            )
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved["payload"]["probability_home"], 0.8)

    def test_receipt_hash_with_no_matching_file_in_real_search_roots_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            # Deliberately do NOT write any file -- the directory exists but
            # is empty, so the claimed hash cannot resolve to anything.
            forecast = {
                **FINAL,
                "ncaa_contest_id": "TEST:GAME:1",
                "candidate_id": "TEST:MODEL",
                "cohort": "TEST:COHORT",
                "checkpoint": "TEST:EARLY",
                "forecast_row_id": "ROW-EMPTY",
                "frozen": True,
                "probability_home": 0.8,
                "freeze_receipt": {
                    "receipt_id": "RECEIPT-EMPTY",
                    "receipt_sha256": "b" * 64,
                    "frozen_at_utc": "2026-01-01T00:00:00Z",
                    "ncaa_contest_id": "TEST:GAME:1",
                    "candidate_id": "TEST:MODEL",
                    "cohort": "TEST:COHORT",
                    "checkpoint": "TEST:EARLY",
                },
            }
            self.assertFalse(freeze_is_proven(forecast, search_roots=(tmp,)))

    def test_receipt_pointing_at_unrelated_evidence_is_rejected(self) -> None:
        """Real, resolvable evidence exists -- but it is about a different
        contest. The claimed hash resolves; the content does not match."""

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            digest = _write_real_evidence(
                tmp, contest="TEST:GAME:UNRELATED", probability=0.8
            )
            forecast = {
                **FINAL,
                "ncaa_contest_id": "TEST:GAME:1",
                "candidate_id": "TEST:MODEL",
                "cohort": "TEST:COHORT",
                "checkpoint": "TEST:EARLY",
                "forecast_row_id": "ROW-UNRELATED",
                "frozen": True,
                "probability_home": 0.8,
                "freeze_receipt": {
                    "receipt_id": "RECEIPT-UNRELATED",
                    "receipt_sha256": digest,
                    "frozen_at_utc": "2026-01-01T00:00:00Z",
                    "ncaa_contest_id": "TEST:GAME:1",
                    "candidate_id": "TEST:MODEL",
                    "cohort": "TEST:COHORT",
                    "checkpoint": "TEST:EARLY",
                },
            }
            self.assertFalse(freeze_is_proven(forecast, search_roots=(tmp,)))

    def test_receipt_pointing_at_altered_evidence_is_rejected(self) -> None:
        """Real, resolvable evidence for the correct contest/candidate/
        cohort/checkpoint exists -- but its own declared probability
        disagrees with the row being scored (the number was changed after
        the fact). The resolved payload is the source of truth, not the
        row's own probability_home field."""

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            forecast = _evidence_bound_forecast(
                tmp,
                probability=0.8,
                row_id="ROW-ALTERED",
                receipt_id="RECEIPT-ALTERED",
                evidence_probability=0.35,  # backing evidence disagrees
            )
            self.assertFalse(freeze_is_proven(forecast, search_roots=(tmp,)))

    def test_replay_is_deterministic_across_different_as_of_reference_times(self) -> None:
        """Running the check with different explicit `as_of_utc` reference
        times (standing in for "different wall-clock times") must not
        change the result, as long as the reference stays after the
        evidence's own frozen_at_utc. This is what makes the check
        deterministic under replay rather than merely monotonic-by-luck."""

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            forecast = _evidence_bound_forecast(
                tmp,
                probability=0.8,
                row_id="ROW-DET",
                receipt_id="RECEIPT-DET",
                frozen_at="2026-01-01T00:00:00Z",
            )
            near = datetime(2026, 1, 2, tzinfo=timezone.utc)
            far = datetime(2030, 1, 1, tzinfo=timezone.utc)
            self.assertTrue(
                freeze_is_proven(forecast, search_roots=(tmp,), as_of_utc=near)
            )
            self.assertTrue(
                freeze_is_proven(forecast, search_roots=(tmp,), as_of_utc=far)
            )
            # A reference time BEFORE the evidence's own frozen_at_utc must
            # correctly reject it as not-yet-frozen-as-of-then.
            before = datetime(2025, 12, 31, tzinfo=timezone.utc)
            self.assertFalse(
                freeze_is_proven(forecast, search_roots=(tmp,), as_of_utc=before)
            )

    def test_score_unique_frozen_games_shares_one_as_of_reference_per_call(self) -> None:
        """score_unique_frozen_games resolves as_of_utc ONCE per call and
        threads it through every row, rather than re-reading the system
        clock per forecast -- verified here by injecting a fixed as_of_utc
        and confirming two full calls at that fixed reference are
        byte-identical regardless of when the test itself actually runs."""

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
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
            forecast = _evidence_bound_forecast(
                tmp, probability=0.8, row_id="ROW-FIXED", receipt_id="RECEIPT-FIXED"
            )
            fixed_reference = datetime(2027, 6, 15, tzinfo=timezone.utc)
            first = score_unique_frozen_games(
                [game], forecasts=[forecast], search_roots=(tmp,), as_of_utc=fixed_reference
            )
            second = score_unique_frozen_games(
                [game], forecasts=[forecast], search_roots=(tmp,), as_of_utc=fixed_reference
            )
            self.assertEqual(first["scored_rows"], second["scored_rows"])
            self.assertEqual(first["as_of_utc"], second["as_of_utc"])
            self.assertEqual(first["scored_candidate_checkpoint_rows"], 1)


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
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            f1 = _evidence_bound_forecast(
                tmp, probability=0.8, row_id="ROW-A", receipt_id="RECEIPT-A"
            )
            f2 = _evidence_bound_forecast(
                tmp, probability=0.2, row_id="ROW-B", receipt_id="RECEIPT-B"
            )
            forward = score_unique_frozen_games(
                [self._game()], forecasts=[f1, f2], search_roots=(tmp,)
            )
            reverse = score_unique_frozen_games(
                [self._game()], forecasts=[f2, f1], search_roots=(tmp,)
            )
            self.assertEqual(forward["brier_mean"], reverse["brier_mean"])
            self.assertIsNone(forward["brier_mean"])
            self.assertEqual(forward["scored_candidate_checkpoint_rows"], 0)
            self.assertEqual(forward["quarantined_conflicting_forecast_keys"], 1)
            self.assertEqual(reverse["quarantined_conflicting_forecast_keys"], 1)

    def test_identical_duplicate_forecasts_deduplicate_and_score_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            f1 = _evidence_bound_forecast(
                tmp, probability=0.8, row_id="ROW-A", receipt_id="RECEIPT-A"
            )
            f2 = _evidence_bound_forecast(
                tmp, probability=0.8, row_id="ROW-B", receipt_id="RECEIPT-B"
            )
            result = score_unique_frozen_games(
                [self._game()], forecasts=[f1, f2], search_roots=(tmp,)
            )
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
        import tempfile
        from pathlib import Path

        from aggie_analytics.cycle33.forecast_inventory import (
            _canonical_payload_digest,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "genuine_forecast.json"
            payload = {
                "issued_at_utc": "2026-01-01T00:00:00Z",
                "known_at_utc": "2026-01-01T00:00:00Z",
                "contest_id": "TEST:1",
                "probability_home": 0.62,
            }
            # MR33-10 re-repair: receipt_sha256 must be the ACTUAL digest of
            # this payload's own bytes, computed independently here -- not an
            # invented placeholder that merely satisfies the hex64 shape.
            payload["receipt_sha256"] = _canonical_payload_digest(payload)
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = inspect_forecast_eligibility(path)
            self.assertEqual(result["eligibility_verdict"], "ELIGIBLE")


class ForecastInventoryInventedHashTests(unittest.TestCase):
    """MR33-10 re-repair: the manager's exact counterexample pattern applied
    to forecast_inventory.py -- a plausible-looking hex64 receipt_sha256
    with no genuine relationship to the payload it claims to describe (an
    invented value, or one copied from an unrelated packet) must be
    INELIGIBLE, not merely format-valid. A NEW class, not a modification of
    ForecastInventoryForgeryTests above."""

    def test_well_formed_but_invented_hash_is_rejected(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invented_hash_forecast.json"
            path.write_text(
                json.dumps(
                    {
                        # Exactly the manager's counterexample shape: a
                        # plausible, well-formed-looking hash with no real
                        # relationship to this payload's actual bytes.
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
            self.assertEqual(result["eligibility_verdict"], "INELIGIBLE")
            self.assertIn(
                "RECEIPT_SHA256_DOES_NOT_MATCH_PAYLOAD_BYTES",
                result["failed_predicates"],
            )

    def test_hash_copied_from_a_different_unrelated_packet_is_rejected(self) -> None:
        import tempfile
        from pathlib import Path

        from aggie_analytics.cycle33.forecast_inventory import (
            _canonical_payload_digest,
        )

        with tempfile.TemporaryDirectory() as tmp:
            unrelated_payload = {
                "issued_at_utc": "2025-01-01T00:00:00Z",
                "known_at_utc": "2025-01-01T00:00:00Z",
                "contest_id": "TEST:OTHER",
                "probability_home": 0.10,
            }
            borrowed_hash = _canonical_payload_digest(unrelated_payload)
            path = Path(tmp) / "borrowed_hash_forecast.json"
            path.write_text(
                json.dumps(
                    {
                        "receipt_sha256": borrowed_hash,  # a REAL hash -- just not this payload's
                        "issued_at_utc": "2026-01-01T00:00:00Z",
                        "known_at_utc": "2026-01-01T00:00:00Z",
                        "contest_id": "TEST:1",
                        "probability_home": 0.62,
                    }
                ),
                encoding="utf-8",
            )
            result = inspect_forecast_eligibility(path)
            self.assertEqual(result["eligibility_verdict"], "INELIGIBLE")
            self.assertIn(
                "RECEIPT_SHA256_DOES_NOT_MATCH_PAYLOAD_BYTES",
                result["failed_predicates"],
            )


if __name__ == "__main__":
    unittest.main()
