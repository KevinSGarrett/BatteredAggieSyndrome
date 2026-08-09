import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.experimentation.tournaments import TournamentSpec

class ModelTournamentTests(unittest.TestCase):
    def test_tamu_specialization_requires_no_adjustment_baseline(self):
        bad=TournamentSpec("M1","MODEL","tamu_margin","SPLIT-DEV-SEL","mae","min",["X","Y"],"X",tamu_specialization=True)
        with self.assertRaises(ValueError): bad.validate()
        ok=TournamentSpec("M2","MODEL","tamu_margin","SPLIT-DEV-SEL","mae","min",["TAMU-SP-00","X"],"TAMU-SP-00",tamu_specialization=True)
        ok.validate()
    def test_model_tournament_needs_two_entrants(self):
        s=TournamentSpec("M1","MODEL","win","SPLIT-DEV-SEL","brier","min",["BASE"],"BASE")
        with self.assertRaises(ValueError): s.validate()
