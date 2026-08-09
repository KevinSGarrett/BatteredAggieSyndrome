import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.experimentation.hypotheses import HypothesisRecord, validate_transition

class HypothesisTests(unittest.TestCase):
    def test_record_requires_falsifiable_fields(self):
        h=HypothesisRecord("H1","X improves Y","margin","baseline","no development gain"); h.validate()
    def test_terminal_reject_cannot_reopen_in_place(self):
        with self.assertRaises(ValueError): validate_transition("REJECTED","TRIAGED")
    def test_approved_to_testing(self):
        validate_transition("APPROVED_FOR_EXPERIMENT","TESTING")
