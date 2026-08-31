"""Independent reconstruction and contamination-isolation proof for BAT-674.

The reconstruction checks read the mounted data root but never write to it.  The
determinism checks copy every required input into a throwaway data root, so a
concurrent suite running against the shared mount cannot observe or be affected by
anything this module materializes.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _entry in (ROOT / "tools", ROOT / "src"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from build_week_zero_2026_official_final_scoring_successor import (  # noqa: E402
    build_successor,
    read_json,
)
from validate_week_zero_2026_official_final_scoring_successor import validate  # noqa: E402

from aggie_analytics.modeling.week_zero_official_final_scoring import (  # noqa: E402
    OfficialFinalScoringViolation,
)

GATE_PATH = ROOT / "artifacts/shadow/week_zero_2026_official_final_scoring_successor_gate.json"
DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

TRACKED_ARTIFACTS = (
    "artifacts/shadow/week_zero_2026_official_final_scoring_successor_gate.json",
    "artifacts/shadow/week_zero_2026_official_final_scoring_successor_payload.json",
    "artifacts/shadow/week_zero_2026_official_final_scoring_successor_replay.json",
    "artifacts/shadow/week_zero_2026_official_final_scoring_successor_state_transitions.json",
    "artifacts/shadow/week_zero_2026_prospective_residual_successor_payload.json",
    "artifacts/shadow/week_zero_2026_cfbd_crosswalk.json",
    "artifacts/shadow/week_zero_2026_result_reconciliation_gate.json",
)


def mounted() -> bool:
    if not GATE_PATH.is_file() or not DATA_ROOT.is_dir():
        return False
    gate = read_json(GATE_PATH)
    manifest = (
        DATA_ROOT
        / "manifests/shadow/week_zero_2026_live_execution/sha256"
        / str(gate["acquisition_capture_identity"])
        / "week_zero_2026_live_execution_capture_manifest.json"
    )
    return manifest.is_file()


def tracked_digest() -> dict[str, str]:
    return {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in TRACKED_ARTIFACTS
        if (ROOT / relative).is_file()
    }


def isolated_data_root(destination: Path) -> Path:
    """Copy only the immutable inputs BAT-674 consumes into a throwaway data root."""
    gate = read_json(GATE_PATH)
    acquisition = str(gate["acquisition_capture_identity"])
    predecessor = str(gate["bound_predecessor_identities"]["bat665_capture_identity"])

    relatives: list[str] = []
    for identity in (acquisition, predecessor):
        relatives.append(
            f"manifests/shadow/week_zero_2026_live_execution/sha256/{identity}"
            "/week_zero_2026_live_execution_capture_manifest.json"
        )

    acquisition_manifest = read_json(DATA_ROOT / relatives[0])
    for row in acquisition_manifest.get("captures", []):
        if row.get("raw_relative_path"):
            relatives.append(str(row["raw_relative_path"]))

    forecast_gate = read_json(ROOT / "artifacts/shadow/prospective_2026_shadow_forecast_gate.json")
    forecast_manifest_relative = str(forecast_gate["manifest"]["relative_path"])
    relatives.append(forecast_manifest_relative)
    for payload in read_json(DATA_ROOT / forecast_manifest_relative)["payloads"]:
        relatives.append(str(payload["relative_path"]))

    for relative in relatives:
        source = DATA_ROOT / relative
        if not source.is_file():
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return destination


@unittest.skipUnless(mounted(), "the BAT-674 inputs are not mounted in this environment")
class IndependentReconstructionTests(unittest.TestCase):
    def test_every_committed_artifact_reconstructs_from_the_raw_official_bytes(self) -> None:
        self.assertEqual([], validate(repo_root=ROOT, data_root=DATA_ROOT))

    def test_validation_does_not_change_a_single_tracked_artifact(self) -> None:
        before = tracked_digest()
        validate(repo_root=ROOT, data_root=DATA_ROOT)
        self.assertEqual(before, tracked_digest())

    def test_the_corrected_capture_counts_are_materialized(self) -> None:
        summary = read_json(GATE_PATH)["official_capture_summary"]
        self.assertEqual(3, summary["capture_count"])
        self.assertEqual(2, summary["source_substitution_capture_count"])
        self.assertEqual(1, summary["admissible_final_capture_count"])
        self.assertEqual(8, summary["unique_official_final_count"])


@unittest.skipUnless(mounted(), "the BAT-674 inputs are not mounted in this environment")
class IsolatedDeterminismTests(unittest.TestCase):
    """Three serial rebuilds in an isolated root must produce identical identities."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="bat674-isolated-")
        self.addCleanup(self.temporary.cleanup)
        self.data_root = isolated_data_root(Path(self.temporary.name))
        self.gate = read_json(GATE_PATH)

    def rebuild(self) -> dict:
        return build_successor(
            repo_root=ROOT,
            data_root=self.data_root,
            execution_time_utc=str(self.gate["execution_time_utc"]),
            acquisition_capture_identity=str(self.gate["acquisition_capture_identity"]),
        )

    def test_three_serial_runs_produce_identical_identities(self) -> None:
        identities = [
            (
                bundle["gate"]["gate_identity"],
                bundle["scoring"]["payload_identity"],
                bundle["residual"]["payload_identity"],
                bundle["crosswalk"]["crosswalk_identity"],
                bundle["reconciliation_gate"]["gate_identity"],
                bundle["transition_ledger"]["ledger_identity"],
                bundle["capture_manifest"]["capture_identity"],
            )
            for bundle in (self.rebuild(), self.rebuild(), self.rebuild())
        ]
        self.assertEqual(identities[0], identities[1])
        self.assertEqual(identities[1], identities[2])

    def test_the_isolated_rebuild_agrees_with_the_committed_gate(self) -> None:
        self.assertEqual(self.gate["gate_identity"], self.rebuild()["gate"]["gate_identity"])

    def test_rebuilding_in_the_isolated_root_leaves_the_shared_mount_untouched(self) -> None:
        marker = (
            DATA_ROOT
            / "manifests/shadow/week_zero_2026_official_final_capture/sha256"
            / str(self.gate["bound_child_artifact_identities"]["official_capture_identity"])
            / "week_zero_2026_official_final_capture_manifest.json"
        )
        before = marker.read_bytes() if marker.is_file() else None
        self.rebuild()
        after = marker.read_bytes() if marker.is_file() else None
        self.assertEqual(before, after)

    def test_rebuilding_never_writes_a_tracked_repository_file(self) -> None:
        before = tracked_digest()
        self.rebuild()
        self.assertEqual(before, tracked_digest())

    def test_a_tampered_raw_capture_is_rejected_against_its_declared_sha(self) -> None:
        baseline = self.rebuild()["gate"]["gate_identity"]
        acquisition = read_json(
            self.data_root
            / "manifests/shadow/week_zero_2026_live_execution/sha256"
            / str(self.gate["acquisition_capture_identity"])
            / "week_zero_2026_live_execution_capture_manifest.json"
        )
        admissible = next(
            row
            for row in acquisition["captures"]
            if str(row["game_date"]) == "2026-08-29"
        )
        raw_path = self.data_root / str(admissible["raw_relative_path"])
        original = raw_path.read_bytes()
        self.addCleanup(raw_path.write_bytes, original)
        raw_path.write_bytes(original + b"<!-- tampered -->")
        with self.assertRaises(OfficialFinalScoringViolation):
            self.rebuild()
        raw_path.write_bytes(original)
        self.assertEqual(baseline, self.rebuild()["gate"]["gate_identity"])


@unittest.skipUnless(mounted(), "the BAT-674 inputs are not mounted in this environment")
class ChildBindingTests(unittest.TestCase):
    def test_the_gate_binds_the_on_disk_sha_of_every_child_file(self) -> None:
        gate = read_json(GATE_PATH)
        bound = gate["bound_child_artifact_identities"]
        expectations = {
            "contract_sha256": "configs/week_zero_2026_official_final_scoring_successor_contract.json",
            "core_module_sha256": "src/aggie_analytics/modeling/week_zero_official_final_scoring.py",
            "producer_sha256": "tools/build_week_zero_2026_official_final_scoring_successor.py",
            "validator_sha256": "tools/validate_week_zero_2026_official_final_scoring_successor.py",
            "temporal_audit_sha256": "artifacts/shadow/prospective_2026_shadow_temporal_audit_gate.json",
        }
        for key, relative in expectations.items():
            self.assertEqual(
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                bound[key],
                f"{key} is stale for {relative}",
            )

    def test_every_child_payload_identity_matches_its_committed_payload(self) -> None:
        gate = read_json(GATE_PATH)
        bound = gate["bound_child_artifact_identities"]
        pairs = {
            "scoring_payload_identity": (
                "artifacts/shadow/week_zero_2026_official_final_scoring_successor_payload.json",
                "payload_identity",
            ),
            "residual_payload_identity": (
                "artifacts/shadow/week_zero_2026_prospective_residual_successor_payload.json",
                "payload_identity",
            ),
            "crosswalk_identity": (
                "artifacts/shadow/week_zero_2026_cfbd_crosswalk.json",
                "crosswalk_identity",
            ),
            "reconciliation_gate_identity": (
                "artifacts/shadow/week_zero_2026_result_reconciliation_gate.json",
                "gate_identity",
            ),
            "transition_ledger_identity": (
                "artifacts/shadow/week_zero_2026_official_final_scoring_successor_state_transitions.json",
                "ledger_identity",
            ),
        }
        for key, (relative, field) in pairs.items():
            payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(payload[field], bound[key], f"{key} is not bound to {relative}")


if __name__ == "__main__":
    unittest.main()
