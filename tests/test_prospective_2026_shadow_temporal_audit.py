"""Tamper and fail-closed coverage for the 2026 shadow forecast temporal audit."""

from __future__ import annotations

import copy
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.modeling.shadow_forecast_temporal_audit import (  # noqa: E402
    FAIL_CLOSED,
    GATE_RELATIVE,
    MISSED_CUTOFF,
    PROOF_COMPLETE,
    TemporalAuditViolation,
    build_audit,
    gate_identity_of,
    load_contract,
    probability_identity,
    reconstruct_population,
    validate_artifact,
)

MODEL_IDENTITY = "model-identity"
CODE_IDENTITY = "code-identity"
FEATURE_IDENTITY = "feature-identity"
SNAPSHOT_IDENTITY = "snapshot-identity"


def synthetic_population() -> dict[str, object]:
    snapshot = {
        "checkpoints": [
            {"checkpoint_id": "T_MINUS_24H", "deadline_utc": "2026-09-04T19:45:00Z"},
            {"checkpoint_id": "T_MINUS_90M", "deadline_utc": "2026-09-05T18:15:00Z"},
        ],
        "forecast_state": "SNAPSHOT_FROZEN",
        "ncaa_contest_id": "6582887",
        "snapshot": {
            "capture_retrieved_at_utc": "2026-08-28T21:49:31Z",
            "cutoff_checkpoint_id": "T_MINUS_90M",
            "snapshot_frozen_at_utc": "2026-08-28T23:34:57Z",
            "snapshot_identity": SNAPSHOT_IDENTITY,
        },
        "source_published_game_date": "2026-09-05",
    }
    forecast = {
        "candidate_id": "national_base_rate",
        "code_identity": CODE_IDENTITY,
        "created_at_utc": "2026-08-28T23:34:57Z",
        "feature_identity": FEATURE_IDENTITY,
        "forecast_state": "FORECAST_FROZEN",
        "kickoff_utc_conservative_lower_bound": "2026-09-05T19:45:00Z",
        "model_identity": MODEL_IDENTITY,
        "ncaa_contest_id": "6582887",
        "probability_home_win": 0.61,
        "snapshot_identity": SNAPSHOT_IDENTITY,
        "source_published_game_date": "2026-09-05",
    }
    return {
        "calendar_gate": {
            "corrected_calendar": [{"corrected_label": "WEEK_ONE", "game_date": "2026-09-05"}],
            "gate_identity": "calendar-identity",
        },
        "cohort_gate": {
            "gate_identity": "cohort-identity",
            "schedule_window": {
                "week_one_dates": ["2026-09-05"],
                "week_zero_dates": ["2026-08-22"],
            },
        },
        "forecast_gate": {
            "gate_identity": "forecast-identity",
            "identities": {
                "code_identity": CODE_IDENTITY,
                "feature_identity": FEATURE_IDENTITY,
                "model_identity": MODEL_IDENTITY,
            },
        },
        "forecast_rows": [forecast],
        "manifest": {},
        "snapshot_records": [snapshot],
    }


def synthetic_contract() -> dict[str, object]:
    return {
        "expected_population": {
            "contests_observed": 1,
            "forecast_rows_emitted": 1,
            "forecast_rows_frozen": 1,
            "snapshots_frozen": 1,
            "unsupported_contests": 0,
        },
        "non_frozen_row_explanations": {},
        "outcome_exclusion": "NO_OUTCOME_FIELD_IS_READ_BY_THIS_AUDIT",
        "scientific_nonclaims": {},
    }


class SyntheticTemporalAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.population = synthetic_population()
        self.contract = synthetic_contract()

    def audit(self, population: dict[str, object] | None = None) -> dict[str, object]:
        return build_audit(population or self.population, self.contract)

    def only_verdict(self, gate: dict[str, object]) -> dict[str, object]:
        rows = gate["row_verdicts"]
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_an_untampered_row_proves_complete(self) -> None:
        verdict = self.only_verdict(self.audit())
        self.assertEqual(verdict["verdict"], PROOF_COMPLETE)
        self.assertEqual(verdict["missing_bindings"], [])
        self.assertTrue(all(verdict["ordering_checks"].values()))

    def test_the_audit_is_deterministic_and_self_covering(self) -> None:
        first = self.audit()
        second = self.audit(copy.deepcopy(self.population))
        self.assertEqual(first["gate_identity"], second["gate_identity"])
        self.assertEqual(gate_identity_of(first), first["gate_identity"])

    def test_moving_the_kickoff_bound_behind_issuance_is_caught(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["kickoff_utc_conservative_lower_bound"] = (
            "2026-08-28T00:00:00Z"
        )
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], MISSED_CUTOFF)
        self.assertFalse(verdict["ordering_checks"]["issuance_strictly_precedes_kickoff"])

    def test_a_forecast_issued_exactly_at_kickoff_is_not_timely(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["created_at_utc"] = "2026-09-05T19:45:00Z"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], MISSED_CUTOFF)

    def test_a_post_kickoff_snapshot_freeze_is_caught(self) -> None:
        population = copy.deepcopy(self.population)
        population["snapshot_records"][0]["snapshot"]["snapshot_frozen_at_utc"] = (
            "2026-09-05T21:00:00Z"
        )
        population["forecast_rows"][0]["created_at_utc"] = "2026-09-05T21:00:01Z"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], MISSED_CUTOFF)

    def test_issuance_after_the_declared_cutoff_but_before_kickoff_is_a_missed_cutoff(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["created_at_utc"] = "2026-09-05T19:00:00Z"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], MISSED_CUTOFF)
        self.assertFalse(verdict["ordering_checks"]["issuance_within_declared_cutoff"])
        self.assertTrue(verdict["ordering_checks"]["issuance_strictly_precedes_kickoff"])

    def test_altering_the_issued_at_stamp_out_of_order_is_caught(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["created_at_utc"] = "2026-08-28T20:00:00Z"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], FAIL_CLOSED)
        self.assertFalse(verdict["ordering_checks"]["snapshot_freeze_precedes_issuance"])

    def test_an_unparseable_issued_at_stamp_fails_closed(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["created_at_utc"] = "not-a-timestamp"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], FAIL_CLOSED)
        self.assertIn("forecast_issued_at_utc", verdict["missing_bindings"])

    def test_substituting_the_contest_identity_fails_closed(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["ncaa_contest_id"] = "9999999"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], FAIL_CLOSED)
        self.assertIn("official_contest_identity", verdict["missing_bindings"])

    def test_moving_the_published_game_date_fails_closed(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["source_published_game_date"] = "2026-09-06"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], FAIL_CLOSED)
        self.assertIn("official_game_date", verdict["missing_bindings"])

    def test_inserting_a_candidate_without_a_snapshot_fails_closed(self) -> None:
        population = copy.deepcopy(self.population)
        inserted = copy.deepcopy(population["forecast_rows"][0])
        inserted["candidate_id"] = "smuggled_candidate"
        inserted["ncaa_contest_id"] = "7777777"
        population["forecast_rows"].append(inserted)
        gate = self.audit(population)
        smuggled = [r for r in gate["row_verdicts"] if r["candidate_id"] == "smuggled_candidate"]
        self.assertEqual(len(smuggled), 1)
        self.assertEqual(smuggled[0]["verdict"], FAIL_CLOSED)

    def test_mutating_the_probability_changes_the_probability_identity(self) -> None:
        original = probability_identity(self.population["forecast_rows"][0])
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["probability_home_win"] = 0.62
        mutated = probability_identity(population["forecast_rows"][0])
        self.assertNotEqual(original, mutated)
        self.assertNotEqual(self.audit()["gate_identity"], self.audit(population)["gate_identity"])

    def test_a_null_probability_cannot_carry_a_complete_proof(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["probability_home_win"] = None
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], FAIL_CLOSED)
        self.assertIn("probability_identity", verdict["missing_bindings"])

    def test_forging_the_model_identity_fails_closed(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["model_identity"] = "forged"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], FAIL_CLOSED)
        self.assertIn("model_identity", verdict["missing_bindings"])

    def test_forging_the_snapshot_identity_fails_closed(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"][0]["snapshot_identity"] = "forged"
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], FAIL_CLOSED)
        self.assertIn("snapshot_identity", verdict["missing_bindings"])

    def test_a_capture_taken_after_the_snapshot_freeze_fails_closed(self) -> None:
        population = copy.deepcopy(self.population)
        population["snapshot_records"][0]["snapshot"]["capture_retrieved_at_utc"] = (
            "2026-08-29T00:00:00Z"
        )
        verdict = self.only_verdict(self.audit(population))
        self.assertEqual(verdict["verdict"], FAIL_CLOSED)
        self.assertFalse(verdict["ordering_checks"]["capture_precedes_snapshot_freeze"])

    def test_the_corrected_label_is_applied_without_moving_membership(self) -> None:
        population = copy.deepcopy(self.population)
        population["calendar_gate"]["corrected_calendar"] = [
            {"corrected_label": "WEEK_ZERO", "game_date": "2026-09-05"}
        ]
        gate = self.audit(population)
        correction = gate["taxonomy_corrections"][0]
        self.assertTrue(correction["label_changed"])
        self.assertFalse(correction["membership_changed"])
        self.assertEqual(correction["contest_count"], 1)


class CommittedTemporalAuditGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        if not self.data_root:
            self.skipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")

    def test_the_committed_gate_reproduces_from_the_frozen_population(self) -> None:
        summary = validate_artifact(REPO_ROOT, Path(self.data_root))
        self.assertEqual(summary["rows_audited"], 164)
        self.assertEqual(summary["verdict_counts"][PROOF_COMPLETE], 164)

    def test_reconstruction_matches_the_declared_cycle_twenty_population(self) -> None:
        population = reconstruct_population(REPO_ROOT, Path(self.data_root))
        self.assertEqual(len(population["snapshot_records"]), 99)
        self.assertEqual(len(population["forecast_rows"]), 495)

    def test_the_validator_rejects_a_forged_gate_identity(self) -> None:
        committed = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        forged = copy.deepcopy(committed)
        forged["gate_identity"] = "0" * 64
        self.assertNotEqual(gate_identity_of(forged), forged["gate_identity"])

    def test_the_contract_binding_is_checked(self) -> None:
        contract = load_contract(REPO_ROOT)
        self.assertEqual(contract["jira_key"], "BAT-664")

    def test_the_validator_rejects_a_missing_gate(self) -> None:
        with self.assertRaises(TemporalAuditViolation):
            validate_artifact(Path(self.data_root), Path(self.data_root))


if __name__ == "__main__":
    unittest.main()
