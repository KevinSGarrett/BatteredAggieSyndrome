import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import unittest
from aggie_analytics.experimentation.model_tournament import ModelEntrant,ModelTournamentPlan,validate_research_decision

class ModelTournamentFullTests(unittest.TestCase):
    def e(self,i,cls="ELO",lane="PURE_FOOTBALL",tamu=None,bas=None,coherent=True):
        return ModelEntrant(i,"fam",cls,"margin",lane,"EXP-"+i,"C1",coherent,tamu,bas)
    def test_simple_baseline_required(self):
        p=ModelTournamentPlan("T","margin","SPLIT-DEV-SEL","PURE_FOOTBALL",[self.e("A","BOOSTED"),self.e("B","NEURAL")],"mae","min")
        with self.assertRaises(ValueError): p.validate()
    def test_tamu_no_adjustment_required(self):
        p=ModelTournamentPlan("T","margin","SPLIT-DEV-SEL","PURE_FOOTBALL",[self.e("A","ELO"),self.e("B","BOOSTED",tamu="TAMU-SP-01")],"mae","min",tamu_specialization=True)
        with self.assertRaises(ValueError): p.validate()
    def test_valid_tamu(self):
        p=ModelTournamentPlan("T","margin","SPLIT-DEV-SEL","PURE_FOOTBALL",[self.e("A","ELO",tamu="TAMU-SP-00"),self.e("B","BOOSTED",tamu="TAMU-SP-01")],"mae","min",tamu_specialization=True)
        p.validate()
    def test_no_promote(self):
        with self.assertRaises(ValueError): validate_research_decision("PROMOTE")
