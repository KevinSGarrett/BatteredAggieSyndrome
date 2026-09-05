"""Classify branch/worktree records. Deletion is never implied by age alone."""

from __future__ import annotations

from typing import Any, Mapping

ACTIVE_STATES = {
    "ACTIVE_PR",
    "ACTIVE_UNMERGED_WORK",
    "PRESERVATION_RETAIN",
    "UNRELATED_OWNER_RETAIN",
    "DIVERGED_OR_UNKNOWN_BLOCKED",
}
DISPOSABLE_STATES = {
    "MERGED_OBSOLETE_ELIGIBLE",
    "REMOTE_GONE_TRACKING_ONLY",
}


def classify_branch(record: Mapping[str, Any]) -> str:
    if record.get("is_default") or record.get("protected") or record.get("preservation"):
        return "PRESERVATION_RETAIN"
    if record.get("open_pr"):
        return "ACTIVE_PR"
    if record.get("locked_worktree") or record.get("dirty_worktree"):
        return "ACTIVE_UNMERGED_WORK"
    if record.get("unique_unmerged"):
        return "ACTIVE_UNMERGED_WORK"
    if record.get("unrelated_owner"):
        return "UNRELATED_OWNER_RETAIN"
    if record.get("closed_unmerged_pr") and not record.get("squash_or_merge_tree_equivalent"):
        return "DIVERGED_OR_UNKNOWN_BLOCKED"
    if record.get("missing_upstream") and not record.get("squash_or_merge_tree_equivalent"):
        return "DIVERGED_OR_UNKNOWN_BLOCKED"
    if record.get("age_days") is not None and not record.get("squash_or_merge_tree_equivalent"):
        if not record.get("merged_obsolete_proven"):
            return "DIVERGED_OR_UNKNOWN_BLOCKED"
    if record.get("squash_or_merge_tree_equivalent") and record.get("merged_obsolete_proven"):
        if record.get("tip_matches_last_verified") and not record.get("open_pr"):
            return "MERGED_OBSOLETE_ELIGIBLE"
    if record.get("remote_gone") and record.get("tracking_only"):
        return "REMOTE_GONE_TRACKING_ONLY"
    return "DIVERGED_OR_UNKNOWN_BLOCKED"


def deletion_allowed(record: Mapping[str, Any]) -> bool:
    state = classify_branch(record)
    if state not in DISPOSABLE_STATES:
        return False
    if record.get("tip_changed_since_inventory"):
        return False
    if record.get("open_pr") or record.get("locked_worktree") or record.get("dirty_worktree"):
        return False
    if record.get("preservation") or record.get("protected") or record.get("is_default"):
        return False
    if record.get("force_delete_required") and not record.get("explicit_force_approval"):
        return False
    return True


def local_prune_is_not_remote_deletion(record: Mapping[str, Any]) -> bool:
    return bool(record.get("local_prune_only")) and not bool(
        record.get("remote_compare_and_delete_succeeded")
    )
