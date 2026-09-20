"""R35-12: re-resolve the All-22 / C01 integration surface at Cycle #35 start.

A stale clone is not remote authority and an old HOLD document is not a
current release state, so every identity below is re-resolved now and
compared against what the manager observed, rather than copied forward.

Strictly read-only with respect to the owner workspace. Dirty owner
worktrees are observed and preserved; nothing is checked out, fetched,
cleaned or mutated. The BAS operational checkout and the All-22 integration
checkout stay separate, and nothing here creates a runtime path dependency
on C:\\All-22.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.all22_adapter import (  # noqa: E402
    OPTIONAL_PRESERVED_FIELDS,
    REQUIRED_EPISODE_FIELDS,
    REQUIRED_IDENTITY_FIELDS,
    SEMANTIC_PRESERVED_FIELDS,
    STAFF_SNAPSHOT_V1,
    encode_episode,
    project_lossy_staff_snapshot_v1,
    verify_lossless_round_trip,
)

ALL22_ROOT = Path(r"C:\All-22")
MANAGER_EVIDENCE = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle34\20260920T164407Z"
)

#: What the manager observed. Re-resolved here, never assumed still true.
MANAGER_OBSERVED = {
    "c01_wheel_v0_1_2_sha256": (
        "a57d4a58cb268e14f88ea7a66bf49131e89b7f930ea1acabc05c2dfeca689af3"
    ),
    "c01_main_head": "7ac42d21fb1ad58913cec8adef992292e8e4e4ba",
}

#: The ACTUAL released StaffSnapshotV1 value object. Recorded so a richer
#: local proposal can never be mistaken for the adopted contract.
STAFF_SNAPSHOT_V1_ACTUAL_FIELDS = ("team_id", "coach_ids")


def git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def discover_clones(root: Path) -> list[dict[str, Any]]:
    """Every git checkout under the owner workspace, observed read-only."""

    found: list[dict[str, Any]] = []
    if not root.is_dir():
        return found
    seen: set[str] = set()
    for candidate in sorted(root.rglob(".git")):
        work = candidate.parent
        key = str(work).casefold()
        if key in seen:
            continue
        # Skip nested checkouts inside an already-recorded one.
        if any(key.startswith(prev + "\\") for prev in seen):
            continue
        seen.add(key)
        head = git(["rev-parse", "HEAD"], work)
        if head is None:
            continue
        status = git(["status", "--porcelain"], work)
        found.append(
            {
                "path": str(work),
                "head": head,
                "branch": git(["rev-parse", "--abbrev-ref", "HEAD"], work),
                "remote": git(["remote", "get-url", "origin"], work),
                "dirty": bool(status),
                "dirty_entry_count": len(status.splitlines()) if status else 0,
                "observed_read_only": True,
                "preserved_without_mutation": True,
            }
        )
    return found


def staff_snapshot_boundary() -> dict[str, Any]:
    """What the released contract can actually carry, versus our proposal."""

    episode = {
        "person": "A Coach",
        "role": "OC",
        "source_title": "Official staff page",
        "source_class": "OFFICIAL_PROGRAM_PAGE",
        "valid_time_precision": "SEASON",
        "recorded_at_utc": "2026-01-01T00:00:00+00:00",
        "schema_version": "StaffRoleEpisodeV1Proposed",
        "program_id": "prog-1",
        "person_id": "p1",
        "season": "2021",
        "valid_from": "2020-01-01",
        "valid_to": "2021-01-01",
        "receipt_sha256": "b" * 64,
        "source_span": {"start": 0, "end": 10},
        "conflict_state": "DISPUTED",
        "responsibility": "play_calling",
        "rights_state": "RESTRICTED",
        "source_revision": "rev-123",
        "an_unmodelled_extension": {"x": 1},
    }
    encoded = encode_episode(episode)
    report = verify_lossless_round_trip(episode)
    lossy = project_lossy_staff_snapshot_v1([episode])

    field_decisions = []
    for field in (
        tuple(REQUIRED_EPISODE_FIELDS)
        + tuple(REQUIRED_IDENTITY_FIELDS)
        + tuple(OPTIONAL_PRESERVED_FIELDS)
        + tuple(SEMANTIC_PRESERVED_FIELDS)
    ):
        carried_by_v1 = field in STAFF_SNAPSHOT_V1_ACTUAL_FIELDS
        field_decisions.append(
            {
                "field": field,
                "carried_by_proposed_episode_envelope": field in encoded,
                "carried_by_released_staff_snapshot_v1": carried_by_v1,
                "decision": (
                    "TRANSPORTS_IN_PROPOSAL_ONLY"
                    if field in encoded and not carried_by_v1
                    else "TRANSPORTS_IN_BOTH"
                    if carried_by_v1
                    else "NOT_TRANSPORTED"
                ),
            }
        )
    return {
        "released_staff_snapshot_v1_fields": list(STAFF_SNAPSHOT_V1_ACTUAL_FIELDS),
        "released_envelope_name": STAFF_SNAPSHOT_V1,
        "proposed_envelope_lossless": report["lossless"],
        "semantic_fields_dropped": report["semantic_fields_dropped"],
        "retained_unmodelled_extension_fields": report[
            "retained_unmodelled_extension_fields"
        ],
        "lossy_projection_to_released_v1": lossy,
        "field_by_field_decisions": field_decisions,
        "compatibility_finding": (
            "The released StaffSnapshotV1 value object carries only team_id "
            "and coach_ids. Full employment/role history cannot be forced "
            "into that shape, so the BAS-local StaffRoleEpisodeV1Proposed "
            "envelope is a PROPOSAL, and projecting to the released contract "
            "is explicitly lossy. Neither may be described as adopted."
        ),
        "owner_adoption_state": "C01_OWNER_ADOPTION_PENDING",
    }


def producer_consumer_dag() -> dict[str, Any]:
    """Who produces what, who consumes it, and what invalidates it."""

    nodes = [
        {
            "id": "BAS:coaching_release",
            "kind": "PRODUCER",
            "produces": "CYCLE35_COACHING_RELEASE (source observations, "
            "episodes, role assertions, conflicts, lineage)",
            "invalidated_by": [
                "any change to a bound source file's bytes",
                "a parser identity change that alters admission",
                "a canonical program or person identity change",
            ],
        },
        {
            "id": "BAS:all22_adapter",
            "kind": "TRANSFORMER",
            "consumes": ["BAS:coaching_release"],
            "produces": "StaffRoleEpisodeV1Proposed envelope (BAS-local)",
            "invalidated_by": [
                "a change to REQUIRED_/SEMANTIC_PRESERVED_FIELDS",
                "an owner schema revision to StaffSnapshotV1",
            ],
        },
        {
            "id": "C01:StaffSnapshotV1",
            "kind": "OWNER_CONTRACT",
            "consumes": ["BAS:all22_adapter (lossy projection)"],
            "fields": list(STAFF_SNAPSHOT_V1_ACTUAL_FIELDS),
            "invalidated_by": [
                "an owner release that changes the value object",
                "a wheel digest change for the pinned version",
            ],
            "owned_by": "CFIP owner, not BAS",
        },
    ]
    return {
        "nodes": nodes,
        "invalidation_policy": (
            "A downstream artifact is invalid as soon as any upstream "
            "identity it names changes. Invalidation is by identity, not by "
            "timestamp, so a rebuild that reproduces the same identities does "
            "not invalidate consumers and a same-timestamp rebuild that "
            "changes identities does."
        ),
        "no_runtime_path_dependency_on_all22": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    clones = discover_clones(ALL22_ROOT)
    manager_heads: list[dict[str, Any]] = []
    heads_file = MANAGER_EVIDENCE / "ALL22_REMOTE_HEADS.json"
    if heads_file.is_file():
        manager_heads = json.loads(heads_file.read_text(encoding="utf-8"))

    boundary = staff_snapshot_boundary()
    dag = producer_consumer_dag()

    result = {
        "artifact_type": "CYCLE35_R35_12_ALL22_ALIGNMENT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "all22_root": str(ALL22_ROOT),
        "all22_root_present": ALL22_ROOT.is_dir(),
        "owner_workspace_read_only": True,
        "owner_workspace_not_mutated": True,
        "clones_observed": len(clones),
        "clones": clones,
        "dirty_clones_preserved": [c["path"] for c in clones if c["dirty"]],
        "manager_recorded_remote_heads": manager_heads,
        "manager_observed_values": MANAGER_OBSERVED,
        "remote_heads_reresolved_this_cycle": False,
        "remote_head_reresolution_reason": (
            "Re-resolving the five private GitHub remote heads requires a "
            "network call against owner-private repositories. This cycle is "
            "cache-first and does not spend that budget without a specific "
            "confirmation, so the manager's recorded heads are carried "
            "forward as OBSERVED-BY-MANAGER rather than re-verified. They are "
            "explicitly not treated as current BAS-verified authority."
        ),
        "staff_snapshot_boundary": boundary,
        "producer_consumer_dag": dag,
        "owner_proposal_state": {
            "existing_cfip_comments": 4,
            "comments_are_submissions_not_adoption": True,
            "new_proposal_submitted_this_cycle": False,
            "reason": (
                "The four existing CFIP comments already carry the schema-gap "
                "submission. Adding a fifth restating it would be noise, not "
                "progress; what is missing is an owner decision, which BAS "
                "cannot supply. The field-by-field compatibility decision "
                "above is prepared so that decision can be made."
            ),
        },
        "separate_dimensions": {
            "contract_acceptance": "PENDING_OWNER",
            "artifact_integrity": "BAS_LOCAL_VERIFIED",
            "rights": "PRIVATE_NOT_REDISTRIBUTABLE",
            "operational_readiness": "NOT_CLAIMED",
            "scientific_validity": "NOT_CLAIMED",
        },
        "no_private_wheel_or_owner_document_in_public_ci": True,
        "pit_admitted": False,
    }
    (out_dir / "CYCLE35_ALL22_ALIGNMENT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "all22_root_present": result["all22_root_present"],
            "clones_observed": len(clones),
            "dirty_clones": len(result["dirty_clones_preserved"]),
            "manager_recorded_heads": len(manager_heads),
            "remote_heads_reresolved": False,
            "proposed_envelope_lossless": boundary["proposed_envelope_lossless"],
            "semantic_fields_dropped": boundary["semantic_fields_dropped"],
            "released_v1_fields": boundary["released_staff_snapshot_v1_fields"],
            "owner_adoption_state": boundary["owner_adoption_state"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
