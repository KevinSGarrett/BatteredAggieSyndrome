import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.experimentation.worktree import WorktreePlan

class WorktreeTests(unittest.TestCase):
    def test_protected_mutation_rejected(self):
        p=WorktreePlan("E","GIT_WORKTREE",["governance/METRIC_REGISTRY.csv"],{"cpu":1})
        with self.assertRaises(PermissionError): p.validate()
    def test_paid_compute_requires_approval(self):
        p=WorktreePlan("E","GIT_WORKTREE",["src/foo.py"],{"paid_remote_compute":True},False)
        with self.assertRaises(PermissionError): p.validate()
    def test_local_plan_valid(self):
        WorktreePlan("E","IMMUTABLE_SOURCE_SNAPSHOT",["src/foo.py"],{"cpu":2,"ram_gb":4},False).validate()
