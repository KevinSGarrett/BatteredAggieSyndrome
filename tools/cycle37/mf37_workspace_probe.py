r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Reproduce MF37-01, MF37-02 and MF37-03 against a *chosen* source tree.

The point of the ``--src`` argument is that the same probe runs unchanged
against the retained predecessor and against the repaired head, so the
before/after difference is a property of the source under test rather than of
the probe. Nothing outside ``--scratch`` is created, read for mutation or
removed, and the predecessor tree is only ever imported.

Every probe records what the *real* helper did. A probe that raises is not a
probe failure: for a negative control, refusal is the expected outcome and is
recorded as such, so the receipt distinguishes "the gate held" from "the gate
was never reached".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself
    @staticmethod
    def _module():
        import sys as _bas_sys

        if "aggie_analytics" not in _bas_sys.modules:
            return None  # never bind the package from another tree before the tool does
        try:
            from aggie_analytics import atomic_io
        except ImportError:
            return None
        return atomic_io

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        module = cls._module()
        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)


sys.dont_write_bytecode = True


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, help="source tree whose src/ is imported")
    parser.add_argument("--scratch", required=True, help="owned scratch root for this probe")
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    src = Path(args.src).resolve()
    import_root = src / "src"
    if not (import_root / "aggie_analytics").is_dir():
        raise SystemExit(f"{import_root} does not contain an aggie_analytics package")
    # The venv carries an editable .pth for a *different* worktree. Taking the
    # front of sys.path is what makes this a comparison of the requested tree
    # rather than of whatever happens to be installed; the assertion below is
    # what makes that a proof instead of an assumption.
    sys.path.insert(0, str(import_root))
    for name in [m for m in sys.modules if m.startswith("aggie_analytics")]:
        del sys.modules[name]
    import aggie_analytics.workspace.paths as P  # noqa: E402

    origin = Path(P.__file__).resolve()
    if src not in origin.parents:
        raise SystemExit(
            f"import binding failed: aggie_analytics.workspace.paths resolved to "
            f"{origin}, which is not under the requested source tree {src}"
        )

    scratch = Path(args.scratch).resolve()
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    declared_root = scratch / "root"
    declared_root.mkdir()
    layout = P.WorkspaceLayout(
        roots={"validation": declared_root, "data": scratch / "data"},
        sources={"validation": "explicit", "data": "explicit"},
    )

    result: dict[str, Any] = {
        "label": args.label,
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "source_tree": str(src),
        "module_origin": str(origin),
        "module_sha256": _digest(origin),
        "python": sys.version.split()[0],
        "declared_validation_root": str(declared_root),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "probes": {},
    }

    def probe(name: str, fn: Callable[[], Any]) -> None:
        try:
            result["probes"][name] = {"outcome": "ALLOWED", "detail": fn()}
        except BaseException as error:  # noqa: BLE001 - the outcome IS the datum
            result["probes"][name] = {
                "outcome": "REFUSED",
                "error_type": type(error).__name__,
                "error": str(error)[:500],
            }

    def describe(workspace: Any) -> dict[str, Any]:
        root = Path(workspace.root)
        resolved = root.resolve()
        inside = str(resolved).startswith(str(declared_root.resolve()) + os.sep)
        return {
            "root": str(root),
            "resolved": str(resolved),
            "inside_declared_root": inside,
            "created_on_disk": root.exists(),
        }

    # ------------------------------------------------ MF37-02: escape inputs
    probe(
        "positive_allocation",
        lambda: describe(
            P.allocate_run_workspace("tool", category="validation", layout=layout, run_id="normal")
        ),
    )
    probe(
        "mf37_02_parent_traversal_tool",
        lambda: describe(
            P.allocate_run_workspace("..", category="validation", layout=layout, run_id="escaped")
        ),
    )
    probe(
        "mf37_02_absolute_run_id",
        lambda: describe(
            P.allocate_run_workspace(
                "tool", category="validation", layout=layout, run_id=str(scratch / "absolute_escape")
            )
        ),
    )
    probe(
        "mf37_02_unc_run_id",
        lambda: describe(
            P.allocate_run_workspace(
                "tool", category="validation", layout=layout, run_id=r"\\\\server\\share\\escaped"
            )
        ),
    )
    probe(
        "mf37_02_drive_qualified_tool",
        lambda: describe(
            P.allocate_run_workspace("C:", category="validation", layout=layout, run_id="drive")
        ),
    )
    probe(
        "mf37_02_separator_in_run_id",
        lambda: describe(
            P.allocate_run_workspace(
                "tool", category="validation", layout=layout, run_id="nested/child"
            )
        ),
    )

    # -------------------------------------------- MF37-03: seed digest gate
    seed = scratch / "seed"
    (seed / "repo").mkdir(parents=True)
    _bas_atomic.write_text(seed / "repo" / "a.json", '{"k": 1}\n', encoding="utf-8")
    (seed / "data").mkdir()
    _bas_atomic.write_text(seed / "data" / "b.json", '{"k": 2}\n', encoding="utf-8")
    # A top-level entry the contract does not pin, exactly like the real seed's
    # leftover tamper fixtures: pinning must not require pinning everything.
    (seed / "t_leftover").mkdir()
    _bas_atomic.write_text(seed / "t_leftover" / "c.json", '{"k": 3}\n', encoding="utf-8")
    good = P.seed_entry_digests(seed, ["repo", "data"])

    seed_before = {
        name: P.seed_entry_digests(seed, [name]).get(name)
        for name in ("repo", "data", "t_leftover")
    }

    def contract_file(name: str, body: dict[str, Any]) -> Path:
        path = scratch / name
        _bas_atomic.write_text(path, json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    base = {"schema": "BAS_SEED_CONTRACT_V1", "contract_id": "PROBE-V1"}
    cases = {
        "mf37_03_no_entry_digests": contract_file("c_none.json", dict(base)),
        "mf37_03_empty_entry_digests": contract_file("c_empty.json", dict(base, entry_digests={})),
        "mf37_03_partial_entry_digests": contract_file(
            "c_partial.json", dict(base, entry_digests={"repo": good["repo"]})
        ),
        "mf37_03_malformed_entry_digests": contract_file(
            "c_malformed.json",
            dict(base, entry_digests={"repo": "not-a-digest", "data": good["data"]}),
        ),
        "mf37_03_escaping_entry_path": contract_file(
            "c_escape.json",
            dict(
                base,
                entry_digests={"../outside": "0" * 64, "repo": good["repo"], "data": good["data"]},
            ),
        ),
        "mf37_03_changed_entry_digests": contract_file(
            "c_changed.json", dict(base, entry_digests={"repo": "f" * 64, "data": good["data"]})
        ),
        "mf37_03_absent_pinned_entry": contract_file(
            "c_absent.json",
            dict(base, entry_digests=dict(good, gone="e" * 64)),
        ),
        "mf37_03_valid_entry_digests": contract_file("c_valid.json", dict(base, entry_digests=good)),
    }

    def seed_probe(path: Path, **kwargs: Any) -> Callable[[], Any]:
        def run() -> dict[str, Any]:
            _, contract = P.resolve_seed(
                "PROBE-V1",
                explicit=seed,
                env={},
                required_entries=("repo", "data"),
                contract_path=path,
                **kwargs,
            )
            return {
                "digests_verified": contract.get("digests_verified"),
                "unverified_reason": contract.get("digests_unverified_reason"),
            }

        return run

    for name, path in cases.items():
        probe(name, seed_probe(path))
    probe(
        "mf37_03_verify_disabled_without_reason",
        seed_probe(cases["mf37_03_valid_entry_digests"], verify_digests=False),
    )

    result["mf37_03_seed_unchanged"] = {
        "before": seed_before,
        "after": {
            name: P.seed_entry_digests(seed, [name]).get(name)
            for name in ("repo", "data", "t_leftover")
        },
    }
    result["mf37_03_seed_unchanged"]["preserved"] = (
        result["mf37_03_seed_unchanged"]["before"] == result["mf37_03_seed_unchanged"]["after"]
    )

    # ------------------------- MF37-01: explicit workspace over foreign bytes
    occupied = scratch / "occupied"
    (occupied / "repo").mkdir(parents=True)
    sentinel = occupied / "repo" / "SENTINEL.txt"
    _bas_atomic.write_text(sentinel, "manager sentinel bytes\n", encoding="utf-8")
    sentinel_before = _digest(sentinel)

    def explicit_route() -> dict[str, Any]:
        if hasattr(P, "prepare_explicit_workspace"):
            workspace = P.prepare_explicit_workspace(
                occupied, tool="probe", run_id="r1", layout=layout
            )
            root, route = Path(workspace.root), "prepare_explicit_workspace"
        else:
            P.check_path_budget(occupied)
            occupied.mkdir(parents=True, exist_ok=True)
            root, route = occupied, "check_path_budget + mkdir(exist_ok=True)"
        # Verbatim the next statement in r35_31.build_isolated_repo.
        target = root / "repo"
        if target.exists():
            shutil.rmtree(target)
        return {"route": route, "repo_subtree_removed": not target.exists()}

    probe("mf37_01_explicit_workspace_over_existing", explicit_route)
    result["mf37_01_sentinel"] = {
        "path": str(sentinel),
        "digest_before": sentinel_before,
        "exists_after": sentinel.exists(),
        "digest_after": _digest(sentinel) if sentinel.exists() else None,
        "preserved": sentinel.exists() and _digest(sentinel) == sentinel_before,
    }

    # A fresh leased explicit workspace must still work.
    def explicit_fresh() -> dict[str, Any]:
        fresh = scratch / "fresh_explicit"
        if hasattr(P, "prepare_explicit_workspace"):
            workspace = P.prepare_explicit_workspace(
                fresh, tool="probe", run_id="r2", layout=layout
            )
            return {"root": str(workspace.root), "created": Path(workspace.root).is_dir()}
        P.check_path_budget(fresh)
        fresh.mkdir(parents=True, exist_ok=True)
        return {"root": str(fresh), "created": fresh.is_dir()}

    probe("mf37_01_fresh_explicit_workspace", explicit_fresh)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out, json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, record in result["probes"].items():
        print(f"{record['outcome']:<8} {name}")
    print("mf37_01_sentinel_preserved =", result["mf37_01_sentinel"]["preserved"])
    print("mf37_03_seed_preserved     =", result["mf37_03_seed_unchanged"]["preserved"])
    print("receipt:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
