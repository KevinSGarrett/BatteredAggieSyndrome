from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.run_leakage_battery import (
    DATASET_IDENTITY,
    REQUIRED_PAYLOADS,
    SCENARIOS,
    compute_artifact_identity,
    derive_terminal_state,
    resolve_external_path,
    validate_results,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "artifacts" / "pit" / "leakage_battery_results.json"


def _payload_identity(name: str) -> dict[str, object]:
    spec = REQUIRED_PAYLOADS[name]
    return {
        "name": name,
        "path": (
            f"C:/BatteredAggieSyndrome.data/features/historical_known_at/sha256/"
            f"{DATASET_IDENTITY}/{name}"
        ),
        "bytes": 4096,
        "sha256": spec["sha256"],
        "rows": spec["rows"],
        "columns": list(spec["required_columns"]),
    }


def _scenario(scenario_id: str, *, disposition: str = "PASS", **overrides: object) -> dict[str, object]:
    baseline = "a" * 64
    mutated = "b" * 64 if scenario_id in {
        "value_mutation_isolation",
        "prediction_cutoff_enforcement",
        "known_at_timestamp_enforcement",
    } else baseline
    row = {
        "scenario_id": scenario_id,
        "disposition": disposition,
        "mutation": f"executed {scenario_id}",
        "source_input_identity": DATASET_IDENTITY,
        "expected_behavior": "fail-closed leakage behavior",
        "observed_behavior": "pass" if disposition == "PASS" else "fail",
        "affected_row_ids": ["row-affected"] if scenario_id == "value_mutation_isolation" else [],
        "unaffected_control_row_ids": ["row-control"],
        "baseline_hash": baseline,
        "mutated_hash": mutated,
        "applicable_cutoff": "TARGET_START_UTC_MINUS_24_HOURS",
        "remediation_on_failure": "preserve evidence and fix the failing control",
    }
    row.update(overrides)
    return row


def _valid_payload(*, fail_scenario: str | None = None) -> dict[str, object]:
    scenarios = []
    for scenario_id in SCENARIOS:
        disposition = "FAIL" if scenario_id == fail_scenario else "PASS"
        scenarios.append(_scenario(scenario_id, disposition=disposition))
    derived = derive_terminal_state(scenarios)
    acceptance_pass = derived["status"] == "DONE"
    payload = {
        "schema_version": "aggie.pit.leakage_battery.v2",
        "artifact_type": "REAL_SCOPED_LEAKAGE_BATTERY_RESULTS",
        "decision_unit": "POST-SUBTASK-049",
        "jira_key": "BAT-399",
        "dataset_identity": DATASET_IDENTITY,
        "input_identities": {
            "dataset_identity": DATASET_IDENTITY,
            "manifest_path": (
                f"C:/BatteredAggieSyndrome.data/manifests/historical_known_at/sha256/"
                f"{DATASET_IDENTITY}/known_at_replay_manifest.json"
            ),
            "payloads": [_payload_identity(name) for name in REQUIRED_PAYLOADS],
        },
        "scenarios": scenarios,
        "acceptance_matrix": [
            {
                "criterion": "Authoritative BAT-523 payloads exist, hash-verify, and bind dataset identity.",
                "disposition": "PASS",
                "evidence": "input_identities.payloads",
            },
            {
                "criterion": "All required leakage scenarios execute real mutations or governed-absence checks with row-level evidence.",
                "disposition": "PASS" if acceptance_pass else "FAIL",
                "evidence": "scenarios",
            },
            {
                "criterion": "Terminal status, blockers, BAT-400 eligibility, and acceptance are derived from scenario dispositions.",
                "disposition": "PASS" if acceptance_pass else "FAIL",
                "evidence": "status + remaining_blockers + downstream_eligibility",
            },
        ],
        "status": derived["status"],
        "remaining_blockers": derived["remaining_blockers"],
        "downstream_eligibility": {
            "BAT-400": derived["bat400"],
            "reason": "derived",
        },
    }
    payload["artifact_identity"] = compute_artifact_identity(payload)
    return payload


class LeakageBatteryResultsTests(unittest.TestCase):
    def test_validate_accepts_consistent_done_payload(self) -> None:
        payload = _valid_payload()
        self.assertEqual(payload["status"], "DONE")
        validate_results(payload, ROOT)

    def test_validate_rejects_cycle3_forged_terminal_authority(self) -> None:
        payload = _valid_payload(fail_scenario="value_mutation_isolation")
        self.assertEqual(payload["status"], "BLOCKED")
        validate_results(payload, ROOT)
        forged = copy.deepcopy(payload)
        forged["status"] = "DONE"
        forged["remaining_blockers"] = ["NONE"]
        forged["downstream_eligibility"] = {
            "BAT-400": "READY",
            "reason": "forged",
        }
        for row in forged["acceptance_matrix"]:
            row["disposition"] = "PASS"
        forged["artifact_identity"] = compute_artifact_identity(forged)
        with self.assertRaisesRegex(ValueError, "status is not bound to scenario dispositions"):
            validate_results(forged, ROOT)

    def test_validate_rejects_forged_blockers_and_readiness_after_rehash(self) -> None:
        payload = _valid_payload(fail_scenario="future_record_append_invariance")
        forged = copy.deepcopy(payload)
        forged["remaining_blockers"] = ["NONE"]
        forged["downstream_eligibility"] = {"BAT-400": "READY", "reason": "forged"}
        forged["artifact_identity"] = compute_artifact_identity(forged)
        with self.assertRaisesRegex(ValueError, "remaining_blockers"):
            validate_results(forged, ROOT)

    def test_validate_rejects_missing_reordered_and_unknown_scenarios(self) -> None:
        payload = _valid_payload()
        missing = copy.deepcopy(payload)
        missing["scenarios"] = missing["scenarios"][:-1]
        missing["artifact_identity"] = compute_artifact_identity(missing)
        with self.assertRaisesRegex(ValueError, "scenario set/order mismatch"):
            validate_results(missing, ROOT)

        reordered = copy.deepcopy(payload)
        reordered["scenarios"] = list(reversed(reordered["scenarios"]))
        reordered["artifact_identity"] = compute_artifact_identity(reordered)
        with self.assertRaisesRegex(ValueError, "scenario set/order mismatch"):
            validate_results(reordered, ROOT)

        unknown = copy.deepcopy(payload)
        unknown["scenarios"][0]["scenario_id"] = "not_a_real_scenario"
        unknown["artifact_identity"] = compute_artifact_identity(unknown)
        with self.assertRaisesRegex(ValueError, "scenario set/order mismatch"):
            validate_results(unknown, ROOT)

    def test_validate_rejects_altered_identity_and_unresolved_path(self) -> None:
        payload = _valid_payload()
        identity = copy.deepcopy(payload)
        identity["dataset_identity"] = "0" * 64
        identity["artifact_identity"] = compute_artifact_identity(identity)
        with self.assertRaisesRegex(ValueError, "dataset identity mismatch"):
            validate_results(identity, ROOT)

        unresolved = copy.deepcopy(payload)
        unresolved["input_identities"]["payloads"][0]["path"] = (
            "<external-data-root>/features/BAT-397/pregame_matrix_rows.parquet"
        )
        unresolved["artifact_identity"] = compute_artifact_identity(unresolved)
        with self.assertRaisesRegex(ValueError, "unresolved or obsolete"):
            validate_results(unresolved, ROOT)

    def test_validate_rejects_identical_hashes_for_value_mutation_pass(self) -> None:
        payload = _valid_payload()
        row = next(item for item in payload["scenarios"] if item["scenario_id"] == "value_mutation_isolation")
        row["mutated_hash"] = row["baseline_hash"]
        payload["artifact_identity"] = compute_artifact_identity(payload)
        with self.assertRaisesRegex(ValueError, "identical hashes without an executed mutation"):
            validate_results(payload, ROOT)

    def test_resolve_external_path_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "features").mkdir()
            resolved = resolve_external_path(root, "<external-data-root>/features/ok.parquet")
            self.assertEqual(resolved, (root / "features" / "ok.parquet").resolve())
            with self.assertRaisesRegex(ValueError, "traversal"):
                resolve_external_path(root, "<external-data-root>/features/../secret.parquet")
            with self.assertRaisesRegex(ValueError, "must start with"):
                resolve_external_path(root, str(root / "features" / "ok.parquet"))

    def test_real_artifact_binds_terminal_state_and_payload_identities(self) -> None:
        self.assertTrue(RESULTS_PATH.is_file(), "leakage battery artifact is missing")
        payload = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "aggie.pit.leakage_battery.v2")
        self.assertEqual([row["scenario_id"] for row in payload["scenarios"]], SCENARIOS)
        validate_results(payload, ROOT)
        self.assertEqual(payload["dataset_identity"], DATASET_IDENTITY)
        self.assertNotIn("ROW_LEVEL_MATRIX_PAYLOADS_UNAVAILABLE", payload["remaining_blockers"])
        if payload["status"] == "DONE":
            self.assertEqual(payload["remaining_blockers"], ["NONE"])
            self.assertEqual(payload["downstream_eligibility"]["BAT-400"], "READY")
            self.assertTrue(all(row["disposition"] == "PASS" for row in payload["scenarios"]))


if __name__ == "__main__":
    unittest.main()
