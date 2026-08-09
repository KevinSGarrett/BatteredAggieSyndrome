import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import unittest
from aggie_analytics.experimentation.feature_tournament import FeatureFamilyCandidate,FeatureTournamentEvidence,research_disposition,validate_outcome

class FeatureTournamentFullTests(unittest.TestCase):
    def test_temporal_block(self):
        c=FeatureFamilyCandidate("F","margin",["RAW1"],["BANNED_FROM_PREGAME"],"T1","BASE","CAND")
        with self.assertRaises(ValueError): c.validate()
    def test_stability_required(self):
        e=FeatureTournamentEvidence("F","E0","E1",None,"SPLIT-DEV-SEL","mae","margin",False,True,True,5)
        self.assertEqual(research_disposition(e),"RETAIN_EXPERIMENTAL")
    def test_no_production_promotion(self):
        for state in ("CORE","SUPPORTED","PROMOTE"):
            with self.assertRaises(ValueError): validate_outcome(state)
