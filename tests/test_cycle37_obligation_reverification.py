"""Cycle #37 - Attempt #2 - ACTUAL_STATE

The inherited-obligation re-measurement must read the release, not repeat a
category. These tests build a small release database and check that each
database-backed obligation moves with the data, and that the contract
parser neither drops nor invents an obligation.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_path = ROOT / "tools" / "cycle37" / "r37_01_obligation_reverification.py"
_spec = importlib.util.spec_from_file_location("r37_01_obligation_reverification", _path)
tool = importlib.util.module_from_spec(_spec)
sys.modules["r37_01_obligation_reverification"] = tool
_spec.loader.exec_module(tool)


def release(tmp: Path, *, cells=(("CONFIRMED_SOURCE_SCOPED", 2), ("NO_EVIDENCE", 3)),
            stated=None, scheme=(("p1", 2020, "Page A"),), unresolved_detail="no declared name matches") -> Path:
    path = tmp / "release.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript("""
        create table coverage_summary (grain text, bucket text, value integer);
        create table core_role_cell (cell_id text, program_id text, season integer, role_code text,
                                     coverage_state text, observations integer);
        create table scheme_assertion (program_id text, season integer, page_title text);
        create table unresolved_program_name (unresolved_id text, raw_name text, state text, seasons text,
                                              candidate_program_ids text, detail text);
        create table user_corpus_cell (season integer);
        create table responsibility_assertion (disposition text);
    """)
    n = 0
    for state, count in cells:
        for _ in range(count):
            n += 1
            conn.execute("insert into core_role_cell values (?,?,?,?,?,?)", (f"c{n}", "p", 2020, "HC", state, 1))
    for state, count in (stated if stated is not None else cells):
        conn.execute("insert into coverage_summary values ('CORE_ROLE_CELL', ?, ?)", (state, count))
    conn.executemany("insert into scheme_assertion values (?,?,?)", scheme)
    conn.execute("insert into unresolved_program_name values ('u1','X','UNRESOLVED',NULL,NULL,?)",
                 (unresolved_detail,))
    conn.executemany("insert into user_corpus_cell values (?)", [(2014,), (2005,)])
    conn.executemany("insert into responsibility_assertion values (?)",
                     [("ADMITTED_EXPLICIT_SOURCE_STATEMENT",), ("REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT",)])
    conn.commit()
    conn.close()
    return path


class DatabaseChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r37_obl_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def ctx(self, **kwargs) -> "tool.Context":
        fresh = Path(tempfile.mkdtemp(dir=self.tmp))
        ctx = tool.Context(release(fresh, **kwargs))
        self.addCleanup(ctx.conn.close)
        return ctx

    def test_confirmed_coverage_follows_the_cells(self) -> None:
        self.assertEqual(tool.c_confirmed_coverage(self.ctx())["state"], tool.SATISFIED)

    def test_no_confirmed_cell_is_not_satisfied(self) -> None:
        ctx = self.ctx(cells=(("NO_EVIDENCE", 3),))
        self.assertEqual(tool.c_confirmed_coverage(ctx)["state"], tool.LOCAL)

    def test_a_summary_that_disagrees_with_its_rows_is_caught(self) -> None:
        ctx = self.ctx(stated=(("CONFIRMED_SOURCE_SCOPED", 5), ("NO_EVIDENCE", 0)))
        self.assertEqual(tool.c_release_states_coverage(ctx)["state"], tool.LOCAL)
        self.assertEqual(tool.c_release_states_coverage(self.ctx())["state"], tool.SATISFIED)

    def test_two_page_titles_on_one_program_season_is_a_collision(self) -> None:
        ctx = self.ctx(scheme=(("p1", 2020, "Page A"), ("p1", 2020, "Page B")))
        self.assertEqual(tool.c_scheme_crosswalk(ctx)["state"], tool.LOCAL)

    def test_an_unresolved_name_without_a_reason_is_not_settled(self) -> None:
        self.assertEqual(tool.c_program_unresolved(self.ctx(unresolved_detail=""))["state"], tool.LOCAL)
        self.assertEqual(tool.c_program_unresolved(self.ctx())["state"], tool.SATISFIED)

    def responsibility_state(self, receipt: dict | None) -> str:
        attempt = Path(tempfile.mkdtemp(dir=self.tmp))
        if receipt is not None:
            (attempt / "evidence" / "repairs").mkdir(parents=True)
            (attempt / "evidence" / "repairs" / "R37_06_SCHEME_RESPONSIBILITY.json").write_text(
                json.dumps(receipt), encoding="utf-8")
        original = tool.ATTEMPT
        tool.ATTEMPT = attempt
        try:
            return tool.c_responsibility(self.ctx())["state"]
        finally:
            tool.ATTEMPT = original

    def test_responsibility_follows_the_whole_cache_scan(self) -> None:
        both = {"current_responsibility_episodes": [{"person": "p"}],
                "population": {"encyclopedia": {"CANDIDATE_HISTORICAL_EXPLICIT_STATEMENT": 3}}}
        only_history = {"current_responsibility_episodes": [],
                        "population": {"encyclopedia": {"CANDIDATE_HISTORICAL_EXPLICIT_STATEMENT": 3}}}
        self.assertEqual(self.responsibility_state(both), tool.SATISFIED)
        self.assertEqual(self.responsibility_state(only_history), tool.PARTIAL)
        self.assertEqual(self.responsibility_state(None), tool.MISSING)


class KernelEvidenceChecks(unittest.TestCase):
    """OBL_KERNEL_*: the obligations follow the R37-08 evidence, not a category."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r37_obl_k_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "evidence" / "repairs").mkdir(parents=True)
        original = tool.ATTEMPT
        tool.ATTEMPT = self.tmp
        self.addCleanup(setattr, tool, "ATTEMPT", original)

    def write(self, name: str, payload) -> None:
        path = self.tmp / "evidence" / "repairs" / name
        if isinstance(payload, list):
            path.write_text("".join(json.dumps(row) + "\n" for row in payload), encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")

    def test_labels_are_settled_only_when_every_one_is_withdrawn(self) -> None:
        self.assertEqual(tool.c_kernel_receipts(None)["state"], tool.LOCAL)
        audit = {"predecessor": {"labelled_rows": 2, "bytes_preserved": True}, "gates_pass": True}
        withdrawn = {"successor_state": "WITHDRAWN_NO_PER_PRIOR_PUBLICATION_RECEIPT", "pit_admissible": False}
        self.write("R37_08_LABEL_CONSUMER_AUDIT.json", audit)
        self.write("R37_08_PRODUCER_LABEL_SUCCESSOR.jsonl", [withdrawn])
        self.assertEqual(tool.c_kernel_receipts(None)["state"], tool.PARTIAL)
        self.write("R37_08_PRODUCER_LABEL_SUCCESSOR.jsonl", [withdrawn, withdrawn])
        self.assertEqual(tool.c_kernel_receipts(None)["state"], tool.SATISFIED)
        self.write("R37_08_LABEL_CONSUMER_AUDIT.json", {**audit, "gates_pass": False})
        self.assertEqual(tool.c_kernel_receipts(None)["state"], tool.PARTIAL)

    def test_sources_are_settled_only_with_no_unsourced_row_or_residual(self) -> None:
        self.assertEqual(tool.c_kernel_sources(None)["state"], tool.LOCAL)
        good = {"population_equations": {"membership": {"PUBLIC_CFBD_FILE": 3}, "no_row_disappeared": True},
                "field_reconciliation": {"unexplained_residual_sides": 0}, "requests": {"game_source_requests": 0}}
        self.write("R37_08_KERNEL_RECONCILIATION.json", good)
        self.assertEqual(tool.c_kernel_sources(None)["state"], tool.SATISFIED)
        unsourced = {**good, "population_equations": {"membership": {"NO_LOCAL_SOURCE": 1}, "no_row_disappeared": True}}
        self.write("R37_08_KERNEL_RECONCILIATION.json", unsourced)
        self.assertEqual(tool.c_kernel_sources(None)["state"], tool.PARTIAL)
        self.write("R37_08_KERNEL_RECONCILIATION.json", {**good, "field_reconciliation": {"unexplained_residual_sides": 2}})
        self.assertEqual(tool.c_kernel_sources(None)["state"], tool.PARTIAL)


class ContractParsing(unittest.TestCase):
    def test_obligations_are_parsed_verbatim_and_rows_are_kept(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="r37_obl_c_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        body = {"obligation": "OBL_X", "acceptance_predicate": "p", "state": "OPEN", "source_entry_count": 1}
        statement = "Account and fulfill the applicable unchanged inherited obligation OBL_X: " + json.dumps(body)
        contract = {"requirements": [
            {"id": "R1", "acceptance": [{"id": "R1-CF-OBL-X", "statement": statement},
                                        {"id": "R1-AC01", "statement": "Something else."}]},
            {"id": "R2", "acceptance": [{"id": "R2-CF-OBL-X", "statement": statement}]},
        ]}
        path = tmp / "contract.json"
        path.write_text(json.dumps(contract), encoding="utf-8")
        parsed = tool.parse_contract(path)
        self.assertEqual(parsed["rows"], {"OBL_X": ["R1-CF-OBL-X", "R2-CF-OBL-X"]})
        self.assertEqual(parsed["bodies"]["OBL_X"], body)

    def test_every_check_is_named_for_a_distinct_obligation(self) -> None:
        self.assertEqual(len(tool.CHECKS), 30)
        self.assertTrue(all(name.startswith("OBL_") for name in tool.CHECKS))


if __name__ == "__main__":
    unittest.main()
