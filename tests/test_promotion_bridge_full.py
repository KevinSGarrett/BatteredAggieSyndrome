import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import unittest
from aggie_analytics.experimentation.promotion_bridge import PromotionReviewPacket,validate_research_handoff,contains_protected_result_feedback

class PromotionBridgeFullTests(unittest.TestCase):
    def test_only_review_request(self):
        p=PromotionReviewPacket("E","R","RP","a"*64,"b"*64,"c"*64,"PROMOTION_REVIEW_REQUIRED")
        p.validate()
    def test_promote_rejected(self):
        with self.assertRaises(ValueError): validate_research_handoff("PROMOTE")
    def test_protected_feedback_detected(self):
        self.assertTrue(contains_protected_result_feedback({"protected_metrics":{"brier":.1}}))
