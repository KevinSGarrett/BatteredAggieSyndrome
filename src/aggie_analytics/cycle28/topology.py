"""BAS repository topology, clone roles, and transfer-readiness helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

ACTIVE_ROOT_NAME = "BatteredAggieSyndrome"
INTEGRATION_MARKER = Path("All-22") / "repos" / "BatteredAggieSyndrome"
TRANSFER_PREPARED = "BAS_REPOSITORY_TRANSFER_PREPARED_NOT_AUTHORIZED"
UNMERGED_UNIQUE = "UNMERGED_UNIQUE_HISTORY"


class TopologyError(ValueError):
    """Raised when clone roles or transfer readiness are violated."""


def classify_clone(root: Path) -> str:
    posix = root.as_posix().replace("\\", "/")
    if posix.endswith("/All-22/repos/BatteredAggieSyndrome") or posix.endswith(
        "/All-22/repos/BatteredAggieSyndrome/"
    ):
        return "INTEGRATION_CLONE"
    if posix.endswith("/BatteredAggieSyndrome") or posix.endswith("/BatteredAggieSyndrome/"):
        return "ACTIVE_AUTHORITATIVE_CHECKOUT"
    return "UNKNOWN"


def reject_role_confusion(active_root: Path, integration_root: Path) -> None:
    if classify_clone(active_root) != "ACTIVE_AUTHORITATIVE_CHECKOUT":
        raise TopologyError("active checkout role cannot be reconstructed")
    if classify_clone(integration_root) != "INTEGRATION_CLONE":
        raise TopologyError("integration clone role cannot be reconstructed")
    if active_root.resolve() == integration_root.resolve():
        raise TopologyError("active and integration clones must be non-overlapping")


def classify_branch(
    *,
    live_owner: bool,
    open_pr: bool,
    unique_commits: Sequence[str],
    merged: bool,
    preservation: bool,
) -> str:
    if live_owner:
        return "ACTIVE_LIVE_OWNER"
    if open_pr:
        return "OPEN_PR_HEAD"
    if unique_commits and not merged:
        return UNMERGED_UNIQUE
    if preservation:
        return "PRESERVATION_RETAIN"
    if merged and not unique_commits and not live_owner and not open_pr:
        return "MERGED_SAFE_TO_DELETE"
    return "STALE_REQUIRES_USER_DECISION"


def reject_cfip_replacing_bat(bat_owner_omitted: bool, cfip_replaces_bat: bool) -> None:
    if bat_owner_omitted or cfip_replaces_bat:
        raise TopologyError("BAT ownership cannot be replaced by CFIP")


def reject_generic_plan_as_substantive(source_atoms: Sequence[Any], line_count: int) -> str:
    if not source_atoms and line_count <= 54:
        return "PLAN_STRUCTURE_PRESENT_SUBSTANTIVE_BAS_INTEGRATION_INCOMPLETE"
    if not source_atoms:
        return "EMPTY_SOURCE_ATOMS_WITH_MAPPED_EVIDENCE"
    return "SUBSTANTIVE"


def reject_generated_index_as_completeness(used_as_proof: bool) -> None:
    if used_as_proof:
        raise TopologyError(
            "generated requirement/capability indexes cannot prove substantive specification completeness"
        )


def reject_freeform_c01_staff(complete: bool, freeform_role: bool) -> None:
    if complete and freeform_role:
        raise TopologyError(
            "free-form coach role or player availability string is not a complete C01 interface"
        )


def reject_orphaned_link(orphaned: bool, circular: bool, stale: bool, duplicative: bool) -> None:
    if orphaned or circular or stale or duplicative:
        raise TopologyError("orphaned, circular, stale or responsibility-duplicating BAT/CFIP link")


def transfer_conclusion(authorized: bool, executed: bool) -> str:
    if executed and not authorized:
        raise TopologyError("unauthorized transfer")
    if authorized and executed:
        return "TRANSFER_EXECUTED"
    return TRANSFER_PREPARED
