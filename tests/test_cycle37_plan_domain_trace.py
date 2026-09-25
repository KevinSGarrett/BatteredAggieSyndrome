"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-14: the plan-link adjudicator and the domain trace must not call a link
or a domain more than it is.

The plan tests build a tiny git repository with the four token registries,
commit a discovery-time file, change it, and check each verdict the
adjudicator can reach -- including the ones that say a heuristic link was
never real. The domain tests check that consumers and tests come from the
import graph rather than from a declaration, and that an all-skipped test
file is not read as a pass.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(filename: str):
    name = Path(filename).stem
    path = ROOT / "tools" / "cycle37" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


plan = _load("r37_14_plan_inventory.py")
trace = _load("r37_14_domain_trace.py")
successor = _load("r37_14_plan_successor.py")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout


class TokenAndContextTests(unittest.TestCase):
    def test_a_token_does_not_match_inside_a_longer_id(self) -> None:
        rx = plan.token_regex("REQ-001")
        self.assertIsNone(rx.search("REQ-0010"))
        self.assertIsNone(rx.search("XREQ-001"))
        self.assertIsNotNone(rx.search("see REQ-001."))

    def test_the_malformed_regex_artifact_is_not_canonical(self) -> None:
        self.assertIsNone(plan.CANONICAL_TOKEN.match("REQ-ADR-RISK-AC"))
        self.assertIsNotNone(plan.CANONICAL_TOKEN.match("THR-015"))

    def test_csv_contexts_distinguish_the_key_column(self) -> None:
        text = "id,refs\nREQ-001,AC-002\nREQ-002,REQ-001\n"
        self.assertEqual(plan.occurrence_contexts("x.csv", text, "REQ-001"),
                         ["CSV_KEY_COLUMN", "CSV_COLUMN:refs"])

    def test_json_contexts_distinguish_id_fields(self) -> None:
        text = json.dumps({"rows": [{"id": "AC-001", "note": "needs AC-001"}]})
        self.assertEqual(sorted(plan.occurrence_contexts("x.json", text, "AC-001")),
                         ["JSON_ID_FIELD", "JSON_VALUE:note"])

    def test_markdown_contexts_skip_nothing_and_see_fences(self) -> None:
        text = "# REQ-001 heading\n\n- item REQ-001\n\n```\nREQ-001\n```\nprose REQ-001\n"
        self.assertEqual(plan.occurrence_contexts("x.md", text, "REQ-001"),
                         ["MD_HEADING", "MD_LIST_ITEM", "MD_CODE_BLOCK", "MD_PROSE"])


class SectionTests(unittest.TestCase):
    def test_headings_inside_a_fence_are_not_sections(self) -> None:
        text = "# One\nMust do A.\n```\n# not a heading\n```\n## Two\nNever do B.\n"
        sections = plan.md_sections(text)
        self.assertEqual([s["heading_path"] for s in sections], [["One"], ["One", "Two"]])

    def test_only_normative_units_become_statements(self) -> None:
        units = plan.md_units(["The team must file X.", "", "Background text.", "", "- never do Y"])
        normative = [u for u in units if plan.NORMATIVE.search(u)]
        self.assertEqual(normative, ["The team must file X.", "- never do Y"])

    def test_user_additions_are_classified(self) -> None:
        self.assertEqual(plan.source_class_of({"id": "ANCESTRAL-122",
                                               "path": r"C:\x\USER_COACHES_DATA_REVIEW.md"}), "USER_ADDITION")
        self.assertEqual(plan.source_class_of({"id": "RECOVERY37", "path": r"C:\x\m.md"}), "USER_ADDITION")
        self.assertEqual(plan.source_class_of({"id": "HIST-37-040", "path": r"C:\x\a.md"}),
                         "HISTORICAL_PRESERVED")


class LinkAdjudicationTests(unittest.TestCase):
    """End to end over a real, tiny repository."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r37_14_links_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        repo = self.tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "fixture@example.invalid")
        git(repo, "config", "user.name", "fixture")
        files = {
            "governance/REQUIREMENTS_INDEX.csv": "requirement_id,title,status\nREQ-001,a,ACTIVE\nREQ-002,b,ACTIVE\n",
            "governance/ACCEPTANCE_CONTROL_CATALOG.csv": "control_id,title,current_status\nAC-001,a,PASS\n",
            "governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv": "threshold_id,name,status\nTHR-001,a,TBD\n",
            "docs/data_research/w06/DATA_DOMAIN_COVERAGE_MATRIX.csv": "domain_id,domain,confidence\nDOM-001,g,HIGH\n",
            "governance/TRACE.csv": "requirement_id,control\nREQ-001,AC-001\n",
            "docs/plan.md": "# Plan\nThis cites REQ-002 and REQ-001.\n",
        }
        for rel, text in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_bytes(text.encode("utf-8"))
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "discovery")
        discovery = {rel: hashlib.sha256((repo / rel).read_bytes()).hexdigest() for rel in files}
        # After discovery the plan drops REQ-002.
        (repo / "docs/plan.md").write_bytes(b"# Plan\nThis cites REQ-001.\n")
        git(repo, "commit", "-q", "-am", "later")
        index = [
            {"path": "governance/REQUIREMENTS_INDEX.csv", "sha256": discovery["governance/REQUIREMENTS_INDEX.csv"],
             "tokens": ["REQ-001"]},
            {"path": "governance/TRACE.csv", "sha256": discovery["governance/TRACE.csv"],
             "tokens": ["REQ-001", "AC-001", "REQ-ADR-RISK-AC", "REQ-009"]},
            {"path": "docs/plan.md", "sha256": discovery["docs/plan.md"],
             "tokens": ["REQ-001", "REQ-002", "AC-001"]},
        ]
        self.index_path = self.tmp / "index.json"
        self.index_path.write_text(json.dumps(index), encoding="utf-8")
        self.repo = repo

    def verdicts(self) -> dict[tuple[str, str], dict]:
        out = self.tmp / "out"
        out.mkdir()
        args = argparse.Namespace(discovery_index=self.index_path)
        summary = plan.adjudicate_links(args, self.repo, out)
        rows = [json.loads(line) for line in (out / "R37_14_LINK_ADJUDICATION.jsonl").read_text(
            encoding="utf-8").splitlines()]
        self.assertEqual(summary["pairs"], 8)
        return {(r["path"], r["token"]): r for r in rows}

    def test_every_verdict_is_reached_and_none_is_semantic(self) -> None:
        rows = self.verdicts()
        self.assertEqual(rows[("governance/REQUIREMENTS_INDEX.csv", "REQ-001")]["verdict"],
                         "REGISTRY_DEFINITION")
        self.assertEqual(rows[("governance/TRACE.csv", "REQ-001")]["verdict"], "RESOLVED_KEYED_TRACE_ROW")
        self.assertEqual(rows[("governance/TRACE.csv", "AC-001")]["verdict"],
                         "RESOLVED_STRUCTURED_CROSS_REFERENCE")
        self.assertEqual(rows[("governance/TRACE.csv", "REQ-ADR-RISK-AC")]["verdict"],
                         "MALFORMED_TOKEN_EXTRACTION_ARTIFACT")
        # REQ-009 never occurred in the discovery bytes: the heuristic link was not real.
        self.assertEqual(rows[("governance/TRACE.csv", "REQ-009")]["verdict"],
                         "NOT_REPRODUCED_AT_DISCOVERY_BYTES")
        self.assertEqual(rows[("docs/plan.md", "REQ-001")]["verdict"], "RESOLVED_TEXT_REFERENCE")
        self.assertEqual(rows[("docs/plan.md", "REQ-002")]["verdict"], "TOKEN_REMOVED_AT_HEAD")
        self.assertEqual(rows[("docs/plan.md", "AC-001")]["verdict"], "NOT_REPRODUCED_AT_DISCOVERY_BYTES")
        self.assertTrue(all(r["semantic_relevance"] == "NOT_ADJUDICATED" for r in rows.values()))

    def test_discovery_bytes_are_recovered_from_history(self) -> None:
        rows = self.verdicts()
        row = rows[("docs/plan.md", "REQ-002")]
        self.assertEqual(row["file_state"], "CHANGED_SINCE_DISCOVERY")
        self.assertNotEqual(row["discovery_bytes_source"], "HEAD")
        self.assertTrue(row["present_at_discovery_bytes"])


class DomainTraceTests(unittest.TestCase):
    def test_consumers_and_tests_come_from_imports(self) -> None:
        imports = {
            "src/aggie_analytics/a.py": set(),
            "src/aggie_analytics/b.py": {"aggie_analytics.a"},
            "tools/run_b.py": {"aggie_analytics.b"},
            "tests/test_a.py": {"aggie_analytics", "aggie_analytics.a"},
            "tests/test_unrelated.py": {"aggie_analytics.c"},
            "tests/fixture_builder.py": {"aggie_analytics.a"},
        }
        consumers, tests = trace.importers_of("src/aggie_analytics/a.py", imports, {})
        self.assertEqual(consumers, ["src/aggie_analytics/b.py"])
        self.assertEqual(tests, ["tests/test_a.py"])

    def test_a_tool_is_found_by_its_script_name(self) -> None:
        refs = {"tests/test_tool.py": {"c36_09_neutral_travel.py"}}
        imports = {"tests/test_tool.py": set()}
        _, tests = trace.importers_of("tools/cycle36/c36_09_neutral_travel.py", imports, refs)
        self.assertEqual(tests, ["tests/test_tool.py"])

    def test_all_skipped_is_not_a_pass(self) -> None:
        text = "...\n----------------------------------------------------------------------\nRan 3 tests in 0.1s\n\nOK (skipped=3)\n"
        self.assertEqual(trace.classify_unittest(text, 0)["state"], "ALL_SKIPPED")

    def test_ok_with_some_skips_passes(self) -> None:
        text = "Ran 5 tests in 0.2s\n\nOK (skipped=2)\n"
        outcome = trace.classify_unittest(text, 0)
        self.assertEqual((outcome["state"], outcome["ran"], outcome["skipped"]), ("PASSED", 5, 2))

    def test_failures_and_errors_fail(self) -> None:
        text = "Ran 4 tests in 0.2s\n\nFAILED (failures=1, errors=2)\n"
        outcome = trace.classify_unittest(text, 1)
        self.assertEqual((outcome["state"], outcome["failures_and_errors"]), ("FAILED", 3))

    def test_no_summary_means_nothing_ran(self) -> None:
        self.assertEqual(trace.classify_unittest("ImportError: boom", 1)["state"], "DID_NOT_RUN")
        self.assertEqual(trace.classify_unittest("Ran 0 tests in 0.0s\n\nOK\n", 0)["state"], "DID_NOT_RUN")

    def test_the_declaration_covers_the_named_domains(self) -> None:
        declaration = json.loads((ROOT / "tools/cycle37/r37_14_domain_trace_declaration.json").read_text(
            encoding="utf-8"))
        for tag in ("injuries", "coaches", "rosters", "recruiting", "transfers", "weather", "travel",
                    "venues", "markets", "game_and_play_data", "conditional_nil",
                    "conditional_high_school", "conditional_substitution", "conditional_altitude",
                    "conditional_time_zone"):
            with self.subTest(tag=tag):
                self.assertTrue(declaration["named_requirement_tags"][tag])
                for did in declaration["named_requirement_tags"][tag]:
                    self.assertIn(did, declaration["domains"])


class PlanSuccessorTests(unittest.TestCase):
    ORIGINAL = (
        "# Plan\r\n\r\nIntro.\r\n\r\n"
        "## TP37-01 — One\r\n\r\nBody one.\r\n\r\n"
        "## TP37-02 — Two\r\n\r\nBody two.\r\n\r\n"
        "## TP37-03 — Three\r\n\r\nBody three.\r\n"
    )

    def test_only_named_sections_change_and_line_endings_survive(self) -> None:
        out = successor.apply_changes(self.ORIGINAL, {"TP37-02": "### Actual state\n\n- x\n"},
                                      {"TP37-03": "## TP37-N — New\n\nText.\n"})
        before = dict(successor.split_sections(self.ORIGINAL))
        after = dict(successor.split_sections(out))
        self.assertEqual(before[None], after[None])
        self.assertEqual(before["TP37-01"], after["TP37-01"])
        self.assertEqual(before["TP37-03"].rstrip("\r\n"), after["TP37-03"].rstrip("\r\n"))
        self.assertIn("Body two.", after["TP37-02"])
        self.assertIn("### Actual state", after["TP37-02"])
        self.assertIn("TP37-N", after)
        self.assertNotIn("\n", out.replace("\r\n", ""))

    def test_a_missing_section_is_an_error_not_a_no_op(self) -> None:
        with self.assertRaises(ValueError):
            successor.apply_changes(self.ORIGINAL, {"TP37-99": "x"}, {})


if __name__ == "__main__":
    unittest.main()
