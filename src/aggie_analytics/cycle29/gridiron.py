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
    return {
        "artifact_type": "CYCLE29_ALL22_SNAPSHOT",
        "repos": inventory.get("repos", []),
        "worktrees": inventory.get("worktrees", []),
        "prs": inventory.get("prs", []),
        "c01_consumed": False,
        "c01_state": "BLOCKED_NO_IMMUTABLE_RELEASE_BOM",
        "synthetic_fixtures_are_bounded_compatibility_only": True,
        "dirty_programspecifications_not_overwritten": True,
    }


def coaching_contract_vnext() -> dict[str, Any]:
    return {
        "contract_id": "GRIDIRON-COACHING-CONTRACT-VNEXT-CYCLE29",
        "role_level_unknowns_explicit": True,
        "responsibility_episodes_separate_from_titles": True,
        "play_caller_not_inferred_from_coordinator": True,
    }
