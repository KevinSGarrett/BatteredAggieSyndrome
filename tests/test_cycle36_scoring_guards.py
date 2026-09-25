"""R36-10: every scoring refusal R36-10 names, with its own reason code.

A generic "join failed" is not a guard. These tests require that a wrong
contest, a late freeze, a supplied-score mismatch, a future correction, an
inverted neutral orientation and a duplicate oriented row each produce their
own named refusal, and that the admitted path is reached only when all of
them hold.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.scoring_guards import (  # noqa: E402
    ADMITTED,
    DUPLICATE_ORIENTED_ROW,
    FUTURE_CORRECTION,
    INVALID_DIGEST,
    LATE_FREEZE,
    MODEL_MISMATCH,
    NO_AUTHORITY,
    NO_RECEIPT,
    NOT_FINAL,
    ORIENTATION_INVERTED,
    RECEIPT_NOT_VERIFIED,
    SCORE_MISMATCH,
    WRONG_CONTEST,
    FrozenForecast,
    OfficialFinal,
    admit_for_scoring,
    packet_eligibility,
)
from aggie_analytics.cycle37.receipt_fixtures import bind_final, bind_forecast, fixture_authority  # noqa: E402

CUTOFF = datetime(2026, 9, 5, 18, 0, tzinfo=timezone.utc)

#: MF37A02-02 fixture correction (Cycle #37 - Attempt #3). The positive tests below used to admit the
#: digest-shaped placeholders "ab" * 32 and "cd" * 32 with no receipt or packet bytes behind them -- the exact
#: behaviour MF37A02-02 names as the defect (invented digests reached ADMITTED_FOR_SCORING). Their intent, that
#: the admitted path is reached only when every invariant holds, is kept by binding each positive case to real
#: bytes in a test-only fixture store and passing its authority; the placeholder shape is kept as a negative in
#: DigestShapeIsNotADigest. Every admission here is labelled a fixture and counts as no real forecast.
_STORE: tempfile.TemporaryDirectory | None = None
AUTHORITY = None


def setUpModule() -> None:
    global _STORE, AUTHORITY
    _STORE = tempfile.TemporaryDirectory()
    AUTHORITY = fixture_authority(Path(_STORE.name) / "store", "r36-10-scoring-fixture")


def tearDownModule() -> None:
    if _STORE is not None:
        _STORE.cleanup()


def bound(packet: FrozenForecast, result: OfficialFinal) -> tuple[FrozenForecast, OfficialFinal]:
    """The forecast and final with real receipt, packet and source bytes behind their digests."""

    return bind_forecast(AUTHORITY.root, packet), bind_final(AUTHORITY.root, result)


def forecast(**overrides) -> FrozenForecast:
    base = dict(
        contest_id="SRC-002:GAME:1",
        model_identity="model-a",
        input_identity="inputs-a",
        designated_home_team="SRC-002:TEAM:10",
        designated_away_team="SRC-002:TEAM:20",
        home_win_probability=0.7,
        freeze_known_at=CUTOFF - timedelta(hours=2),
        cutoff_utc=CUTOFF,
        # MF36-04 fixture correction. These were "r" * 64 and "p" * 64.
        # Neither is a SHA-256: "r" and "p" are not hexadecimal digits, so
        # they are 64-character strings shaped like a digest and carrying no
        # digest. That is precisely the "arbitrary digest strings reach
        # admission" half of the finding, and the repaired guard rejects
        # them. The placeholders are now hexadecimal so the positive path
        # still exercises a well-formed digest; see
        # test_a_digest_shaped_non_hex_string_is_refused below for the
        # preserved negative.
        receipt_digest="ab" * 32,
        packet_bytes_digest="cd" * 32,
        neutral_site=False,
    )
    base.update(overrides)
    return FrozenForecast(**base)


def final(**overrides) -> OfficialFinal:
    base = dict(
        contest_id="SRC-002:GAME:1",
        home_team="SRC-002:TEAM:10",
        away_team="SRC-002:TEAM:20",
        home_points=24,
        away_points=17,
        lifecycle="FINAL",
        observed_at=CUTOFF + timedelta(hours=4),
        neutral_site=False,
    )
    base.update(overrides)
    return OfficialFinal(**base)


class AdmissionTests(unittest.TestCase):
    def test_the_admitted_path(self) -> None:
        result = admit_for_scoring(*bound(forecast(), final()), authority=AUTHORITY)
        self.assertEqual(result["state"], ADMITTED)
        self.assertTrue(result["home_won"])
        self.assertAlmostEqual(result["brier_component"], (0.7 - 1.0) ** 2)
        self.assertFalse(result["counts_as_real_eligible_forecast"])

    def test_a_tie_is_outcome_one_half_not_a_home_loss(self) -> None:
        result = admit_for_scoring(*bound(forecast(), final(home_points=21, away_points=21)), authority=AUTHORITY)
        self.assertEqual(result["state"], ADMITTED)
        self.assertTrue(result["tie"])
        self.assertEqual(result["outcome_for_home"], 0.5)
        self.assertAlmostEqual(result["brier_component"], (0.7 - 0.5) ** 2)

    def test_a_correction_supersedes_without_rewriting_the_scored_row(self) -> None:
        from aggie_analytics.cycle36.scoring_guards import supersede_after_correction

        original = admit_for_scoring(*bound(forecast(), final()), authority=AUTHORITY)
        corrected = admit_for_scoring(*bound(forecast(), final(home_points=17, away_points=24)), authority=AUTHORITY)
        known = CUTOFF + timedelta(days=2)
        row = supersede_after_correction(original, corrected, correction_known_at=known, authority=AUTHORITY)
        self.assertEqual(row["supersedes"]["final"], [24, 17])
        self.assertFalse(row["home_won"])
        self.assertEqual(original["final_home_points"], 24)  # the scored row is untouched
        with self.assertRaises(ValueError):
            supersede_after_correction(original, original, correction_known_at=known, authority=AUTHORITY)
        other = admit_for_scoring(*bound(forecast(contest_id="SRC-002:GAME:9"), final(contest_id="SRC-002:GAME:9")),
                                  authority=AUTHORITY)
        with self.assertRaises(ValueError):
            supersede_after_correction(original, other, correction_known_at=known, authority=AUTHORITY)

    def test_wrong_contest(self) -> None:
        result = admit_for_scoring(forecast(contest_id="SRC-002:GAME:2"), final())
        self.assertEqual(result["state"], WRONG_CONTEST)
        self.assertFalse(result["admitted"])

    def test_late_freeze(self) -> None:
        result = admit_for_scoring(
            forecast(freeze_known_at=CUTOFF + timedelta(seconds=1)), final()
        )
        self.assertEqual(result["state"], LATE_FREEZE)

    def test_freeze_exactly_at_cutoff_is_late(self) -> None:
        result = admit_for_scoring(forecast(freeze_known_at=CUTOFF), final())
        self.assertEqual(result["state"], LATE_FREEZE)

    def test_missing_receipt(self) -> None:
        for field in ("receipt_digest", "packet_bytes_digest"):
            with self.subTest(field=field):
                result = admit_for_scoring(forecast(**{field: None}), final())
                self.assertEqual(result["state"], NO_RECEIPT)

    def test_supplied_score_mismatch(self) -> None:
        result = admit_for_scoring(
            forecast(supplied_home_points=21, supplied_away_points=17), final()
        )
        self.assertEqual(result["state"], SCORE_MISMATCH)

    def test_supplied_score_agreement_is_allowed(self) -> None:
        result = admit_for_scoring(
            *bound(forecast(supplied_home_points=24, supplied_away_points=17), final()), authority=AUTHORITY
        )
        self.assertEqual(result["state"], ADMITTED)

    def test_future_correction(self) -> None:
        result = admit_for_scoring(
            forecast(),
            final(corrected_at=CUTOFF + timedelta(days=2)),
        )
        self.assertEqual(result["state"], FUTURE_CORRECTION)

    def test_neutral_orientation_inversion(self) -> None:
        result = admit_for_scoring(
            forecast(
                designated_home_team="SRC-002:TEAM:20",
                designated_away_team="SRC-002:TEAM:10",
            ),
            final(neutral_site=True),
        )
        self.assertEqual(result["state"], ORIENTATION_INVERTED)

    def test_neutral_flag_disagreement_is_refused(self) -> None:
        result = admit_for_scoring(
            forecast(neutral_site=True), final(neutral_site=False)
        )
        self.assertEqual(result["state"], ORIENTATION_INVERTED)

    def test_duplicate_oriented_row(self) -> None:
        result = admit_for_scoring(
            forecast(),
            final(),
            already_scored_contests=frozenset({"SRC-002:GAME:1"}),
        )
        self.assertEqual(result["state"], DUPLICATE_ORIENTED_ROW)

    def test_nonfinal_observation(self) -> None:
        for lifecycle in ("PREGAME", "CANCELLED", "IN_PROGRESS"):
            with self.subTest(lifecycle=lifecycle):
                result = admit_for_scoring(forecast(), final(lifecycle=lifecycle))
                self.assertEqual(result["state"], NOT_FINAL)

    def test_model_or_input_identity_mismatch(self) -> None:
        self.assertEqual(
            admit_for_scoring(
                forecast(), final(), receipt_model_identity="model-b"
            )["state"],
            MODEL_MISMATCH,
        )
        self.assertEqual(
            admit_for_scoring(
                forecast(), final(), receipt_input_identity="inputs-b"
            )["state"],
            MODEL_MISMATCH,
        )

    def test_a_tie_is_reported_not_counted_as_a_home_win(self) -> None:
        result = admit_for_scoring(*bound(forecast(), final(home_points=17, away_points=17)), authority=AUTHORITY)
        self.assertEqual(result["state"], ADMITTED)
        self.assertTrue(result["tie"])
        self.assertFalse(result["home_won"])


class PacketEligibilityTests(unittest.TestCase):
    def test_a_complete_packet_is_eligible(self) -> None:
        bound_forecast, _ = bound(forecast(), final())
        packet = {
            "contest_id": "SRC-002:GAME:1",
            "model_identity": "model-a",
            "input_identity": "inputs-a",
            "packet_bytes_digest": bound_forecast.packet_bytes_digest,
            "receipt_digest": bound_forecast.receipt_digest,
            "freeze_known_at": "2026-09-05T16:00:00Z",
            "cutoff_utc": "2026-09-05T18:00:00Z",
        }
        self.assertTrue(packet_eligibility(packet, authority=AUTHORITY)["eligible"])
        # MF37A02-02: the same complete, well-formed packet without an authority is not eligible.
        self.assertEqual(packet_eligibility(packet)["state"], "INELIGIBLE_NO_TRUSTED_RECEIPT_AUTHORITY")

    def test_a_packet_without_a_receipt_is_ineligible(self) -> None:
        result = packet_eligibility(
            {
                "contest_id": "SRC-002:GAME:1",
                "model_identity": "model-a",
                "input_identity": "inputs-a",
                "packet_bytes_digest": "cd" * 32,
                "freeze_known_at": "2026-09-05T16:00:00Z",
                "cutoff_utc": "2026-09-05T18:00:00Z",
            }
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["missing_fields"], ["receipt_digest"])

    def test_an_empty_packet_names_every_missing_binding(self) -> None:
        result = packet_eligibility({})
        self.assertFalse(result["eligible"])
        self.assertEqual(len(result["missing_fields"]), 7)


if __name__ == "__main__":
    unittest.main()


class DigestShapeIsNotADigest(unittest.TestCase):
    """MF36-04: a 64-character string is not a SHA-256 unless it is hex.

    This is the negative the corrected fixtures above refer to. It is kept
    explicit so the reason those placeholders changed stays visible: the old
    values were rejected because they were never digests, not because the
    guard became arbitrarily stricter.
    """

    def test_a_digest_shaped_non_hex_string_is_refused(self) -> None:
        for value in ("r" * 64, "p" * 64, "z" * 64):
            with self.subTest(value=value[:4] + "..."):
                result = admit_for_scoring(
                    forecast(receipt_digest=value, packet_bytes_digest=value), final()
                )
                self.assertFalse(result["admitted"])
                self.assertEqual(result["state"], INVALID_DIGEST)

    def test_a_short_or_uppercase_hex_string_is_refused(self) -> None:
        for value in ("ab" * 16, ("AB" * 32)):
            with self.subTest(value=value[:4] + "..."):
                result = admit_for_scoring(forecast(receipt_digest=value), final())
                self.assertFalse(result["admitted"])

    def test_a_well_formed_hex_digest_is_accepted(self) -> None:
        # MF37A02-02: a well-formed digest passes the *domain* check only. With no bytes behind it the guard
        # refuses -- without an authority for want of one, with an authority because the bytes are absent --
        # and the same forecast with real bytes behind its digests is admitted.
        self.assertEqual(admit_for_scoring(forecast(), final())["state"], NO_AUTHORITY)
        self.assertEqual(admit_for_scoring(forecast(), final(), authority=AUTHORITY)["state"], RECEIPT_NOT_VERIFIED)
        self.assertTrue(admit_for_scoring(*bound(forecast(), final()), authority=AUTHORITY)["admitted"])
