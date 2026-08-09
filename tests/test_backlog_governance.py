from __future__ import annotations
import csv,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.validate_backlog import validate

class BacklogGovernanceTests(unittest.TestCase):
    def test_backlog_valid(self): self.assertEqual([],validate(ROOT))
    def test_five_phases(self):
        with (ROOT/'governance/IMPLEMENTATION_PHASES.csv').open(newline='',encoding='utf-8') as f:self.assertEqual(5,len(list(csv.DictReader(f))))
    def test_w06_replan_gate_state(self):
        with (ROOT/'governance/IMPLEMENTATION_WBS.csv').open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        by_id={x['task_id']:x for x in rows}
        self.assertEqual('DONE',by_id['TASK-006']['status'])
        self.assertIn(by_id['TASK-007']['status'], {'READY','DONE','COMPLETE_W07','DONE_W07'})
        self.assertFalse(any(x['status']=='PLANNED_REVALIDATE_AFTER_W06' for x in rows))
        self.assertTrue(any(x['owner_wave']=='W06' and x['critical_dependency_gate']=='YES' for x in rows))
    def test_no_duration_fields(self):
        with (ROOT/'governance/IMPLEMENTATION_WBS.csv').open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        self.assertNotIn('estimated_hours',rows[0]); self.assertNotIn('estimated_days',rows[0])
    def test_every_task_has_req_and_acceptance_mapping(self):
        with (ROOT/'governance/IMPLEMENTATION_WBS.csv').open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        self.assertTrue(all(x['requirement_ids'].strip() for x in rows))
        self.assertTrue(all(x['acceptance_control_ids'].strip() for x in rows))
    def test_json_matches_csv_task_count(self):
        plan=json.loads((ROOT/'configs/implementation_plan.json').read_text())
        with (ROOT/'governance/IMPLEMENTATION_WBS.csv').open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),len(plan['tasks']))
if __name__=='__main__':unittest.main()
