import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.validation import (
    brier_score,log_loss,mae,rmse,expected_calibration_error,
    bas_probabilities_are_nested,classify_season,PromotionContext,evaluate_promotion,
)

class ValidationScienceTests(unittest.TestCase):
    def test_protected_split_boundaries(self):
        self.assertEqual(classify_season(2022),"DEVELOPMENT")
        self.assertEqual(classify_season(2023),"DEVELOPMENT_SELECTION")
        self.assertEqual(classify_season(2024),"PROTECTED_TEST")
        self.assertEqual(classify_season(2025),"PROTECTED_TEST")
        self.assertEqual(classify_season(2026),"FORWARD_SHADOW")

    def test_reference_metrics(self):
        self.assertAlmostEqual(brier_score([1,0],[0.8,0.3]),0.065)
        self.assertGreater(log_loss([1,0],[0.8,0.3]),0.0)
        self.assertEqual(mae([1,3],[2,1]),1.5)
        self.assertAlmostEqual(rmse([1,3],[2,1]),(2.5)**0.5)

    def test_ece_requires_explicit_bins(self):
        value=expected_calibration_error([1,0,1,0],[0.9,0.1,0.6,0.4],bin_edges=[0.0,0.5,1.0])
        self.assertGreaterEqual(value,0.0)

    def test_bas_nested(self):
        self.assertTrue(bas_probabilities_are_nested(0.4,0.3,0.2,0.1))
        self.assertFalse(bas_probabilities_are_nested(0.2,0.3,0.1,0.05))

    def test_blank_threshold_blocks_promotion(self):
        ctx=PromotionContext(True,True,["THR-001"],{"THR-001":None})
        self.assertEqual(evaluate_promotion(ctx),"BLOCKED_THRESHOLD_UNSET")

    def test_ready_before_protected_results(self):
        ctx=PromotionContext(True,True,["THR-001"],{"THR-001":0.01},False,None)
        self.assertEqual(evaluate_promotion(ctx),"PROTECTED_READY")

    def test_registry_claims_no_empirical_results(self):
        reg=json.loads((ROOT/"configs/validation_science_registry.json").read_text())
        self.assertFalse(reg["protected_empirical_results_inspected_w17"])
        self.assertFalse(reg["trained_model_metrics_claimed_w17"])
        self.assertFalse(reg["selected_model_family_w17"])

if __name__=="__main__":
    unittest.main()
