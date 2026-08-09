import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import unittest
from aggie_analytics.experimentation.advanced_challengers import ChallengerAdmissionEvidence

class AdvancedChallengerFullTests(unittest.TestCase):
    def base(self,**kw):
        d=dict(candidate_class="SEQUENCE_TRANSFORMER",conventional_baseline_materialized=False,baseline_saturated_or_specific_gap_demonstrated=False,protected_protocol_sealed=True,development_only_plan=True,local_resource_budget_declared=True,incremental_hypothesis="sequence matters",complexity_rationale="test sequential dependence",required_inputs_available=True,rights_ok=True,maintenance_owner="research")
        d.update(kw);return ChallengerAdmissionEvidence(**d)
    def test_blocked_without_baseline(self):
        state,reasons=self.base().evaluate();self.assertEqual(state,"BLOCKED");self.assertIn("CONVENTIONAL_BASELINE_NOT_MATERIALIZED",reasons)
    def test_admitted_only_when_all_gates(self):
        state,reasons=self.base(conventional_baseline_materialized=True,baseline_saturated_or_specific_gap_demonstrated=True).evaluate()
        self.assertEqual(state,"ADMITTED_RESEARCH_ONLY");self.assertEqual(reasons,())
