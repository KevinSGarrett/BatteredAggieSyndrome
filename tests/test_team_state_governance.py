from __future__ import annotations
import csv,json,sys,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"src"))
from tools.validate_team_state import validate
from aggie_analytics.team_state import (
    StrengthEstimate,TeamStateSnapshot,placeholder_available_strength,
    exponential_recency_weight,weighted_similarity,combined_history_weight,
    blend_prior_observed,pseudo_count_blend,precision_weighted_blend,
    standardized_shift,CompetitionLevel,affine_translation,root_sum_square_uncertainty
)

class TeamStateGovernanceTests(unittest.TestCase):
    def test_registry_contract(self): self.assertEqual([],validate(ROOT))
    def test_state_semantics_separate(self):
        u=StrengthEstimate(80,3,"prior"); a=placeholder_available_strength(u)
        s=TeamStateSnapshot("TAMU",datetime(2026,8,8,tzinfo=timezone.utc),StrengthEstimate(78,5),u,a,None,None,0,"regime-x",{"state_epistemic":5})
        self.assertEqual(80,s.underlying_strength.value);self.assertEqual(80,s.available_strength.value);self.assertEqual(0,s.current_season_games)
    def test_recency_has_no_default_decay(self):
        self.assertAlmostEqual(1.0,exponential_recency_weight(4,0))
        self.assertLess(exponential_recency_weight(4,.2),1)
        with self.assertRaises(ValueError):exponential_recency_weight(1,-.1)
    def test_regime_similarity_is_explicitly_weighted(self):
        v=weighted_similarity({"hc":1.0,"qb":0.0},{"hc":1.0,"qb":1.0})
        self.assertEqual(.5,v);self.assertEqual(.25,combined_history_weight(.5,.5))
    def test_early_blend_is_parameterized(self):
        self.assertEqual(75,blend_prior_observed(70,80,.5))
        self.assertEqual(75,pseudo_count_blend(70,80,2,2))
        x=precision_weighted_blend(70,10,80,10);self.assertEqual(75,x)
    def test_change_point_has_no_frozen_threshold(self):
        self.assertEqual(2,standardized_shift(10,14,2))
        with (ROOT/"governance/CHANGE_POINT_CANDIDATES.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
        self.assertTrue(all(not x["threshold"] and x["automatic_reset"]=="false" for x in r))
    def test_lower_division_translation_has_no_fixed_penalty(self):
        self.assertEqual(50,affine_translation(50,scale=1,offset=0))
        self.assertGreater(root_sum_square_uncertainty(3,4),4.9)
        with (ROOT/"governance/OPPONENT_STRENGTH_HIERARCHY.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
        self.assertEqual(["FBS","FCS","DII","DIII","NAIA","JUCO","OTHER"],[x["division"] for x in r])
        self.assertTrue(all(x["fixed_fbs_equivalent_penalty"]=="false" for x in r))
    def test_w10_candidates_not_promoted(self):
        with (ROOT/"governance/FEATURE_CANDIDATE_SEEDS.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
        self.assertEqual(736,len(r));self.assertTrue(all(x["initial_lifecycle_state"]=="EXPERIMENTAL" and x["production_approved"]=="false" for x in r))
if __name__=="__main__":unittest.main()
