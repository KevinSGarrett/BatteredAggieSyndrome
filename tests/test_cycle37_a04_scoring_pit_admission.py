"""Cycle #37 — Attempt #4 — MF37A03-02 (scoring supersession) and MF37A03-03 (PIT target cutoff).

MF37A03-02. Two byte-verified fixture rows superseded correctly, but ``supersede_after_correction`` returned
whatever the corrected mapping said: both rows' contest ids rewritten to ``UNRELATED-GAME``, probability 1.8,
Brier -900, ``DURABLE_RECEIPT_STORE`` and ``counts_as_real_eligible_forecast=True`` all came back intact, and a
correction "known" before the freeze was accepted. The repaired function rebuilds both rows from their verified
receipts through the whole admission path and constructs the successor only from the rebuilt values.

MF37A03-03. With no target cutoff, ``classify_pit`` let each receipt's own cutoff stand in for the target's, so
two receipts carrying 12:00 and 14:00 proved the row (reported cutoff null) and a prior known at 13:00 became
admissible by omitting the cutoff. The repaired gate requires one aware target cutoff before any prior is
verified and reports that cutoff with the admission.

Every admission here comes from a test-only fixture authority and must say so; none is real eligibility or
real point-in-time proof. The independently conceived challenges (``*_challenge``) test assumptions the
manager's cases do not: that a correction's chronology is only about the freeze (it is also about the two
finals' own observations), that the two rows re-score the same forecast, that a second authority cannot
vouch for another's rows, and that instants are compared as instants rather than as text.
"""

from __future__ import annotations

import copy
import dataclasses
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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

UTC = timezone.utc


def t(hour: int, minute: int = 0) -> datetime:
    return datetime(2020, 1, 1, hour, minute, tzinfo=UTC)


NOW = datetime(2026, 9, 24, tzinfo=UTC)


class _Store(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "store"
        self.authority = fixture_authority(self.root, "a04-scoring-pit")

    def tearDown(self) -> None:
        self._tmp.cleanup()


class SupersessionTests(_Store):
    """MF37A03-02: a supersession is rebuilt from bytes and only its verified values are returned."""

    def forecast(self, **changes) -> g.FrozenForecast:
        base = dict(contest_id="FIXTURE-GAME", model_identity="fixture-model", input_identity="fixture-input",
                    designated_home_team="H", designated_away_team="A", home_win_probability=0.7,
                    freeze_known_at=t(10), cutoff_utc=t(12), receipt_digest=None, packet_bytes_digest=None)
        base.update(changes)
        return bind_forecast(self.root, g.FrozenForecast(**base))

    def final(self, home: int, away: int, **changes) -> g.OfficialFinal:
        base = dict(contest_id="FIXTURE-GAME", home_team="H", away_team="A", home_points=home, away_points=away,
                    lifecycle="FINAL", observed_at=t(16))
        base.update(changes)
        return bind_final(self.root, g.OfficialFinal(**base))

    def rows(self, forecast=None, corrected_final=None):
        forecast = forecast or self.forecast()
        original = g.admit_for_scoring(forecast, self.final(21, 17), authority=self.authority)
        corrected = g.admit_for_scoring(forecast, corrected_final or self.final(14, 17, observed_at=t(18)),
                                        authority=self.authority)
        self.assertTrue(original["admitted"], original)
        self.assertTrue(corrected["admitted"], corrected)
        return original, corrected

    def refuse(self, original, corrected, known=None, authority=None, expect=""):
        with self.assertRaises(ValueError) as caught:
            g.supersede_after_correction(original, corrected, correction_known_at=known or t(19),
                                         authority=authority or self.authority)
        self.assertIn(expect, str(caught.exception))
        return str(caught.exception)

    # ---- positive
    def test_a_valid_correction_produces_an_immutable_test_only_successor(self) -> None:
        original, corrected = self.rows()
        snapshot = copy.deepcopy(original)
        row = g.supersede_after_correction(original, corrected, correction_known_at=t(19), authority=self.authority)
        self.assertEqual(original, snapshot, "the predecessor row must not be changed")
        self.assertEqual((row["final_home_points"], row["final_away_points"]), (14, 17))
        self.assertFalse(row["home_won"])
        self.assertEqual(row["outcome_for_home"], 0.0)
        self.assertAlmostEqual(row["brier_component"], 0.7 ** 2)
        self.assertEqual(row["authority_class"], ra.TEST_ONLY)
        self.assertFalse(row["counts_as_real_eligible_forecast"])
        self.assertEqual(row["supersedes"]["final"], [21, 17])
        self.assertAlmostEqual(row["supersedes"]["brier_component"], (0.7 - 1.0) ** 2)
        self.assertEqual(row["supersedes"]["row_sha256"], g._row_digest(original))
        self.assertEqual(row["supersession_version"], g.SUPERSESSION_VERSION)
        self.assertTrue(row["original_row_kept"])

    def test_the_manager_positive_shape_with_equal_observation_times_still_supersedes(self) -> None:
        # The manager's fixture observed both finals at 16:00 and knew the correction at 17:00.
        original, corrected = self.rows(corrected_final=self.final(14, 17))
        row = g.supersede_after_correction(original, corrected, correction_known_at=t(17), authority=self.authority)
        self.assertEqual(row["supersedes"]["final"], [21, 17])

    # ---- the manager's three counterexamples
    def test_forged_contest_in_both_rows_is_refused(self) -> None:
        original, corrected = self.rows()
        original["contest_id"] = corrected["contest_id"] = "UNRELATED-GAME"
        self.refuse(original, corrected, expect="contest_id")

    def test_forged_probability_score_and_authority_are_refused(self) -> None:
        original, corrected = self.rows()
        for row in (original, corrected):
            row.update(home_win_probability=1.8, brier_component=-900, authority_class=ra.DURABLE,
                       counts_as_real_eligible_forecast=True)
        detail = self.refuse(original, corrected)
        for field in ("home_win_probability", "brier_component", "authority_class", "counts_as_real_eligible_forecast"):
            self.assertIn(field, detail)

    def test_a_correction_known_before_the_freeze_is_refused(self) -> None:
        original, corrected = self.rows()
        self.refuse(original, corrected, known=t(9), expect="cannot be known before")

    # ---- the declared negative classes, each on its own
    def test_each_single_field_forgery_is_refused(self) -> None:
        for field, value in (("home_win_probability", 0.71), ("brier_component", 0.0), ("outcome_for_home", 1.0),
                             ("home_won", True), ("tie", True), ("final_home_points", 99),
                             ("authority_class", ra.DURABLE), ("counts_as_real_eligible_forecast", True),
                             ("state", "SOMETHING"), ("guard_version", "v0")):
            with self.subTest(field=field):
                original, corrected = self.rows()
                corrected[field] = value
                self.assertIn(field, self.refuse(original, corrected))

    def test_extra_or_missing_fields_are_refused(self) -> None:
        original, corrected = self.rows()
        corrected["real_evidence"] = True
        self.refuse(original, corrected, expect="real_evidence")
        original, corrected = self.rows()
        del corrected["evidence"]["authority"]
        self.refuse(original, corrected, expect="evidence")

    def test_evidence_authority_promotion_is_refused(self) -> None:
        original, corrected = self.rows()
        corrected["evidence"]["authority"]["authority_class"] = ra.DURABLE
        corrected["evidence"]["authority"]["counts_as_real_evidence"] = True
        self.refuse(original, corrected, expect="evidence")

    def test_absent_or_altered_bytes_are_refused(self) -> None:
        original, corrected = self.rows()
        final_digest = corrected["evidence"]["final_receipt"]["receipt_digest"]
        (self.root / "receipts" / f"{final_digest}.json").unlink()
        self.refuse(original, corrected, expect="RECEIPT_BYTES_ABSENT")
        original, corrected = self.rows()
        payload = corrected["evidence"]["forecast_receipt"]["payload_digest"]
        (self.root / "payloads" / f"{payload}.bin").write_bytes(b'{"home_win_probability": 0.99}')
        self.refuse(original, corrected, expect="PAYLOAD_BYTES_DO_NOT_MATCH")

    def test_a_swapped_final_receipt_of_another_contest_is_refused(self) -> None:
        original, corrected = self.rows()
        other = self.final(3, 0, contest_id="OTHER-GAME", observed_at=t(18))
        corrected["evidence"]["final_receipt"]["receipt_digest"] = other.source_receipt_digest
        self.refuse(original, corrected)

    def test_altered_final_provenance_is_refused(self) -> None:
        # A final receipt of the same contest whose stored bytes state another score than the row.
        original, corrected = self.rows()
        altered = self.final(10, 17, observed_at=t(18))
        corrected["evidence"]["final_receipt"]["receipt_digest"] = altered.source_receipt_digest
        self.refuse(original, corrected, expect="final_home_points")

    def test_the_same_final_twice_is_not_a_correction(self) -> None:
        original, _corrected = self.rows()
        self.refuse(original, copy.deepcopy(original), expect="same final receipt")

    def test_a_final_observed_before_the_cutoff_is_not_admitted_at_all(self) -> None:
        early = g.admit_for_scoring(self.forecast(), self.final(21, 17, observed_at=t(11)), authority=self.authority)
        self.assertEqual(early["state"], g.FINAL_BEFORE_CUTOFF)

    def test_an_unaware_or_absent_correction_time_or_authority_is_refused(self) -> None:
        original, corrected = self.rows()
        self.refuse(original, corrected, known=datetime(2020, 1, 1, 19), expect="timezone-aware")
        with self.assertRaises(ValueError):
            g.supersede_after_correction(original, corrected, correction_known_at=t(19), authority=None)

    # ---- this attempt's own challenges
    def test_correction_chronology_challenge_the_corrected_final_cannot_precede_the_original(self) -> None:
        forecast = self.forecast()
        original = g.admit_for_scoring(forecast, self.final(21, 17, observed_at=t(18)), authority=self.authority)
        corrected = g.admit_for_scoring(forecast, self.final(14, 17, observed_at=t(16)), authority=self.authority)
        self.refuse(original, corrected, known=t(20), expect="before the final it corrects")
        # And a correction known before the corrected final was itself observed.
        original, corrected = self.rows(corrected_final=self.final(14, 17, observed_at=t(20)))
        self.refuse(original, corrected, known=t(19), expect="cannot be known before")

    def test_forecast_swap_challenge_two_rows_must_rescore_one_frozen_forecast(self) -> None:
        first = self.forecast()
        second = self.forecast(model_identity="another-model")
        original = g.admit_for_scoring(first, self.final(21, 17), authority=self.authority)
        corrected = g.admit_for_scoring(second, self.final(14, 17, observed_at=t(18)), authority=self.authority)
        self.assertTrue(original["admitted"] and corrected["admitted"])
        self.refuse(original, corrected, expect="same frozen forecast")

    def test_second_authority_challenge_rows_do_not_verify_in_another_store(self) -> None:
        original, corrected = self.rows()
        other = fixture_authority(Path(self._tmp.name) / "other", "a04-other-store")
        self.refuse(original, corrected, authority=other, expect="does not verify")

    def test_orientation_inversion_challenge_is_refused_in_the_rebuild(self) -> None:
        original, corrected = self.rows()
        inverted = self.final(17, 14, home_team="A", away_team="H", observed_at=t(18))
        corrected["evidence"]["final_receipt"]["receipt_digest"] = inverted.source_receipt_digest
        self.refuse(original, corrected, expect="REFUSED_NEUTRAL_ORIENTATION_INVERTED")


class TargetCutoffTests(_Store):
    """MF37A03-03: one explicit, aware target cutoff, before any prior is verified, used throughout."""

    def receipt(self, prior: str, known: datetime, cutoff: datetime | None = None) -> str:
        extra = {"cutoff_utc": cutoff.isoformat()} if cutoff else None
        digest, _stored = prior_receipt(self.root, priors=prior, published_at=known - timedelta(hours=1),
                                        known_at=known, extra=extra)
        return digest

    def classify(self, row, receipts, **kw):
        return k.classify_pit(row, receipts, now=NOW, authority=self.authority, **kw)

    def admits(self, row, receipts, classification=None, **kw) -> bool:
        classification = classification or self.classify(row, receipts, **kw)
        return k.admit_to_pit_consumer(classification, row=row, receipts_by_game=receipts, now=NOW,
                                       authority=self.authority, **kw)

    # ---- positive
    def test_verified_priors_before_one_explicit_cutoff_are_admitted_with_that_cutoff(self) -> None:
        receipts = {"PRIOR-1": self.receipt("PRIOR-1", t(9)), "PRIOR-2": self.receipt("PRIOR-2", t(11, 30))}
        row = {"canonical_game_id": "TARGET", "consumed_prior_ids": ["PRIOR-1", "PRIOR-2"],
               "cutoff_utc": t(12).isoformat()}
        classification = self.classify(row, receipts)
        self.assertEqual(classification["successor_state"], k.PIT_PROVEN, classification.get("receipt_validation"))
        self.assertEqual(classification["cutoff_utc"], t(12).isoformat())
        self.assertEqual(classification["cutoff_source"], "row cutoff_utc")
        self.assertEqual(classification["authority_class"], ra.TEST_ONLY)
        self.assertFalse(classification["counts_as_real_pit_proof"])
        self.assertTrue(self.admits(row, receipts, classification))

    def test_a_future_target_cutoff_is_a_legitimate_decision_time(self) -> None:
        receipts = {"PRIOR-1": self.receipt("PRIOR-1", t(9))}
        row = {"canonical_game_id": "UPCOMING", "consumed_prior_ids": ["PRIOR-1"],
               "cutoff_utc": "2099-09-01T18:00:00+00:00"}
        self.assertEqual(self.classify(row, receipts)["successor_state"], k.PIT_PROVEN)

    # ---- the manager's cases
    def test_the_manager_missing_and_mixed_receipt_cutoff_cases_refuse(self) -> None:
        r1 = self.receipt("PRIOR-1", t(9), cutoff=t(12))
        r2 = self.receipt("PRIOR-2", t(13), cutoff=t(14))
        missing = self.classify({"canonical_game_id": "TARGET", "consumed_prior_ids": ["PRIOR-1"]}, {"PRIOR-1": r1})
        mixed = {"canonical_game_id": "TARGET", "consumed_prior_ids": ["PRIOR-1", "PRIOR-2"]}
        both = self.classify(mixed, {"PRIOR-1": r1, "PRIOR-2": r2})
        for verdict in (missing, both):
            self.assertNotEqual(verdict["successor_state"], k.PIT_PROVEN)
            self.assertEqual(verdict["receipt_validation"]["code"], k.REFUSED_NO_TARGET_CUTOFF)
            self.assertIsNone(verdict["cutoff_utc"])
        self.assertFalse(self.admits(mixed, {"PRIOR-1": r1, "PRIOR-2": r2}))

    def test_a_late_prior_cannot_become_admissible_by_omitting_the_cutoff(self) -> None:
        r2 = self.receipt("PRIOR-2", t(13), cutoff=t(14))
        row = {"canonical_game_id": "TARGET", "consumed_prior_ids": ["PRIOR-2"]}
        self.assertFalse(self.admits(row, {"PRIOR-2": r2}))
        self.assertFalse(self.admits(dict(row, cutoff_utc=t(12).isoformat()), {"PRIOR-2": r2}))
        self.assertEqual(self.classify(dict(row, cutoff_utc=t(12).isoformat()), {"PRIOR-2": r2})
                         ["receipt_validation"]["code"], "REFUSED_RECEIPT_KNOWN_AT_IS_NOT_BEFORE_THE_CUTOFF")

    # ---- malformed, naive and conflicting target cutoffs
    def test_unusable_target_cutoffs_refuse_before_any_prior_is_verified(self) -> None:
        receipts = {"PRIOR-1": self.receipt("PRIOR-1", t(9))}
        base = {"canonical_game_id": "TARGET", "consumed_prior_ids": ["PRIOR-1"]}
        for label, row, kw, code in (
            ("unparseable", dict(base, cutoff_utc="noon"), {}, k.REFUSED_TARGET_CUTOFF_UNUSABLE),
            ("naive string", dict(base, cutoff_utc="2020-01-01T12:00:00"), {}, k.REFUSED_TARGET_CUTOFF_UNUSABLE),
            ("naive datetime", dict(base, cutoff_utc=datetime(2020, 1, 1, 12)), {}, k.REFUSED_TARGET_CUTOFF_UNUSABLE),
            ("not an instant", dict(base, cutoff_utc=1577880000), {}, k.REFUSED_TARGET_CUTOFF_UNUSABLE),
            ("naive argument", base, {"cutoff_utc": datetime(2020, 1, 1, 12)}, k.REFUSED_TARGET_CUTOFF_UNUSABLE),
            ("argument versus row", dict(base, cutoff_utc=t(12).isoformat()), {"cutoff_utc": t(13)},
             k.REFUSED_TARGET_CUTOFF_CONFLICT),
            ("two row fields", dict(base, cutoff_utc=t(12).isoformat(), decision_cutoff_utc=t(14).isoformat()), {},
             k.REFUSED_TARGET_CUTOFF_CONFLICT),
        ):
            with self.subTest(case=label):
                verdict = self.classify(row, receipts, **kw)
                self.assertEqual(verdict["receipt_validation"]["code"], code, verdict["receipt_validation"])
                self.assertFalse(self.admits(row, receipts, **kw))

    def test_the_gate_refuses_a_classification_reporting_another_cutoff(self) -> None:
        receipts = {"PRIOR-1": self.receipt("PRIOR-1", t(9))}
        row = {"canonical_game_id": "TARGET", "consumed_prior_ids": ["PRIOR-1"], "cutoff_utc": t(12).isoformat()}
        classification = dict(self.classify(row, receipts), cutoff_utc=t(15).isoformat())
        self.assertFalse(self.admits(row, receipts, classification))
        genuine = self.classify(row, receipts)
        self.assertFalse(k.admit_to_pit_consumer(genuine, row=row, receipts_by_game=receipts, cutoff_utc=t(13),
                                                 now=NOW, authority=self.authority))

    def test_the_domain_helper_no_longer_substitutes_a_receipt_cutoff(self) -> None:
        from aggie_analytics.cycle37.admission_domains import valid_publication_receipt

        receipt = {"source_id": "S", "prior_game_id": "P", "payload_sha256": "a" * 64,
                   "published_at_utc": t(8).isoformat(), "known_at_utc": t(9).isoformat(),
                   "cutoff_utc": t(12).isoformat()}
        verdict = valid_publication_receipt(receipt, prior_game_id="P", cutoff_utc=None, now=NOW)
        self.assertEqual(verdict.code, "REFUSED_RECEIPT_HAS_NO_CUTOFF_TO_COMPARE")

    # ---- this attempt's own challenge: instants, not text
    def test_offset_instants_challenge_compares_values_not_text(self) -> None:
        # 07:00-05:00 is 12:00Z. A prior known at 13:00+02:00 (11:00Z) is before it although "13:00" sorts
        # after "07:00"; a prior known at 07:30-05:00 (12:30Z) is after it although "07:30" sorts before "12:00".
        cutoff_text = "2020-01-01T07:00:00-05:00"
        early = prior_receipt(self.root, priors="EARLY", published_at=t(10),
                              known_at=datetime(2020, 1, 1, 13, tzinfo=timezone(timedelta(hours=2))))[0]
        late = prior_receipt(self.root, priors="LATE", published_at=t(11),
                             known_at=datetime(2020, 1, 1, 7, 30, tzinfo=timezone(timedelta(hours=-5))))[0]
        row = {"canonical_game_id": "TARGET", "consumed_prior_ids": ["EARLY"], "cutoff_utc": cutoff_text}
        admitted = self.classify(row, {"EARLY": early})
        self.assertEqual(admitted["successor_state"], k.PIT_PROVEN, admitted.get("receipt_validation"))
        # The same instant stated twice in two spellings is one cutoff, not a conflict.
        same = self.classify(dict(row, decision_cutoff_utc="2020-01-01T12:00:00Z"), {"EARLY": early})
        self.assertEqual(same["successor_state"], k.PIT_PROVEN, same.get("receipt_validation"))
        refused = self.classify(dict(row, consumed_prior_ids=["LATE"]), {"LATE": late})
        self.assertEqual(refused["receipt_validation"]["code"], "REFUSED_RECEIPT_KNOWN_AT_IS_NOT_BEFORE_THE_CUTOFF")


if __name__ == "__main__":
    unittest.main()
