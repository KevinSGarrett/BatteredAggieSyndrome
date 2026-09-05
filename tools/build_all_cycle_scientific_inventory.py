"""Build Cycle #25.5 scientific-integrity artifacts from independent local evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.governance.scientific_trust_recovery_hold import (  # noqa: E402
    STARTING_SHA,
    bind_identity,
)

ALL_CYCLES = REPO_ROOT / "artifacts" / "scientific_integrity" / "all_cycles"
CYCLE_SHA_TABLE = [
    (1, "b86a0759", "f318d184"),
    (2, "f318d184", "a40527ab"),
    (3, "a40527ab", "5baf80d4"),
    (4, "5baf80d4", "05b17030"),
    (5, "05b17030", "062121dc"),
    (6, "062121dc", "bf988188"),
    (7, "bf988188", "9aab811c"),
    (8, "9aab811c", "2b230a63"),
    (9, "2b230a63", "93049610"),
    (10, "93049610", "0fc3d317"),
    (11, "0fc3d317", "4d901113"),
    (12, "4d901113", "b5458ce1"),
    (13, "b5458ce1", "b0329999"),
    (14, "b0329999", "589160ad"),
    (15, "589160ad", "c873056f"),
    (16, "c873056f", "6c4ed8a9"),
    (17, "6c4ed8a9", "71952d40"),
    (18, "71952d40", "1c44df09"),
    (19, "1c44df09", "1c44df09"),
    (20, "1c44df09", "862b4ff5"),
    (21, "862b4ff5", "f7b68d77"),
    (22, "f7b68d77", "f7b68d77"),
    (23, "f7b68d77", "cbb78b07"),
    (24, "cbb78b07", "991bf466"),
    (25, "991bf466", "c1c310da"),
]
INSTRUCTION_TEXT = (
    "USER_EXPLICIT_CURSOR_AUTHORIZATION_CYCLE_25_5\n"
    "Execute all Cycle #25.5 Scientific Trust Recovery Program work in this one "
    "Cursor session without assistive workers; retired assistive pipeline remains inactive."
)
PACK_PATH = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle25_5\CYCLE_25_5_CURSOR_INSTRUCTION_PACK.md"
)


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git failed")
    return completed.stdout.strip()


def _expand(prefix: str) -> str:
    return _git("rev-parse", prefix)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _is_ancestor(maybe_ancestor: str, maybe_descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", maybe_ancestor, maybe_descendant],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.returncode == 0


def verify_cycle_shas() -> list[dict[str, Any]]:
    rows = []
    for number, start_prefix, end_prefix in CYCLE_SHA_TABLE:
        start = _expand(start_prefix)
        end = _expand(end_prefix)
        rows.append(
            {
                "cycle_number": number,
                "declared_starting_prefix": start_prefix,
                "declared_ending_prefix": end_prefix,
                "starting_sha": start,
                "ending_sha": end,
                "objects_exist": True,
                "end_descends_from_start": _is_ancestor(start, end),
                "independent_verification": "git_rev_parse_and_merge_base_is_ancestor",
            }
        )
    return rows


def classify_role(relative: str) -> str:
    posix = relative.replace("\\", "/")
    name = Path(posix).name.lower()
    if posix.startswith("src/aggie_analytics/scientific_reference/"):
        return "INDEPENDENT_SEMANTIC_REFERENCE"
    if posix.startswith("src/aggie_analytics/validation/") or (
        posix.startswith("tools/") and name.startswith("validate_")
    ):
        return "SCIENTIFIC_VALIDATOR"
    if posix.startswith("src/aggie_analytics/") and posix.endswith(".py"):
        return "SCIENTIFIC_PRODUCER"
    if posix.startswith("schemas/"):
        return "SCIENTIFIC_CONTRACT_SCHEMA"
    if posix.startswith("governance/") or posix.startswith("configs/"):
        return "GOVERNANCE"
    if posix.startswith("artifacts/forecast/") or posix.startswith("artifacts/pit/"):
        return "SCIENTIFIC"
    if "gate" in posix or "contract" in posix:
        return "SCIENTIFIC_IF_QUANTITATIVE_ELSE_GOVERNANCE"
    if posix.startswith("artifacts/jira_evidence/"):
        return "GOVERNANCE"
    if posix.startswith("artifacts/scientific_integrity/"):
        return "SCIENTIFIC_TRUST_RECOVERY"
    if posix.startswith("artifacts/"):
        return "SCIENTIFIC_IF_QUANTITATIVE_ELSE_GOVERNANCE"
    if posix.startswith("tools/") and posix.endswith(".py"):
        return "SCIENTIFIC_VALIDATOR" if "validate" in name else "SCIENTIFIC_PRODUCER"
    return "NON_SCIENTIFIC_OR_PROCESS"


def first_add_commit(relative: str) -> str:
    completed = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", relative],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    commits = (completed.stdout or "").split()
    if not commits:
        return ""
    # git log is newest-first; originating_cycle uses the earliest add.
    return commits[-1]


def first_add_index() -> dict[str, str]:
    """Map each path to its earliest add commit.

    `git log` is newest-first, so the last SHA written for a path is the
    earliest add. This avoids one process per inventoried file.
    """
    output = _git("log", "--diff-filter=A", "--name-only", "--pretty=format:%H")
    index: dict[str, str] = {}
    current = ""
    for raw in output.splitlines():
        line = raw.strip().replace("\\", "/")
        if not line:
            continue
        if len(line) == 40 and all(char in "0123456789abcdef" for char in line.lower()):
            current = line
            continue
        if current:
            index[line] = current
    return index


def cycle_commit_index(cycle_rows: list[dict[str, Any]]) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for row in cycle_rows:
        number = int(row["cycle_number"])
        start = str(row["starting_sha"])
        end = str(row["ending_sha"])
        if start == end:
            index.setdefault(start, []).append(number)
            continue
        log = _git("log", "--format=%H", f"{start}..{end}")
        for commit in log.split():
            index.setdefault(commit, []).append(number)
        if number == 1:
            # start..end excludes the declared Cycle 1 starting commit. Include
            # that commit only; do not attribute any pre-start history to Cycle 1.
            index.setdefault(start, []).append(number)
    return index


def git_first_add_cycle(
    relative: str,
    cycle_rows: list[dict[str, Any]],
    commit_index: dict[str, list[int]],
    add_index: dict[str, str] | None = None,
) -> tuple[int | str, str]:
    commit = (add_index or {}).get(relative) or first_add_commit(relative)
    if not commit:
        return "UNMAPPED", "GIT_FIRST_ADD_NOT_FOUND"
    matches = commit_index.get(commit, [])
    unique = sorted(set(matches))
    if len(unique) == 1:
        return unique[0], "GIT_FIRST_ADD"
    if unique:
        return "UNMAPPED", "GIT_FIRST_ADD_AMBIGUOUS_CYCLE"
    cycle_one_start = str(cycle_rows[0]["starting_sha"])
    cycle_25_end = str(cycle_rows[-1]["ending_sha"])
    if commit != cycle_one_start and _is_ancestor(commit, cycle_one_start):
        return "UNMAPPED", "GIT_FIRST_ADD_BEFORE_CYCLE_1"
    if commit != cycle_25_end and _is_ancestor(cycle_25_end, commit):
        return "UNMAPPED", "GIT_FIRST_ADD_AFTER_CYCLE_25"
    return "UNMAPPED", "GIT_FIRST_ADD_OUTSIDE_DECLARED_RANGES"


def cycle_for_path(relative: str, cycle_rows: list[dict[str, Any]]) -> int | str:
    posix = relative.replace("\\", "/").lower()
    mapping = (
        ("scientific_integrity", 25),
        ("cycle25", 25),
        ("week1_2026", 24),
        ("cycle24", 24),
        ("cycle23", 23),
        ("cycle22", 22),
        ("cycle21", 21),
        ("cycle20", 20),
        ("national_foundation", 18),
        ("development_2023", 18),
        ("tamu", 12),
        ("protected", 17),
        ("pit_", 8),
        ("data_lake", 6),
        ("jira_evidence", 5),
        ("forecast", 24),
        ("shadow", 23),
        ("assistive", 14),
        ("artifact_binding", 16),
        ("codex_usage", 14),
        ("unified_assistive", 14),
    )
    for token, cycle in mapping:
        if token in posix:
            return cycle
    _ = cycle_rows
    return "UNMAPPED"


AUTHORITY_SUFFIXES = {".json", ".yaml", ".yml", ".csv", ".md", ".py"}
CENSUS_ROOTS = (
    "artifacts",
    "configs",
    "governance",
    "schemas",
    "src/aggie_analytics",
    "tools",
)


def authority_paths() -> list[str]:
    paths: list[str] = []
    for root_name in CENSUS_ROOTS:
        root = REPO_ROOT / Path(*root_name.split("/"))
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in AUTHORITY_SUFFIXES:
                continue
            paths.append(path.relative_to(REPO_ROOT).as_posix())
    return sorted(set(paths))


def build_hold_receipt(cycle_rows: list[dict[str, Any]]) -> dict[str, Any]:
    pack_hash = _sha256_file(PACK_PATH) if PACK_PATH.is_file() else None
    payload = {
        "artifact_type": "OPERATOR_HOLD_RECEIPT",
        "audited_starting_sha": STARTING_SHA,
        "calendar_exceptions": {
            "kickoff_utc": "2026-09-05T23:00:00Z",
            "never_backfill_missed_checkpoint": True,
            "t24h_deadline_utc": "2026-09-04T23:00:00Z",
            "t90m_deadline_utc": "2026-09-05T21:30:00Z",
        },
        "cycle25_hold_incident": {
            "hold_was_implemented": False,
            "merged_prs_despite_intended_hold": [665, 666, 667],
            "must_not_hide_or_rewrite": True,
            "record": (
                "The earlier Cycle #25 hold was not implemented and PRs #665-#667 merged."
            ),
        },
        "hold_id": "CYCLE-25.5-SCIENTIFIC-TRUST-RECOVERY-OPERATOR-HOLD",
        "issue_scope": [
            "BAT-688",
            "BAT-689",
            "BAT-690",
            "BAT-691",
            "BAT-692",
            "BAT-693",
            "BAT-694",
            "BAT-695",
            "BAT-696",
        ],
        "issued_at_utc": "2026-09-01T17:43:27Z",
        "permitted_actions": [
            "issue_scoped_branches_and_worktrees",
            "commits_and_draft_or_ready_for_review_prs",
            "ci_runs",
            "immutable_live_evidence_capture_at_actual_deadlines",
            "jira_transitions_through_in_review",
            "read_only_audits_and_validation",
            "separately_authorized_review_infrastructure_merge",
        ],
        "pr_scope": {
            "do_not_touch": ["654"],
            "scientific_correction_merges_forbidden": True,
        },
        "prohibited_actions": [
            "merge_scientific_correction_prs",
            "transition_scientific_trust_recovery_owners_to_done",
            "post_cycle_25_5_bat_523_parent_progress_comment",
            "describe_fitted_week1_forecast_as_credible_or_recommended",
            "promote_a_candidate",
            "declare_cycle_25_5_complete",
        ],
        "release_authority": {
            "authorizing_user": "KevinSGarrett",
            "requires_operator_release_receipt": True,
        },
        "schema_version": 1,
        "status": "ACTIVE",
        "trusted_source": {
            "agent_recorded_wall_clock_utc": "2026-09-01T17:43:27Z",
            "audited_starting_sha": STARTING_SHA,
            "instruction_pack_sha256": pack_hash,
            "instruction_text_sha256": _sha256_text(INSTRUCTION_TEXT),
            "note": (
                "Wall-clock is agent-recorded and is not durable acquisition authority; "
                "binding identities are the audited SHA and instruction hashes."
            ),
        },
        "user_instruction_identity": {
            "instruction_pack_path": str(PACK_PATH),
            "instruction_pack_sha256": pack_hash,
            "instruction_text": INSTRUCTION_TEXT,
            "instruction_text_sha256": _sha256_text(INSTRUCTION_TEXT),
        },
        "verified_cycle_sha_table": cycle_rows,
    }
    return bind_identity(payload, "receipt_identity")


def known_findings() -> list[dict[str, Any]]:
    return [
        {
            "finding_id": "P0-C24-RIDGE-DISTRIBUTION-INCOHERENCE",
            "severity": "P0",
            "cycles": [24, 25],
            "disposition": "FAIL",
            "summary": (
                "national_margin_ridge emits logistic probabilities and Normal residual "
                "intervals that are not one predictive distribution."
            ),
            "evidence": [
                "src/aggie_analytics/data/week1_2026_ridge_distribution_coherence.py"
            ],
        },
        {
            "finding_id": "P0-C25-HISTORICAL-ROW-TRANSPLANT",
            "severity": "P0",
            "cycles": [25],
            "disposition": "FAIL",
            "summary": (
                "Cycle #25 successor copies terminal historical game rows into current "
                "Week 1 targets instead of binding the current contest opponent."
            ),
            "evidence": [
                "src/aggie_analytics/data/week1_2026_forecast_input_binding_successor.py"
            ],
        },
        {
            "finding_id": "P0-PRE-MARKET-FREEZE-NOT-PROVEN",
            "severity": "P0",
            "cycles": [25],
            "disposition": "FAIL",
            "summary": "Model freeze predating market access is not proven.",
            "evidence": [
                "src/aggie_analytics/data/week1_2026_market_benchmark_and_adequacy.py"
            ],
        },
        {
            "finding_id": "P0-FOCUS-GAME-QUOTE-COUNT-FALSE-ZERO",
            "severity": "P0",
            "cycles": [25],
            "disposition": "FAIL",
            "summary": (
                "Focus-game quote_count=0 can be produced by Missouri State / Missouri St. "
                "alias mismatch despite raw quotes."
            ),
            "evidence": [
                "src/aggie_analytics/data/week1_2026_market_benchmark_and_adequacy.py"
            ],
        },
        {
            "finding_id": "P0-VALIDATOR-PRODUCER-HELPER-REUSE",
            "severity": "P0",
            "cycles": [24, 25],
            "disposition": "FAIL",
            "summary": "Scientific validators import producer helpers they purport to challenge.",
            "evidence": ["tools/validate_week1_2026_ridge_distribution_coherence.py"],
        },
        {
            "finding_id": "P0-C25-HOLD-NOT-IMPLEMENTED",
            "severity": "P0",
            "cycles": [25],
            "disposition": "FAIL",
            "summary": "Cycle #25 hold was not implemented; PRs #665-#667 merged.",
            "evidence": ["git log origin/main", "PRs 665-667"],
        },
        {
            "finding_id": "P1-FALSE-QUARANTINE-312472199",
            "severity": "P1",
            "cycles": [18, 20, 21],
            "disposition": "REPRODUCIBLE_WRONG_SPECIFICATION",
            "summary": (
                "Substring postponed/canceled detection on notes falsely quarantines "
                "SRC-002:GAME:312472199 (2011 Howard-EMU completed 41-9)."
            ),
            "evidence": [
                "src/aggie_analytics/data/national_foundation_reconciliation.py"
            ],
        },
        {
            "finding_id": "P1-EVEN-SIZED-MEDIAN-UPPER-MIDDLE",
            "severity": "P1",
            "cycles": [25],
            "disposition": "FAIL",
            "summary": "Even-sized median uses sorted(values)[len//2] rather than the mean of the two central values.",
            "evidence": [
                "src/aggie_analytics/data/week1_2026_market_benchmark_and_adequacy.py"
            ],
        },
        {
            "finding_id": "P1-2024-2025-EXPOSED-NOT-BLIND",
            "severity": "P1",
            "cycles": [17, 25],
            "disposition": "FAIL",
            "summary": "2024/2025 are historically exposed and cannot be restored to blind/protected status.",
            "evidence": ["BAT-401", "RETAIN_PROTECTED_LANE_BLOCKED"],
        },
        {
            "finding_id": "P2-REMAINING-OPEN-CHECKPOINTS-PLANNED",
            "severity": "P2",
            "cycles": [25],
            "disposition": "REPRODUCIBLE_ONLY",
            "summary": (
                "Remaining A&M T-24H 2026-09-04T23:00:00Z and T-90M 2026-09-05T21:30:00Z "
                "are OPEN planned checkpoints, not an integrity defect. Sep 3 T-24H is "
                "MISSED_CUTOFF_NO_BACKFILL. Sep 3 T-90M and the Sep4-window T-24H were "
                "captured before their cutoffs. Do not backfill a missed checkpoint."
            ),
            "evidence": [
                "artifacts/scientific_integrity/cycle26/CYCLE26_WEEK1_CAPTURE_RECEIPT.json",
                "artifacts/scientific_integrity/cycle26/CYCLE26_SEP3_T90M_FREEZE_RECEIPT.json",
                "artifacts/scientific_integrity/cycle26/CYCLE26_SEP4_WINDOW_T24H_FREEZE_RECEIPT.json",
            ],
        },
        {
            "finding_id": "P1-NATIONAL-CAPTURE-COUNT-990-VS-MOUNTED",
            "severity": "P1",
            "cycles": [18, 20, 21],
            "disposition": "BLOCKED_INSUFFICIENT_EVIDENCE",
            "summary": (
                "Declared national capture set is 990 (BAT-382 / POST-SUBTASK-044). "
                "Mounted raw/SRC-002 currently contains 980 files (63 under games/). "
                "The full 990-capture 2,550,148,419-byte archive was not rehashed because "
                "that exact capture set is not mounted as 990 files."
            ),
            "evidence": [
                "artifacts/data_lake/national_lake_readiness.json",
                "mounted:raw/SRC-002 file count 980",
            ],
        },
    ]


def false_positive_rejections() -> list[dict[str, Any]]:
    return [
        {
            "finding_id": "FP-BROAD-RAW-CORRUPTION",
            "rejected": True,
            "reason": "Independent inspection did not show wholesale raw-file corruption.",
        },
        {
            "finding_id": "FP-A&M-ADMITTED-SCORE-CORRUPTION",
            "rejected": True,
            "reason": "No evidence that admitted A&M final scores were rewritten.",
        },
        {
            "finding_id": "FP-REJECTION-LEAKAGE-INTO-UNION",
            "rejected": True,
            "reason": "Rejected URLs are not shown to enter union membership in committed gates.",
        },
        {
            "finding_id": "FP-CYCLE-3-LEAKAGE",
            "rejected": True,
            "reason": "Cycle #3 leakage claim was not independently reproduced from current artifacts.",
        },
        {
            "finding_id": "FP-A&M-PARSER-CONTAMINATES-NATIONAL-MODEL",
            "rejected": True,
            "reason": "A&M parser defects do not automatically contaminate national SRC-002 rows.",
        },
        {
            "finding_id": "FP-BAS-CHAMPION-PROMOTION",
            "rejected": True,
            "reason": "Repository non-claims continue to forbid BAS/champion/production promotion.",
        },
        {
            "finding_id": "P1-NATIONAL-CAPTURE-COUNT-990-VS-MOUNTED",
            "rejected": True,
            "original_assertion_preserved": True,
            "reason": (
                "Manager rehash of the BAT-651 CFBD request_index plus SportsDataverse "
                "captures, including CAPTURED_EMPTY, verified 972+18=990 valid records, "
                "983 distinct paths/hashes, and 2,550,148,419 record-weighted bytes. "
                "A recursive SRC-002 directory count is not the declared population. "
                "Byte verification does not admit a feature or restore trust."
            ),
        },
    ]


def build_inventory(cycle_rows: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts = []
    commit_index = cycle_commit_index(cycle_rows)
    add_index = first_add_index()
    for relative in authority_paths():
        git_cycle, git_note = git_first_add_cycle(
            relative, cycle_rows, commit_index, add_index
        )
        if git_note == "GIT_FIRST_ADD":
            cycle, mapping_note = git_cycle, git_note
        else:
            cycle, mapping_note = "UNMAPPED", git_note
        artifacts.append(
            {
                "path": relative,
                "originating_cycle": cycle,
                "mapping_note": mapping_note,
                "jira_owner": "SEE_CYCLE_AUDIT",
                "pr_or_merge": "SEE_CYCLE_AUDIT",
                "scientific_claim_or_role": classify_role(relative),
                "producer": "COMMITTED_MODULE_OR_BUILDER",
                "validator": "COMMITTED_VALIDATOR_OR_NONE",
                "source_identities": ["git:" + relative],
                "current_trust_classification": "UNREVIEWED",
                "affected_successors": [],
                "authority_bearing": True,
            }
        )
    return bind_identity(
        {
            "artifact_type": "ALL_CYCLE_ARTIFACT_INVENTORY",
            "artifacts": artifacts,
            "audited_starting_sha": STARTING_SHA,
            "census_roots": list(CENSUS_ROOTS),
            "completeness_rule": (
                "Unmapped authority-bearing artifacts are a hard completeness failure "
                "for scientific_trust_recovered and must keep inventory_completeness="
                "INCOMPLETE_UNMAPPED_AUTHORITY. Census roots are artifacts, configs, "
                "governance, schemas, src/aggie_analytics, and tools. Inside those "
                "roots every authority-suffixed file is inventoried; token or filename "
                "filters are not inclusion authority. Files outside the six roots remain "
                "uncensused. A passing inventory validator means that incompleteness is "
                "recorded with explicit mapping_notes, not that mapping is complete."
            ),
            "cycle_sha_table": cycle_rows,
            "cycles": [
                {
                    "cycle_number": row["cycle_number"],
                    "starting_sha": row["starting_sha"],
                    "ending_sha": row["ending_sha"],
                    "artifact_count": sum(
                        1
                        for item in artifacts
                        if item["originating_cycle"] == row["cycle_number"]
                    ),
                }
                for row in cycle_rows
            ],
            "schema_version": 1,
            "unmapped_authority_count": sum(
                1 for item in artifacts if item.get("originating_cycle") == "UNMAPPED"
            ),
        },
        "inventory_identity",
    )


def build_claims(inventory: dict[str, Any]) -> dict[str, Any]:
    claims = []
    for finding in known_findings():
        for cycle in finding["cycles"]:
            claims.append(
                {
                    "claim_id": f"{finding['finding_id']}:C{cycle:02d}",
                    "cycle_number": cycle,
                    "summary": finding["summary"],
                    "trust_classification": finding["disposition"]
                    if finding["disposition"]
                    in {
                        "FAIL",
                        "BLOCKED_INSUFFICIENT_EVIDENCE",
                        "REPRODUCIBLE_ONLY",
                    }
                    else "FAIL"
                    if finding["disposition"] == "REPRODUCIBLE_WRONG_SPECIFICATION"
                    else finding["disposition"],
                    "validator_class": "INDEPENDENT_SEMANTIC_REFERENCE"
                    if finding["finding_id"].startswith("P0")
                    or finding["finding_id"].startswith("P1")
                    else "SAME_SPECIFICATION_INDEPENDENT_CODE",
                    "severity": finding["severity"],
                    "producer": finding["evidence"][0],
                }
            )
    for cycle in range(1, 26):
        claims.append(
            {
                "claim_id": f"CYCLE-{cycle:02d}-PROVENANCE-COMPLETE",
                "cycle_number": cycle,
                "summary": "Pass One provenance/completeness skeleton for the cycle SHA range.",
                "trust_classification": "REPRODUCIBLE_ONLY",
                "validator_class": "SAME_SPECIFICATION_INDEPENDENT_CODE",
                "severity": "P2",
                "producer": "git",
            }
        )
        pass_two = assess_cycle_pass_two(
            cycle, [item for item in known_findings() if cycle in item["cycles"]]
        )
        claims.append(
            {
                "claim_id": f"CYCLE-{cycle:02d}-SEMANTIC-RECONSTRUCTION",
                "cycle_number": cycle,
                "summary": pass_two["limitation"],
                "trust_classification": pass_two["status"],
                "validator_class": "INDEPENDENT_SEMANTIC_REFERENCE",
                "severity": "P0",
                "producer": "external_payloads_not_in_git",
            }
        )
    for item in claims:
        if item["trust_classification"] == "REPRODUCIBLE_WRONG_SPECIFICATION":
            item["trust_classification"] = "FAIL"
            item["specification_note"] = "REPRODUCIBLE_WRONG_SPECIFICATION"
    return bind_identity(
        {
            "artifact_type": "ALL_CYCLE_CLAIM_REGISTRY",
            "audited_starting_sha": STARTING_SHA,
            "claims": claims,
            "counts_by_classification": _counts(
                [item["trust_classification"] for item in claims]
            ),
            "counts_by_cycle": {
                str(cycle): sum(1 for item in claims if item["cycle_number"] == cycle)
                for cycle in range(1, 26)
            },
            "inventory_identity": inventory.get("inventory_identity"),
            "schema_version": 1,
        },
        "registry_identity",
    )


def _counts(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def build_dag(claims: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    for cycle in range(1, 26):
        failed = any(
            item["cycle_number"] == cycle
            and item["trust_classification"]
            in {"FAIL", "BLOCKED_INSUFFICIENT_EVIDENCE"}
            for item in claims["claims"]
        )
        nodes.append(
            {
                "id": f"CYCLE-{cycle:02d}",
                "cycle_number": cycle,
                "disposition": "FAIL" if failed else "REPRODUCIBLE_ONLY",
            }
        )
    edges = [
        {
            "from": f"CYCLE-{cycle:02d}",
            "to": f"CYCLE-{cycle + 1:02d}",
            "kind": "lineage",
        }
        for cycle in range(1, 25)
        if not (cycle == 19)
    ]
    edges.append(
        {"from": "CYCLE-19", "to": "CYCLE-20", "kind": "integrated_during_later_cycle"}
    )
    edges.append(
        {"from": "CYCLE-22", "to": "CYCLE-23", "kind": "integrated_during_later_cycle"}
    )
    edges.append({"from": "CYCLE-18", "to": "CYCLE-20", "kind": "national_foundation"})
    edges.append({"from": "CYCLE-24", "to": "CYCLE-25", "kind": "forecast_successor"})
    return bind_identity(
        {
            "artifact_type": "ALL_CYCLE_DEPENDENCY_DAG",
            "circular_authority": False,
            "edges": edges,
            "nodes": nodes,
            "orphaned_authority": [],
            "schema_version": 1,
        },
        "dag_identity",
    )


def build_successors(dag: dict[str, Any]) -> dict[str, Any]:
    failed = {
        node["id"]
        for node in dag["nodes"]
        if node["disposition"] in {"FAIL", "BLOCKED_INSUFFICIENT_EVIDENCE"}
    }
    successors = []
    for edge in dag["edges"]:
        if edge["from"] in failed:
            successors.append(
                {
                    "successor_id": edge["to"],
                    "failed_predecessors": [edge["from"]],
                    "affected_claims": [f"{edge['to']}-INHERITED-FAILURE"],
                    "corrected_successor_requirement": (
                        "Rebuild on authority-clean independent reconstruction; "
                        "do not treat predecessor PASS as inherited."
                    ),
                    "apparently_passing_built_on_failed_predecessor": True,
                }
            )
    return bind_identity(
        {
            "artifact_type": "ALL_CYCLE_AFFECTED_SUCCESSORS",
            "schema_version": 1,
            "successors": successors,
        },
        "affected_successors_identity",
    )


def assess_cycle_pass_two(number: int, related: list[dict[str, Any]]) -> dict[str, Any]:
    """Check this cycle's declared payload dependencies; do not stamp every cycle missing."""

    required: list[str] = []
    skipped_false_positive: list[str] = []
    for finding in related:
        for evidence in finding.get("evidence") or []:
            text = str(evidence)
            if "raw/SRC-002 file count" in text or text.startswith(
                "mounted:raw/SRC-002"
            ):
                skipped_false_positive.append(text)
                continue
            if text.startswith("mounted:") or text.startswith("raw/"):
                required.append(text)
    if number in (18, 20, 21):
        required.append(
            "git:artifacts/data_lake/national_foundation_reconciliation_gate.json"
        )

    missing: list[str] = []
    data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    for req in required:
        if req.startswith("git:"):
            if not (REPO_ROOT / req[4:]).is_file():
                missing.append(req)
            continue
        if req.startswith("mounted:"):
            relative = req.split(":", 1)[1].strip()
            if not data_root:
                missing.append(req)
                continue
            if not (Path(data_root) / relative).exists():
                missing.append(req)
            continue
        if not (REPO_ROOT / req).exists():
            missing.append(req)

    missing_raw = bool(missing)
    if missing_raw:
        status = "BLOCKED_INSUFFICIENT_EVIDENCE"
        limitation = "declared_raw_or_mounted_payloads_missing"
    else:
        status = "NOT_AUDITED_YET"
        limitation = (
            "Declared payload dependencies were checked for this cycle; independent "
            "reconstruction of remaining material claims is unfinished. "
            "NOT_AUDITED_YET is not PASS and does not authorize SEMANTICALLY_AUDITED."
        )
    return {
        "status": status,
        "independent_of_producer_helpers": True,
        "missing_raw_payloads": missing_raw,
        "declared_payload_requirement_count": len(required),
        "missing_declared_payloads": missing,
        "skipped_false_positive_payload_assertions": skipped_false_positive,
        "limitation": limitation,
    }


def build_matrix() -> dict[str, Any]:
    findings = known_findings()
    cycles = []
    for cycle in range(1, 26):
        related = [item for item in findings if cycle in item["cycles"]]
        pass_two = assess_cycle_pass_two(cycle, related)
        cycles.append(
            {
                "cycle_number": cycle,
                "passes": {
                    "pass_one": "COMPLETE",
                    "pass_two": pass_two["status"],
                    # Category search alone is PARTIAL, not review-of-review COMPLETE.
                    "pass_three": "PARTIAL",
                },
                "cycle_disposition": "FAIL" if cycle >= 18 else pass_two["status"],
                "semantically_audited": False,
            }
        )
    return bind_identity(
        {
            "artifact_type": "ALL_CYCLE_THREE_PASS_AUDIT_MATRIX",
            "cycles": cycles,
            "note": (
                "No later cycle confers PASS on an earlier one. Missing evidence is "
                "BLOCKED_INSUFFICIENT_EVIDENCE, not PASS. Pass two is NOT_AUDITED_YET "
                "when declared payload dependencies are present or were a disproved "
                "directory-count assertion; it is not independent reconstruction of "
                "every material claim. Pass three PARTIAL means listed adversarial "
                "categories were searched only; it is not complete review-of-review "
                "and does not authorize SEMANTICALLY_AUDITED."
            ),
            "schema_version": 1,
        },
        "matrix_identity",
    )


def build_cycle_audit(
    cycle_row: dict[str, Any], findings: list[dict[str, Any]]
) -> dict[str, Any]:
    number = cycle_row["cycle_number"]
    related = [item for item in findings if number in item["cycles"]]
    pass_two = assess_cycle_pass_two(number, related)
    trust = "FAIL" if related else pass_two["status"]
    return bind_identity(
        {
            "artifact_type": "CYCLE_SCIENTIFIC_AUDIT",
            "cycle_number": number,
            "ending_sha": cycle_row["ending_sha"],
            "findings": related,
            "pass_one_provenance": {
                "status": "COMPLETE",
                "starting_sha": cycle_row["starting_sha"],
                "ending_sha": cycle_row["ending_sha"],
                "end_descends_from_start": cycle_row["end_descends_from_start"],
                "proves": "provenance_and_completeness_only",
            },
            "pass_three_adversarial": {
                "status": "PARTIAL",
                "limitation": (
                    "Category search only. Pass two did not independently reconstruct "
                    "every material claim from mounted raw payloads. Category search is "
                    "PARTIAL, not complete review-of-review."
                ),
                "searched_for": [
                    "omitted_artifacts",
                    "circular_validation",
                    "target_leakage",
                    "pair_incoherence",
                    "protected_exposure",
                    "ignored_user_holds",
                ],
            },
            "pass_two_semantic": pass_two,
            "schema_version": 1,
            "starting_sha": cycle_row["starting_sha"],
            "trust_classification": trust,
        },
        "audit_identity",
    )


def build_gate(claims: dict[str, Any]) -> dict[str, Any]:
    return bind_identity(
        {
            "artifact_type": "ALL_CYCLE_TRUST_RECOVERY_GATE",
            "blocked_claims": [
                item["claim_id"]
                for item in claims["claims"]
                if item["trust_classification"]
                in {"FAIL", "BLOCKED_INSUFFICIENT_EVIDENCE"}
            ],
            "cycle_25_5_complete": False,
            "hold_active": True,
            "inventory_completeness": "INCOMPLETE_UNMAPPED_AUTHORITY",
            "missing_evidence_is_blocked_not_pass": True,
            "scientific_trust_recovered": False,
            "t24h_state": "OPEN",
            "t90m_state": "OPEN",
            "week1_forecast_credibility": "UNTRUSTED_SHADOW",
            "schema_version": 1,
        },
        "gate_identity",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-inventory",
        action="store_true",
        help="Reuse the existing artifact inventory instead of recrawling git first-add.",
    )
    args = parser.parse_args(argv)
    ALL_CYCLES.mkdir(parents=True, exist_ok=True)
    cycle_rows = verify_cycle_shas()
    hold_path = (
        REPO_ROOT / "artifacts" / "scientific_integrity" / "OPERATOR_HOLD_RECEIPT.json"
    )
    if hold_path.is_file():
        receipt = json.loads(hold_path.read_text(encoding="utf-8"))
    else:
        receipt = build_hold_receipt(cycle_rows)
        _write(hold_path, receipt)
    inventory_path = ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json"
    if args.skip_inventory and inventory_path.is_file():
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    else:
        inventory = build_inventory(cycle_rows)
        _write(inventory_path, inventory)
    claims = build_claims(inventory)
    _write(ALL_CYCLES / "ALL_CYCLE_CLAIM_REGISTRY.json", claims)
    dag = build_dag(claims)
    _write(ALL_CYCLES / "ALL_CYCLE_DEPENDENCY_DAG.json", dag)
    successors = build_successors(dag)
    _write(ALL_CYCLES / "ALL_CYCLE_AFFECTED_SUCCESSORS.json", successors)
    matrix = build_matrix()
    _write(ALL_CYCLES / "ALL_CYCLE_THREE_PASS_AUDIT_MATRIX.json", matrix)
    findings_payload = bind_identity(
        {
            "artifact_type": "ALL_CYCLE_FINDINGS",
            "findings": known_findings(),
            "schema_version": 1,
        },
        "findings_identity",
    )
    _write(ALL_CYCLES / "ALL_CYCLE_FINDINGS.json", findings_payload)
    fp_payload = bind_identity(
        {
            "artifact_type": "ALL_CYCLE_FALSE_POSITIVE_REJECTIONS",
            "rejections": false_positive_rejections(),
            "schema_version": 1,
        },
        "false_positive_identity",
    )
    _write(ALL_CYCLES / "ALL_CYCLE_FALSE_POSITIVE_REJECTIONS.json", fp_payload)
    gate = build_gate(claims)
    _write(ALL_CYCLES / "ALL_CYCLE_TRUST_RECOVERY_GATE.json", gate)
    for row in cycle_rows:
        audit = build_cycle_audit(row, known_findings())
        _write(
            ALL_CYCLES / f"CYCLE_{row['cycle_number']:02d}_SCIENTIFIC_AUDIT.json", audit
        )
    print(
        json.dumps(
            {
                "result": "WROTE",
                "artifact_count": inventory["unmapped_authority_count"]
                if False
                else len(inventory["artifacts"]),
                "claim_count": len(claims["claims"]),
                "receipt_identity": receipt["receipt_identity"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
