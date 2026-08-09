import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.experimentation.replay import compare_hashes
from aggie_analytics.experimentation.adoption import adoption_decision

class ReplayAdoptionTests(unittest.TestCase):
    def test_hash_match_verifies(self):
        r=compare_hashes({"a":"1"},{"a":"1"}); self.assertEqual(r.status,"VERIFIED")
    def test_hash_mismatch_blocks(self):
        r=compare_hashes({"a":"1"},{"a":"2"}); self.assertEqual(r.status,"MISMATCH"); self.assertEqual(r.failure_code,"HASH_MISMATCH")
    def test_adoption_requires_verified_replay(self):
        self.assertEqual(adoption_decision(replay_status="MISMATCH",recommendation="ADOPT_AS_CHALLENGER"),"BLOCKED_REPLAY_NOT_VERIFIED")
        self.assertEqual(adoption_decision(replay_status="VERIFIED",recommendation="ADOPT_AS_CHALLENGER"),"ADOPT_AS_CHALLENGER")
    def test_research_cannot_promote(self):
        with self.assertRaises(ValueError): adoption_decision(replay_status="VERIFIED",recommendation="PROMOTE")
