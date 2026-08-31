"""Independently reconstruct and validate the BAT-674 scoring successor.

This consumer never calls the network and never writes.  It rebuilds the capture
manifest, orientation proofs, outcomes, residuals, metrics, calibration bins and
transition ledger from the raw NCAA HTML plus the immutable predecessors, then
compares the reconstruction against every committed artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
for _entry in (ROOT / "tools", ROOT / "src"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from build_week_zero_2026_official_final_scoring_successor import (  # noqa: E402
    CROSSWALK_RELATIVE,
    GATE_RELATIVE,
    RECONCILIATION_RELATIVE,
    REPLAY_RELATIVE,
    RESIDUAL_RELATIVE,
    SCORING_RELATIVE,
    TRANSITIONS_RELATIVE,
    build_successor,
    read_json,
)

ARTIFACT_BY_KEY = {
    "gate": GATE_RELATIVE,
    "replay": REPLAY_RELATIVE,
    "scoring": SCORING_RELATIVE,
    "residual": RESIDUAL_RELATIVE,
    "transition_ledger": TRANSITIONS_RELATIVE,
    "crosswalk": CROSSWALK_RELATIVE,
    "reconciliation_gate": RECONCILIATION_RELATIVE,
}


def _first_difference(expected: Any, actual: Any, path: str = "") -> str | None:
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                return f"{path}/{key} is present in the committed artifact but not reconstructed"
            if key not in actual:
                return f"{path}/{key} was reconstructed but is absent from the committed artifact"
            difference = _first_difference(expected[key], actual[key], f"{path}/{key}")
            if difference:
                return difference
        return None
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return f"{path} length {len(actual)} != committed length {len(expected)}"
        for index, (left, right) in enumerate(zip(expected, actual)):
            difference = _first_difference(left, right, f"{path}[{index}]")
            if difference:
                return difference
        return None
    if expected != actual:
        return f"{path}: committed {expected!r} != reconstructed {actual!r}"
    return None


def validate(*, repo_root: Path, data_root: Path) -> list[str]:
    findings: list[str] = []

    gate_path = repo_root / GATE_RELATIVE
    if not gate_path.is_file():
        return [f"{GATE_RELATIVE} is missing"]
    committed_gate = read_json(gate_path)

    execution_time_utc = str(committed_gate["execution_time_utc"])
    acquisition_identity = str(committed_gate["acquisition_capture_identity"])

    rebuilt = build_successor(
        repo_root=repo_root,
        data_root=data_root,
        execution_time_utc=execution_time_utc,
        acquisition_capture_identity=acquisition_identity,
    )

    for key, relative in sorted(ARTIFACT_BY_KEY.items()):
        path = repo_root / relative
        if not path.is_file():
            findings.append(f"{relative} is missing")
            continue
        difference = _first_difference(read_json(path), rebuilt[key])
        if difference:
            findings.append(f"{relative} does not reconstruct: {difference}")

    manifest_relative = str(rebuilt["capture_manifest_relative_path"])
    manifest_path = data_root / manifest_relative
    if not manifest_path.is_file():
        findings.append(f"external capture manifest {manifest_relative} is missing")
    else:
        difference = _first_difference(read_json(manifest_path), rebuilt["capture_manifest"])
        if difference:
            findings.append(f"{manifest_relative} does not reconstruct: {difference}")

    bound = committed_gate.get("bound_child_artifact_identities", {})
    if bound.get("official_capture_manifest_relative_path") != manifest_relative:
        findings.append("the gate does not bind the reconstructed capture manifest path")

    summary = committed_gate.get("official_capture_summary", {})
    if summary.get("capture_count") != 3:
        findings.append("capture_count must remain 3")
    if summary.get("source_substitution_capture_count") != 2:
        findings.append("source_substitution_capture_count must remain 2")
    if summary.get("admissible_final_capture_count") != 1:
        findings.append("admissible_final_capture_count must remain 1")
    if summary.get("unique_official_final_count") != 8:
        findings.append("unique_official_final_count must remain 8")

    for proof in rebuilt["scoring"]["orientation_proofs"]:
        if proof["proof_state"] == "ORIENTATION_PROVEN" and not proof["final_capture_after_kickoff"]:
            findings.append(
                f"contest {proof['ncaa_contest_id']} was proven without a post-kickoff capture"
            )

    scored_identities = {row["scoring_row_identity"] for row in rebuilt["scoring"]["scored_rows"]}
    for row in rebuilt["residual"]["admitted_rows"]:
        if row["scoring_row_identity"] not in scored_identities:
            findings.append("a residual row is not backed by a scored row")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()

    findings = validate(repo_root=args.repo_root.resolve(), data_root=args.data_root.resolve())
    print(
        json.dumps(
            {
                "finding_count": len(findings),
                "findings": findings,
                "result": "PASS_INDEPENDENT_RECONSTRUCTION"
                if not findings
                else "FAIL_INDEPENDENT_RECONSTRUCTION",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
