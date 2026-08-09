import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.experimentation.hpo import HPOStudySpec, SearchParameter

class HPOTests(unittest.TestCase):
    def study(self, **kw):
        base=dict(candidate_family="boosted",search_space_version="v1",parameters=[SearchParameter("depth","int",{"low":2,"high":8,"step":1})],
                  development_split="SPLIT-DEV-SEL",objective_metrics=["brier"],trial_budget=20,concurrency=2)
        base.update(kw); return HPOStudySpec(**base)
    def test_protected_split_forbidden(self):
        with self.assertRaises(ValueError): self.study(development_split="SPLIT-PROTECTED").validate()
    def test_forward_split_forbidden(self):
        with self.assertRaises(ValueError): self.study(development_split="SPLIT-FORWARD").validate()
    def test_study_id_deterministic(self):
        self.assertEqual(self.study().study_id,self.study().study_id)
    def test_sqlite_distributed_nfs_forbidden(self):
        with self.assertRaises(ValueError): self.study(storage_backend="SQLITE_DISTRIBUTED_NFS").validate()
    def test_bad_log_range_rejected(self):
        p=SearchParameter("lr","log_float",{"low":0,"high":1})
        with self.assertRaises(ValueError): p.validate()
