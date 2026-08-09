from __future__ import annotations
import csv,sys,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"src"))
from tools.validate_tamu_specialization import validate
from aggie_analytics.tamu import TamuStateOverlay,ForecastSnapshotCandidate,SpecializationSignal,no_adjustment_signal,shrink_adjustment,weighted_similarity
from aggie_analytics.tamu.state import validate_snapshot_order
from aggie_analytics.tamu.specialization import manual_aggie_bonus

class TamuSpecializationGovernanceTests(unittest.TestCase):
    def test_registry_contract(self):self.assertEqual([],validate(ROOT))
    def test_same_identity_overlay_and_uncertainty(self):
        t=datetime(2026,8,8,tzinfo=timezone.utc)
        s=TamuStateOverlay("TAMU",t,"national:TAMU","pit:TAMU",{"qb":"q1"},{"availability":2.0})
        self.assertEqual("TAMU",s.team_id);self.assertEqual("national:TAMU",s.national_team_state_ref)
    def test_no_adjustment_baseline_is_zero(self):
        s=no_adjustment_signal("margin");self.assertEqual(0.0,s.raw_adjustment);self.assertEqual(0.0,s.shrunk_adjustment);self.assertFalse(s.production_selected)
    def test_shrinkage_can_reach_zero(self):
        self.assertEqual(0.0,shrink_adjustment(7.0,0.0));self.assertEqual(7.0,shrink_adjustment(7.0,1.0))
        with self.assertRaises(ValueError):shrink_adjustment(1,1.1)
    def test_w14_cannot_production_select_signal(self):
        with self.assertRaises(ValueError):SpecializationSignal("x","margin",1,.5,1,True)
    def test_peer_similarity_has_no_default_weights(self):
        self.assertAlmostEqual(.75,weighted_similarity({"a":1.0,"b":.5},{"a":1.0,"b":1.0}))
        with self.assertRaises(ValueError):weighted_similarity({"a":1.0},{"b":1.0})
    def test_snapshot_candidates_are_immutable_ordered(self):
        t=datetime(2026,8,8,tzinfo=timezone.utc);a=ForecastSnapshotCandidate("a","g",t,"c");b=ForecastSnapshotCandidate("b","g",t+timedelta(hours=1),"c")
        self.assertTrue(validate_snapshot_order((a,b)))
        with self.assertRaises(ValueError):ForecastSnapshotCandidate("x","g",t,"c",False)
    def test_manual_aggie_bonus_forbidden(self):
        with self.assertRaises(RuntimeError):manual_aggie_bonus("12th man",3)
    def test_all_candidates_unselected_and_thr005_blank(self):
        with (ROOT/"governance/TAMU_SPECIALIZATION_CANDIDATES.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
        self.assertTrue(all(x["production_selected_w14"]=="false" for x in r));self.assertTrue(any(x["candidate_id"]=="TAMU-SP-00" for x in r))
        with (ROOT/"governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv").open(newline="",encoding="utf-8") as f:t=list(csv.DictReader(f))
        x=next(x for x in t if x["threshold_id"]=="THR-005");self.assertEqual("",x["value"])
    def test_w10_candidates_still_unpromoted(self):
        with (ROOT/"governance/FEATURE_CANDIDATE_SEEDS.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
        self.assertEqual(736,len(r));self.assertTrue(all(x["initial_lifecycle_state"]=="EXPERIMENTAL" and x["production_approved"]=="false" for x in r))
if __name__=="__main__":unittest.main()
