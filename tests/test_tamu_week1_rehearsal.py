"""Offline tests for the Texas A&M Week One 2026 rehearsal."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.modeling.tamu_week1_rehearsal import (
    CONTRACT_RELATIVE,
    TAMU_CANONICAL_TEAM_ID,
    augmentation_summary,
    build_rehearsal_bundle,
    checkpoint_plan,
    feature_availability_matrix,
    load_contract,
    no_adjustment_path,
    select_target_contest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

EXECUTION_TIME = datetime.now(timezone.utc)
KICKOFF = EXECUTION_TIME + timedelta(days=8)
CREATED = EXECUTION_TIME - timedelta(minutes=5)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def contract() -> dict:
    return load_contract(REPO_ROOT)


def snapshot_row(**overrides) -> dict:
    declared = contract()["target_contest"]
    row = {
        "ncaa_contest_id": "6607349",
        "home_source_display_name": declared["declared_home_source_display_name"],
        "away_source_display_name": declared["declared_away_source_display_name"],
        "source_published_game_date": declared["declared_source_published_game_date"],
        "source_published_clock_text": declared["declared_source_published_clock_text"],
        "home_canonical_team_id": TAMU_CANONICAL_TEAM_ID,
        "away_canonical_team_id": "SRC-002:TEAM:2623",
        "is_neutral_site": False,
        "forecast_state": "SNAPSHOT_FROZEN",
        "kickoff_utc_conservative_lower_bound": iso(KICKOFF),
        "snapshot": {
            "snapshot_identity": "a" * 64,
            "capture_sha256": "b" * 64,
            "capture_retrieved_at_utc": iso(CREATED),
            "snapshot_frozen_at_utc": iso(CREATED),
            "outcome_read_before_freeze": False,
        },
    }
    row.update(overrides)
    return row


def forecast_row(candidate_id: str, *, frozen: bool, **overrides) -> dict:
    row = {
        "ncaa_contest_id": "6607349",
        "candidate_id": candidate_id,
        "candidate_admissibility": "ADMISSIBLE_FOR_PROSPECTIVE_SHADOW_USE"
        if frozen
        else "NOT_ADMISSIBLE_MISSING_REQUIRED_FEATURES",
        "forecast_state": "FORECAST_FROZEN" if frozen else "MISSING_REQUIRED_FEATURES_ABSTAIN",
        "probability_home_win": 0.87 if frozen else None,
        "orientation": "PROBABILITY_IS_STATED_FOR_THE_HOME_OR_FIRST_LISTED_CANONICAL_TEAM",
        "abstention_state": None if frozen else "MISSING_REQUIRED_FEATURES_ABSTAIN",
        "abstention_reason": None if frozen else "features are not materialized for 2026",
        "model_identity": "c" * 64,
        "feature_identity": "d" * 64,
        "code_identity": "e" * 64,
        "snapshot_identity": "a" * 64,
        "created_at_utc": iso(CREATED),
        "forecast_authority": "PROSPECTIVE_SHADOW_OBSERVATION_ONLY",
        "kickoff_utc_conservative_lower_bound": iso(KICKOFF),
    }
    row.update(overrides)
    return row


BASELINE_CONTRACT = {
    "candidates": [
        {"candidate_id": "national_base_rate"},
        {"candidate_id": "national_elo"},
        {"candidate_id": "prior_only"},
        {"candidate_id": "national_logistic_l2"},
        {"candidate_id": "national_margin_ridge"},
    ]
}

DOMAIN_GATE = {
    "admission_matrix": [
        {
            "domain_id": "team_outcomes_and_priors",
            "label": "Team outcomes and priors",
            "decision": "ADMITTED",
            "known_at_basis": "PREGAME_STATIC_ATTRIBUTE",
            "domain_scope_games": 45099,
            "tamu_share": {"domain_scope_tamu_games": 724, "tamu_game_share_of_domain": 0.016},
        },
        {
            "domain_id": "plays",
            "label": "Plays",
            "decision": "CANDIDATE",
            "known_at_basis": "POSTGAME_ONLY",
            "domain_scope_games": 18721,
            "tamu_share": {"domain_scope_tamu_games": 287, "tamu_game_share_of_domain": 0.015},
        },
        {
            "domain_id": "coaching_staff",
            "label": "Coaching and staff",
            "decision": "SOURCE_ABSENT",
            "known_at_basis": "SOURCE_ABSENT",
            "domain_scope_games": 0,
            "tamu_share": {"domain_scope_tamu_games": 0, "tamu_game_share_of_domain": None},
        },
        {
            "domain_id": "rankings",
            "label": "Rankings",
            "decision": "CANDIDATE",
            "known_at_basis": "PREGAME_PUBLISHED_ORDINAL",
            "domain_scope_games": 9000,
            "tamu_share": {"domain_scope_tamu_games": 120, "tamu_game_share_of_domain": 0.013},
        },
    ]
}

TAMU_GATES = {
    "tamu_cross_source_domain_gate": {
        "admissions": {
            "gate_admission": "CANDIDATE_ONLY",
            "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
            "pregame_availability": "BLOCKED",
        },
        "counts": {"scheduled_games": 26, "pregame_availability_true": 0},
    },
    "tamu_official_evidence_gap_matrix_gate": {"admissions": {}},
}


class ContractInvariants(unittest.TestCase):
    def test_contract_loads_and_forbids_specialization_output(self) -> None:
        loaded = contract()
        self.assertFalse(loaded["specialization"]["specialization_output_permitted"])
        self.assertTrue(loaded["no_adjustment_path"]["mandatory"])

    def test_authority_flags_cannot_be_relaxed(self) -> None:
        raw = json.loads((REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig"))
        for field in (
            "protected_evaluation_admission",
            "champion_or_production_promotion",
            "tamu_specialization_admission",
        ):
            self.assertFalse(raw["authority"][field])


class TargetContestSelection(unittest.TestCase):
    def test_exactly_one_contest_is_required(self) -> None:
        rows = [snapshot_row(), snapshot_row(ncaa_contest_id="9999999")]
        with self.assertRaises(ValueError):
            select_target_contest(rows, contract())

    def test_unfrozen_snapshot_is_rejected(self) -> None:
        row = snapshot_row(forecast_state="MISSED_CUTOFF_NO_BACKFILL")
        with self.assertRaises(ValueError):
            select_target_contest([row], contract())

    def test_clock_drift_is_rejected(self) -> None:
        row = snapshot_row(source_published_clock_text="08:00 PM")
        with self.assertRaises(ValueError):
            select_target_contest([row], contract())

    def test_matching_row_is_returned(self) -> None:
        selected = select_target_contest([snapshot_row()], contract())
        self.assertEqual(selected["ncaa_contest_id"], "6607349")


class NoAdjustmentPath(unittest.TestCase):
    def test_frozen_and_abstaining_rows_are_separated(self) -> None:
        rows = [
            forecast_row("national_base_rate", frozen=True),
            forecast_row("national_elo", frozen=True),
            forecast_row("prior_only", frozen=False),
        ]
        path = no_adjustment_path(
            rows,
            contest_id="6607349",
            contract=contract(),
            baseline_contract=BASELINE_CONTRACT,
        )
        self.assertEqual(path["frozen_candidate_ids"], ["national_base_rate", "national_elo"])
        self.assertEqual(path["abstaining_candidate_ids"], ["prior_only"])
        self.assertFalse(path["tamu_adjustment_applied"])

    def test_candidate_outside_the_frozen_set_is_rejected(self) -> None:
        rows = [forecast_row("tamu_specialization_v1", frozen=True)]
        with self.assertRaises(ValueError):
            no_adjustment_path(
                rows,
                contest_id="6607349",
                contract=contract(),
                baseline_contract=BASELINE_CONTRACT,
            )

    def test_forecast_created_after_kickoff_is_rejected(self) -> None:
        rows = [
            forecast_row(
                "national_elo",
                frozen=True,
                created_at_utc=iso(KICKOFF + timedelta(minutes=1)),
            )
        ]
        with self.assertRaises(ValueError):
            no_adjustment_path(
                rows,
                contest_id="6607349",
                contract=contract(),
                baseline_contract=BASELINE_CONTRACT,
            )

    def test_missing_frozen_row_is_rejected(self) -> None:
        rows = [forecast_row("prior_only", frozen=False)]
        with self.assertRaises(ValueError):
            no_adjustment_path(
                rows,
                contest_id="6607349",
                contract=contract(),
                baseline_contract=BASELINE_CONTRACT,
            )


class AvailabilityMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = feature_availability_matrix(
            domain_gate=DOMAIN_GATE, tamu_gates=TAMU_GATES, contract=contract()
        )

    def test_every_class_is_declared_and_nothing_is_materialized(self) -> None:
        declared = set(contract()["feature_availability"]["classes"])
        for row in self.matrix:
            self.assertIn(row["availability_class"], declared)
            self.assertFalse(row["target_contest_feature_materialized"])

    def test_postgame_and_absent_domains_are_not_augmentation_candidates(self) -> None:
        summary = augmentation_summary(self.matrix)
        self.assertIn("plays", summary["temporally_ineligible"])
        self.assertIn("coaching_staff", summary["unavailable"])
        self.assertIn("rankings", summary["could_augment_if_admitted_and_temporally_eligible"])
        self.assertIn(
            "team_outcomes_and_priors", summary["already_consumed_by_the_national_baseline"]
        )
        self.assertEqual(summary["materialized_augmentation_features_for_the_target_contest"], 0)

    def test_tamu_archive_is_temporally_ineligible(self) -> None:
        row = next(
            item
            for item in self.matrix
            if item["domain_id"] == "tamu_official_structured_domains"
        )
        self.assertEqual(row["availability_class"], "TEMPORALLY_INELIGIBLE_UNKNOWN_KNOWN_AT")

    def test_pregame_availability_route_is_blocked(self) -> None:
        row = next(
            item for item in self.matrix if item["domain_id"] == "tamu_pregame_availability"
        )
        self.assertEqual(row["availability_class"], "UNAVAILABLE_ROUTE_BLOCKED")


class Checkpoints(unittest.TestCase):
    def test_three_checkpoints_with_no_backfill(self) -> None:
        plan = checkpoint_plan(
            kickoff=KICKOFF, execution_time=EXECUTION_TIME, contract=contract()
        )
        self.assertEqual(
            [item["checkpoint_id"] for item in plan],
            ["T_MINUS_7D", "T_MINUS_24H", "T_MINUS_90M"],
        )
        self.assertTrue(all(item["backfill_permitted_after_the_deadline"] is False for item in plan))
        self.assertEqual(
            [item["is_snapshot_cutoff"] for item in plan], [False, False, True]
        )

    def test_a_passed_checkpoint_is_closed(self) -> None:
        plan = checkpoint_plan(
            kickoff=EXECUTION_TIME + timedelta(hours=2),
            execution_time=EXECUTION_TIME,
            contract=contract(),
        )
        states = {item["checkpoint_id"]: item["state"] for item in plan}
        self.assertEqual(states["T_MINUS_7D"], "CLOSED")
        self.assertEqual(states["T_MINUS_24H"], "CLOSED")
        self.assertEqual(states["T_MINUS_90M"], "OPEN")


class Bundle(unittest.TestCase):
    def bundle(self) -> dict:
        return build_rehearsal_bundle(
            contract=contract(),
            baseline_contract=BASELINE_CONTRACT,
            snapshots=[snapshot_row()],
            forecasts=[
                forecast_row("national_base_rate", frozen=True),
                forecast_row("national_elo", frozen=True),
                forecast_row("prior_only", frozen=False),
            ],
            domain_gate=DOMAIN_GATE,
            tamu_gates=TAMU_GATES,
            execution_time=EXECUTION_TIME,
        )

    def test_bundle_reports_one_contest_and_no_specialization_row(self) -> None:
        bundle = self.bundle()
        self.assertEqual(bundle["counts"]["target_contests"], 1)
        self.assertEqual(bundle["counts"]["specialization_rows_emitted"], 0)
        self.assertTrue(bundle["specialization"]["comparator_is_mandatory_and_present"])
        self.assertFalse(bundle["specialization"]["single_game_lift_claimed"])

    def test_rehearsal_after_kickoff_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_rehearsal_bundle(
                contract=contract(),
                baseline_contract=BASELINE_CONTRACT,
                snapshots=[
                    snapshot_row(
                        kickoff_utc_conservative_lower_bound=iso(
                            EXECUTION_TIME - timedelta(hours=1)
                        )
                    )
                ],
                forecasts=[forecast_row("national_elo", frozen=True)],
                domain_gate=DOMAIN_GATE,
                tamu_gates=TAMU_GATES,
                execution_time=EXECUTION_TIME,
            )

    def test_scoring_plan_refuses_early_outcome_access(self) -> None:
        plan = self.bundle()["scoring_plan"]
        self.assertFalse(plan["outcome_load_permitted_before_forecast_freeze"])
        self.assertFalse(plan["may_promote_a_model"])
        self.assertEqual(plan["current_state"], "AWAITING_ELIGIBLE_OFFICIAL_FINALS")


if __name__ == "__main__":
    unittest.main()
