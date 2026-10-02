r"""Resolved, budgeted, owned workspace paths for BAS tools.

TP37-S repair. Three defects motivated this module and each one is addressed
by a named function here rather than by a comment:

1. ``tools/cycle36/c36_12_family_b_composed.py`` hardcoded
   ``SEED = Path(r"C:\bas35q")``. A directory created as disposable Cycle 35
   qualification scratch had silently become an undeclared *input* to later
   validation, so the scratch could not be cleaned without breaking
   qualification, and the qualification could not be reproduced on another
   machine at all. :func:`resolve_seed` replaces the literal with an explicit
   configured location plus a *versioned seed contract*: the seed must declare
   which contract it satisfies, and the declared identity must match before a
   single byte is read.

2. ``tools/cycle36/c36_15_validation.py`` hardcoded ``C:\basc36lane`` and then
   called ``shutil.rmtree(..., ignore_errors=True)`` on it before every run.
   Two concurrent runs would delete each other's workspace, an unrelated
   directory that happened to occupy the name would be destroyed without
   comment, and a cleanup failure was silently discarded.
   :func:`allocate_run_workspace` gives every run its own namespace under a
   declared root and stamps an ownership marker; :meth:`RunWorkspace.release`
   refuses to delete anything it does not own and raises on failure instead of
   swallowing it.

3. The short ``C:\bas*`` roots were not arbitrary: the successor lake is
   content-addressed (``features/<name>/sha256/<64 hex>/<file>``) and nesting
   that under a normal run directory pushed the destination past the Windows
   MAX_PATH limit, so copies failed and the lane reported a qualification
   failure that belonged to the path. That constraint is real, so it is
   *measured and enforced* here (:data:`MAX_ROOT_LENGTH`) instead of being
   worked around with a new drive-root folder. A root that cannot fit its
   deepest descendant is rejected up front, with the arithmetic in the error.

A note on what this module deliberately does NOT do: it does not move, delete
or migrate any existing path, and it does not introduce another ``C:\bas*``
default. Legacy absolute-path contracts keep working because the declared
defaults are the directories the project already uses.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

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
    "clear_owned_subtree",
    "prepare_explicit_workspace",
    "atomic_write_json",
    "atomic_write_text",
    "free_bytes",
    "require_free_bytes",
    "resolve_layout",
    "resolve_seed",
    "seed_entry_digests",
]


# --------------------------------------------------------------- exceptions


class WorkspaceError(RuntimeError):
    """Base class. Every failure here is fail-closed and explicit."""


class PathBudgetExceeded(WorkspaceError):
    """A root cannot hold its deepest declared descendant within MAX_PATH."""


class WorkspaceBoundaryError(WorkspaceError):
    """A path escaped the root it was required to stay inside."""


class UnownedWorkspace(WorkspaceError):
    """Refused to reuse or delete a directory this run does not own."""


class SeedContractError(WorkspaceError):
    """A seed is missing, or does not satisfy its declared contract."""


# ------------------------------------------------------------ path budgeting

#: Windows MAX_PATH is 260 including the terminating NUL, so 259 usable
#: characters. Long-path support is NOT assumed: this repository runs with
#: ``LongPathsEnabled=0`` and ``git core.longpaths`` unset, and enabling
#: either is a scoped operator decision, not something a tool may assume.
PATH_BUDGET_TOTAL = 259

#: Longest path measured *below* a composed Family B qualification root
#: (``C:\bas35q``, 2026-09-21): 173 characters, from the content-addressed
#: successor lake. Raise this only with a fresh measurement, never to make a
#: failing root fit.
WORST_CASE_RELATIVE_LENGTH = 173

#: The resulting budget for the root itself. 259 - 173 = 86.
MAX_ROOT_LENGTH = PATH_BUDGET_TOTAL - WORST_CASE_RELATIVE_LENGTH


def check_path_budget(
    root: Path,
    worst_case_relative: int = WORST_CASE_RELATIVE_LENGTH,
) -> None:
    """Reject a root that cannot hold its deepest descendant.

    The arithmetic is reported so the operator can see exactly how much room
    is missing rather than guessing at a truncated-copy failure later.
    """

    text = str(root)
    allowed = PATH_BUDGET_TOTAL - worst_case_relative
    if len(text) > allowed:
        raise PathBudgetExceeded(
            f"workspace root is {len(text)} characters but at most {allowed} "
            f"fit within the {PATH_BUDGET_TOTAL}-character path budget once "
            f"the deepest declared descendant ({worst_case_relative} "
            f"characters) is appended: {text!r}. Choose a shorter root under "
            f"the declared layout; do not create a new drive-root directory "
            f"and do not assume long-path support."
        )


def assert_within(root: Path, candidate: Path) -> Path:
    """Return ``candidate`` resolved, proving it stays inside ``root``.

    ``Path.resolve()`` follows reparse points, which is the point: a junction
    planted inside a scratch root must not let a delete escape to the lake.
    """

    resolved_root = Path(root).resolve()
    resolved = Path(candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise WorkspaceBoundaryError(
            f"{resolved} is outside the permitted root {resolved_root}"
        )
    return resolved


def _is_reparse_point(path: Path) -> bool:
    try:
        stat = os.stat(path, follow_symlinks=False)
    except OSError:
        return False
    if path.is_symlink():
        return True
    return bool(getattr(stat, "st_file_attributes", 0) & 0x400)


def assert_no_reparse_ancestor(root: Path, candidate: Path) -> list[str]:
    """Prove no existing link between ``root`` and ``candidate`` redirects it.

    ``assert_within`` resolves and therefore already *detects* a junction that
    moves the destination outside the root. This walks the chain explicitly so
    the refusal can name the link, and so a reparse point that redirects
    *within* the root -- which resolution alone would accept -- is still
    reported to the caller before anything is created.
    """

    resolved_root = Path(root).resolve()
    chain: list[str] = []
    probe = Path(candidate)
    seen: list[Path] = []
    while True:
        seen.append(probe)
        if probe.parent == probe:
            break
        probe = probe.parent
    for item in reversed(seen):
        if item == resolved_root or resolved_root in item.parents:
            if item.exists() and _is_reparse_point(item):
                chain.append(str(item))
    return chain


# --------------------------------------------------------- name safety (MF37-02)

#: Characters Windows forbids in a path component. ``:`` matters most: it is
#: how a drive qualifier and an alternate data stream are both spelled.
_FORBIDDEN_NAME_CHARACTERS = set('<>:"/\\|?*') | {chr(code) for code in range(32)}

#: Reserved device names. ``CON``/``NUL``/``COM1`` resolve to devices, not to
#: directories, whatever the containing path says.
_RESERVED_DEVICE_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{n}" for n in range(1, 10)),
    *(f"LPT{n}" for n in range(1, 10)),
}


class UnsafeNameComponent(WorkspaceError):
    """A caller-supplied name is not a single, inert path component."""


def assert_safe_component(value: str, *, label: str) -> str:
    """Return ``value`` proven to be one inert path component.

    ``allocate_run_workspace`` composed ``scratch_root / tool / run_id`` from
    caller strings and only checked the *result* afterwards, so ``tool='..'``
    walked out of the declared root and an absolute ``run_id`` replaced it
    outright -- ``Path('C:/a') / 'C:/b'`` is ``C:/b``. Both created a directory
    outside the registered root before any check could object. The composition
    is only safe if each component is proven inert first, so that is checked
    here, before a path is built rather than after one exists.
    """

    if not isinstance(value, str):
        raise UnsafeNameComponent(
            f"{label} must be a string, not {type(value).__name__}"
        )
    if not value:
        raise UnsafeNameComponent(f"{label} must not be empty")
    if value in {".", ".."}:
        raise UnsafeNameComponent(
            f"{label}={value!r} is a relative traversal component, not a name"
        )
    bad = sorted(set(value) & _FORBIDDEN_NAME_CHARACTERS)
    if bad:
        raise UnsafeNameComponent(
            f"{label}={value!r} contains path or device separators "
            f"{[c if c.isprintable() else repr(c) for c in bad]}; a workspace "
            f"name must be one inert component, never a path or a drive"
        )
    if os.path.isabs(value) or os.path.splitdrive(value)[0]:
        raise UnsafeNameComponent(
            f"{label}={value!r} is absolute or drive-qualified; it would "
            f"replace the declared root instead of nesting under it"
        )
    if value != value.strip(" ."):
        raise UnsafeNameComponent(
            f"{label}={value!r} has leading or trailing spaces or dots, which "
            f"Windows silently strips, so the created name would differ from "
            f"the recorded one"
        )
    if value.split(".")[0].upper() in _RESERVED_DEVICE_NAMES:
        raise UnsafeNameComponent(
            f"{label}={value!r} is a reserved Windows device name"
        )
    if len(Path(value).parts) != 1:
        raise UnsafeNameComponent(
            f"{label}={value!r} is not a single path component"
        )
    return value


# ------------------------------------------------------------------ capacity


def free_bytes(path: Path) -> int:
    """Free bytes on the volume holding ``path`` (nearest existing parent)."""

    probe = Path(path)
    while not probe.exists():
        if probe.parent == probe:
            break
        probe = probe.parent
    return shutil.disk_usage(probe).free


def require_free_bytes(path: Path, needed: int, reserve: int = 2 * 1024**3) -> int:
    """Fail closed before an operation that cannot fit.

    ``reserve`` defaults to 2 GiB. The Cycle 36 incident -- a volume driven to
    roughly 14 MB free -- is why every sizeable write checks first: a
    truncating write that runs out of space destroys the file it was replacing.
    """

    available = free_bytes(path)
    if available < needed + reserve:
        raise WorkspaceError(
            f"insufficient free space at {path}: {available} bytes available, "
            f"{needed} needed plus a {reserve}-byte reserve. Refusing to start "
            f"an operation that cannot complete."
        )
    return available


# ------------------------------------------------------------- atomic writes


def atomic_write_bytes(path: Path, data: bytes, *, reserve: int = 64 * 1024**2) -> Path:
    """Write ``data`` to ``path`` atomically, or leave ``path`` untouched.

    ``Path.write_bytes`` opens with ``O_TRUNC``: the previous content is gone
    the instant the handle opens, so a failure part-way through -- ENOSPC, a
    kill, a crash -- leaves a zero-byte file and no original. That is not
    hypothetical here. A content-addressed canonical payload
    (``features/tamu_official_historical_coverage_inventory/sha256/d39d35ff.../
    inventory.json``) was truncated to zero bytes on 2026-09-22 while its
    immutable identity directory kept its original 2026-08-19 timestamp, and
    the repository's own strict validator has been unable to run against the
    real lake ever since.

    Writing to a temporary file in the same directory and then ``os.replace``
    keeps the previous bytes readable until the new bytes are durable.
    """

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    require_free_bytes(destination.parent, len(data), reserve=reserve)
    handle, temporary_name = tempfile.mkstemp(
        dir=str(destination.parent), prefix=".tmp-", suffix=destination.suffix
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        # A failed write must not leave the temporary behind and must not have
        # touched the destination at all.
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    return destination


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8", newline: str = "\n") -> Path:
    body = text.replace("\r\n", "\n").replace("\r", "\n")
    if newline != "\n":
        body = body.replace("\n", newline)
    return atomic_write_bytes(Path(path), body.encode(encoding))


def atomic_write_json(path: Path, value: Any, *, indent: int = 2, sort_keys: bool = True) -> Path:
    body = json.dumps(value, indent=indent, sort_keys=sort_keys) + "\n"
    return atomic_write_text(Path(path), body)


# -------------------------------------------------------------------- layout

#: The directory family this project already uses. These are declared
#: defaults, not new inventions: each one exists today and is named in TP37-S.
DEFAULT_ROOTS: Mapping[str, str] = {
    "canonical": r"C:\BatteredAggieSyndrome",
    "data": r"C:\BatteredAggieSyndrome.data",
    "backups": r"C:\BatteredAggieSyndrome.backups",
    "packaging": r"C:\BatteredAggieSyndrome.packaging",
    "reconciliation": r"C:\BatteredAggieSyndrome.reconciliation",
    "validation": r"C:\BatteredAggieSyndrome.validation",
    "worktrees": r"C:\BatteredAggieSyndrome.worktrees",
}

#: Environment overrides, checked before the declared defaults.
ENV_OVERRIDES: Mapping[str, str] = {
    "canonical": "BAS_CANONICAL_ROOT",
    "data": "AGGIE_ANALYTICS_DATA_ROOT",
    "backups": "BAS_BACKUPS_ROOT",
    "packaging": "BAS_PACKAGING_ROOT",
    "reconciliation": "BAS_RECONCILIATION_ROOT",
    "validation": "BAS_VALIDATION_ROOT",
    "worktrees": "BAS_WORKTREES_ROOT",
}

#: Optional on-disk registry, pointed at by ``BAS_PATH_REGISTRY``. A JSON
#: object of ``{"roots": {"validation": "...", ...}}``.
REGISTRY_ENV = "BAS_PATH_REGISTRY"


@dataclass(frozen=True)
class WorkspaceLayout:
    """Where each category of work is allowed to live, and why."""

    roots: Mapping[str, Path]
    sources: Mapping[str, str]

    def root(self, name: str) -> Path:
        try:
            return self.roots[name]
        except KeyError:
            raise WorkspaceError(
                f"unknown workspace root {name!r}; declared roots are "
                f"{sorted(self.roots)}"
            ) from None

    def source(self, name: str) -> str:
        return self.sources.get(name, "unknown")

    def describe(self) -> dict[str, Any]:
        return {
            "roots": {k: str(v) for k, v in sorted(self.roots.items())},
            "resolved_from": dict(sorted(self.sources.items())),
            "path_budget": {
                "total": PATH_BUDGET_TOTAL,
                "worst_case_relative": WORST_CASE_RELATIVE_LENGTH,
                "max_root_length": MAX_ROOT_LENGTH,
            },
        }


def resolve_layout(
    overrides: Mapping[str, Path | str] | None = None,
    env: Mapping[str, str] | None = None,
) -> WorkspaceLayout:
    """Resolve every root, recording which source supplied each one.

    Order, highest first: explicit ``overrides`` -> environment variable ->
    ``BAS_PATH_REGISTRY`` file -> declared default. Recording the source
    matters as much as the value: a receipt that cannot say where a root came
    from cannot prove what a run actually read.
    """

    environment = dict(os.environ if env is None else env)
    supplied = {k: str(v) for k, v in (overrides or {}).items()}

    registry: dict[str, str] = {}
    registry_path = environment.get(REGISTRY_ENV)
    if registry_path:
        candidate = Path(registry_path)
        if not candidate.is_file():
            raise WorkspaceError(
                f"{REGISTRY_ENV} points at {candidate}, which is not a file"
            )
        try:
            document = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise WorkspaceError(
                f"{REGISTRY_ENV} at {candidate} is unreadable: {error}"
            ) from error
        registry = {str(k): str(v) for k, v in (document.get("roots") or {}).items()}

    roots: dict[str, Path] = {}
    sources: dict[str, str] = {}
    for name, default in DEFAULT_ROOTS.items():
        if name in supplied:
            roots[name], sources[name] = Path(supplied[name]), "explicit"
        elif ENV_OVERRIDES[name] in environment:
            roots[name] = Path(environment[ENV_OVERRIDES[name]])
            sources[name] = f"env:{ENV_OVERRIDES[name]}"
        elif name in registry:
            roots[name], sources[name] = Path(registry[name]), f"registry:{registry_path}"
        else:
            roots[name], sources[name] = Path(default), "declared_default"
    return WorkspaceLayout(roots=roots, sources=sources)


# ------------------------------------------------------- run-owned workspace

OWNER_MARKER = ".bas-workspace-owner.json"
OWNER_SCHEMA = "BAS_WORKSPACE_OWNER_V1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunWorkspace:
    """A directory this run created, owns, and is allowed to remove."""

    root: Path
    tool: str
    run_id: str
    category: str
    layout: WorkspaceLayout = field(repr=False)
    released: bool = field(default=False, init=False)

    @property
    def marker_path(self) -> Path:
        return self.root / OWNER_MARKER

    def describe(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "tool": self.tool,
            "run_id": self.run_id,
            "category": self.category,
            "root_length": len(str(self.root)),
            "max_root_length": MAX_ROOT_LENGTH,
            "owner_marker": str(self.marker_path),
        }

    def read_marker(self) -> dict[str, Any]:
        try:
            return json.loads(self.marker_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise UnownedWorkspace(
                f"ownership marker at {self.marker_path} is missing or "
                f"unreadable ({error}); refusing to treat {self.root} as ours"
            ) from error

    def release(self, *, missing_ok: bool = False) -> dict[str, Any]:
        """Delete the workspace, but only after proving we may.

        Every one of these checks exists because ``rmtree(fixed_root,
        ignore_errors=True)`` had none of them. Errors are raised, never
        suppressed: a cleanup that silently failed is how a stale root became
        a hidden input in the first place.
        """

        if not self.root.exists():
            if missing_ok:
                self.released = True
                return {"state": "ALREADY_ABSENT", "root": str(self.root)}
            raise WorkspaceError(f"workspace {self.root} does not exist")

        if _is_reparse_point(self.root):
            raise WorkspaceBoundaryError(
                f"{self.root} is a reparse point; refusing to delete through it"
            )

        scratch_root = self.layout.root(self.category)
        assert_within(scratch_root, self.root)

        marker = self.read_marker()
        if marker.get("schema") != OWNER_SCHEMA:
            raise UnownedWorkspace(
                f"{self.marker_path} is not a {OWNER_SCHEMA} marker"
            )
        if marker.get("run_id") != self.run_id or marker.get("tool") != self.tool:
            raise UnownedWorkspace(
                f"{self.root} is owned by tool={marker.get('tool')!r} "
                f"run_id={marker.get('run_id')!r}, not by tool={self.tool!r} "
                f"run_id={self.run_id!r}"
            )

        failures: list[str] = []

        # ``onerror`` is deprecated from 3.12; ``onexc`` replaces it. Both are
        # collected rather than ignored -- the whole point is that a cleanup
        # failure is reported, not swallowed.
        if sys.version_info >= (3, 12):
            shutil.rmtree(
                self.root,
                onexc=lambda _f, path, exc: failures.append(f"{path}: {exc}"),
            )
        else:  # pragma: no cover - exercised on the 3.11 local interpreter
            shutil.rmtree(
                self.root,
                onerror=lambda _f, path, info: failures.append(f"{path}: {info[1]}"),
            )
        if failures:
            raise WorkspaceError(
                f"failed to remove {len(failures)} entries under {self.root}: "
                + "; ".join(failures[:10])
            )
        self.released = True
        return {"state": "REMOVED", "root": str(self.root)}


def _short_run_id(seed: str) -> str:
    import hashlib

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = hashlib.sha256(f"{seed}:{stamp}:{os.getpid()}".encode()).hexdigest()[:8]
    return f"{stamp}_{suffix}"


def allocate_run_workspace(
    tool: str,
    *,
    category: str = "validation",
    layout: WorkspaceLayout | None = None,
    run_id: str | None = None,
    worst_case_relative: int = WORST_CASE_RELATIVE_LENGTH,
) -> RunWorkspace:
    """Create a fresh, uniquely named, owned workspace under a declared root.

    The directory must not already exist. Two concurrent runs therefore cannot
    collide, and an unrelated directory that happens to share a name is never
    adopted or destroyed.

    Every check below happens *before* ``mkdir``. The previous order --
    compose, budget-check, then test ``root.exists()`` -- let ``tool='..'`` and
    an absolute ``run_id`` create a directory outside the registered root and
    stamp an ownership marker there; the later cleanup guard could then only
    refuse to delete what had already been made in the wrong place.
    """

    resolved_layout = layout or resolve_layout()
    scratch_root = resolved_layout.root(category)
    identifier = run_id or _short_run_id(tool)

    assert_safe_component(tool, label="tool")
    assert_safe_component(identifier, label="run_id")

    root = scratch_root / tool / identifier

    check_path_budget(root, worst_case_relative=worst_case_relative)

    # Proven inert components still compose with whatever the declared root
    # points at, so the composed destination is re-proved against the root and
    # the existing chain is checked for links that would redirect it.
    assert_within(scratch_root, root)
    redirects = assert_no_reparse_ancestor(scratch_root, root)
    if redirects:
        raise WorkspaceBoundaryError(
            f"refusing to allocate {root}: the path traverses reparse "
            f"point(s) {redirects}, so what is created is not decided by the "
            f"declared root"
        )

    if root.exists():
        raise UnownedWorkspace(
            f"refusing to reuse an existing workspace at {root}; run "
            f"namespaces are unique by construction, so this path belongs to "
            f"something else"
        )

    root.mkdir(parents=True, exist_ok=False)
    workspace = RunWorkspace(
        root=root,
        tool=tool,
        run_id=identifier,
        category=category,
        layout=resolved_layout,
    )
    atomic_write_json(
        workspace.marker_path,
        {
            "schema": OWNER_SCHEMA,
            "tool": tool,
            "run_id": identifier,
            "category": category,
            "root": str(root),
            "pid": os.getpid(),
            "created_at_utc": _utc_now(),
        },
    )
    return workspace


def prepare_explicit_workspace(
    path: Path | str,
    *,
    tool: str,
    run_id: str | None = None,
    category: str = "validation",
    layout: WorkspaceLayout | None = None,
    worst_case_relative: int = WORST_CASE_RELATIVE_LENGTH,
) -> RunWorkspace:
    r"""Take an operator-named workspace, but only when taking it is safe.

    ``allocate_run_workspace`` closed the *default* route. The explicit route
    stayed open: ``--workspace`` ran ``mkdir(parents=True, exist_ok=True)`` on
    whatever it was handed, and the first thing the caller then did was
    ``shutil.rmtree(workspace / "repo")``. Pointing it at a directory that
    already held someone else's ``repo`` -- which is exactly what an operator
    reusing a path does -- destroyed those bytes with no check at all. A
    manager sentinel was deleted this way while proving the point.

    So an explicit root is adopted only when it is demonstrably free to use:

    * it is not a reparse point and is not reached through one,
    * it either does not exist, is empty, or already carries *this* tool and
      run's ownership marker,
    * a marker naming a different owner, or any unmarked content, refuses.

    Nothing is created or removed until every check above has passed.
    """

    resolved_layout = layout or resolve_layout()
    identifier = run_id or _short_run_id(tool)
    assert_safe_component(tool, label="tool")
    assert_safe_component(identifier, label="run_id")

    root = Path(path)
    if not root.is_absolute():
        raise WorkspaceBoundaryError(
            f"explicit workspace {root} must be an absolute path so the "
            f"receipt records where it actually was, not where the process "
            f"happened to be standing"
        )
    check_path_budget(root, worst_case_relative=worst_case_relative)

    if root.exists() and _is_reparse_point(root):
        raise WorkspaceBoundaryError(
            f"{root} is a reparse point; refusing to build a workspace that "
            f"redirects somewhere this run never named"
        )
    redirects = assert_no_reparse_ancestor(root.anchor, root)
    if redirects:
        raise WorkspaceBoundaryError(
            f"refusing to use {root}: it is reached through reparse "
            f"point(s) {redirects}"
        )

    marker_path = root / OWNER_MARKER
    if root.exists():
        if not root.is_dir():
            raise UnownedWorkspace(f"{root} exists and is not a directory")
        entries = sorted(item.name for item in root.iterdir())
        if entries and entries != [OWNER_MARKER]:
            if not marker_path.is_file():
                raise UnownedWorkspace(
                    f"refusing to use {root}: it already holds {len(entries)} "
                    f"entr{'y' if len(entries) == 1 else 'ies'} "
                    f"({entries[:8]}) and carries no {OWNER_MARKER}. An "
                    f"explicit workspace is never emptied on the caller's "
                    f"behalf; choose a fresh path or remove it deliberately."
                )
            try:
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise UnownedWorkspace(
                    f"{marker_path} is unreadable ({error}); refusing to "
                    f"treat {root} as ours"
                ) from error
            if marker.get("schema") != OWNER_SCHEMA:
                raise UnownedWorkspace(
                    f"{marker_path} is not a {OWNER_SCHEMA} marker"
                )
            if marker.get("tool") != tool or marker.get("run_id") != identifier:
                raise UnownedWorkspace(
                    f"refusing to use {root}: it is owned by "
                    f"tool={marker.get('tool')!r} "
                    f"run_id={marker.get('run_id')!r}, not by tool={tool!r} "
                    f"run_id={identifier!r}"
                )
    else:
        root.mkdir(parents=True, exist_ok=False)

    workspace = RunWorkspace(
        root=root,
        tool=tool,
        run_id=identifier,
        category=category,
        layout=resolved_layout,
    )
    if not marker_path.is_file():
        atomic_write_json(
            marker_path,
            {
                "schema": OWNER_SCHEMA,
                "tool": tool,
                "run_id": identifier,
                "category": category,
                "root": str(root),
                "pid": os.getpid(),
                "created_at_utc": _utc_now(),
                "route": "explicit",
            },
        )
    return workspace


def clear_owned_subtree(workspace: RunWorkspace, relative: str) -> dict[str, Any]:
    """Remove ``workspace/relative`` only if this run owns the workspace.

    The qualification tools rebuild ``repo`` and ``data`` subtrees on every
    run. Doing that with a bare ``shutil.rmtree`` is safe only once the parent
    has been proved to be ours, which is what this insists on.
    """

    assert_safe_component(relative, label="relative")
    target = workspace.root / relative
    assert_within(workspace.root, workspace.root / relative)
    marker = workspace.read_marker()
    if marker.get("schema") != OWNER_SCHEMA:
        raise UnownedWorkspace(f"{workspace.marker_path} is not a {OWNER_SCHEMA} marker")
    if marker.get("tool") != workspace.tool or marker.get("run_id") != workspace.run_id:
        raise UnownedWorkspace(
            f"{workspace.root} is owned by tool={marker.get('tool')!r} "
            f"run_id={marker.get('run_id')!r}; refusing to clear {target}"
        )
    if not target.exists():
        return {"state": "ALREADY_ABSENT", "path": str(target)}
    if _is_reparse_point(target):
        raise WorkspaceBoundaryError(
            f"{target} is a reparse point; refusing to delete through it"
        )
    failures: list[str] = []
    if sys.version_info >= (3, 12):
        shutil.rmtree(target, onexc=lambda _f, p, exc: failures.append(f"{p}: {exc}"))
    else:  # pragma: no cover - exercised on the 3.11 local interpreter
        shutil.rmtree(target, onerror=lambda _f, p, info: failures.append(f"{p}: {info[1]}"))
    if failures:
        raise WorkspaceError(
            f"failed to remove {len(failures)} entries under {target}: "
            + "; ".join(failures[:10])
        )
    return {"state": "REMOVED", "path": str(target)}


# -------------------------------------------------------------- seed contract

SEED_CONTRACT_FILE = "SEED_CONTRACT.json"
SEED_CONTRACT_SCHEMA = "BAS_SEED_CONTRACT_V1"


def seed_entry_digests(seed: Path, entries: Iterable[str]) -> dict[str, str]:
    """Digest each declared top-level entry of a seed, files and trees alike.

    A tree digest covers every relative path and its bytes, so a file added,
    removed, renamed or edited inside the seed changes the digest.
    """

    import hashlib

    digests: dict[str, str] = {}
    for name in sorted(entries):
        target = Path(seed) / name
        if not target.exists():
            continue
        if target.is_file():
            digests[name] = hashlib.sha256(target.read_bytes()).hexdigest()
            continue
        accumulator = hashlib.sha256()
        for item in sorted(target.rglob("*")):
            if not item.is_file():
                continue
            accumulator.update(item.relative_to(target).as_posix().encode("utf-8"))
            accumulator.update(b"\0")
            accumulator.update(hashlib.sha256(item.read_bytes()).digest())
        digests[name] = accumulator.hexdigest()
    return digests


def resolve_seed(
    contract_id: str,
    *,
    explicit: Path | str | None = None,
    env_var: str = "BAS_FAMILY_B_SEED",
    layout: WorkspaceLayout | None = None,
    env: Mapping[str, str] | None = None,
    required_entries: Iterable[str] = (),
    contract_path: Path | str | None = None,
    verify_digests: bool = True,
    unverified_reason: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    r"""Resolve and verify a seed directory against a versioned contract.

    There is deliberately no default location. ``SEED = Path(r"C:\bas35q")``
    was portable-looking code that only ever worked on one machine, and it
    made a scratch directory undeletable without anyone deciding that. A run
    that cannot say which seed it used, and prove the seed is the one the
    contract names, should fail rather than quietly read whatever is there.

    Returns the resolved seed root and the parsed contract.
    """

    environment = dict(os.environ if env is None else env)
    source = "explicit"
    candidate = explicit
    if candidate is None and env_var in environment:
        candidate, source = environment[env_var], f"env:{env_var}"
    if candidate is None and contract_path is not None:
        # A contract that pins digests may also declare where the seed it
        # pins currently lives. That is a declaration of an existing
        # dependency, not a built-in default: the digests still have to match.
        try:
            declared_document = json.loads(
                Path(contract_path).read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as error:
            raise SeedContractError(
                f"{contract_path} is unreadable: {error}"
            ) from error
        registered = declared_document.get("registered_location")
        if registered:
            candidate = registered
            source = f"contract:{contract_path}"
    if candidate is None:
        registry_layout = layout or resolve_layout(env=environment)
        raise SeedContractError(
            f"no seed configured for contract {contract_id!r}. Pass --seed or "
            f"set {env_var}. There is no default: the seed is a declared "
            f"input, not scratch that happens to still be on this machine. "
            f"Declared roots: {sorted(registry_layout.roots)}"
        )

    seed = Path(candidate)
    if not seed.is_dir():
        raise SeedContractError(
            f"seed for contract {contract_id!r} resolved to {seed} "
            f"(from {source}), which is not a directory"
        )

    # The contract may live inside the seed, or -- so that an already
    # preserved seed never has to be written to in order to be declared --
    # alongside it in the cycle evidence packet.
    if contract_path is not None:
        document_path = Path(contract_path)
        contract_source = "external"
    else:
        document_path = seed / SEED_CONTRACT_FILE
        contract_source = "in_seed"
    if not document_path.is_file():
        raise SeedContractError(
            f"seed {seed} has no {SEED_CONTRACT_FILE} at {document_path}, so "
            f"it cannot be proven to satisfy contract {contract_id!r}. Point "
            f"--seed-contract at the declared contract; do not read an "
            f"unlabelled directory."
        )
    try:
        contract = json.loads(document_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SeedContractError(f"{document_path} is unreadable: {error}") from error

    if contract.get("schema") != SEED_CONTRACT_SCHEMA:
        raise SeedContractError(
            f"{document_path} is not a {SEED_CONTRACT_SCHEMA} document"
        )
    declared = contract.get("contract_id")
    if declared != contract_id:
        raise SeedContractError(
            f"{document_path} declares contract {declared!r} but "
            f"{contract_id!r} was required"
        )

    missing = [name for name in required_entries if not (seed / name).exists()]
    if missing:
        raise SeedContractError(
            f"seed {seed} satisfies contract {contract_id!r} but is missing "
            f"required entries: {sorted(missing)}"
        )

    # A contract that merely names a directory proves nothing about its
    # bytes. The previous guard only compared digests when the contract
    # happened to declare some: a well-formed contract with the right ID,
    # the right schema and *no* ``entry_digests`` was accepted outright and
    # reported ``digests_verified: false`` as an informational field. The
    # supplied Cycle 35 contract does pin digests, so the real path was safe
    # while the general consumer was not. Verification is now a precondition,
    # and declining it is an explicit, recorded decision.
    expected_raw = contract.get("entry_digests")
    observed: dict[str, str] = {}
    unverified_note: str | None = None

    if not verify_digests:
        if not unverified_reason:
            raise SeedContractError(
                f"digest verification was disabled for contract "
                f"{contract_id!r} without an ``unverified_reason``. A seed "
                f"read without proving its bytes is an unidentified input; "
                f"if that is genuinely intended, say why so the receipt "
                f"records it."
            )
        unverified_note = str(unverified_reason)
    else:
        if expected_raw is None:
            raise SeedContractError(
                f"{document_path} declares contract {contract_id!r} but pins "
                f"no ``entry_digests``. Naming a directory is not identifying "
                f"it: any directory placed at {seed} would be accepted. "
                f"Declare a digest for every required entry."
            )
        if not isinstance(expected_raw, Mapping):
            raise SeedContractError(
                f"{document_path} has a malformed ``entry_digests``: expected "
                f"an object of name -> sha256, found "
                f"{type(expected_raw).__name__}"
            )
        if not expected_raw:
            raise SeedContractError(
                f"{document_path} declares an empty ``entry_digests`` for "
                f"contract {contract_id!r}; an empty pin proves nothing"
            )

        expected = {str(k): v for k, v in expected_raw.items()}

        malformed = sorted(
            name
            for name, value in expected.items()
            if not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value.lower())
        )
        if malformed:
            raise SeedContractError(
                f"{document_path} pins malformed digests for {malformed}: a "
                f"seed digest must be a 64-character hexadecimal SHA-256"
            )

        # A key that is not an inert relative name would make the contract
        # pin bytes outside the seed it claims to describe.
        escaping = []
        for name in expected:
            probe = Path(name)
            if probe.is_absolute() or os.path.splitdrive(name)[0] or ".." in probe.parts:
                escaping.append(name)
        if escaping:
            raise SeedContractError(
                f"{document_path} pins entries {sorted(escaping)} that are "
                f"absolute or traverse outside the seed; a seed contract "
                f"describes the seed, not the rest of the volume"
            )

        undeclared = sorted(set(map(str, required_entries)) - set(expected))
        if undeclared:
            raise SeedContractError(
                f"{document_path} pins digests for {sorted(expected)} but the "
                f"caller requires {undeclared}, which are unpinned. A partial "
                f"contract cannot identify the seed the caller depends on."
            )

        observed = seed_entry_digests(seed, expected)
        absent = sorted(name for name in expected if name not in observed)
        if absent:
            raise SeedContractError(
                f"seed {seed} is missing entries {absent} that contract "
                f"{contract_id!r} pins"
            )
        mismatched = sorted(
            name
            for name, value in expected.items()
            if observed.get(name) != str(value).lower()
        )
        if mismatched:
            raise SeedContractError(
                f"seed {seed} does not match contract {contract_id!r}: entries "
                f"{mismatched} differ from the declared digests. Expected "
                + ", ".join(f"{n}={str(expected[n])[:12]}" for n in mismatched)
                + "; observed "
                + ", ".join(f"{n}={observed.get(n, 'ABSENT')[:12]}" for n in mismatched)
            )

    contract = dict(contract)
    contract["resolved_seed"] = str(seed)
    contract["resolved_from"] = source
    contract["contract_document"] = str(document_path)
    contract["contract_document_source"] = contract_source
    contract["digests_verified"] = bool(verify_digests)
    if unverified_note is not None:
        contract["digests_unverified_reason"] = unverified_note
    if observed:
        contract["observed_entry_digests"] = observed
    return seed, contract
