import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import unittest
from aggie_analytics.experimentation.hpo_engine import DiscreteParameter,enumerate_trials,run_trials

class HPOEngineFullTests(unittest.TestCase):
    def test_budget(self):
        ts=enumerate_trials("S",[DiscreteParameter("d",[2,3,4]),DiscreteParameter("lr",[.1,.2])],4)
        self.assertEqual(len(ts),4);self.assertEqual(len({t.trial_id for t in ts}),4)
    def test_run(self):
        ts=enumerate_trials("S",[DiscreteParameter("x",[1,2])],2)
        rs=run_trials(ts,lambda p:p["x"]**2)
        self.assertEqual([r.objective for r in rs],[1.0,4.0])
