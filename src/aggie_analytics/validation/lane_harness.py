r"""Honest unittest accounting for validation lanes.

MF37-04 repair. Two specific losses in the Cycle 36 runner made a lane result
say less than it appeared to:

1. ``parse_unittest`` matched ``^(FAIL|ERROR):\s+(\S+)`` and collected the
   results into a ``set``. ``\S+`` stops at the method name, so two genuinely
   different failures --

       ERROR: test_shared (suite_alpha.Alpha.test_shared)
       ERROR: test_shared (suite_beta.Beta.test_shared)

   -- both reduced to ``"test_shared"`` and the set kept one. A baseline
   comparison "about identities, not counts" then compared identities that had
   already been merged, and the reported ``failed_or_errored_count`` (1)
   disagreed with unittest's own summary (``errors=2``) with nothing to notice
   the contradiction.

2. ``run_lane`` derived ``PASS`` from ``exit_code == 0``. ``unittest`` exits 0
   for a suite in which every test was skipped, so a lane that executed no
   assertion at all reported the same state as a lane that executed and passed
   thousands.

Both are fixed here rather than in the caller, because the caller is not the
only consumer and a second copy of this logic is how the two drifted apart in
the first place. The parser keeps unittest's own summary counts beside the
parsed identities, and :func:`reconcile` reports a disagreement between them
as a defect in the parse instead of silently preferring one.

Nothing here decides whether a scientific result is acceptable. It decides
only what a test run actually did.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from aggie_analytics import atomic_io as _bas_atomic

__all__ = [
    "BLOCKED",
    "FAIL",
    "NOT_RUN",
    "PASS",
    "UNSATISFIED",
    "LaneOutcome",
    "parse_unittest",
    "reconcile",
    "run_lane",
]

PASS = "PASS"
FAIL = "FAIL"
NOT_RUN = "NOT_RUN"
BLOCKED = "BLOCKED"
#: A lane whose command ran and exited zero, but which executed no test. It is
#: deliberately not ``PASS`` and deliberately not ``FAIL``: the command is
#: reported as executed, the acceptance lane is reported as unsatisfied.
UNSATISFIED = "UNSATISFIED_NO_EXECUTED_TEST"

# ``FAIL: name (module.Class.name)`` / ``ERROR: name (module.Class.name)``,
# optionally followed by a subtest discriminator ``[i=3]``. The dotted
# identity inside the parentheses is what makes two same-named methods in
# different modules distinct, so it is the identity that is kept.
_IDENTITY = re.compile(
    r"^(?P<kind>FAIL|ERROR):\s+(?P<method>\S+)\s+\((?P<dotted>[^)]*)\)(?P<subtest>.*)$",
    re.M,
)
#: Older/plainer output that carries no parenthesised identity at all.
_IDENTITY_BARE = re.compile(r"^(?P<kind>FAIL|ERROR):\s+(?P<method>\S+)\s*$", re.M)
#: A verbose status line for a skip, in every shape unittest prints (MF37A02-05). The Attempt #2 pattern
#: accepted only ``name (dotted) ... skipped 'reason'`` on one line and so missed four of seventeen skips:
#:
#: * a test with a docstring prints its first line on the *next* line, before `` ... skipped``;
#: * ``repr`` quotes a reason containing a single quote with double quotes;
#: * a skipped subtest is indented two spaces and carries ``[msg]``/``(k=v)`` after the identity;
#: * a class or module fixture prints ``setUpClass (module.Class)``.
_SKIP = re.compile(
    r"^(?P<indent>  )?(?P<method>\S+) \((?P<dotted>[^()\n]*)\)"
    r"(?P<subtest>(?: \[[^\n]*?\])?(?: \((?:<subtest>|[^()\n]*=[^\n]*?)\))?)"
    r"(?:\n(?P<doc>[^\n]*?))? \.\.\. skipped (?P<reason>'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\")$",
    re.M,
)
_EXPECTED_FAILURE = re.compile(r"^(?P<method>\S+) \((?P<dotted>[^()\n]*)\)(?:\n[^\n]*?)? \.\.\. expected failure$", re.M)
_UNEXPECTED_SUCCESS = re.compile(r"^(?P<method>\S+) \((?P<dotted>[^()\n]*)\)(?:\n[^\n]*?)? \.\.\. unexpected success$", re.M)
#: unittest's fixture holders; their parenthesised part is the module or class, not a test id.
_FIXTURES = frozenset({"setUpClass", "tearDownClass", "setUpModule", "tearDownModule"})


def _unquote_reason(text: str) -> str:
    import ast

    try:
        return str(ast.literal_eval(text))
    except (ValueError, SyntaxError):
        return text[1:-1]


def skip_identity(method: str, dotted: str, subtest: str = "") -> str:
    """The identity a skip is known by: the dotted test id, a fixture's own name, plus any subtest part."""

    base = f"{method} ({dotted})" if method in _FIXTURES else dotted
    return f"{base} {subtest}".strip() if subtest else base
_COUNT_LINE = re.compile(r"^Ran (\d+) tests? in ([\d.]+)s$", re.M)
_RESULT_LINE = re.compile(r"^(OK|FAILED)\b(.*)$", re.M)
_SUMMARY_FIELD = re.compile(r"(failures|errors|skipped|expected failures|unexpected successes)=(\d+)")
#: ``unittest.loader._FailedTest`` is how an import error is reported.
_IMPORT_ERROR_MARKER = "unittest.loader._FailedTest"


def _summary_counts(summary_line: str | None) -> dict[str, int]:
    if not summary_line:
        return {}
    return {
        key.replace(" ", "_"): int(value)
        for key, value in _SUMMARY_FIELD.findall(summary_line)
    }


def parse_unittest(output: str) -> dict[str, Any]:
    """Parse a unittest run without merging distinct identities.

    Returned identities are ordered as unittest emitted them and are *not*
    deduplicated across differing dotted paths or subtest discriminators.
    Exact duplicates -- the same dotted identity reported twice -- are kept
    once and counted in ``duplicate_identity_lines`` so a genuinely repeated
    line is visible rather than either hidden or double-counted.
    """

    failures: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates = 0
    for match in _IDENTITY.finditer(output):
        dotted = match.group("dotted").strip()
        subtest = (match.group("subtest") or "").strip()
        method_name = match.group("method")
        if method_name in _FIXTURES:
            # ``ERROR: setUpClass (module.Class)``: the fixture failed, so every method of the class
            # went unrun. Its identity names the fixture; the parenthesised part is a class, not a test.
            identity = skip_identity(method_name, dotted, subtest)
            parts = dotted.split(".")
            failures_row_module = ".".join(parts[:-1]) if method_name.endswith("Class") else dotted
            failures_row_class = parts[-1] if method_name.endswith("Class") else ""
        else:
            identity = f"{dotted} {subtest}".strip() if subtest else dotted
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        parts = dotted.split(".")
        row = {
            "kind": match.group("kind"),
            "identity": identity,
            "dotted": dotted,
            "module": ".".join(parts[:-2]) if len(parts) >= 3 else (parts[0] if parts else ""),
            "class": parts[-2] if len(parts) >= 2 else "",
            "method": parts[-1] if parts else method_name,
            "subtest": subtest or None,
            "is_import_error": _IMPORT_ERROR_MARKER in dotted,
        }
        if method_name in _FIXTURES:
            row.update(module=failures_row_module, **{"class": failures_row_class}, method=None,
                       fixture=method_name)
        failures.append(row)

    # A line with no parenthesised identity still has to be recorded; dropping
    # it would understate the failure set.
    for match in _IDENTITY_BARE.finditer(output):
        identity = match.group("method").strip()
        if identity in seen:
            continue
        seen.add(identity)
        failures.append(
            {
                "kind": match.group("kind"),
                "identity": identity,
                "dotted": identity,
                "module": "",
                "class": "",
                "method": identity,
                "subtest": None,
                "is_import_error": False,
                "identity_form": "unqualified",
            }
        )

    skips: list[dict[str, Any]] = []
    for match in _SKIP.finditer(output):
        method = match.group("method")
        dotted = match.group("dotted").strip()
        subtest = (match.group("subtest") or "").strip()
        scope = ("FIXTURE" if method in _FIXTURES else "SUBTEST" if match.group("indent") or subtest
                 else "METHOD")
        skips.append(
            {
                "identity": skip_identity(method, dotted, subtest),
                "method": method,
                "reason": _unquote_reason(match.group("reason")),
                "scope": scope,
                "subtest": subtest or None,
                "docstring_line_between": match.group("doc") is not None,
            }
        )
    expected_failures = [m.group("dotted") for m in _EXPECTED_FAILURE.finditer(output)]
    unexpected_successes = [m.group("dotted") for m in _UNEXPECTED_SUCCESS.finditer(output)]

    counts = _COUNT_LINE.search(output)
    summary = _RESULT_LINE.search(output)
    summary_line = summary.group(0).strip() if summary else None
    declared = _summary_counts(summary_line)

    tests_run = int(counts.group(1)) if counts else None
    skipped_count = len(skips)
    # Only a whole-method skip removes a counted test from execution. A fixture skip's methods were never
    # counted in "Ran N" and a skipped subtest's parent test did run, so neither is subtracted.
    method_skips = sum(1 for row in skips if row["scope"] == "METHOD")
    executed = None if tests_run is None else tests_run - method_skips

    return {
        "tests_run": tests_run,
        "seconds": float(counts.group(2)) if counts else None,
        "failed_or_errored": failures,
        "failed_or_errored_identities": [row["identity"] for row in failures],
        "failed_or_errored_count": len(failures),
        "import_error_identities": [
            row["identity"] for row in failures if row.get("is_import_error")
        ],
        "subtest_identities": [row["identity"] for row in failures if row.get("subtest")],
        "fixture_failure_identities": [row["identity"] for row in failures if row.get("fixture")],
        "duplicate_identity_lines": duplicates,
        "skipped": skips,
        "skipped_count": skipped_count,
        "skip_scope_counts": {scope: sum(1 for row in skips if row["scope"] == scope)
                              for scope in ("METHOD", "SUBTEST", "FIXTURE")},
        "expected_failure_identities": expected_failures,
        "unexpected_success_identities": unexpected_successes,
        "executed_test_count": executed,
        "summary_line": summary_line,
        "summary_declared_counts": declared,
        "ran_any_test": bool(tests_run),
        "executed_any_unskipped_test": bool(executed) if executed is not None else None,
    }


def reconcile(parsed: Mapping[str, Any]) -> dict[str, Any]:
    """Compare the parsed identities against unittest's own summary counts.

    A parser that silently merges identities disagrees with the summary line
    it was printed next to. Making that disagreement an explicit field is what
    turns "the regex was wrong" from an invisible fact into a reported one.
    """

    declared = dict(parsed.get("summary_declared_counts") or {})
    declared_failures = declared.get("failures", 0) + declared.get("errors", 0)
    observed_failures = int(parsed.get("failed_or_errored_count") or 0)
    declared_skips = declared.get("skipped")
    observed_skips = int(parsed.get("skipped_count") or 0)
    problems: list[str] = []
    if parsed.get("summary_line") and declared_failures != observed_failures:
        problems.append(
            f"unittest summary declares {declared_failures} failure/error(s) "
            f"but {observed_failures} distinct identit(y/ies) were parsed"
        )
    if declared_skips is not None and declared_skips != observed_skips:
        problems.append(
            f"unittest summary declares {declared_skips} skip(s) but "
            f"{observed_skips} were parsed"
        )
    for label, key, field in (("expected failure", "expected_failures", "expected_failure_identities"),
                              ("unexpected success", "unexpected_successes", "unexpected_success_identities")):
        declared_value = declared.get(key)
        if declared_value is not None and declared_value != len(parsed.get(field) or []):
            problems.append(f"unittest summary declares {declared_value} {label}(s) but "
                            f"{len(parsed.get(field) or [])} were parsed")
    return {
        "declared_failures_or_errors": declared_failures,
        "parsed_failures_or_errors": observed_failures,
        "declared_skips": declared_skips,
        "parsed_skips": observed_skips,
        "consistent": not problems,
        "problems": problems,
    }


#: Record kinds from :mod:`aggie_analytics.validation.unittest_census` that unittest counts as a failure,
#: an error or a skip, and the canonical identity each shares with the verbose-text parse.
_CENSUS_FAILURE_KINDS = {"FAIL", "ERROR", "SUBTEST_FAIL", "SUBTEST_ERROR"}
_CENSUS_SKIP_KINDS = {"SKIP", "SUBTEST_SKIP"}


def _census_identity(row: Mapping[str, Any]) -> str:
    base = str(row["id"])
    subtest = row.get("subtest")
    return f"{base} {subtest}".strip() if subtest else base


def reconcile_census(parsed: Mapping[str, Any], census_summary: Mapping[str, Any],
                     records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Reconcile three independent accounts of one run by exact identity (MF37A02-05).

    1. unittest's own summary line and ``Ran N`` (the framework's counts);
    2. the verbose text, parsed by :func:`parse_unittest`;
    3. the per-outcome JSON records the census result class wrote while the run happened.

    Every failure/error/skip identity must appear in both the text parse and the records, and each count
    must equal the framework's. A disagreement is a defect in one of the accounts and is reported by
    identity, never averaged away.
    """

    framework = dict(census_summary.get("framework_counts") or {})
    census_failures = [_census_identity(r) for r in records if r.get("kind") in _CENSUS_FAILURE_KINDS]
    census_skips = [_census_identity(r) for r in records if r.get("kind") in _CENSUS_SKIP_KINDS]
    census_expected = [str(r["id"]) for r in records if r.get("kind") == "EXPECTED_FAILURE"]
    census_unexpected = [str(r["id"]) for r in records if r.get("kind") == "UNEXPECTED_SUCCESS"]
    text_failures = list(parsed.get("failed_or_errored_identities") or [])
    text_skips = [row["identity"] for row in parsed.get("skipped") or []]
    problems: list[str] = []

    def compare(label: str, text: list[str], census: list[str], framework_count: int | None) -> dict[str, Any]:
        missing_from_text = sorted(set(census) - set(text))
        missing_from_census = sorted(set(text) - set(census))
        if missing_from_text:
            problems.append(f"{label}: {len(missing_from_text)} identit(y/ies) recorded but not parsed from text: "
                            f"{missing_from_text[:5]}")
        if missing_from_census:
            problems.append(f"{label}: {len(missing_from_census)} identit(y/ies) parsed from text but not "
                            f"recorded: {missing_from_census[:5]}")
        if framework_count is not None and len(census) != framework_count:
            problems.append(f"{label}: unittest counted {framework_count} but {len(census)} were recorded")
        if len(census) != len(set(census)):
            problems.append(f"{label}: duplicate recorded identities")
        return {"text": len(text), "records": len(census), "framework": framework_count,
                "missing_from_text": missing_from_text, "missing_from_records": missing_from_census}

    failures = compare("failures/errors", text_failures, census_failures,
                       (framework.get("failures") or 0) + (framework.get("errors") or 0)
                       if framework else None)
    skips = compare("skips", text_skips, census_skips, framework.get("skipped"))
    expected = compare("expected failures", list(parsed.get("expected_failure_identities") or []),
                       census_expected, framework.get("expected_failures"))
    unexpected = compare("unexpected successes", list(parsed.get("unexpected_success_identities") or []),
                         census_unexpected, framework.get("unexpected_successes"))
    ran_records = sum(1 for r in records if r.get("kind") in {"PASS", "FAIL", "ERROR", "SKIP", "EXPECTED_FAILURE",
                                                               "UNEXPECTED_SUCCESS"}
                      and not r.get("fixture"))
    tests_run = census_summary.get("tests_run")
    if parsed.get("tests_run") is not None and tests_run is not None and parsed["tests_run"] != tests_run:
        problems.append(f"text says Ran {parsed['tests_run']} but the runner counted {tests_run}")
    # A test that ran reports exactly one terminal outcome; a subtest failure inside a passing parent adds a
    # SUBTEST_* row and no PASS row, so terminal rows can be fewer than tests_run only by those parents.
    subtest_parents = {r["id"] for r in records if str(r.get("kind", "")).startswith("SUBTEST_")}
    terminal_ids = {r["id"] for r in records if r.get("kind") in {"PASS", "FAIL", "ERROR", "SKIP",
                                                                   "EXPECTED_FAILURE", "UNEXPECTED_SUCCESS"}
                    and not r.get("fixture")}
    unaccounted = (tests_run or 0) - len(terminal_ids | subtest_parents)
    if tests_run is not None and unaccounted != 0:
        problems.append(f"{unaccounted} test(s) in Ran {tests_run} have no recorded outcome")
    discovered = list(census_summary.get("discovered") or [])
    ran_ids = terminal_ids | subtest_parents
    never_ran = sorted(set(discovered) - ran_ids)
    fixture_rows = [r for r in records if r.get("fixture")]
    return {
        "consistent": not problems,
        "problems": problems,
        "failures_and_errors": failures,
        "skips": skips,
        "expected_failures": expected,
        "unexpected_successes": unexpected,
        "tests_run": tests_run,
        "terminal_outcome_rows": ran_records,
        "discovered_count": len(discovered),
        "discovered_but_never_ran": never_ran,
        "discovered_but_never_ran_count": len(never_ran),
        "fixture_outcomes": [{"id": r["id"], "kind": r["kind"], "reason": r.get("reason")} for r in fixture_rows],
        "import_failures": [r["id"] for r in records if r.get("is_import_error")],
        "whole_method_skips": [_census_identity(r) for r in records if r.get("kind") == "SKIP" and not r.get("fixture")],
        "subtest_skips": [_census_identity(r) for r in records if r.get("kind") == "SUBTEST_SKIP"],
        "subtest_failures": [_census_identity(r) for r in records if r.get("kind") in {"SUBTEST_FAIL", "SUBTEST_ERROR"}],
        "origin_audit_holds": (census_summary.get("origin_audit") or {}).get("holds"),
    }


@dataclass(frozen=True)
class LaneOutcome:
    """The state of one lane plus the reason it holds."""

    state: str
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"result": self.state, "state_reason": self.reason}


def classify(
    *,
    kind: str,
    exit_code: int | None,
    parsed: Mapping[str, Any] | None,
) -> LaneOutcome:
    """Decide a lane's state from what actually happened.

    ``kind='TEST'`` requires at least one executed, unskipped case. Exit 0
    from an entirely skipped suite is reported as :data:`UNSATISFIED`, which
    is neither a pass nor an inherited red: the command ran, and the
    acceptance it was supposed to supply was not supplied.
    """

    if exit_code is None:
        return LaneOutcome(BLOCKED, "the command did not complete")
    if exit_code != 0:
        return LaneOutcome(FAIL, f"exit code {exit_code}")
    if kind.upper() != "TEST":
        return LaneOutcome(PASS, "check exited zero")
    if parsed is None:
        return LaneOutcome(
            UNSATISFIED,
            "a TEST lane exited zero but produced no parseable unittest result",
        )
    if not parsed.get("tests_run"):
        return LaneOutcome(
            UNSATISFIED,
            "a TEST lane exited zero having discovered no test at all",
        )
    executed = parsed.get("executed_test_count")
    if executed is not None and executed <= 0:
        return LaneOutcome(
            UNSATISFIED,
            f"a TEST lane exited zero with all {parsed.get('tests_run')} "
            f"discovered test(s) skipped; no assertion was executed",
        )
    reconciliation = reconcile(parsed)
    if not reconciliation["consistent"]:
        return LaneOutcome(
            FAIL,
            "; ".join(reconciliation["problems"]),
        )
    return LaneOutcome(PASS, f"{executed} executed test(s), exit code 0")


def run_lane(
    lane: str,
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str | None] | None = None,
    timeout: int = 5400,
    log_dir: Path,
    parse: bool = True,
    kind: str = "TEST",
    note: str = "",
    census: tuple[Path, Path] | None = None,
) -> dict[str, Any]:
    """Run one lane and record what it did, including its raw log.

    The full combined stdout/stderr is always written to ``log_dir`` before
    any classification, so the receipt can never be the only surviving account
    of the run.

    ``census`` is ``(records.jsonl, summary.json)`` when the command runs under
    :mod:`aggie_analytics.validation.unittest_census`. Its per-outcome records
    are then reconciled against the text parse and unittest's own counts by
    exact identity, and a disagreement -- or an import from a checkout other
    than the selected one -- fails the lane.
    """

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{lane}.log"

    environment = dict(os.environ)
    if env:
        for key, value in env.items():
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value

    started = time.time()
    reason: str | None = None
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            cwd=str(cwd),
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = (completed.stdout or "") + "\n" + (completed.stderr or "")
        exit_code: int | None = completed.returncode
    except subprocess.TimeoutExpired as error:
        raw = error.output
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        output = raw or ""
        exit_code = None
        reason = f"timed out after {timeout}s"
    except OSError as error:
        output = f"{type(error).__name__}: {error}\n"
        exit_code = None
        reason = f"the command could not be started: {error}"

    _bas_atomic.write_text(log_path, output, encoding="utf-8")

    parsed = parse_unittest(output) if parse else None
    outcome = classify(kind=kind, exit_code=exit_code, parsed=parsed)
    census_report: dict[str, Any] | None = None
    if census is not None:
        records_path, summary_path = (Path(census[0]), Path(census[1]))
        if records_path.is_file() and summary_path.is_file() and parsed is not None:
            import json

            census_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            census_records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()
                              if line.strip()]
            census_report = reconcile_census(parsed, census_summary, census_records)
            census_report["origin_audit"] = census_summary.get("origin_audit")
            census_report["summary_path"] = str(summary_path)
            census_report["records_path"] = str(records_path)
            if outcome.state in (PASS, UNSATISFIED) and not census_report["consistent"]:
                outcome = LaneOutcome(FAIL, "; ".join(census_report["problems"][:3]))
            if census_report["origin_audit_holds"] is False:
                outcome = LaneOutcome(FAIL, "import origin violation: " + "; ".join(
                    ((census_summary.get("origin_audit") or {}).get("problems") or [])[:3]))
        else:
            census_report = {"consistent": False, "problems": ["the census records or summary were not written"]}
            if outcome.state == PASS:
                outcome = LaneOutcome(FAIL, "the unittest census produced no records to reconcile")
    if reason:
        outcome = LaneOutcome(BLOCKED, reason)

    record: dict[str, Any] = {
        "lane": lane,
        "kind": kind,
        "result": outcome.state,
        "state_reason": outcome.reason,
        "satisfies_acceptance": outcome.state == PASS,
        "command": [str(item) for item in command],
        "command_line": " ".join(str(item) for item in command),
        "cwd": str(cwd),
        "exit_code": exit_code,
        "elapsed_seconds": round(time.time() - started, 3),
        "log_path": str(log_path),
        "log_bytes": log_path.stat().st_size,
        "output_tail": output[-4000:],
        "note": note,
    }
    if env:
        record["env_overrides"] = {k: ("<unset>" if v is None else v) for k, v in env.items()}
    if parsed is not None:
        record["unittest"] = parsed
        record["unittest_reconciliation"] = reconcile(parsed)
    if census_report is not None:
        record["census_reconciliation"] = census_report
    return record
