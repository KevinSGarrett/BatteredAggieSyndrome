r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

U37-11: sweep the existing plain writers onto atomic writes.

Every ``R.write_text(...)``, ``R.write_bytes(...)`` and ``with R.open("w" | "wb"
| "wt", ...)`` in a swept file becomes ``_bas_atomic.write_text(R, ...)``,
``_bas_atomic.write_bytes(R, ...)`` or ``_bas_atomic.open_write(R, ...)``
(:mod:`aggie_analytics.atomic_io`), with the arguments passed through
unchanged. The rewrite works on the exact source spans the parser reports, so
everything outside those calls keeps its bytes.

A file is not swept, and is listed with the reason, when:

* its current SHA-256 is bound by a committed JSON artifact or config (a
  committed gate reconstructs from those bytes, so changing them re-binds the
  gate, which is an owner decision);
* it computes a code identity, or appears as a literal in a module that
  does: gates hash bundles of module bytes (``compute_code_identity``), so a
  file can be bound without its own digest appearing anywhere;
* a release builder packages it in a closed file set (a module-level
  ``FILES`` list) that does not include the helper: the packaged copy would
  import a module the release does not carry;
* the strict validator or the full suites showed that changing it breaks a
  committed binding (``BOUND_BY_VALIDATION``).

A file that a committed JSON record merely names (a Jira record, a producer
field, a test fixture) is swept, and marked JSON-named in the report so the
validators that ran after the sweep are its proof of being unbound.
* it is a test, or one of the atomic helpers themselves;
* the parser rejects it.

A tool that changes ``sys.path`` inside a function gets a lazy shim instead:
importing the package at module level there could bind it from another tree
before the tool points at its own (the installed-package contamination R37-02
names), so the helper is used only once the tool has imported
``aggie_analytics`` itself, and every earlier or package-free write stays the
plain call.

A tool without a top-level ``aggie_analytics`` import gets a guarded shim after
its imports and top-level ``sys.path`` setup: the helper when the package is
importable, and otherwise the plain calls it had, so a standalone run behaves
exactly as before.

A call is left as it is when it sits inside a function whose name says it is
already an atomic writer, when the file mode is appending or exclusive, or when
it would overlap another rewritten call.

``--check`` reports without writing; the default writes the files and a report.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKTREE = Path(__file__).resolve().parents[2]
IMPORT = "from aggie_analytics import atomic_io as _bas_atomic"
SHIM = (
    "try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise\n"
    "    from aggie_analytics import atomic_io as _bas_atomic\n"
    "except ImportError:  # a standalone run without the package keeps its plain writes\n"
    "    import types as _bas_types\n"
    "\n"
    "    _bas_atomic = _bas_types.SimpleNamespace(\n"
    "        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),\n"
    "        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),\n"
    "        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),\n"
    "    )\n"
)
#: Tools whose value is independence from producer code (three-pass pass-2 verifiers, independent references,
#: and tools whose evidence states that they import nothing from aggie_analytics) get a self-contained
#: atomic writer instead of an import of the package (W37R-69).
INDEPENDENT = frozenset({
    'tools/cycle35/r35_09_independent_kernel_reference.py',
    'tools/cycle36/c36_03_independent_season_review.py',
    'tools/cycle37/delivered_db_review.py',
    'tools/cycle37/r37_02_cause_comparison.py',
    'tools/cycle37/r37_03_historical_sample.py',
    'tools/cycle37/r37_03_labelled_sample.py',
    'tools/cycle37/r37_03_season_support_check.py',
    'tools/cycle37/r37_04_official_membership.py',
    'tools/cycle37/r37_04_population_audit.py',
    'tools/cycle37/r37_05_national_staff_counts.py',
    'tools/cycle37/r37_05_primary_tranche.py',
    'tools/cycle37/r37_07_cycle34_transcription_reconciliation.py',
    'tools/cycle37/r37_09_independent_check.py',
    'tools/cycle37/r37_10_finals_reconstruction.py',
})
INDEPENDENT_SHIM = 'class _bas_atomic:  # U37-11: atomic writes, self-contained -- this tool stays independent of aggie_analytics\n    @staticmethod\n    def _begin(path):\n        import os as _bas_os\n        import pathlib as _bas_pathlib\n        import tempfile as _bas_tempfile\n\n        target = path.resolve() if path.is_symlink() else path\n        handle, name = _bas_tempfile.mkstemp(dir=str(target.parent), prefix="~", suffix="")\n        _bas_os.close(handle)\n        return target, _bas_pathlib.Path(name)\n\n    @staticmethod\n    def _finish(temporary, target):\n        import os as _bas_os\n        import stat as _bas_stat\n        import time as _bas_time\n\n        with open(temporary, "rb+") as stream:\n            _bas_os.fsync(stream.fileno())\n        try:\n            mode = _bas_stat.S_IMODE(_bas_os.stat(target).st_mode)\n        except FileNotFoundError:\n            umask = _bas_os.umask(0)\n            _bas_os.umask(umask)\n            mode = 0o666 & ~umask\n        _bas_os.chmod(temporary, mode)\n        for attempt in range(6):\n            try:\n                _bas_os.replace(temporary, target)\n                return\n            except PermissionError:\n                if attempt == 5:\n                    raise\n                _bas_time.sleep(0.05 * (attempt + 1))\n\n    @classmethod\n    def _call(cls, method, path, *args, **kwargs):\n        import pathlib as _bas_pathlib\n\n        if not isinstance(path, _bas_pathlib.Path):\n            return getattr(path, method)(*args, **kwargs)\n        target, temporary = cls._begin(path)\n        try:\n            written = getattr(temporary, method)(*args, **kwargs)\n            cls._finish(temporary, target)\n        except BaseException:\n            temporary.unlink(missing_ok=True)\n            raise\n        return written\n\n    @classmethod\n    def write_text(cls, path, *args, **kwargs):\n        return cls._call("write_text", path, *args, **kwargs)\n\n    @classmethod\n    def write_bytes(cls, path, *args, **kwargs):\n        return cls._call("write_bytes", path, *args, **kwargs)\n\n    @classmethod\n    def open_write(cls, path, *args, **kwargs):\n        import contextlib as _bas_contextlib\n        import pathlib as _bas_pathlib\n\n        @_bas_contextlib.contextmanager\n        def _stream():\n            if not isinstance(path, _bas_pathlib.Path):\n                with path.open(*args, **kwargs) as stream:\n                    yield stream\n                return\n            target, temporary = cls._begin(path)\n            try:\n                with temporary.open(*args, **kwargs) as stream:\n                    yield stream\n                cls._finish(temporary, target)\n            except BaseException:\n                temporary.unlink(missing_ok=True)\n                raise\n\n        return _stream()\n'
LAZY_SHIM = (
    "class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself\n"
    "    @staticmethod\n"
    "    def _module():\n"
    "        import sys as _bas_sys\n"
    "\n"
    "        if \"aggie_analytics\" not in _bas_sys.modules:\n"
    "            return None  # never bind the package from another tree before the tool does\n"
    "        try:\n"
    "            from aggie_analytics import atomic_io\n"
    "        except ImportError:\n"
    "            return None\n"
    "        return atomic_io\n"
    "\n"
    "    @classmethod\n"
    "    def write_text(cls, path, *args, **kwargs):\n"
    "        module = cls._module()\n"
    "        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)\n"
    "\n"
    "    @classmethod\n"
    "    def write_bytes(cls, path, *args, **kwargs):\n"
    "        module = cls._module()\n"
    "        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)\n"
    "\n"
    "    @classmethod\n"
    "    def open_write(cls, path, *args, **kwargs):\n"
    "        module = cls._module()\n"
    "        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)\n"
)
HELPERS = {"src/aggie_analytics/atomic_io.py", "src/aggie_analytics/workspace/paths.py",
           "tools/cycle37/r37_s_atomic_write_sweep.py"}


def tracked(*patterns: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(WORKTREE), "ls-files", *patterns], capture_output=True, text=True,
                         check=True).stdout
    return [line for line in out.splitlines() if line]


def bound_digests() -> set[str]:
    """Every 64-hex digest written in a committed JSON file outside the file manifest."""

    import re

    digests: set[str] = set()
    for rel in tracked("*.json", "*.jsonl"):
        if rel.startswith("provenance/"):
            continue
        try:
            text = (WORKTREE / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        digests.update(re.findall(r"\b[0-9a-f]{64}\b", text))
    return digests


BOUND_BY_VALIDATION: set[str] = set([])


def release_closures() -> set[str]:
    """Files a release builder packages in a closed FILES set that lacks the helper."""

    closed: set[str] = set()
    for rel in tracked("tools/*.py"):
        try:
            tree = ast.parse((WORKTREE / rel).read_bytes())
        except SyntaxError:
            continue
        for node in tree.body:
            if not (isinstance(node, (ast.Assign, ast.AnnAssign))):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(isinstance(t, ast.Name) and t.id == "FILES" for t in targets):
                continue
            value = node.value
            if isinstance(value, (ast.Tuple, ast.List)):
                members = [e.value for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                if members and "src/aggie_analytics/atomic_io.py" not in members:
                    closed.update(m for m in members if m.endswith(".py"))
    return closed


def json_named_paths() -> set[str]:
    """Repository .py paths that a committed JSON file names (recorded, not excluded)."""

    import re

    pattern = re.compile(r"(?:src|tools|tests)[/\\\\]+[A-Za-z0-9_./\\\\-]+?\.py\b")
    named: set[str] = set()
    for rel in tracked("*.json", "*.jsonl"):
        if rel.startswith("provenance/"):
            continue
        try:
            text = (WORKTREE / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        named.update(re.sub(r"[\\/]+", "/", m) for m in pattern.findall(text))
    return named


def named_paths() -> set[str]:
    """Repository .py paths that compute a code identity, or that an identity-computing module lists."""

    import re

    pattern = re.compile(r"(?:src|tools|tests)[/\\\\]+[A-Za-z0-9_./\\\\-]+?\.py\b")
    named: set[str] = set()
    for rel in tracked("src/*.py", "tools/*.py"):
        text = (WORKTREE / rel).read_text(encoding="utf-8", errors="replace")
        if "code_identity" not in text and "code_bundle" not in text.lower() and "CODE_BUNDLE" not in text:
            continue
        named.update(re.sub(r"[\\/]+", "/", m) for m in pattern.findall(text))
        named.add(rel)
    return named


def _offsets(data: bytes) -> list[int]:
    starts, position = [0], 0
    for line in data.split(b"\n")[:-1]:
        position += len(line) + 1
        starts.append(position)
    return starts


def _span(node: ast.AST, starts: list[int]) -> tuple[int, int]:
    return (starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset)


def _atomic_function(stack: list[ast.AST]) -> bool:
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and "atomic" in n.name.lower() for n in stack)


def _inside_shim(stack: list[ast.AST]) -> bool:
    """The sweep's own shim: its fallback keeps the plain calls, so they are never rewritten."""

    for node in stack:
        if isinstance(node, ast.ClassDef) and node.name == "_bas_atomic":
            return True
        if isinstance(node, ast.Try) and any(
                isinstance(item, ast.ImportFrom) and any(a.asname == "_bas_atomic" for a in item.names)
                for item in node.body):
            return True
    return False


def _write_mode(call: ast.Call) -> str | None:
    mode = None
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        mode = call.args[0].value
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            mode = keyword.value.value
    if isinstance(mode, str) and mode.replace("t", "").replace("b", "") == "w":
        return mode
    return None


def rewrites(tree: ast.Module, data: bytes) -> tuple[list[tuple[int, int, bytes]], list[dict[str, Any]]]:
    starts = _offsets(data)
    edits: list[tuple[int, int, bytes]] = []
    left: list[dict[str, Any]] = []
    with_calls: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.With, ast.AsyncWith)):
            with_calls.update(id(item.context_expr) for item in node.items)

    def visit(node: ast.AST, stack: list[ast.AST]) -> None:
        for child in ast.iter_child_nodes(node):
            visit(child, stack + [node])
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            return
        attr = node.func.attr
        if attr not in ("write_text", "write_bytes", "open"):
            return
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "_bas_atomic":
            return  # already swept: the sweep is idempotent
        if _inside_shim(stack):
            return
        if attr == "open":
            if id(node) not in with_calls:
                return
            if _write_mode(node) is None:
                return
            helper = "open_write"
        else:
            helper = attr
        if _atomic_function(stack):
            left.append({"line": node.lineno, "call": attr, "reason": "INSIDE_AN_EXISTING_ATOMIC_WRITER"})
            return
        start, end = _span(node, starts)
        receiver = data[slice(*_span(node.func.value, starts))]
        func_end = _span(node.func, starts)[1]
        inner = data[func_end:end].strip()
        if not (inner.startswith(b"(") and inner.endswith(b")")):
            left.append({"line": node.lineno, "call": attr, "reason": "UNEXPECTED_CALL_SHAPE"})
            return
        arguments = inner[1:-1]
        separator = b", " if arguments.strip() else b""
        new = b"_bas_atomic." + helper.encode() + b"(" + receiver + separator + arguments + b")"
        edits.append((start, end, new))

    visit(tree, [])
    edits.sort()
    kept: list[tuple[int, int, bytes]] = []
    for edit in edits:
        if kept and edit[0] < kept[-1][1]:
            left.append({"offset": edit[0], "reason": "OVERLAPS_ANOTHER_REWRITTEN_CALL"})
            continue
        kept.append(edit)
    return kept, left


def _sys_path_call(node: ast.AST) -> bool:
    call = node.value if isinstance(node, ast.Expr) else None
    return (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Attribute) and call.func.value.attr == "path"
            and isinstance(call.func.value.value, ast.Name) and call.func.value.value.id == "sys")


def sys_path_inside_function(tree: ast.Module) -> bool:
    top = {id(node) for node in tree.body}
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and _sys_path_call(node) and id(node) not in top:
            return True
    return False


def shim_position(tree: ast.Module, data: bytes) -> int | None:
    """After the last top-level import or sys.path statement that precedes the first definition."""

    starts = _offsets(data)
    last = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        if isinstance(node, (ast.Import, ast.ImportFrom)) or _sys_path_call(node):
            last = node
    return _span(last, starts)[1] if last is not None else None


def import_position(tree: ast.Module, data: bytes, is_tool: bool) -> int | None:
    """Byte offset after which the helper import goes."""

    starts = _offsets(data)
    body = tree.body
    if is_tool:
        for node in body:
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("aggie_analytics"):
                return _span(node, starts)[1]
            if isinstance(node, ast.Import) and any(a.name.startswith("aggie_analytics") for a in node.names):
                return _span(node, starts)[1]
        return None
    last = None
    for node in body:
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and last is None:
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last = node
            continue
        break
    if last is None:
        return None
    return _span(last, starts)[1]


def sweep(write: bool) -> dict[str, Any]:
    digests = bound_digests()
    named = named_paths()
    json_named = json_named_paths()
    closures = release_closures()
    files = [f for f in tracked("src/*.py", "tools/*.py") if f.endswith(".py")]
    report: dict[str, Any] = {"swept": [], "not_swept": [], "calls_rewritten": 0, "calls_left": []}
    for rel in files:
        path = WORKTREE / rel
        data = path.read_bytes()
        if b"write_text" not in data and b"write_bytes" not in data and b".open(" not in data:
            continue
        try:
            tree = ast.parse(data)
        except SyntaxError as error:
            report["not_swept"].append({"file": rel, "reason": f"PARSE_ERROR {error}"})
            continue
        edits, left = rewrites(tree, data)
        if not edits:
            if left:
                report["calls_left"].extend({"file": rel, **row} for row in left)
            continue
        digest = hashlib.sha256(data).hexdigest()
        reason = None
        if rel in HELPERS:
            reason = "ATOMIC_HELPER_ITSELF"
        elif digest in digests:
            reason = "BYTES_BOUND_BY_A_COMMITTED_ARTIFACT"
        elif rel in named:
            reason = "MEMBER_OF_A_CODE_IDENTITY"
        elif rel in closures:
            reason = "IN_A_RELEASE_FILE_CLOSURE_WITHOUT_THE_HELPER"
        elif rel in BOUND_BY_VALIDATION:
            reason = "BOUND_BY_VALIDATION"
        is_tool = rel.startswith("tools/")
        position = import_position(tree, data, is_tool)
        header = IMPORT
        if reason is None and position is None and is_tool:
            position = shim_position(tree, data)
            header = (INDEPENDENT_SHIM if rel in INDEPENDENT
                      else LAZY_SHIM if sys_path_inside_function(tree) else SHIM)
        if reason is None and position is None:
            reason = "NO_IMPORT_BLOCK"
        if reason:
            report["not_swept"].append({"file": rel, "reason": reason, "calls": len(edits), "sha256": digest})
            continue
        newline = b"\r\n" if b"\r\n" in data else b"\n"
        out = data
        for start, end, new in reversed(edits):
            out = out[:start] + new + out[end:]
        if IMPORT.encode() not in out and b"class _bas_atomic:" not in out:
            insert = position  # the import block precedes every rewritten call
            block = header.replace("\n", newline.decode()).encode()
            out = out[:insert] + newline + block.rstrip(newline) + out[insert:]
        compile(out, rel, "exec")
        if write:
            path.write_bytes(out)
        report["swept"].append({"file": rel, "calls": len(edits), "sha256_before": digest,
                                "json_named": rel in json_named,
                                "import": ("LAZY_SHIM" if header is LAZY_SHIM else "SHIM" if header is SHIM
                                           else "IMPORT"),
                                "sha256_after": hashlib.sha256(out).hexdigest()})
        report["calls_rewritten"] += len(edits)
        report["calls_left"].extend({"file": rel, **row} for row in left)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    parser.add_argument("--check", action="store_true", help="report without writing")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = sweep(write=not args.check)
    summary = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE", "cycle_number": 37, "attempt_number": 2,
        "requirement": "R37-S-CF-U37-11", "mode": "CHECK" if args.check else "WRITTEN",
        "files_swept": len(report["swept"]), "calls_rewritten": report["calls_rewritten"],
        "files_not_swept": len(report["not_swept"]),
        "not_swept_by_reason": {r: sum(1 for x in report["not_swept"] if x["reason"].startswith(r))
                                for r in sorted({x["reason"].split(" ")[0] for x in report["not_swept"]})},
        "calls_left_in_swept_files": len(report["calls_left"]),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **report,
    }
    if args.out:
        args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if not isinstance(v, list)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
