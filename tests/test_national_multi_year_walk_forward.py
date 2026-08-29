"""Fail-closed and tamper coverage for the 2018-2023 national walk-forward."""

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
        "the national walk-forward tests require the optional modeling dependencies"
    ) from exc

from aggie_analytics.modeling.national_multi_year_walk_forward import (  # noqa: E402
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    PIT_ELIGIBLE_LABEL,
    PROXY_LABEL,
    WalkForwardViolation,
    build_season_folds,
    candidate_authority,
    candidate_features,
    fold_transforms,
    gate_identity_of,
    load_candidates,
    load_contract,
    stability_report,
    validate_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR_RELATIVE = "configs/national_expectation_baselines_and_peers_contract.json"


def contract() -> dict[str, Any]:
    return copy.deepcopy(load_contract(REPO_ROOT))


def matrix_rows(seasons: dict[int, int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for season, count in sorted(seasons.items()):
        for index in range(count):
            rows.append(
                {
                    "canonical_game_id": f"G-{season}-{index}",
                    "canonical_team_id": f"T-{index % 4}",
                    "season": season,
                }
            )
    return rows


class CandidatePreservationTests(unittest.TestCase):
    def test_the_cycle_twenty_candidate_list_loads_verbatim(self) -> None:
        candidates, digest = load_candidates(REPO_ROOT, contract())
        self.assertEqual(len(candidates), 5)
        self.assertEqual(len(digest), 64)

    def test_a_drifted_candidate_list_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for relative in (CONTRACT_RELATIVE, PREDECESSOR_RELATIVE):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((REPO_ROOT / relative).read_bytes())
            path = root / PREDECESSOR_RELATIVE
            body = json.loads(path.read_text("utf-8-sig"))
            body["candidates"] = body["candidates"][:3]
            path.write_text(json.dumps(body), "utf-8")
            with self.assertRaises(WalkForwardViolation):
                load_candidates(root, contract())

    def test_a_missing_candidate_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(WalkForwardViolation):
                load_candidates(Path(raw), contract())


class AuthorityLabelTests(unittest.TestCase):
    def test_a_prior_only_scope_is_point_in_time_eligible(self) -> None:
        candidate = {
            "candidate_id": "c",
            "feature_scope": "PRIOR_OUTCOME_DOMAIN_AND_SITE",
        }
        self.assertEqual(candidate_authority(candidate), PIT_ELIGIBLE_LABEL)

    def test_a_scope_touching_rankings_or_venues_is_proxy_only(self) -> None:
        candidate = {"candidate_id": "c", "feature_scope": "ALL_ADMITTED_FEATURES"}
        self.assertEqual(candidate_authority(candidate), PROXY_LABEL)
        features = candidate_features(candidate)
        self.assertTrue(any(f.startswith("ap_poll") for f in features))
        self.assertTrue(any(f.startswith("venue_") for f in features))

    def test_an_unknown_scope_fails_closed(self) -> None:
        with self.assertRaises(WalkForwardViolation):
            candidate_authority({"candidate_id": "c", "feature_scope": "INVENTED"})


class FoldTests(unittest.TestCase):
    def test_each_fold_trains_only_on_strictly_preceding_seasons(self) -> None:
        rows = matrix_rows({season: 400 for season in range(2012, 2024)})
        folds = build_season_folds(rows, contract())
        self.assertEqual(len(folds), 6)
        for fold in folds:
            self.assertLess(fold["training_seasons"][1], fold["evaluation_season"])

    def test_a_fold_with_too_little_training_data_is_refused(self) -> None:
        rows = matrix_rows({2017: 10, **{season: 400 for season in range(2018, 2024)}})
        with self.assertRaises(WalkForwardViolation):
            build_season_folds(rows, contract())

    def test_a_missing_evaluation_season_is_refused(self) -> None:
        rows = matrix_rows({season: 400 for season in range(2012, 2023)})
        with self.assertRaises(WalkForwardViolation):
            build_season_folds(rows, contract())

    def test_a_forbidden_season_can_never_be_evaluated(self) -> None:
        body = contract()
        body["evaluation"]["evaluation_seasons"] = [2024]
        rows = matrix_rows({season: 400 for season in range(2012, 2025)})
        with self.assertRaises(WalkForwardViolation):
            build_season_folds(rows, body)

    def test_transforms_are_fitted_only_on_the_rows_they_are_given(self) -> None:
        low = fold_transforms([{"prior_win_rate": 0.0}, {"prior_win_rate": 1.0}])
        high = fold_transforms([{"prior_win_rate": 0.4}, {"prior_win_rate": 0.6}])
        self.assertEqual(low["prior_win_rate"]["mean"], 0.5)
        self.assertEqual(high["prior_win_rate"]["mean"], 0.5)
        self.assertNotEqual(low["prior_win_rate"]["stdev"], high["prior_win_rate"]["stdev"])

    def test_a_feature_with_one_observation_gets_no_scale(self) -> None:
        transforms = fold_transforms([{"prior_win_rate": 0.4}])
        self.assertIsNone(transforms["prior_win_rate"]["stdev"])
        self.assertIsNone(transforms["prior_win_rate"]["mean"])


class StabilityTests(unittest.TestCase):
    def test_a_single_leader_across_seasons_reports_stable(self) -> None:
        summaries = [
            {
                "aggregate": {"brier": 0.2},
                "candidate_id": "a",
                "per_season": [{"evaluation_season": s, "brier": 0.2} for s in (2018, 2019)],
            },
            {
                "aggregate": {"brier": 0.3},
                "candidate_id": "b",
                "per_season": [{"evaluation_season": s, "brier": 0.3} for s in (2018, 2019)],
            },
        ]
        report = stability_report(summaries)
        self.assertTrue(report["ordering_is_stable_across_every_season"])
        self.assertEqual(report["aggregate_brier_ranking"][0], "a")

    def test_a_changing_leader_reports_unstable(self) -> None:
        summaries = [
            {
                "aggregate": {"brier": 0.2},
                "candidate_id": "a",
                "per_season": [
                    {"evaluation_season": 2018, "brier": 0.1},
                    {"evaluation_season": 2019, "brier": 0.4},
                ],
            },
            {
                "aggregate": {"brier": 0.3},
                "candidate_id": "b",
                "per_season": [
                    {"evaluation_season": 2018, "brier": 0.4},
                    {"evaluation_season": 2019, "brier": 0.1},
                ],
            },
        ]
        self.assertFalse(stability_report(summaries)["ordering_is_stable_across_every_season"])


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
            with self.assertRaises(WalkForwardViolation):
                validate_artifact(root)

    def test_the_committed_gate_validates(self) -> None:
        gate = self._gate()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, gate)
            self.assertEqual(validate_artifact(root)["gate_identity"], gate["gate_identity"])

    def test_forging_the_gate_identity_is_caught(self) -> None:
        self._reject(lambda gate: gate.update(gate_identity="f" * 64))

    def test_swapping_in_a_different_candidate_set_hash_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["candidate_set_sha256"] = "a" * 64
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_dropping_a_negative_candidate_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["candidate_metrics"] = [
                row for row in gate["candidate_metrics"] if row["candidate_id"] != "national_base_rate"
            ]
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_smuggling_a_sealed_season_into_the_evaluation_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["evaluation_seasons"] = sorted(gate["evaluation_seasons"] + [2024])
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_a_fold_trained_on_its_own_season_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["folds"][0]["training_seasons"][1] = gate["folds"][0]["evaluation_season"]
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_relabelling_a_proxy_candidate_as_authorized_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            for row in gate["candidate_metrics"]:
                row["authority"] = "FULLY_AUTHORIZED"
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_claiming_a_champion_promotion_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["authority"]["champion_or_production_promotion"] = True
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_opening_the_protected_lane_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["protected_lane"] = "OPEN"
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_a_triggered_leakage_check_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["leakage_checks"]["transforms_reused_across_folds"] = True
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_dropping_a_season_from_a_candidate_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["candidate_metrics"][0]["seasons_evaluated"] = 2
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_claiming_separation_the_interval_does_not_support_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["known_at_authority_separation"]["the_leader_is_separably_better"] = True
            gate["known_at_authority_separation"]["leading_candidate_authority"] = PROXY_LABEL
            gate["known_at_authority_separation"]["paired_bootstrap"]["percentile_97_5"] = 0.02
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_a_missing_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for relative in (CONTRACT_RELATIVE, PREDECESSOR_RELATIVE):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((REPO_ROOT / relative).read_bytes())
            with self.assertRaises(WalkForwardViolation):
                validate_artifact(root)


class CommittedArtifactTests(unittest.TestCase):
    def test_the_committed_walk_forward_covers_every_declared_season(self) -> None:
        summary = validate_artifact(REPO_ROOT)
        self.assertEqual(summary["evaluation_seasons"], [2018, 2019, 2020, 2021, 2022, 2023])

    def test_the_committed_walk_forward_promotes_nothing(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        self.assertFalse(gate["authority"]["champion_or_production_promotion"])
        self.assertEqual(gate["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertFalse(gate["scientific_nonclaims"]["champion_or_production_selection"])

    def test_every_negative_candidate_is_preserved(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        reported = {row["candidate_id"] for row in gate["candidate_metrics"]}
        self.assertIn("national_base_rate", reported)
        self.assertEqual(len(reported), 5)

    def test_candidates_touching_blocked_domains_are_labelled_proxy_only(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        self.assertEqual(
            sorted(gate["candidates_requiring_a_chronology_proxy_label"]),
            ["national_logistic_l2", "national_margin_ridge"],
        )


if __name__ == "__main__":
    unittest.main()
