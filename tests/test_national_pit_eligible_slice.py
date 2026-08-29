"""Forged-identity and fail-closed coverage for the first national PIT-eligible slice."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from aggie_analytics.data.national_pit_eligible_slice import (
    AUTHORITY_GATE_RELATIVE,
    CONTRACT_RELATIVE,
    ELIGIBLE,
    ELIGIBLE_NO_PRIOR,
    GATE_RELATIVE,
    REJECTED_NO_OUTCOME,
    REJECTED_NO_START,
    REJECTED_SEALED,
    PitSliceViolation,
    build_gate,
    build_rows,
    gate_identity_of,
    load_authority,
    load_contract,
    measure_leakage_exposure,
    payload_lines,
    require_authority,
    summarize,
    validate_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def contract() -> dict[str, Any]:
    return copy.deepcopy(load_contract(REPO_ROOT))


def authority() -> dict[str, Any]:
    return copy.deepcopy(load_authority(REPO_ROOT))


def policy() -> dict[str, Any]:
    return authority()["conservative_bound_policy"]


def observation(game: str, team: str, season: int, week: int = 1) -> dict[str, Any]:
    return {
        "canonical_game_id": game,
        "canonical_team_id": team,
        "is_home": True,
        "is_neutral_site": False,
        "opponent_canonical_team_id": "TEAM-OTHER",
        "season": season,
        "week": week,
    }


def outcome(game: str, team: str, season: int, *, win: bool, pf: int, pa: int) -> dict[str, Any]:
    return {
        "canonical_game_id": game,
        "canonical_team_id": team,
        "label_tie": False,
        "label_win": win,
        "margin": pf - pa,
        "points_against": pa,
        "points_for": pf,
        "season": season,
    }


class ClockedSequenceTests(unittest.TestCase):
    """A team with published start instants, one week apart."""

    def setUp(self) -> None:
        self.starts = {
            "G1": "2010-09-04T18:00:00Z",
            "G2": "2010-09-11T18:00:00Z",
            "G3": "2010-09-18T18:00:00Z",
        }
        self.observations = [
            observation("G1", "T", 2010, 1),
            observation("G2", "T", 2010, 2),
            observation("G3", "T", 2010, 3),
        ]
        self.outcomes = [
            outcome("G1", "T", 2010, win=True, pf=30, pa=10),
            outcome("G2", "T", 2010, win=False, pf=14, pa=21),
            outcome("G3", "T", 2010, win=True, pf=28, pa=7),
        ]
        self.rows = {
            row["canonical_game_id"]: row
            for row in build_rows(
                self.observations, self.outcomes, self.starts, contract(), policy()
            )
        }

    def test_the_first_contest_has_no_prior_information(self) -> None:
        first = self.rows["G1"]
        self.assertEqual(first["row_verdict"], ELIGIBLE_NO_PRIOR)
        self.assertEqual(first["pit_prior_games_played"], 0)
        self.assertIsNone(first["pit_prior_win_rate"])

    def test_a_contest_never_counts_itself_as_a_prior(self) -> None:
        self.assertEqual(self.rows["G2"]["pit_prior_games_played"], 1)
        self.assertEqual(self.rows["G3"]["pit_prior_games_played"], 2)

    def test_prior_aggregates_use_only_completed_earlier_contests(self) -> None:
        third = self.rows["G3"]
        self.assertEqual(third["pit_prior_win_rate"], 0.5)
        self.assertEqual(third["pit_prior_points_for_mean"], 22.0)
        self.assertEqual(third["pit_prior_points_against_mean"], 15.5)
        self.assertEqual(third["pit_prior_margin_mean"], 6.5)

    def test_season_to_date_tracks_the_current_season_only(self) -> None:
        self.assertEqual(self.rows["G3"]["pit_season_to_date_games"], 2)
        self.assertEqual(self.rows["G3"]["pit_season_to_date_win_rate"], 0.5)


class BoundEdgeTests(unittest.TestCase):
    def test_a_contest_twelve_hours_earlier_is_admitted_but_eleven_is_not(self) -> None:
        for offset, expected in (("06:00:00Z", 1), ("05:00:00Z", 0)):
            starts = {"P": "2010-09-04T18:00:00Z", "T": f"2010-09-05T{offset}"}
            rows = {
                row["canonical_game_id"]: row
                for row in build_rows(
                    [observation("P", "T", 2010), observation("T", "T", 2010, 2)],
                    [
                        outcome("P", "T", 2010, win=True, pf=20, pa=0),
                        outcome("T", "T", 2010, win=True, pf=20, pa=0),
                    ],
                    starts,
                    contract(),
                    policy(),
                )
            }
            self.assertEqual(rows["T"]["pit_prior_games_played"], expected, offset)

    def test_date_only_records_require_three_days_of_separation(self) -> None:
        for day, expected in ((6, 0), (7, 1)):
            starts = {"P": "1970-09-04T00:00:00Z", "T": f"1970-09-0{day}T00:00:00Z"}
            rows = {
                row["canonical_game_id"]: row
                for row in build_rows(
                    [observation("P", "T", 1970), observation("T", "T", 1970, 2)],
                    [
                        outcome("P", "T", 1970, win=True, pf=20, pa=0),
                        outcome("T", "T", 1970, win=True, pf=20, pa=0),
                    ],
                    starts,
                    contract(),
                    policy(),
                )
            }
            self.assertEqual(rows["T"]["pit_prior_games_played"], expected, f"day {day}")

    def test_a_row_without_start_evidence_is_rejected(self) -> None:
        rows = build_rows(
            [observation("G1", "T", 2010)],
            [outcome("G1", "T", 2010, win=True, pf=1, pa=0)],
            {"G1": ""},
            contract(),
            policy(),
        )
        self.assertEqual(rows[0]["row_verdict"], REJECTED_NO_START)

    def test_a_row_without_an_outcome_reference_is_rejected(self) -> None:
        rows = build_rows(
            [observation("G1", "T", 2010)],
            [],
            {"G1": "2010-09-04T18:00:00Z"},
            contract(),
            policy(),
        )
        self.assertEqual(rows[0]["row_verdict"], REJECTED_NO_OUTCOME)

    def test_a_sealed_season_row_is_rejected_before_anything_else(self) -> None:
        rows = build_rows(
            [observation("G1", "T", 2024)],
            [outcome("G1", "T", 2024, win=True, pf=1, pa=0)],
            {"G1": "2024-09-04T18:00:00Z"},
            contract(),
            policy(),
        )
        self.assertEqual(rows[0]["row_verdict"], REJECTED_SEALED)

    def test_a_sealed_season_contest_never_becomes_a_prior(self) -> None:
        starts = {"S": "2024-09-04T18:00:00Z", "T": "2025-09-04T18:00:00Z"}
        rows = build_rows(
            [observation("S", "T", 2024), observation("T", "T", 2025)],
            [
                outcome("S", "T", 2024, win=True, pf=40, pa=0),
                outcome("T", "T", 2025, win=True, pf=40, pa=0),
            ],
            starts,
            contract(),
            policy(),
        )
        self.assertTrue(all(row["row_verdict"] == REJECTED_SEALED for row in rows))


class FutureAppendInvarianceTests(unittest.TestCase):
    def test_appending_later_contests_cannot_change_an_earlier_row(self) -> None:
        starts = {f"G{i}": f"2010-09-{4 + 7 * i:02d}T18:00:00Z" for i in range(4)}
        observations = [observation(f"G{i}", "T", 2010, i + 1) for i in range(4)]
        outcomes = [
            outcome(f"G{i}", "T", 2010, win=i % 2 == 0, pf=20 + i, pa=10)
            for i in range(4)
        ]
        full = {
            row["canonical_game_id"]: row
            for row in build_rows(observations, outcomes, starts, contract(), policy())
        }
        partial = {
            row["canonical_game_id"]: row
            for row in build_rows(
                observations[:2], outcomes[:2], starts, contract(), policy()
            )
        }
        for game in partial:
            self.assertEqual(full[game], partial[game], game)


class LeakageMeasurementTests(unittest.TestCase):
    def test_a_bound_that_removes_priors_is_measured_not_hidden(self) -> None:
        starts = {"P": "2010-09-04T18:00:00Z", "T": "2010-09-05T05:00:00Z"}
        rows = build_rows(
            [observation("P", "T", 2010), observation("T", "T", 2010, 2)],
            [
                outcome("P", "T", 2010, win=True, pf=20, pa=0),
                outcome("T", "T", 2010, win=True, pf=20, pa=0),
            ],
            starts,
            contract(),
            policy(),
        )
        spine = [
            {"canonical_game_id": "T", "canonical_team_id": "T", "prior_games_played": 1},
            {"canonical_game_id": "P", "canonical_team_id": "T", "prior_games_played": 0},
        ]
        measured = measure_leakage_exposure(rows, spine)
        self.assertEqual(measured["total_priors_removed_by_the_bound"], 1)
        self.assertEqual(measured["rows_where_recomputation_exceeded_the_spine"], 0)

    def test_recomputing_more_priors_than_the_spine_is_reported(self) -> None:
        rows = [
            {
                "canonical_game_id": "T",
                "canonical_team_id": "T",
                "pit_prior_games_played": 5,
                "row_verdict": ELIGIBLE,
            }
        ]
        spine = [{"canonical_game_id": "T", "canonical_team_id": "T", "prior_games_played": 2}]
        measured = measure_leakage_exposure(rows, spine)
        self.assertEqual(measured["rows_where_recomputation_exceeded_the_spine"], 1)


class AuthorityGuardTests(unittest.TestCase):
    def test_a_slice_cannot_be_built_without_audited_authority(self) -> None:
        weakened = authority()
        weakened["domains_with_sufficient_authority"] = ["team_season_context"]
        with self.assertRaises(PitSliceViolation):
            require_authority(weakened, contract())

    def test_a_slice_cannot_be_built_if_an_excluded_domain_stopped_being_blocked(self) -> None:
        drifted = authority()
        drifted["domains_blocked_from_point_in_time_admission"] = ["venues"]
        with self.assertRaises(PitSliceViolation):
            require_authority(drifted, contract())

    def test_an_empty_slice_is_refused_rather_than_reported_as_success(self) -> None:
        with self.assertRaises(PitSliceViolation):
            build_gate([], [], contract(), authority(), {})


class TamperTests(unittest.TestCase):
    def _gate(self) -> dict[str, Any]:
        return json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))

    def _write(self, root: Path, gate: dict[str, Any]) -> None:
        for relative in (CONTRACT_RELATIVE, AUTHORITY_GATE_RELATIVE):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO_ROOT / relative).read_bytes())
        target = root / GATE_RELATIVE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(gate, indent=2, sort_keys=True), "utf-8")

    def _reject(self, mutate) -> None:
        gate = self._gate()
        mutate(gate)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, gate)
            with self.assertRaises(PitSliceViolation):
                validate_artifact(root)

    def test_the_committed_gate_validates(self) -> None:
        gate = self._gate()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, gate)
            self.assertEqual(validate_artifact(root)["gate_identity"], gate["gate_identity"])

    def test_forging_the_gate_identity_is_caught(self) -> None:
        self._reject(lambda gate: gate.update(gate_identity="f" * 64))

    def test_editing_the_population_without_restamping_is_caught(self) -> None:
        self._reject(lambda gate: gate["population"].update(eligible_team_rows=999999))

    def test_rebinding_to_a_foreign_contract_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["contract_sha256"] = "a" * 64
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_forging_the_payload_hash_alone_is_caught(self) -> None:
        self._reject(lambda gate: gate["payload"].update(sha256="b" * 64))

    def test_admitting_a_blocked_domain_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["admitted_domains"] = sorted(gate["admitted_domains"] + ["rankings"])
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_emitting_a_blocked_domain_feature_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["emitted_features"] = sorted(gate["emitted_features"] + ["ap_poll_rank"])
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_a_verdict_tally_that_does_not_reconcile_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["population"]["row_verdict_counts"][ELIGIBLE] += 7
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_smuggling_a_sealed_season_into_the_population_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["population"]["eligible_seasons"] = sorted(
                gate["population"]["eligible_seasons"] + [2024]
            )
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_claiming_more_priors_than_the_spine_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["leakage_exposure"]["rows_where_recomputation_exceeded_the_spine"] = 4
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_falsely_closing_gap_002_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["gap_verdict"]["remains_open"] = False
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_opening_the_protected_lane_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["protected_lane"] = "OPEN"
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_an_emptied_slice_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["population"]["eligible_team_rows"] = 0
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_a_missing_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for relative in (CONTRACT_RELATIVE, AUTHORITY_GATE_RELATIVE):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((REPO_ROOT / relative).read_bytes())
            with self.assertRaises(PitSliceViolation):
                validate_artifact(root)


class DeterminismTests(unittest.TestCase):
    def test_the_payload_serialization_is_stable(self) -> None:
        rows = [
            {"canonical_game_id": "G1", "b": 2, "a": 1},
            {"a": 3, "canonical_game_id": "G2", "b": 4},
        ]
        self.assertEqual(payload_lines(rows), payload_lines(rows))
        self.assertIn(b'{"a":1,"b":2,"canonical_game_id":"G1"}', payload_lines(rows))

    def test_summarize_reports_every_declared_verdict_even_when_zero(self) -> None:
        summary = summarize([{"canonical_game_id": "G", "row_verdict": REJECTED_SEALED, "season": 2024}])
        self.assertEqual(summary["row_verdict_counts"][ELIGIBLE], 0)
        self.assertEqual(summary["eligible_team_rows"], 0)


class CommittedArtifactTests(unittest.TestCase):
    def test_the_committed_slice_is_nonzero_and_valid(self) -> None:
        summary = validate_artifact(REPO_ROOT)
        self.assertEqual(summary["result"], "PASS_FIRST_NATIONAL_PIT_ELIGIBLE_SLICE")
        self.assertGreater(summary["eligible_team_rows"], 0)

    def test_the_committed_slice_excludes_every_blocked_feature(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        for feature in gate["emitted_features"]:
            self.assertFalse(feature.startswith(("ap_poll", "coaches_poll", "venue_")))

    def test_the_committed_slice_keeps_gap_002_open(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        self.assertTrue(gate["gap_verdict"]["remains_open"])
        self.assertEqual(gate["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")


if __name__ == "__main__":
    unittest.main()
