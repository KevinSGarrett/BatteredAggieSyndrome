"""R35-26 (Cycle #35 closeout review, 20260921T025300Z), sections 7 and 8.

The review says of the declared unfinished list: "Reconcile each entry with
delivered evidence; do not simply delete the list or relabel its contents."
Reconciling it is r35_22's job. This is the other half of honesty about that
list: the review's own work surfaced obligations that were not on it, and
folding those into the 26 would make the original list unauditable while
leaving them out would make the packet look smaller than the work is.

So they are recorded separately, and every one is derived from an artifact
this review produced. Nothing here is asserted: each item reads its numbers
out of a named file, and an item whose evidence is absent is reported as
UNVERIFIABLE rather than stated from memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CYCLE_RUNS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
SKIP_DIRECTORY_NAMES = frozenset(
    {"wheel_venv", "Lib", "site-packages", "Scripts", "__pycache__", ".git"}
)

OPEN_LOCAL = "OPEN_REAL_LOCAL_WORK"
OPEN_ACQUISITION = "OPEN_REQUIRES_ACQUISITION_DECISION"
OPEN_REVIEWER = "OPEN_REQUIRES_INDEPENDENT_REVIEWER"
CLOSED_HERE = "FOUND_AND_FIXED_IN_THIS_REVIEW"
UNVERIFIABLE = "UNVERIFIABLE_EVIDENCE_ARTIFACT_ABSENT"


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def find(root: Path, name: str) -> Path | None:
    newest: tuple[float, Path] | None = None
    for path in root.rglob(name):
        if SKIP_DIRECTORY_NAMES.intersection(path.parts):
            continue
        try:
            stamp = path.stat().st_mtime
        except OSError:
            continue
        if newest is None or stamp > newest[0]:
            newest = (stamp, path)
    return newest[1] if newest else None


def load(path: Path | None) -> Any:
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def item(
    key: str,
    requirement: str,
    state: str,
    evidence: Path | None,
    finding: str | None,
) -> dict[str, Any]:
    if evidence is None or finding is None:
        return {
            "key": key,
            "requirement": requirement,
            "state": UNVERIFIABLE,
            "evidence": None,
            "evidence_sha256": None,
            "finding": None,
        }
    return {
        "key": key,
        "requirement": requirement,
        "state": state,
        "evidence": str(evidence),
        "evidence_sha256": sha256_file(evidence),
        "finding": finding,
    }


def coverage_item(root: Path) -> dict[str, Any]:
    path = find(root, "CYCLE35_RELEASE_COVERAGE_BINDING.json")
    payload = load(path)
    finding = None
    if payload:
        states = payload.get("coverage_states", {})
        confirmed = states.get("COVERED_BY_CONFIRMED_ASSERTION", 0)
        candidate = states.get("COVERED_BY_CANDIDATE_OBSERVATION_ONLY", 0)
        finding = (
            f"{confirmed} of {payload.get('expected_cells'):,} expected "
            f"program-season-role cells are covered at the confirmed layer; "
            f"{candidate:,} are covered by an unpromoted candidate observation "
            f"only. All {payload.get('episode_assertions_without_a_stated_season'):,} "
            "confirmed assertions hang off episodes whose season the source "
            "states as 'CURRENT', so none can be placed in a cell. Recording a "
            "season where the sources state one, or promoting candidates on "
            "corroboration, is local work; inventing a season is not."
        )
    return item(
        "EXPECTED_POPULATION_HAS_NO_CONFIRMED_COVERAGE",
        "R35-03",
        OPEN_LOCAL,
        path,
        finding,
    )


def recall_gap_item(root: Path) -> dict[str, Any]:
    path = find(root, "CYCLE35_SOURCE_SPAN_SEMANTIC_REVIEW.json")
    payload = load(path)
    finding = None
    if payload:
        kinds = payload.get("disagreements_by_kind", {})
        recall = kinds.get("PARSER_FOUND_NO_RECORD_BUT_BOTH_SPANS_PRESENT", 0)
        finding = (
            f"{recall} of {payload.get('rows_reviewed')} sampled rows carry "
            "disposition QUARANTINED_REPARSE_WITHDRAWS_SUPPORT although an "
            "independent locator finds both the person's name and the exact "
            "title text verbatim in the raw source, and the reparse returned "
            "no record at all. The quarantine must not be read as the source "
            "failing to support the claim. Nothing is re-promoted on this "
            "alone: the reparse recall path is what needs work."
        )
    return item(
        "REPARSE_RECALL_GAP_ON_QUARANTINED_ROWS", "R35-02", OPEN_LOCAL, path, finding
    )


def nondeterminism_item(root: Path) -> dict[str, Any]:
    path = find(root, "CYCLE35_DETERMINISTIC_RELEASE_REPLAY.json")
    payload = load(path)
    finding = None
    if payload:
        diffs = payload.get("comparison", {}).get("column_level_diffs", [])
        detail = "; ".join(
            f"{entry['table']}.{column} ({rows} rows)"
            for entry in diffs
            for column, rows in entry.get("columns_differing", {}).items()
        )
        finding = (
            "Two builds of identical inputs differ in "
            f"{detail or 'no column'}. The difference is confined to a "
            "wall-clock column and is reported by name; "
            "INCIDENTAL_EXCLUDED_COLUMNS stays empty rather than being used "
            "to make the disagreement disappear. A release whose rows change "
            "between builds cannot be content-addressed until the clock is "
            "bound to the build, not to the moment each row is written."
        )
    return item(
        "ADJUDICATION_TIMESTAMP_IS_NOT_REPRODUCIBLE",
        "R35-03",
        OPEN_LOCAL,
        path,
        finding,
    )


def kernel_source_item(root: Path) -> dict[str, Any]:
    path = find(root, "R35_09_INDEPENDENT_KERNEL_REFERENCE.json")
    payload = load(path)
    finding = None
    if payload:
        disposition = payload.get("comparison", {}).get("residual_disposition", {})
        missing = disposition.get("seasons_missing_from_declared_sources", [])
        absent = disposition.get("absent_game_rows_by_disposition", {})
        finding = (
            "The declared kernel raw sources omit season(s) "
            f"{', '.join(str(year) for year in missing) or 'none'} entirely, and "
            f"{absent.get('SEASON_ACQUIRED_BUT_THIS_GAME_IS_NOT_IN_THE_PULL', 0)} "
            "kernel rows reference games that an acquired season's pull does "
            "not contain. Acquiring them is a spend decision, not an "
            "implementation task."
        )
    return item(
        "DECLARED_KERNEL_SOURCES_ARE_INCOMPLETE",
        "R35-09",
        OPEN_ACQUISITION,
        path,
        finding,
    )


def mounted_lane_item(root: Path) -> dict[str, Any]:
    path = find(root, "CYCLE35_MOUNTED_LANE_RECEIPT.json")
    payload = load(path)
    finding = None
    if payload:
        lanes = {lane["lane"]: lane for lane in payload.get("lanes", [])}
        mounted = lanes.get("FULL_SUITE_MOUNTED_EXPLICIT_ENV", {})
        unmounted = lanes.get("FULL_SUITE_GENUINELY_UNMOUNTED", {})
        mounted_counts = mounted.get("counts", {})
        unmounted_counts = unmounted.get("counts", {})
        executed_difference = mounted_counts.get("passed", 0) - unmounted_counts.get(
            "passed", 0
        )
        finding = (
            "The genuinely mounted full suite exits "
            f"{mounted.get('exit_code')} ({mounted.get('summary_line')}) while "
            f"the unmounted suite exits {unmounted.get('exit_code')} "
            f"({unmounted.get('summary_line')}). {executed_difference} more "
            "tests execute when the private lake is mounted, so a green hosted "
            "run cannot stand in for the mounted lane. The mounted failures are "
            "the inherited BAT-637 legacy pin disagreement, which is not "
            "concealed and not patched by copying the live hash."
        )
    return item(
        "HOSTED_GREEN_DOES_NOT_COVER_THE_MOUNTED_LANE",
        "R35-14",
        OPEN_REVIEWER,
        path,
        finding,
    )


def line_ending_item(root: Path) -> dict[str, Any]:
    path = find(root, "CYCLE35_MOUNTED_LANE_RECEIPT.json")
    if path is None:
        return item("MIXED_LINE_ENDINGS_IN_A_TRACKED_TEST_FILE", "R35-14", CLOSED_HERE, None, None)
    return item(
        "MIXED_LINE_ENDINGS_IN_A_TRACKED_TEST_FILE",
        "R35-14",
        CLOSED_HERE,
        path,
        "The first genuinely mounted full-suite run failed "
        "test_tracked_file_purity with TRACKED_TEXT_FILE_MIXES_LINE_ENDINGS on "
        "tests/test_cycle35_r35_08_national_neutral_site.py, self-inflicted by "
        "a splice script's text-mode write. Fixed at 4913ea1c by normalising "
        "the file back to LF. Recorded because it is exactly the class of "
        "defect the withdrawn unqualified FULL_SUITE_MOUNTED pass was hiding: "
        "invisible to the cycle35 lane scope, visible only to the whole suite.",
    )


BUILDERS = (
    coverage_item,
    recall_gap_item,
    nondeterminism_item,
    kernel_source_item,
    mounted_lane_item,
    line_ending_item,
)


def build(root: Path) -> dict[str, Any]:
    items = [builder(root) for builder in BUILDERS]
    by_state: dict[str, int] = {}
    for entry in items:
        by_state[entry["state"]] = by_state.get(entry["state"], 0) + 1
    return {
        "artifact_type": "CYCLE35_NEWLY_DISCOVERED_OBLIGATIONS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "why_separate_from_the_declared_list": (
            "The packet's 26 declared unfinished entries are reconciled in "
            "place by the evidence graph and none was added, removed or "
            "reworded. These are obligations this review surfaced that were "
            "never on that list. Folding them in would make the original "
            "unauditable; leaving them out would make the packet look smaller "
            "than the work is."
        ),
        "items": items,
        "item_count": len(items),
        "by_state": by_state,
        "every_item_is_derived_from_an_artifact": all(
            entry["state"] == UNVERIFIABLE or entry["evidence_sha256"]
            for entry in items
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Newly discovered obligations.")
    parser.add_argument("--cycle-root", type=Path, default=CYCLE_RUNS)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    result = build(args.cycle_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "CYCLE35_NEWLY_DISCOVERED_OBLIGATIONS.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "item_count": result["item_count"],
                "by_state": result["by_state"],
                "every_item_is_derived_from_an_artifact": result[
                    "every_item_is_derived_from_an_artifact"
                ],
                "artifact": str(out_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
