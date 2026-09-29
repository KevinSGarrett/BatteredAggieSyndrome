"""Cycle #37 — Attempt #11 — R37A11-05-A: a lane may keep its original execution only under a current, complete dependency check.

The contract lets a worker lane "execute or provide a current complete unchanged-dependency CHECK". The Attempt 11 output
wrapper had no adapter for it, so any commit after the lanes ran made every receipt stale (``at_head`` compares heads).
``tools/cycle37/attempt11_reuse.py`` is the bounded adapter; these cases prove it on tiny owned repositories and receipts:

* the runner delta is proved bookkeeping-only on the syntax tree -- the declared statements are the only difference, each
  present exactly once -- and an extra statement, a changed unrelated function, an undeclared new function, a repeated or
  missing declared statement, a changed parser description and a new reference to the changed code each refuse;
* the check passes a lane whose original receipt, index row, logs, sealed submission, heads, tracked delta, commands, bound
  tools, interpreter, recorded (path, digest) pairs, environment and data all hold, and refuses each of a forged
  receipt, a changed lane log or command log, a sealed submission that disagrees, an undeclared changed tracked path, a
  head that is not an ancestor, a retained command that executes a changed tool, a test run when a test was added, a
  changed bound tool digest, another interpreter, a broken recorded pair, and a changed wheel, installed file or database;
* a command that reads a changed tool is executed again inside the check when it is on the allowlist and refuses when it
  fails; nothing is accepted on a stored record alone (``verified_lanes`` recomputes it).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "cycle37"))

import attempt11_reuse as reuse  # noqa: E402

A7_PATH, A11_PATH = "tools/cycle37/attempt07_lanes.py", "tools/cycle37/attempt11_lanes.py"

A7_BEFORE = '''"""synthetic attempt 7 runner"""


def other(run):
    return run


def lane_final_packet(run):
    """verify"""
    held = {"only_this_lane_open": [v.get("operation") for v in open_now.values()]
            == [f"LANE FINAL_PACKET {run.stamp}" + (" (rehearsal)" if run.rehearsal else "")]}
    return held


LANE_FUNCTIONS = {"START_CONTEXT": other, "FINAL_PACKET": lane_final_packet}
'''
A7_AFTER = '''"""synthetic attempt 7 runner"""


def other(run):
    return run


def _owned_final_reservation(run, open_now):
    return bool(open_now)


def lane_final_packet(run):
    """verify"""
    held = {"only_this_lane_open": _owned_final_reservation(run, open_now)}
    return held


LANE_FUNCTIONS = {"START_CONTEXT": other, "FINAL_PACKET": lane_final_packet}
'''
A11_BEFORE = '''"""synthetic attempt 11 runner"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane")
    run = LaneRun()
    run.rehearsal = args.rehearsal
    return 0


LANE_FUNCTIONS = {"FINAL_PACKET": a7.lane_final_packet, "START_CONTEXT": lane_start_context}
'''
A11_AFTER = '''"""synthetic attempt 11 runner

more text after the first line"""


def _reservation_for_check(args, final_lane, reservation, paths):
    return reservation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane")
    run = LaneRun()
    run.rehearsal = args.rehearsal
    run.storage_reservation = _reservation_for_check(args, final_lane, reservation, paths)
    return 0


LANE_FUNCTIONS = {"FINAL_PACKET": a7.lane_final_packet, "START_CONTEXT": lane_start_context}
'''
SPEC = {
    A7_PATH: {"added": ("_owned_final_reservation",),
              "modified": {"lane_final_packet": [
                  ("expr_replaced",
                   '[v.get("operation") for v in open_now.values()] == [f"LANE FINAL_PACKET {run.stamp}" + '
                   '(" (rehearsal)" if run.rehearsal else "")]', "_owned_final_reservation(run, open_now)")]}},
    A11_PATH: {"added": ("_reservation_for_check",),
               "modified": {"main": [
                   ("stmt_added", "run.storage_reservation = _reservation_for_check(args, final_lane, reservation, paths)")]}},
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RunnerDeltaProofTests(unittest.TestCase):
    """The syntax-tree proof, on synthetic runner modules."""

    def delta(self, before: str, after: str, path: str) -> dict[str, Any]:
        return reuse.module_delta(before, after, SPEC[path])

    def test_the_declared_statements_are_the_only_difference(self) -> None:
        for before, after, path in ((A7_BEFORE, A7_AFTER, A7_PATH), (A11_BEFORE, A11_AFTER, A11_PATH)):
            with self.subTest(path=path):
                proof = self.delta(before, after, path)
                self.assertTrue(proof["holds"], proof["problems"])

    def test_an_extra_statement_in_the_changed_function_refuses(self) -> None:
        tampered = A11_AFTER.replace("    return 0\n\n\nLANE", "    run.extra = 1\n    return 0\n\n\nLANE")
        proof = self.delta(A11_BEFORE, tampered, A11_PATH)
        self.assertFalse(proof["holds"])
        self.assertTrue([p for p in proof["problems"] if "beyond the declared statements" in p])

    def test_a_changed_unrelated_function_refuses(self) -> None:
        proof = self.delta(A7_BEFORE, A7_AFTER.replace("    return run\n", "    return None\n"), A7_PATH)
        self.assertFalse(proof["holds"])
        self.assertTrue([p for p in proof["problems"] if "other" in p and "not declared" in p])

    def test_an_undeclared_new_function_refuses(self) -> None:
        proof = self.delta(A11_BEFORE, A11_AFTER + "\n\ndef sneaky():\n    return 1\n", A11_PATH)
        self.assertFalse(proof["holds"])
        self.assertTrue([p for p in proof["problems"] if "top-level structure" in p])

    def test_a_missing_declared_statement_and_a_repeated_one_refuse(self) -> None:
        missing = self.delta(A11_BEFORE, A11_AFTER.replace(
            "    run.storage_reservation = _reservation_for_check(args, final_lane, reservation, paths)\n", ""), A11_PATH)
        self.assertFalse(missing["holds"])
        repeated = self.delta(A11_BEFORE, A11_AFTER.replace(
            "    return 0\n\n\nLANE", "    run.storage_reservation = _reservation_for_check(args, final_lane, reservation, paths)\n"
                                     "    return 0\n\n\nLANE"), A11_PATH)
        self.assertFalse(repeated["holds"])
        self.assertTrue([p for p in repeated["problems"] if "present 2 times" in p])

    def test_a_declared_replacement_that_is_not_made_refuses(self) -> None:
        proof = self.delta(A7_BEFORE, A7_AFTER.replace("_owned_final_reservation(run, open_now)}", "True}"), A7_PATH)
        self.assertFalse(proof["holds"])

    def test_the_parser_description_line_is_compared_and_the_rest_of_a_docstring_is_not(self) -> None:
        self.assertTrue(self.delta(A11_BEFORE, A11_AFTER, A11_PATH)["holds"])  # the docstring body grew: not code
        changed = A11_AFTER.replace('"""synthetic attempt 11 runner\n', '"""a different first line\n')
        proof = self.delta(A11_BEFORE, changed, A11_PATH)
        self.assertFalse(proof["holds"])
        self.assertTrue([p for p in proof["problems"] if "first line" in p])

    def test_a_changed_module_constant_refuses(self) -> None:
        proof = self.delta(A7_BEFORE, A7_AFTER.replace('"START_CONTEXT": other', '"START_CONTEXT": lane_final_packet'), A7_PATH)
        self.assertFalse(proof["holds"])

    # ---- who can reach the changed code
    def references(self, **sources: str) -> list[str]:
        return reuse.reference_problems({f"tools/cycle37/{name}.py": text for name, text in sources.items()})

    def test_the_changed_code_is_reachable_only_where_the_delta_says(self) -> None:
        wrapper = "def lane_final_packet(run):\n    a7.lane_final_packet(run)\n\nT = {'FINAL_PACKET': lane_final_packet}\n"
        self.assertEqual(self.references(attempt07_lanes=A7_AFTER, attempt11_lanes=A11_AFTER, attempt08_lanes=wrapper), [])

    def test_a_new_reference_to_the_changed_code_from_another_lane_refuses(self) -> None:
        for extra in ("def lane_other(run):\n    a7.lane_final_packet(run)\n",
                      "def lane_other(run):\n    return _owned_final_reservation(run, {})\n",
                      "def lane_other(run):\n    return _reservation_for_check(None, False, None, {})\n",
                      "def lane_other(run):\n    return run.storage_reservation\n",
                      "TABLE = {'START_CONTEXT': a7.lane_final_packet}\n"):
            with self.subTest(extra=extra):
                problems = self.references(attempt07_lanes=A7_AFTER, attempt11_lanes=A11_AFTER + "\n" + extra)
                self.assertTrue(problems, extra)

    def test_the_kept_reservation_must_be_stored_once_and_the_helper_called_once(self) -> None:
        twice = A11_AFTER.replace("    return 0\n\n\nLANE", "    run.storage_reservation = 1\n    return 0\n\n\nLANE")
        self.assertTrue(self.references(attempt07_lanes=A7_AFTER, attempt11_lanes=twice))
        self.assertTrue(self.references(attempt07_lanes=A7_AFTER, attempt11_lanes=A11_BEFORE))


class CommandEntryTests(unittest.TestCase):
    """What a command runs: the repository scripts it names, and whether it invokes a test runner."""

    def entries(self, *argv: str) -> tuple[list[str], bool]:
        env = mock.Mock()
        env.repo = Path(r"C:\repo")
        return reuse.command_entries(env, list(argv), r"C:\repo")

    def test_a_command_that_invokes_a_test_runner_is_a_test_run(self) -> None:
        for argv in (("python", "-m", "unittest", "discover"), ("python", "-B", "-m", "pytest", "tests"),
                     ("python", "-m", "aggie_analytics.validation.unittest_census", "--selected-root", "x"),
                     (r"C:\venv\Scripts\pytest.exe", "tests"), ("pytest", "-q")):
            with self.subTest(argv=argv):
                self.assertTrue(self.entries(*argv)[1])

    def test_a_module_name_handed_to_another_program_is_not_a_test_run(self) -> None:
        argv = ("python", "-B", "-c", "import importlib", "aggie_analytics.validation.lane_harness",
                "aggie_analytics.validation.unittest_census", "aggie_analytics.cycle33.query")
        self.assertFalse(self.entries(*argv)[1])
        self.assertFalse(self.entries("git", "log", "unittest")[1])

    def test_scripts_under_the_repository_are_found_relative_to_the_cwd(self) -> None:
        scripts, tests = self.entries("python", "-B", "tools/cycle37/attempt11_platform.py", "ledger")
        self.assertEqual((scripts, tests), (["tools/cycle37/attempt11_platform.py"], False))
        self.assertEqual(self.entries("python", r"C:\elsewhere\probe.py")[0], [])


class InterpreterIdentityTests(unittest.TestCase):
    """The recorded identity was ``pip freeze``; inside a guarded child pip is not reproducible (a PYTHONPATH naming the
    worktree adds the source tree's own distribution, and pip's blocked ``hg`` probe changes the editable line), so the
    identity is read from metadata in this process and compared by meaning."""

    RECORDED = {"executable": "C:\\py\\python.exe", "sha256": "aa", "version": "3.12.10", "implementation": "CPython",
                "base_prefix": "C:\\base",
                "distributions": ["-e git+https://example/x.git@abc#egg=aggie_analytics_engine&subdirectory=..", "duckdb==1.5.5",
                                  "mypy_extensions==1.1.0", "numpy==2.2.6", "pip==25.0.1"]}

    def current(self, **changes: Any) -> dict[str, Any]:
        document = {**self.RECORDED, "distributions": ["aggie-analytics-engine==0.25.0.dev25", "duckdb==1.5.5",
                                                       "mypy-extensions==1.1.0", "numpy==2.2.6", "pip==25.0.1"]}
        document.update(changes)
        return document

    def test_a_freeze_and_a_metadata_reading_of_the_same_interpreter_match(self) -> None:
        same, detail = reuse.interpreters_match(self.RECORDED, self.current())
        self.assertTrue(same, detail)
        self.assertEqual(detail["recorded_editable_names"], ["aggie-analytics-engine"])

    def test_each_difference_of_identity_is_refused(self) -> None:
        for name, changes in (("version of a package", {"distributions": ["aggie-analytics-engine==1", "duckdb==1.5.6",
                                                                          "mypy-extensions==1.1.0", "numpy==2.2.6", "pip==25.0.1"]}),
                              ("an extra package", {"distributions": ["aggie-analytics-engine==1", "duckdb==1.5.5", "evil==1",
                                                                      "mypy-extensions==1.1.0", "numpy==2.2.6", "pip==25.0.1"]}),
                              ("a missing package", {"distributions": ["duckdb==1.5.5", "mypy-extensions==1.1.0", "pip==25.0.1"]}),
                              ("another executable", {"executable": "C:\\other\\python.exe"}),
                              ("another digest", {"sha256": "bb"}), ("another version", {"version": "3.13.0"}),
                              ("another prefix", {"base_prefix": "C:\\elsewhere"})):
            with self.subTest(name):
                self.assertFalse(reuse.interpreters_match(self.RECORDED, self.current(**changes))[0])

    def test_an_empty_recorded_identity_never_matches(self) -> None:
        self.assertFalse(reuse.interpreters_match(None, self.current())[0])

    def test_the_identity_read_here_ignores_a_source_path_named_by_pythonpath(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "zzfake_package-9.9.dist-info"
            folder.mkdir()
            (folder / "METADATA").write_text("Metadata-Version: 2.1\nName: zzfake-package\nVersion: 9.9\n", encoding="utf-8")
            with mock.patch.object(sys, "path", [tmp, *sys.path]):
                with mock.patch.dict(os.environ, {"PYTHONPATH": tmp}):
                    without = reuse.interpreter_identity(Path(sys.executable))
                with mock.patch.dict(os.environ):
                    os.environ.pop("PYTHONPATH", None)
                    control = reuse.interpreter_identity(Path(sys.executable))
        self.assertNotIn("zzfake-package==9.9", without["distributions"])
        self.assertIn("zzfake-package==9.9", control["distributions"])  # the fixture is visible when PYTHONPATH does not hide it
        self.assertEqual(without["executable"], sys.executable)

    def test_the_identity_read_here_needs_no_subprocess(self) -> None:
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("a subprocess was started")):
            identity = reuse.interpreter_identity(Path(sys.executable))
        self.assertTrue(identity["distributions"])


class RecordedPairTests(unittest.TestCase):
    def pairs(self, node: Any) -> list[tuple[str, str]]:
        return [(row["path"], row["sha256"]) for row in reuse.recorded_pairs(node)]

    def test_only_unambiguous_pairs_are_taken(self) -> None:
        digest = "a" * 64
        node = {"a": {"path": r"C:\x\a.txt", "sha256": digest},
                "b": {"log_path": r"C:\x\b.log", "log_sha256": digest},
                "c": {"successor": r"C:\x\c.sqlite", "successor_sha256": digest},
                "d": {"guard": r"C:\x\d.py", "guard_sha256": digest, "receipt": r"C:\x\r.json"},
                "e": {"summary": r"C:\x\s.json", "stdout_sha256": digest},          # a stream's digest, not the summary's
                "f": {"path": "relative.txt", "sha256": digest},                    # not an absolute path
                "g": {"path": r"C:\x\g.txt", "sha256": "not-hex"}}
        self.assertEqual(sorted(self.pairs(node)), sorted([(r"C:\x\a.txt", digest), (r"C:\x\b.log", digest),
                                                          (r"C:\x\c.sqlite", digest), (r"C:\x\d.py", digest)]))

    def test_pairs_inside_lists_are_found(self) -> None:
        digest = "b" * 64
        self.assertEqual(self.pairs({"commands": [{"log_path": r"D:\l.log", "log_sha256": digest}]}),
                         [(r"D:\l.log", digest)])


# ------------------------------------------------------------------ the check, end to end on a tiny repository


class CheckFixture(unittest.TestCase):
    LANE = "LANE_A"

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.out_root = self.base / "attempt"
        self.git_env = {**os.environ, "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                        "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                        "GIT_CEILING_DIRECTORIES": str(self.base)}
        self._git("init", "-q")
        self.put("src/aggie_analytics/__init__.py", "VERSION = 1\n")
        self.put("tests/test_existing.py", "import unittest\n")
        self.put("tools/cycle37/attempt03_platform.py", "print('platform')\n")
        self.put("tools/cycle37/attempt11_platform.py", "import attempt03_platform\n")
        self.put("tools/cycle37/attempt11_outputs.py", "import sys\nsys.exit(0)\n")
        self.put(A7_PATH, A7_BEFORE)
        self.put(A11_PATH, A11_BEFORE)
        self.put("provenance/CURRENT_TREE.txt", "tree 0\n")
        self.h0 = self.commit("H0")
        self.contract = self.base / "contract.json"
        self.contract.write_text('{"contract": true}\n', encoding="utf-8")
        self.contract_sha = sha(self.contract.read_bytes())
        self.patches = [mock.patch.object(reuse, "RUNNER_DELTA_SPEC", SPEC),
                        mock.patch.dict(reuse.DELTA_CLASSES, {
                            A7_PATH: (reuse.RUNNER, "x"), A11_PATH: (reuse.RUNNER, "x"),
                            "tools/cycle37/attempt11_outputs.py": (reuse.OUTPUT_TOOL, "x"),
                            "tests/test_new.py": (reuse.NEW_TEST, "x"),
                            "provenance/CURRENT_TREE.txt": (reuse.PROVENANCE, "x")}, clear=True)]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    # ---- repository helpers
    def _git(self, *args: str) -> str:
        done = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.safecrlf=false", "-C", str(self.repo), *args],
                              capture_output=True, text=True, env=self.git_env, check=True)
        return done.stdout.strip()

    def put(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def commit(self, message: str) -> str:
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message)
        return self._git("rev-parse", "HEAD")

    def blob(self, rev: str, path: str) -> bytes:
        return subprocess.run(["git", "-C", str(self.repo), "cat-file", "blob", f"{rev}:{path}"], capture_output=True,
                              check=True, env=self.git_env).stdout

    def advance(self, *, runner: bool = True, extra: dict[str, str] | None = None) -> str:
        """The current head: the declared runner delta, the output tool rewritten, provenance regenerated."""

        if runner:
            self.put(A7_PATH, A7_AFTER)
            self.put(A11_PATH, A11_AFTER)
        self.put("tools/cycle37/attempt11_outputs.py", "import sys\nsys.exit(0)\n# rewritten\n")
        self.put("provenance/CURRENT_TREE.txt", "tree 1\n")
        for rel, text in (extra or {}).items():
            self.put(rel, text)
        return self.commit("H1")

    # ---- the attempt root and the original execution of one lane
    def record_lane(self, lane: str, *, commands: list[dict[str, Any]] | None = None, result: str = "PASS",
                    details: dict[str, Any] | None = None, tree: str | None = None) -> dict[str, Any]:
        folder = self.out_root / "lanes" / lane / "20260929T000000000000Z"
        (folder / "logs").mkdir(parents=True)
        lane_log = folder / "lane.log"
        lane_log.write_text("the lane's console\n", encoding="utf-8")
        recorded = []
        for spec in commands or [{"name": "fixture_command", "argv": ["python", "-B", "tools/cycle37/attempt11_platform.py"]}]:
            log = folder / "logs" / f"{lane}__{spec['name']}.log"
            log.write_text(f"output of {spec['name']}\n", encoding="utf-8")
            recorded.append({"lane": f"{lane}__{spec['name']}", "command": spec["argv"], "cwd": str(self.repo),
                             "log_path": str(log), "log_sha256": sha(log.read_bytes()), "exit_code": 0})
        binding = {"head": self.h0, "tree": tree or self._git("rev-parse", f"{self.h0}^{{tree}}"),
                   "source_digest": "d0" * 32, "clean": True, "dirty_entries": [], "commits_after_base": "1",
                   "runner_sha256": sha(self.blob(self.h0, A11_PATH)),
                   "rebound_attempt7_runner_sha256": sha(self.blob(self.h0, A7_PATH)),
                   "storage_tool_sha256": "e1" * 32, "branch": "b", "base": "c" * 40}
        self.binding = binding
        self.interpreter = {"executable": sys.executable, "version": "3.12", "sha256": "f2" * 32, "distributions": ["x==1"]}
        receipt = {"lane": lane, "run": "20260929T000000000000Z", "result": result, "rehearsal": False,
                   "contract": {"sha256": self.contract_sha}, "source_binding": binding,
                   "source_binding_after": dict(binding), "interpreter": self.interpreter, "lane_log": str(lane_log),
                   "lane_log_sha256_at_receipt": sha(lane_log.read_bytes()), "commands": recorded,
                   "counts": {"tests": 3, "failures": 0}, "details": details or {}}
        path = folder / "receipt.json"
        path.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
        row = {"lane": lane, "run": receipt["run"], "result": result, "head": self.h0, "source_digest": binding["source_digest"],
               "receipt": str(path), "receipt_sha256": sha(path.read_bytes()), "at": "2026-09-29T00:00:00+00:00"}
        with (self.out_root / "lanes" / "RUNS.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        self.receipt_path, self.log_path = path, lane_log
        self.sealed = {"candidate": {"head": self.h0}, "lanes": [{"id": lane, "status": result}],
                       "evidence": [{"id": f"E-LANE-{lane}-RECEIPT", "sha256": sha(path.read_bytes())},
                                    {"id": f"E-LANE-{lane}-LOG", "sha256": sha(lane_log.read_bytes())}]}
        return receipt

    def environment(self, head: str, **overrides: Any) -> reuse.Env:
        def git_bytes(*args: str) -> bytes:
            done = subprocess.run(["git", "-c", "core.autocrlf=false", "-C", str(self.repo), *args], capture_output=True,
                                  env=self.git_env, check=False)
            if done.returncode != 0:
                raise SystemExit(done.stderr.decode("utf-8", "replace"))
            return done.stdout

        def bind() -> dict[str, Any]:
            current = {**self.binding, "head": head, "tree": self._git("rev-parse", f"{head}^{{tree}}"),
                       "source_digest": "d1" * 32, "commits_after_base": "2", "clean": True,
                       "runner_sha256": sha(self.blob(head, A11_PATH)),
                       "rebound_attempt7_runner_sha256": sha(self.blob(head, A7_PATH))}
            return current

        values: dict[str, Any] = dict(
            repo=self.repo, out_root=self.out_root, contract_sha256=self.contract_sha, head=head,
            git=lambda *a: git_bytes(*a).decode("utf-8").strip(), git_bytes=git_bytes, bind_source=bind,
            bind_interpreter=lambda: dict(self.interpreter), python=sys.executable,
            immutable_roots=(self.out_root,), scratch_env=lambda: dict(os.environ), passthrough=lambda: True,
            original_submission=self.sealed)
        values.update(overrides)
        return reuse.Env(**values)

    def check(self, lane: str | None = None, head: str | None = None, **overrides: Any) -> dict[str, Any]:
        env = self.environment(head or self.h1, **overrides)
        return reuse.check_lane(env, lane or self.LANE, reexecute=True, log_dir=self.base / "reuse-logs", stamp="T1")

    def names(self, result: dict[str, Any], holds: bool) -> list[str]:
        return [c["name"] for c in result["checks"] if c["holds"] is holds]

    def prepare(self, *, runner: bool = True, extra: dict[str, str] | None = None, **record: Any) -> None:
        """Record the original execution at the first head, then move to the current head."""

        self.record_lane(record.pop("lane", self.LANE), **record)
        self.h1 = self.advance(runner=runner, extra=extra)

    def refuses(self, cause: str, result: dict[str, Any] | None = None) -> None:
        result = result or self.check()
        self.assertFalse(result["holds"])
        self.assertIn(cause, result["refused_by"], result["refused_by"])


class PositiveCheckTests(CheckFixture):
    def setUp(self) -> None:
        super().setUp()
        self.prepare()

    def test_a_lane_whose_dependencies_all_hold_is_retained(self) -> None:
        result = self.check()
        self.assertTrue(result["holds"], result["refused_by"])
        self.assertEqual(result["original"]["head"], self.h0)
        self.assertEqual(result["current"]["head"], self.h1)
        self.assertEqual(result["original"]["result"], "PASS")
        self.assertEqual(result["original"]["counts"], {"tests": 3, "failures": 0})
        self.assertEqual(result["reexecuted"], [])
        self.assertIn("runner_delta_is_bookkeeping_only", self.names(result, True))

    def test_the_original_receipt_is_untouched_and_the_index_gains_no_row(self) -> None:
        before = (self.receipt_path.read_bytes(), (self.out_root / "lanes" / "RUNS.jsonl").read_bytes())
        self.check()
        self.assertEqual(before, (self.receipt_path.read_bytes(), (self.out_root / "lanes" / "RUNS.jsonl").read_bytes()))

    def test_a_proof_record_is_create_only_and_names_its_head_and_that_it_is_not_fresh(self) -> None:
        env = self.environment(self.h1)
        result = reuse.check_lane(env, self.LANE, reexecute=True, stamp="T1")
        path = reuse.write_proof(env, result, rehearsal=False, stamp="T1")
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(document["not_a_fresh_execution"])
        self.assertEqual(document["mode"], reuse.MODE)
        self.assertEqual(document["current"]["head"], self.h1)
        self.assertEqual(document["original"]["head"], self.h0)
        with self.assertRaises(FileExistsError):
            reuse.write_proof(env, result, rehearsal=False, stamp="T1")

    def test_verified_lanes_recomputes_and_accepts_a_proof_that_still_holds(self) -> None:
        env = self.environment(self.h1)
        reuse.write_proof(env, reuse.check_lane(env, self.LANE, reexecute=True, stamp="T1"), rehearsal=False, stamp="T1")
        accepted, refused = reuse.verified_lanes(self.environment(self.h1), [self.LANE])
        self.assertEqual(list(accepted), [self.LANE])
        self.assertEqual(refused, {})
        self.assertEqual(accepted[self.LANE]["original"]["head"], self.h0)


class RefusalTests(CheckFixture):
    """One dependency at a time: each is refused for its own cause, never by an unrelated check."""

    def setUp(self) -> None:
        super().setUp()
        self.prepare()

    def test_a_forged_receipt_is_refused(self) -> None:
        text = self.receipt_path.read_text(encoding="utf-8")
        self.receipt_path.write_text(text.replace('"tests": 3', '"tests": 4'), encoding="utf-8")
        self.refuses("original_receipt_and_logs_are_what_they_were")

    def test_a_changed_lane_log_is_refused(self) -> None:
        self.log_path.write_text("a different console\n", encoding="utf-8")
        self.refuses("original_receipt_and_logs_are_what_they_were")

    def test_a_changed_command_log_is_refused(self) -> None:
        log = next((self.out_root / "lanes" / self.LANE).rglob("*fixture_command.log"))
        log.write_text("edited after the run\n", encoding="utf-8")
        self.refuses("original_receipt_and_logs_are_what_they_were")

    def test_a_missing_command_log_is_refused(self) -> None:
        next((self.out_root / "lanes" / self.LANE).rglob("*fixture_command.log")).unlink()
        self.refuses("original_receipt_and_logs_are_what_they_were")

    def test_a_receipt_of_another_contract_is_refused(self) -> None:
        self.refuses("original_receipt_and_logs_are_what_they_were", self.check(contract_sha256="0" * 64))

    def test_a_rehearsal_receipt_is_never_retained(self) -> None:
        receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        receipt["rehearsal"] = True
        self.receipt_path.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
        rows = [json.loads(line) for line in (self.out_root / "lanes" / "RUNS.jsonl").read_text().splitlines()]
        rows[-1]["receipt_sha256"] = sha(self.receipt_path.read_bytes())
        (self.out_root / "lanes" / "RUNS.jsonl").write_text(json.dumps(rows[-1]) + "\n", encoding="utf-8")
        self.refuses("original_receipt_and_logs_are_what_they_were")

    def test_a_sealed_submission_that_disagrees_is_refused(self) -> None:
        for change in (lambda s: s["evidence"][0].update(sha256="0" * 64),
                       lambda s: s["evidence"][1].update(sha256="0" * 64),
                       lambda s: s["candidate"].update(head="9" * 40),
                       lambda s: s["lanes"][0].update(status="FAIL"),
                       lambda s: s.update(evidence=[])):
            with self.subTest():
                sealed = json.loads(json.dumps(self.sealed))
                change(sealed)
                self.refuses("sealed_original_submission_agrees", self.check(original_submission=sealed))

    def test_no_sealed_submission_is_a_refusal(self) -> None:
        self.refuses("sealed_original_submission_agrees", self.check(original_submission=None))

    def test_a_changed_bound_tool_digest_is_refused(self) -> None:
        env = self.environment(self.h1)
        original = env.bind_source
        env.bind_source = lambda: {**original(), "storage_tool_sha256": "00" * 32}
        self.refuses("bound_tool_digests_are_unchanged", reuse.check_lane(env, self.LANE, reexecute=True, stamp="T1"))

    def test_a_runner_digest_that_is_not_the_committed_file_is_refused(self) -> None:
        env = self.environment(self.h1)
        original = env.bind_source
        env.bind_source = lambda: {**original(), "runner_sha256": "11" * 32}
        self.refuses("changed_runner_digests_are_the_committed_files",
                     reuse.check_lane(env, self.LANE, reexecute=True, stamp="T1"))

    def test_a_dirty_current_subject_is_refused(self) -> None:
        env = self.environment(self.h1)
        original = env.bind_source
        env.bind_source = lambda: {**original(), "clean": False}
        self.refuses("current_subject_is_clean_and_committed", reuse.check_lane(env, self.LANE, reexecute=True, stamp="T1"))

    def test_another_interpreter_is_refused(self) -> None:
        self.refuses("interpreter_is_the_recorded_one",
                     self.check(bind_interpreter=lambda: {**self.interpreter, "version": "3.13"}))

    def test_a_reservation_helper_that_is_not_a_passthrough_is_refused(self) -> None:
        self.refuses("runner_delta_is_bookkeeping_only", self.check(passthrough=lambda: False))

    def test_the_lane_already_at_the_current_head_is_not_a_retained_one(self) -> None:
        self.refuses("original_execution_is_not_already_current", self.check(head=self.h0))

    def test_a_lane_with_no_run_is_refused(self) -> None:
        self.refuses("original_execution_exists", self.check(lane="NEVER_RAN"))

    def test_a_head_that_is_not_a_descendant_is_refused(self) -> None:
        self._git("checkout", "-q", "--orphan", "other")
        self.put("only.txt", "unrelated\n")
        orphan = self.commit("orphan with the same files and no shared history")
        self.assertFalse(self.environment(orphan).is_ancestor(self.h0, orphan))
        self.refuses("original_head_is_an_ancestor_of_the_current_head", self.check(head=orphan))


class VariantRefusalTests(CheckFixture):
    """Refusals that need their own original execution or their own current head."""

    def test_a_blocked_original_result_is_never_retained(self) -> None:
        self.prepare(result="BLOCKED")
        self.refuses("original_receipt_and_logs_are_what_they_were")

    def test_an_undeclared_changed_tracked_path_is_refused(self) -> None:
        self.prepare(extra={"src/aggie_analytics/__init__.py": "VERSION = 2\n"})
        result = self.check()
        self.refuses("every_changed_tracked_path_is_declared", result)
        self.assertEqual(result["delta"]["unclassified"], ["src/aggie_analytics/__init__.py"])

    def test_a_recorded_tree_that_is_not_the_original_heads_is_refused(self) -> None:
        self.prepare(tree="1" * 40)
        self.refuses("recorded_tree_is_the_original_heads_tree")

    def test_an_undeclared_runner_change_is_refused(self) -> None:
        self.record_lane(self.LANE)
        self.put(A7_PATH, A7_AFTER)
        self.put(A11_PATH, A11_AFTER.replace("    return 0\n\n\nLANE", "    run.extra = 1\n    return 0\n\n\nLANE"))
        self.put("provenance/CURRENT_TREE.txt", "tree 1\n")
        self.h1 = self.commit("H1 with an extra statement in main")
        self.refuses("runner_delta_is_bookkeeping_only")

    def test_a_retained_command_that_executes_a_changed_tool_is_refused_unless_it_is_allowlisted(self) -> None:
        self.prepare(commands=[{"name": "accounting", "argv": ["python", "-B", "tools/cycle37/attempt11_outputs.py", "check"]}])
        self.refuses("no_retained_command_executes_a_changed_dependency")

    def test_a_command_that_imports_a_changed_tool_indirectly_is_refused(self) -> None:
        self.put("tools/cycle37/attempt11_platform.py", "import attempt11_outputs\n")
        self.h0 = self.commit("the platform tool imports the outputs tool")
        self.prepare()
        self.refuses("no_retained_command_executes_a_changed_dependency")

    def test_a_test_run_is_refused_when_a_test_was_added(self) -> None:
        self.prepare(commands=[{"name": "suite", "argv": ["python", "-m", "unittest", "discover"]}],
                     extra={"tests/test_new.py": "import unittest\n"})
        self.refuses("no_retained_command_executes_a_changed_dependency")

    def test_an_archive_of_a_changed_path_is_refused(self) -> None:
        self.prepare(commands=[{"name": "git_archive_committed_subject",
                                "argv": ["git", "archive", "-o", "x.tar", "HEAD", "--", "provenance"]}])
        self.refuses("no_retained_command_executes_a_changed_dependency")


class RecordedDigestPairTests(CheckFixture):
    def setUp(self) -> None:
        super().setUp()
        self.artifact = self.out_root / "evidence" / "artifact.json"
        self.artifact.parent.mkdir(parents=True)
        self.artifact.write_text('{"a": 1}\n', encoding="utf-8")
        self.prepare(details={"input": {"path": str(self.artifact), "sha256": sha(self.artifact.read_bytes())}})

    def test_a_recorded_pair_that_holds_is_counted(self) -> None:
        result = self.check()
        self.assertTrue(result["holds"], result["refused_by"])
        pairs = next(c for c in result["checks"] if c["name"] == "every_recorded_path_and_digest_pair_holds")
        self.assertEqual(pairs["detail"]["verified"], 2)  # the command log and the input

    def test_a_changed_recorded_input_is_refused(self) -> None:
        self.artifact.write_text('{"a": 2}\n', encoding="utf-8")
        result = self.check()
        self.assertIn("every_recorded_path_and_digest_pair_holds", result["refused_by"])

    def test_a_missing_recorded_input_is_refused(self) -> None:
        self.artifact.unlink()
        self.assertIn("every_recorded_path_and_digest_pair_holds", self.check()["refused_by"])


class AllowlistedReexecutionTests(CheckFixture):
    LANE = "PLATFORM_CARRY"

    def setUp(self) -> None:
        super().setUp()
        self.record_lane(self.LANE, commands=[
            {"name": "platform_ledger_totals", "argv": ["python", "-B", "tools/cycle37/attempt11_platform.py", "ledger"]},
            {"name": "carryforward_accounting", "argv": ["python", "-B", "tools/cycle37/attempt11_outputs.py", "check"]}])

    def test_a_command_that_reads_a_changed_tool_is_executed_again_here_and_logged(self) -> None:
        self.h1 = self.advance()
        result = self.check()
        self.assertTrue(result["holds"], result["refused_by"])
        self.assertEqual([r["name"] for r in result["reexecuted"]], ["carryforward_accounting"])
        rerun = result["reexecuted"][0]
        self.assertEqual((rerun["exit"], rerun["head"]), (0, self.h1))
        self.assertEqual(sha(Path(rerun["log"]).read_bytes()), rerun["log_sha256"])
        dispositions = {c["command"]: c["disposition"] for c in result["commands"]}
        self.assertEqual(dispositions, {"platform_ledger_totals": "RETAINED",
                                        "carryforward_accounting": "EXECUTED_AGAIN_IN_THIS_CHECK"})

    def test_a_reexecuted_command_that_fails_refuses_the_lane(self) -> None:
        self.put("tools/cycle37/attempt11_outputs.py", "import sys\nsys.exit(3)\n")
        self.put(A7_PATH, A7_AFTER)
        self.put(A11_PATH, A11_AFTER)
        self.put("provenance/CURRENT_TREE.txt", "tree 1\n")
        self.h1 = self.commit("H1 whose output tool fails")
        result = self.check()
        self.assertIn("commands_that_read_a_changed_tool_were_executed_again_at_this_head", result["refused_by"])
        self.assertEqual(result["reexecuted"][0]["exit"], 3)

    def test_verification_needs_the_recorded_rerun_to_match_its_log(self) -> None:
        self.h1 = self.advance()
        env = self.environment(self.h1)
        result = reuse.check_lane(env, self.LANE, reexecute=True, log_dir=self.base / "reuse-logs", stamp="T1")
        reuse.write_proof(env, result, rehearsal=False, stamp="T1")
        accepted, refused = reuse.verified_lanes(self.environment(self.h1), [self.LANE])
        self.assertIn(self.LANE, accepted)
        Path(result["reexecuted"][0]["log"]).write_text("rewritten after the check\n", encoding="utf-8")
        accepted, refused = reuse.verified_lanes(self.environment(self.h1), [self.LANE])
        self.assertNotIn(self.LANE, accepted)
        self.assertIn("commands_that_read_a_changed_tool_were_executed_again_at_this_head", refused[self.LANE]["refused_by"])


class StoredRecordIsNeverTrustedTests(CheckFixture):
    def setUp(self) -> None:
        super().setUp()
        self.prepare()
        self.env = self.environment(self.h1)
        self.result = reuse.check_lane(self.env, self.LANE, reexecute=True, stamp="T1")
        self.proof = reuse.write_proof(self.env, self.result, rehearsal=False, stamp="T1")

    def accepted(self, head: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        return reuse.verified_lanes(self.environment(head or self.h1), [self.LANE])

    def test_the_proof_is_accepted_while_the_dependencies_hold(self) -> None:
        self.assertIn(self.LANE, self.accepted()[0])

    def test_a_dependency_changed_after_the_proof_refuses_it(self) -> None:
        self.log_path.write_text("changed after the proof was written\n", encoding="utf-8")
        accepted, refused = self.accepted()
        self.assertNotIn(self.LANE, accepted)
        self.assertIn("original_receipt_and_logs_are_what_they_were", refused[self.LANE]["refused_by"])

    def test_a_proof_for_an_earlier_head_is_not_a_proof_for_a_later_one(self) -> None:
        self.put("src/aggie_analytics/__init__.py", "VERSION = 3\n")
        newer = self.commit("a later commit that changes product code")
        self.assertEqual(self.accepted(newer), ({}, {}))  # no proof exists for that head at all

    def test_a_hand_written_proof_for_the_current_head_is_recomputed_not_trusted(self) -> None:
        self.log_path.write_text("changed before the forged record was read\n", encoding="utf-8")
        forged = self.out_root / "evidence" / "reuse" / f"REUSE_{self.LANE}_{self.h1[:12]}_ZZ.json"
        forged.parent.mkdir(parents=True, exist_ok=True)
        forged.write_text(json.dumps({"holds": True, "current": {"head": self.h1}, "reexecuted": [], "checks": []}),
                          encoding="utf-8")
        accepted, refused = self.accepted()
        self.assertNotIn(self.LANE, accepted)
        self.assertTrue(refused)

    def test_a_proof_that_did_not_hold_is_never_accepted(self) -> None:
        document = json.loads(self.proof.read_text(encoding="utf-8"))
        document["holds"] = False
        document["refused_by"] = ["something"]
        self.proof.write_text(json.dumps(document), encoding="utf-8")
        accepted, refused = self.accepted()
        self.assertNotIn(self.LANE, accepted)
        self.assertEqual(refused[self.LANE]["refused_by"], ["something"])

    def test_a_rehearsal_proof_is_never_accepted(self) -> None:
        document = json.loads(self.proof.read_text(encoding="utf-8"))
        document["rehearsal"] = True
        self.proof.write_text(json.dumps(document), encoding="utf-8")
        self.assertEqual(self.accepted(), ({}, {}))


class InstalledConsumerChecksTests(CheckFixture):
    LANE = "INSTALLED_CONSUMER_C01"

    def setUp(self) -> None:
        super().setUp()
        stage = self.base / "stage"
        self.wheel = stage / "dist" / "aggie.whl"
        self.wheel.parent.mkdir(parents=True)
        self.wheel.write_bytes(b"wheel bytes")
        self.record = stage / "venv" / "Lib" / "site-packages" / "aggie-0.dist-info" / "RECORD"
        self.installed = self.record.parent.parent / "aggie_analytics" / "__init__.py"
        self.installed.parent.mkdir(parents=True)
        self.record.parent.mkdir(parents=True)
        self.installed.write_bytes(self.blob(self.h0, "src/aggie_analytics/__init__.py"))
        self.put("src/aggie_analytics/cycle30/schemas/one.json", '{"schema": 1}\n')
        self.h0 = self.commit("a packaged schema file")
        self.schema = self.installed.parent / "cycle30" / "schemas" / "one.json"
        self.schema.parent.mkdir(parents=True)
        self.schema.write_bytes(self.blob(self.h0, "src/aggie_analytics/cycle30/schemas/one.json"))
        (self.installed.parent / "__pycache__").mkdir()
        (self.installed.parent / "__pycache__" / "x.cpython-312.pyc").write_bytes(b"compiled")
        self.record.write_text("aggie_analytics/__init__.py,sha256=x,1\naggie_analytics/cycle30/schemas/one.json,sha256=y,1\n"
                               "aggie_analytics/__pycache__/x.cpython-312.pyc,,\naggie-0.dist-info/RECORD,,\n", encoding="utf-8")
        self.database = self.base / "delivered.sqlite"
        self.database.write_bytes(b"database")
        self.successor = self.base / "successor.sqlite"
        self.successor.write_bytes(b"successor")
        details = {"installed": {"wheel": str(self.wheel)}, "wheel_sha256": sha(b"wheel bytes"),
                   "installed_source_equivalence": {"record": str(self.record), "installed_files": 2,
                                                    "installed_equal_to_committed_source": 2},
                   "delivered_database_unchanged": {"before": sha(b"database"), "after": sha(b"database"),
                                                    "expected": sha(b"database")},
                   "installed_identity_census": {"census": {"successor": str(self.successor),
                                                            "successor_sha256": sha(b"successor")}}}
        self.prepare(details=details)

    def check(self, lane: str | None = None, head: str | None = None, **overrides: Any) -> dict[str, Any]:
        overrides.setdefault("lane_checks", {self.LANE: reuse.installed_consumer_checks})
        overrides.setdefault("database", self.database)
        return super().check(lane, head, **overrides)

    def test_the_wheel_the_installed_files_the_database_and_the_successor_all_holding_is_retained(self) -> None:
        result = self.check()
        self.assertTrue(result["holds"], result["refused_by"])

    def test_a_changed_wheel_is_refused(self) -> None:
        self.wheel.write_bytes(b"another wheel")
        self.assertIn("packaged_wheel_is_the_recorded_one", self.check()["refused_by"])

    def test_an_installed_file_that_differs_from_the_committed_source_is_refused(self) -> None:
        self.installed.write_bytes(b"VERSION = 99\n")
        self.assertIn("installed_files_equal_the_current_committed_source", self.check()["refused_by"])

    def test_an_installed_file_that_the_current_source_no_longer_matches_is_refused(self) -> None:
        # the source changed at the current head after the wheel was built (the installed file is the old one)
        self.put("src/aggie_analytics/__init__.py", "VERSION = 5\n")
        newer = self.commit("product source changed")
        result = self.check(head=newer)
        self.assertIn("every_changed_tracked_path_is_declared", result["refused_by"])
        self.assertIn("installed_files_equal_the_current_committed_source", result["refused_by"])

    def test_a_packaged_schema_file_is_held_to_the_committed_source_like_a_python_file(self) -> None:
        self.schema.write_bytes(b'{"schema": 2}\n')
        self.assertIn("installed_files_equal_the_current_committed_source", self.check()["refused_by"])

    def test_the_count_of_installed_files_must_be_the_recorded_one(self) -> None:
        (self.installed.parent / "extra.py").write_bytes(b"x = 1\n")
        self.record.write_text(self.record.read_text(encoding="utf-8") + "aggie_analytics/extra.py,sha256=z,1\n",
                               encoding="utf-8")
        self.assertIn("installed_files_equal_the_current_committed_source", self.check()["refused_by"])

    def test_a_changed_delivered_database_or_successor_is_refused(self) -> None:
        self.database.write_bytes(b"other database")
        self.assertIn("delivered_database_is_the_recorded_one", self.check()["refused_by"])
        self.database.write_bytes(b"database")
        self.successor.write_bytes(b"other successor")
        self.assertIn("successor_is_the_recorded_one", self.check()["refused_by"])


if __name__ == "__main__":
    unittest.main()
