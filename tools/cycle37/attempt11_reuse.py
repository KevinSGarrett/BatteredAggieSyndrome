r"""Cycle #37 — Attempt #11 — a current, complete dependency check that lets a lane keep its original execution (R37A11-05-A).

    attempt11_reuse.py check  --contract C --out-root R --lane L [--lane L ...] [--write]
                              [--original-handoff-zip Z --original-handoff-manifest M] [--rehearsal-head REV]
    attempt11_reuse.py verify --contract C --out-root R --lane L [--lane L ...]

The contract lets a worker lane "execute or provide a current complete unchanged-dependency CHECK" (R37A11-05-A). The
Attempt 11 output wrapper had no adapter for it (EVIDENCE_REUSE_IMPLEMENTATION_GAP.json): its ``at_head`` accepts only a
receipt whose head is the current head, so the only way to a passing packet after any later commit was a full rerun.
This tool is the adapter, and it is deliberately narrow:

* It never relabels an old execution fresh. The original run, head, receipt, log, counts and result stay exactly as they
  were; the check is a separate, current, create-only record bound to the current head, and every report says the lane was
  retained, not executed again.
* It never trusts a stored record. ``check`` computes every check and writes the record; ``verify`` (used by the output
  tool each time it builds or checks) recomputes every check again and accepts the lane only if they still hold and the
  recorded re-executed commands still match their logs. A hand-written or stale record is not a proof.
* It refuses on any changed, missing or forged dependency, for its own cause, and a refused lane is simply not at the
  current head (it needs a fresh run): the original receipt and its log and every command log still hash to what the
  index and the sealed original submission recorded; the original head is an ancestor of the current head; every tracked
  path that differs between the two heads is one this repair declared (anything else refuses); the runner delta is proved
  bookkeeping-only by the syntax tree, not asserted; no retained command executes a changed tool (a command that does is
  either on a short allowlist of local, network-free commands that this check executes again now, or the lane is
  refused); no retained command runs tests when a test file was added; the interpreter, the runner's bound tool digests
  and every recorded (path, digest) pair of the receipt still hold; and the lane's own environment and data
  (the packaged wheel, the installed files against the current source, the delivered database and successor) still hold.

Nothing here is a scientific claim, an acceptance or new spending authority.
"""

from __future__ import annotations

import argparse
import ast
import collections
import copy
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

CYCLE_NUMBER, ATTEMPT_NUMBER = 37, 11
LABEL = "Cycle #37 — Attempt #11 —"
SCHEMA = "BAS-C37A11-LANE-REUSE-CHECK-1"
MODE = "RETAINED_ORIGINAL_EXECUTION_UNDER_A_CURRENT_COMPLETE_DEPENDENCY_CHECK"
REUSE_DIR = Path("evidence") / "reuse"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# ------------------------------------------------------------------ what this repair changed, and what may be retained

RUNNER, OUTPUT_TOOL, NEW_TOOL, NEW_TEST, PROVENANCE = "RUNNER", "OUTPUT_TOOL", "NEW_TOOL", "NEW_TEST", "PROVENANCE"

#: Every tracked path this repair changes between the original head and the current head, by class. A path outside this
#: table that differs refuses reuse for every lane: an unknown change to a product, test or tool file is a changed
#: dependency, and the lane needs a fresh run.
DELTA_CLASSES: dict[str, tuple[str, str]] = {
    "tools/cycle37/attempt07_lanes.py": (RUNNER, "FINAL_PACKET's reservation-identity predicate and its one call"),
    "tools/cycle37/attempt11_lanes.py": (RUNNER, "the runner keeps its admitted reservation; explicit --continuation admission"),
    "tools/cycle37/attempt11_outputs.py": (OUTPUT_TOOL, "the accounting derives lane execution from receipts and proofs"),
    "tools/cycle37/attempt11_report.py": (OUTPUT_TOOL, "the report derives lane execution from receipts and proofs"),
    "tools/cycle37/attempt11_preflight.py": (OUTPUT_TOOL, "the tiny-fixture preflight covers the repair and the check"),
    "tools/cycle37/attempt11_reuse.py": (NEW_TOOL, "this check"),
    "tests/test_cycle37_a11_final_reservation_identity.py": (NEW_TEST, "MF37A11-01 regression tests"),
    "tests/test_cycle37_a11_lane_reuse.py": (NEW_TEST, "regression tests of this check"),
    "provenance/CURRENT_TREE.txt": (PROVENANCE, "regenerated from the tree by the canonical generator"),
    "provenance/PROJECT_FILE_MANIFEST.csv": (PROVENANCE, "regenerated from the tree by the canonical generator"),
    "provenance/PROJECT_FILE_HASHES.sha256": (PROVENANCE, "regenerated from the tree by the canonical generator"),
}

#: Commands a retained lane may execute again inside the check, because they read a changed output tool: local,
#: network-free and cheap. Anything else that reads a changed tool refuses the lane.
REEXECUTABLE: dict[str, tuple[str, ...]] = {"PLATFORM_CARRY": ("carryforward_accounting",)}

#: Source-binding keys that legitimately differ between two heads. The two runner digests differ by the proved runner
#: delta; the rest name the heads themselves.
BINDING_MAY_DIFFER = frozenset({"head", "tree", "source_digest", "commits_after_base", "runner_sha256",
                                "rebound_attempt7_runner_sha256", "clean", "dirty_entries"})
RUNNER_DIGEST_FILES = {"runner_sha256": "tools/cycle37/attempt11_lanes.py",
                       "rebound_attempt7_runner_sha256": "tools/cycle37/attempt07_lanes.py"}

#: The syntax-tree specification of the runner delta: every top-level definition of the two changed runner modules is
#: identical except these, and inside the two changed functions only these statements and expressions differ.
#: ``stmt_added`` is a statement present only at the current head; ``stmt_replaced`` and ``expr_replaced`` pair a
#: statement (or expression) as it was with what replaces it.
RUNNER_DELTA_SPEC: dict[str, dict[str, Any]] = {
    "tools/cycle37/attempt07_lanes.py": {
        "added": ("_owned_final_reservation",),
        "modified": {
            "lane_final_packet": [
                ("expr_replaced",
                 '[v.get("operation") for v in open_now.values()] == [f"LANE FINAL_PACKET {run.stamp}" + '
                 '(" (rehearsal)" if run.rehearsal else "")]',
                 "_owned_final_reservation(run, open_now)"),
            ]}},
    "tools/cycle37/attempt11_lanes.py": {
        "added": ("_reservation_for_check",),
        "modified": {
            "main": [
                ("stmt_added", 'parser.add_argument("--continuation", action="store_true", help="After the operational '
                               'ledger is frozen, admit this lane on the attempt\'s one claimed final-output '
                               'continuation (same budget, roots and reserve; no new segment). Without it a material '
                               'lane is refused once the ledger is frozen.")'),
                ("stmt_added", "run.storage_reservation = _reservation_for_check(args, final_lane, reservation, paths)"),
                ("expr_replaced", "FINAL_SNAPSHOT.is_file() and (not final_lane)",
                 "FINAL_SNAPSHOT.is_file() and (not final_lane) and (not args.continuation)"),
                ("stmt_replaced",
                 'blocked.append(f"the operational ledger is frozen by {FINAL_SNAPSHOT.name}; material lanes are refused")',
                 'blocked.append(f"the operational ledger is frozen by {FINAL_SNAPSHOT.name}; material lanes are refused '
                 '(--continuation admits one on the final-output continuation)")'),
                ("stmt_added", 'if args.continuation and (not FINAL_SNAPSHOT.is_file()):\n'
                               '    blocked.append("--continuation applies only after the operational ledger is frozen")'),
            ]}},
}


# ------------------------------------------------------------------ small helpers


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def norm(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def under(path: Path | str, root: Path | str) -> bool:
    child, parent = norm(path), norm(root)
    return child == parent or child.startswith(parent + os.sep)


def _check(name: str, holds: bool, detail: Any = None, **extra: Any) -> dict[str, Any]:
    return {"name": name, "holds": bool(holds), "detail": detail, **extra}


# ------------------------------------------------------------------ the environment the checks read


@dataclass
class Env:
    """Everything a check reads, injectable so the checks run on tiny synthetic repositories in the tests."""

    repo: Path
    out_root: Path
    contract_sha256: str
    head: str                                   # the current head the check binds to
    git: Callable[..., str]                     # git(*args) -> stripped stdout, raising on failure
    git_bytes: Callable[..., bytes]             # git(*args) -> raw stdout
    bind_source: Callable[[], dict[str, Any]]   # the runner's own binding at the current head
    bind_interpreter: Callable[[], dict[str, Any]]
    python: str = sys.executable
    immutable_roots: tuple[Path, ...] = ()      # roots whose recorded (path, digest) pairs are immutable evidence
    scratch_env: Callable[[], dict[str, str]] = dict
    passthrough: Callable[[], bool] = lambda: True  # the reservation helper hands a non-FINAL_PACKET lane its own
    original_submission: dict[str, Any] | None = None
    original_submission_source: str | None = None
    handoff_paths: dict[str, str] | None = None
    database: Path | None = None                # the delivered database a lane recorded (INSTALLED_CONSUMER_C01)
    lane_checks: dict[str, Callable[["Env", dict[str, Any], dict[str, Any]], list[dict[str, Any]]]] = field(default_factory=dict)

    def is_ancestor(self, older: str, newer: str) -> bool:
        try:
            self.git("merge-base", "--is-ancestor", older, newer)
        except SystemExit:
            return False
        return True

    def blob(self, rev: str, path: str) -> str | None:
        try:
            return self.git_bytes("cat-file", "blob", f"{rev}:{path}").decode("utf-8")
        except (SystemExit, subprocess.CalledProcessError, OSError):
            return None

    def blob_bytes(self, rev: str, path: str) -> bytes | None:
        try:
            return self.git_bytes("cat-file", "blob", f"{rev}:{path}")
        except (SystemExit, subprocess.CalledProcessError, OSError):
            return None

    def tracked(self, rev: str) -> set[str]:
        raw = self.git_bytes("ls-tree", "-r", "--name-only", "-z", rev)
        return {p for p in raw.decode("utf-8").split("\0") if p}


# ------------------------------------------------------------------ the runner delta, proved on the syntax tree


def _strip_docstrings(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]


def _doc_first_line(tree: ast.Module) -> str | None:
    text = ast.get_docstring(tree, clean=False)
    return text.splitlines()[0] if text else None


def _key(node: ast.stmt, index: int) -> tuple[str, str]:
    if isinstance(node, ast.FunctionDef):
        return ("def", node.name)
    if isinstance(node, ast.ClassDef):
        return ("class", node.name)
    if isinstance(node, ast.Assign):
        return ("assign", ",".join(ast.dump(t) for t in node.targets))
    if isinstance(node, ast.AnnAssign):
        return ("assign", ast.dump(node.target))
    return ("stmt", str(index))


def _parse_spec(entry: tuple[str, ...]) -> tuple[str, ast.AST, ast.AST | None]:
    kind = entry[0]
    if kind == "stmt_added":
        return kind, ast.parse(entry[1]).body[0], None
    if kind == "stmt_replaced":
        return kind, ast.parse(entry[2]).body[0], ast.parse(entry[1]).body[0]
    if kind == "expr_replaced":
        return kind, ast.parse(entry[2], mode="eval").body, ast.parse(entry[1], mode="eval").body
    raise ValueError(f"unknown delta entry {kind}")


class _Undo(ast.NodeTransformer):
    """Take the declared delta back out of the later tree: drop each declared added statement and put each replaced
    node's earlier form back. What is left must equal the earlier function."""

    def __init__(self, added: dict[str, ast.AST], replaced: dict[str, ast.AST]) -> None:
        self.added, self.replaced = added, replaced
        self.seen_added: collections.Counter[str] = collections.Counter()
        self.seen_replaced: collections.Counter[str] = collections.Counter()

    def visit(self, node: ast.AST) -> Any:
        dumped = ast.dump(node)
        if dumped in self.replaced:
            self.seen_replaced[dumped] += 1
            return copy.deepcopy(self.replaced[dumped])
        return super().visit(node)

    def generic_visit(self, node: ast.AST) -> ast.AST:
        for name, old in ast.iter_fields(node):
            if isinstance(old, list):
                kept: list[Any] = []
                for item in old:
                    if isinstance(item, ast.stmt) and ast.dump(item) in self.added:
                        self.seen_added[ast.dump(item)] += 1
                        continue
                    if isinstance(item, ast.AST):
                        item = self.visit(item)
                        if item is None:
                            continue
                    kept.append(item)
                old[:] = kept
            elif isinstance(old, ast.AST):
                new = self.visit(old)
                if new is None:
                    delattr(node, name)
                else:
                    setattr(node, name, new)
        return node


def function_delta(before: ast.FunctionDef, after: ast.FunctionDef, entries: list[tuple[str, ...]], name: str) -> list[str]:
    added: dict[str, ast.AST] = {}
    replaced: dict[str, ast.AST] = {}
    for entry in entries:
        kind, later, earlier = _parse_spec(entry)
        (added if kind == "stmt_added" else replaced)[ast.dump(later)] = later if kind == "stmt_added" else earlier
    undo = _Undo(added, replaced)
    restored = undo.visit(copy.deepcopy(after))
    problems = []
    for dumped in added:
        if undo.seen_added[dumped] != 1:
            problems.append(f"{name}: a declared added statement is present {undo.seen_added[dumped]} times, not once")
    for dumped in replaced:
        if undo.seen_replaced[dumped] != 1:
            problems.append(f"{name}: a declared replacement is present {undo.seen_replaced[dumped]} times, not once")
    if ast.dump(restored) != ast.dump(before):
        problems.append(f"{name} differs from its original beyond the declared statements")
    return problems


def module_delta(before_src: str, after_src: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Every top-level definition of the two module texts is identical except the declared additions and the two
    declared functions, and those differ only by the declared statements. Docstrings do not run; the module docstring's
    first line does (the argument parser's description) and is compared."""

    before, after = ast.parse(before_src), ast.parse(after_src)
    problems: list[str] = []
    if _doc_first_line(before) != _doc_first_line(after):
        problems.append("the module docstring's first line (the parser description) changed")
    _strip_docstrings(before)
    _strip_docstrings(after)
    added = set(spec.get("added", ()))
    modified = spec.get("modified", {})
    present = {n.name for n in after.body if isinstance(n, ast.FunctionDef)}
    for name in sorted(added):
        if name not in present:
            problems.append(f"the declared addition {name} is missing")
    before_nodes = [(_key(n, i), n) for i, n in enumerate(before.body)]
    kept_nodes = [n for n in after.body if not (isinstance(n, ast.FunctionDef) and n.name in added)]
    after_kept = [(_key(n, i), n) for i, n in enumerate(kept_nodes)]
    if [k for k, _ in before_nodes] != [k for k, _ in after_kept]:
        problems.append("the module's top-level structure differs beyond the declared additions")
        return {"holds": False, "problems": problems, "functions_compared": 0, "modified": []}
    changed: list[str] = []
    for (key, old), (_, new) in zip(before_nodes, after_kept):
        if ast.dump(old) == ast.dump(new):
            continue
        if key[0] != "def" or key[1] not in modified:
            problems.append(f"{key[0]} {key[1]} changed and is not declared")
            continue
        changed.append(key[1])
        problems += function_delta(old, new, modified[key[1]], key[1])
    for name in modified:
        if name not in changed:
            problems.append(f"the declared modified function {name} is unchanged")
    return {"holds": not problems, "problems": problems, "functions_compared": len(before_nodes),
            "modified": sorted(changed), "added": sorted(added)}


def _references(tree: ast.AST, module: str) -> list[dict[str, Any]]:
    """Every name, attribute and string constant of interest in one module, with its enclosing function and context."""

    interest = {"lane_final_packet", "_owned_final_reservation", "_reservation_for_check", "storage_reservation"}
    rows: list[dict[str, Any]] = []

    def visit(node: ast.AST, functions: tuple[str, ...], parent: ast.AST | None) -> None:
        if isinstance(node, ast.FunctionDef):
            if node.name in interest:
                rows.append({"module": module, "ident": node.name, "kind": "def", "in": functions})
            functions = functions + (node.name,)
        ident = kind = None
        if isinstance(node, ast.Name) and node.id in interest:
            ident, kind = node.id, "name"
        elif isinstance(node, ast.Attribute) and node.attr in interest:
            ident, kind = node.attr, "attr"
        elif isinstance(node, ast.Constant) and node.value in interest and isinstance(node.value, str):
            ident, kind = node.value, "string"
        if ident is not None:
            dict_key = None
            if isinstance(parent, ast.Dict) and node in parent.values:
                key = parent.keys[parent.values.index(node)]
                dict_key = key.value if isinstance(key, ast.Constant) else None
            rows.append({"module": module, "ident": ident, "kind": kind, "in": functions, "dict_key": dict_key,
                         "store": isinstance(getattr(node, "ctx", None), ast.Store)})
        for child in ast.iter_child_nodes(node):
            visit(child, functions, node)

    visit(tree, (), None)
    return rows


def reference_problems(sources: dict[str, str]) -> list[str]:
    """The changed runner definitions are reachable only where the delta says: ``lane_final_packet`` only as
    FINAL_PACKET's entry in a lane table; ``_owned_final_reservation`` only from ``lane_final_packet``;
    ``_reservation_for_check`` only from ``main``; and the ``storage_reservation`` attribute is stored once, in ``main``,
    and read only by ``_owned_final_reservation``. Nothing else can reach the changed code, so a lane other than
    FINAL_PACKET cannot execute it."""

    rows: list[dict[str, Any]] = []
    for module, text in sources.items():
        rows += _references(ast.parse(text), module)
    problems = []
    for row in rows:
        ident, kind, where = row["ident"], row["kind"], row["in"]
        if ident == "lane_final_packet":
            # A definition; FINAL_PACKET's entry in a lane table; or a call inside another function of that same name (the
            # earlier attempts' own wrappers), which is itself reachable only through one of those two.
            if kind == "def":
                continue
            if row.get("dict_key") == "FINAL_PACKET" and where == ():
                continue
            if where and where[-1] == "lane_final_packet":
                continue
        elif ident == "_owned_final_reservation":
            if kind == "def" or (kind == "name" and where == ("lane_final_packet",)):
                continue
        elif ident == "_reservation_for_check":
            if kind == "def" or (kind == "name" and where == ("main",)):
                continue
        elif ident == "storage_reservation":
            if kind == "attr" and row.get("store") and where == ("main",):
                continue
            if where == ("_owned_final_reservation",):
                continue
        problems.append(f"{ident} is reachable from {row['module']}:{'.'.join(where) or '<module>'} ({kind})")
    counts = collections.Counter((r["ident"], r["kind"]) for r in rows)
    if counts[("_reservation_for_check", "name")] != 1:
        problems.append("_reservation_for_check is not called exactly once")
    if counts[("_owned_final_reservation", "name")] != 1:
        problems.append("_owned_final_reservation is not called exactly once")
    if sum(1 for r in rows if r["ident"] == "storage_reservation" and r["kind"] == "attr" and r.get("store")) != 1:
        problems.append("run.storage_reservation is not stored exactly once")
    return problems


def runner_delta(env: Env, before: str, after: str) -> dict[str, Any]:
    """The whole runner delta between two heads, proved."""

    documents: dict[str, Any] = {}
    problems: list[str] = []
    after_sources: dict[str, str] = {}
    for path in sorted(env.tracked(after)):
        if path.startswith("tools/cycle37/attempt") and path.endswith("_lanes.py"):
            text = env.blob(after, path)
            if text is not None:
                after_sources[path] = text
    for path, spec in RUNNER_DELTA_SPEC.items():
        old, new = env.blob(before, path), env.blob(after, path)
        if old is None or new is None:
            problems.append(f"{path} is missing at one of the two heads")
            continue
        documents[path] = module_delta(old, new, spec)
        problems += [f"{path}: {p}" for p in documents[path]["problems"]]
    problems += reference_problems(after_sources) if after_sources else ["no runner module found at the current head"]
    behaviour = bool(env.passthrough())
    if not behaviour:
        problems.append("the reservation helper does not hand a non-FINAL_PACKET lane its own reservation")
    return {"holds": not problems, "problems": problems, "modules": documents,
            "runner_modules_read": sorted(after_sources), "reservation_helper_is_a_passthrough": behaviour,
            "meaning": ("the only runner statements that differ execute in FINAL_PACKET's own function, on a refusal path "
                        "no unfrozen run reaches, or set an attribute nothing but FINAL_PACKET reads")}


# ------------------------------------------------------------------ dependency checks


def changed_paths(env: Env, before: str, after: str) -> list[tuple[str, str]]:
    raw = env.git_bytes("diff", "--name-status", "--no-renames", "-z", before, after).decode("utf-8")
    fields = [f for f in raw.split("\0") if f]
    return [(fields[i], fields[i + 1]) for i in range(0, len(fields) - 1, 2)]


def local_closure(env: Env, rev: str, entries: list[str], tracked: set[str]) -> set[str]:
    """The tracked files a script can import from its own folder or ``tools/``, read from the committed text."""

    seen: set[str] = set()
    stack = list(entries)
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        text = env.blob(rev, path)
        if text is None:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                for candidate in (f"{os.path.dirname(path)}/{top}.py", f"tools/{top}.py"):
                    if candidate in tracked:
                        stack.append(candidate)
    return seen


def command_entries(env: Env, command: list[str], cwd: str) -> tuple[list[str], bool]:
    """(the repository files a command names as scripts, whether it runs a test runner)."""

    scripts: list[str] = []
    tests = False
    tokens = [str(t) for t in command]
    if tokens and os.path.basename(tokens[0]).lower() in ("pytest", "pytest.exe", "py.test", "py.test.exe"):
        tests = True
    for index, text in enumerate(tokens):
        # A command runs tests when it invokes a runner module (-m unittest, pytest or the project's census runner); a
        # module NAME handed to some other program (an import probe printing where modules load from) is not a run.
        if text == "-m" and index + 1 < len(tokens) and (tokens[index + 1] in ("unittest", "pytest")
                                                          or tokens[index + 1].endswith(".unittest_census")
                                                          or tokens[index + 1] == "unittest_census"):
            tests = True
        if text.lower().endswith(".py"):
            path = Path(text) if Path(text).is_absolute() else Path(cwd) / text
            if under(path, env.repo):
                scripts.append(Path(os.path.relpath(path, env.repo)).as_posix())
    return scripts, tests


def recorded_pairs(node: Any, pointer: str = "") -> list[dict[str, str]]:
    """The receipt's unambiguous (path, SHA-256) pairs: ``sha256`` with ``path``/``file``, ``log_sha256`` with
    ``log_path``, and ``<x>_sha256`` with ``<x>``, ``<x>_path`` or ``<x>_file``. A digest of something other than the
    named file (a stream, a guard) is never paired by guesswork."""

    rows: list[dict[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and HEX64.match(value) and (key == "sha256" or key.endswith("_sha256")):
                if key == "sha256":
                    names = ("path", "file")
                elif key == "log_sha256":
                    names = ("log_path",)
                else:
                    base = key[:-len("_sha256")]
                    names = (base, base + "_path", base + "_file")
                for name in names:
                    target = node.get(name)
                    if isinstance(target, str) and re.match(r"^[A-Za-z]:[\\/]", target):
                        rows.append({"pointer": f"{pointer}/{key}", "path": target, "sha256": value})
                        break
        for key, value in node.items():
            rows += recorded_pairs(value, f"{pointer}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            rows += recorded_pairs(value, f"{pointer}[{index}]")
    return rows


def normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def interpreter_identity(python: Path) -> dict[str, Any]:
    """The interpreter's identity computed in this process, with no subprocess: its executable and digest, version,
    implementation, base prefix and the installed distributions read from package metadata over ``sys.path`` minus every
    entry ``PYTHONPATH`` named. ``pip freeze`` was the recorded form, but run inside a guarded child it is not reproducible:
    a ``PYTHONPATH`` naming the worktree makes pip list the source tree's own distribution, and pip's VCS probing (``hg``) is
    blocked by the write guard, changing its editable-install line (both found by running this check inside the
    FINAL_PACKET lane's guard environment)."""

    import importlib.metadata as metadata  # noqa: PLC0415

    explicit = {norm(part) for part in os.environ.get("PYTHONPATH", "").split(os.pathsep) if part}
    paths = [entry for entry in sys.path if entry and os.path.isdir(entry) and norm(entry) not in explicit]
    seen: dict[str, str] = {}
    for distribution in metadata.distributions(path=paths):
        name = distribution.metadata["Name"]
        if name and normalized_name(name) not in seen:
            seen[normalized_name(name)] = distribution.version
    return {"executable": str(python), "sha256": sha256_file(python), "version": sys.version,
            "implementation": platform.python_implementation(), "base_prefix": sys.base_prefix,
            "distributions": sorted(f"{name}=={version}" for name, version in seen.items())}


def _distribution_sets(document: dict[str, Any]) -> tuple[set[str], set[str]]:
    """(``name==version`` pairs, names of editable installs) from either form: ``pip freeze`` lines or metadata pairs."""

    pairs: set[str] = set()
    editable: set[str] = set()
    for line in document.get("distributions") or []:
        line = str(line)
        if line.startswith("-e "):
            found = re.search(r"#egg=([A-Za-z0-9_.\-]+)", line)
            if found:
                editable.add(normalized_name(found.group(1)))
            continue
        found = re.match(r"^([A-Za-z0-9_.\-]+)==(.+)$", line)
        if found:
            pairs.add(f"{normalized_name(found.group(1))}=={found.group(2)}")
        else:
            pairs.add(line)
    return pairs, editable


def interpreters_match(recorded: dict[str, Any] | None, current: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """The same interpreter: the same executable, digest, version, implementation and base prefix, and the same installed
    distributions (name and version). The recorded editable install is matched by its name, so the project's own
    editable entry (whose version pip prints as a VCS URL) does not decide the identity."""

    recorded = recorded or {}
    differing = [key for key in ("executable", "sha256", "version", "implementation", "base_prefix")
                 if recorded.get(key) != current.get(key)]
    wanted, editable = _distribution_sets(recorded)
    have, _ = _distribution_sets(current)
    have = {pair for pair in have if pair.split("==")[0] not in editable}
    detail = {"differing_facts": differing, "recorded_only": sorted(wanted - have)[:8], "current_only": sorted(have - wanted)[:8],
              "recorded_editable_names": sorted(editable), "distributions": len(wanted)}
    return not differing and wanted == have, detail


def latest_execution(env: Env, lane: str) -> dict[str, Any] | None:
    index = env.out_root / "lanes" / "RUNS.jsonl"
    if not index.is_file():
        return None
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row.get("lane") == lane]
    return rows[-1] if rows else None


def check_lane(env: Env, lane: str, *, reexecute: bool, recorded: dict[str, Any] | None = None,
               log_dir: Path | None = None, stamp: str | None = None) -> dict[str, Any]:
    """Every dependency of one lane's original execution, checked now. ``reexecute`` runs the allowlisted commands
    again and logs them; otherwise the recorded runs of a previous check are verified against their logs."""

    checks: list[dict[str, Any]] = []
    row = latest_execution(env, lane)
    result: dict[str, Any] = {"lane": lane, "checks": checks, "reexecuted": [], "original": None,
                              "current": {"head": env.head}}
    if row is None:
        checks.append(_check("original_execution_exists", False, "no run of this lane is recorded"))
        return _finish(result)
    if row.get("head") == env.head:
        checks.append(_check("original_execution_is_not_already_current", False,
                             "the latest run is at the current head; it is a fresh execution, not a retained one"))
        return _finish(result)
    receipt_path = Path(row["receipt"])
    receipt = read_json(receipt_path) if receipt_path.is_file() else None
    result["original"] = {"run": row.get("run"), "head": row.get("head"), "source_digest": row.get("source_digest"),
                          "result": row.get("result"), "receipt": str(receipt_path),
                          "receipt_sha256": row.get("receipt_sha256"), "indexed_at": row.get("at")}
    if receipt is None:
        checks.append(_check("original_receipt_present", False, str(receipt_path)))
        return _finish(result)
    # ---- 1. the original receipt, index row, log and every command log are what they were
    binding = receipt.get("source_binding") or {}
    log_path = Path(receipt.get("lane_log") or "")
    commands = receipt.get("commands") or []
    problems = []
    if sha256_file(receipt_path) != row.get("receipt_sha256"):
        problems.append("the receipt's bytes differ from the index row's digest")
    for name, expected, actual in (("lane", lane, receipt.get("lane")), ("run", row.get("run"), receipt.get("run")),
                                   ("head", row.get("head"), binding.get("head")),
                                   ("source_digest", row.get("source_digest"), binding.get("source_digest")),
                                   ("result", row.get("result"), receipt.get("result")),
                                   ("contract", env.contract_sha256, (receipt.get("contract") or {}).get("sha256"))):
        if expected != actual:
            problems.append(f"the receipt's {name} is {actual!r}, the index row or contract says {expected!r}")
    if receipt.get("rehearsal"):
        problems.append("the receipt is a rehearsal")
    if receipt.get("result") not in ("PASS", "FAIL"):
        problems.append(f"the receipt's result is {receipt.get('result')!r}, not an executed PASS or FAIL")
    if not (binding.get("clean") and (receipt.get("source_binding_after") or {}).get("head") == binding.get("head")):
        problems.append("the original subject was not a clean committed head before and after")
    if not log_path.is_file() or sha256_file(log_path) != receipt.get("lane_log_sha256_at_receipt"):
        problems.append("the lane log is missing or differs from the digest taken at the receipt")
    bad_logs = [c.get("lane") for c in commands
                if not c.get("log_path") or not Path(c["log_path"]).is_file()
                or sha256_file(c["log_path"]) != c.get("log_sha256")]
    if bad_logs:
        problems.append(f"{len(bad_logs)} command log(s) are missing or differ from their recorded digest: {bad_logs[:5]}")
    checks.append(_check("original_receipt_and_logs_are_what_they_were", not problems, problems or
                         {"commands": len(commands), "receipt_sha256": row.get("receipt_sha256")}))
    result["original"].update({"counts": receipt.get("counts"), "log": str(log_path),
                               "log_sha256": receipt.get("lane_log_sha256_at_receipt"), "commands": len(commands),
                               "started_at": receipt.get("started_at"), "finished_at": receipt.get("finished_at")})
    # ---- 2. the sealed original submission names the same bytes
    sealed = env.original_submission
    if sealed is None:
        checks.append(_check("sealed_original_submission_agrees", False, "no sealed original submission was supplied"))
    else:
        evidence = {e.get("id"): e for e in sealed.get("evidence") or []}
        lane_row = next((r for r in sealed.get("lanes") or [] if r.get("id") == lane), {})
        mismatch = []
        for identity, path in ((f"E-LANE-{lane}-RECEIPT", receipt_path), (f"E-LANE-{lane}-LOG", log_path)):
            if identity not in evidence:
                mismatch.append(f"{identity} is not in the sealed submission")
            elif evidence[identity].get("sha256") != sha256_file(path):
                mismatch.append(f"{identity} differs from the sealed submission")
        if (sealed.get("candidate") or {}).get("head") != row.get("head"):
            mismatch.append("the sealed submission's subject is not the original head")
        if lane_row.get("status") != receipt.get("result"):
            mismatch.append("the sealed lane status differs from the receipt's result")
        checks.append(_check("sealed_original_submission_agrees", not mismatch, mismatch or
                             {"source": env.original_submission_source}))
    # ---- 3. the two heads
    original_head = str(row["head"])
    checks.append(_check("original_head_is_an_ancestor_of_the_current_head", env.is_ancestor(original_head, env.head),
                         {"original": original_head, "current": env.head}))
    tree_ok = env.git("rev-parse", f"{original_head}^{{tree}}") == binding.get("tree")
    checks.append(_check("recorded_tree_is_the_original_heads_tree", tree_ok))
    delta = changed_paths(env, original_head, env.head)
    unknown = [path for _, path in delta if path not in DELTA_CLASSES]
    classes = {path: DELTA_CLASSES[path][0] for _, path in delta if path in DELTA_CLASSES}
    result["delta"] = {"changed": [f"{s}\t{p}" for s, p in delta], "classes": classes, "unclassified": unknown}
    checks.append(_check("every_changed_tracked_path_is_declared", not unknown, unknown or {"changed": len(delta)}))
    tracked = env.tracked(env.head)
    # ---- 4. the runner delta
    proof = runner_delta(env, original_head, env.head) if any(c == RUNNER for c in classes.values()) else \
        {"holds": True, "problems": [], "note": "the runner is unchanged between the two heads"}
    result["runner_delta"] = proof
    checks.append(_check("runner_delta_is_bookkeeping_only", proof["holds"], proof["problems"] or proof.get("meaning")))
    # ---- 5. what each retained command executes
    allowed = set(REEXECUTABLE.get(lane, ()))
    changed_set = {path for _, path in delta}
    report: list[dict[str, Any]] = []
    refusals: list[str] = []
    must_reexecute: list[dict[str, Any]] = []
    for command in commands:
        argv = [str(t) for t in (command.get("command") or [])]
        scripts, tests = command_entries(env, argv, str(command.get("cwd") or env.repo))
        closure = sorted(local_closure(env, env.head, scripts, tracked)) if scripts else []
        touched = sorted(set(closure) & changed_set)
        touched_outputs = [p for p in touched if classes.get(p) in (OUTPUT_TOOL, NEW_TOOL, RUNNER)]
        name = str(command.get("lane", "")).split("__", 1)[-1]
        row_c = {"command": name, "scripts": scripts, "runs_tests": tests, "closure_files": len(closure),
                 "changed_files_executed": touched, "disposition": "RETAINED"}
        if touched_outputs:
            if name in allowed:
                row_c["disposition"] = "EXECUTED_AGAIN_IN_THIS_CHECK"
                must_reexecute.append({"name": name, "argv": argv, "cwd": command.get("cwd")})
            else:
                refusals.append(f"{name} executes changed file(s) {touched_outputs} and is not an allowlisted command")
        if tests and any(c == NEW_TEST for c in classes.values()):
            refusals.append(f"{name} runs tests and a test file was added")
        if any(str(a).replace("\\", "/").rstrip("/").split("/")[-1] == "provenance" or "provenance/" in str(a).replace("\\", "/")
               for a in argv) and any(c == PROVENANCE for c in classes.values()):
            refusals.append(f"{name} reads the provenance files, which changed")
        if name == "git_archive_committed_subject" or "archive" in argv:
            specs = argv[argv.index("--") + 1:] if "--" in argv else []
            moved = [p for p in changed_set if any(p == s.rstrip("/") or p.startswith(s.rstrip("/") + "/") for s in specs)]
            row_c["archive_pathspecs"] = specs
            if moved:
                refusals.append(f"{name} archived path(s) that changed: {moved[:5]}")
        report.append(row_c)
    result["commands"] = report
    checks.append(_check("no_retained_command_executes_a_changed_dependency", not refusals, refusals or
                         {"commands": len(report), "executed_again": [m["name"] for m in must_reexecute]}))
    # ---- 6. the runner's bound tools and the interpreter
    try:
        current = env.bind_source()
    except (SystemExit, OSError, subprocess.CalledProcessError) as error:
        current = {}
        checks.append(_check("runner_binding_computed", False, str(error)))
    if current:
        differing = sorted(k for k in set(binding) | set(current) if k not in BINDING_MAY_DIFFER
                           and binding.get(k) != current.get(k))
        explained = []
        for key, path in RUNNER_DIGEST_FILES.items():
            old, new = env.blob_bytes(original_head, path), env.blob_bytes(env.head, path)
            explained.append(old is not None and new is not None and sha256_bytes(old) == binding.get(key)
                             and sha256_bytes(new) == current.get(key))
        clean_now = bool(current.get("clean")) and current.get("head") == env.head
        checks.append(_check("bound_tool_digests_are_unchanged", not differing, differing or
                             {"keys_compared": len(set(binding) | set(current)) - len(BINDING_MAY_DIFFER)}))
        checks.append(_check("changed_runner_digests_are_the_committed_files", all(explained),
                             "each differing runner digest is the SHA-256 of that file's committed text at its own head"))
        checks.append(_check("current_subject_is_clean_and_committed", clean_now, {"clean": current.get("clean")}))
    same, why = interpreters_match(receipt.get("interpreter"), env.bind_interpreter())
    checks.append(_check("interpreter_is_the_recorded_one", same, why))
    # ---- 7. every recorded (path, digest) pair of the receipt
    bad, verified, skipped = [], 0, 0
    for pair in recorded_pairs(receipt):
        path = Path(pair["path"])
        rel = None
        if under(path, env.repo):
            rel = Path(os.path.relpath(path, env.repo)).as_posix()
        if rel in changed_set and classes.get(rel) == RUNNER:
            skipped += 1  # the runner digests are explained by check 4 and 6
            continue
        if not any(under(path, root) for root in env.immutable_roots):
            skipped += 1  # scratch (fixtures, packaging) is verified by the lane's own checks below, never by guesswork
            continue
        if not path.is_file():
            bad.append(f"{pair['pointer']}: {path} is missing")
        elif sha256_file(path) != pair["sha256"]:
            bad.append(f"{pair['pointer']}: {path} differs from its recorded digest")
        else:
            verified += 1
    checks.append(_check("every_recorded_path_and_digest_pair_holds", not bad, bad[:8] or
                         {"verified": verified, "not_paired_or_scratch": skipped}))
    # ---- 8. the lane's own environment and data
    extra = env.lane_checks.get(lane)
    if extra is not None:
        checks += extra(env, receipt, result)
    # ---- 9. the commands executed again now, or the recorded ones verified
    reruns: list[dict[str, Any]] = []
    for item in must_reexecute:
        if reexecute:
            reruns.append(run_again(env, lane, item, log_dir, stamp))
        else:
            previous = next((r for r in (recorded or {}).get("reexecuted", []) if r.get("name") == item["name"]), None)
            ok = bool(previous and previous.get("head") == env.head and previous.get("exit") == 0
                      and Path(previous.get("log") or "").is_file() and sha256_file(previous["log"]) == previous.get("log_sha256"))
            reruns.append({**(previous or {"name": item["name"]}), "verified_against_its_log": ok})
    result["reexecuted"] = reruns
    if must_reexecute:
        checks.append(_check("commands_that_read_a_changed_tool_were_executed_again_at_this_head",
                             all(r.get("exit") == 0 and (reexecute or r.get("verified_against_its_log")) for r in reruns)
                             and len(reruns) == len(must_reexecute),
                             [{k: r.get(k) for k in ("name", "exit", "log", "log_sha256", "head")} for r in reruns]))
    return _finish(result)


def _finish(result: dict[str, Any]) -> dict[str, Any]:
    result["holds"] = bool(result["checks"]) and all(c["holds"] for c in result["checks"])
    result["refused_by"] = [c["name"] for c in result["checks"] if not c["holds"]]
    return result


def run_again(env: Env, lane: str, item: dict[str, Any], log_dir: Path | None, stamp: str | None) -> dict[str, Any]:
    """Execute one allowlisted command again at the current head, its console kept in a create-only log."""

    argv = [env.python if index == 0 else token for index, token in enumerate(item["argv"])]
    log_dir = log_dir or (env.out_root / REUSE_DIR / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"REUSE_{lane}_{item['name']}_{stamp or utc_now().replace(':', '').replace('-', '')[:19]}.log"
    started = utc_now()
    completed = subprocess.run(argv, cwd=item.get("cwd") or str(env.repo), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=env.scratch_env(), check=False)
    with log.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{LABEL} retained-lane check: {item['name']} executed again at head {env.head}\n"
                     f"argv: {json.dumps(argv)}\nstarted: {started}\nexit: {completed.returncode}\n--- stdout ---\n"
                     f"{completed.stdout}\n--- stderr ---\n{completed.stderr}\n")
    return {"name": item["name"], "argv": argv, "cwd": item.get("cwd"), "head": env.head, "exit": completed.returncode,
            "log": str(log), "log_sha256": sha256_file(log), "started_at": started, "finished_at": utc_now()}


# ------------------------------------------------------------------ lane-specific environment and data checks


def installed_consumer_checks(env: Env, receipt: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    """INSTALLED_CONSUMER_C01: the wheel, the installed files against the current committed source, the delivered
    database and the successor, all as the receipt recorded them."""

    details = receipt.get("details") or {}
    checks = []
    installed = details.get("installed") or {}
    wheel = Path(installed.get("wheel") or "")
    checks.append(_check("packaged_wheel_is_the_recorded_one", wheel.is_file() and sha256_file(wheel) == details.get("wheel_sha256"),
                         {"wheel": str(wheel), "recorded": details.get("wheel_sha256")}))
    equivalence = details.get("installed_source_equivalence") or {}
    record = Path(equivalence.get("record") or "")
    problems: list[str] = []
    equal = files = 0
    if not record.is_file():
        problems.append(f"the installed distribution's RECORD is missing: {record}")
    else:
        site = record.parent.parent
        for line in record.read_text(encoding="utf-8").splitlines():
            name = line.split(",", 1)[0]
            if not name.startswith("aggie_analytics/") or name.endswith(".pyc") or "/__pycache__/" in name:
                continue  # every installed file of the package: the Python sources and the packaged schema files
            files += 1
            blob = env.blob_bytes(env.head, f"src/{name}")
            path = site / name
            if blob is None or not path.is_file():
                problems.append(f"{name}: missing")
            elif sha256_file(path) == sha256_bytes(blob):
                equal += 1
            else:
                problems.append(f"{name}: the installed file differs from the current committed source")
        if files != equivalence.get("installed_files") or equal != equivalence.get("installed_equal_to_committed_source"):
            problems.append(f"installed files {files}/{equal} differ from the recorded {equivalence.get('installed_files')}/"
                            f"{equivalence.get('installed_equal_to_committed_source')}")
    checks.append(_check("installed_files_equal_the_current_committed_source", not problems, problems[:6] or
                         {"installed_files": files, "equal": equal}))
    unchanged = details.get("delivered_database_unchanged") or {}
    database = env.database
    if database is not None:
        current = sha256_file(database) if Path(database).is_file() else None
        checks.append(_check("delivered_database_is_the_recorded_one",
                             current is not None and current == unchanged.get("expected") == unchanged.get("before")
                             == unchanged.get("after"), {"database": str(database), "current": current}))
    census = (details.get("installed_identity_census") or {}).get("census") or {}
    successor = Path(census.get("successor") or "")
    checks.append(_check("successor_is_the_recorded_one", successor.is_file()
                         and sha256_file(successor) == census.get("successor_sha256"), {"successor": str(successor)}))
    return checks


def platform_carry_checks(env: Env, receipt: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    """PLATFORM_CARRY: the AFTER platform evidence its receipt names is the evidence it was; no request is made."""

    details = receipt.get("details") or {}
    reads = details.get("platform_reads") or {}
    missing = [mode for mode, row in reads.items() if not (row.get("summary") and Path(row["summary"]).is_file())]
    return [_check("platform_reads_evidence_is_present", not missing and bool(reads), missing or sorted(reads)),
            _check("no_platform_request_is_made_by_this_check", True,
                   "the AFTER reads, the private Jira successor and the two granted comments are retained records; "
                   "reading them again would spend the ceiling this attempt has left")]


LANE_CHECKS = {"INSTALLED_CONSUMER_C01": installed_consumer_checks, "PLATFORM_CARRY": platform_carry_checks}


# ------------------------------------------------------------------ proofs on disk


def proof_dir(out_root: Path) -> Path:
    return out_root / REUSE_DIR


def write_proof(env: Env, result: dict[str, Any], *, rehearsal: bool, stamp: str) -> Path:
    directory = proof_dir(env.out_root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"REUSE_{result['lane']}_{env.head[:12]}_{stamp}.json"
    document = {
        "label": f"{LABEL} IN_PROGRESS_LOCAL_WORK_REMAINS (retained-lane dependency check {result['lane']}"
                 f"{' REHEARSAL, NOT EVIDENCE' if rehearsal else ''})",
        "schema": SCHEMA, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "mode": MODE,
        "rehearsal": rehearsal, "not_a_fresh_execution": True, "checked_at": utc_now(),
        "original_handoff": env.handoff_paths, **result,
        "rule": ("The lane's original head, receipt, log, counts and result are retained unchanged and are never "
                 "relabelled fresh. This record is bound to the current head and is recomputed, not trusted, every "
                 "time the accounting builds or checks; any changed, missing or forged dependency refuses it."),
    }
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False, default=str) + "\n")
    return path


def latest_proof(out_root: Path, lane: str, head: str) -> tuple[Path, dict[str, Any]] | None:
    found = sorted(proof_dir(out_root).glob(f"REUSE_{lane}_{head[:12]}_*.json")) if proof_dir(out_root).is_dir() else []
    for path in reversed(found):
        document = read_json(path)
        if not document.get("rehearsal"):
            return path, document
    return None


def verified_lanes(env: Env, lanes: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """(accepted, refused): the lanes whose latest proof for the current head still holds when every check is
    recomputed now, and the ones a proof exists for but the recomputation refuses. An accepted value carries the proof's
    path and digest, the original execution and the recorded re-executed commands; nothing is accepted on a stored
    record alone."""

    accepted: dict[str, dict[str, Any]] = {}
    refused: dict[str, Any] = {}
    for lane in lanes:
        proof = latest_proof(env.out_root, lane, env.head)
        if proof is None:
            continue
        path, document = proof
        if not document.get("holds") or (document.get("current") or {}).get("head") != env.head:
            refused[lane] = {"proof": str(path), "refused_by": document.get("refused_by") or ["the recorded check did not hold"]}
            continue
        handoff = document.get("original_handoff") or {}
        if handoff.get("archive") and env.original_submission is None:
            attach_handoff(env, Path(handoff["archive"]), Path(handoff["manifest"]))
        current = check_lane(env, lane, reexecute=False, recorded=document)
        if not current["holds"]:
            refused[lane] = {"proof": str(path), "refused_by": current["refused_by"]}
            continue
        accepted[lane] = {"proof": str(path), "proof_sha256": sha256_file(path), "original": current["original"],
                          "checks": len(current["checks"]), "reexecuted": current["reexecuted"],
                          "delta": current.get("delta"), "commands": current.get("commands"),
                          "original_handoff": handoff}
    return accepted, refused


# ------------------------------------------------------------------ production environment and CLI


def attach_handoff(env: Env, archive: Path, manifest: Path) -> None:
    """Bind the sealed original submission: the retained archive must equal its manifest, and the submission inside it
    must equal the manifest's digest for it."""

    recorded = read_json(manifest)
    if sha256_file(archive) != recorded.get("archive_sha256"):
        raise SystemExit("the original handoff archive differs from its manifest")
    with zipfile.ZipFile(archive) as bundle:
        data = bundle.read("submission.json")
    if sha256_bytes(data) != next(r["sha256"] for r in recorded["files"] if r["id"] == "submission.json"):
        raise SystemExit("the archived submission differs from its manifest")
    env.original_submission = json.loads(data.decode("utf-8"))
    env.original_submission_source = f"{archive} :: submission.json (manifest {manifest})"
    env.handoff_paths = {"archive": str(archive), "manifest": str(manifest), "archive_sha256": sha256_file(archive),
                         "manifest_sha256": sha256_file(manifest)}


def production_env(contract: Path, out_root: Path, *, head: str | None = None) -> Env:
    import attempt09_git  # noqa: PLC0415
    import attempt11_lanes as lanes  # noqa: PLC0415

    lanes.rebind()
    repo = Path(lanes.base.WORKTREE)
    environment = {k: v for k, v in os.environ.items() if k not in ("GIT_ASKPASS", "GIT_EDITOR", "GIT_TERMINAL_PROMPT")}
    for name, value in dict(lanes.credential_scrub()).items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "TEMP": str(lanes.PACKAGING_ROOT),
                        "TMP": str(lanes.PACKAGING_ROOT)})

    def git(*args: str) -> str:
        return attempt09_git.git(*args, repo=repo, env=environment)

    def git_bytes(*args: str) -> bytes:
        done = subprocess.run(attempt09_git.command(*args, repo=repo), capture_output=True, env=environment, check=False)
        if done.returncode != 0:
            raise SystemExit(f"git {' '.join(args)} failed: {done.stderr.decode('utf-8', 'replace').strip()}")
        return done.stdout

    def passthrough() -> bool:
        from types import SimpleNamespace  # noqa: PLC0415

        sentinel = {"token": "0" * 32, "operation": "LANE START_CONTEXT x", "decision": "ADMITTED"}
        paths = {"final_output_ledger": Path("x")}
        cases = [(SimpleNamespace(rehearsal=False), False), (SimpleNamespace(rehearsal=False), True),
                 (SimpleNamespace(rehearsal=True), False)]
        return (all(lanes._reservation_for_check(args, final, sentinel, paths) is sentinel for args, final in cases)
                and lanes._reservation_for_check(SimpleNamespace(rehearsal=True), True, None, {}) is None)

    return Env(repo=repo, out_root=out_root, contract_sha256=sha256_file(contract), head=head or git("rev-parse", "HEAD"),
               git=git, git_bytes=git_bytes, bind_source=lanes.bind_source,
               bind_interpreter=lambda: interpreter_identity(Path(sys.executable)), python=sys.executable,
               immutable_roots=(out_root, Path(lanes.DATA_ROOT), repo), scratch_env=lambda: dict(environment),
               passthrough=passthrough, database=Path(lanes.DELIVERED_DB), lane_checks=dict(LANE_CHECKS))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("check", "verify"))
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--lane", action="append", required=True)
    parser.add_argument("--write", action="store_true", help="write the create-only proof records (check only)")
    parser.add_argument("--original-handoff-zip", type=Path)
    parser.add_argument("--original-handoff-manifest", type=Path)
    parser.add_argument("--rehearsal-head", help="development only: bind to this commit instead of HEAD; never evidence")
    args = parser.parse_args(argv)
    env = production_env(args.contract.resolve(), args.out_root.resolve(), head=args.rehearsal_head)
    if args.original_handoff_zip:
        attach_handoff(env, args.original_handoff_zip.resolve(), args.original_handoff_manifest.resolve())
    stamp = utc_now().replace(":", "").replace("-", "").replace("+", "").replace(".", "")[:20] + "Z"
    outcomes = []
    for lane in args.lane:
        result = check_lane(env, lane, reexecute=args.mode == "check", stamp=stamp)
        record = None
        if args.mode == "check" and args.write:
            record = str(write_proof(env, result, rehearsal=bool(args.rehearsal_head), stamp=stamp))
        outcomes.append({"lane": lane, "holds": result["holds"], "refused_by": result["refused_by"], "record": record,
                         "checks": [(c["name"], c["holds"]) for c in result["checks"]],
                         "reexecuted": [(r.get("name"), r.get("exit")) for r in result["reexecuted"]]})
    print(json.dumps({"label": f"{LABEL} retained-lane dependency {args.mode}", "head": env.head, "lanes": outcomes},
                     indent=2, ensure_ascii=False))
    return 0 if all(o["holds"] for o in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
