"""Tamper and fail-closed coverage for the historical known-at authority audit."""

from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.data.historical_known_at_authority import (
    CONSERVATIVE_BOUND,
    CONTRACT_ID,
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    OBSERVED_PUBLICATION,
    POSTGAME_ONLY,
    RETRIEVAL_ONLY,
    KnownAtAuthorityViolation,
    build_audit,
    gate_identity_of,
    load_contract,
    prior_is_guaranteed_complete,
    profile_start_evidence,
    start_evidence_kind,
    validate_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def synthetic_contract() -> dict[str, Any]:
    return copy.deepcopy(load_contract(REPO_ROOT))


def synthetic_matrix() -> dict[str, Any]:
    domains = ["team_outcome_priors", "team_season_context", "venues", "rankings"]
    return {
        "admission_matrix": [
            {"domain_id": domain, "known_at_basis": f"DECLARED_BASIS_FOR_{domain.upper()}"}
            for domain in domains
        ],
        "admitted_feature_registry": [
            {"domain_id": domain, "feature_id": f"{domain}__feature_one"} for domain in domains
        ],
        "gate_identity": "a" * 64,
    }


def synthetic_spine() -> list[dict[str, Any]]:
    return [
        {"canonical_game_id": "G-1970", "season": 1970, "start_date_utc_text": "1970-09-19T00:00:00Z"},
        {"canonical_game_id": "G-1970", "season": 1970, "start_date_utc_text": "1970-09-19T00:00:00Z"},
        {"canonical_game_id": "G-2010", "season": 2010, "start_date_utc_text": "2010-09-04T18:30:00Z"},
        {"canonical_game_id": "G-2010B", "season": 2010, "start_date_utc_text": "2010-09-11T00:00:00Z"},
    ]


def synthetic_capture(*, ap_instants: int = 3, ncaa_state: str = "CAPTURED") -> dict[str, Any]:
    return {
        "capture_identity": "b" * 64,
        "routes": [
            {
                "failure_condition": None if ncaa_state == "CAPTURED" else "HTTP_404",
                "publication_instants": [],
                "raw_bytes": 27488,
                "raw_sha256": "c" * 64,
                "retrieved_at_utc": "2026-08-29T07:23:34Z",
                "route_id": "NCAA_OFFICIAL_STATS_RANKINGS",
                "source_uri": "https://stats.ncaa.org/rankings",
                "state": ncaa_state,
            },
            {
                "publication_instants": [
                    {"pattern": "p", "raw_value": str(1787969660000 + index)}
                    for index in range(ap_instants)
                ],
                "raw_bytes": 899665,
                "raw_sha256": "d" * 64,
                "retrieved_at_utc": "2026-08-29T07:23:34Z",
                "route_id": "AP_OFFICIAL_TOP25_FOOTBALL",
                "source_uri": "https://apnews.com/hub/ap-top-25-college-football-poll",
                "state": "CAPTURED",
            },
        ],
    }


def synthetic_gate(**kwargs: Any) -> dict[str, Any]:
    return build_audit(
        synthetic_matrix(),
        profile_start_evidence(synthetic_spine()),
        synthetic_capture(**kwargs),
        synthetic_contract(),
    )


class StartEvidenceClassificationTests(unittest.TestCase):
    def test_a_midnight_sentinel_is_calendar_date_evidence_only(self) -> None:
        self.assertEqual(
            start_evidence_kind("1970-09-19T00:00:00Z"), "CALENDAR_DATE_ONLY_MIDNIGHT_SENTINEL"
        )

    def test_a_real_clock_is_a_published_start_instant(self) -> None:
        self.assertEqual(start_evidence_kind("2010-09-04T18:30:00Z"), "PUBLISHED_START_INSTANT")

    def test_unparseable_evidence_is_never_promoted_to_an_instant(self) -> None:
        for text in ("", "unknown", "not-a-date"):
            self.assertEqual(start_evidence_kind(text), "NO_PARSEABLE_START_EVIDENCE")

    def test_the_profile_counts_games_not_team_rows(self) -> None:
        profile = profile_start_evidence(synthetic_spine())
        self.assertEqual(profile["distinct_games"], 3)
        self.assertEqual(profile["seasons_with_calendar_date_evidence_only"], [1970])
        self.assertEqual(profile["seasons_with_a_published_start_instant"], [2010])


class ConservativeBoundTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = synthetic_contract()["conservative_bound_policy"]

    def test_a_date_only_prior_within_two_days_is_not_guaranteed_complete(self) -> None:
        for separation in (0, 1, 2):
            target = (datetime(1970, 9, 19, tzinfo=timezone.utc) + timedelta(days=separation)).strftime(
                "%Y-%m-%dT00:00:00Z"
            )
            self.assertFalse(
                prior_is_guaranteed_complete("1970-09-19T00:00:00Z", target, self.policy),
                f"a {separation}-day separation must not be admitted",
            )

    def test_a_date_only_prior_three_days_earlier_is_guaranteed_complete(self) -> None:
        self.assertTrue(
            prior_is_guaranteed_complete(
                "1970-09-19T00:00:00Z", "1970-09-22T00:00:00Z", self.policy
            )
        )

    def test_two_clocked_contests_use_the_tighter_twelve_hour_rule(self) -> None:
        self.assertTrue(
            prior_is_guaranteed_complete(
                "2010-09-04T18:30:00Z", "2010-09-05T06:30:00Z", self.policy
            )
        )
        self.assertFalse(
            prior_is_guaranteed_complete(
                "2010-09-04T18:30:00Z", "2010-09-05T06:29:00Z", self.policy
            )
        )

    def test_a_same_day_clocked_prior_is_not_guaranteed_complete(self) -> None:
        self.assertFalse(
            prior_is_guaranteed_complete(
                "2010-09-04T18:30:00Z", "2010-09-04T19:00:00Z", self.policy
            )
        )

    def test_missing_evidence_never_admits_a_prior(self) -> None:
        self.assertFalse(prior_is_guaranteed_complete("", "2010-09-05T06:30:00Z", self.policy))
        self.assertFalse(prior_is_guaranteed_complete("2010-09-04T18:30:00Z", "", self.policy))

    def test_the_bound_is_asymmetric_and_never_admits_a_later_prior(self) -> None:
        self.assertFalse(
            prior_is_guaranteed_complete(
                "1970-09-22T00:00:00Z", "1970-09-19T00:00:00Z", self.policy
            )
        )


class AuthorityClassificationTests(unittest.TestCase):
    def test_the_audit_covers_exactly_the_declared_domains(self) -> None:
        gate = synthetic_gate()
        self.assertEqual(
            sorted(row["domain_id"] for row in gate["domain_authority"]),
            sorted(synthetic_contract()["audited_domains"]),
        )

    def test_rankings_stay_retrieval_only_when_no_route_bears_a_historical_instant(self) -> None:
        gate = synthetic_gate()
        rankings = next(r for r in gate["domain_authority"] if r["domain_id"] == "rankings")
        self.assertEqual(rankings["authority_class"], RETRIEVAL_ONLY)
        self.assertFalse(rankings["authority_is_sufficient_for_point_in_time_admission"])

    def test_venues_stay_blocked_because_mutable_attributes_lack_authority(self) -> None:
        gate = synthetic_gate()
        venues = next(r for r in gate["domain_authority"] if r["domain_id"] == "venues")
        self.assertEqual(venues["authority_class"], RETRIEVAL_ONLY)
        self.assertFalse(venues["authority_is_sufficient_for_point_in_time_admission"])

    def test_outcome_labels_are_postgame_only_evidence(self) -> None:
        gate = synthetic_gate()
        outcome = next(
            r for r in gate["domain_authority"] if r["domain_id"] == "outcome_labels_and_cutoffs"
        )
        self.assertEqual(outcome["authority_class"], POSTGAME_ONLY)

    def test_the_bounded_domains_are_labeled_as_bounds(self) -> None:
        gate = synthetic_gate()
        bounded = [
            r["domain_id"]
            for r in gate["domain_authority"]
            if r["authority_class"] == CONSERVATIVE_BOUND
        ]
        self.assertEqual(bounded, ["team_outcome_priors", "team_season_context"])
        self.assertIn("BOUND_NOT_AN_OBSERVED", gate["conservative_bound_policy"]["label"])

    def test_gap_002_remains_open_while_any_domain_is_blocked(self) -> None:
        gate = synthetic_gate()
        self.assertTrue(gate["gap_verdict"]["remains_open"])
        self.assertTrue(gate["domains_blocked_from_point_in_time_admission"])

    def test_an_unavailable_route_is_reported_truthfully_not_silently_dropped(self) -> None:
        gate = synthetic_gate(ncaa_state="TECHNICALLY_UNAVAILABLE")
        ncaa = next(
            r
            for r in gate["publication_time_route_findings"]
            if r["route_id"] == "NCAA_OFFICIAL_STATS_RANKINGS"
        )
        self.assertEqual(ncaa["state"], "TECHNICALLY_UNAVAILABLE")
        self.assertEqual(ncaa["failure_condition"], "HTTP_404")
        self.assertFalse(ncaa["bears_a_publication_instant"])

    def test_an_observed_instant_is_never_promoted_to_a_historical_release_instant(self) -> None:
        gate = synthetic_gate()
        ap = next(
            r
            for r in gate["publication_time_route_findings"]
            if r["route_id"] == "AP_OFFICIAL_TOP25_FOOTBALL"
        )
        self.assertTrue(ap["bears_a_publication_instant"])
        self.assertFalse(ap["historical_per_season_release_instant_available"])

    def test_the_audit_is_deterministic_across_rebuilds(self) -> None:
        self.assertEqual(synthetic_gate()["gate_identity"], synthetic_gate()["gate_identity"])


class TamperTests(unittest.TestCase):
    def _write(self, root: Path, gate: dict[str, Any]) -> None:
        (root / "configs").mkdir(parents=True, exist_ok=True)
        (root / "artifacts" / "data_lake").mkdir(parents=True, exist_ok=True)
        (root / CONTRACT_RELATIVE).write_bytes((REPO_ROOT / CONTRACT_RELATIVE).read_bytes())
        (root / GATE_RELATIVE).write_text(json.dumps(gate, indent=2, sort_keys=True), "utf-8")

    def _reject(self, mutate) -> None:
        import tempfile

        gate = synthetic_gate()
        mutate(gate)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, gate)
            with self.assertRaises(KnownAtAuthorityViolation):
                validate_artifact(root)

    def test_a_baseline_gate_validates(self) -> None:
        import tempfile

        gate = synthetic_gate()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, gate)
            self.assertEqual(validate_artifact(root)["gate_identity"], gate["gate_identity"])

    def test_promoting_a_retrieval_only_domain_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            for row in gate["domain_authority"]:
                if row["domain_id"] == "rankings":
                    row["authority_is_sufficient_for_point_in_time_admission"] = True
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_relabeling_rankings_as_an_observed_publication_instant_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            for row in gate["publication_time_route_findings"]:
                row["bears_a_publication_instant"] = False
                row["historical_per_season_release_instant_available"] = True
            for row in gate["domain_authority"]:
                if row["domain_id"] == "rankings":
                    row["authority_class"] = OBSERVED_PUBLICATION
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_dropping_a_route_below_the_two_route_requirement_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["publication_time_route_findings"] = gate["publication_time_route_findings"][:1]
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_weakening_the_date_only_separation_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["conservative_bound_policy"]["date_only_rule"]["required_separation_days"] = 1
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_declaring_the_bound_policy_after_the_fact_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["conservative_bound_policy"]["precommitted"] = False
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_falsely_closing_gap_002_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["gap_verdict"]["remains_open"] = False
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_dropping_an_audited_domain_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["domain_authority"] = gate["domain_authority"][:-1]
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_an_undeclared_authority_class_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["domain_authority"][0]["authority_class"] = "OBSERVED_BECAUSE_WE_SAID_SO"
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_editing_the_gate_without_restamping_its_identity_is_caught(self) -> None:
        self._reject(lambda gate: gate["domain_authority"][0].update(evidence="rewritten"))

    def test_rebinding_the_gate_to_a_foreign_contract_is_caught(self) -> None:
        def mutate(gate: dict[str, Any]) -> None:
            gate["contract_sha256"] = "e" * 64
            gate["gate_identity"] = gate_identity_of(gate)

        self._reject(mutate)

    def test_a_missing_gate_fails_closed(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "configs").mkdir(parents=True)
            (root / CONTRACT_RELATIVE).write_bytes((REPO_ROOT / CONTRACT_RELATIVE).read_bytes())
            with self.assertRaises(KnownAtAuthorityViolation):
                validate_artifact(root)

    def test_a_missing_contract_fails_closed(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(KnownAtAuthorityViolation):
                load_contract(Path(raw))


class CommittedArtifactTests(unittest.TestCase):
    def test_the_committed_gate_validates_and_binds_the_contract(self) -> None:
        summary = validate_artifact(REPO_ROOT)
        self.assertEqual(summary["result"], "PASS_HISTORICAL_KNOWN_AT_AUTHORITY_AUDIT")
        self.assertEqual(load_contract(REPO_ROOT)["contract_id"], CONTRACT_ID)

    def test_the_committed_gate_blocks_rankings_and_venues(self) -> None:
        summary = validate_artifact(REPO_ROOT)
        self.assertEqual(
            summary["domains_blocked_from_point_in_time_admission"], ["rankings", "venues"]
        )

    def test_the_committed_gate_records_the_real_spine_bifurcation(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text("utf-8-sig"))
        profile = gate["start_time_evidence_profile"]
        self.assertEqual(max(profile["seasons_with_calendar_date_evidence_only"]), 2000)
        self.assertEqual(min(profile["seasons_with_a_published_start_instant"]), 2001)


if __name__ == "__main__":
    unittest.main()
