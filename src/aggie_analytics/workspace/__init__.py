"""Workspace path governance for BAS tools.

TP37-S (Cycle 37) repair. Everything that used to be a machine-specific
literal -- ``C:\\bas35q``, ``C:\\basc36lane`` -- resolves through
:mod:`aggie_analytics.workspace.paths` instead, so a root is declared once,
validated, and owned rather than invented per tool.
"""

from .paths import (  # noqa: F401
    MAX_ROOT_LENGTH,
    PATH_BUDGET_TOTAL,
    WORST_CASE_RELATIVE_LENGTH,
    PathBudgetExceeded,
    RunWorkspace,
    SeedContractError,
    UnownedWorkspace,
    UnsafeNameComponent,
    WorkspaceBoundaryError,
    WorkspaceError,
    WorkspaceLayout,
    allocate_run_workspace,
    assert_no_reparse_ancestor,
    assert_safe_component,
    assert_within,
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
    clear_owned_subtree,
    free_bytes,
    prepare_explicit_workspace,
    require_free_bytes,
    resolve_layout,
    resolve_seed,
)

__all__ = [
    "MAX_ROOT_LENGTH",
    "PATH_BUDGET_TOTAL",
    "WORST_CASE_RELATIVE_LENGTH",
    "PathBudgetExceeded",
    "RunWorkspace",
    "SeedContractError",
    "UnownedWorkspace",
    "UnsafeNameComponent",
    "WorkspaceBoundaryError",
    "WorkspaceError",
    "WorkspaceLayout",
    "allocate_run_workspace",
    "assert_no_reparse_ancestor",
    "assert_safe_component",
    "assert_within",
    "atomic_write_bytes",
    "atomic_write_json",
    "atomic_write_text",
    "clear_owned_subtree",
    "free_bytes",
    "prepare_explicit_workspace",
    "require_free_bytes",
    "resolve_layout",
    "resolve_seed",
]
