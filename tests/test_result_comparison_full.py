import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import unittest
from aggie_analytics.experimentation.comparison import MetricValue,metric_delta,assert_semantically_compatible,pareto_dominated,ordered_development_ranking

class ResultComparisonFullTests(unittest.TestCase):
    def packet(self,eid,split="SPLIT-DEV-SEL",lane="PURE_FOOTBALL",mae=7.0):
        return {"experiment_id":eid,"target":"margin","split_id":split,"data_snapshot_id":"D1","feature_version":"F1","metric_registry_version":"M1","lane":lane,"bas_anchor_version":None,"tamu_baseline_version":None,"metrics":{"mae":mae}}
    def test_compatibility(self):
        assert_semantically_compatible(self.packet("A"),self.packet("B"))
        with self.assertRaises(ValueError): assert_semantically_compatible(self.packet("A"),self.packet("B",lane="MARKET_AUGMENTED"))
    def test_protected_ranking_rejected(self):
        with self.assertRaises(ValueError): ordered_development_ranking([self.packet("A",split="SPLIT-PROTECTED"),self.packet("B")],primary_metric="mae",direction="min")
    def test_delta_direction(self):
        self.assertGreater(metric_delta(MetricValue("mae",6.0,"min"),MetricValue("mae",7.0,"min")),0)
