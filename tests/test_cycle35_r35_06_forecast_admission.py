"""R35-06 regression tests for MR34-01 and MR34-02.

Every rejection case the Cycle #35 pack names is exercised here against the
real contract, together with the positive control that must be admitted --
a suite in which nothing is ever admitted would "pass" while proving only
that the code rejects everything.

The two manager counterexamples are reproduced verbatim:
  * a receipt committed AFTER kickoff, paired with wrong participants;
  * a self-rehashed, future-dated packet whose probability is Boolean True.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.cycle35.forecast_admission import (
    ForecastAdmissionError,
    TrustedReceiptStore,
    admit,
    admit_many,
    contest_cutoff,
    ordered_participants,
    strict_probability,
)
from aggie_analytics.cycle35.scoring_successor import score_admitted_forecasts

AS_OF = datetime(2026, 9, 20, tzinfo=timezone.utc)
KICKOFF = "2026-09-05T23:00:00+00:00"
ISSUER = "BAS_FORECAST_FREEZE_SERVICE"

CONTEST = {
    "ncaa_contest_id": "C1",
    "home_canonical_team_id": "REAL_HOME",
    "away_canonical_team_id": "REAL_AWAY",
    "kickoff_utc": KICKOFF,
    "schedule_version": "SCHED-v1",
    "home_points": 30,
    "away_points": 10,
    "game_state": "F",
}


def _receipt(**overrides):
    row = {
        "receipt_id": "R1",
        "issuer": ISSUER,
        "receipt_sha256": "b" * 64,
        # T24 against a 23:00 kickoff -> cutoff is 2026-09-04T23:00Z.
        "commitment_time_utc": "2026-09-04T12:00:00+00:00",
        "contest_id": "C1",
        "candidate_id": "M1",
        "cohort": "CO1",
        "checkpoint": "T24",
        "home_canonical_team_id": "REAL_HOME",
        "away_canonical_team_id": "REAL_AWAY",
        "schedule_version": "SCHED-v1",
        "model_code_identity": "code@abc",
        "model_data_identity": "data@def",
    }
    row.update(overrides)
    return row


def _forecast(**overrides):
    row = {
        "ncaa_contest_id": "C1",
        "candidate_id": "M1",
        "cohort": "CO1",
        "checkpoint": "T24",
        "probability_home": 0.9,
        "home_canonical_team_id": "REAL_HOME",
        "away_canonical_team_id": "REAL_AWAY",
        "freeze_receipt": {"receipt_id": "R1"},
    }
    row.update(overrides)
    return row


def _store(*receipts):
    return TrustedReceiptStore(
        receipts or (_receipt(),), trusted_issuers=(ISSUER,), source_identity="TEST"
    )


class StrictTypeTests(unittest.TestCase):
    def test_boolean_true_is_not_a_probability(self) -> None:
        self.assertIsNone(strict_probability(True))
        self.assertIsNone(strict_probability(False))

    def test_finite_unit_interval_is_required(self) -> None:
        self.assertEqual(strict_probability(0.0), 0.0)
        self.assertEqual(strict_probability(1.0), 1.0)
        for bad in (-0.1, 1.1, float("nan"), float("inf"), None, "abc", [0.5]):
            self.assertIsNone(strict_probability(bad), bad)

    def test_ordered_participants_reject_degenerate_pairs(self) -> None:
        self.assertEqual(
            ordered_participants(
                {"home_canonical_team_id": "A", "away_canonical_team_id": "B"}
            ),
            ("A", "B"),
        )
        self.assertIsNone(
            ordered_participants(
                {"home_canonical_team_id": "A", "away_canonical_team_id": "A"}
            )
        )
        self.assertIsNone(ordered_participants({"home_canonical_team_id": "A"}))


class CutoffTests(unittest.TestCase):
    def test_checkpoint_lead_derives_cutoff_from_kickoff(self) -> None:
        cutoff, reason = contest_cutoff(CONTEST, "T24")
        self.assertIsNone(reason)
        self.assertEqual(cutoff, datetime(2026, 9, 4, 23, 0, tzinfo=timezone.utc))

    def test_unknown_checkpoint_has_no_derivable_cutoff(self) -> None:
        cutoff, reason = contest_cutoff(CONTEST, "TEST:EARLY")
        self.assertIsNone(cutoff)
        self.assertEqual(reason, "UNKNOWN_CHECKPOINT_NO_DERIVABLE_CUTOFF")

    def test_missing_kickoff_is_reported_not_defaulted(self) -> None:
        cutoff, reason = contest_cutoff({"schedule_version": "v"}, "T24")
        self.assertIsNone(cutoff)
        self.assertEqual(reason, "MISSING_OR_UNPARSEABLE_KICKOFF")


class ManagerCounterexampleTests(unittest.TestCase):
    """MR34-01: the exact defect reproduced at 517ff324 must now be rejected."""

    def test_positive_control_is_admitted(self) -> None:
        verdict = admit(_forecast(), CONTEST, store=_store(), as_of_utc=AS_OF)
        self.assertTrue(verdict.admitted, verdict.failed_predicates)
        self.assertEqual(verdict.issuer, ISSUER)

    def test_commitment_after_kickoff_is_rejected(self) -> None:
        store = _store(_receipt(commitment_time_utc="2026-09-06T02:00:00+00:00"))
        verdict = admit(_forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("COMMITMENT_AFTER_CUTOFF", verdict.failed_predicates)

    def test_commitment_after_checkpoint_cutoff_but_before_kickoff_is_rejected(self) -> None:
        """A "T24" promise broken by 23 hours is still broken, even though the
        commitment precedes kickoff -- the cutoff is the checkpoint, not
        kickoff."""
        store = _store(_receipt(commitment_time_utc="2026-09-05T22:00:00+00:00"))
        verdict = admit(_forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("COMMITMENT_AFTER_CUTOFF", verdict.failed_predicates)

    def test_wrong_participants_are_rejected(self) -> None:
        verdict = admit(
            _forecast(
                home_canonical_team_id="OTHER_HOME",
                away_canonical_team_id="OTHER_AWAY",
            ),
            CONTEST,
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn(
            "FORECAST_PARTICIPANTS_DO_NOT_MATCH_CONTEST", verdict.failed_predicates
        )

    def test_reversed_participants_are_a_different_claim(self) -> None:
        verdict = admit(
            _forecast(
                home_canonical_team_id="REAL_AWAY",
                away_canonical_team_id="REAL_HOME",
            ),
            CONTEST,
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)

    def test_future_commitment_is_rejected(self) -> None:
        store = _store(_receipt(commitment_time_utc="2099-01-01T00:00:00+00:00"))
        verdict = admit(_forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("COMMITMENT_IN_THE_FUTURE", verdict.failed_predicates)

    def test_boolean_probability_is_rejected(self) -> None:
        verdict = admit(
            _forecast(probability_home=True), CONTEST, store=_store(), as_of_utc=AS_OF
        )
        self.assertFalse(verdict.admitted)
        self.assertIn(
            "PROBABILITY_NOT_STRICT_FINITE_UNIT_INTERVAL", verdict.failed_predicates
        )

    def test_receipt_absent_from_store_is_rejected(self) -> None:
        verdict = admit(
            _forecast(freeze_receipt={"receipt_id": "UNKNOWN"}),
            CONTEST,
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn("RECEIPT_NOT_IN_TRUSTED_STORE", verdict.failed_predicates)

    def test_caller_supplied_timestamp_cannot_substitute_for_the_store(self) -> None:
        """A forecast may claim any `frozen_at_utc` it likes; the contract
        reads the commitment time only from the trusted store, so a forged
        caller timestamp has no path into the decision."""
        forged = _forecast(
            frozen_at_utc="2026-09-04T00:00:00+00:00",
            freeze_receipt={
                "receipt_id": "UNKNOWN",
                "frozen_at_utc": "2026-09-04T00:00:00+00:00",
            },
        )
        verdict = admit(forged, CONTEST, store=_store(), as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIsNone(verdict.commitment_time_utc)

    def test_schedule_version_mismatch_is_rejected(self) -> None:
        verdict = admit(
            _forecast(),
            {**CONTEST, "schedule_version": "SCHED-v2"},
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn("SCHEDULE_VERSION_MISMATCH", verdict.failed_predicates)

    def test_untrusted_issuer_never_enters_the_store(self) -> None:
        store = TrustedReceiptStore(
            [_receipt(issuer="MANAGER_REVIEW_SYNTHETIC_PROBE")],
            trusted_issuers=(ISSUER,),
        )
        self.assertEqual(len(store), 0)
        verdict = admit(_forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("RECEIPT_NOT_IN_TRUSTED_STORE", verdict.failed_predicates)


class StoreIntegrityTests(unittest.TestCase):
    def test_duplicate_receipt_id_with_conflicting_content_drops_both(self) -> None:
        store = TrustedReceiptStore(
            [_receipt(), _receipt(candidate_id="M2")], trusted_issuers=(ISSUER,)
        )
        self.assertEqual(len(store), 0)
        self.assertTrue(
            any(
                r.get("reason") == "DUPLICATE_RECEIPT_ID_CONFLICTING_CONTENT"
                for r in store.rejected_rows
            )
        )

    def test_identical_duplicate_receipt_is_idempotent(self) -> None:
        store = TrustedReceiptStore([_receipt(), _receipt()], trusted_issuers=(ISSUER,))
        self.assertEqual(len(store), 1)

    def test_store_rows_missing_required_identity_are_rejected(self) -> None:
        store = TrustedReceiptStore(
            [_receipt(model_data_identity="")], trusted_issuers=(ISSUER,)
        )
        self.assertEqual(len(store), 0)
        self.assertIn("MISSING_MODEL_DATA_IDENTITY", store.rejected_rows[0]["reasons"])

    def test_store_loads_from_declared_allowlist_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "allowlist.json"
            path.write_text(
                json.dumps({"trusted_issuers": [ISSUER], "receipts": [_receipt()]}),
                encoding="utf-8",
            )
            store = TrustedReceiptStore.from_file(path)
            self.assertEqual(len(store), 1)
            self.assertEqual(store.identities()["source_identity"], str(path))

    def test_non_store_argument_is_a_contract_error(self) -> None:
        with self.assertRaises(ForecastAdmissionError):
            admit(_forecast(), CONTEST, store={}, as_of_utc=AS_OF)  # type: ignore[arg-type]

    def test_naive_as_of_is_a_contract_error(self) -> None:
        with self.assertRaises(ForecastAdmissionError):
            admit(_forecast(), CONTEST, store=_store(), as_of_utc=datetime(2026, 9, 20))


class BatchAndScoringTests(unittest.TestCase):
    def test_conflicting_duplicates_quarantine_the_whole_key(self) -> None:
        out = admit_many(
            [_forecast(), _forecast(probability_home=0.2)],
            {"C1": CONTEST},
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["admitted_count"], 0)
        self.assertEqual(len(out["quarantined_conflicting_keys"]), 1)

    def test_equal_key_order_permutations_agree(self) -> None:
        rows = [
            _forecast(),
            _forecast(
                candidate_id="M2",
                freeze_receipt={"receipt_id": "R2"},
                probability_home=0.3,
            ),
        ]
        store = _store(_receipt(), _receipt(receipt_id="R2", candidate_id="M2"))
        forward = admit_many(rows, {"C1": CONTEST}, store=store, as_of_utc=AS_OF)
        reverse = admit_many(
            list(reversed(rows)), {"C1": CONTEST}, store=store, as_of_utc=AS_OF
        )
        self.assertEqual(
            sorted(tuple(a["key"]) for a in forward["admitted"]),
            sorted(tuple(a["key"]) for a in reverse["admitted"]),
        )
        self.assertEqual(forward["admitted_count"], 2)

    def test_absent_receipts_preserve_zero_eligible(self) -> None:
        out = score_admitted_forecasts(
            [CONTEST],
            [_forecast()],
            store=TrustedReceiptStore((), trusted_issuers=(ISSUER,)),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_row_count"], 0)
        self.assertEqual(out["rejected_forecast_rows"], 1)
        self.assertTrue(out["zero_scored_is_valid_evidence_incompleteness"])

    def test_distinct_candidate_checkpoint_metrics_are_not_pooled(self) -> None:
        store = _store(
            _receipt(),
            _receipt(receipt_id="R2", candidate_id="M2"),
        )
        rows = [
            _forecast(),
            _forecast(
                candidate_id="M2",
                probability_home=0.1,
                freeze_receipt={"receipt_id": "R2"},
            ),
        ]
        out = score_admitted_forecasts(
            [CONTEST], rows, store=store, as_of_utc=AS_OF
        )
        self.assertEqual(out["scored_row_count"], 2)
        metrics = {m["candidate_id"]: m for m in out["metrics_by_candidate_cohort_checkpoint"]}
        self.assertEqual(set(metrics), {"M1", "M2"})
        # 0.9 on a home win is a good forecast; 0.1 on the same win is a bad
        # one. Pooling them would hide exactly that difference.
        self.assertLess(metrics["M1"]["brier_mean"], metrics["M2"]["brier_mean"])

    def test_tie_scores_produce_no_direction_and_are_counted(self) -> None:
        tie_contest = {**CONTEST, "home_points": 21, "away_points": 21}
        out = score_admitted_forecasts(
            [tie_contest],
            [_forecast(probability_home=0.5)],
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_rows"][0]["winner"], "TIE")
        self.assertEqual(out["scored_rows"][0]["predicted_favorite"], "NO_DIRECTION")
        self.assertEqual(
            out["metrics_by_candidate_cohort_checkpoint"][0]["ties"], 1
        )

    def test_contradictory_supplied_winner_cannot_override_scores(self) -> None:
        out = score_admitted_forecasts(
            [{**CONTEST, "winner": "AWAY"}],
            [_forecast()],
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_rows"][0]["winner"], "HOME")
        self.assertTrue(out["winner_recomputed_from_scores_not_supplied_label"])

    def test_final_without_canonical_participants_is_unusable(self) -> None:
        out = score_admitted_forecasts(
            [{k: v for k, v in CONTEST.items() if "canonical_team_id" not in k}],
            [_forecast()],
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_row_count"], 0)
        self.assertEqual(
            out["unusable_finals"][0]["reason"], "MISSING_ORDERED_PARTICIPANTS"
        )

    def test_invalid_scores_do_not_produce_a_metric(self) -> None:
        out = score_admitted_forecasts(
            [{**CONTEST, "home_points": "thirty"}],
            [_forecast()],
            store=_store(),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_row_count"], 0)
        self.assertEqual(out["unusable_finals"][0]["reason"], "NON_INTEGER_SCORES")


if __name__ == "__main__":
    unittest.main()
