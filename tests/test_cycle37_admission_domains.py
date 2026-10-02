"""Cycle #37 - Attempt #2 - ACTUAL_STATE

MF36-03 and MF36-04 regressions, at the real consumers.

Every negative the Cycle 36 manager reproduced is here, plus the cases a
value-domain gate has to get right in the other direction: a gate that
refuses everything is not repaired, it is broken the other way. So each
family carries its positive control beside its negatives.
"""

from __future__ import annotations

import hashlib
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36 import kernel_reference, scoring_guards  # noqa: E402
from aggie_analytics.cycle37.admission_domains import (  # noqa: E402
    valid_digest,
    valid_instant,
    valid_probability,
    valid_publication_receipt,
    valid_score,
)

CUTOFF = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
FREEZE = CUTOFF - timedelta(hours=2)
KNOWN = CUTOFF - timedelta(days=1)
PACKET_DIGEST = hashlib.sha256(b"packet").hexdigest()
RECEIPT_DIGEST = hashlib.sha256(b"receipt").hexdigest()

#: MF37A02-02/03 fixture correction (Cycle #37 - Attempt #3). PACKET_DIGEST and RECEIPT_DIGEST are hashes of
#: the literals b"packet" and b"receipt": well formed, but no receipt or packet with those bytes exists, and the
#: gates used to admit them anyway -- the defect MF37A02-02/03 names. The positive controls below now bind real
#: bytes in a test-only fixture store and pass its authority; the bare digests remain the negatives.
_STORE = None
AUTHORITY = None


def setUpModule() -> None:
    global _STORE, AUTHORITY
    import tempfile

    from aggie_analytics.cycle37.receipt_fixtures import fixture_authority

    _STORE = tempfile.TemporaryDirectory()
    AUTHORITY = fixture_authority(Path(_STORE.name) / "store", "mf36-domains-fixture")


def tearDownModule() -> None:
    if _STORE is not None:
        _STORE.cleanup()


class ValueDomains(unittest.TestCase):
    def test_a_probability_must_be_a_real_number_in_the_unit_interval(self) -> None:
        for value in (1.8, -0.5, float("nan"), float("inf"), float("-inf"), "0.6", None):
            with self.subTest(value=value):
                self.assertFalse(valid_probability(value))
        for value in (0.0, 0.5, 1.0, 0, 1):
            with self.subTest(value=value):
                self.assertTrue(valid_probability(value))

    def test_a_boolean_is_not_a_probability_even_though_it_is_an_int(self) -> None:
        verdict = valid_probability(True)
        self.assertFalse(verdict)
        self.assertEqual(verdict.code, "REFUSED_PROBABILITY_IS_BOOLEAN")

    def test_a_score_must_be_a_non_negative_whole_number(self) -> None:
        for value in (-7, True, False, 1.5, "24", None, float("nan")):
            with self.subTest(value=value):
                self.assertFalse(valid_score(value))
        for value in (0, 24, 17.0):
            with self.subTest(value=value):
                self.assertTrue(valid_score(value))

    def test_a_digest_must_be_a_sha256_not_merely_non_empty(self) -> None:
        for value in ("yes", "", None, "Z" * 64, PACKET_DIGEST.upper(), 12345):
            with self.subTest(value=value):
                self.assertFalse(valid_digest(value))
        self.assertTrue(valid_digest(PACKET_DIGEST))

    def test_an_instant_must_be_aware_and_not_in_the_future(self) -> None:
        self.assertFalse(valid_instant("2026-09-01T10:00:00"))
        self.assertFalse(valid_instant("2099-01-01T00:00:00+00:00"))
        self.assertFalse(valid_instant("not a time"))
        self.assertFalse(valid_instant(None))
        self.assertTrue(valid_instant(FREEZE.isoformat()))


class PublicationReceipts(unittest.TestCase):
    VALID: dict[str, Any] = {
        "source_id": "SRC-001",
        "prior_game_id": "G1",
        "payload_sha256": PACKET_DIGEST,
        "published_at_utc": (KNOWN - timedelta(hours=1)).isoformat(),
        "known_at_utc": KNOWN.isoformat(),
    }

    def _check(self, receipt: Any, **kwargs: Any):
        return valid_publication_receipt(
            receipt, prior_game_id="G1", cutoff_utc=CUTOFF, **kwargs
        )

    def test_the_valid_receipt_is_accepted(self) -> None:
        self.assertTrue(self._check(self.VALID))

    def test_an_unrelated_truthy_dictionary_is_not_a_receipt(self) -> None:
        verdict = self._check({"unrelated": True})
        self.assertFalse(verdict)
        self.assertEqual(verdict.code, "REFUSED_RECEIPT_MISSING_REQUIRED_FIELDS")

    def test_a_truthy_string_is_not_a_receipt(self) -> None:
        verdict = self._check("a receipt, honest")
        self.assertEqual(verdict.code, "REFUSED_RECEIPT_IS_NOT_A_MAPPING")

    def test_a_receipt_for_another_prior_is_refused(self) -> None:
        verdict = self._check({**self.VALID, "prior_game_id": "G-OTHER"})
        self.assertEqual(verdict.code, "REFUSED_RECEIPT_NAMES_A_DIFFERENT_PRIOR")

    def test_a_receipt_known_at_or_after_the_cutoff_is_refused(self) -> None:
        for offset in (timedelta(0), timedelta(hours=1)):
            with self.subTest(offset=offset):
                verdict = self._check(
                    {**self.VALID, "known_at_utc": (CUTOFF + offset).isoformat()}
                )
                self.assertFalse(verdict)

    def test_a_future_receipt_is_refused(self) -> None:
        verdict = self._check({**self.VALID, "known_at_utc": "2099-01-01T00:00:00+00:00"})
        self.assertEqual(verdict.code, "REFUSED_INSTANT_IS_IN_THE_FUTURE")

    def test_publication_after_known_at_is_refused_as_impossible(self) -> None:
        verdict = self._check(
            {**self.VALID, "published_at_utc": (KNOWN + timedelta(hours=1)).isoformat()}
        )
        self.assertEqual(verdict.code, "REFUSED_RECEIPT_PUBLISHED_AFTER_IT_WAS_KNOWN")

    def test_without_a_cutoff_nothing_can_be_proven_in_time(self) -> None:
        verdict = valid_publication_receipt(
            self.VALID, prior_game_id="G1", cutoff_utc=None
        )
        self.assertEqual(verdict.code, "REFUSED_RECEIPT_HAS_NO_CUTOFF_TO_COMPARE")


class PitGate(unittest.TestCase):
    #: MF37A02-03: the row now declares the prior its features consumed ("P1"); a receipt keyed by the row's
    #: own id "G1" with ``prior_game_id`` "G1" named the target contest, not a prior, and was admitted.
    ROW = {
        "canonical_game_id": "G1",
        "authority_class": "PROVEN_PIT_TRAINING_ROW",
        "cutoff_utc": CUTOFF.isoformat(),
        "prior_observation_ids": ["P1"],
    }

    def verified(self) -> dict[str, Any]:
        from aggie_analytics.cycle37.receipt_fixtures import prior_receipt

        digest, _stored = prior_receipt(AUTHORITY.root, priors="P1", published_at=KNOWN - timedelta(hours=1),
                                        known_at=KNOWN)
        return {"P1": digest}

    def test_a_valid_receipt_admits(self) -> None:
        classification = kernel_reference.classify_pit(self.ROW, self.verified(), authority=AUTHORITY)
        self.assertEqual(classification["successor_state"], kernel_reference.PIT_PROVEN)
        self.assertTrue(classification["admissible_to_a_pit_consumer"])

    def test_the_old_self_asserted_valid_receipt_no_longer_admits(self) -> None:
        # PublicationReceipts.VALID names the target "G1" as its prior and has no bytes behind its digest.
        classification = kernel_reference.classify_pit(self.ROW, {"G1": PublicationReceipts.VALID})
        self.assertNotEqual(classification["successor_state"], kernel_reference.PIT_PROVEN)
        self.assertEqual(classification["receipt_validation"]["code"], "REFUSED_CONSUMED_PRIOR_IS_NOT_ATTESTED")

    def test_a_truthy_object_no_longer_proves_point_in_time(self) -> None:
        classification = kernel_reference.classify_pit(self.ROW, {"G1": {"unrelated": True}})
        self.assertNotEqual(classification["successor_state"], kernel_reference.PIT_PROVEN)
        self.assertFalse(classification["admissible_to_a_pit_consumer"])
        self.assertTrue(classification["receipt_offered"])
        self.assertIn("rejected", classification["detail"])

    def test_a_row_with_no_receipt_keeps_its_superseded_label(self) -> None:
        classification = kernel_reference.classify_pit(self.ROW, {})
        self.assertEqual(
            classification["successor_state"], kernel_reference.PIT_SUPERSEDED
        )

    def test_a_forged_classification_is_not_admitted(self) -> None:
        self.assertFalse(
            kernel_reference.admit_to_pit_consumer(
                {
                    "canonical_game_id": "G1",
                    "successor_state": kernel_reference.PIT_PROVEN,
                    "admissible_to_a_pit_consumer": True,
                }
            )
        )

    def test_a_forged_classification_carrying_a_forged_receipt_is_not_admitted(self) -> None:
        self.assertFalse(
            kernel_reference.admit_to_pit_consumer(
                {
                    "canonical_game_id": "G1",
                    "successor_state": kernel_reference.PIT_PROVEN,
                    "admissible_to_a_pit_consumer": True,
                    "receipt": {"unrelated": True},
                    "cutoff_utc": CUTOFF.isoformat(),
                }
            )
        )

    def test_admission_is_derived_from_the_row_when_one_is_supplied(self) -> None:
        receipts = self.verified()
        classification = kernel_reference.classify_pit(self.ROW, receipts, authority=AUTHORITY)
        self.assertTrue(
            kernel_reference.admit_to_pit_consumer(
                classification, row=self.ROW, receipts_by_game=receipts, authority=AUTHORITY
            )
        )
        # The same asserted classification, derived against an empty store,
        # is refused: the conclusion travels with the caller, the evidence
        # does not.
        self.assertFalse(
            kernel_reference.admit_to_pit_consumer(
                classification, row=self.ROW, receipts_by_game={}, authority=AUTHORITY
            )
        )

    def test_a_valid_standalone_classification_no_longer_admits(self) -> None:
        # MF37A02-03 correction: this test used to assert the opposite. A classification carries whatever
        # priors its author chose, so without the row it cannot show those were the priors consumed; a
        # standalone classification is refused even when it was derived from genuine fixture bytes.
        classification = kernel_reference.classify_pit(self.ROW, self.verified(), authority=AUTHORITY)
        self.assertEqual(classification["successor_state"], kernel_reference.PIT_PROVEN)
        self.assertFalse(kernel_reference.admit_to_pit_consumer(classification))
        self.assertFalse(kernel_reference.admit_to_pit_consumer(classification, authority=AUTHORITY))


def forecast(**overrides: Any) -> scoring_guards.FrozenForecast:
    base = dict(
        contest_id="G1",
        model_identity="M1",
        input_identity="I1",
        designated_home_team="HOME",
        designated_away_team="AWAY",
        home_win_probability=0.6,
        freeze_known_at=FREEZE,
        cutoff_utc=CUTOFF,
        receipt_digest=RECEIPT_DIGEST,
        packet_bytes_digest=PACKET_DIGEST,
    )
    base.update(overrides)
    return scoring_guards.FrozenForecast(**base)


def final(**overrides: Any) -> scoring_guards.OfficialFinal:
    base = dict(
        contest_id="G1",
        home_team="HOME",
        away_team="AWAY",
        home_points=24,
        away_points=17,
        lifecycle="FINAL",
        observed_at=CUTOFF + timedelta(hours=6),
    )
    base.update(overrides)
    return scoring_guards.OfficialFinal(**base)


class ScoringGate(unittest.TestCase):
    def test_a_valid_packet_still_scores(self) -> None:
        from aggie_analytics.cycle37.receipt_fixtures import bind_final, bind_forecast

        packet, result = bind_forecast(AUTHORITY.root, forecast()), bind_final(AUTHORITY.root, final())
        verdict = scoring_guards.admit_for_scoring(packet, result, authority=AUTHORITY)
        self.assertTrue(verdict["admitted"], verdict)
        self.assertAlmostEqual(verdict["brier_component"], (0.6 - 1.0) ** 2)
        # The bare well-formed digests of b"receipt" and b"packet" have no bytes behind them.
        self.assertFalse(scoring_guards.admit_for_scoring(forecast(), final(), authority=AUTHORITY)["admitted"])

    def test_every_invalid_probability_is_refused(self) -> None:
        for value in (1.8, -0.5, float("nan"), float("inf"), True, "0.6"):
            with self.subTest(value=value):
                verdict = scoring_guards.admit_for_scoring(
                    forecast(home_win_probability=value), final()
                )
                self.assertFalse(verdict["admitted"])
                self.assertEqual(verdict["state"], scoring_guards.INVALID_PROBABILITY)
                self.assertNotIn("brier_component", verdict)

    def test_a_negative_or_boolean_final_score_is_refused(self) -> None:
        for value in (-7, True):
            with self.subTest(value=value):
                verdict = scoring_guards.admit_for_scoring(forecast(), final(home_points=value))
                self.assertFalse(verdict["admitted"])
                self.assertEqual(verdict["state"], scoring_guards.INVALID_SCORE)

    def test_a_negative_supplied_packet_score_is_refused(self) -> None:
        verdict = scoring_guards.admit_for_scoring(
            forecast(supplied_home_points=-1, supplied_away_points=17), final()
        )
        self.assertEqual(verdict["state"], scoring_guards.INVALID_SCORE)

    def test_an_arbitrary_string_is_not_a_digest(self) -> None:
        verdict = scoring_guards.admit_for_scoring(
            forecast(receipt_digest="yes", packet_bytes_digest="yes"), final()
        )
        self.assertFalse(verdict["admitted"])
        self.assertEqual(verdict["state"], scoring_guards.INVALID_DIGEST)

    def test_the_original_identity_and_time_refusals_still_hold(self) -> None:
        cases = {
            scoring_guards.WRONG_CONTEST: (forecast(contest_id="G2"), final()),
            scoring_guards.NOT_FINAL: (forecast(), final(lifecycle="IN_PROGRESS")),
            scoring_guards.LATE_FREEZE: (
                forecast(freeze_known_at=CUTOFF + timedelta(hours=1)),
                final(),
            ),
            scoring_guards.ORIENTATION_INVERTED: (
                forecast(designated_home_team="AWAY", designated_away_team="HOME"),
                final(),
            ),
        }
        for expected, (packet, result) in cases.items():
            with self.subTest(expected=expected):
                verdict = scoring_guards.admit_for_scoring(packet, result)
                self.assertEqual(verdict["state"], expected)

    def test_the_guard_version_records_that_admission_changed(self) -> None:
        self.assertNotEqual(
            scoring_guards.SCORING_GUARD_VERSION,
            scoring_guards.PREDECESSOR_GUARD_VERSION,
        )


class PacketEligibility(unittest.TestCase):
    GOOD = {
        "contest_id": "G1",
        "model_identity": "M1",
        "input_identity": "I1",
        "packet_bytes_digest": PACKET_DIGEST,
        "receipt_digest": RECEIPT_DIGEST,
        "freeze_known_at": FREEZE.isoformat(),
        "cutoff_utc": CUTOFF.isoformat(),
    }

    def test_a_complete_valid_packet_is_eligible(self) -> None:
        from aggie_analytics.cycle37.receipt_fixtures import bind_forecast

        bound = bind_forecast(AUTHORITY.root, forecast())
        packet = {**self.GOOD, "receipt_digest": bound.receipt_digest, "packet_bytes_digest": bound.packet_bytes_digest}
        self.assertTrue(scoring_guards.packet_eligibility(packet, authority=AUTHORITY)["eligible"])
        self.assertFalse(scoring_guards.packet_eligibility(self.GOOD, authority=AUTHORITY)["eligible"])
        self.assertFalse(scoring_guards.packet_eligibility(packet)["eligible"])

    def test_a_missing_field_is_still_reported_as_missing(self) -> None:
        verdict = scoring_guards.packet_eligibility({**self.GOOD, "receipt_digest": None})
        self.assertFalse(verdict["eligible"])
        self.assertIn("receipt_digest", verdict["missing_fields"])

    def test_nonsense_non_empty_fields_are_out_of_domain_not_eligible(self) -> None:
        verdict = scoring_guards.packet_eligibility(
            {**self.GOOD, "packet_bytes_digest": "yes", "receipt_digest": "sure"}
        )
        self.assertFalse(verdict["eligible"])
        self.assertEqual(verdict["state"], "INELIGIBLE_FIELD_OUT_OF_DOMAIN")
        self.assertEqual(len(verdict["domain_failures"]), 2)

    def test_naive_instants_are_refused(self) -> None:
        verdict = scoring_guards.packet_eligibility(
            {**self.GOOD, "freeze_known_at": "2026-09-01T10:00:00"}
        )
        self.assertFalse(verdict["eligible"])

    def test_a_freeze_at_or_after_the_cutoff_is_refused(self) -> None:
        verdict = scoring_guards.packet_eligibility(
            {**self.GOOD, "freeze_known_at": CUTOFF.isoformat()}
        )
        self.assertFalse(verdict["eligible"])
        self.assertEqual(verdict["state"], "INELIGIBLE_FREEZE_IS_NOT_BEFORE_THE_CUTOFF")


class NoForecastIsInvented(unittest.TestCase):
    """The repair closes a fail-open gate. It creates no eligible forecast."""

    def test_an_empty_store_still_yields_zero_admitted_rows(self) -> None:
        rows = [
            {"canonical_game_id": f"G{n}", "authority_class": "PROVEN_PIT_TRAINING_ROW"}
            for n in range(25)
        ]
        admitted = [
            row
            for row in rows
            if kernel_reference.admit_to_pit_consumer(
                kernel_reference.classify_pit(row, {}), row=row, receipts_by_game={}
            )
        ]
        self.assertEqual(admitted, [])


if __name__ == "__main__":
    unittest.main()
