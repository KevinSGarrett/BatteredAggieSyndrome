"""BAS-owned Gridiron Cortex consumer boundary. Synthetic fixtures only."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

ALLOWED_CLAIM = "GRIDIRON_CORTEX_CONSUMER_BOUNDARY_SCAFFOLDED_WITH_SYNTHETIC_FIXTURES"
FORBIDDEN_CLAIMS = {
    "GRIDIRON_CORTEX_INTEGRATED",
    "FILM_FEATURES_ADMITTED",
    "LANE_RUNTIME_OPERATIONAL",
}
DEFAULT_FORBIDDEN_ROOT = Path(r"C:\All-22")
DRIFTED = "DRIFTED_NOT_CONSUMABLE"
UNCOMMISSIONED = "BLOCKED_UNCOMMISSIONED"
TRANSFER_PREPARED = "BAS_REPOSITORY_TRANSFER_PREPARED_NOT_AUTHORIZED"


class GridironBoundaryError(ValueError):
    """Raised when a Gridiron payload or snapshot cannot be consumed."""


def reject_default_all22_path(root: Path | None) -> None:
    if root is None:
        return
    resolved = root.resolve()
    if resolved == DEFAULT_FORBIDDEN_ROOT or DEFAULT_FORBIDDEN_ROOT in resolved.parents:
        raise GridironBoundaryError("All-22 local path cannot be a runtime dependency")


def reject_uncommissioned_or_drifted(
    *,
    foundation_bound_head: str,
    observed_contracts_head: str,
    part3_blocked: bool,
    commissioned: bool,
) -> str:
    if part3_blocked or not commissioned:
        return UNCOMMISSIONED
    if foundation_bound_head != observed_contracts_head:
        return DRIFTED
    return "SNAPSHOT_CONSUMABLE"


def reject_mutable_worktree_as_bom(dirty: bool, unreleased_branch: bool) -> None:
    if dirty or unreleased_branch:
        raise GridironBoundaryError(
            "mutable All-22 branch/worktree cannot be treated as a release BOM"
        )


def reject_film_auto_admit(auto_admitted: bool) -> None:
    if auto_admitted:
        raise GridironBoundaryError("Film package cannot be auto-admitted")


def reject_programops_runtime(is_runtime_authority: bool) -> None:
    if is_runtime_authority:
        raise GridironBoundaryError("ProgramOps cannot be runtime/scientific authority")


def reject_forbidden_claim(claim: str) -> None:
    if claim in FORBIDDEN_CLAIMS:
        raise GridironBoundaryError(f"forbidden claim {claim}")
    if claim != ALLOWED_CLAIM:
        raise GridironBoundaryError(f"unsupported consumer-boundary claim {claim}")


def reject_incompatible_payload(payload: Mapping[str, Any], *, adapter_version: str) -> None:
    if payload.get("contract_version") != adapter_version:
        raise GridironBoundaryError("incompatible version")
    if payload.get("unknown_schema"):
        raise GridironBoundaryError("unknown schema")
    if payload.get("future_known"):
        raise GridironBoundaryError("future-known data")
    if payload.get("identity_conflict"):
        raise GridironBoundaryError("identity conflict")
    if payload.get("rights_restricted"):
        raise GridironBoundaryError("rights restriction")
    if payload.get("missing_field"):
        raise GridironBoundaryError("missing field")
    if payload.get("invalid_uncertainty"):
        raise GridironBoundaryError("invalid uncertainty")
    if payload.get("ood"):
        raise GridironBoundaryError("OOD")
    if payload.get("snapshot_state") in {DRIFTED, UNCOMMISSIONED}:
        raise GridironBoundaryError("uncommissioned/drifted C01 snapshot admitted")


def classify_breaking_change(
    *,
    grain_changed: bool,
    identity_changed: bool,
    time_changed: bool,
    units_changed: bool,
    missingness_changed: bool,
    uncertainty_changed: bool,
    rights_changed: bool,
    enums_changed: bool,
    upstream_label: str,
) -> str:
    breaking = any(
        (
            grain_changed,
            identity_changed,
            time_changed,
            units_changed,
            missingness_changed,
            uncertainty_changed,
            rights_changed,
            enums_changed,
        )
    )
    if breaking and upstream_label in {"patch", "compatible", "nonbreaking"}:
        return "BREAKING_DESPITE_UPSTREAM_LABEL"
    return "BREAKING" if breaking else "COMPATIBLE"


def require_affected_claim_invalidation(
    contract_changed: bool, invalidated_claims: Sequence[str]
) -> None:
    if contract_changed and not invalidated_claims:
        raise GridironBoundaryError(
            "changed All-22 contract without affected-BAS-claim invalidation"
        )


def load_synthetic_adapter(fixture_root: Path | None, installed_package_root: Path | None) -> dict[str, str]:
    if fixture_root is None and installed_package_root is None:
        raise GridironBoundaryError("adapter must not default to C:\\All-22")
    for candidate in (fixture_root, installed_package_root):
        if candidate is not None:
            reject_default_all22_path(candidate)
    return {
        "claim": ALLOWED_CLAIM,
        "imported_fields_state": "QUARANTINE_CANDIDATE",
        "runtime_all22_dependency": "false",
    }


def reject_active_checkout_move(active_root: Path, all22_root: Path) -> None:
    active = str(active_root).replace("\\", "/").rstrip("/").lower()
    all22 = str(all22_root).replace("\\", "/").rstrip("/").lower()
    if active == f"{all22}/repos/batteredaggiesyndrome" or active.startswith(all22 + "/"):
        raise GridironBoundaryError("active BAS checkout physically moved into C:\\All-22")


def reject_integration_clone_as_authority(clone_is_authoritative: bool) -> None:
    if clone_is_authoritative:
        raise GridironBoundaryError(
            "integration clone cannot be the authoritative BAS checkout or runtime source"
        )


def reject_disconnected_target_created(created: bool) -> None:
    if created:
        raise GridironBoundaryError(
            "disconnected target repository cannot be created instead of preserving GitHub identity"
        )


def reject_unauthorized_transfer(executed: bool, authorized: bool) -> None:
    if executed and not authorized:
        raise GridironBoundaryError("GitHub transfer attempted without separate exact authorization")


def reject_transfer_as_science(claim: str) -> None:
    if claim in {"scientific_trust_recovered", "all22_admitted"}:
        raise GridironBoundaryError(
            "repository ownership transfer cannot be represented as scientific trust or All-22 admission"
        )


def reject_secret_values_in_inventory(inventory: Mapping[str, Any]) -> None:
    for key, value in inventory.items():
        lowered = str(key).lower()
        if any(token in lowered for token in ("secret", "token", "password", "api_key", "_key")):
            if value not in {None, "", "***", "[REDACTED_NAME_ONLY]"} and not str(key).endswith("_name"):
                raise GridironBoundaryError("secret values exported in the pre-transfer settings inventory")
