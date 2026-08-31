"""Independently reconstruct and validate the Week 1 2026 current-feature spine.

The validator never reaches the network and never writes. It rebuilds every spine
row and admission cell from the immutable captures and predecessor gates, compares
the reconstruction to the committed payloads byte for byte, and then rechecks the
published gate against the same evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.national_foundation_reconciliation import sha256_file  # noqa: E402
from aggie_analytics.data.week1_2026_current_feature_spine import (  # noqa: E402
    CELL_PAYLOAD_NAME,
    GATE_RELATIVE,
    ROW_PAYLOAD_NAME,
    Week1FeatureSpineViolation,
    assert_future_append_invariance,
    build_spine_rows,
    index_rankings,
    read_jsonl,
    validate_artifact,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_week1_2026_current_feature_spine import load_inputs  # noqa: E402


def reconstruct(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Rebuild the payloads from raw evidence at the gate's own snapshot issuance."""

    gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
    snapshot = gate["snapshot_issuance_utc"]
    inputs = load_inputs(repo_root, data_root)
    rankings = index_rankings(
        inputs["poll"]["entries"], inputs["participants"], inputs["aliases"]
    )
    rows, cells = build_spine_rows(
        contract=inputs["contract"],
        contests=inputs["contests"],
        participants=inputs["participants"],
        rankings=rankings,
        ranking_capture=inputs["ranking_capture"],
        publication_authority_text=inputs["poll"]["publication_authority_text"],
        week_zero=inputs["week_zero"],
        weather=inputs["weather"],
        forecast_periods=inputs["forecast_periods"],
        prior_evidence=inputs["prior_evidence"],
        snapshot_issuance=datetime.fromisoformat(snapshot.replace("Z", "+00:00")),
    )
    assert_future_append_invariance(rows, cells)

    manifest = json.loads(
        (data_root / gate["manifest"]["relative_path"]).read_text(encoding="utf-8-sig")
    )
    committed: dict[str, list[dict[str, Any]]] = {}
    for payload in manifest["payloads"]:
        committed[payload["name"]] = read_jsonl(data_root / payload["relative_path"])

    findings: list[str] = []
    for name, reconstructed in ((ROW_PAYLOAD_NAME, rows), (CELL_PAYLOAD_NAME, cells)):
        published = committed.get(name)
        if published is None:
            findings.append(f"committed payload absent: {name}")
            continue
        if len(published) != len(reconstructed):
            findings.append(
                f"{name}: reconstructed {len(reconstructed)} rows against {len(published)} committed"
            )
            continue
        for index, (left, right) in enumerate(zip(published, reconstructed)):
            if left != right:
                findings.append(f"{name}: row {index} does not reconstruct")
                break
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""))
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)
    try:
        reconstruction = reconstruct(repo_root, data_root)
        artifact = validate_artifact(repo_root=repo_root, data_root=data_root)
    except Week1FeatureSpineViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    report = {
        "result": "PASS"
        if reconstruction["result"] == "PASS" and artifact["result"] == "PASS"
        else "FAIL",
        "independent_reconstruction": reconstruction,
        "artifact_validation": artifact,
        "gate_sha256": sha256_file(repo_root / GATE_RELATIVE),
        "network_access": "NONE",
        "writes_performed": "NONE",
    }
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
