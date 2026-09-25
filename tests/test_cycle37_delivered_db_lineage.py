"""Cycle #37 - Attempt #2 - ACTUAL_STATE: a role-count change is excused only by matching lineage."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cycle37" / "delivered_db_review.py"


def _load():
    spec = importlib.util.spec_from_file_location("delivered_db_review", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _connection(before: dict[int, list[str]], after: dict[int, list[str]],
                lineage: dict[int, tuple[list[str], list[str]]]) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("ATTACH DATABASE ':memory:' AS pred")
    for schema, rows in (("main", after), ("pred", before)):
        connection.execute(f'CREATE TABLE {schema}."staff_role_assignment" (observation_id INTEGER, role_code TEXT)')
        connection.executemany(
            f'INSERT INTO {schema}."staff_role_assignment" VALUES (?, ?)',
            [(o, code) for o, codes in rows.items() for code in codes],
        )
    # The released lineage table stores the observation id as text.
    connection.execute(
        'CREATE TABLE main."staff_reparse_change" (observation_id TEXT, field TEXT, cycle36_value TEXT, cycle37_value TEXT)'
    )
    connection.executemany(
        'INSERT INTO main."staff_reparse_change" VALUES (?, ?, ?, ?)',
        [(str(o), "role_codes", json.dumps(old), json.dumps(new)) for o, (old, new) in lineage.items()],
    )
    return connection


BEFORE = {1: ["assistant_head_coach", "equipment_staff"], 2: ["administrative_staff", "assistant_head_coach"], 3: ["quarterbacks"]}
AFTER = {1: ["administrative_staff", "equipment_staff"], 2: ["administrative_staff"], 3: ["quarterbacks"]}


class LineageReconciliationTests(unittest.TestCase):
    """A count change is excused only by matching lineage rows."""

    def test_every_recorded_change_reconciles(self) -> None:
        tool = _load()
        lineage = {1: (BEFORE[1], AFTER[1]), 2: (BEFORE[2], AFTER[2])}
        result = tool.reconcile_by_lineage(_connection(BEFORE, AFTER, lineage), "staff_role_assignment")
        assert result["reconciled"] and result["changed_observations"] == 2 and result["recorded"] == 2

    def test_an_unrecorded_change_is_not_excused(self) -> None:
        tool = _load()
        result = tool.reconcile_by_lineage(_connection(BEFORE, AFTER, {1: (BEFORE[1], AFTER[1])}), "staff_role_assignment")
        assert not result["reconciled"] and result["unrecorded"] == [2]

    def test_a_lineage_row_that_disagrees_with_the_tables_is_not_excused(self) -> None:
        tool = _load()
        lineage = {1: (BEFORE[1], AFTER[1]), 2: (BEFORE[2], ["head_coach"])}
        result = tool.reconcile_by_lineage(_connection(BEFORE, AFTER, lineage), "staff_role_assignment")
        assert not result["reconciled"] and result["values_disagree_with_the_tables"] == [2]


if __name__ == "__main__":
    unittest.main()
