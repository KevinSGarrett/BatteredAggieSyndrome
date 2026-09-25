"""R35-06: MR34-01/MR34-02 must close in the paths the manager actually drove.

`cycle33.scoring_successor` and `cycle33.forecast_inventory` remain in
service, so closing the counterexample only in the Cycle #35 successor would
leave the demonstrated defect reachable. These tests drive the legacy entry
points directly with the manager's own fixtures, and each rejection test is
paired with the positive control that must still be admitted -- a suite that
rejected everything would pass while proving nothing.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.cycle33 import forecast_inventory as fi
from aggie_analytics.cycle33.forecast_inventory import inspect_forecast_eligibility
from aggie_analytics.cycle33.scoring_successor import score_unique_frozen_games

AS_OF = datetime(2026, 9, 20, tzinfo=timezone.utc)
KICKOFF = "2026-09-05T23:00:00+00:00"
MANAGER_REVIEW_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews")


def _write_evidence(
    root: Path, *, probability: float = 0.9, frozen_at: str
) -> str:
    payload = {
        "ncaa_contest_id": "fixture-game",
        "candidate_id": "fixture-model",
        "cohort": "fixture",
        "checkpoint": "T24",
        "probability_home": probability,
        "frozen_at_utc": frozen_at,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    (root / ("forecast_" + digest[:12] + ".json")).write_bytes(raw)
    return digest


def _game(**overrides):
    game = {
        "ncaa_contest_id": "fixture-game",
        "home_points": 30,
        "away_points": 10,
        "home_canonical_team_id": "REAL_HOME",
        "away_canonical_team_id": "REAL_AWAY",
        "status_code_display": "Final",
        "game_state": "F",
        "terminal_state": "TERMINAL_STATUS_ESTABLISHED",
        "kickoff_utc": KICKOFF,
    }
    game.update(overrides)
    return game


def _forecast(digest: str, **overrides):
    row = {
        "ncaa_contest_id": "fixture-game",
        "candidate_id": "fixture-model",
        "cohort": "fixture",
        "checkpoint": "T24",
        "probability_home": 0.9,
        "frozen": True,
        "forecast_row_id": "ROW-1",
        "freeze_receipt": {"receipt_id": "r1", "receipt_sha256": digest},
        "home_canonical_team_id": "REAL_HOME",
        "away_canonical_team_id": "REAL_AWAY",
    }
    row.update(overrides)
    return row


class LegacyScoringPathHardeningTests(unittest.TestCase):
    def test_pre_kickoff_commitment_still_scores(self) -> None:
        """Positive control: the legacy path must still do its job."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = _write_evidence(root, frozen_at="2026-09-04T12:00:00+00:00")
            out = score_unique_frozen_games(
                [_game()],
                forecasts=[_forecast(digest)],
                as_of_utc=AS_OF,
                search_roots=[root],
            )
            self.assertEqual(out["scored_candidate_checkpoint_rows"], 1)

    def test_post_kickoff_commitment_is_no_longer_scored(self) -> None:
        """The manager's exact counterexample: a freeze claimed two hours
        after kickoff, on a receipt written during the review."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = _write_evidence(root, frozen_at="2026-09-06T02:00:00+00:00")
            out = score_unique_frozen_games(
                [_game()],
                forecasts=[_forecast(digest)],
                as_of_utc=AS_OF,
                search_roots=[root],
            )
            self.assertEqual(out["scored_candidate_checkpoint_rows"], 0)
            self.assertEqual(out["excluded_unproven_freeze"], 1)

    def test_wrong_participants_are_no_longer_scored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = _write_evidence(root, frozen_at="2026-09-04T12:00:00+00:00")
            out = score_unique_frozen_games(
                [_game()],
                forecasts=[
                    _forecast(
                        digest,
                        home_canonical_team_id="OTHER_HOME",
                        away_canonical_team_id="OTHER_AWAY",
                    )
                ],
                as_of_utc=AS_OF,
                search_roots=[root],
            )
            self.assertEqual(out["scored_candidate_checkpoint_rows"], 0)
            self.assertEqual(out["excluded_participant_mismatch"], 1)

    def test_reversed_participants_are_a_different_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = _write_evidence(root, frozen_at="2026-09-04T12:00:00+00:00")
            out = score_unique_frozen_games(
                [_game()],
                forecasts=[
                    _forecast(
                        digest,
                        home_canonical_team_id="REAL_AWAY",
                        away_canonical_team_id="REAL_HOME",
                    )
                ],
                as_of_utc=AS_OF,
                search_roots=[root],
            )
            self.assertEqual(out["scored_candidate_checkpoint_rows"], 0)
            self.assertEqual(out["excluded_participant_mismatch"], 1)

    def test_unbound_participants_are_excluded_and_counted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = _write_evidence(root, frozen_at="2026-09-04T12:00:00+00:00")
            forecast = _forecast(digest)
            forecast.pop("home_canonical_team_id")
            out = score_unique_frozen_games(
                [_game()],
                forecasts=[forecast],
                as_of_utc=AS_OF,
                search_roots=[root],
            )
            self.assertEqual(out["scored_candidate_checkpoint_rows"], 0)
            self.assertEqual(out["excluded_unbound_participants"], 1)

    def test_contest_without_kickoff_cannot_establish_timeliness(self) -> None:
        """Honest limit: with no kickoff authority on the contest, the legacy
        predicate cannot judge lateness, so the row scores and the result
        says the check was only applied where kickoff was available. The
        bound decision belongs to the Cycle #35 admission contract."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = _write_evidence(root, frozen_at="2026-09-06T02:00:00+00:00")
            game = _game()
            game.pop("kickoff_utc")
            out = score_unique_frozen_games(
                [game],
                forecasts=[_forecast(digest)],
                as_of_utc=AS_OF,
                search_roots=[root],
            )
            self.assertEqual(out["scored_candidate_checkpoint_rows"], 1)
            self.assertTrue(out["commitment_checked_against_kickoff_when_available"])


class InventoryScopeTests(unittest.TestCase):
    def test_manager_review_roots_are_not_forecast_authority(self) -> None:
        self.assertNotIn(MANAGER_REVIEW_ROOT, fi.SEARCH_ROOTS)
        self.assertIn(MANAGER_REVIEW_ROOT, fi.EXCLUDED_NON_AUTHORITY_ROOTS)

    @staticmethod
    def _packet(tmp: str, name: str, **overrides):
        payload = {
            "contest_id": "c1",
            "frozen": True,
            "issued_at_utc": "2026-09-04T00:00:00+00:00",
            "known_at_utc": "2026-09-04T00:00:00+00:00",
            "probability_home": 0.7,
        }
        payload.update(overrides)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload["receipt_sha256"] = hashlib.sha256(raw).hexdigest()
        path = Path(tmp) / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_structurally_valid_packet_is_eligible_but_scope_limited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            verdict = inspect_forecast_eligibility(
                self._packet(tmp, "ok.json"), as_of_utc=AS_OF
            )
            self.assertEqual(verdict["eligibility_verdict"], "ELIGIBLE")
            self.assertEqual(
                verdict["eligibility_scope"], "STRUCTURAL_WELL_FORMEDNESS_ONLY"
            )
            self.assertTrue(verdict["self_hash_is_not_issuer_authority"])
            self.assertTrue(verdict["self_hash_is_not_commitment_evidence"])
            self.assertEqual(
                verdict["admission_authority"],
                "aggie_analytics.cycle35.forecast_admission.admit",
            )

    def test_boolean_probability_packet_is_ineligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            verdict = inspect_forecast_eligibility(
                self._packet(tmp, "bool.json", probability_home=True), as_of_utc=AS_OF
            )
            self.assertEqual(verdict["eligibility_verdict"], "INELIGIBLE")
            self.assertIn(
                "MISSING_ACTUAL_FORECAST_CONTENT", verdict["failed_predicates"]
            )

    def test_future_dated_packet_is_ineligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            verdict = inspect_forecast_eligibility(
                self._packet(
                    tmp,
                    "future.json",
                    issued_at_utc="2099-01-01T00:00:00+00:00",
                    known_at_utc="2099-01-01T00:00:00+00:00",
                ),
                as_of_utc=AS_OF,
            )
            self.assertEqual(verdict["eligibility_verdict"], "INELIGIBLE")
            self.assertIn(
                "ISSUED_OR_SNAPSHOT_UTC_IN_THE_FUTURE", verdict["failed_predicates"]
            )
            self.assertIn("KNOWN_AT_UTC_IN_THE_FUTURE", verdict["failed_predicates"])

    def test_integer_zero_and_one_remain_valid_probabilities(self) -> None:
        """Guard against over-correcting: rejecting `bool` must not reject
        an honest integer 0 or 1."""
        with tempfile.TemporaryDirectory() as tmp:
            for value in (0, 1):
                verdict = inspect_forecast_eligibility(
                    self._packet(tmp, f"int{value}.json", probability_home=value),
                    as_of_utc=AS_OF,
                )
                self.assertEqual(
                    verdict["eligibility_verdict"], "ELIGIBLE", f"value={value}"
                )


if __name__ == "__main__":
    unittest.main()
