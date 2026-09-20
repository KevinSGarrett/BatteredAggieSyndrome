"""R35-06 regression tests for MR34-01, MR34-02, MF35-01 and MF35-02.

Every rejection case the Cycle #35 pack and the Cycle #35 manager follow-up
name is exercised here against the real contract, together with the positive
control that must be admitted -- a suite in which nothing is ever admitted
would "pass" while proving only that the code rejects everything.

MF35-01/02 (the manager's follow-up counterexamples, reproduced verbatim in
`ManagerFollowupCounterexampleTests` below) showed that the prior version of
this contract:

  * admitted a forecast whose receipt had NO verifiable backing bytes at all
    (`evidence_bytes_confirmed` was computed but never enforced);
  * admitted a changed probability under the same receipt (nothing bound the
    forecast's claimed content to anything the receipt actually committed);
  * admitted a substituted contest id, because nothing checked that the
    `contest` mapping handed to `admit()` declared its own identity;
  * let an empty trusted-issuer allowlist accept a named issuer (fail-open,
    not fail-closed, on empty configuration);
  * let a receipt ID that had carried conflicting content become trusted
    again on a THIRD row repeating the original content (A / conflicting-B /
    A resurrected A).

Every fixture below now binds each receipt to REAL backing bytes on disk,
verified by an independently recomputed sha256 -- exactly the pattern the
manager used to demonstrate the defects, now used to prove they are closed.
"""

from __future__ import annotations

import hashlib
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


class EvidenceBoundFixture(unittest.TestCase):
    """Base class: a real temp evidence root plus receipt/forecast builders
    that bind every receipt to ACTUAL backing bytes on disk.

    `_receipt()` writes a real JSON payload matching the receipt's own
    declared fields (unless `payload_overrides` diverges it deliberately, for
    tests that need a payload disagreeing with its own receipt metadata) and
    returns a receipt ROW carrying the recomputed sha256 and the relative
    payload path -- never an invented hash.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.evidence_root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write_payload(self, name: str, payload: dict) -> tuple[str, str]:
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        (self.evidence_root / name).write_bytes(raw)
        return name, digest

    def _receipt(
        self,
        *,
        payload_name: str = "payload.json",
        payload_overrides: dict | None = None,
        omit_payload: bool = False,
        **overrides,
    ) -> dict:
        row = {
            "receipt_id": "R1",
            "issuer": ISSUER,
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
            "probability_home": 0.9,
        }
        row.update(overrides)
        payload = {
            "contest_id": row["contest_id"],
            "candidate_id": row["candidate_id"],
            "cohort": row["cohort"],
            "checkpoint": row["checkpoint"],
            "home_canonical_team_id": row["home_canonical_team_id"],
            "away_canonical_team_id": row["away_canonical_team_id"],
            "probability_home": row.pop("probability_home"),
        }
        if payload_overrides:
            payload.update(payload_overrides)
        if omit_payload:
            row["receipt_sha256"] = "b" * 64
        else:
            name, digest = self._write_payload(payload_name, payload)
            row["payload_path"] = name
            row["receipt_sha256"] = digest
        return row

    def _forecast(self, **overrides) -> dict:
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

    def _store(self, *receipts, trusted_issuers=(ISSUER,)) -> TrustedReceiptStore:
        return TrustedReceiptStore(
            receipts or (self._receipt(),),
            trusted_issuers=trusted_issuers,
            source_identity="TEST",
            evidence_root=self.evidence_root,
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


class ManagerCounterexampleTests(EvidenceBoundFixture):
    """MR34-01: the exact defect reproduced at 517ff324 must now be rejected."""

    def test_positive_control_is_admitted(self) -> None:
        verdict = admit(self._forecast(), CONTEST, store=self._store(), as_of_utc=AS_OF)
        self.assertTrue(verdict.admitted, verdict.failed_predicates)
        self.assertEqual(verdict.issuer, ISSUER)
        self.assertTrue(verdict.evidence_bytes_confirmed)
        self.assertEqual(verdict.probability_home, 0.9)

    def test_commitment_after_kickoff_is_rejected(self) -> None:
        store = self._store(
            self._receipt(commitment_time_utc="2026-09-06T02:00:00+00:00")
        )
        verdict = admit(self._forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("COMMITMENT_AFTER_CUTOFF", verdict.failed_predicates)

    def test_commitment_after_checkpoint_cutoff_but_before_kickoff_is_rejected(self) -> None:
        """A "T24" promise broken by 23 hours is still broken, even though the
        commitment precedes kickoff -- the cutoff is the checkpoint, not
        kickoff."""
        store = self._store(
            self._receipt(commitment_time_utc="2026-09-05T22:00:00+00:00")
        )
        verdict = admit(self._forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("COMMITMENT_AFTER_CUTOFF", verdict.failed_predicates)

    def test_wrong_participants_are_rejected(self) -> None:
        verdict = admit(
            self._forecast(
                home_canonical_team_id="OTHER_HOME",
                away_canonical_team_id="OTHER_AWAY",
            ),
            CONTEST,
            store=self._store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn(
            "FORECAST_PARTICIPANTS_DO_NOT_MATCH_CONTEST", verdict.failed_predicates
        )

    def test_reversed_participants_are_a_different_claim(self) -> None:
        verdict = admit(
            self._forecast(
                home_canonical_team_id="REAL_AWAY",
                away_canonical_team_id="REAL_HOME",
            ),
            CONTEST,
            store=self._store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)

    def test_future_commitment_is_rejected(self) -> None:
        store = self._store(
            self._receipt(commitment_time_utc="2099-01-01T00:00:00+00:00")
        )
        verdict = admit(self._forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("COMMITMENT_IN_THE_FUTURE", verdict.failed_predicates)

    def test_boolean_probability_is_rejected(self) -> None:
        verdict = admit(
            self._forecast(probability_home=True),
            CONTEST,
            store=self._store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn(
            "PROBABILITY_NOT_STRICT_FINITE_UNIT_INTERVAL", verdict.failed_predicates
        )

    def test_receipt_absent_from_store_is_rejected(self) -> None:
        verdict = admit(
            self._forecast(freeze_receipt={"receipt_id": "UNKNOWN"}),
            CONTEST,
            store=self._store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn("RECEIPT_NOT_IN_TRUSTED_STORE", verdict.failed_predicates)

    def test_caller_supplied_timestamp_cannot_substitute_for_the_store(self) -> None:
        """A forecast may claim any `frozen_at_utc` it likes; the contract
        reads the commitment time only from the trusted store, so a forged
        caller timestamp has no path into the decision."""
        forged = self._forecast(
            frozen_at_utc="2026-09-04T00:00:00+00:00",
            freeze_receipt={
                "receipt_id": "UNKNOWN",
                "frozen_at_utc": "2026-09-04T00:00:00+00:00",
            },
        )
        verdict = admit(forged, CONTEST, store=self._store(), as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIsNone(verdict.commitment_time_utc)

    def test_schedule_version_mismatch_is_rejected(self) -> None:
        verdict = admit(
            self._forecast(),
            {**CONTEST, "schedule_version": "SCHED-v2"},
            store=self._store(),
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn("SCHEDULE_VERSION_MISMATCH", verdict.failed_predicates)

    def test_untrusted_issuer_never_enters_the_store(self) -> None:
        store = TrustedReceiptStore(
            [self._receipt(issuer="MANAGER_REVIEW_SYNTHETIC_PROBE")],
            trusted_issuers=(ISSUER,),
            evidence_root=self.evidence_root,
        )
        self.assertEqual(len(store), 0)
        verdict = admit(self._forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("RECEIPT_NOT_IN_TRUSTED_STORE", verdict.failed_predicates)


class ManagerFollowupCounterexampleTests(EvidenceBoundFixture):
    """MF35-01/02: the Cycle #35 manager follow-up's exact reproduced
    counterexamples against `c6bb041a`, verified closed here. Each test names
    the manager's finding it closes.

    The manager's own probe script (`consumer_probes.py`) is reproduced
    field-for-field: same synthetic contest/candidate/cohort/checkpoint ids,
    same participants, same probabilities (0.1 then 0.9), same substituted
    contest id (SYNTHETIC-C2), same empty-issuer and A/conflicting-B/A
    sequences.
    """

    def _manager_receipt(self, **overrides) -> dict:
        row = dict(
            receipt_id="SYNTHETIC-R1",
            issuer="SYNTHETIC-ISSUER",
            receipt_sha256="b" * 64,
            commitment_time_utc="2026-09-04T12:00:00Z",
            contest_id="SYNTHETIC-C1",
            candidate_id="M1",
            cohort="CO1",
            checkpoint="T24",
            home_canonical_team_id="H",
            away_canonical_team_id="A",
            schedule_version="V1",
            model_code_identity="CODE1",
            model_data_identity="DATA1",
        )
        row.update(overrides)
        return row

    def _manager_forecast(self, **overrides) -> dict:
        row = dict(
            ncaa_contest_id="SYNTHETIC-C1",
            candidate_id="M1",
            cohort="CO1",
            checkpoint="T24",
            probability_home=0.1,
            home_canonical_team_id="H",
            away_canonical_team_id="A",
            freeze_receipt={"receipt_id": "SYNTHETIC-R1"},
        )
        row.update(overrides)
        return row

    def _manager_contest(self, **overrides) -> dict:
        row = dict(
            ncaa_contest_id="SYNTHETIC-C1",
            home_canonical_team_id="H",
            away_canonical_team_id="A",
            kickoff_utc="2026-09-05T23:00:00Z",
            schedule_version="V1",
        )
        row.update(overrides)
        return row

    # ---- MF35-01: admission without confirmed bytes ------------------

    def test_mf35_01_admit_without_payload_is_rejected(self) -> None:
        """The manager's exact `admit_without_payload` probe: a receipt with
        a well-formed but entirely fabricated sha256 and no bound payload
        must never be admitted. `evidence_bytes_confirmed` must gate
        admission, not merely describe it."""
        store = TrustedReceiptStore(
            [self._manager_receipt()],  # note: no payload_path at all
            trusted_issuers=["SYNTHETIC-ISSUER"],
        )
        # A receipt with no payload_path is rejected at STORE construction,
        # so it is not even in the store -- the strongest possible closure.
        self.assertEqual(len(store), 0)
        self.assertTrue(
            any(
                "MISSING_PAYLOAD_PATH" in r.get("reasons", [])
                for r in store.rejected_rows
            )
        )
        verdict = admit(
            self._manager_forecast(),
            self._manager_contest(),
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn("RECEIPT_NOT_IN_TRUSTED_STORE", verdict.failed_predicates)

    def test_mf35_01_receipt_with_unresolvable_payload_path_is_rejected(self) -> None:
        """A receipt that DOES declare a payload_path, but the path resolves
        to nothing on disk, must fail at admission time with an explicit
        evidence-not-confirmed reason -- not silently admit."""
        store = TrustedReceiptStore(
            [self._manager_receipt(payload_path="does_not_exist.json")],
            trusted_issuers=["SYNTHETIC-ISSUER"],
            evidence_root=self.evidence_root,
        )
        self.assertEqual(len(store), 1)
        verdict = admit(
            self._manager_forecast(),
            self._manager_contest(),
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn("EVIDENCE_PAYLOAD_FILE_NOT_FOUND", verdict.failed_predicates)
        self.assertFalse(verdict.evidence_bytes_confirmed)

    def test_mf35_01_changed_probability_same_receipt_is_rejected(self) -> None:
        """The manager's exact `changed_probability_same_receipt` probe: a
        real payload commits probability_home=0.1; a forecast row claiming
        0.9 under the SAME receipt must be rejected, not admitted at 0.9."""
        name, digest = self._write_payload(
            "p1.json",
            {
                "contest_id": "SYNTHETIC-C1",
                "candidate_id": "M1",
                "cohort": "CO1",
                "checkpoint": "T24",
                "home_canonical_team_id": "H",
                "away_canonical_team_id": "A",
                "probability_home": 0.1,
            },
        )
        store = TrustedReceiptStore(
            [self._manager_receipt(receipt_sha256=digest, payload_path=name)],
            trusted_issuers=["SYNTHETIC-ISSUER"],
            evidence_root=self.evidence_root,
        )
        contest = self._manager_contest()

        genuine = admit(
            self._manager_forecast(probability_home=0.1),
            contest,
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertTrue(genuine.admitted, genuine.failed_predicates)
        self.assertEqual(genuine.probability_home, 0.1)

        tampered = admit(
            self._manager_forecast(probability_home=0.9),
            contest,
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertFalse(tampered.admitted)
        self.assertIn(
            "FORECAST_PROBABILITY_DISAGREES_WITH_VERIFIED_PAYLOAD",
            tampered.failed_predicates,
        )

    def test_mf35_01_wrong_contest_same_participants_is_rejected(self) -> None:
        """The manager's exact `wrong_contest_same_participants` probe: only
        the `contest` mapping's own declared id changes (to SYNTHETIC-C2);
        participants and schedule_version are held equal. Must be rejected
        because nothing about matching participants proves it is the same
        game."""
        name, digest = self._write_payload(
            "p2.json",
            {
                "contest_id": "SYNTHETIC-C1",
                "candidate_id": "M1",
                "cohort": "CO1",
                "checkpoint": "T24",
                "home_canonical_team_id": "H",
                "away_canonical_team_id": "A",
                "probability_home": 0.1,
            },
        )
        store = TrustedReceiptStore(
            [self._manager_receipt(receipt_sha256=digest, payload_path=name)],
            trusted_issuers=["SYNTHETIC-ISSUER"],
            evidence_root=self.evidence_root,
        )
        verdict = admit(
            self._manager_forecast(),
            self._manager_contest(ncaa_contest_id="SYNTHETIC-C2"),
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn(
            "CONTEST_IDENTITY_DOES_NOT_MATCH_FORECAST_KEY", verdict.failed_predicates
        )

    def test_mf35_01_missing_contest_id_is_rejected(self) -> None:
        contest = self._manager_contest()
        del contest["ncaa_contest_id"]
        store = self._store()
        verdict = admit(self._forecast(), contest, store=store, as_of_utc=AS_OF)
        self.assertFalse(verdict.admitted)
        self.assertIn("CONTEST_MISSING_CANONICAL_ID", verdict.failed_predicates)

    def test_mf35_01_payload_key_mismatch_is_rejected(self) -> None:
        """The receipt's METADATA matches the forecast, but the actual bytes
        behind it commit to a different cohort. Bytes are the ground truth."""
        name, digest = self._write_payload(
            "p3.json",
            {
                "contest_id": "SYNTHETIC-C1",
                "candidate_id": "M1",
                "cohort": "DIFFERENT-COHORT",
                "checkpoint": "T24",
                "home_canonical_team_id": "H",
                "away_canonical_team_id": "A",
                "probability_home": 0.1,
            },
        )
        store = TrustedReceiptStore(
            [self._manager_receipt(receipt_sha256=digest, payload_path=name)],
            trusted_issuers=["SYNTHETIC-ISSUER"],
            evidence_root=self.evidence_root,
        )
        verdict = admit(
            self._manager_forecast(),
            self._manager_contest(),
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn("PAYLOAD_KEY_DOES_NOT_MATCH_RECEIPT", verdict.failed_predicates)

    def test_mf35_01_payload_participants_mismatch_is_rejected(self) -> None:
        name, digest = self._write_payload(
            "p4.json",
            {
                "contest_id": "SYNTHETIC-C1",
                "candidate_id": "M1",
                "cohort": "CO1",
                "checkpoint": "T24",
                "home_canonical_team_id": "OTHER_H",
                "away_canonical_team_id": "OTHER_A",
                "probability_home": 0.1,
            },
        )
        store = TrustedReceiptStore(
            [self._manager_receipt(receipt_sha256=digest, payload_path=name)],
            trusted_issuers=["SYNTHETIC-ISSUER"],
            evidence_root=self.evidence_root,
        )
        verdict = admit(
            self._manager_forecast(),
            self._manager_contest(),
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn(
            "PAYLOAD_PARTICIPANTS_DO_NOT_MATCH_RECEIPT", verdict.failed_predicates
        )

    def test_mf35_01_tampered_bytes_fail_the_hash_check(self) -> None:
        """A payload file exists and parses fine, but its bytes were changed
        after the receipt's sha256 was pinned."""
        name, digest = self._write_payload(
            "p5.json",
            {
                "contest_id": "SYNTHETIC-C1",
                "candidate_id": "M1",
                "cohort": "CO1",
                "checkpoint": "T24",
                "home_canonical_team_id": "H",
                "away_canonical_team_id": "A",
                "probability_home": 0.1,
            },
        )
        # Tamper the bytes on disk AFTER the digest was computed and pinned.
        (self.evidence_root / name).write_bytes(b'{"tampered": true}')
        store = TrustedReceiptStore(
            [self._manager_receipt(receipt_sha256=digest, payload_path=name)],
            trusted_issuers=["SYNTHETIC-ISSUER"],
            evidence_root=self.evidence_root,
        )
        verdict = admit(
            self._manager_forecast(),
            self._manager_contest(),
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertFalse(verdict.admitted)
        self.assertIn(
            "EVIDENCE_BYTES_DO_NOT_MATCH_RECEIPT_SHA256", verdict.failed_predicates
        )

    # ---- MF35-02: receipt-store fail-open / conflict resurrection ----

    def test_mf35_02_empty_issuer_allowlist_accepts_nothing(self) -> None:
        """The manager's exact `empty_issuer_allowlist` probe."""
        store = TrustedReceiptStore(
            [self._manager_receipt(payload_path="x.json")], trusted_issuers=[]
        )
        self.assertIsNone(store.get("SYNTHETIC-R1"))
        self.assertEqual(len(store), 0)
        self.assertTrue(
            any(
                "NO_TRUSTED_ISSUERS_CONFIGURED" in r.get("reasons", [])
                for r in store.rejected_rows
            )
        )

    def test_mf35_02_empty_allowlist_rejects_even_a_plausible_issuer(self) -> None:
        """Fail-closed must not depend on whether the issuer STRING looks
        legitimate -- an empty allowlist trusts nobody, full stop."""
        store = TrustedReceiptStore(
            [self._manager_receipt(issuer=ISSUER, payload_path="x.json")],
            trusted_issuers=[],
        )
        self.assertEqual(len(store), 0)

    def test_mf35_02_conflict_resurrection_aba_is_rejected(self) -> None:
        """The manager's exact `conflict_resurrection_ABA` probe: receipt A,
        then conflicting-content B under the same ID, then A again. The
        third row must NOT resurrect A."""
        r = self._manager_receipt(payload_path="x.json")
        conflicting = {**r, "model_data_identity": "CONFLICTING-DATA"}
        store = TrustedReceiptStore(
            [r, conflicting, r],
            trusted_issuers=["SYNTHETIC-ISSUER"],
            evidence_root=self.evidence_root,
        )
        self.assertIsNone(store.get("SYNTHETIC-R1"))
        self.assertEqual(len(store), 0)
        reasons = [row["reason"] for row in store.rejected_rows]
        self.assertIn("DUPLICATE_RECEIPT_ID_CONFLICTING_CONTENT", reasons)
        self.assertIn(
            "RECEIPT_ID_PERMANENTLY_QUARANTINED_CONFLICTING_CONTENT_SEEN_EARLIER_IN_LOAD",
            reasons,
        )

    def test_mf35_02_conflict_resurrection_all_six_permutations(self) -> None:
        """Order must not matter: every permutation of {A, A, conflicting-B}
        must leave the ID unresolvable at the end."""
        import itertools

        r = self._manager_receipt(payload_path="x.json")
        b = {**r, "model_data_identity": "CONFLICTING-DATA"}
        for perm in itertools.permutations([r, r, b]):
            store = TrustedReceiptStore(
                list(perm),
                trusted_issuers=["SYNTHETIC-ISSUER"],
                evidence_root=self.evidence_root,
            )
            self.assertEqual(len(store), 0, perm)
            self.assertIsNone(store.get("SYNTHETIC-R1"), perm)


class StoreIntegrityTests(EvidenceBoundFixture):
    def test_duplicate_receipt_id_with_conflicting_content_drops_both(self) -> None:
        store = TrustedReceiptStore(
            [self._receipt(), self._receipt(payload_name="p2.json", candidate_id="M2")],
            trusted_issuers=(ISSUER,),
            evidence_root=self.evidence_root,
        )
        self.assertEqual(len(store), 0)
        self.assertTrue(
            any(
                r.get("reason") == "DUPLICATE_RECEIPT_ID_CONFLICTING_CONTENT"
                for r in store.rejected_rows
            )
        )

    def test_identical_duplicate_receipt_is_idempotent(self) -> None:
        receipt = self._receipt()
        store = TrustedReceiptStore(
            [receipt, dict(receipt)],
            trusted_issuers=(ISSUER,),
            evidence_root=self.evidence_root,
        )
        self.assertEqual(len(store), 1)

    def test_store_rows_missing_required_identity_are_rejected(self) -> None:
        store = TrustedReceiptStore(
            [self._receipt(model_data_identity="")],
            trusted_issuers=(ISSUER,),
            evidence_root=self.evidence_root,
        )
        self.assertEqual(len(store), 0)
        self.assertIn("MISSING_MODEL_DATA_IDENTITY", store.rejected_rows[0]["reasons"])

    def test_receipt_without_payload_path_is_rejected_at_parse_time(self) -> None:
        store = TrustedReceiptStore(
            [self._receipt(omit_payload=True)],
            trusted_issuers=(ISSUER,),
            evidence_root=self.evidence_root,
        )
        self.assertEqual(len(store), 0)
        self.assertIn("MISSING_PAYLOAD_PATH", store.rejected_rows[0]["reasons"])

    def test_store_loads_from_declared_allowlist_file(self) -> None:
        allowlist_dir = self.evidence_root / "allowlist_dir"
        allowlist_dir.mkdir()
        raw = json.dumps({"probability_home": 0.9, "contest_id": "C1",
                          "candidate_id": "M1", "cohort": "CO1", "checkpoint": "T24",
                          "home_canonical_team_id": "REAL_HOME",
                          "away_canonical_team_id": "REAL_AWAY"},
                         sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        (allowlist_dir / "payload.json").write_bytes(raw)
        row = {
            "receipt_id": "R1", "issuer": ISSUER, "receipt_sha256": digest,
            "commitment_time_utc": "2026-09-04T12:00:00+00:00", "contest_id": "C1",
            "candidate_id": "M1", "cohort": "CO1", "checkpoint": "T24",
            "home_canonical_team_id": "REAL_HOME", "away_canonical_team_id": "REAL_AWAY",
            "schedule_version": "SCHED-v1", "model_code_identity": "code@abc",
            "model_data_identity": "data@def", "payload_path": "payload.json",
        }
        path = allowlist_dir / "allowlist.json"
        path.write_text(
            json.dumps({"trusted_issuers": [ISSUER], "receipts": [row]}),
            encoding="utf-8",
        )
        store = TrustedReceiptStore.from_file(path)
        self.assertEqual(len(store), 1)
        self.assertEqual(store.identities()["source_identity"], str(path))
        verdict = admit(self._forecast(), CONTEST, store=store, as_of_utc=AS_OF)
        self.assertTrue(verdict.admitted, verdict.failed_predicates)

    def test_non_store_argument_is_a_contract_error(self) -> None:
        with self.assertRaises(ForecastAdmissionError):
            admit(self._forecast(), CONTEST, store={}, as_of_utc=AS_OF)  # type: ignore[arg-type]

    def test_naive_as_of_is_a_contract_error(self) -> None:
        with self.assertRaises(ForecastAdmissionError):
            admit(
                self._forecast(),
                CONTEST,
                store=self._store(),
                as_of_utc=datetime(2026, 9, 20),
            )


class BatchAndScoringTests(EvidenceBoundFixture):
    def test_conflicting_duplicates_quarantine_the_whole_key(self) -> None:
        """Two DIFFERENT receipts (distinct receipt ids, each independently
        bytes-confirmed and each internally consistent with its own claimed
        forecast probability) that both declare the SAME forecast key but
        disagree on the committed probability. Each admits individually;
        `admit_many` must still quarantine the shared key rather than pick
        one arbitrarily."""
        store = self._store(
            self._receipt(probability_home=0.9),
            self._receipt(
                payload_name="conflict.json", receipt_id="R2", probability_home=0.2
            ),
        )
        out = admit_many(
            [
                self._forecast(probability_home=0.9),
                self._forecast(
                    probability_home=0.2, freeze_receipt={"receipt_id": "R2"}
                ),
            ],
            {"C1": CONTEST},
            store=store,
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["admitted_count"], 0)
        self.assertEqual(len(out["quarantined_conflicting_keys"]), 1)
        self.assertEqual(
            out["quarantined_conflicting_keys"][0]["distinct_probabilities"],
            [0.2, 0.9],
        )

    def test_equal_key_order_permutations_agree(self) -> None:
        rows = [
            self._forecast(),
            self._forecast(
                candidate_id="M2",
                freeze_receipt={"receipt_id": "R2"},
                probability_home=0.3,
            ),
        ]
        store = self._store(
            self._receipt(),
            self._receipt(
                payload_name="p2.json",
                receipt_id="R2",
                candidate_id="M2",
                probability_home=0.3,
            ),
        )
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
            [self._forecast()],
            store=TrustedReceiptStore((), trusted_issuers=(ISSUER,)),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_row_count"], 0)
        self.assertEqual(out["rejected_forecast_rows"], 1)
        self.assertTrue(out["zero_scored_is_valid_evidence_incompleteness"])

    def test_distinct_candidate_checkpoint_metrics_are_not_pooled(self) -> None:
        store = self._store(
            self._receipt(probability_home=0.9),
            self._receipt(
                payload_name="p2.json",
                receipt_id="R2",
                candidate_id="M2",
                probability_home=0.1,
            ),
        )
        rows = [
            self._forecast(),
            self._forecast(
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
            [self._forecast(probability_home=0.5)],
            store=self._store(self._receipt(probability_home=0.5)),
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
            [self._forecast()],
            store=self._store(),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_rows"][0]["winner"], "HOME")
        self.assertTrue(out["winner_recomputed_from_scores_not_supplied_label"])

    def test_final_without_canonical_participants_is_unusable(self) -> None:
        out = score_admitted_forecasts(
            [{k: v for k, v in CONTEST.items() if "canonical_team_id" not in k}],
            [self._forecast()],
            store=self._store(),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_row_count"], 0)
        self.assertEqual(
            out["unusable_finals"][0]["reason"], "MISSING_ORDERED_PARTICIPANTS"
        )

    def test_invalid_scores_do_not_produce_a_metric(self) -> None:
        out = score_admitted_forecasts(
            [{**CONTEST, "home_points": "thirty"}],
            [self._forecast()],
            store=self._store(),
            as_of_utc=AS_OF,
        )
        self.assertEqual(out["scored_row_count"], 0)
        self.assertEqual(out["unusable_finals"][0]["reason"], "NON_INTEGER_SCORES")


if __name__ == "__main__":
    unittest.main()
