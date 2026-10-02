"""R36-08: reconstruct the arithmetic, and keep PIT admission fail-closed.

The reconstruction must exclude the target contest, order priors by instant,
never read a target outcome, and change its answer when the declared source
universe changes -- because the stored kernel and the Cycle #35 reference
disagreed about the universe and neither said so.

The admission gate must refuse a producer ``PROVEN`` label that carries no
receipt, which is all 36 of them.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.kernel_reference import (  # noqa: E402
    PIT_PROVEN,
    PIT_RETROSPECTIVE_ONLY,
    PIT_SUPERSEDED,
    RECONSTRUCTED_DIFFERENT,
    RECONSTRUCTED_EXACT,
    TARGET_GAME_ABSENT,
    TeamObservation,
    admit_to_pit_consumer,
    build_universe,
    classify_pit,
    observations_from_rows,
    parse_instant,
    reconstruct_row,
)

BASE = datetime(2020, 9, 5, 18, 0, tzinfo=timezone.utc)


def game(gid: int, offset_days: int, home: int, away: int, hp: int, ap: int, **kw):
    return {
        "id": gid,
        "season": kw.get("season", 2020),
        "startDate": (BASE + timedelta(days=offset_days)).isoformat().replace("+00:00", "Z"),
        "homeId": home,
        "awayId": away,
        "homePoints": hp,
        "awayPoints": ap,
        "completed": kw.get("completed", True),
        "homeClassification": "fbs",
        "awayClassification": "fbs",
    }


ROWS = [
    game(1, 0, 10, 20, 30, 10),
    game(2, 7, 10, 30, 14, 21),
    game(3, 14, 40, 10, 7, 28),
    game(4, 21, 10, 50, 17, 17),      # tie
    game(5, 28, 10, 60, 20, 10),      # the target
]
EXTRA = [game(6, 10, 10, 70, 13, 6)]  # only in the "wide" universe


def universe(rows, name="U", **kw):
    return build_universe(name, observations_from_rows(rows, "fixture.jsonl"), **kw)


KERNEL_ROW = {
    "canonical_game_id": "SRC-002:GAME:5",
    "season": 2020,
    "home_canonical_team_id": "SRC-002:TEAM:10",
    "away_canonical_team_id": "SRC-002:TEAM:60",
    "authority_class": "PROVEN_PIT_TRAINING_ROW",
    "home_features": {
        "pit_prior_games_played": 4,
        "pit_prior_points_for_mean": 22.25,   # (30+14+28+17)/4
        "pit_prior_points_against_mean": 13.75,
        "pit_prior_margin_mean": 8.5,         # (89-55)/4
        "pit_prior_win_rate": 2 / 3,
        "pit_season_to_date_games": 4,
        "pit_season_to_date_win_rate": 2 / 3,
        "pit_prior_season_win_rate": 2 / 3,
    },
    "away_features": {
        "pit_prior_games_played": 0,
        "pit_prior_points_for_mean": None,
        "pit_prior_points_against_mean": None,
        "pit_prior_margin_mean": None,
        "pit_prior_win_rate": None,
        "pit_season_to_date_games": 0,
        "pit_season_to_date_win_rate": None,
        "pit_prior_season_win_rate": None,
    },
}


class ReconstructionTests(unittest.TestCase):
    def test_exact_match_under_the_right_universe(self) -> None:
        result = reconstruct_row(KERNEL_ROW, universe(ROWS))
        self.assertEqual(result["state"], RECONSTRUCTED_EXACT, result.get("differences"))
        self.assertEqual(result["home_admitted_prior_count"], 4)

    def test_target_contest_is_excluded_from_its_own_priors(self) -> None:
        result = reconstruct_row(KERNEL_ROW, universe(ROWS))
        # Four priors, not five: the target itself never counts.
        self.assertEqual(result["home_admitted_prior_count"], 4)
        self.assertFalse(result["target_outcome_read"])

    def test_a_wider_universe_changes_the_answer(self) -> None:
        result = reconstruct_row(KERNEL_ROW, universe(ROWS + EXTRA, name="WIDE"))
        self.assertEqual(result["state"], RECONSTRUCTED_DIFFERENT)
        self.assertEqual(result["home_admitted_prior_count"], 5)

    def test_absent_target_is_reported_not_guessed(self) -> None:
        result = reconstruct_row(KERNEL_ROW, universe(ROWS[:-1], name="NARROW"))
        self.assertEqual(result["state"], TARGET_GAME_ABSENT)

    def test_ties_count_as_played_and_leave_win_rate_alone(self) -> None:
        result = reconstruct_row(KERNEL_ROW, universe(ROWS))
        self.assertEqual(result["state"], RECONSTRUCTED_EXACT)

    def test_same_instant_policy_is_declared_and_changes_the_count(self) -> None:
        simultaneous = ROWS + [game(7, 28, 10, 80, 3, 0)]
        strict = universe(simultaneous, name="STRICT")
        loose = build_universe(
            "LOOSE",
            observations_from_rows(simultaneous, "fixture.jsonl"),
            same_instant_policy="INCLUDE_EQUAL_INSTANT",
        )
        self.assertEqual(
            reconstruct_row(KERNEL_ROW, strict)["home_admitted_prior_count"], 4
        )
        self.assertEqual(
            reconstruct_row(KERNEL_ROW, loose)["home_admitted_prior_count"], 5
        )

    def test_unscored_and_incomplete_contests_are_excluded_with_a_reason(self) -> None:
        polluted = ROWS + [game(8, 3, 10, 90, 0, 0, completed=False)]
        built = universe(polluted, name="EXCL")
        self.assertEqual(built.rejected.get("NOT_COMPLETED"), 1)
        self.assertEqual(
            reconstruct_row(KERNEL_ROW, built)["home_admitted_prior_count"], 4
        )

    def test_a_private_team_row_is_admitted_and_deduplicated(self) -> None:
        private = [
            TeamObservation(
                team_id="SRC-002:TEAM:10",
                canonical_game_id="PRIVATE:GAME:99",
                start=BASE + timedelta(days=3),
                season=2020,
                points_for=21,
                points_against=7,
                source_file="private.parquet",
            )
        ]
        with_private = build_universe(
            "WITH_PRIVATE",
            observations_from_rows(ROWS, "fixture.jsonl"),
            extra_team_observations=private,
        )
        self.assertEqual(
            reconstruct_row(KERNEL_ROW, with_private)["home_admitted_prior_count"], 5
        )
        duplicate = build_universe(
            "DEDUPED",
            observations_from_rows(ROWS, "fixture.jsonl"),
            extra_team_observations=private + private,
        )
        self.assertEqual(
            duplicate.rejected.get(
                "PRIVATE_ROW_ALREADY_PRESENT_IN_A_PUBLIC_SOURCE"
            ),
            1,
        )

    def test_contest_identity_dedup_crosses_id_namespaces(self) -> None:
        """The same contest under two ids must not be counted twice."""

        restated = [
            TeamObservation(
                team_id="SRC-002:TEAM:10",
                canonical_game_id="OTHER-NAMESPACE:GAME:1",
                start=parse_instant(ROWS[0]["startDate"]),
                season=2020,
                points_for=30,
                points_against=10,
                source_file="private.parquet",
            )
        ]
        naive = build_universe(
            "NAIVE",
            observations_from_rows(ROWS, "fixture.jsonl"),
            extra_team_observations=restated,
        )
        careful = build_universe(
            "CAREFUL",
            observations_from_rows(ROWS, "fixture.jsonl"),
            extra_team_observations=restated,
            dedupe_by="CONTEST_IDENTITY",
        )
        self.assertEqual(
            reconstruct_row(KERNEL_ROW, naive)["home_admitted_prior_count"], 5
        )
        self.assertEqual(
            reconstruct_row(KERNEL_ROW, careful)["home_admitted_prior_count"], 4
        )


class PitAdmissionTests(unittest.TestCase):
    def test_producer_proven_without_a_receipt_is_superseded(self) -> None:
        classification = classify_pit(KERNEL_ROW)
        self.assertEqual(classification["successor_state"], PIT_SUPERSEDED)
        self.assertFalse(classification["admissible_to_a_pit_consumer"])
        self.assertEqual(classification["producer_label"], "PROVEN_PIT_TRAINING_ROW")

    def test_the_consumer_gate_refuses_a_superseded_label(self) -> None:
        self.assertFalse(admit_to_pit_consumer(classify_pit(KERNEL_ROW)))

    def test_an_unlabelled_row_is_retrospective_only(self) -> None:
        row = {**KERNEL_ROW, "authority_class": None, "row_verdict": None}
        self.assertEqual(
            classify_pit(row)["successor_state"], PIT_RETROSPECTIVE_ONLY
        )

    #: MF36-03 fixture correction. This receipt previously carried only
    #: ``prior_observation_ids``, ``source_known_at_utc`` and ``cutoff_utc``,
    #: and it admitted -- which is exactly the hole the finding names:
    #: ``classify_pit`` did ``if receipt:`` and never asked which source
    #: published the priors or what bytes were published. R37-08-AC02
    #: requires "typed source/parent identities, actual bytes, prior-game
    #: identity, publication/availability time <= cutoff". The old fixture
    #: satisfies none of the first two, so under the repaired gate it
    #: correctly does not admit. The test's intent -- a real receipt admits,
    #: and only then -- is preserved by making the fixture a real receipt;
    #: the weaker shape is kept below as a negative control so the
    #: difference is visible rather than erased.
    REAL_RECEIPT = {
        "source_id": "SRC-002",
        "prior_observation_ids": ["SRC-002:GAME:1"],
        "payload_sha256": "b" * 64,
        "published_at_utc": "2020-09-05T23:00:00Z",
        "source_known_at_utc": "2020-09-06T00:00:00Z",
        "cutoff_utc": "2020-10-03T18:00:00Z",
    }

    def test_a_real_receipt_admits_and_only_then(self) -> None:
        """MF37A02-03 fixture correction (Cycle #37 - Attempt #3).

        REAL_RECEIPT above admitted under v37.2, yet it is neither real nor sufficient: its ``payload_sha256``
        is ``"b" * 64`` with no bytes behind it, and it attests one prior (``GAME:1``) for a row whose home
        features were computed from four (``GAME:1``-``GAME:4``). MF37A02-03 is precisely that a self-asserted
        receipt for priors other than the consumed ones proved a row. It is kept as a negative below. The
        test's intent -- a real receipt admits, and only then -- now uses a receipt written with its bytes to a
        test-only fixture store, attesting exactly the four consumed priors the row declares.
        """

        import tempfile

        from aggie_analytics.cycle37.receipt_fixtures import fixture_authority, prior_receipt

        consumed = [f"SRC-002:GAME:{n}" for n in (1, 2, 3, 4)]
        row = {**KERNEL_ROW, "home_admitted_prior_game_ids": consumed, "away_admitted_prior_game_ids": []}
        with tempfile.TemporaryDirectory() as tmp:
            authority = fixture_authority(tmp, "r36-08-kernel-fixture")
            digest, stored = prior_receipt(tmp, priors=consumed,
                                           published_at=datetime(2020, 9, 26, 23, tzinfo=timezone.utc),
                                           known_at=datetime(2020, 9, 27, tzinfo=timezone.utc))
            receipts = {"SRC-002:GAME:5": {**stored, "receipt_digest": digest}}
            classification = classify_pit(row, receipts, cutoff_utc=BASE + timedelta(days=28), authority=authority)
            self.assertEqual(classification["successor_state"], PIT_PROVEN, classification.get("receipt_validation"))
            self.assertFalse(classification["counts_as_real_pit_proof"])
            self.assertTrue(admit_to_pit_consumer(classification, row=row, receipts_by_game=receipts,
                                                  cutoff_utc=BASE + timedelta(days=28), authority=authority))
            # The v37.2 fixture: one self-asserted prior of four, no bytes. Refused for the omitted priors.
            # MF37A03-03 fixture correction (Cycle #37 - Attempt #4): this call passed no target cutoff and
            # reached its intended refusal only because the gate substituted REAL_RECEIPT's own cutoff_utc --
            # the defect MF37A03-03 names. The row's decision time is now stated, so the refusal is still the
            # omitted priors; without it the gate refuses first for the missing cutoff, asserted separately.
            weaker = classify_pit(row, {"SRC-002:GAME:5": dict(self.REAL_RECEIPT)},
                                  cutoff_utc=BASE + timedelta(days=28), authority=authority)
            self.assertNotEqual(weaker["successor_state"], PIT_PROVEN)
            self.assertEqual(weaker["receipt_validation"]["code"], "REFUSED_CONSUMED_PRIOR_IS_NOT_ATTESTED")
            no_cutoff = classify_pit(row, {"SRC-002:GAME:5": dict(self.REAL_RECEIPT)}, authority=authority)
            self.assertEqual(no_cutoff["receipt_validation"]["code"], "REFUSED_TARGET_HAS_NO_CUTOFF")
            self.assertIsNone(no_cutoff["cutoff_utc"])

    def test_a_receipt_without_source_or_bytes_no_longer_admits(self) -> None:
        """The pre-MF36-03 shape: named priors and a time, no source, no bytes.

        MF37A03-03 fixture correction (Cycle #37 - Attempt #4): the row states no cutoff, and the refusal read
        "source_id" only because the receipt's own cutoff_utc was substituted for the target's. The target's
        decision time is now passed, so the intended refusal (no source, no bytes) is what is tested.
        """

        receipts = {
            "SRC-002:GAME:5": {
                "prior_observation_ids": ["SRC-002:GAME:1"],
                "source_known_at_utc": "2020-09-06T00:00:00Z",
                "cutoff_utc": "2020-10-03T18:00:00Z",
            }
        }
        classification = classify_pit(KERNEL_ROW, receipts, cutoff_utc=BASE + timedelta(days=28))
        self.assertNotEqual(classification["successor_state"], PIT_PROVEN)
        self.assertFalse(admit_to_pit_consumer(classification))
        self.assertIn("source_id", classification["receipt_validation"]["detail"])

    def test_a_receipt_known_after_the_cutoff_does_not_admit(self) -> None:
        # MF37A03-03: the target's decision time is stated, so the refusal is the late known-at itself.
        late = {**self.REAL_RECEIPT, "source_known_at_utc": "2020-10-04T00:00:00Z"}
        classification = classify_pit(KERNEL_ROW, {"SRC-002:GAME:5": late}, cutoff_utc=BASE + timedelta(days=28))
        self.assertFalse(admit_to_pit_consumer(classification))
        self.assertEqual(classification["receipt_validation"]["code"],
                         "REFUSED_RECEIPT_KNOWN_AT_IS_NOT_BEFORE_THE_CUTOFF")

    def test_an_empty_receipt_does_not_admit(self) -> None:
        classification = classify_pit(KERNEL_ROW, {"SRC-002:GAME:5": {}})
        self.assertFalse(admit_to_pit_consumer(classification))


if __name__ == "__main__":
    unittest.main()
