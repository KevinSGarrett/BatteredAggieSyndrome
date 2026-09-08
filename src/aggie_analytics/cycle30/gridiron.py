"""All-22 / Gridiron Cortex qualification. Do not consume C01 without an immutable BOM."""

from __future__ import annotations

from typing import Any, Mapping


class GridironError(ValueError):
    """Raised when All-22 qualification contracts fail."""


def reject_stale_c01(manifest_released: bool, bom_pass: bool, consumed: bool) -> None:
    if consumed and not (manifest_released and bom_pass):
        raise GridironError("stale C01 manifest/BOM cannot be treated as released")


def reject_skipped_integration_as_compat(
    skipped: bool, claimed_compatible: bool
) -> None:
    if skipped and claimed_compatible:
        raise GridironError(
            "skipped integration test cannot be treated as compatibility"
        )


def reject_obsolete_foundation(
    current_recovery_contradicts: bool, older_pass_used: bool
) -> None:
    if current_recovery_contradicts and older_pass_used:
        raise GridironError(
            "obsolete FoundationControl state cannot override current evidence"
        )


def snapshot(inventory: Mapping[str, Any]) -> dict[str, Any]:
    repos = list(inventory.get("repos") or [])
    worktrees = list(inventory.get("worktrees") or [])
    prs = list(inventory.get("prs") or [])
    return {
        "artifact_type": "CYCLE30_ALL22_SNAPSHOT",
        "repos": repos,
        "worktrees": worktrees,
        "prs": prs,
        "repo_count": len(repos),
        "worktree_count": len(worktrees),
        "pr_count": len(prs),
        "c01_manifest_object_count": inventory.get("c01_manifest_object_count"),
        "c01_manifest_fixture_count": inventory.get("c01_manifest_fixture_count"),
        "c01_catalog_object_count": inventory.get("c01_catalog_object_count"),
        "c01_catalog_fixture_count": inventory.get("c01_catalog_fixture_count"),
        "c01_manifest_catalog_reconciled": False,
        "c01_consumed": False,
        "c01_state": "BLOCKED_NO_IMMUTABLE_RELEASE_BOM",
        "synthetic_fixtures_are_bounded_compatibility_only": True,
        "dirty_programspecifications_not_overwritten": True,
        "four_field_boolean_snapshot_insufficient": True,
    }


def coaching_contract_vnext() -> dict[str, Any]:
    return {
        "contract_id": "GRIDIRON-COACHING-CONTRACT-VNEXT-CYCLE30",
        "role_level_unknowns_explicit": True,
        "responsibility_episodes_separate_from_titles": True,
        "play_caller_not_inferred_from_coordinator": True,
        "schema": "proposed/StaffSnapshotV2",
        "adoption": "PENDING_OWNER",
    }


def reject_missing_release_bom(
    *, manifest_objects: int | None, catalog_objects: int | None, consumed: bool
) -> None:
    if consumed:
        raise GridironError("C01 consumption blocked until release/BOM pass")
    if manifest_objects is None or catalog_objects is None:
        raise GridironError("C01 manifest/catalog counts must be observed")
    if manifest_objects != catalog_objects:
        # Recorded disagreement is not patched in place.
        return
