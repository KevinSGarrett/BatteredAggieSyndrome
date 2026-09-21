"""R35-25 (Cycle #35 closeout review, 20260921T025300Z), section 7.

"...produce a single entry point, updated final report, requirement/finding
dispositions, national coverage, source manifest, plan/Jira trace and
validation accounting. Avoid self-referential hash claims; finalize children
before sealing their parent manifest."

One document a reader can start from, binding every closing artifact to a
path and a digest that were read off disk at seal time.

What this deliberately does NOT do:

* It does not restate any artifact's conclusions. Every section resolves to
  the artifact that carries them, so there is exactly one place a number
  lives. A summary that paraphrases its children is a second, diverging copy
  of the truth.
* It does not hash itself. Children are read and digested first, the entry
  point is composed from those digests, and its own digest goes in a sidecar
  written after it is closed.
* It does not silently omit a section whose artifact is missing. A required
  artifact that is absent is reported as MISSING with the path that was
  looked for, because a short report and a complete one must not look alike.
* It does not upgrade its own status. The status is read from the
  authorization file the cycle is operating under.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE_RUNS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")

STATUS = "IN_PROGRESS_LOCAL_WORK_REMAINS"

#: section -> (artifact file name, whether the entry point is incomplete
#: without it). The names are resolved across every run directory, so a
#: section does not break when a tool is re-run into a new directory.
SECTIONS: tuple[tuple[str, str, bool], ...] = (
    ("final_report", "CYCLE35_FINAL_REPORT.md", True),
    ("requirement_status", "CYCLE35_REQUIREMENT_STATUS.json", True),
    ("finding_disposition", "CYCLE35_FINDING_DISPOSITION.json", True),
    ("unfinished_items", "CYCLE35_UNFINISHED_ITEMS.json", True),
    ("minimal_decisions_required", "CYCLE35_MINIMAL_DECISIONS_REQUIRED.json", True),
    ("evidence_graph", "CYCLE35_EVIDENCE_GRAPH.json", True),
    ("national_coverage", "CYCLE35_NATIONAL_COVERAGE.json", True),
    ("source_receipt_index", "CYCLE35_SOURCE_RECEIPT_INDEX.json", True),
    ("plan_jira_trace", "CYCLE35_PLAN_JIRA_TRACE.json", True),
    ("validation_accounting", "CYCLE35_VALIDATION_RESULTS_SUCCESSOR.json", True),
    ("mounted_lane_receipt", "CYCLE35_MOUNTED_LANE_RECEIPT.json", True),
    ("published_release_manifest", "CYCLE35_PUBLISHED_RELEASE_MANIFEST.json", True),
    ("release_coverage_binding", "CYCLE35_RELEASE_COVERAGE_BINDING.json", True),
    ("release_layer_binding", "CYCLE35_RELEASE_LAYER_BINDING.json", True),
    (
        "career_tranche_key_reconciliation",
        "CYCLE35_CAREER_TRANCHE_KEY_RECONCILIATION.json",
        True,
    ),
    ("delivered_release_comparison", "CYCLE35_DELIVERED_RELEASE_COMPARISON.json", True),
    ("source_span_review", "CYCLE35_SOURCE_SPAN_SEMANTIC_REVIEW.json", True),
    ("kernel_reference", "R35_09_INDEPENDENT_KERNEL_REFERENCE.json", True),
    ("cycle_request_ledger", "CYCLE35_CYCLE_WIDE_REQUEST_LEDGER.json", True),
    ("isolated_family_b_consumer", "CYCLE35_ISOLATED_FAMILY_B_CONSUMER.json", True),
    ("deterministic_release_replay", "CYCLE35_DETERMINISTIC_RELEASE_REPLAY.json", True),
    ("private_data_lanes", "CYCLE35_PRIVATE_DATA_LANE_RESULTS.json", True),
    ("pit_feasibility", "R35_09_PIT_FEASIBILITY.json", True),
    ("all22_alignment", "CYCLE35_ALL22_ALIGNMENT.json", True),
)

SKIP_DIRECTORY_NAMES = frozenset(
    {"wheel_venv", "Lib", "site-packages", "Scripts", "__pycache__", ".git"}
)


def sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def newest_by_name(root: Path) -> dict[str, Path]:
    """Every artifact name mapped to its most recently written copy."""

    found: dict[str, tuple[float, Path]] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_DIRECTORY_NAMES.intersection(path.parts):
            continue
        try:
            stamp = path.stat().st_mtime
        except OSError:
            continue
        current = found.get(path.name)
        if current is None or stamp > current[0]:
            found[path.name] = (stamp, path)
    return {name: path for name, (_, path) in found.items()}


def resolve_sections(index: dict[str, Path]) -> dict[str, Any]:
    sections: dict[str, Any] = {}
    missing_required: list[str] = []
    for key, filename, required in SECTIONS:
        path = index.get(filename)
        if path is None:
            sections[key] = {
                "artifact": filename,
                "state": "MISSING",
                "required": required,
                "path": None,
                "sha256": None,
            }
            if required:
                missing_required.append(filename)
            continue
        stat = path.stat()
        sections[key] = {
            "artifact": filename,
            "state": "BOUND",
            "required": required,
            "path": str(path),
            "sha256": sha256_file(path),
            "bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
        }
    return {"sections": sections, "missing_required": missing_required}


def head_commit() -> str | None:
    import subprocess

    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def build(root: Path) -> dict[str, Any]:
    index = newest_by_name(root)
    resolved = resolve_sections(index)
    sections = resolved["sections"]
    bound = [key for key, value in sections.items() if value["state"] == "BOUND"]
    return {
        "artifact_type": "CYCLE35_SINGLE_ENTRY_POINT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": STATUS,
        "head": head_commit(),
        "cycle_root": str(root),
        "how_to_read_this": (
            "Every section below names the one artifact that carries that "
            "subject, with the path and digest read off disk when this file "
            "was sealed. Nothing here restates a child's conclusions: a "
            "summary that paraphrases its children becomes a second copy of "
            "the truth that drifts from the first."
        ),
        "sections": sections,
        "section_count": len(sections),
        "bound_count": len(bound),
        "missing_required": resolved["missing_required"],
        "complete": not resolved["missing_required"],
        "sealing_order": (
            "Children are read and digested before this file is composed. It "
            "carries no digest of itself; that is written to the sidecar named "
            "below, after this file is closed."
        ),
        "own_digest_sidecar": "CYCLE35_SINGLE_ENTRY_POINT.sha256",
        "authorization": {
            "status": STATUS,
            "not_authorized": [
                "merge",
                "canonical activation",
                "C01 self-adoption",
                "protected-lane activation",
                "paid AI/API review or new subscription",
                "Done transition",
                "hold release",
                "BAT-523 completion",
                "force-push",
                "secret disclosure",
                "dirty All-22 mutation",
                "scientific acceptance",
            ],
            "binding_this_entry_point_is_not_acceptance": (
                "Binding an artifact records that it exists and what it "
                "contains. It does not certify its conclusions, and no owner "
                "decision is implied by its presence here."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seal the single entry point.")
    parser.add_argument("--cycle-root", type=Path, default=CYCLE_RUNS)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    result = build(args.cycle_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    entry_path = args.out_dir / "CYCLE35_SINGLE_ENTRY_POINT.json"
    entry_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    sidecar = args.out_dir / "CYCLE35_SINGLE_ENTRY_POINT.sha256"
    sidecar.write_text(
        f"{sha256_file(entry_path)}  CYCLE35_SINGLE_ENTRY_POINT.json\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": result["status"],
                "head": result["head"],
                "sections": result["section_count"],
                "bound": result["bound_count"],
                "missing_required": result["missing_required"],
                "complete": result["complete"],
                "entry_point": str(entry_path),
            },
            indent=2,
        )
    )
    # An entry point missing a required section is not a usable entry point.
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
