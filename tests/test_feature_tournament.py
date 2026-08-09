import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.experimentation.tournaments import TournamentSpec, TournamentEntry, rank_entries, validate_research_decision

class FeatureTournamentTests(unittest.TestCase):
    def test_requires_development_split(self):
        s=TournamentSpec("T1","FEATURE","margin","SPLIT-PROTECTED","mae","min",["BASE","F1"],"BASE")
        with self.assertRaises(ValueError): s.validate()
    def test_rank_is_development_only_and_deterministic(self):
        s=TournamentSpec("T1","FEATURE","margin","SPLIT-DEV-SEL","mae","min",["BASE","F1"],"BASE")
        e=[TournamentEntry("BASE","EXP-b","baseline",{"mae":7.0}),TournamentEntry("F1","EXP-f","feature",{"mae":6.5})]
        self.assertEqual([x.entry_id for x in rank_entries(s,e)],["F1","BASE"])
    def test_feature_tournament_cannot_promote(self):
        with self.assertRaises(ValueError): validate_research_decision("CORE")
        with self.assertRaises(ValueError): validate_research_decision("PROMOTE")
        validate_research_decision("ADOPT_AS_CHALLENGER")
