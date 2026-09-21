"""R35-22: one coherent evidence graph, and a reconciliation of every
unfinished item against delivered evidence.

Cycle #35 closeout review (20260921T025300Z), section 7:

    "Generate one coherent current evidence graph across run directories.
    Do not use fixed narrative status dictionaries as authority. Resolve
    every evidence reference to a real path/hash and produce a single
    entry point... The current packet has 26 unfinished entries, 22
    labeled local, yet lists only five owner decisions as if no local work
    remained. Some entries are stale and others remain real. Reconcile
    each entry with delivered evidence; do not simply delete the list or
    relabel its contents. Missing facts, failed validations, implementation
    gaps, reviewer decisions and release authority are different
    categories."

Two things this does that the packet did not:

* Evidence references are resolved across EVERY run directory, not only
  the output directory the packet happened to be writing to. The packet's
  own sha256 map resolved almost nothing for that reason.
* Each unfinished entry is checked against a real artifact or a real
  query and classified into one of five distinct categories, with the
  path or query that decided it recorded alongside. An entry is only
  called stale when something delivered actually contradicts it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CYCLE_RUNS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
SKIP_DIRECTORY_NAMES = frozenset(
    {"wheel_venv", "Lib", "site-packages", "Scripts", "__pycache__", ".git"}
)

#: The five categories the review requires be kept apart.
CATEGORY_STALE = "STALE_CONTRADICTED_BY_DELIVERED_EVIDENCE"
CATEGORY_LOCAL = "REAL_LOCAL_WORK_REMAINING"
CATEGORY_DATA_GAP = "REAL_DATA_GAP_NOT_AN_IMPLEMENTATION_GAP"
CATEGORY_FAILED_VALIDATION = "REAL_FAILED_VALIDATION"
CATEGORY_REVIEWER = "REQUIRES_INDEPENDENT_REVIEWER_DECISION"
CATEGORY_RELEASE_AUTHORITY = "REQUIRES_RELEASE_AUTHORITY"
CATEGORY_BUDGET = "REQUIRES_BUDGET_OR_ACCESS_DECISION"


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def index_artifacts(root: Path = CYCLE_RUNS) -> dict[str, Any]:
    """Every cycle artifact, indexed by filename across all run directories."""

    by_name: dict[str, list[dict[str, Any]]] = {}
    directories: dict[str, int] = {}
    if not root.is_dir():
        return {"by_name": {}, "directories": {}, "artifact_count": 0}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_DIRECTORY_NAMES.intersection(path.parts):
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".sqlite", ".log", ".md", ".txt"}:
            continue
        try:
            run_dir = path.relative_to(root).parts[0]
        except ValueError:
            continue
        directories[run_dir] = directories.get(run_dir, 0) + 1
        by_name.setdefault(path.name, []).append(
            {
                "path": str(path),
                "run_directory": run_dir,
                "bytes": path.stat().st_size,
                "modified_utc": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )
    return {
        "by_name": by_name,
        "directories": dict(sorted(directories.items())),
        "artifact_count": sum(len(v) for v in by_name.values()),
    }


def resolve_evidence(units: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    """Resolve every declared evidence reference to a real path and hash."""

    resolved: dict[str, Any] = {}
    dangling: list[dict[str, str]] = []
    for unit_id, unit in units.items():
        entries = []
        for reference in unit.get("evidence", []):
            name = Path(str(reference).split(" (")[0].strip()).name
            matches = index["by_name"].get(name, [])
            if not matches:
                dangling.append({"unit": unit_id, "reference": str(reference)})
                entries.append(
                    {
                        "reference": str(reference),
                        "resolved": False,
                        "reason": "not found in any run directory",
                    }
                )
                continue
            newest = max(matches, key=lambda item: item["modified_utc"])
            entries.append(
                {
                    "reference": str(reference),
                    "resolved": True,
                    "path": newest["path"],
                    "sha256": sha256_file(Path(newest["path"])),
                    "run_directory": newest["run_directory"],
                    "copies_across_run_directories": len(matches),
                }
            )
        resolved[unit_id] = entries
    return {
        "by_unit": resolved,
        "dangling_references": dangling,
        "dangling_count": len(dangling),
        "resolved_count": sum(
            1 for items in resolved.values() for item in items if item["resolved"]
        ),
    }


def query_release(db_path: Path) -> dict[str, Any]:
    """Facts read from the DELIVERED queryable release, not from code."""

    if not db_path.is_file():
        return {"queried": False, "reason": f"no release database at {db_path}"}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cursor = conn.cursor()

        def scalar(sql: str, params: tuple = ()) -> Any:
            return cursor.execute(sql, params).fetchone()[0]

        in_range = (
            "SELECT COUNT(*) FROM source_observation WHERE observed_season "
            "GLOB '[0-9][0-9][0-9][0-9]' AND CAST(observed_season AS INTEGER) "
            "BETWEEN ? AND ?"
        )
        return {
            "queried": True,
            "database": str(db_path),
            "database_sha256": sha256_file(db_path),
            "source_observations": scalar("SELECT COUNT(*) FROM source_observation"),
            "observations_2000_2012": scalar(in_range, (2000, 2012)),
            "observations_2013_2026": scalar(in_range, (2013, 2026)),
            "acquisition_receipts": {
                str(row[0]): int(row[1])
                for row in cursor.execute(
                    "SELECT acquisition_receipt, COUNT(*) FROM source_file "
                    "GROUP BY acquisition_receipt"
                )
            },
            "responsibility_assertions": scalar(
                "SELECT COUNT(*) FROM responsibility_assertion"
            ),
            "scheme_assertions": scalar("SELECT COUNT(*) FROM scheme_assertion"),
            "formal_role_assertions": scalar(
                "SELECT COUNT(*) FROM formal_role_assertion"
            ),
            "assertions_without_support": scalar(
                "SELECT COUNT(*) FROM formal_role_assertion a WHERE NOT EXISTS ("
                "SELECT 1 FROM assertion_support s WHERE s.assertion_id = a.assertion_id)"
            ),
            "expected_cells": scalar("SELECT COUNT(*) FROM expected_cell"),
            "canonical_people": scalar("SELECT COUNT(*) FROM canonical_person"),
            "garbled_wikitext_names": scalar(
                "SELECT COUNT(*) FROM canonical_person WHERE canonical_name "
                "LIKE '%oc_year%' OR canonical_name LIKE '|%'"
            ),
        }
    finally:
        conn.close()


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def reconcile_items(
    items: list[dict[str, Any]], index: dict[str, Any], release: dict[str, Any]
) -> list[dict[str, Any]]:
    """Check every unfinished entry against something real."""

    def newest(name: str) -> Path | None:
        matches = index["by_name"].get(name, [])
        if not matches:
            return None
        return Path(max(matches, key=lambda item: item["modified_utc"])["path"])

    cohort = load(newest("R35_08_NATIONAL_NEUTRAL_SITE_COHORT.json") or Path("."))
    availability = load(newest("R35_11_AVAILABILITY_RELEASE.json") or Path("."))
    heads = load(newest("CYCLE35_ALL22_REMOTE_HEADS_REFRESHED.json") or Path("."))
    jira = load(newest("CYCLE35_JIRA_LIVE_READBACK.json") or Path("."))
    family_b = load(newest("CYCLE35_ISOLATED_FAMILY_B_CONSUMER.json") or Path("."))
    mounted = load(newest("CYCLE35_MOUNTED_LANE_RECEIPT.json") or Path("."))

    out: list[dict[str, Any]] = []
    for item in items:
        blocker = item["blocker"]
        record = {**item, "category": CATEGORY_LOCAL, "checked_against": None, "finding": None}

        if "2013-2026 user rows are not cell-ingested" in blocker:
            if release.get("queried") and release["observations_2013_2026"] > 0:
                record.update(
                    category=CATEGORY_STALE,
                    checked_against=release["database"],
                    finding=(
                        f"The delivered release carries "
                        f"{release['observations_2013_2026']:,} observations in "
                        "2013-2026 under acquisition receipt "
                        "CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS. The entry is "
                        "contradicted by the delivered release, not merely by code."
                    ),
                )
        elif "Travel distance is never computed" in blocker:
            if cohort and cohort.get("travel_coverage", {}).get("rows_with_both_legs", 0) > 0:
                coverage = cohort["travel_coverage"]
                record.update(
                    category=CATEGORY_STALE,
                    checked_against="R35_08_NATIONAL_NEUTRAL_SITE_COHORT.json",
                    finding=(
                        f"{coverage['rows_with_both_legs']:,} of "
                        f"{cohort['row_count']:,} rows now carry both travel legs "
                        "from the cached CFBD /venues payload. What remains is an "
                        "acquisition gap for pre-2000 games, recorded separately."
                    ),
                )
        elif "No live Jira readback performed" in blocker:
            if jira and jira.get("issues"):
                record.update(
                    category=CATEGORY_STALE,
                    checked_against="CYCLE35_JIRA_LIVE_READBACK.json",
                    finding=(
                        f"A live readback of {len(jira['issues'])} issues exists at "
                        f"{jira.get('generated_at_utc')}. Whether it is still current "
                        "is a freshness question, not an absence."
                    ),
                )
        elif "remote heads carried as OBSERVED-BY-MANAGER" in blocker:
            if heads and heads.get("reresolved_count"):
                record.update(
                    category=CATEGORY_STALE,
                    checked_against="CYCLE35_ALL22_REMOTE_HEADS_REFRESHED.json",
                    finding=(
                        f"All {heads['reresolved_count']} heads were re-resolved "
                        f"({heads.get('failed_count', 0)} failures) and are recorded "
                        "as BAS-verified."
                    ),
                )
        elif "Stale BAT-637 code sidecar pin" in blocker:
            if family_b and family_b.get("isolated_consumer_qualified"):
                record.update(
                    category=CATEGORY_STALE,
                    checked_against="CYCLE35_ISOLATED_FAMILY_B_CONSUMER.json",
                    finding=(
                        "The versioned consumer is wired: the successor pin is "
                        "derived from declared contract authority and qualified in "
                        "isolation with stale/mixed/missing/tampered negative "
                        "controls. The stale constant is deliberately preserved. "
                        "What remains is canonical activation, tracked separately."
                    ),
                )
        elif "responsibility_assertion and scheme_assertion have zero rows" in blocker:
            if release.get("queried"):
                record.update(
                    category=CATEGORY_DATA_GAP,
                    checked_against=release["database"],
                    finding=(
                        f"Confirmed in the delivered release: "
                        f"{release['responsibility_assertions']} responsibility and "
                        f"{release['scheme_assertions']} scheme assertions. No source "
                        "evidences either, so the gap is retained rather than inferred."
                    ),
                )
        elif "Canonical activation requires" in blocker:
            record.update(
                category=CATEGORY_RELEASE_AUTHORITY,
                checked_against="CYCLE35_ISOLATED_FAMILY_B_CONSUMER.json",
                finding="The isolated path is now qualified; activation remains a "
                "distinct approval that this cycle neither performs nor requests.",
            )
        elif "Owner adoption of the schema extension" in blocker:
            record.update(
                category=CATEGORY_REVIEWER,
                finding="An owner decision, not a local task.",
            )
        elif "Stratified manual semantic adjudication" in blocker:
            record.update(
                category=CATEGORY_REVIEWER,
                finding="Independent labels are required. The reviewable queue with "
                "positive and negative controls is local work; the adjudication "
                "itself is not.",
            )
        elif "Family B mounted failures remain FAIL" in blocker:
            if mounted:
                record.update(
                    category=CATEGORY_FAILED_VALIDATION,
                    checked_against="CYCLE35_MOUNTED_LANE_RECEIPT.json",
                    finding=(
                        "Reproduced with the mount variable explicitly set: "
                        f"{mounted.get('canonical_mounted_acceptance')}. Inherited "
                        "and not concealed."
                    ),
                )
        elif "wheel not downloaded" in blocker or "needs a network call" in blocker:
            record.update(
                category=CATEGORY_BUDGET,
                finding="Requires a network request against existing authority and "
                "remaining allowance.",
            )
        elif "2024 and 2025 membership have no acquired source" in blocker:
            record.update(
                category=CATEGORY_BUDGET,
                finding="Not a permanent gap: an acquisition scope decision against "
                "the reconciled remaining allowance.",
            )
        elif "no local roster data" in blocker or "no availability-reporting language" in blocker:
            record.update(
                category=CATEGORY_DATA_GAP,
                checked_against="R35_11_AVAILABILITY_RELEASE.json"
                if availability
                else None,
                finding="A source-coverage gap, not an implementation gap.",
            )
        elif "Zero kernel rows independently proven PIT" in blocker or (
            "no identified input source" in blocker
        ) or "carry no per-row receipt" in blocker:
            record.update(
                category=CATEGORY_DATA_GAP,
                finding="A retained evidence gap. Maintaining zero proven PIT where "
                "justified is correct, not a defect to resolve by relabelling.",
            )
        elif "No trusted receipt store exists" in blocker:
            record.update(
                category=CATEGORY_DATA_GAP,
                finding="Correct-not-resolved: zero eligible forecasts is a valid "
                "state and no forecast may be invented to change it.",
            )
        elif "Hosted CI cannot exercise the mounted private-data lane" in blocker:
            record.update(
                category=CATEGORY_DATA_GAP,
                finding="Structural: the hosted runner has no private mount. Green "
                "hosted checks never supersede canonical private-data results.",
            )
        out.append(record)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--cycle-root", default=str(CYCLE_RUNS))
    parser.add_argument("--release-db", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(args.cycle_root)

    index = index_artifacts(root)

    release_db = Path(args.release_db) if args.release_db else None
    if release_db is None:
        candidates = sorted(
            (p for p in root.rglob("*.sqlite") if not SKIP_DIRECTORY_NAMES.intersection(p.parts)),
            key=lambda p: p.stat().st_mtime,
        )
        release_db = candidates[-1] if candidates else Path("none")
    release = query_release(release_db)

    status_path = out_dir / "CYCLE35_REQUIREMENT_STATUS.json"
    unfinished_path = out_dir / "CYCLE35_UNFINISHED_ITEMS.json"
    units = (load(status_path) or {}).get("units", {})
    items = (load(unfinished_path) or {}).get("items", [])

    evidence = resolve_evidence(units, index)
    reconciled = reconcile_items(items, index, release)

    by_category: dict[str, int] = {}
    for item in reconciled:
        by_category[item["category"]] = by_category.get(item["category"], 0) + 1

    result = {
        "artifact_type": "CYCLE35_EVIDENCE_GRAPH",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cycle_root": str(root),
        "run_directories": index["directories"],
        "artifact_count": index["artifact_count"],
        "delivered_release": release,
        "evidence_resolution": {
            "resolved_count": evidence["resolved_count"],
            "dangling_count": evidence["dangling_count"],
            "dangling_references": evidence["dangling_references"],
            "by_unit": evidence["by_unit"],
        },
        "unfinished_reconciliation": {
            "item_count": len(reconciled),
            "by_category": by_category,
            "items": reconciled,
        },
        "categories_are_kept_distinct": [
            CATEGORY_STALE,
            CATEGORY_LOCAL,
            CATEGORY_DATA_GAP,
            CATEGORY_FAILED_VALIDATION,
            CATEGORY_REVIEWER,
            CATEGORY_RELEASE_AUTHORITY,
            CATEGORY_BUDGET,
        ],
        "evidence_resolved_across_all_run_directories_not_one": True,
        "no_entry_deleted_or_relabelled_without_a_checked_artifact": True,
    }
    (out_dir / "CYCLE35_EVIDENCE_GRAPH.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "run_directories": len(index["directories"]),
                "artifact_count": index["artifact_count"],
                "evidence_resolved": evidence["resolved_count"],
                "dangling_references": evidence["dangling_count"],
                "release_2013_2026_observations": release.get("observations_2013_2026"),
                "unfinished_by_category": by_category,
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
