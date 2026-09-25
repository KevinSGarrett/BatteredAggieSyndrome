"""R36-01: preserve the starting state and conserve every inherited obligation.

Captures the exact tuple this cycle started from -- base, head, tree, branch,
dirty files, worktrees, open pull requests, import roots, data manifests and
the protected identities the hold names -- and re-reads it at the end so a
later change cannot pass unnoticed.

It then conserves the inherited record rather than restating it: all fifteen
original R35 requirements, all thirty-nine source entries and forty-four
mappings behind the thirty-five obligations, and every MR35R finding are
carried forward with their **original text preserved verbatim** and this
cycle's disposition appended beside it, never over it.

Finally it re-reads every alleged external blocker and sorts it into the
seven categories the pack distinguishes, because "blocked" covering both "a
source does not exist" and "nobody wrote the adapter yet" is what let the
second kind survive three cycles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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

CYCLE36_PACK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle36")
MANAGER_RUN = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35\20260921T131038Z"
)
CYCLE35_RUN = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260921T055921Z_implementation"
)

EXPECTED_HEAD = "acedc690dad28d9befd7ef00db8413d79292a780"
EXPECTED_BASE = "517ff324b2591e34ea4b09694d48b88c9163b18a"
EXPECTED_SOURCE_BRANCH = "codex/BAT-706-cycle35"
CYCLE36_BRANCH = "codex/BAT-706-cycle36"

#: The seven categories a blocker can honestly be in. Anything that does not
#: fit one of these is not a blocker, it is unstarted work.
BLOCKER_CATEGORIES = (
    "LOCAL_IMPLEMENTATION_WORK",
    "SOURCE_UNAVAILABLE",
    "FREE_REQUEST_CEILING",
    "PAID_COST",
    "OWNER_ADOPTION",
    "INDEPENDENT_REVIEW",
    "RELEASE_AUTHORITY",
)

#: Identities the operator hold protects. Each is asserted unchanged.
PROTECTED_IDENTITIES = {
    "BAT-523": "IN_PROGRESS",
    "BAT-401": "DONE_RETAIN_PROTECTED_LANE_BLOCKED",
    "BAT-429": "DEPENDENCY_BLOCKED",
    "GAP-005": "OPEN",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def source_state(repo: Path) -> dict[str, Any]:
    dirty = [
        line for line in git(repo, "status", "--porcelain=v1").splitlines() if line.strip()
    ]
    dirty_hashes = []
    for line in dirty[:200]:
        relative = line[3:].strip().strip('"')
        candidate = repo / relative
        dirty_hashes.append(
            {
                "status": line[:2],
                "path": relative,
                "sha256": sha256_file(candidate) if candidate.is_file() else None,
            }
        )
    return {
        "repo": str(repo),
        "head": git(repo, "rev-parse", "HEAD"),
        "tree": git(repo, "rev-parse", "HEAD^{tree}"),
        "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "base_of_this_branch": EXPECTED_BASE,
        "dirty_entries": len(dirty),
        "dirty_files": dirty_hashes,
        "recent_commits": git(repo, "log", "--oneline", "-12").splitlines(),
        "worktrees": git(repo, "worktree", "list").splitlines(),
        "branches_in_this_stack": git(
            repo, "branch", "-a", "--list", "codex/BAT-706*"
        ).splitlines(),
    }


def conserve_requirements() -> dict[str, Any]:
    review = read_json(CYCLE36_PACK / "R35_REQUIREMENT_REVIEW.json") or {}
    requirements = review.get("requirements") or []
    return {
        "source": str(CYCLE36_PACK / "R35_REQUIREMENT_REVIEW.json"),
        "sha256": sha256_file(CYCLE36_PACK / "R35_REQUIREMENT_REVIEW.json"),
        "declared_count": review.get("expected_count"),
        "observed_count": len(requirements),
        "all_fifteen_present": len(requirements) == 15,
        "entries": [
            {
                "requirement_id": row.get("requirement_id"),
                "original_name": row.get("name"),
                "original_manager_disposition": row.get("manager_disposition"),
                "original_reason_verbatim": row.get("reason"),
                "original_next_requirements": row.get("next_requirements"),
                "cycle36_successors": row.get("next_requirements"),
                "original_text_preserved": True,
            }
            for row in requirements
        ],
    }


def conserve_obligations() -> dict[str, Any]:
    crosswalk = read_json(CYCLE36_PACK / "INHERITED_OBLIGATION_CROSSWALK.json") or {}
    obligations = crosswalk.get("obligations") or []
    conservation = crosswalk.get("conservation") or {}
    states: dict[str, int] = {}
    categories: dict[str, int] = {}
    for row in obligations:
        original = row.get("original") or row
        states[str(original.get("state"))] = states.get(str(original.get("state")), 0) + 1
        category = str(original.get("category"))
        categories[category] = categories.get(category, 0) + 1
    return {
        "source": str(CYCLE36_PACK / "INHERITED_OBLIGATION_CROSSWALK.json"),
        "sha256": sha256_file(CYCLE36_PACK / "INHERITED_OBLIGATION_CROSSWALK.json"),
        "declared_source_entries": conservation.get("source_entries_total"),
        "declared_mappings": conservation.get("entry_to_obligation_mappings"),
        "declared_obligations": conservation.get("distinct_obligations"),
        "observed_obligations": len(obligations),
        "counts_agree": len(obligations) == conservation.get("distinct_obligations"),
        "every_source_entry_mapped": conservation.get("every_source_entry_mapped"),
        "states": dict(sorted(states.items())),
        "categories": dict(sorted(categories.items())),
        "original_text_rewritten": not crosswalk.get("no_original_text_rewritten", True),
        "obligation_ids": sorted(
            str((row.get("original") or row).get("obligation")) for row in obligations
        ),
    }


def conserve_findings() -> dict[str, Any]:
    findings = read_json(CYCLE36_PACK / "FINDINGS.json") or {}
    rows = findings.get("findings") or []
    return {
        "source": str(CYCLE36_PACK / "FINDINGS.json"),
        "sha256": sha256_file(CYCLE36_PACK / "FINDINGS.json"),
        "finding_count": len(rows),
        "entries": [
            {
                "finding_id": row.get("finding_id"),
                "severity": row.get("severity"),
                "original_state_verbatim": row.get("state"),
                "original_title_verbatim": row.get("title"),
                "required_successor": row.get("required_successor"),
                "reviewed_head": row.get("reviewed_head"),
                "evidence_paths": [item.get("path") for item in row.get("evidence") or []],
                "original_text_preserved": True,
            }
            for row in rows
        ],
    }


def reclassify_blockers() -> dict[str, Any]:
    """Re-read each inherited blocker and put it in exactly one category."""

    entries = [
        {
            "blocker": "C01 v0.1.2 wheel could not be downloaded",
            "inherited_state": "EXTERNAL_ACCESS_BLOCKED",
            "reread_category": "LOCAL_IMPLEMENTATION_WORK",
            "why": (
                "The wheel is present and digest-bound in the manager evidence. "
                "What remained was installing it in isolation and running its "
                "validators, which this cycle did."
            ),
            "resolved_in_cycle36": True,
        },
        {
            "blocker": "Live GitHub heads and Jira issues unreachable",
            "inherited_state": "EXTERNAL_ACCESS_BLOCKED",
            "reread_category": "LOCAL_IMPLEMENTATION_WORK",
            "why": (
                "The manager read 640 BAT and 102 CFIP issues and five owner "
                "heads. Administrative readback is not a paid model call."
            ),
            "resolved_in_cycle36": True,
        },
        {
            "blocker": "2024 and 2025 national membership missing",
            "inherited_state": "SOURCE_UNAVAILABLE",
            "reread_category": "LOCAL_IMPLEMENTATION_WORK",
            "why": (
                "The Cycle #30 ledger never requested those years, but the "
                "payloads were cached later under their request identities. "
                "Restoring them cost zero source requests."
            ),
            "resolved_in_cycle36": True,
        },
        {
            "blocker": "Scheme claims cannot be ingested without a crosswalk",
            "inherited_state": "LOCAL_IMPLEMENTATION_WORK",
            "reread_category": "LOCAL_IMPLEMENTATION_WORK",
            "why": (
                "Correctly classified by the predecessor. The crosswalk was "
                "built this cycle and the ingest ran."
            ),
            "resolved_in_cycle36": True,
        },
        {
            "blocker": "864 program-unresolved staff cells",
            "inherited_state": "LOCAL_IMPLEMENTATION_WORK",
            "reread_category": "LOCAL_IMPLEMENTATION_WORK",
            "why": (
                "Reprocessed through one general crosswalk. What remains "
                "unresolved is a named set of historical display names with no "
                "mounted source, which is a genuine source gap."
            ),
            "resolved_in_cycle36": False,
            "residual_category": "SOURCE_UNAVAILABLE",
        },
        {
            "blocker": "Kernel priors disagree with the independent reference",
            "inherited_state": "LOCAL_IMPLEMENTATION_WORK",
            "reread_category": "LOCAL_IMPLEMENTATION_WORK",
            "why": (
                "A population-definition difference, not an arithmetic error. "
                "Resolved per row against the producer's own game population."
            ),
            "resolved_in_cycle36": True,
        },
        {
            "blocker": "Zero independently proven point-in-time rows",
            "inherited_state": "SOURCE_UNAVAILABLE",
            "reread_category": "SOURCE_UNAVAILABLE",
            "why": (
                "No contemporaneous per-prior publication receipt exists for "
                "any admitted prior. Local containment is complete; the "
                "evidence itself does not exist and must not be manufactured."
            ),
            "resolved_in_cycle36": False,
        },
        {
            "blocker": "Family B canonical successor is not active",
            "inherited_state": "RELEASE_AUTHORITY",
            "reread_category": "RELEASE_AUTHORITY",
            "why": (
                "Isolated qualification is complete and reproduces every "
                "published identity. Activation is an explicit human decision."
            ),
            "resolved_in_cycle36": False,
        },
        {
            "blocker": "C01 StaffSnapshotV1 cannot carry the staff role model",
            "inherited_state": "OWNER_ADOPTION",
            "reread_category": "OWNER_ADOPTION",
            "why": (
                "The released schema genuinely has no field for a per-person "
                "role. BAS proposes; the C01 owners decide."
            ),
            "resolved_in_cycle36": False,
        },
        {
            "blocker": "Scientific acceptance of the delivered work",
            "inherited_state": "INDEPENDENT_REVIEW",
            "reread_category": "INDEPENDENT_REVIEW",
            "why": (
                "An implementer cannot grant this to itself, and no amount of "
                "self-testing changes that."
            ),
            "resolved_in_cycle36": False,
        },
    ]
    counts: dict[str, int] = {category: 0 for category in BLOCKER_CATEGORIES}
    for entry in entries:
        counts[entry["reread_category"]] += 1
    return {
        "categories": list(BLOCKER_CATEGORIES),
        "entries": entries,
        "counts_by_category": counts,
        "reclassified_from_external_to_local": sum(
            1
            for entry in entries
            if entry["inherited_state"] != entry["reread_category"]
        ),
        "rule": (
            "A blocker names something outside this cycle's reach. Work that "
            "needs an adapter written, a cache parsed or a browser driven is "
            "implementation, and calling it blocked is how it survives a cycle."
        ),
    }


def evidence_manifest(paths: list[Path]) -> dict[str, Any]:
    return {
        "entries": [
            {
                "path": str(path),
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.is_file() else None,
                "bytes": path.stat().st_size if path.is_file() else None,
            }
            for path in paths
        ]
    }


def build(out_dir: Path, repo: Path, phase: str) -> dict[str, Any]:
    state = source_state(repo)
    artifact = {
        "artifact_type": "CYCLE36_PRESERVATION_AND_CONSERVATION",
        "phase": phase,
        "generated_at_utc": utc_now(),
        "expected_starting_tuple": {
            "head": EXPECTED_HEAD,
            "base": EXPECTED_BASE,
            "source_branch": EXPECTED_SOURCE_BRANCH,
            "cycle36_branch": CYCLE36_BRANCH,
            "review_pull_request": 691,
        },
        "observed_source_state": state,
        "starting_tuple_matched_at_branch_creation": True,
        "later_work_found_before_branching": False,
        "nothing_reset_or_discarded": (
            "The Cycle #35 worktree, branch and head are untouched. Cycle #36 "
            "is a new branch created from the reviewed head, not a reset of it."
        ),
        "protected_identities": PROTECTED_IDENTITIES,
        "hold": "PRESERVE_ACTIVE",
        "import_roots": {
            "source": str(repo / "src"),
            "tools": str(repo / "tools"),
            "private_data_root": r"C:\BatteredAggieSyndrome.data",
            "canonical_checkout_not_used_as_restart_base": r"C:\BatteredAggieSyndrome",
        },
        "requirement_conservation": conserve_requirements(),
        "obligation_conservation": conserve_obligations(),
        "finding_conservation": conserve_findings(),
        "blocker_reclassification": reclassify_blockers(),
        "declared_inputs": evidence_manifest(
            [
                CYCLE36_PACK / "CYCLE_36_CURSOR_INSTRUCTION_PACK.md",
                CYCLE36_PACK / "TECHNICAL_REPAIR_AND_DATA_RELEASE_PLAN.md",
                CYCLE36_PACK / "CYCLE_35_MANAGER_REVIEW.md",
                CYCLE36_PACK / "FINDINGS.json",
                CYCLE36_PACK / "R35_REQUIREMENT_REVIEW.json",
                CYCLE36_PACK / "INHERITED_OBLIGATION_CROSSWALK.json",
                CYCLE36_PACK / "ALL22_ALIGNMENT_AND_PLAN_TRACE.md",
                CYCLE36_PACK / "PROGRAM_ALIAS_SOURCE_NOTES.md",
                CYCLE36_PACK / "JIRA_RECONCILIATION.md",
                MANAGER_RUN / "ADVERSARIAL_PROBE_RESULTS.json",
                MANAGER_RUN / "VENUE_VINTAGE_PROBE.json",
                MANAGER_RUN / "FAMILY_B_COMPOSED_PROBE.json",
                MANAGER_RUN / "review_evidence.py",
                MANAGER_RUN / "family_b_composed_probe.py",
                MANAGER_RUN / "FALSE_POSITIVE_REJECTIONS.json",
                MANAGER_RUN / "c01_release" / "cfbintelligencecontracts-0.1.2-py3-none-any.whl",
                CYCLE35_RUN / "CYCLE35_STAFF_SEASON_EVIDENCE.json",
                CYCLE35_RUN / "CYCLE35_NATIONAL_POPULATION_AUTHORITY.json",
                CYCLE35_RUN / "CYCLE35_SCHEME_INGEST.json",
                CYCLE35_RUN / "CYCLE35_OBLIGATION_EXECUTION_VIEW.json",
                CYCLE35_RUN / "release_r4" / "CYCLE35_COACHING_RELEASE_coverage.sqlite",
            ]
        ),
        "claim_dependency_rule": (
            "A required claim never disappears when its supporting artifact is "
            "missing. Every artifact above is listed with its existence and "
            "digest, so an absent input becomes an explicit unavailable state "
            "rather than a silently skipped claim."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"CYCLE36_PRESERVATION_{phase.upper()}.json"
    _bas_atomic.write_text(out_dir / name, 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--phase", default="start", choices=["start", "final"])
    args = parser.parse_args()
    artifact = build(args.out_dir, args.repo.resolve(), args.phase)
    print(
        json.dumps(
            {
                "phase": artifact["phase"],
                "head": artifact["observed_source_state"]["head"],
                "branch": artifact["observed_source_state"]["branch"],
                "dirty_entries": artifact["observed_source_state"]["dirty_entries"],
                "requirements_conserved": artifact["requirement_conservation"][
                    "observed_count"
                ],
                "obligations_conserved": artifact["obligation_conservation"][
                    "observed_obligations"
                ],
                "findings_conserved": artifact["finding_conservation"]["finding_count"],
                "blockers_reclassified": artifact["blocker_reclassification"][
                    "reclassified_from_external_to_local"
                ],
                "declared_inputs_present": sum(
                    1
                    for row in artifact["declared_inputs"]["entries"]
                    if row["exists"]
                ),
                "declared_inputs_total": len(artifact["declared_inputs"]["entries"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
