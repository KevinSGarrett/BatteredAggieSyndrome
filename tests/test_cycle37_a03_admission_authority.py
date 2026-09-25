"""Cycle #37 — Attempt #3 — scoring and PIT admission bound to verified bytes (MF37A02-02, MF37A02-03).

The Attempt #2 manager's probes, replayed here verbatim in shape:

* ``admit_for_scoring`` admitted invented ``"a"*64``/``"b"*64`` digests with no receipt or packet bytes, no
  final provenance, the same team on both sides; omitted model/input bindings were never checked; a naive
  freeze instant raised ``TypeError``;
* ``classify_pit`` proved a row consuming ``REQUIRED-PRIOR`` from a self-asserted receipt naming
  ``UNRELATED-PRIOR`` with an invented digest.

Every positive case below runs against a test-only fixture store holding the actual bytes, and every
admission it supports is labelled as a fixture (never a real eligible forecast or real PIT proof).
"""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36 import kernel_reference as k  # noqa: E402
from aggie_analytics.cycle36 import scoring_guards as g  # noqa: E402
from aggie_analytics.cycle37 import receipt_authority as ra  # noqa: E402
from aggie_analytics.cycle37.receipt_fixtures import (  # noqa: E402
    bind_final,
    bind_forecast,
    fixture_authority,
    prior_receipt,
)

CUTOFF = datetime(2026, 9, 2, tzinfo=timezone.utc)
FREEZE = datetime(2026, 9, 1, tzinfo=timezone.utc)
NOW = datetime(2026, 9, 24, tzinfo=timezone.utc)


def forecast(**overrides) -> g.FrozenForecast:
    base = dict(contest_id="FIXTURE-GAME", model_identity="model-a", input_identity="inputs-a",
                designated_home_team="HOME", designated_away_team="AWAY", home_win_probability=0.7,
                freeze_known_at=FREEZE, cutoff_utc=CUTOFF, receipt_digest=None, packet_bytes_digest=None,
                neutral_site=False)
    base.update(overrides)
    return g.FrozenForecast(**base)


def final(**overrides) -> g.OfficialFinal:
    base = dict(contest_id="FIXTURE-GAME", home_team="HOME", away_team="AWAY", home_points=21, away_points=14,
                lifecycle="FINAL", observed_at=CUTOFF + timedelta(hours=4), neutral_site=False)
    base.update(overrides)
    return g.OfficialFinal(**base)


class _Store(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "fixture_store"
        self.authority = fixture_authority(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def bound(self, f=None, z=None):
        return bind_forecast(self.root, f or forecast()), bind_final(self.root, z or final())


class ManagerScoringCounterexamples(_Store):
    """ADMISSION_SOURCE_PROBE / ADMISSION_INSTALLED_PROBE cases, each refused for its own reason."""

    invented = dict(receipt_digest="a" * 64, packet_bytes_digest="b" * 64)

    def test_invented_digests_without_bytes_are_refused_with_or_without_an_authority(self) -> None:
        f, z = forecast(**self.invented), final(observed_at=None)
        self.assertEqual(g.admit_for_scoring(f, z)["state"], g.NO_AUTHORITY)
        verdict = g.admit_for_scoring(f, z, authority=self.authority)
        self.assertEqual(verdict["state"], g.RECEIPT_NOT_VERIFIED)
        self.assertIn("REFUSED_RECEIPT_BYTES_ABSENT", verdict["detail"])

    def test_the_explicit_model_mismatch_refusal_is_preserved(self) -> None:
        verdict = g.admit_for_scoring(forecast(**self.invented), final(), receipt_model_identity="other")
        self.assertEqual(verdict["state"], g.MODEL_MISMATCH)

    def test_nan_is_still_not_a_probability(self) -> None:
        verdict = g.admit_for_scoring(forecast(home_win_probability=float("nan"), **self.invented), final())
        self.assertEqual(verdict["state"], g.INVALID_PROBABILITY)

    def test_naive_and_mixed_instants_refuse_instead_of_raising(self) -> None:
        naive = forecast(freeze_known_at=datetime(2026, 9, 1), cutoff_utc=datetime(2026, 9, 2), **self.invented)
        mixed = forecast(freeze_known_at=datetime(2026, 9, 1), **self.invented)
        naive_final = final(observed_at=datetime(2026, 9, 3))
        for f, z in ((naive, final()), (mixed, final()), (forecast(**self.invented), naive_final)):
            with self.subTest(freeze=f.freeze_known_at, observed=z.observed_at):
                self.assertEqual(g.admit_for_scoring(f, z, authority=self.authority)["state"], g.INVALID_INSTANT)

    def test_the_same_team_on_both_sides_is_refused(self) -> None:
        f, z = self.bound()
        verdict = g.admit_for_scoring(dataclasses.replace(f, designated_away_team="HOME"),
                                      dataclasses.replace(z, away_team="HOME"), authority=self.authority)
        self.assertEqual(verdict["state"], g.PARTICIPANTS_NOT_DISTINCT)


class VerifiedScoringPath(_Store):
    def test_a_fixture_with_verified_bytes_and_test_only_authority_scores_and_says_so(self) -> None:
        f, z = self.bound()
        verdict = g.admit_for_scoring(f, z, authority=self.authority)
        self.assertEqual(verdict["state"], g.ADMITTED, verdict)
        self.assertAlmostEqual(verdict["brier_component"], (0.7 - 1.0) ** 2)
        self.assertEqual(verdict["authority_class"], ra.TEST_ONLY)
        self.assertFalse(verdict["counts_as_real_eligible_forecast"])
        self.assertEqual(verdict["evidence"]["forecast_receipt"]["receipt_digest"], f.receipt_digest)

    def test_a_tie_and_the_neutral_and_supplied_score_rules_still_hold(self) -> None:
        f, z = self.bound(z=final(home_points=17, away_points=17))
        verdict = g.admit_for_scoring(f, z, authority=self.authority)
        self.assertEqual((verdict["state"], verdict["outcome_for_home"], verdict["tie"]), (g.ADMITTED, 0.5, True))
        f2, z2 = self.bound(f=forecast(supplied_home_points=21, supplied_away_points=14))
        self.assertEqual(g.admit_for_scoring(f2, z2, authority=self.authority)["state"], g.ADMITTED)

    def test_every_binding_is_checked_against_the_bytes(self) -> None:
        f, z = self.bound()
        cases = {
            "tampered receipt digest": (dataclasses.replace(f, receipt_digest="c" * 64), z, g.RECEIPT_NOT_VERIFIED),
            "packet digest not the attested one": (dataclasses.replace(f, packet_bytes_digest="d" * 64), z,
                                                   g.PACKET_NOT_BOUND),
            "model differs from the receipt": (dataclasses.replace(f, model_identity="model-b"), z, g.MODEL_MISMATCH),
            "input differs from the receipt": (dataclasses.replace(f, input_identity="inputs-b"), z, g.MODEL_MISMATCH),
            "cutoff differs": (dataclasses.replace(f, cutoff_utc=CUTOFF + timedelta(minutes=1)), z,
                               g.RECEIPT_BINDING_MISMATCH),
            "freeze differs": (dataclasses.replace(f, freeze_known_at=FREEZE - timedelta(minutes=1)), z,
                               g.RECEIPT_BINDING_MISMATCH),
            "probability differs from the packet": (dataclasses.replace(f, home_win_probability=0.71), z,
                                                    g.PACKET_NOT_BOUND),
            "final without source provenance": (f, dataclasses.replace(z, source_receipt_digest=None),
                                                g.FINAL_NO_PROVENANCE),
            "final score differs from its receipt": (f, dataclasses.replace(z, home_points=24),
                                                     g.FINAL_PROVENANCE_MISMATCH),
            "final observation time absent": (f, dataclasses.replace(z, observed_at=None), g.FINAL_PROVENANCE_MISMATCH),
        }
        for name, (packet, result, expected) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(g.admit_for_scoring(packet, result, authority=self.authority)["state"], expected)

    def test_contest_and_orientation_are_bound_by_the_receipt_not_only_by_the_final(self) -> None:
        # The receipt was written for FIXTURE-GAME; a forecast and final both relabelled to another contest
        # agree with each other and must still be refused by the bytes.
        f, z = self.bound()
        other = g.admit_for_scoring(dataclasses.replace(f, contest_id="OTHER"),
                                    dataclasses.replace(z, contest_id="OTHER"), authority=self.authority)
        self.assertEqual(other["state"], g.RECEIPT_BINDING_MISMATCH)

    def test_tampered_receipt_or_payload_bytes_refuse(self) -> None:
        f, z = self.bound()
        (self.root / "payloads" / f"{f.packet_bytes_digest}.bin").write_bytes(b'{"home_win_probability": 0.99}')
        self.assertEqual(g.admit_for_scoring(f, z, authority=self.authority)["state"], g.RECEIPT_NOT_VERIFIED)
        f2, z2 = self.bound(f=forecast(contest_id="FIXTURE-GAME"))
        receipt_path = self.root / "receipts" / f"{f2.receipt_digest}.json"
        receipt_path.write_bytes(receipt_path.read_bytes().replace(b"model-a", b"model-z"))
        verdict = g.admit_for_scoring(f2, z2, authority=self.authority)
        self.assertEqual(verdict["state"], g.RECEIPT_NOT_VERIFIED)
        self.assertIn("DO_NOT_MATCH_THE_DIGEST", verdict["detail"])

    def test_an_untrusted_source_or_wrong_receipt_kind_refuses(self) -> None:
        untrusted = bind_forecast(self.root, forecast(), source_id="SELF-ASSERTED")
        z = bind_final(self.root, final())
        self.assertIn("SOURCE_NOT_TRUSTED",
                      g.admit_for_scoring(untrusted, z, authority=self.authority)["detail"])
        wrong_kind = dataclasses.replace(z, source_receipt_digest=bind_forecast(self.root, forecast()).receipt_digest)
        self.assertEqual(g.admit_for_scoring(bind_forecast(self.root, forecast()), wrong_kind,
                                             authority=self.authority)["state"], g.FINAL_NO_PROVENANCE)

    def test_packet_eligibility_needs_verified_bytes(self) -> None:
        f, _ = self.bound()
        packet = {"contest_id": f.contest_id, "model_identity": f.model_identity, "input_identity": f.input_identity,
                  "packet_bytes_digest": f.packet_bytes_digest, "receipt_digest": f.receipt_digest,
                  "freeze_known_at": FREEZE.isoformat(), "cutoff_utc": CUTOFF.isoformat()}
        self.assertEqual(g.packet_eligibility(packet)["state"], "INELIGIBLE_NO_TRUSTED_RECEIPT_AUTHORITY")
        verdict = g.packet_eligibility(packet, authority=self.authority)
        self.assertTrue(verdict["eligible"], verdict)
        self.assertFalse(verdict["counts_as_real_eligible_forecast"])
        self.assertEqual(g.packet_eligibility({**packet, "model_identity": "model-b"}, authority=self.authority)["state"],
                         "INELIGIBLE_RECEIPT_DOES_NOT_BIND_THIS_PACKET")
        self.assertEqual(g.packet_eligibility({**packet, "receipt_digest": "e" * 64}, authority=self.authority)["state"],
                         "INELIGIBLE_RECEIPT_BYTES_NOT_VERIFIED")

    def test_a_supersession_needs_both_rows_verified(self) -> None:
        f, z = self.bound()
        original = g.admit_for_scoring(f, z, authority=self.authority)
        corrected_final = bind_final(self.root, final(home_points=14, away_points=21))
        corrected = g.admit_for_scoring(f, corrected_final, authority=self.authority)
        row = g.supersede_after_correction(original, corrected, correction_known_at=NOW, authority=self.authority)
        self.assertEqual(row["supersedes"]["final"], [21, 14])
        with self.assertRaises(ValueError):
            g.supersede_after_correction(original, corrected, correction_known_at=NOW)
        forged = {**corrected, "final_home_points": 30}
        with self.assertRaises(ValueError):
            g.supersede_after_correction(original, forged, correction_known_at=NOW, authority=self.authority)
        with self.assertRaises(ValueError):
            g.supersede_after_correction(original, corrected, correction_known_at=datetime(2026, 9, 5),
                                         authority=self.authority)


class AuthorityConstruction(unittest.TestCase):
    def test_a_test_only_authority_must_be_acknowledged_and_marked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ra.ReceiptAuthorityError):
                ra.ReceiptAuthority(root, authority_class=ra.TEST_ONLY, authority_id="x", trusted_source_ids={"S"})
            with self.assertRaises(ra.ReceiptAuthorityError):
                ra.ReceiptAuthority(root, authority_class=ra.TEST_ONLY, authority_id="x", trusted_source_ids={"S"},
                                    acknowledge_test_only=True)
            ra.create_test_only_store(root, "x")
            with self.assertRaises(ra.ReceiptAuthorityError):
                ra.ReceiptAuthority(root, authority_class=ra.TEST_ONLY, authority_id="y", trusted_source_ids={"S"},
                                    acknowledge_test_only=True)
            ra.ReceiptAuthority(root, authority_class=ra.TEST_ONLY, authority_id="x", trusted_source_ids={"S"},
                                acknowledge_test_only=True)

    def test_no_durable_store_is_declared_so_real_eligibility_cannot_be_asserted(self) -> None:
        self.assertEqual(ra.DECLARED_DURABLE_STORES, ())
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ra.ReceiptAuthorityError):
                ra.ReceiptAuthority(tmp, authority_class=ra.DURABLE, authority_id="d", trusted_source_ids={"S"})

    def test_a_test_only_store_cannot_live_in_the_canonical_data_root(self) -> None:
        data_root = Path(ra._CANONICAL_DATA_ROOT)
        if not data_root.is_dir():
            self.skipTest("the canonical data root is not present on this machine")
        with self.assertRaises(ra.ReceiptAuthorityError):
            ra.ReceiptAuthority(data_root, authority_class=ra.TEST_ONLY, authority_id="x",
                                trusted_source_ids={"S"}, acknowledge_test_only=True)


ROW = {"canonical_game_id": "FIXTURE-TARGET", "authority_class": "PROVEN_PIT_TRAINING_ROW",
       "cutoff_utc": CUTOFF.isoformat(), "prior_observation_ids": ["PRIOR-1", "PRIOR-2"]}
PUBLISHED, KNOWN = FREEZE - timedelta(hours=2), FREEZE - timedelta(hours=1)


class ManagerPitCounterexample(unittest.TestCase):
    """PIT_INSTALLED_PROBE: a self-asserted receipt for UNRELATED-PRIOR admitted a row consuming REQUIRED-PRIOR."""

    row = {"canonical_game_id": "MANAGER-FIXTURE-ONLY", "cutoff_utc": CUTOFF.isoformat(),
           "authority_class": "RETROSPECTIVE", "prior_observation_ids": ["REQUIRED-PRIOR"]}
    receipt = {"source_id": "SELF-ASSERTED", "payload_sha256": "a" * 64, "published_at_utc": "2026-09-01T00:00:00Z",
               "known_at_utc": "2026-09-01T01:00:00Z", "prior_observation_ids": ["UNRELATED-PRIOR"]}

    def test_the_unrelated_prior_is_refused_and_both_gates_stay_closed(self) -> None:
        receipts = {self.row["canonical_game_id"]: self.receipt}
        derived = k.classify_pit(self.row, receipts, cutoff_utc=CUTOFF, now=NOW)
        self.assertNotEqual(derived["successor_state"], k.PIT_PROVEN)
        self.assertEqual(derived["receipt_validation"]["code"], k.REFUSED_PRIOR_NOT_ATTESTED)
        self.assertFalse(k.admit_to_pit_consumer(derived, now=NOW))
        self.assertFalse(k.admit_to_pit_consumer(derived, row=self.row, receipts_by_game=receipts,
                                                 cutoff_utc=CUTOFF, now=NOW))

    def test_the_required_prior_named_but_self_asserted_is_still_refused(self) -> None:
        claimed = {**self.receipt, "prior_observation_ids": ["REQUIRED-PRIOR"]}
        derived = k.classify_pit(self.row, {self.row["canonical_game_id"]: claimed}, cutoff_utc=CUTOFF, now=NOW)
        self.assertEqual(derived["receipt_validation"]["code"], k.REFUSED_NO_AUTHORITY)

    def test_the_missing_digest_and_late_known_at_refusals_are_preserved(self) -> None:
        for change, code in (({"payload_sha256": ""}, "REFUSED_RECEIPT_MISSING_REQUIRED_FIELDS"),
                             ({"known_at_utc": "2026-09-03T00:00:00Z"},
                              "REFUSED_RECEIPT_KNOWN_AT_IS_NOT_BEFORE_THE_CUTOFF")):
            with self.subTest(code=code):
                derived = k.classify_pit(self.row, {self.row["canonical_game_id"]: {**self.receipt, **change}},
                                         cutoff_utc=CUTOFF, now=NOW)
                self.assertEqual(derived["receipt_validation"]["code"], code)


class VerifiedPitPath(_Store):
    def _prior(self, priors, **kw):
        return prior_receipt(self.root, priors=priors, published_at=kw.pop("published", PUBLISHED),
                             known_at=kw.pop("known", KNOWN), **kw)

    def test_valid_test_receipts_binding_every_consumed_prior_prove_and_are_labelled(self) -> None:
        digest, stored = self._prior(["PRIOR-1", "PRIOR-2"])
        receipts = {ROW["canonical_game_id"]: {**stored, "receipt_digest": digest}}
        derived = k.classify_pit(ROW, receipts, now=NOW, authority=self.authority)
        self.assertEqual(derived["successor_state"], k.PIT_PROVEN, derived.get("receipt_validation"))
        self.assertEqual(derived["authority_class"], ra.TEST_ONLY)
        self.assertFalse(derived["counts_as_real_pit_proof"])
        self.assertTrue(k.admit_to_pit_consumer(derived, row=ROW, receipts_by_game=receipts, now=NOW,
                                                authority=self.authority))

    def test_per_prior_receipts_by_digest_also_prove(self) -> None:
        one, _ = self._prior("PRIOR-1")
        two, _ = self._prior("PRIOR-2")
        derived = k.classify_pit(ROW, {"PRIOR-1": one, "PRIOR-2": two}, now=NOW, authority=self.authority)
        self.assertEqual(derived["successor_state"], k.PIT_PROVEN, derived.get("receipt_validation"))

    def test_each_failure_class_refuses_for_its_own_reason(self) -> None:
        good, stored = self._prior(["PRIOR-1", "PRIOR-2"])
        unrelated, unrelated_stored = self._prior(["UNRELATED"])
        omitted, omitted_stored = self._prior(["PRIOR-1"])
        extra, extra_stored = self._prior(["PRIOR-1", "PRIOR-2", "PRIOR-3"])
        late, late_stored = self._prior(["PRIOR-1", "PRIOR-2"], known=CUTOFF + timedelta(hours=1),
                                        published=CUTOFF)
        future, future_stored = self._prior(["PRIOR-1", "PRIOR-2"], known=NOW + timedelta(days=30),
                                            published=NOW + timedelta(days=29))
        conflicting, _ = self._prior("PRIOR-1", publication=b"a different publication")
        other_two, _ = self._prior("PRIOR-2")
        agreeing_one, _ = self._prior("PRIOR-1")
        target = ROW["canonical_game_id"]
        cases = {
            k.REFUSED_PRIOR_NOT_ATTESTED + " (unrelated)": ({target: {**unrelated_stored, "receipt_digest": unrelated}}, ROW),
            k.REFUSED_PRIOR_NOT_ATTESTED + " (omitted)": ({target: {**omitted_stored, "receipt_digest": omitted}}, ROW),
            k.REFUSED_PRIOR_NOT_CONSUMED: ({target: {**extra_stored, "receipt_digest": extra}}, ROW),
            "REFUSED_RECEIPT_KNOWN_AT_IS_NOT_BEFORE_THE_CUTOFF": ({target: {**late_stored, "receipt_digest": late}}, ROW),
            "REFUSED_INSTANT_IS_IN_THE_FUTURE": ({target: {**future_stored, "receipt_digest": future}}, ROW),
            k.REFUSED_CONFLICTING: ({"PRIOR-1": [agreeing_one, conflicting], "PRIOR-2": other_two}, ROW),
            k.REFUSED_NO_BYTES_IDENTITY: ({target: stored}, ROW),
            k.REFUSED_CLAIM_DIFFERS: ({target: {**stored, "receipt_digest": good, "source_id": "OTHER"}}, ROW),
            "REFUSED_RECEIPT_BYTES_ABSENT": ({target: "f" * 64}, ROW),
            k.REFUSED_DEPENDENCIES_UNDECLARED: ({target: {**stored, "receipt_digest": good}},
                                                {k2: v for k2, v in ROW.items() if k2 != "prior_observation_ids"}),
            k.REFUSED_NOTHING_TO_PROVE: ({target: {**stored, "receipt_digest": good}}, {**ROW, "prior_observation_ids": []}),
        }
        for label, (receipts, row) in cases.items():
            expected = label.split(" ")[0]
            with self.subTest(case=label):
                derived = k.classify_pit(row, receipts, now=NOW, authority=self.authority)
                self.assertNotEqual(derived["successor_state"], k.PIT_PROVEN)
                self.assertEqual(derived["receipt_validation"]["code"], expected, derived["receipt_validation"])
                self.assertFalse(k.admit_to_pit_consumer(derived, row=row, receipts_by_game=receipts, now=NOW,
                                                         authority=self.authority))

    def test_tampered_receipt_bytes_refuse(self) -> None:
        digest, stored = self._prior(["PRIOR-1", "PRIOR-2"])
        path = self.root / "receipts" / f"{digest}.json"
        path.write_bytes(path.read_bytes().replace(b"PRIOR-2", b"PRIOR-9"))
        derived = k.classify_pit(ROW, {ROW["canonical_game_id"]: digest}, now=NOW, authority=self.authority)
        self.assertEqual(derived["receipt_validation"]["code"], "REFUSED_RECEIPT_BYTES_DO_NOT_MATCH_THE_DIGEST")

    def test_a_fabricated_or_standalone_classification_is_never_admitted(self) -> None:
        digest, stored = self._prior(["PRIOR-1", "PRIOR-2"])
        receipts = {ROW["canonical_game_id"]: {**stored, "receipt_digest": digest}}
        genuine = k.classify_pit(ROW, receipts, now=NOW, authority=self.authority)
        self.assertEqual(genuine["successor_state"], k.PIT_PROVEN)
        # A proven classification handed in without its row: the gate cannot see what the row consumed.
        self.assertFalse(k.admit_to_pit_consumer(genuine, now=NOW, authority=self.authority))
        fabricated = {"canonical_game_id": ROW["canonical_game_id"], "successor_state": k.PIT_PROVEN,
                      "admissible_to_a_pit_consumer": True, "receipt": stored}
        self.assertFalse(k.admit_to_pit_consumer(fabricated, now=NOW, authority=self.authority))
        # The same asserted classification against its row but no receipts, or no authority: refused.
        self.assertFalse(k.admit_to_pit_consumer(genuine, row=ROW, receipts_by_game={}, now=NOW,
                                                 authority=self.authority))
        self.assertFalse(k.admit_to_pit_consumer(genuine, row=ROW, receipts_by_game=receipts, now=NOW))


class RealEvidenceStaysZero(unittest.TestCase):
    def test_without_a_declared_durable_store_nothing_real_is_admitted(self) -> None:
        rows = [{"canonical_game_id": f"G{n}", "authority_class": "PROVEN_PIT_TRAINING_ROW",
                 "prior_observation_ids": [f"P{n}"], "cutoff_utc": CUTOFF.isoformat()} for n in range(25)]
        self.assertEqual([r for r in rows if k.admit_to_pit_consumer(k.classify_pit(r, {}), row=r, receipts_by_game={})],
                         [])
        self.assertEqual(ra.DECLARED_DURABLE_STORES, ())


if __name__ == "__main__":
    unittest.main()
