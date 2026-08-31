"""Materialize the final, post-merge Cycle #22 completion report.

The pre-merge report is immutable historical evidence: it recorded a dirty tree with
no pull request and no merge.  This producer classifies that report as historical and
derives the final report from the merged BAT-674 scoring gate rather than restating
metrics by hand, so the report cannot drift from the authority it describes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PRE_MERGE_REPORT = "artifacts/shadow/cycle22_week_zero_completion_report.json"
FINAL_REPORT = "artifacts/shadow/cycle22_week_zero_final_report.json"
SCORING_GATE = "artifacts/shadow/week_zero_2026_official_final_scoring_successor_gate.json"

BAT675_MERGE_SHA = "e29a8b0ff6dd5e004d9786f73d3da50d6ab0bd0c"
BAT674_MERGE_SHA = "140dba42a2593b56985a375cdcc550667cfaf56d"
CYCLE21_ENDING_SHA = "f7b68d776a2d7c602ac6ae003f23fbac8d0f2820"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_identity(payload: dict[str, Any], omit: str) -> str:
    reduced = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(reduced, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline=""
    )


def commit_exists(repo_root: Path, sha: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
    )
    return result.returncode == 0


def classify_pre_merge_report_as_historical(repo_root: Path) -> dict[str, Any]:
    path = repo_root / PRE_MERGE_REPORT
    report = read_json(path)
    report["supersession"] = {
        "historical_attempt": True,
        "current_authority": False,
        "reason": (
            "This report was generated before any Cycle #22 pull request existed and "
            "recorded a dirty tree, uncorrected scoring denominators and an unmerged "
            "state."
        ),
        "superseded_by_relative_path": FINAL_REPORT,
        "superseded_by_material_merge_sha": BAT674_MERGE_SHA,
    }
    write_json(path, report)
    return report


def build_final_report(repo_root: Path) -> dict[str, Any]:
    gate_path = repo_root / SCORING_GATE
    gate = read_json(gate_path)
    candidates = gate["metrics_by_candidate"]

    metrics = {}
    for name, candidate in sorted(candidates.items()):
        metrics[name] = {
            "predeclared_eligible_frozen_opportunity_count": candidate[
                "predeclared_eligible_frozen_opportunity_count"
            ],
            "scored_row_count": candidate["scored_row_count"],
            "pending_row_count": candidate["pending_row_count"],
            "temporal_exclusion_count": candidate["temporal_exclusion_count"],
            "unsupported_count": candidate["unsupported_count"],
            "missed_cutoff_with_no_forecast_count": candidate[
                "missed_cutoff_with_no_forecast_count"
            ],
            "coverage": candidate["coverage"],
            "abstention_count": candidate["abstention_count"],
            "brier_score": candidate["brier_score"],
            "log_loss": candidate["log_loss"],
            "mean_absolute_residual": candidate["mean_absolute_residual"],
            "directional_row_count": candidate["directional_row_count"],
            "directional_accuracy": candidate["directional_accuracy"],
            "classification_threshold_behaviour": candidate[
                "classification_threshold_behaviour"
            ],
            "populated_calibration_bins": [
                bin_row
                for bin_row in candidate["calibration_bins"]
                if bin_row["row_count"] > 0
            ],
        }

    report: dict[str, Any] = {
        "artifact_type": "CYCLE22_WEEK_ZERO_FINAL_REPORT",
        "schema_version": "aggie.shadow.cycle22_week_zero_final_report.v1",
        "cycle": 22,
        "classification": "POST_MERGE_FINAL",
        "predecessor_cycle_ending_sha": CYCLE21_ENDING_SHA,
        "material_merges": [
            {
                "jira_key": "BAT-675",
                "pull_request": 647,
                "merge_sha": BAT675_MERGE_SHA,
                "scope": (
                    "Checkout-authority pin validation, second-pass read-only purity and "
                    "BAT-523 comment-ledger supersession hardening"
                ),
            },
            {
                "jira_key": "BAT-674",
                "pull_request": 648,
                "merge_sha": BAT674_MERGE_SHA,
                "scope": (
                    "Corrected Week Zero 2026 official-final capture semantics, orientation "
                    "proof, identity binding, metric denominators and independent "
                    "reconstruction"
                ),
            },
        ],
        "cycle_ending_sha": BAT674_MERGE_SHA,
        "official_capture_summary": gate["official_capture_summary"],
        "contest_state_counts": gate["contest_state_counts"],
        "forecast_state_counts": gate["forecast_state_counts"],
        "metrics_by_candidate": metrics,
        "pooled_model_row_diagnostics": gate["pooled_model_row_diagnostics"],
        "unique_contest_outcome_diagnostics": gate["unique_contest_outcome_diagnostics"],
        "bound_authority": {
            "scoring_gate_relative_path": SCORING_GATE,
            "scoring_gate_identity": gate["gate_identity"],
            "scoring_gate_sha256": file_sha256(gate_path),
            "predecessor_bat665_gate_identity": gate["bound_predecessor_identities"][
                "bat665_gate_identity"
            ],
            "acquisition_capture_identity": gate["acquisition_capture_identity"],
        },
        "superseded_pre_merge_report": {
            "relative_path": PRE_MERGE_REPORT,
            "classification": "HISTORICAL_PRE_MERGE",
        },
        "governance": {
            "lane": gate["lane"],
            "protected_lane": gate["protected_lane"],
            "bat401_state": "DONE_RETAIN_PROTECTED_LANE_BLOCKED",
            "bat429_state": "BLOCKED",
            "bat523_state": "IN_PROGRESS",
            "gap005_state": "OPEN",
            "protected_seasons_sealed": ["2024", "2025"],
        },
        "scientific_nonclaims": gate["scientific_nonclaims"],
    }
    report["report_identity"] = canonical_identity(report, "report_identity")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    for sha in (BAT675_MERGE_SHA, BAT674_MERGE_SHA):
        if not commit_exists(repo_root, sha):
            raise SystemExit(f"MATERIAL_MERGE_COMMIT_ABSENT:{sha}")

    classify_pre_merge_report_as_historical(repo_root)
    report = build_final_report(repo_root)
    write_json(repo_root / FINAL_REPORT, report)
    print(
        json.dumps(
            {
                "final_report_relative_path": FINAL_REPORT,
                "report_identity": report["report_identity"],
                "cycle_ending_sha": report["cycle_ending_sha"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
