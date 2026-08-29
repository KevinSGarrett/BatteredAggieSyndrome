"""Fail-closed and tamper coverage for the predeclared residual stability test."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

try:
    import numpy  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by core-only CI
    raise unittest.SkipTest(
        "the residual stability tests require the optional modeling dependencies"
    ) from exc

from aggie_analytics.modeling.peer_and_tamu_residual_stability import (  # noqa: E402
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    ResidualStabilityViolation,
    _sign,
    gate_identity_of,
    group_residuals,
    jaccard,
    leave_one_season_out,
    load_contract,
    load_peer_rule,
    peer_membership_stability,
    run_predeclared_tests,
    summarize_groups,
    validate_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR_RELATIVE = "configs/national_expectation_baselines_and_peers_contract.json"
SEASONS = (2018, 2019, 2020, 2021, 2022, 2023)


def contract() -> dict[str, Any]:
    return copy.deepcopy(load_contract(REPO_ROOT))


def prediction(season: int, index: int, team: str, target: float, predicted: float) -> dict:
    return {
        "candidate_id": "prior_only",
        "canonical_game_id": f"G-{season}-{index}",
        "canonical_team_id": team,
        "evaluation_season": season,
        "predicted_win_probability": predicted,
        "target": target,
    }


class ContractTests(unittest.TestCase):
    def test_the_contract_declares_predeclaration(self) -> None:
        body = contract()
        self.assertTrue(
            body["predeclaration"]["declared_before_reading_any_2018_2023_residual"]
        )
        self.assertEqual(len(body["predeclared_tests"]), 7)

    def test_a_contract_without_predeclaration_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / CONTRACT_RELATIVE
            target.parent.mkdir(parents=True, exist_ok=True)
            body = contract()
            body["predeclaration"]["declared_before_reading_any_2018_2023_residual"] = False
            target.write_text(json.dumps(body), "utf-8")
            with self.assertRaises(ResidualStabilityViolation):
                load_contract(root)

    def test_every_failure_verdict_is_declared_in_the_verdict_rules(self) -> None:
        body = contract()
        for test in body["predeclared_tests"]:
            self.assertIn(test["failure_verdict"], body["verdict_rules"])
        for verdict in body["verdict_rules"]:
            self.assertIn(verdict, body["verdict_precedence"])

    def test_the_preserved_peer_rule_is_not_reputation_seeded(self) -> None:
        rule, digest = load_peer_rule(REPO_ROOT, contract())
        self.assertFalse(rule["seeded_from_famous_programs"])
        self.assertEqual(len(digest), 64)


class MembershipTests(unittest.TestCase):
    def test_identical_cohorts_are_perfectly_similar(self) -> None:
        self.assertEqual(jaccard({"a", "b"}, {"a", "b"}), 1.0)

    def test_disjoint_cohorts_are_maximally_dissimilar(self) -> None:
        self.assertEqual(jaccard({"a"}, {"b"}), 0.0)

    def test_membership_churn_lowers_the_mean_similarity(self) -> None:
        stable = peer_membership_stability(
            [{"members": [{"canonical_team_id": t} for t in "abcd"]} for _ in range(3)]
        )
        churning = peer_membership_stability(
            [
                {"members": [{"canonical_team_id": t} for t in "abcd"]},
                {"members": [{"canonical_team_id": t} for t in "cdef"]},
                {"members": [{"canonical_team_id": t} for t in "efgh"]},
            ]
        )
        self.assertEqual(stable["mean_pairwise_jaccard"], 1.0)
        self.assertLess(churning["mean_pairwise_jaccard"], 0.5)
        self.assertEqual(churning["members_present_in_every_window"], 0)


class ResidualTests(unittest.TestCase):
    def test_the_residual_is_observed_minus_predicted(self) -> None:
        groups = group_residuals(
            predictions=[prediction(2018, 0, "SRC-002:TEAM:245", 1.0, 0.4)],
            contract=contract(),
            peers_by_season={2018: set()},
        )
        self.assertAlmostEqual(groups["TEXAS_AM"][0]["residual"], 0.6)
        self.assertAlmostEqual(groups["NATIONAL"][0]["residual"], 0.6)

    def test_texas_am_is_never_placed_in_its_own_peer_cohort(self) -> None:
        groups = group_residuals(
            predictions=[prediction(2018, 0, "SRC-002:TEAM:245", 1.0, 0.4)],
            contract=contract(),
            peers_by_season={2018: {"SRC-002:TEAM:999"}},
        )
        self.assertEqual(groups["PEER_COHORT"], [])

    def test_a_missing_reference_candidate_fails_closed(self) -> None:
        rows = [{**prediction(2018, 0, "T", 1.0, 0.4), "candidate_id": "something_else"}]
        with self.assertRaises(ResidualStabilityViolation):
            group_residuals(predictions=rows, contract=contract(), peers_by_season={})

    def test_leave_one_season_out_exposes_a_single_season_driver(self) -> None:
        records = [
            {"canonical_game_id": "G", "residual": -0.1, "season": season}
            for season in (2018, 2019, 2021, 2022, 2023)
        ] + [{"canonical_game_id": "H", "residual": 5.0, "season": 2020}]
        refits = {row["season_removed"]: row["sign"] for row in leave_one_season_out(records, SEASONS)}
        self.assertEqual(refits[2020], "NEGATIVE")
        self.assertEqual(refits[2018], "POSITIVE")

    def test_sign_of_zero_is_reported_as_zero(self) -> None:
        self.assertEqual(_sign(0.0), "ZERO")
        self.assertEqual(_sign(None), "UNDEFINED")


class VerdictTests(unittest.TestCase):
    def _run(self, predictions, peers_by_season, membership_jaccard=1.0):
        body = contract()
        body["evaluation"]["bootstrap"]["resamples"] = 200
        groups = group_residuals(
            predictions=predictions, contract=body, peers_by_season=peers_by_season
        )
        summaries = summarize_groups(groups, body)
        membership = {"mean_pairwise_jaccard": membership_jaccard, "cohorts_compared": 6}
        return run_predeclared_tests(
            summaries=summaries, groups=groups, membership=membership, contract=body
        )

    def _population(self, tamu_residual_by_season: dict[int, float]):
        rows = []
        for season in SEASONS:
            for index in range(40):
                rows.append(prediction(season, index, f"T-{index % 8}", 1.0, 0.5))
            for index in range(12):
                shift = tamu_residual_by_season[season]
                rows.append(
                    prediction(
                        season,
                        100 + index,
                        "SRC-002:TEAM:245",
                        0.5 + shift,
                        0.5,
                    )
                )
        return rows

    def test_too_few_texas_am_rows_yields_insufficient_evidence(self) -> None:
        rows = [prediction(season, 0, "SRC-002:TEAM:245", 1.0, 0.5) for season in SEASONS]
        rows += [prediction(season, 1, "T-1", 1.0, 0.5) for season in SEASONS]
        _, verdict, _ = self._run(rows, {season: {"T-1"} for season in SEASONS})
        self.assertEqual(verdict, "INSUFFICIENT_EVIDENCE")

    def test_a_flipping_sign_yields_the_unstable_sign_verdict(self) -> None:
        flipping = {2018: 0.3, 2019: 0.3, 2020: 0.3, 2021: -0.3, 2022: -0.3, 2023: -0.3}
        _, verdict, _ = self._run(
            self._population(flipping), {season: {"T-1"} for season in SEASONS}
        )
        self.assertEqual(verdict, "UNSTABLE_SIGN_FLIPS_ACROSS_SEASONS")

    def test_churning_peer_membership_takes_verdict_precedence(self) -> None:
        flipping = {2018: 0.3, 2019: 0.3, 2020: 0.3, 2021: -0.3, 2022: -0.3, 2023: -0.3}
        _, verdict, _ = self._run(
            self._population(flipping),
            {season: {"T-1"} for season in SEASONS},
            membership_jaccard=0.1,
        )
        self.assertEqual(verdict, "UNSTABLE_PEER_MEMBERSHIP_CHURNS")

    def test_a_consistent_but_tiny_residual_is_not_declared_stable(self) -> None:
        tiny = {season: 0.0 for season in SEASONS}
        _, verdict, _ = self._run(
            self._population(tiny), {season: {"T-1"} for season in SEASONS}
        )
        self.assertIn(verdict, {"NULL_NOT_SEPARABLE_FROM_ZERO", "NULL_INDISTINGUISHABLE_FROM_PEERS"})


class TamperTests(unittest.TestCase):
    def _gate(self) -> dict[str, Any]:
        return json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))

    def _write(self, root: Path, gate: dict[str, Any]) -> None:
        for relative in (CONTRACT_RELATIVE, PREDECESSOR_RELATIVE):
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
            with self.assertRaises(ResidualStabilityViolation):
                validate_artifact(root)

    def test_the_committed_gate_validates(self) -> None:
        gate = self._gate()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, gate)
            self.assertEqual(validate_artifact(root)["verdict"], gate["verdict"])

    def test_forging_the_gate_identity_is_caught(self) -> None:
        self._reject(lambda gate: gate.update(gate_identity="f" * 64))

    def test_upgrading_a_null_verdict_to_a_stable_claim_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["verdict"] = "STABLE_PERSISTENT_RESIDUAL_DETECTED"
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_flipping_a_failed_predeclared_test_to_passed_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            for row in gate["predeclared_test_results"]:
                row["passed"] = True
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_dropping_a_predeclared_test_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["predeclared_test_results"] = gate["predeclared_test_results"][:4]
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_substituting_the_peer_cohort_rule_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["peer_cohort_rule_sha256"] = "a" * 64
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_asserting_a_bas_or_aggie_excess_claim_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["scientific_nonclaims"]["bas_or_aggie_excess"] = True
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_asserting_a_causal_effect_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["authority"]["causal_effect_established"] = True
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_admitting_the_model_was_tuned_on_texas_am_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["authority"]["national_model_tuned_on_texas_am"] = True
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_opening_the_protected_lane_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["protected_lane"] = "OPEN"
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_smuggling_a_sealed_season_into_the_evaluation_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["evaluation_seasons"] = sorted(gate["evaluation_seasons"] + [2024])
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_reporting_an_undeclared_verdict_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["verdict"] = "TOTALLY_INVENTED_VERDICT"
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_a_missing_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for relative in (CONTRACT_RELATIVE, PREDECESSOR_RELATIVE):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((REPO_ROOT / relative).read_bytes())
            with self.assertRaises(ResidualStabilityViolation):
                validate_artifact(root)


class CommittedArtifactTests(unittest.TestCase):
    def test_the_committed_verdict_is_declared_and_consistent(self) -> None:
        summary = validate_artifact(REPO_ROOT)
        body = contract()
        self.assertIn(summary["verdict"], body["verdict_rules"])

    def test_no_forbidden_claim_is_asserted(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        for value in gate["scientific_nonclaims"].values():
            self.assertFalse(value)
        self.assertEqual(gate["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")

    def test_the_reference_candidate_stays_inside_authorized_domains(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        self.assertEqual(gate["reference_candidate"], "prior_only")

    def test_all_three_comparison_groups_are_reported(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        self.assertEqual(
            sorted(row["group"] for row in gate["residual_summaries"]),
            ["NATIONAL", "PEER_COHORT", "TEXAS_AM"],
        )


if __name__ == "__main__":
    unittest.main()
