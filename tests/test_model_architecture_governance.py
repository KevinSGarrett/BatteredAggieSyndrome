
from __future__ import annotations
import csv,sys,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"src"))
from tools.validate_model_architecture import validate
from aggie_analytics.modeling import (
    ScoreOutcome,JointScoreDistribution,SimulationScenario,derive_summary,margin_pmf,
    bas_severity_probabilities,mix_joint_distributions,sample_score_outcomes,
    UncertaintySignal,validate_uncertainty_signals
)

def dist(outcomes, ot=None):
    return JointScoreDistribution("d","m","v",datetime(2026,8,8,17,tzinfo=timezone.utc),
                                  tuple(ScoreOutcome(*x) for x in outcomes),ot)

class ModelArchitectureGovernanceTests(unittest.TestCase):
    def test_registry(self): self.assertEqual([],validate(ROOT))
    def test_normalization(self):
        with self.assertRaises(ValueError):
            dist([(20,10,.6),(10,20,.5)]).validate()
    def test_coherent_summary(self):
        d=dist([(30,20,.6),(20,30,.4)]);s=derive_summary(d)
        self.assertAlmostEqual(s["win_probability"],.6);self.assertAlmostEqual(s["loss_probability"],.4)
        self.assertAlmostEqual(s["expected_margin"],2.0);self.assertEqual(margin_pmf(d),{-10:.4,10:.6})
    def test_tie_requires_ot(self):
        d=dist([(20,20,.2),(30,20,.8)])
        with self.assertRaises(ValueError):d.validate()
        d=dist([(20,20,.2),(30,20,.8)],.6);s=derive_summary(d)
        self.assertAlmostEqual(s["win_probability"],.92);self.assertAlmostEqual(s["loss_probability"],.08)
    def test_bas_probabilities_nested(self):
        d=dist([(30,20,.25),(20,20,.25),(10,20,.25),(0,20,.25)],.5)
        p=bas_severity_probabilities(d,10)
        self.assertGreaterEqual(p["ge_3"],p["ge_7"]);self.assertGreaterEqual(p["ge_7"],p["ge_14"]);self.assertGreaterEqual(p["ge_14"],p["ge_21"])
    def test_scenario_mixture(self):
        d1=dist([(30,20,1.0)]);d2=dist([(10,20,1.0)])
        s1=SimulationScenario("s1","snap",.75,{},{"e":"1"});s2=SimulationScenario("s2","snap",.25,{},{"e":"2"})
        m=mix_joint_distributions([(s1,d1),(s2,d2)],distribution_id="mix",model_id="mixm",model_version="v")
        self.assertAlmostEqual(derive_summary(m)["win_probability"],.75)
    def test_seed_reproducible(self):
        d=dist([(30,20,.5),(10,20,.5)])
        self.assertEqual(sample_score_outcomes(d,20,7),sample_score_outcomes(d,20,7))
    def test_uncertainty_numeric_requires_calibration(self):
        with self.assertRaises(ValueError): validate_uncertainty_signals([UncertaintySignal("x","EPISTEMIC_MODEL","WARN",0.4,False)])
        self.assertTrue(validate_uncertainty_signals([UncertaintySignal("x","EPISTEMIC_MODEL","WARN",None,False)]))
    def test_thresholds_blank(self):
        with (ROOT/"governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
        by={x["threshold_id"]:x for x in r}
        self.assertEqual("",by["THR-014"]["value"]);self.assertEqual("",by["THR-015"]["value"])
if __name__=="__main__":unittest.main()
