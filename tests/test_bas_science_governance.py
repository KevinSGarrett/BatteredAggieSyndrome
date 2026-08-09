from __future__ import annotations
import csv,sys,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"src"))
from tools.validate_bas_science import validate
from aggie_analytics.bas import ExpectedMarginEvidence,build_tamu_bas_label,performance_residual,severity_flags,validate_nested_probability_forecast,descriptive_excess_rate
def ev(**kw):
    t=datetime(2026,8,8,17,tzinfo=timezone.utc);d=dict(evidence_id="e1",target_game_id="g1",model_id="m",model_version="v",fold_id="f",expected_margin=10.0,prediction_cutoff=t,model_training_cutoff=t-timedelta(days=1));d.update(kw);return ExpectedMarginEvidence(**d)
class BasScienceGovernanceTests(unittest.TestCase):
    def test_registry(self):self.assertEqual([],validate(ROOT))
    def test_sign_threshold(self):self.assertEqual(-7.0,performance_residual(3,10));self.assertTrue(severity_flags(3,10)["ge_7"])
    def test_nested(self):self.assertTrue(validate_nested_probability_forecast(.4,.3,.2,.1));self.assertRaises(ValueError,validate_nested_probability_forecast,.2,.3,.1,.05)
    def test_label(self):self.assertTrue(build_tamu_bas_label("g1",3,ev()).ge_7);self.assertRaises(ValueError,build_tamu_bas_label,"x",3,ev())
    def test_target_exclusion(self):self.assertRaises(ValueError,ev(target_game_excluded=False).validate);self.assertRaises(ValueError,ev(canonical_game_group_excluded=False).validate)
    def test_chronology(self):
        t=datetime(2026,8,8,17,tzinfo=timezone.utc);self.assertRaises(ValueError,ev(model_training_cutoff=t).validate)
    def test_circular(self):self.assertRaises(ValueError,ev(uses_bas_target=True).validate);self.assertRaises(ValueError,ev(uses_aggie_underperformance_target=True).validate)
    def test_descriptive_only(self):self.assertAlmostEqual(.75,descriptive_excess_rate([True,True],[True,False,False,False]))
    def test_thr006_blank(self):
        with (ROOT/"governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
        self.assertEqual("",next(x for x in r if x["threshold_id"]=="THR-006")["value"])
    def test_null_path(self):
        with (ROOT/"governance/BAS_NULL_RESULT_POLICY.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
        self.assertTrue(any("No A&M-specific excess" in x["rule"] for x in r))
if __name__=="__main__":unittest.main()
