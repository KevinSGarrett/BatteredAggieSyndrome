"""R34-07: this session's real acquired career-join and program-season
receipts (R34-06/R34-11) are actually ingested into the query/episode model
(`query.py`'s staff_role_cells table), not just left as markdown receipts,
and the ingested data is genuinely queryable through the real API."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33 import query as q  # noqa: E402

_MODULE_PATH = REPO_ROOT / "tools" / "cycle34_r34_07_ingest_career_joins.py"
_spec = importlib.util.spec_from_file_location("cycle34_r34_07_ingest_career_joins", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)  # type: ignore[union-attr]


class R3407CareerIngestTests(unittest.TestCase):
    def test_all_source_receipts_convert_to_role_cells(self) -> None:
        cells = _module.build_role_cells()
        # 28 program-seasons' roles, plus one explicit negative-control row.
        role_count = sum(len(row["roles"]) for row in _module.PROGRAM_SEASONS)
        self.assertEqual(len(cells), role_count + 1)
        # Every cell must carry a real source URL -- never a placeholder.
        for cell in cells:
            self.assertTrue(cell["source_file"])
            self.assertTrue(cell["source_file"].startswith("https://en.wikipedia.org/"))

    def test_pipeline_loads_and_is_queryable(self) -> None:
        result = _module.run()
        self.assertGreater(result["rows_inserted"], 0)
        self.assertGreater(result["rows_verified_career_join"], 0)
        db_path = Path(result["database_path"])
        self.assertTrue(db_path.is_file())

        conn = q.connect(db_path, readonly=True)
        try:
            rows = q.team_staff(conn, team="Texas A&M", season="2012")
            people = {row["person"] for row in rows}
            self.assertIn("Kevin Sumlin", people)
            self.assertIn("Kliff Kingsbury", people)

            career = q.coach_career(conn, person="Troy Calhoun")
            self.assertGreaterEqual(len(career), 2)
            seasons = {row["season"] for row in career if row["season"]}
            self.assertIn("2018", seasons)
        finally:
            conn.close()

    def test_negative_control_is_present_and_unresolved(self) -> None:
        cells = _module.build_role_cells()
        control = [c for c in cells if c["observation_id"].startswith("R34_07_CONTROL_")]
        self.assertEqual(len(control), 1)
        self.assertFalse(control[0]["verified"])
        self.assertIsNone(control[0]["team"])


if __name__ == "__main__":
    unittest.main()
