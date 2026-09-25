r"""Cycle #37 — Attempt #3 — run unittest and record every outcome by exact identity (MF37A02-05 repair).

``python -m aggie_analytics.validation.unittest_census --records OUT.jsonl --summary OUT.json
[--selected-root ROOT] [--start-dir DIR | NAME ...]``

Two defects in the Attempt #2 full-suite lanes are closed here and in :mod:`lane_harness`:

* **Import root.** ``tests`` and ``src`` were on the path but the repository root was not, so
  ``test_acceptance_governance`` -- the first module in discovery order to ``import tools`` before any other
  module had inserted the root itself -- failed with ``ModuleNotFoundError: No module named 'tools'``. The
  lanes now bind the selected repository root explicitly, and this runner *verifies* the binding after the
  run: every imported module that lives in a Git checkout must live in the selected one, and ``tools`` and
  ``aggie_analytics`` in particular must resolve inside it. A module imported from another checkout is a
  refusal (exit 3), never a pass: an import that silently resolves to someone else's source tests the wrong
  code.
* **Accounting.** The verbose-text parser missed four of seventeen skips (a docstring line split the
  identity from its outcome; three reasons were printed in double quotes). The text is still the primary
  human record and is written unchanged; this runner additionally records each outcome as a JSON line from a
  result class, so the identities can be reconciled from two independent sources and against unittest's own
  summary counts.

What each JSON record carries: ``kind`` (``PASS``, ``FAIL``, ``ERROR``, ``SKIP``, ``EXPECTED_FAILURE``,
``UNEXPECTED_SUCCESS``, ``SUBTEST_FAIL``, ``SUBTEST_ERROR``, ``SUBTEST_SKIP``), the exact ``id`` unittest
uses, the subtest description, the skip reason, whether the row is an import failure
(``unittest.loader._FailedTest``) or a class/module fixture (``setUpClass``/``setUpModule``), and the
exception type. ``inventory`` lists every test *discovered*, including methods of a class whose
``setUpClass`` skipped or failed and which therefore never ran and are not in ``Ran N``.

Nothing here decides whether a scientific result is acceptable; it decides what a test run did.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
import unittest
from pathlib import Path
from typing import Any

CENSUS_VERSION = "BAS-UNITTEST-CENSUS-v37.3"
EXIT_ORIGIN_VIOLATION = 3

_FAILED_TEST = "unittest.loader._FailedTest"


def _identity(test: Any) -> dict[str, Any]:
    """The exact identity of a test, subtest or fixture holder, as unittest names it."""

    from unittest.case import _SubTest  # noqa: PLC0415 - private but stable since 3.4
    from unittest.suite import _ErrorHolder  # noqa: PLC0415

    if isinstance(test, _SubTest):
        parent = test.test_case
        return {"id": parent.id(), "subtest": test._subDescription(), "module": type(parent).__module__,
                "class": type(parent).__qualname__, "method": getattr(parent, "_testMethodName", None),
                "fixture": None, "is_import_error": False}
    if isinstance(test, _ErrorHolder):
        # description is "setUpClass (module.Class)" or "setUpModule (module)" and friends.
        description = test.description
        fixture, _, target = description.partition(" (")
        return {"id": description, "subtest": None, "module": target.rstrip(")").rsplit(".", 1)[0],
                "class": target.rstrip(")").rsplit(".", 1)[-1] if "." in target else None, "method": None,
                "fixture": fixture, "is_import_error": False}
    test_id = test.id()
    return {"id": test_id, "subtest": None, "module": type(test).__module__, "class": type(test).__qualname__,
            "method": getattr(test, "_testMethodName", None), "fixture": None,
            "is_import_error": test_id.startswith(_FAILED_TEST)}


class CensusResult(unittest.TextTestResult):
    """A TextTestResult (so the verbose text is unchanged) that also records every outcome."""

    records: list[dict[str, Any]]

    def __init__(self, stream, descriptions, verbosity, *, durations=None):
        super().__init__(stream, descriptions, verbosity, durations=durations)
        self.records = []

    def _record(self, kind: str, test: Any, *, reason: str | None = None, err: Any = None) -> None:
        row = {"kind": kind, **_identity(test)}
        if reason is not None:
            row["reason"] = reason
        if err is not None:
            exc_type = err[0]
            row["exception"] = f"{exc_type.__module__}.{exc_type.__qualname__}" if exc_type else None
            row["message"] = str(err[1])[:500] if err[1] is not None else None
        self.records.append(row)

    def addSuccess(self, test):  # noqa: N802 - unittest API
        super().addSuccess(test)
        self._record("PASS", test)

    def addFailure(self, test, err):  # noqa: N802
        super().addFailure(test, err)
        self._record("FAIL", test, err=err)

    def addError(self, test, err):  # noqa: N802
        super().addError(test, err)
        self._record("ERROR", test, err=err)

    def addSkip(self, test, reason):  # noqa: N802
        super().addSkip(test, reason)
        from unittest.case import _SubTest  # noqa: PLC0415

        self._record("SUBTEST_SKIP" if isinstance(test, _SubTest) else "SKIP", test, reason=reason)

    def addExpectedFailure(self, test, err):  # noqa: N802
        super().addExpectedFailure(test, err)
        self._record("EXPECTED_FAILURE", test, err=err)

    def addUnexpectedSuccess(self, test):  # noqa: N802
        super().addUnexpectedSuccess(test)
        self._record("UNEXPECTED_SUCCESS", test)

    def addSubTest(self, test, subtest, err):  # noqa: N802
        super().addSubTest(test, subtest, err)
        if err is not None:
            kind = "SUBTEST_FAIL" if issubclass(err[0], test.failureException) else "SUBTEST_ERROR"
            self._record(kind, subtest, err=err)


def inventory(suite: unittest.TestSuite) -> list[str]:
    """Every discovered test id, in discovery order, including never-run methods and import failures."""

    found: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, unittest.TestSuite):
            for child in item:
                walk(child)
        else:
            found.append(item.id())

    walk(suite)
    return found


def _git_checkout_of(path: Path, cache: dict[str, str | None]) -> str | None:
    """The nearest enclosing directory holding a ``.git`` entry, or None."""

    current = path.parent
    visited: list[str] = []
    while True:
        key = os.path.normcase(str(current))
        if key in cache:
            result = cache[key]
            break
        visited.append(key)
        if (current / ".git").exists():
            result = os.path.normcase(str(current))
            break
        if current.parent == current:
            result = None
            break
        current = current.parent
    for key in visited:
        cache[key] = result
    return result


def origin_audit(selected_root: Path | None, runner_modules: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Where every module the tests imported came from, and whether any came from another checkout.

    ``runner_modules`` were already imported when the census started -- the census itself and the packages it
    lives in. Their origins are reported separately (``runner_origins``); the verdict is about what the tests
    imported, and a lane that also needs the runner inside the selected root checks that field itself.
    """

    selected = os.path.normcase(str(selected_root.resolve())) if selected_root else None
    cache: dict[str, str | None] = {}
    foreign: list[dict[str, str]] = []
    checkouts: dict[str, int] = {}
    runner_origins = {}
    for name in sorted(runner_modules):
        file = getattr(sys.modules.get(name), "__file__", None)
        if file and name.startswith(("aggie_analytics", "__main__")):
            origin = str(Path(file).resolve())
            runner_origins[name] = {"origin": origin, "inside_selected_root": bool(
                selected and os.path.normcase(origin).startswith(selected + os.sep))}
    for name, module in list(sys.modules.items()):
        if name in runner_modules:
            continue
        file = getattr(module, "__file__", None)
        if not file:
            continue
        try:
            path = Path(file).resolve()
        except (OSError, ValueError):
            continue
        checkout = _git_checkout_of(path, cache)
        if checkout is None:
            continue
        checkouts[checkout] = checkouts.get(checkout, 0) + 1
        if selected is not None and checkout != selected:
            foreign.append({"module": name, "file": str(path), "checkout": checkout})
    key_modules = {}
    for name in ("tools", "aggie_analytics"):
        module = sys.modules.get(name)
        file = getattr(module, "__file__", None) if module else None
        origin = str(Path(file).resolve()) if file else None
        inside = bool(origin and selected and os.path.normcase(origin).startswith(selected + os.sep))
        key_modules[name] = {"imported": module is not None, "origin": origin, "inside_selected_root": inside,
                             "imported_by": "runner" if name in runner_modules else ("tests" if module else None)}
    problems = [f"{row['module']} imported from {row['checkout']}" for row in foreign[:50]]
    for name, row in key_modules.items():
        if row["imported_by"] == "tests" and selected is not None and not row["inside_selected_root"]:
            problems.append(f"{name} resolved to {row['origin']}, outside the selected root {selected}")
    return {"selected_root": selected, "checkouts_seen": checkouts, "foreign_modules": foreign,
            "foreign_module_count": len(foreign), "key_modules": key_modules, "runner_origins": runner_origins,
            "runner_inside_selected_root": bool(runner_origins) and all(
                row["inside_selected_root"] for row in runner_origins.values()),
            "problems": problems, "holds": not problems}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="test modules/names; default is discovery from --start-dir")
    parser.add_argument("--start-dir", default=".")
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--selected-root", type=Path, default=None,
                        help="the repository whose source this run must exercise; imports from any other Git "
                             "checkout are refused")
    parser.add_argument("-v", "--verbose", action="count", default=2)
    args = parser.parse_args(argv)

    started = time.time()
    runner_modules = frozenset(sys.modules)
    loader = unittest.defaultTestLoader
    if args.names:
        suite = loader.loadTestsFromNames(args.names)
        mode = "names"
    else:
        suite = loader.discover(args.start_dir, pattern=args.pattern)
        mode = "discover"
    discovered = inventory(suite)
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=args.verbose, resultclass=CensusResult)
    try:
        result = runner.run(suite)
    except BaseException:  # noqa: BLE001 - a crashed run is recorded, then re-raised
        traceback.print_exc()
        raise
    audit = origin_audit(args.selected_root, runner_modules)
    args.records.parent.mkdir(parents=True, exist_ok=True)
    with args.records.open("w", encoding="utf-8", newline="\n") as handle:
        for row in result.records:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "census_version": CENSUS_VERSION,
        "mode": mode,
        "names": args.names,
        "start_dir": os.path.abspath(args.start_dir),
        "cwd": os.getcwd(),
        "interpreter": sys.executable,
        "python_version": sys.version,
        "sys_path_head": sys.path[:6],
        "seconds": round(time.time() - started, 3),
        "discovered": discovered,
        "discovered_count": len(discovered),
        "tests_run": result.testsRun,
        "framework_counts": {"failures": len(result.failures), "errors": len(result.errors),
                             "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
                             "unexpected_successes": len(result.unexpectedSuccesses)},
        "was_successful": result.wasSuccessful(),
        "records": str(args.records),
        "record_count": len(result.records),
        "origin_audit": audit,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not audit["holds"]:
        print("UNITTEST CENSUS: import origin violation: " + "; ".join(audit["problems"][:10]), file=sys.stderr)
        return EXIT_ORIGIN_VIOLATION
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
