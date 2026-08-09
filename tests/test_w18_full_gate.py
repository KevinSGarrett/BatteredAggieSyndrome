import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import csv,json,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class W18FullGateTests(unittest.TestCase):
    def test_master_coverage(self):
        with (ROOT/"governance/W18_MASTER_REQUIREMENT_COVERAGE.csv").open(newline="",encoding="utf-8") as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),13)
        self.assertTrue(all("COVERED" in r["status"] for r in rows))
    def test_w18_owned_tasks_complete(self):
        with (ROOT/"governance/IMPLEMENTATION_WBS.csv").open(newline="",encoding="utf-8") as f:
            rows=[r for r in csv.DictReader(f) if r["owner_wave"]=="W18"]
        self.assertTrue(rows)
        self.assertTrue(all(r["status"]=="DONE" for r in rows),[(r["task_id"],r["status"]) for r in rows])
        self.assertIn("TASK-164",{r["task_id"] for r in rows})
    def test_full_rebuild_requirements_present(self):
        with (ROOT/"governance/REQUIREMENTS_INDEX.csv").open(newline="",encoding="utf-8") as f:
            ids={r["requirement_id"] for r in csv.DictReader(f)}
        for n in range(681,701): self.assertIn(f"REQ-{n:03d}",ids)
