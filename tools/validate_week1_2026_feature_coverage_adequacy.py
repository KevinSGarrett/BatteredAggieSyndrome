"""Independently reconstruct and validate the Week 1 2026 adequacy gate.

The validator recomputes every contest and candidate adequacy row from the
committed spine payloads, compares the reconstruction to the committed adequacy
payloads, and rechecks the gate. It never reaches the network and never writes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.national_foundation_reconciliation import sha256_file  # noqa: E402
from aggie_analytics.data.week1_2026_feature_coverage_adequacy import (  # noqa: E402
    CANDIDATE_PAYLOAD_NAME,
    CONTEST_PAYLOAD_NAME,
    GATE_RELATIVE,
    Week1AdequacyViolation,
    build_adequacy_rows,
    read_jsonl,
    validate_artifact,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_week1_2026_feature_coverage_adequacy import load_inputs  # noqa: E402


def reconstruct(repo_root: Path, data_root: Path) -> dict[str, Any]:
    gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
    inputs = load_inputs(repo_root, data_root)
    contest_rows, candidate_rows = build_adequacy_rows(
        contract=inputs["contract"], rows=inputs["rows"], cells=inputs["cells"]
    )
    manifest = json.loads(
        (data_root / gate["manifest"]["relative_path"]).read_text(encoding="utf-8-sig")
    )
    committed = {
        payload["name"]: read_jsonl(data_root / payload["relative_path"])
        for payload in manifest["payloads"]
    }
    findings: list[str] = []
    for name, reconstructed in (
        (CONTEST_PAYLOAD_NAME, contest_rows),
        (CANDIDATE_PAYLOAD_NAME, candidate_rows),
    ):
        published = committed.get(name)
        if published is None:
            findings.append(f"committed payload absent: {name}")
            continue
        if published != reconstructed:
            findings.append(
                f"{name}: reconstruction does not match the committed payload"
            )
    if (
        gate["bound_predecessors"]["feature_spine_gate_identity"]
        != inputs["bound_predecessors"]["feature_spine_gate_identity"]
    ):
        findings.append(
            "the gate is bound to a different feature spine than the one on disk"
        )
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    )
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)
    try:
        reconstruction = reconstruct(repo_root, data_root)
        artifact = validate_artifact(repo_root=repo_root, data_root=data_root)
    except Week1AdequacyViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    report = {
        "result": "PASS"
        if reconstruction["result"] == "PASS" and artifact["result"] == "PASS"
        else "FAIL",
        "independent_reconstruction": reconstruction,
        "artifact_validation": artifact,
        "gate_sha256": sha256_file(repo_root / GATE_RELATIVE),
        "forecast_produced": False,
        "network_access": "NONE",
        "writes_performed": "NONE",
    }
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
