"""R36-14: plan/Jira truth, the named historical audit units, and the ledger.

Three separate obligations are answered here and kept apart, because rolling
them together is how "100% mapped" gets claimed from a keyword count:

1. **Plan and Jira truth.** The live board is read from the manager's
   snapshots (640 BAT and 102 CFIP issues) rather than assumed, the protected
   identities are asserted unchanged, and the discrepancy between the live
   board and the private mirror is reported rather than declared converged.

2. **The three named historical audit units.** Each gets three passes --
   structural evidence, independent semantic reconstruction, and an
   adversarial challenge of the review itself -- and each pass cites the
   artifact this cycle produced. Reusing the producer's helpers would not be
   independent, so each reconstruction names the module it was written in.

3. **The all-cycle ledger.** Cycles 1 through 35 are listed with their audit
   state. Most are unreviewed and say so. This cycle does not claim
   historical-project acceptance while that is true.

All 51 domain rows are carried with a state and a next deliverable, including
the ones with no implementation, because a domain with nothing behind it is
the one most likely to disappear from a summary.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]

MANAGER_RUN = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35\20260921T131038Z"
)
CYCLE36_PACK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle36")
PRIVATE_JIRA = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\JIRA_PRIVATE")

#: What the live board must still read. The pack describes BAT-429 as
#: "dependency-blocked"; the board itself carries that as the workflow status
#: "To Do" plus a dependency link, so the expectation is written against the
#: status the board actually uses rather than against the prose word. The
#: semantic is asserted separately below.
PROTECTED = {
    "BAT-523": "In Progress",
    "BAT-401": "Done",
    "BAT-429": "To Do",
}
PROTECTED_SEMANTICS = {
    "BAT-523": "Stays In Progress; no completion comment and no Done transition.",
    "BAT-401": "Stays Done with the protected lane blocked; not reopened.",
    "BAT-429": (
        "Dependency-blocked. The board status is To Do; the block is carried by "
        "its dependency link, not by a distinct workflow state."
    ),
    "GAP-005": "Open; tracked outside the BAT/CFIP projects.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def live_board() -> dict[str, Any]:
    inventory = read_json(MANAGER_RUN / "JIRA_LIVE_INVENTORY.json") or {}
    owners = read_json(MANAGER_RUN / "JIRA_OWNER_DETAILS.json") or {}
    issues: list[dict[str, Any]] = []
    for page in inventory.get("pages") or []:
        issues.extend(page.get("issues") or [])
    by_project: collections.Counter = collections.Counter()
    by_status: collections.Counter = collections.Counter()
    for issue in issues:
        key = str(issue.get("key") or "")
        by_project[key.split("-", 1)[0] if "-" in key else "UNKNOWN"] += 1
        status = (
            ((issue.get("fields") or {}).get("status") or {}).get("name") or "UNKNOWN"
        )
        by_status[str(status)] += 1
    observed_protected = {
        key: (
            ((owners.get(key) or {}).get("fields") or {}).get("status") or {}
        ).get("name")
        for key in PROTECTED
    }
    return {
        "source": str(MANAGER_RUN / "JIRA_LIVE_INVENTORY.json"),
        "sha256": sha256_file(MANAGER_RUN / "JIRA_LIVE_INVENTORY.json"),
        "observed_at_utc": inventory.get("observed_at"),
        "issues_read": len(issues),
        "by_project": dict(by_project),
        "by_status": dict(by_status.most_common()),
        "protected_identities_expected": PROTECTED,
        "protected_identity_semantics": PROTECTED_SEMANTICS,
        "protected_identities_observed": observed_protected,
        "protected_identities_unchanged": all(
            observed_protected.get(key) == value for key, value in PROTECTED.items()
        ),
        "owner_detail_keys": sorted(owners),
        "no_transition_performed_by_this_cycle": True,
    }


def private_mirror() -> dict[str, Any]:
    """The local mirror, compared to the live board rather than assumed equal."""

    record: dict[str, Any] = {"root": str(PRIVATE_JIRA), "mounted": PRIVATE_JIRA.is_dir()}
    if not PRIVATE_JIRA.is_dir():
        record["state"] = "PRIVATE_MIRROR_NOT_MOUNTED_AT_THIS_PATH"
        record["convergence"] = "NOT_ESTABLISHED"
        record["next_deliverable"] = (
            "Locate the established local Jira producer's output root and run a "
            "row-level comparison against the live readback. Posting comments "
            "is not mirror convergence."
        )
        return record
    files = sorted(path for path in PRIVATE_JIRA.rglob("*") if path.is_file())
    record.update(
        state="PRIVATE_MIRROR_PRESENT",
        files=len(files),
        sample=[str(path.relative_to(PRIVATE_JIRA)) for path in files[:10]],
        convergence="NOT_CERTIFIED",
        next_deliverable=(
            "Row-level comparison of every mirrored issue against the live "
            "readback, with a discrepancy list. Comments alone are not "
            "convergence."
        ),
    )
    return record


def domain_rows() -> dict[str, Any]:
    accounting = read_json(MANAGER_RUN / "DOMAIN_EXECUTION_ACCOUNTING.json") or {}
    domains = accounting.get("domains") or []
    states: collections.Counter = collections.Counter()
    rows = []
    for row in domains:
        states[str(row.get("status"))] += 1
        rows.append(
            {
                "domain_id": row.get("domain_id"),
                "domain": row.get("domain"),
                "natural_grain": row.get("natural_grain"),
                "inherited_status_verbatim": row.get("status"),
                "scientific_acceptance": row.get("scientific_acceptance"),
                "next_deliverable": row.get("followup"),
                "cycle36_touched": _cycle36_touch(str(row.get("domain_id"))),
            }
        )
    return {
        "source": str(MANAGER_RUN / "DOMAIN_EXECUTION_ACCOUNTING.json"),
        "sha256": sha256_file(MANAGER_RUN / "DOMAIN_EXECUTION_ACCOUNTING.json"),
        "rows": rows,
        "row_count": len(rows),
        "states": dict(states),
        "every_row_has_a_next_deliverable": all(row["next_deliverable"] for row in rows),
        "rows_untouched_by_cycle36": sum(
            1 for row in rows if row["cycle36_touched"] == "NOT_TOUCHED_THIS_CYCLE"
        ),
        "full_system_scientific_audit_complete": accounting.get(
            "full_system_scientific_audit_complete"
        ),
    }


#: Which domains this cycle actually produced evidence for. A domain not
#: listed here is explicitly untouched rather than implicitly covered.
_TOUCHED = {
    "D01": "R36-04 national population, crosswalk and effective-dated aliases",
    "D02": "R36-04 membership lineage by exact transform reproduction",
    "D03": "R36-08 game-source namespaces and kernel population",
    "D05": "R36-03/05 source-scoped season and whole-cache staff ingest",
    "D06": "R36-05 role decomposition beyond HC/OC/DC",
    "D07": "R36-06 scheme assertions and responsibility scan",
    "D09": "R36-09 venue vintage and two travel legs",
    "D11": "R36-11 availability identity and national policy denominator",
    "D14": "R36-08 prior-feature reconstruction and PIT containment",
    "D17": "R36-10 forecast eligibility and scoring guards",
    "D21": "R36-13 C01 wheel qualification and boundary matrix",
}


def _cycle36_touch(domain_id: str) -> str:
    return _TOUCHED.get(domain_id, "NOT_TOUCHED_THIS_CYCLE")


def named_audit_units(run_dir: Path) -> dict[str, Any]:
    """Three passes over each named unit, every pass citing its artifact."""

    def artifact(name: str) -> dict[str, Any]:
        path = run_dir / name
        return {
            "path": str(path),
            "exists": path.is_file(),
            "sha256": sha256_file(path),
        }

    units = [
        {
            "unit": "CYCLE30_NATIONAL_MEMBERSHIP_AND_GAME_SOURCE_LINEAGE",
            "structural_pass": {
                "what": (
                    "Declared acquisition ledger, cached payloads and derivative "
                    "files inventoried and rehashed; every /teams request year "
                    "enumerated."
                ),
                "finding": (
                    "The ledger declares 2013-2023 and 2026 only. 2024 and 2025 "
                    "were never requested, which is why the denominator lacked "
                    "them; their payloads were cached later by a different tool."
                ),
                "evidence": artifact("CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json"),
            },
            "independent_semantic_pass": {
                "what": (
                    "Membership derivatives reproduced by re-executing the "
                    "declared transformation on declared response bytes, "
                    "implemented in aggie_analytics.cycle36.membership_lineage "
                    "rather than by calling the Cycle #35 prover."
                ),
                "finding": (
                    "The 2026 derivative reproduces exactly; a one-row subset "
                    "does not, and an unrelated cached year cannot move an "
                    "existing row's authority."
                ),
                "evidence": artifact("CYCLE36_NATIONAL_MEMBERSHIP_ROWS.jsonl"),
            },
            "adversarial_pass": {
                "what": (
                    "Challenged the reviewer's own framing: is the missing "
                    "denominator really a source gap? Checked the cache for the "
                    "two absent years before accepting the inherited blocker."
                ),
                "finding": (
                    "The inherited SOURCE_UNAVAILABLE classification was wrong. "
                    "Reclassified to local work and closed at zero request cost."
                ),
                "evidence": artifact("CYCLE36_PRESERVATION_START.json"),
            },
        },
        {
            "unit": "CYCLE33_STAFF_LOCATOR_PERSON_ROLE_ADMISSION_AND_CORE_POPULATION",
            "structural_pass": {
                "what": (
                    "Every file in the mounted staff cache inventoried, hashed "
                    "and classified: bound attempt, unbound candidate, not-found "
                    "shell, bot challenge, non-HTML or unreadable."
                ),
                "finding": (
                    "2,140 captures, of which 216 bind to a declared attempt. "
                    "The rest are dispositioned rather than dropped."
                ),
                "evidence": artifact("CYCLE36_STAFF_CAPTURE_INVENTORY.jsonl"),
            },
            "independent_semantic_pass": {
                "what": (
                    "Person and title rebound through the Cycle #33 same-record "
                    "contract, with the season decided by a NEW record-scoped "
                    "binder in aggie_analytics.cycle36.source_scoped_season "
                    "rather than by the Cycle #35 page-wide one."
                ),
                "finding": (
                    "16,428 observation rows against a predecessor 880-row "
                    "reference slice; roles decomposed by the versioned "
                    "taxonomy with unmapped titles kept unmapped."
                ),
                "evidence": artifact("CYCLE36_STAFF_OBSERVATION_ROWS.jsonl"),
            },
            "adversarial_pass": {
                "what": (
                    "Challenged the season finding itself: the manager's four "
                    "negative controls prove the binder was wrong, but did the "
                    "defect actually corrupt production rows?"
                ),
                "finding": (
                    "On the real 266-capture corpus, no capture the predecessor "
                    "bound relied only on an inadmissible context. The defect "
                    "was real and its production impact on that corpus was "
                    "zero corrupted rows plus six recovered ones. Reporting it "
                    "as mass corruption would have been a false positive."
                ),
                "evidence": artifact("CYCLE36_FULL_STAFF_INGEST.json"),
            },
        },
        {
            "unit": "CYCLE35_RELEASE_ASSERTION_SEASON_AND_COVERAGE_CONSUMERS",
            "structural_pass": {
                "what": (
                    "Every declared release input rehashed inside the build, "
                    "referential integrity and orphan checks run against the "
                    "delivered database."
                ),
                "finding": (
                    "Coverage numbers are queries over delivered rows; a JSON "
                    "beside the database cannot overrule them."
                ),
                "evidence": artifact("CYCLE36_DELIVERED_RELEASE_MANIFEST.json"),
            },
            "independent_semantic_pass": {
                "what": (
                    "The release rebuilt twice from identical frozen inputs and "
                    "compared table by table at scientific-content grain, with "
                    "the audit clock isolated in its own table rather than "
                    "excluded silently."
                ),
                "finding": (
                    "Determinism is asserted per table, and the query path is "
                    "exercised from a temporary directory with no checkout on "
                    "the path."
                ),
                "evidence": artifact("CYCLE36_DELIVERED_RELEASE_MANIFEST.json"),
            },
            "adversarial_pass": {
                "what": (
                    "Challenged the coverage definition: could confirmed "
                    "coverage rise because the denominator shrank?"
                ),
                "finding": (
                    "The denominator grew from 12,460 to 12,988 program-seasons "
                    "and every season in scope is present, so a coverage "
                    "improvement cannot come from a smaller population."
                ),
                "evidence": artifact("CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json"),
            },
        },
    ]
    return {
        "units": units,
        "unit_count": len(units),
        "passes_per_unit": 3,
        "producer_helpers_reused_for_semantics": False,
        "note": (
            "Three passes over three named units is not a full historical "
            "audit. The all-cycle ledger below records what remains."
        ),
    }


def all_cycle_ledger() -> dict[str, Any]:
    scope = read_json(MANAGER_RUN / "ALL_CYCLE_AUDIT_SCOPE.json") or {}
    cycles = scope.get("cycles") or []
    audited_this_cycle = {30, 33, 35}
    rows = []
    for row in cycles:
        number = int(row.get("cycle"))
        rows.append(
            {
                "cycle": number,
                "inherited_status_verbatim": row.get("status"),
                "full_three_pass_acceptance": row.get("full_three_pass_acceptance"),
                "cycle36_state": (
                    "THREE_PASS_UNIT_AUDITED_THIS_CYCLE"
                    if number in audited_this_cycle
                    else "NOT_AUDITED"
                ),
            }
        )
    return {
        "source": str(MANAGER_RUN / "ALL_CYCLE_AUDIT_SCOPE.json"),
        "sha256": sha256_file(MANAGER_RUN / "ALL_CYCLE_AUDIT_SCOPE.json"),
        "cycles": rows,
        "cycle_count": len(rows),
        "audited_in_cycle36": sorted(audited_this_cycle),
        "still_unaudited": [
            row["cycle"] for row in rows if row["cycle36_state"] == "NOT_AUDITED"
        ],
        "historical_project_acceptance_claimed": False,
        "why": (
            "Named-unit audits in three cycles do not make the other thirty-two "
            "audited. This cycle claims no historical-project acceptance while "
            "that list is non-empty."
        ),
    }


def build(out_dir: Path, run_dir: Path) -> dict[str, Any]:
    artifact = {
        "artifact_type": "CYCLE36_PLAN_JIRA_TRACE",
        "generated_at_utc": utc_now(),
        "live_board": live_board(),
        "private_mirror": private_mirror(),
        "domain_accounting": domain_rows(),
        "named_audit_units": named_audit_units(run_dir),
        "all_cycle_ledger": all_cycle_ledger(),
        "plan_candidate_inventory": {
            "source": str(MANAGER_RUN / "PLAN_CANDIDATE_INVENTORY.json"),
            "sha256": sha256_file(MANAGER_RUN / "PLAN_CANDIDATE_INVENTORY.json"),
            "declared_candidates": 4549,
            "semantically_adjudicated": 0,
            "state": "INVENTORY_ONLY_NOT_A_REQUIREMENT_UNION",
            "next_deliverable": (
                "Classify each candidate as duplicate, superseded, governing or "
                "non-governing with a reason. A keyword match is not a "
                "classification and the inherited 8,111 heuristic relationships "
                "are not a mapping."
            ),
        },
        "no_complete_mapping_claimed": (
            "This cycle does not claim a complete requirement-to-implementation "
            "mapping. It names what it audited, what it did not, and what the "
            "next deliverable is for each domain."
        ),
        "jira_writes_performed_by_this_cycle": 0,
        "status_transitions_performed": 0,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_PLAN_JIRA_TRACE.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    _bas_atomic.write_text(out_dir / "CYCLE36_HISTORICAL_AUDIT_MATRIX.json", 
        json.dumps(
            {
                "artifact_type": "CYCLE36_HISTORICAL_AUDIT_MATRIX",
                "generated_at_utc": artifact["generated_at_utc"],
                "named_units": artifact["named_audit_units"],
                "all_cycle_ledger": artifact["all_cycle_ledger"],
                "domain_rows": artifact["domain_accounting"]["rows"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    artifact = build(args.out_dir, args.run_dir)
    print(
        json.dumps(
            {
                "issues_read": artifact["live_board"]["issues_read"],
                "protected_unchanged": artifact["live_board"][
                    "protected_identities_unchanged"
                ],
                "protected_observed": artifact["live_board"][
                    "protected_identities_observed"
                ],
                "domain_rows": artifact["domain_accounting"]["row_count"],
                "domains_untouched": artifact["domain_accounting"][
                    "rows_untouched_by_cycle36"
                ],
                "named_units": artifact["named_audit_units"]["unit_count"],
                "cycles_still_unaudited": len(
                    artifact["all_cycle_ledger"]["still_unaudited"]
                ),
                "private_mirror_state": artifact["private_mirror"].get("state"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
